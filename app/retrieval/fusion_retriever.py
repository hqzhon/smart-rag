"""Advanced Multi-Path Fusion Retriever with Intelligent Optimization

This module implements the next-generation FusionRetriever with:
- Intelligent query routing
- Progressive retrieval with quality assessment
- Adaptive weight adjustment
- Enhanced reranking strategies
"""

from typing import List, Dict, Any, Optional, Tuple, Union
import asyncio
import time
import re
from dataclasses import dataclass, asdict

from app.storage.vector_store import VectorStore
from app.retrieval.multi_field_bm25 import MultiFieldBM25Retriever
from app.retrieval.fusion_algorithms import FusionEngine
from app.retrieval.enhanced_reranker import EnhancedReranker, RerankStrategy
from app.retrieval.advanced_config import AdvancedRAGConfig, RetrievalPath, FusionMethod
from app.retrieval.query_router import QueryRouter, QueryAnalysis, QueryType, QueryComplexity
from app.retrieval.progressive_retriever import ProgressiveRetriever, RetrievalStage, ProgressiveResult
from app.retrieval.adaptive_weights import AdaptiveWeightAdjuster, QueryContext, PerformanceMetrics, AdaptationStrategy
from app.retrieval.small_to_big_deduplicator import SmallToBigDeduplicator
from app.utils.logger import setup_logger
from app.core.config import get_settings

logger = setup_logger(__name__)
settings = get_settings()


@dataclass
class RetrievalResult:
    """Enhanced retrieval result with optimization metadata"""
    path: RetrievalPath
    documents: List[Dict[str, Any]]
    retrieval_time: float
    query_used: str
    confidence_score: float = 0.0
    quality_metrics: Optional[Dict[str, float]] = None
    error: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class OptimizedFusionResult:
    """Enhanced fusion result with optimization insights"""
    documents: List[Dict[str, Any]]
    total_time: float
    path_results: Dict[RetrievalPath, RetrievalResult]
    fusion_method: FusionMethod
    query_analysis: Optional[QueryAnalysis]
    progressive_stages: Optional[List[RetrievalStage]]
    weight_adjustments: Optional[Dict[str, Any]]
    optimization_stats: Dict[str, Any]
    config_used: Dict[str, Any]


class VectorRetriever:
    """Enhanced vector retrieval with quality assessment"""
    
    def __init__(self, vector_store: VectorStore):
        self.vector_store = vector_store
    
    async def retrieve(self, query: str, top_k: int = 10, 
                      filters: Optional[Dict[str, Any]] = None,
                      quality_threshold: float = 0.0) -> List[Dict[str, Any]]:
        """Retrieve documents with quality filtering"""
        try:
            results = await self.vector_store.similarity_search(
                query=query,
                k=top_k * 2,  # Get more for quality filtering
                filter_dict=filters
            )
            
            # Format and filter by quality
            formatted_results = []
            for i, result in enumerate(results):
                score = result.get('score', 0.0)
                if score >= quality_threshold:
                    doc = {
                        'id': result.get('id', f'vec_{i}'),
                        'content': result.get('page_content', result.get('content', '')),
                        'similarity_score': score,
                        'metadata': result.get('metadata', {}),
                        'retrieval_path': RetrievalPath.VECTOR.value,
                        'quality_score': score
                    }
                    formatted_results.append(doc)
            
            return formatted_results[:top_k]
            
        except Exception as e:
            logger.error(f"Vector retrieval failed: {str(e)}")
            return []


class AdvancedFusionRetriever:
    """Next-generation multi-path fusion retriever with intelligent optimization"""
    
    def __init__(self, 
                 vector_store: VectorStore,
                 documents: Optional[List[Dict[str, Any]]] = None,
                 config: Optional[AdvancedRAGConfig] = None,
                 enable_query_routing: bool = True,
                 enable_progressive: bool = True,
                 enable_adaptive_weights: bool = True):
        """
        Initialize Advanced Fusion Retriever
        
        Args:
            vector_store: Vector store for semantic retrieval
            documents: Document corpus for BM25 indexing
            config: Advanced RAG configuration
            enable_query_routing: Enable intelligent query routing
            enable_progressive: Enable progressive retrieval
            enable_adaptive_weights: Enable adaptive weight adjustment
        """
        self.vector_store = vector_store
        self.config = config or AdvancedRAGConfig()
        self.enable_query_routing = enable_query_routing
        self.enable_progressive = enable_progressive
        self.enable_adaptive_weights = enable_adaptive_weights
        
        # Initialize core retrievers
        self.vector_retriever = VectorRetriever(vector_store)
        self.bm25_retriever = None
        
        if documents:
            self.bm25_retriever = MultiFieldBM25Retriever(documents)
        
        # Initialize fusion and reranking
        self.fusion_engine = FusionEngine()
        
        # Initialize small-to-big deduplicator
        self.deduplicator = SmallToBigDeduplicator()
        self.reranker = None
        
        if self.config.rerank.enabled:
            self.reranker = EnhancedReranker(
                batch_size=self.config.rerank.batch_size,
                max_concurrent=self.config.rerank.max_concurrent,
                strategy=RerankStrategy.HYBRID
            )
        
        # Initialize optimization components
        self.query_router = QueryRouter() if enable_query_routing else None
        self.progressive_retriever = ProgressiveRetriever(self, config) if enable_progressive else None
        self.weight_adjuster = AdaptiveWeightAdjuster(
            strategy=AdaptationStrategy.HYBRID
        ) if enable_adaptive_weights else None
        
        # Enhanced performance tracking
        self.performance_stats = {
            'total_queries': 0,
            'avg_retrieval_time': 0.0,
            'avg_fusion_time': 0.0,
            'path_success_rates': {path: 0.0 for path in RetrievalPath},
            'query_routing_accuracy': 0.0,
            'progressive_early_stops': 0,
            'weight_adjustments': 0,
            'cache_hit_rate': 0.0,
            'quality_improvements': 0.0
        }
        
        logger.info(f"AdvancedFusionRetriever initialized with optimizations: "
                   f"routing={enable_query_routing}, progressive={enable_progressive}, "
                   f"adaptive={enable_adaptive_weights}")
    
    def update_documents(self, documents: List[Dict[str, Any]]):
        """Update document corpus and rebuild indices"""
        try:
            self.bm25_retriever = MultiFieldBM25Retriever(documents)
            logger.info(f"Updated BM25 indices with {len(documents)} documents")
        except Exception as e:
            logger.error(f"Failed to update documents: {str(e)}")
            raise
    
    def update_config(self, config: AdvancedRAGConfig):
        """Update configuration and components"""
        self.config = config
        
        # Update reranker
        if config.rerank.enabled and not self.reranker:
            self.reranker = EnhancedReranker(
                batch_size=config.rerank.batch_size,
                max_concurrent=config.rerank.max_concurrent,
                strategy=RerankStrategy.HYBRID
            )
        elif not config.rerank.enabled:
            self.reranker = None
        elif self.reranker:
            self.reranker.update_strategy(RerankStrategy.HYBRID)
        
        # Update progressive retriever
        if self.progressive_retriever:
            self.progressive_retriever.config = config
        
        logger.info("Configuration updated successfully")
    
    async def retrieve_single_path(self, 
                                  path: RetrievalPath, 
                                  query: str, 
                                  top_k: int,
                                  quality_threshold: float = 0.0,
                                  filters: Optional[Dict[str, Any]] = None) -> RetrievalResult:
        """Enhanced single path retrieval with quality assessment"""
        start_time = time.time()
        
        try:
            documents = []
            confidence_score = 0.0
            
            if path == RetrievalPath.VECTOR:
                documents = await self.vector_retriever.retrieve(
                    query, top_k, filters, quality_threshold
                )
                confidence_score = sum(doc.get('similarity_score', 0) for doc in documents) / max(len(documents), 1)
            
            elif path == RetrievalPath.KEYWORDS and self.bm25_retriever:
                documents = await self.bm25_retriever.search_field_async(
                    'keywords', query, top_k
                )
                for doc in documents:
                    doc['retrieval_path'] = RetrievalPath.KEYWORDS.value
                confidence_score = sum(doc.get('bm25_score', 0) for doc in documents) / max(len(documents), 1)
            
            elif path == RetrievalPath.SUMMARY and self.bm25_retriever:
                documents = await self.bm25_retriever.search_field_async(
                    'summary', query, top_k
                )
                for doc in documents:
                    doc['retrieval_path'] = RetrievalPath.SUMMARY.value
                confidence_score = sum(doc.get('bm25_score', 0) for doc in documents) / max(len(documents), 1)
            
            elif path == RetrievalPath.CONTENT and self.bm25_retriever:
                documents = await self.bm25_retriever.search_field_async(
                    'content', query, top_k
                )
                for doc in documents:
                    doc['retrieval_path'] = RetrievalPath.CONTENT.value
                confidence_score = sum(doc.get('bm25_score', 0) for doc in documents) / max(len(documents), 1)
            
            else:
                logger.warning(f"Path {path} not available or not configured")
            
            retrieval_time = time.time() - start_time
            
            # Calculate quality metrics
            quality_metrics = {
                'relevance_score': confidence_score,
                'diversity_score': self._calculate_diversity(documents),
                'coverage_score': min(len(documents) / top_k, 1.0)
            }
            
            return RetrievalResult(
                path=path,
                documents=documents,
                retrieval_time=retrieval_time,
                query_used=query,
                confidence_score=confidence_score,
                quality_metrics=quality_metrics,
                metadata={'top_k': top_k, 'filters': filters, 'quality_threshold': quality_threshold}
            )
            
        except Exception as e:
            retrieval_time = time.time() - start_time
            logger.error(f"Retrieval failed for path {path}: {str(e)}")
            
            return RetrievalResult(
                path=path,
                documents=[],
                retrieval_time=retrieval_time,
                query_used=query,
                confidence_score=0.0,
                error=str(e)
            )
    
    def _calculate_diversity(self, documents: List[Dict[str, Any]]) -> float:
        """Calculate diversity score for documents"""
        if len(documents) < 2:
            return 1.0
        
        # Simple diversity based on content length variation
        lengths = [len(doc.get('content', '')) for doc in documents]
        if not lengths:
            return 0.0
        
        avg_length = sum(lengths) / len(lengths)
        variance = sum((l - avg_length) ** 2 for l in lengths) / len(lengths)
        
        # Normalize diversity score
        return min(variance / (avg_length + 1), 1.0)
    
    async def retrieve_optimized(self, 
                                query: str, 
                                final_top_k: int = 20,
                                time_budget: Optional[float] = None,
                                quality_threshold: float = 0.0) -> OptimizedFusionResult:
        """Main optimized retrieval with all enhancements"""
        start_time = time.time()
        
        # Step 1: Query Analysis and Routing
        query_analysis = None
        if self.query_router:
            query_analysis = self.query_router.analyze_query(query)
            logger.info(f"Query analysis: type={query_analysis.query_type}, "
                       f"complexity={query_analysis.complexity}, "
                       f"confidence={query_analysis.confidence:.3f}")
        
        # Step 2: Adaptive Weight Adjustment
        adaptive_weights = None
        if self.weight_adjuster and query_analysis:
            query_context = QueryContext(
                query_type=query_analysis.query_type,
                complexity=query_analysis.complexity,
                length=len(query.split()),
                has_entities=bool(query_analysis.key_entities),
                has_numbers=bool(re.search(r'\d+', query)),
                has_dates=bool(re.search(r'\b\d{4}\b|\b\d{1,2}/\d{1,2}/\d{2,4}\b', query)),
                semantic_density=query_analysis.semantic_density,
                keyword_density=query_analysis.keyword_density
            )
            
            base_weights = {
                path: self.config.paths[path].weight 
                for path in RetrievalPath 
                if path in self.config.paths and self.config.paths[path].enabled
            }
            
            adaptive_weights = self.weight_adjuster.adjust_weights(
                query, query_context, base_weights
            )
            
            logger.info(f"Adaptive weights: {adaptive_weights}")
        
        # Step 3: Progressive or Standard Retrieval
        if self.enable_progressive and self.progressive_retriever:
            # Use progressive retrieval
            progressive_result = await self.progressive_retriever.retrieve_progressive(
                query=query,
                final_top_k=final_top_k
            )
            
            documents = progressive_result.documents
            # Create empty path_results for progressive retrieval (different structure)
            path_results = {}
            progressive_stages = [progressive_result.stage_reached]
            
        else:
            # Use standard parallel retrieval
            result = await self._retrieve_parallel_standard(
                query=query,
                final_top_k=final_top_k,
                adaptive_weights=adaptive_weights,
                quality_threshold=quality_threshold
            )
            
            documents = result['documents']
            path_results = result['path_results']
            progressive_stages = None
        
        total_time = time.time() - start_time
        
        # Step 4: Performance Feedback
        if self.weight_adjuster and query_analysis:
            # Calculate performance metrics
            avg_relevance = sum(
                doc.get('fusion_score', 0) for doc in documents[:5]
            ) / min(len(documents), 5) if documents else 0.0
            
            performance_metrics = PerformanceMetrics(
                precision_at_k=avg_relevance,
                recall_at_k=min(len(documents) / final_top_k, 1.0),
                response_time=total_time,
                relevance_score=avg_relevance
            )
            
            # Create path performance mapping
            path_performance = {}
            for path in RetrievalPath:
                path_performance[path] = performance_metrics
            
            self.weight_adjuster.record_feedback(
                query_context, path_performance
            )
        
        # Update performance stats
        self._update_performance_stats(path_results, total_time, query_analysis)
        
        return OptimizedFusionResult(
            documents=documents,
            total_time=total_time,
            path_results=path_results,
            fusion_method=self.config.fusion.method,
            query_analysis=query_analysis,
            progressive_stages=progressive_stages,
            weight_adjustments=adaptive_weights,
            optimization_stats=self.performance_stats.copy(),
            config_used=self.config.to_dict()
        )
    
    async def _retrieve_parallel_standard(self, 
                                         query: str,
                                         final_top_k: int,
                                         adaptive_weights: Optional[Dict[RetrievalPath, float]] = None,
                                         quality_threshold: float = 0.0) -> Dict[str, Any]:
        """Standard parallel retrieval with adaptive weights"""
        # Get enabled paths
        enabled_paths = [path for path, config in self.config.paths.items() 
                        if config.enabled]
        
        if not enabled_paths:
            return {'documents': [], 'path_results': {}}
        
        # Execute parallel retrieval
        tasks = []
        for path in enabled_paths:
            path_config = self.config.paths[path]
            task = self.retrieve_single_path(
                path=path,
                query=query,
                top_k=path_config.top_k,
                quality_threshold=quality_threshold
            )
            tasks.append(task)
        
        path_results_list = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        valid_results = {}
        path_results = {}
        
        for result in path_results_list:
            if isinstance(result, RetrievalResult) and not result.error:
                valid_results[result.path] = result.documents
                path_results[result.path] = result
            elif isinstance(result, Exception):
                logger.error(f"Retrieval task failed: {str(result)}")
        
        # Apply small-to-big deduplication before fusion
        if valid_results:
            # Check if small-to-big retrieval is enabled
            from app.core.config import get_settings
            settings = get_settings()
            
            logger.info("应用小-大检索去重择优处理")
            valid_results = self.deduplicator.deduplicate_path_results(valid_results)
                
            # Log deduplication stats
            dedup_stats = self.deduplicator.get_deduplication_stats(
                {path.value: result.documents for path, result in path_results.items()},
                valid_results
            )
            logger.info(f"去重统计: {dedup_stats}")
            
            path_weights = adaptive_weights or {
                path: self.config.paths[path].weight 
                for path in valid_results.keys()
            }
            
            fused_documents = self.fusion_engine.fuse(
                method=self.config.fusion.method,
                path_results=valid_results,
                path_weights=path_weights,
                final_top_k=final_top_k * 2,
                k=self.config.fusion.rrf_k,
                normalize_scores=self.config.fusion.normalize_scores,
                diversity_penalty=self.config.fusion.diversity_penalty
            )
            
            # Apply reranking
            if self.reranker and fused_documents and self.config.rerank.enabled:
                try:
                    reranked_docs = await self.reranker.rerank_documents(
                        query=query,
                        documents=fused_documents[:self.config.rerank.top_k],
                        top_k=final_top_k
                    )
                    fused_documents = reranked_docs
                except Exception as e:
                    logger.error(f"Reranking failed: {str(e)}")
            
            documents = fused_documents[:final_top_k]
        else:
            documents = []
        
        return {
            'documents': documents,
            'path_results': path_results
        }
    
    def _update_performance_stats(self, 
                                 path_results: Dict[RetrievalPath, RetrievalResult], 
                                 total_time: float,
                                 query_analysis: Optional[QueryAnalysis]):
        """Update enhanced performance statistics"""
        self.performance_stats['total_queries'] += 1
        queries = self.performance_stats['total_queries']
        
        # Update average times
        self.performance_stats['avg_retrieval_time'] = (
            (self.performance_stats['avg_retrieval_time'] * (queries - 1) + total_time) / queries
        )
        
        # Update path success rates (skip if path_results is empty for progressive retrieval)
        if path_results:
            for path, result in path_results.items():
                if path in self.performance_stats['path_success_rates']:
                    current_rate = self.performance_stats['path_success_rates'][path]
                    success = 1.0 if not result.error else 0.0
                    self.performance_stats['path_success_rates'][path] = (
                        current_rate * 0.9 + success * 0.1
                    )
        
        # Update optimization stats
        if query_analysis:
            self.performance_stats['query_routing_accuracy'] = (
                self.performance_stats['query_routing_accuracy'] * 0.9 + 
                query_analysis.confidence * 0.1
            )
        
        if self.weight_adjuster:
            self.performance_stats['weight_adjustments'] += 1
    
    async def retrieve(self, 
                      query: str, 
                      top_k: int = 20,
                      config_override: Optional[AdvancedRAGConfig] = None) -> List[Dict[str, Any]]:
        """Simplified interface for backward compatibility - basic retrieval without progressive features"""
        if config_override:
            original_config = self.config
            self.update_config(config_override)
        
        try:
            # Basic multi-path retrieval without progressive features to avoid circular dependency
            all_documents = []
            
            # Vector retrieval
            if RetrievalPath.VECTOR in self.config.paths:
                vector_docs = await self.vector_retriever.retrieve(
                    query, top_k=min(top_k * 2, 100)
                )
                for doc in vector_docs:
                    doc['retrieval_path'] = RetrievalPath.VECTOR.value
                all_documents.extend(vector_docs)
            
            # BM25 retrieval (keywords, summary, content)
            bm25_paths = [RetrievalPath.KEYWORDS, RetrievalPath.SUMMARY, RetrievalPath.CONTENT]
            for path in bm25_paths:
                if path in self.config.paths and self.bm25_retriever:
                    bm25_docs = self.bm25_retriever.retrieve(
                        query, top_k=min(top_k * 2, 100)
                    )
                    for doc in bm25_docs:
                        doc['retrieval_path'] = path.value
                    all_documents.extend(bm25_docs)
                    break  # Only use one BM25 path to avoid duplicates
            
            # Simple fusion and ranking
            if len(all_documents) > top_k:
                # Simple score-based ranking
                all_documents.sort(key=lambda x: x.get('score', 0), reverse=True)
                all_documents = all_documents[:top_k]
            
            return all_documents
            
        finally:
            if config_override:
                self.update_config(original_config)
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get enhanced performance statistics"""
        stats = self.performance_stats.copy()
        
        # Add component-specific stats
        if self.reranker:
            stats['reranker_stats'] = self.reranker.get_performance_stats()
        
        if self.weight_adjuster:
            stats['weight_adjuster_stats'] = self.weight_adjuster.get_performance_stats()
        
        return stats
    
    def reset_performance_stats(self):
        """Reset all performance statistics"""
        self.performance_stats = {
            'total_queries': 0,
            'avg_retrieval_time': 0.0,
            'avg_fusion_time': 0.0,
            'path_success_rates': {path: 0.0 for path in RetrievalPath},
            'query_routing_accuracy': 0.0,
            'progressive_early_stops': 0,
            'weight_adjustments': 0,
            'cache_hit_rate': 0.0,
            'quality_improvements': 0.0
        }
        
        # Reset component stats
        if self.reranker:
            self.reranker.reset_performance_stats()
        
        if self.weight_adjuster:
            self.weight_adjuster.reset_learning()
    
    async def health_check(self) -> Dict[str, Any]:
        """Enhanced health check with optimization components"""
        health_status = {
            'overall': 'healthy',
            'components': {},
            'paths': {},
            'timestamp': time.time()
        }
        
        # Check retrieval paths
        test_query = "test query"
        for path in RetrievalPath:
            try:
                result = await self.retrieve_single_path(path, test_query, 1)
                health_status['paths'][path.value] = {
                    'status': 'healthy' if not result.error else 'error',
                    'error': result.error,
                    'response_time': result.retrieval_time,
                    'confidence': result.confidence_score
                }
                
                if result.error:
                    health_status['overall'] = 'degraded'
            except Exception as e:
                health_status['paths'][path.value] = {
                    'status': 'error',
                    'error': str(e),
                    'response_time': None
                }
                health_status['overall'] = 'degraded'
        
        # Check optimization components
        health_status['components']['query_router'] = 'enabled' if self.query_router else 'disabled'
        health_status['components']['progressive_retriever'] = 'enabled' if self.progressive_retriever else 'disabled'
        health_status['components']['weight_adjuster'] = 'enabled' if self.weight_adjuster else 'disabled'
        health_status['components']['reranker'] = 'enabled' if self.reranker else 'disabled'
        
        return health_status


# Factory function for easy initialization
async def create_advanced_fusion_retriever(
    vector_store: VectorStore,
    documents: Optional[List[Dict[str, Any]]] = None,
    config_name: str = 'balanced',
    enable_all_optimizations: bool = True
) -> AdvancedFusionRetriever:
    """Factory function to create optimized FusionRetriever
    
    Args:
        vector_store: Vector store instance
        documents: Document corpus for BM25 indexing
        config_name: Predefined config name
        enable_all_optimizations: Enable all optimization features
        
    Returns:
        Initialized AdvancedFusionRetriever
    """
    config = AdvancedRAGConfig.get_preset_config(config_name)
    
    retriever = AdvancedFusionRetriever(
        vector_store=vector_store,
        documents=documents,
        config=config,
        enable_query_routing=enable_all_optimizations,
        enable_progressive=enable_all_optimizations,
        enable_adaptive_weights=enable_all_optimizations
    )
    
    logger.info(f"Created AdvancedFusionRetriever with config '{config_name}' "
               f"and optimizations: {enable_all_optimizations}")
    return retriever


# Backward compatibility alias
FusionRetriever = AdvancedFusionRetriever
create_fusion_retriever = create_advanced_fusion_retriever