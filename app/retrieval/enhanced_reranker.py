"""Enhanced Reranker with Advanced Features

This module provides an enhanced reranking system with support for
batch processing, caching, multiple reranking strategies, and performance optimization.
"""

from typing import List, Dict, Any, Optional, Tuple, Union
import asyncio
import time
import hashlib
import json
from dataclasses import dataclass
from enum import Enum
from collections import defaultdict

from app.workflow.qianwen_client import get_qianwen_client
from app.retrieval.reranker import QianwenReranker
from app.utils.logger import setup_logger
from app.core.config import get_settings

logger = setup_logger(__name__)
settings = get_settings()


class RerankStrategy(Enum):
    """Reranking strategies"""
    QIANWEN_API = "qianwen_api"  # Use Qianwen API for reranking
    SCORE_FUSION = "score_fusion"  # Fuse multiple scores
    HYBRID = "hybrid"  # Combine API and score fusion
    SEMANTIC_SIMILARITY = "semantic_similarity"  # Use embedding similarity


@dataclass
class RerankResult:
    """Container for rerank results"""
    documents: List[Dict[str, Any]]
    rerank_time: float
    strategy_used: RerankStrategy
    cache_hit: bool = False
    api_calls: int = 0
    error: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class RerankCache:
    """Simple in-memory cache for rerank results"""
    
    def __init__(self, max_size: int = 1000, ttl: int = 3600):
        self.max_size = max_size
        self.ttl = ttl
        self.cache = {}
        self.access_times = {}
        self._hits = 0
        self._misses = 0
    
    def _generate_key(self, query: str, doc_ids: List[str], strategy: RerankStrategy) -> str:
        """Generate cache key"""
        content = f"{query}:{':'.join(sorted(doc_ids))}:{strategy.value}"
        return hashlib.md5(content.encode()).hexdigest()
    
    def get(self, query: str, documents: List[Dict[str, Any]], 
           strategy: RerankStrategy) -> Optional[List[Dict[str, Any]]]:
        """Get cached rerank result"""
        doc_ids = [doc.get('id', doc.get('chunk_id', str(i))) 
                  for i, doc in enumerate(documents)]
        key = self._generate_key(query, doc_ids, strategy)
        
        if key in self.cache:
            cached_data, timestamp = self.cache[key]
            
            # Check TTL
            if time.time() - timestamp < self.ttl:
                self.access_times[key] = time.time()
                self._hits += 1
                return cached_data
            else:
                # Expired
                del self.cache[key]
                if key in self.access_times:
                    del self.access_times[key]
        
        self._misses += 1
        return None
    
    def set(self, query: str, documents: List[Dict[str, Any]], 
           strategy: RerankStrategy, result: List[Dict[str, Any]]):
        """Cache rerank result"""
        doc_ids = [doc.get('id', doc.get('chunk_id', str(i))) 
                  for i, doc in enumerate(documents)]
        key = self._generate_key(query, doc_ids, strategy)
        
        # Evict oldest if cache is full
        if len(self.cache) >= self.max_size:
            oldest_key = min(self.access_times.keys(), 
                           key=lambda k: self.access_times[k])
            del self.cache[oldest_key]
            del self.access_times[oldest_key]
        
        self.cache[key] = (result, time.time())
        self.access_times[key] = time.time()
    
    def clear(self):
        """Clear cache"""
        self.cache.clear()
        self.access_times.clear()
        self._hits = 0
        self._misses = 0
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        total_requests = self._hits + self._misses
        hit_rate = self._hits / max(1, total_requests)
        return {
            'size': len(self.cache),
            'max_size': self.max_size,
            'hits': self._hits,
            'misses': self._misses,
            'hit_rate': hit_rate
        }


class ScoreFusionReranker:
    """Score fusion based reranker"""
    
    def __init__(self, weights: Optional[Dict[str, float]] = None):
        """
        Initialize score fusion reranker
        
        Args:
            weights: Weights for different score types
        """
        self.weights = weights or {
            'fusion_score': 0.4,
            'bm25_score': 0.3,
            'similarity_score': 0.2,
            'rerank_score': 0.1
        }
    
    def rerank_documents(self, query: str, documents: List[Dict[str, Any]], 
                        top_k: int = 20) -> List[Dict[str, Any]]:
        """Rerank documents using score fusion"""
        if not documents:
            return []
        
        # Calculate fused scores
        for doc in documents:
            fused_score = 0.0
            total_weight = 0.0
            
            for score_type, weight in self.weights.items():
                if score_type in doc and doc[score_type] is not None:
                    fused_score += weight * float(doc[score_type])
                    total_weight += weight
            
            # Normalize by total weight
            if total_weight > 0:
                doc['fused_rerank_score'] = fused_score / total_weight
            else:
                doc['fused_rerank_score'] = 0.0
        
        # Sort by fused score
        documents.sort(key=lambda x: x.get('fused_rerank_score', 0.0), reverse=True)
        
        return documents[:top_k]


class EnhancedReranker:
    """Enhanced reranker with multiple strategies and optimizations"""
    
    def __init__(self, 
                 strategy: RerankStrategy = RerankStrategy.QIANWEN_API,
                 enable_cache: bool = True,
                 cache_size: int = 1000,
                 cache_ttl: int = 3600,
                 batch_size: int = 50,
                 max_concurrent: int = 3,
                 fallback_strategy: Optional[RerankStrategy] = None):
        """
        Initialize enhanced reranker
        
        Args:
            strategy: Primary reranking strategy
            enable_cache: Whether to enable caching
            cache_size: Maximum cache size
            cache_ttl: Cache TTL in seconds
            batch_size: Batch size for API calls
            max_concurrent: Maximum concurrent API calls
            fallback_strategy: Fallback strategy if primary fails
        """
        self.strategy = strategy
        self.fallback_strategy = fallback_strategy or RerankStrategy.SCORE_FUSION
        self.batch_size = batch_size
        self.max_concurrent = max_concurrent
        
        # Initialize cache
        self.cache = RerankCache(cache_size, cache_ttl) if enable_cache else None
        
        # Initialize strategy-specific components
        self.qianwen_reranker = QianwenReranker()
        self.score_fusion_reranker = ScoreFusionReranker()
        
        # Performance tracking
        self.stats = {
            'total_requests': 0,
            'cache_hits': 0,
            'api_calls': 0,
            'avg_rerank_time': 0.0,
            'strategy_usage': defaultdict(int),
            'error_count': 0
        }
        
        logger.info(f"EnhancedReranker initialized with strategy: {strategy.value}")
    
    async def rerank_documents(self, 
                              query: str, 
                              documents: List[Dict[str, Any]], 
                              top_k: int = 20,
                              strategy_override: Optional[RerankStrategy] = None) -> RerankResult:
        """Enhanced document reranking with multiple strategies
        
        Args:
            query: Search query
            documents: Documents to rerank
            top_k: Number of top documents to return
            strategy_override: Override default strategy
            
        Returns:
            RerankResult with reranked documents and metadata
        """
        start_time = time.time()
        strategy = strategy_override or self.strategy
        
        self.stats['total_requests'] += 1
        self.stats['strategy_usage'][strategy] += 1
        
        # Check cache first
        cache_hit = False
        if self.cache:
            cached_result = self.cache.get(query, documents, strategy)
            if cached_result:
                self.stats['cache_hits'] += 1
                cache_hit = True
                
                return RerankResult(
                    documents=cached_result[:top_k],
                    rerank_time=time.time() - start_time,
                    strategy_used=strategy,
                    cache_hit=True,
                    api_calls=0
                )
        
        # Perform reranking
        try:
            if strategy == RerankStrategy.QIANWEN_API:
                result = await self._rerank_with_qianwen(query, documents, top_k)
            
            elif strategy == RerankStrategy.SCORE_FUSION:
                result = self._rerank_with_score_fusion(query, documents, top_k)
            
            elif strategy == RerankStrategy.HYBRID:
                result = await self._rerank_hybrid(query, documents, top_k)
            
            elif strategy == RerankStrategy.SEMANTIC_SIMILARITY:
                result = await self._rerank_with_similarity(query, documents, top_k)
            
            else:
                raise ValueError(f"Unsupported strategy: {strategy}")
            
            # Cache result
            if self.cache and not result.error:
                self.cache.set(query, documents, strategy, result.documents)
            
            # Update stats
            self._update_stats(result.rerank_time, result.api_calls, False)
            
            return result
            
        except Exception as e:
            logger.error(f"Reranking failed with strategy {strategy}: {str(e)}")
            self.stats['error_count'] += 1
            
            # Try fallback strategy
            if strategy != self.fallback_strategy:
                logger.info(f"Trying fallback strategy: {self.fallback_strategy}")
                try:
                    fallback_result = await self.rerank_documents(
                        query, documents, top_k, self.fallback_strategy
                    )
                    fallback_result.error = f"Primary strategy failed: {str(e)}"
                    return fallback_result
                    
                except Exception as fallback_error:
                    logger.error(f"Fallback strategy also failed: {str(fallback_error)}")
            
            # Return original order as last resort
            return RerankResult(
                documents=documents[:top_k],
                rerank_time=time.time() - start_time,
                strategy_used=strategy,
                cache_hit=cache_hit,
                api_calls=0,
                error=str(e)
            )
    
    async def _rerank_with_qianwen(self, query: str, documents: List[Dict[str, Any]], 
                                  top_k: int) -> RerankResult:
        """Rerank using Qianwen API"""
        start_time = time.time()
        api_calls = 0
        
        if len(documents) <= self.batch_size:
            # Single batch
            reranked_docs = await self.qianwen_reranker.rerank_documents(
                query, documents, top_k
            )
            api_calls = 1
        else:
            # Multiple batches
            reranked_docs = await self._batch_rerank_qianwen(query, documents, top_k)
            api_calls = (len(documents) + self.batch_size - 1) // self.batch_size
        
        self.stats['api_calls'] += api_calls
        
        return RerankResult(
            documents=reranked_docs,
            rerank_time=time.time() - start_time,
            strategy_used=RerankStrategy.QIANWEN_API,
            api_calls=api_calls
        )
    
    async def _batch_rerank_qianwen(self, query: str, documents: List[Dict[str, Any]], 
                                   top_k: int) -> List[Dict[str, Any]]:
        """Batch rerank with Qianwen API"""
        # Split into batches
        batches = [documents[i:i + self.batch_size] 
                  for i in range(0, len(documents), self.batch_size)]
        
        # Process batches with concurrency limit
        semaphore = asyncio.Semaphore(self.max_concurrent)
        
        async def process_batch(batch):
            async with semaphore:
                return await self.qianwen_reranker.rerank_documents(
                    query, batch, len(batch)
                )
        
        # Execute batches
        batch_results = await asyncio.gather(
            *[process_batch(batch) for batch in batches],
            return_exceptions=True
        )
        
        # Combine results
        all_reranked = []
        for result in batch_results:
            if isinstance(result, list):
                all_reranked.extend(result)
            else:
                logger.error(f"Batch rerank failed: {str(result)}")
        
        # Final sort by rerank score
        all_reranked.sort(
            key=lambda x: x.get('rerank_score', 0.0), 
            reverse=True
        )
        
        return all_reranked[:top_k]
    
    def _rerank_with_score_fusion(self, query: str, documents: List[Dict[str, Any]], 
                                 top_k: int) -> RerankResult:
        """Rerank using score fusion"""
        start_time = time.time()
        
        reranked_docs = self.score_fusion_reranker.rerank_documents(
            query, documents, top_k
        )
        
        return RerankResult(
            documents=reranked_docs,
            rerank_time=time.time() - start_time,
            strategy_used=RerankStrategy.SCORE_FUSION,
            api_calls=0
        )
    
    async def _rerank_hybrid(self, query: str, documents: List[Dict[str, Any]], 
                            top_k: int) -> RerankResult:
        """Hybrid reranking combining API and score fusion"""
        start_time = time.time()
        
        # First, use score fusion to get top candidates
        fusion_candidates = min(top_k * 3, len(documents))
        fusion_result = self._rerank_with_score_fusion(
            query, documents, fusion_candidates
        )
        
        # Then use API reranking on top candidates
        if len(fusion_result.documents) > top_k:
            api_result = await self._rerank_with_qianwen(
                query, fusion_result.documents, top_k
            )
            
            return RerankResult(
                documents=api_result.documents,
                rerank_time=time.time() - start_time,
                strategy_used=RerankStrategy.HYBRID,
                api_calls=api_result.api_calls
            )
        else:
            return RerankResult(
                documents=fusion_result.documents,
                rerank_time=time.time() - start_time,
                strategy_used=RerankStrategy.HYBRID,
                api_calls=0
            )
    
    async def _rerank_with_similarity(self, query: str, documents: List[Dict[str, Any]], 
                                     top_k: int) -> RerankResult:
        """Rerank using semantic similarity (placeholder)"""
        start_time = time.time()
        
        # For now, just use existing similarity scores
        # This can be enhanced with actual embedding similarity computation
        documents_copy = documents.copy()
        documents_copy.sort(
            key=lambda x: x.get('similarity_score', 0.0), 
            reverse=True
        )
        
        return RerankResult(
            documents=documents_copy[:top_k],
            rerank_time=time.time() - start_time,
            strategy_used=RerankStrategy.SEMANTIC_SIMILARITY,
            api_calls=0
        )
    
    def _update_stats(self, rerank_time: float, api_calls: int, error: bool):
        """Update performance statistics"""
        # Update average rerank time
        total_requests = self.stats['total_requests']
        self.stats['avg_rerank_time'] = (
            (self.stats['avg_rerank_time'] * (total_requests - 1) + rerank_time) / total_requests
        )
        
        # Update API calls and error count
        self.stats['api_calls'] += api_calls
        if error:
            self.stats['error_count'] += 1
    
    def get_stats(self) -> Dict[str, Any]:
        """Get performance statistics"""
        stats = self.stats.copy()
        if self.cache:
            stats['cache_stats'] = self.cache.get_stats()
        return stats
    
    def reset_stats(self):
        """Reset performance statistics"""
        self.stats = {
            'total_requests': 0,
            'cache_hits': 0,
            'api_calls': 0,
            'avg_rerank_time': 0.0,
            'strategy_usage': defaultdict(int),
            'error_count': 0
        }
        
        if self.cache:
            self.cache.clear()
    
    def update_strategy(self, strategy: RerankStrategy):
        """Update reranking strategy"""
        self.strategy = strategy
        logger.info(f"Updated reranking strategy to: {strategy.value}")


# Factory function for easy initialization
def create_enhanced_reranker(
    strategy: str = 'qianwen_api',
    enable_cache: bool = True,
    **kwargs
) -> EnhancedReranker:
    """Factory function to create EnhancedReranker
    
    Args:
        strategy: Reranking strategy name
        enable_cache: Whether to enable caching
        **kwargs: Additional parameters
        
    Returns:
        EnhancedReranker instance
    """
    strategy_enum = RerankStrategy(strategy)
    
    return EnhancedReranker(
        strategy=strategy_enum,
        enable_cache=enable_cache,
        **kwargs
    )