"""Integrated Multi-Path RAG Retriever

This module provides a unified interface that integrates all multi-path retrieval
components including fusion retrieval, enhanced reranking, and monitoring.
"""

from typing import Dict, Any, List, Optional, Union, Tuple
import asyncio
import time
from dataclasses import dataclass
from pathlib import Path

from app.retrieval.fusion_retriever import FusionRetriever, create_fusion_retriever
from app.retrieval.enhanced_reranker import EnhancedReranker, RerankStrategy, create_enhanced_reranker
from app.retrieval.advanced_config import AdvancedRAGConfig, FusionMethod
from app.retrieval.monitoring import (
    get_monitor, monitor_operation, RetrievalError,
    VectorRetrievalError, FusionError, RerankError
)
from app.utils.logger import setup_logger

logger = setup_logger(__name__)


@dataclass
class RetrievalRequest:
    """Retrieval request parameters"""
    query: str
    top_k: int = 20
    rerank_top_k: Optional[int] = None
    enable_rerank: bool = True
    fusion_method_override: Optional[FusionMethod] = None
    rerank_strategy_override: Optional[RerankStrategy] = None
    filters: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class RetrievalResponse:
    """Comprehensive retrieval response"""
    documents: List[Dict[str, Any]]
    query: str
    total_time: float
    fusion_time: float
    rerank_time: float
    fusion_method: FusionMethod
    rerank_strategy: Optional[RerankStrategy]
    paths_used: List[str]
    performance_metrics: Dict[str, Any]
    cache_hits: Dict[str, bool]
    error: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class IntegratedRetriever:
    """Integrated multi-path RAG retriever with monitoring and optimization"""
    
    def __init__(self,
                 config: Optional[AdvancedRAGConfig] = None,
                 vector_store=None,
                 documents: Optional[List[Dict[str, Any]]] = None,
                 enable_monitoring: bool = True,
                 enable_reranking: bool = True,
                 rerank_strategy: RerankStrategy = RerankStrategy.QIANWEN_API):
        """
        Initialize integrated retriever
        
        Args:
            config: Advanced RAG configuration
            vector_store: Vector store instance
            documents: Document collection for BM25 indexing
            enable_monitoring: Whether to enable monitoring
            enable_reranking: Whether to enable reranking
            rerank_strategy: Default reranking strategy
        """
        self.config = config or AdvancedRAGConfig.create_balanced_config()
        self.enable_monitoring = enable_monitoring
        self.enable_reranking = enable_reranking
        
        # Initialize monitoring
        if enable_monitoring:
            self.monitor = get_monitor()
            self._setup_monitoring()
        else:
            self.monitor = None
        
        # Initialize fusion retriever
        self.fusion_retriever = create_fusion_retriever(
            config=self.config,
            vector_store=vector_store,
            documents=documents
        )
        
        # Initialize enhanced reranker
        if enable_reranking:
            self.reranker = create_enhanced_reranker(
                strategy=rerank_strategy.value,
                enable_cache=True
            )
        else:
            self.reranker = None
        
        # Performance tracking
        self.stats = {
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'avg_response_time': 0.0,
            'cache_hit_rate': 0.0
        }
        
        logger.info("IntegratedRetriever initialized successfully")
    
    def _setup_monitoring(self):
        """Setup monitoring and health checks"""
        # Register health checks
        self.monitor.health_monitor.register_health_check(
            'fusion_retriever', self._check_fusion_health
        )
        
        if self.reranker:
            self.monitor.health_monitor.register_health_check(
                'reranker', self._check_reranker_health
            )
        
        # Create circuit breakers
        self.fusion_circuit_breaker = self.monitor.create_circuit_breaker(
            'fusion_retrieval',
            failure_threshold=3,
            recovery_timeout=30.0
        )
        
        if self.reranker:
            self.rerank_circuit_breaker = self.monitor.create_circuit_breaker(
                'reranking',
                failure_threshold=5,
                recovery_timeout=60.0
            )
    
    async def _check_fusion_health(self) -> Dict[str, Any]:
        """Health check for fusion retriever"""
        try:
            # Simple health check with a test query
            start_time = time.time()
            await self.fusion_retriever.retrieve(
                query="test",
                paths=['vector'],  # Use only vector path for health check
                top_k=1
            )
            response_time = (time.time() - start_time) * 1000
            
            return {
                'status': 'healthy',
                'message': 'Fusion retriever is operational',
                'metrics': {
                    'response_time_ms': response_time
                }
            }
        except Exception as e:
            return {
                'status': 'unhealthy',
                'message': f'Fusion retriever failed: {str(e)}'
            }
    
    async def _check_reranker_health(self) -> Dict[str, Any]:
        """Health check for reranker"""
        if not self.reranker:
            return {
                'status': 'healthy',
                'message': 'Reranker is disabled'
            }
        
        try:
            # Test reranker with dummy documents
            test_docs = [
                {'content': 'test document 1', 'score': 0.8},
                {'content': 'test document 2', 'score': 0.6}
            ]
            
            start_time = time.time()
            result = await self.reranker.rerank_documents(
                query="test",
                documents=test_docs,
                top_k=2
            )
            response_time = (time.time() - start_time) * 1000
            
            return {
                'status': 'healthy',
                'message': 'Reranker is operational',
                'metrics': {
                    'response_time_ms': response_time,
                    'api_calls': result.api_calls
                }
            }
        except Exception as e:
            return {
                'status': 'unhealthy',
                'message': f'Reranker failed: {str(e)}'
            }
    
    @monitor_operation("integrated_retrieval", "integrated_retriever")
    async def retrieve(self, request: Union[RetrievalRequest, str]) -> RetrievalResponse:
        """
        Perform integrated multi-path retrieval
        
        Args:
            request: Retrieval request or query string
            
        Returns:
            Comprehensive retrieval response
        """
        # Normalize request
        if isinstance(request, str):
            request = RetrievalRequest(query=request)
        
        start_time = time.time()
        
        try:
            # Update stats
            self.stats['total_requests'] += 1
            
            # Perform fusion retrieval
            fusion_result = await self._perform_fusion_retrieval(request)
            
            # Perform reranking if enabled
            rerank_result = None
            if self.enable_reranking and self.reranker and request.enable_rerank:
                rerank_result = await self._perform_reranking(request, fusion_result)
            
            # Prepare response
            final_documents = (
                rerank_result.documents if rerank_result 
                else fusion_result.documents
            )
            
            total_time = time.time() - start_time
            
            response = RetrievalResponse(
                documents=final_documents,
                query=request.query,
                total_time=total_time,
                fusion_time=fusion_result.retrieval_time,
                rerank_time=rerank_result.rerank_time if rerank_result else 0.0,
                fusion_method=fusion_result.fusion_method,
                rerank_strategy=rerank_result.strategy_used if rerank_result else None,
                paths_used=fusion_result.paths_used,
                performance_metrics=self._collect_performance_metrics(fusion_result, rerank_result),
                cache_hits={
                    'fusion': getattr(fusion_result, 'cache_hit', False),
                    'rerank': rerank_result.cache_hit if rerank_result else False
                },
                metadata=request.metadata
            )
            
            # Update success stats
            self.stats['successful_requests'] += 1
            self._update_avg_response_time(total_time)
            
            return response
            
        except Exception as e:
            self.stats['failed_requests'] += 1
            
            error_msg = f"Integrated retrieval failed: {str(e)}"
            logger.error(error_msg, exc_info=True)
            
            # Return error response
            return RetrievalResponse(
                documents=[],
                query=request.query,
                total_time=time.time() - start_time,
                fusion_time=0.0,
                rerank_time=0.0,
                fusion_method=self.config.fusion.method,
                rerank_strategy=None,
                paths_used=[],
                performance_metrics={},
                cache_hits={'fusion': False, 'rerank': False},
                error=error_msg,
                metadata=request.metadata
            )
    
    async def _perform_fusion_retrieval(self, request: RetrievalRequest):
        """Perform fusion retrieval with circuit breaker protection"""
        if self.monitor and self.fusion_circuit_breaker:
            return await self.fusion_circuit_breaker.call(
                self._fusion_retrieval_impl, request
            )
        else:
            return await self._fusion_retrieval_impl(request)
    
    async def _fusion_retrieval_impl(self, request: RetrievalRequest):
        """Implementation of fusion retrieval"""
        # Apply configuration overrides
        if request.fusion_method_override:
            original_method = self.config.fusion.method
            self.config.fusion.method = request.fusion_method_override
            
            try:
                result = await self.fusion_retriever.retrieve_and_fuse(
                    query=request.query,
                    top_k=request.top_k,
                    filters=request.filters
                )
            finally:
                self.config.fusion.method = original_method
        else:
            result = await self.fusion_retriever.retrieve_and_fuse(
                query=request.query,
                top_k=request.top_k,
                filters=request.filters
            )
        
        return result
    
    async def _perform_reranking(self, request: RetrievalRequest, fusion_result):
        """Perform reranking with circuit breaker protection"""
        if self.monitor and self.rerank_circuit_breaker:
            return await self.rerank_circuit_breaker.call(
                self._reranking_impl, request, fusion_result
            )
        else:
            return await self._reranking_impl(request, fusion_result)
    
    async def _reranking_impl(self, request: RetrievalRequest, fusion_result):
        """Implementation of reranking"""
        rerank_top_k = request.rerank_top_k or min(request.top_k, len(fusion_result.documents))
        
        return await self.reranker.rerank_documents(
            query=request.query,
            documents=fusion_result.documents,
            top_k=rerank_top_k,
            strategy_override=request.rerank_strategy_override
        )
    
    def _collect_performance_metrics(self, fusion_result, rerank_result) -> Dict[str, Any]:
        """Collect performance metrics from retrieval results"""
        metrics = {
            'fusion_metrics': fusion_result.performance_stats if hasattr(fusion_result, 'performance_stats') else {},
            'documents_retrieved': len(fusion_result.documents),
            'paths_executed': len(fusion_result.paths_used)
        }
        
        if rerank_result:
            metrics['rerank_metrics'] = {
                'api_calls': rerank_result.api_calls,
                'cache_hit': rerank_result.cache_hit,
                'strategy_used': rerank_result.strategy_used.value
            }
        
        return metrics
    
    def _update_avg_response_time(self, response_time: float):
        """Update average response time"""
        total_requests = self.stats['successful_requests']
        if total_requests == 1:
            self.stats['avg_response_time'] = response_time
        else:
            self.stats['avg_response_time'] = (
                (self.stats['avg_response_time'] * (total_requests - 1) + response_time) / total_requests
            )
    
    async def batch_retrieve(self, requests: List[Union[RetrievalRequest, str]]) -> List[RetrievalResponse]:
        """Perform batch retrieval with concurrency control"""
        max_concurrent = self.config.performance.max_concurrent_requests
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def process_request(req):
            async with semaphore:
                return await self.retrieve(req)
        
        return await asyncio.gather(
            *[process_request(req) for req in requests],
            return_exceptions=True
        )
    
    def update_config(self, config: AdvancedRAGConfig):
        """Update configuration"""
        self.config = config
        self.fusion_retriever.update_config(config)
        logger.info("Configuration updated successfully")
    
    def update_documents(self, documents: List[Dict[str, Any]]):
        """Update document collection"""
        self.fusion_retriever.update_documents(documents)
        logger.info(f"Updated document collection with {len(documents)} documents")
    
    async def get_health_status(self) -> Dict[str, Any]:
        """Get comprehensive health status"""
        if not self.monitor:
            return {'status': 'monitoring_disabled'}
        
        health_checks = await self.monitor.run_health_checks()
        system_status = self.monitor.health_monitor.get_system_status()
        
        return {
            'system_status': system_status,
            'component_health': health_checks,
            'performance_stats': self.get_stats(),
            'circuit_breakers': {
                name: cb.get_state() 
                for name, cb in self.monitor.circuit_breakers.items()
            }
        }
    
    def get_stats(self) -> Dict[str, Any]:
        """Get retrieval statistics"""
        stats = self.stats.copy()
        
        # Add component stats
        if hasattr(self.fusion_retriever, 'get_stats'):
            stats['fusion_stats'] = self.fusion_retriever.get_stats()
        
        if self.reranker:
            stats['rerank_stats'] = self.reranker.get_stats()
        
        # Calculate derived metrics
        if stats['total_requests'] > 0:
            stats['success_rate'] = stats['successful_requests'] / stats['total_requests']
            stats['error_rate'] = stats['failed_requests'] / stats['total_requests']
        else:
            stats['success_rate'] = 0.0
            stats['error_rate'] = 0.0
        
        return stats
    
    def reset_stats(self):
        """Reset all statistics"""
        self.stats = {
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'avg_response_time': 0.0,
            'cache_hit_rate': 0.0
        }
        
        if hasattr(self.fusion_retriever, 'reset_stats'):
            self.fusion_retriever.reset_stats()
        
        if self.reranker:
            self.reranker.reset_stats()
        
        logger.info("Statistics reset successfully")
    
    async def optimize_performance(self, 
                                  test_queries: List[str],
                                  target_latency: float = 1000.0) -> Dict[str, Any]:
        """Automatic performance optimization"""
        logger.info("Starting performance optimization...")
        
        optimization_results = {
            'original_config': self.config.to_dict(),
            'test_results': [],
            'optimized_config': None,
            'improvement': {}
        }
        
        # Test current configuration
        baseline_metrics = await self._benchmark_queries(test_queries)
        optimization_results['baseline_metrics'] = baseline_metrics
        
        # Try different configurations
        configs_to_test = [
            AdvancedRAGConfig.create_fast_config(),
            AdvancedRAGConfig.create_high_precision_config(),
            AdvancedRAGConfig.create_keyword_focused_config()
        ]
        
        best_config = self.config
        best_score = self._calculate_performance_score(baseline_metrics, target_latency)
        
        for test_config in configs_to_test:
            try:
                # Update config temporarily
                original_config = self.config
                self.update_config(test_config)
                
                # Test performance
                test_metrics = await self._benchmark_queries(test_queries)
                test_score = self._calculate_performance_score(test_metrics, target_latency)
                
                optimization_results['test_results'].append({
                    'config': test_config.to_dict(),
                    'metrics': test_metrics,
                    'score': test_score
                })
                
                if test_score > best_score:
                    best_config = test_config
                    best_score = test_score
                
                # Restore original config
                self.update_config(original_config)
                
            except Exception as e:
                logger.error(f"Error testing config: {str(e)}")
        
        # Apply best configuration
        if best_config != self.config:
            self.update_config(best_config)
            optimization_results['optimized_config'] = best_config.to_dict()
            
            # Calculate improvement
            final_metrics = await self._benchmark_queries(test_queries)
            optimization_results['final_metrics'] = final_metrics
            optimization_results['improvement'] = {
                'latency_improvement': (
                    (baseline_metrics['avg_latency'] - final_metrics['avg_latency']) / 
                    baseline_metrics['avg_latency'] * 100
                ),
                'score_improvement': (best_score - self._calculate_performance_score(baseline_metrics, target_latency))
            }
        
        logger.info("Performance optimization completed")
        return optimization_results
    
    async def _benchmark_queries(self, queries: List[str]) -> Dict[str, float]:
        """Benchmark performance with test queries"""
        latencies = []
        success_count = 0
        
        for query in queries:
            try:
                start_time = time.time()
                response = await self.retrieve(RetrievalRequest(query=query, top_k=10))
                latency = (time.time() - start_time) * 1000  # ms
                
                if not response.error:
                    latencies.append(latency)
                    success_count += 1
                    
            except Exception as e:
                logger.error(f"Benchmark query failed: {str(e)}")
        
        if not latencies:
            return {'avg_latency': float('inf'), 'success_rate': 0.0}
        
        return {
            'avg_latency': sum(latencies) / len(latencies),
            'p95_latency': sorted(latencies)[int(len(latencies) * 0.95)],
            'success_rate': success_count / len(queries)
        }
    
    def _calculate_performance_score(self, metrics: Dict[str, float], target_latency: float) -> float:
        """Calculate performance score for optimization"""
        if metrics['avg_latency'] == float('inf'):
            return 0.0
        
        # Score based on latency and success rate
        latency_score = max(0, (target_latency - metrics['avg_latency']) / target_latency)
        success_score = metrics['success_rate']
        
        return (latency_score * 0.6 + success_score * 0.4) * 100


# Factory function
def create_integrated_retriever(
    config_path: Optional[str] = None,
    config: Optional[AdvancedRAGConfig] = None,
    **kwargs
) -> IntegratedRetriever:
    """Factory function to create IntegratedRetriever
    
    Args:
        config_path: Path to configuration file
        config: Configuration object
        **kwargs: Additional parameters
        
    Returns:
        IntegratedRetriever instance
    """
    if config_path:
        config = AdvancedRAGConfig.from_file(config_path)
    elif config is None:
        config = AdvancedRAGConfig.create_balanced_config()
    
    return IntegratedRetriever(config=config, **kwargs)