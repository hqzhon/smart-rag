"""Progressive Retrieval System

This module implements progressive retrieval that adapts retrieval depth
based on initial result quality, optimizing performance while maintaining accuracy.
"""

from typing import List, Dict, Any, Optional, Tuple
import asyncio
import time
from dataclasses import dataclass
from enum import Enum

from app.retrieval.advanced_config import RetrievalPath, AdvancedRAGConfig
from app.retrieval.query_router import QueryRouter, QueryAnalysis
from app.utils.logger import setup_logger

logger = setup_logger(__name__)


class RetrievalStage(Enum):
    """Progressive retrieval stages"""
    FAST = "fast"        # Quick initial retrieval
    STANDARD = "standard"  # Normal retrieval depth
    DEEP = "deep"        # Comprehensive retrieval
    EXHAUSTIVE = "exhaustive"  # Maximum depth retrieval


class QualityThreshold(Enum):
    """Quality assessment thresholds"""
    EXCELLENT = 0.8
    GOOD = 0.6
    ACCEPTABLE = 0.4
    POOR = 0.2


@dataclass
class StageConfig:
    """Configuration for each retrieval stage"""
    top_k_per_path: int
    enabled_paths: List[RetrievalPath]
    time_budget: float  # Maximum time in seconds
    quality_threshold: float
    max_total_docs: int


@dataclass
class ProgressiveResult:
    """Result from progressive retrieval"""
    documents: List[Dict[str, Any]]
    stage_reached: RetrievalStage
    total_time: float
    stage_results: Dict[RetrievalStage, Dict[str, Any]]
    quality_scores: Dict[RetrievalStage, float]
    early_stop_reason: Optional[str] = None
    paths_used: List[RetrievalPath] = None


class QualityAssessor:
    """Assess retrieval result quality"""
    
    def __init__(self):
        """Initialize quality assessor"""
        self.min_score_threshold = 0.1
        self.diversity_weight = 0.3
        self.relevance_weight = 0.7
    
    def assess_quality(self, 
                      query: str, 
                      documents: List[Dict[str, Any]], 
                      query_analysis: Optional[QueryAnalysis] = None) -> float:
        """Assess overall quality of retrieval results
        
        Args:
            query: Original query
            documents: Retrieved documents
            query_analysis: Optional query analysis for context
            
        Returns:
            Quality score between 0 and 1
        """
        if not documents:
            return 0.0
        
        # Calculate relevance score
        relevance_score = self._calculate_relevance_score(query, documents)
        
        # Calculate diversity score
        diversity_score = self._calculate_diversity_score(documents)
        
        # Calculate coverage score
        coverage_score = self._calculate_coverage_score(query, documents, query_analysis)
        
        # Weighted combination
        quality_score = (
            relevance_score * self.relevance_weight +
            diversity_score * self.diversity_weight * 0.5 +
            coverage_score * self.diversity_weight * 0.5
        )
        
        return min(quality_score, 1.0)
    
    def _calculate_relevance_score(self, query: str, documents: List[Dict[str, Any]]) -> float:
        """Calculate average relevance score"""
        if not documents:
            return 0.0
        
        scores = []
        for doc in documents:
            # Use various score fields
            score = (
                doc.get('fusion_score', 0.0) * 0.4 +
                doc.get('similarity_score', 0.0) * 0.3 +
                doc.get('bm25_score', 0.0) * 0.2 +
                doc.get('rerank_score', 0.0) * 0.1
            )
            scores.append(score)
        
        if not scores:
            return 0.0
        
        # Weight by position (higher weight for top results)
        weighted_scores = []
        for i, score in enumerate(scores):
            position_weight = 1.0 / (i + 1)  # 1, 0.5, 0.33, ...
            weighted_scores.append(score * position_weight)
        
        return sum(weighted_scores) / sum(1.0 / (i + 1) for i in range(len(scores)))
    
    def _calculate_diversity_score(self, documents: List[Dict[str, Any]]) -> float:
        """Calculate content diversity score"""
        if not documents or len(documents) <= 1:
            return 1.0 if documents else 0.0
        
        # Simple diversity based on content length variation
        content_lengths = []
        for doc in documents:
            if doc and isinstance(doc, dict):
                content = doc.get('content', '')
                content_lengths.append(len(content) if content else 0)
        
        if not content_lengths:
            return 0.0
        
        avg_length = sum(content_lengths) / len(content_lengths)
        if avg_length == 0:
            return 0.0
        
        # Calculate coefficient of variation
        variance = sum((length - avg_length) ** 2 for length in content_lengths) / len(content_lengths)
        std_dev = variance ** 0.5
        cv = std_dev / avg_length if avg_length > 0 else 0
        
        # Normalize to 0-1 range (higher variation = higher diversity)
        diversity_score = min(cv, 1.0)
        
        return diversity_score
    
    def _calculate_coverage_score(self, 
                                 query: str, 
                                 documents: List[Dict[str, Any]], 
                                 query_analysis: Optional[QueryAnalysis]) -> float:
        """Calculate query coverage score"""
        if not documents or not query_analysis:
            return 0.5  # Default moderate score
        
        # Check if key entities are covered
        entity_coverage = 0.0
        if query_analysis.key_entities:
            covered_entities = 0
            for entity in query_analysis.key_entities:
                logger.debug(f"Processing entity: {entity}, type: {type(entity)}")
                if entity and isinstance(entity, str):
                    entity_lower = entity.lower()
                    for doc in documents:
                        content = doc.get('content', '') or ''
                        content = content.lower()
                        if entity_lower in content:
                            covered_entities += 1
                            break
                else:
                    logger.warning(f"Invalid entity found: {entity} (type: {type(entity)})")
            entity_coverage = covered_entities / len(query_analysis.key_entities)
        
        # Check if keywords are covered
        keyword_coverage = 0.0
        if query_analysis.keywords:
            covered_keywords = 0
            for keyword in query_analysis.keywords:
                logger.debug(f"Processing keyword: {keyword}, type: {type(keyword)}")
                if keyword and isinstance(keyword, str):
                    keyword_lower = keyword.lower()
                    for doc in documents:
                        content = doc.get('content', '') or ''
                        content = content.lower()
                        if keyword_lower in content:
                            covered_keywords += 1
                            break
                else:
                    logger.warning(f"Invalid keyword found: {keyword} (type: {type(keyword)})")
            keyword_coverage = covered_keywords / len(query_analysis.keywords)
        
        # Combine coverage scores
        coverage_score = (entity_coverage + keyword_coverage) / 2
        return coverage_score


class ProgressiveRetriever:
    """Progressive retrieval system that adapts depth based on result quality"""
    
    def __init__(self, base_retriever, config: Optional[AdvancedRAGConfig] = None):
        """Initialize progressive retriever
        
        Args:
            base_retriever: Base retriever (FusionRetriever)
            config: Advanced RAG configuration
        """
        self.base_retriever = base_retriever
        self.config = config or AdvancedRAGConfig()
        self.query_router = QueryRouter()
        self.quality_assessor = QualityAssessor()
        
        # Define stage configurations
        self.stage_configs = {
            RetrievalStage.FAST: StageConfig(
                top_k_per_path=5,
                enabled_paths=[RetrievalPath.VECTOR, RetrievalPath.KEYWORDS],
                time_budget=10.0,  # 增加时间预算从1.0秒到10.0秒
                quality_threshold=QualityThreshold.GOOD.value,
                max_total_docs=10
            ),
            RetrievalStage.STANDARD: StageConfig(
                top_k_per_path=10,
                enabled_paths=[RetrievalPath.VECTOR, RetrievalPath.KEYWORDS, RetrievalPath.SUMMARY],
                time_budget=15.0,  # 增加时间预算从3.0秒到15.0秒
                quality_threshold=QualityThreshold.ACCEPTABLE.value,
                max_total_docs=20
            ),
            RetrievalStage.DEEP: StageConfig(
                top_k_per_path=15,
                enabled_paths=list(RetrievalPath),
                time_budget=25.0,  # 增加时间预算从8.0秒到25.0秒
                quality_threshold=QualityThreshold.POOR.value,
                max_total_docs=40
            ),
            RetrievalStage.EXHAUSTIVE: StageConfig(
                top_k_per_path=25,
                enabled_paths=list(RetrievalPath),
                time_budget=40.0,  # 增加时间预算从20.0秒到40.0秒
                quality_threshold=0.0,
                max_total_docs=80
            )
        }
        
        logger.info("ProgressiveRetriever initialized")
    
    async def retrieve_progressive(self, 
                                  query: str, 
                                  final_top_k: int = 20,
                                  max_stage: RetrievalStage = RetrievalStage.DEEP,
                                  force_stages: Optional[List[RetrievalStage]] = None) -> ProgressiveResult:
        """Perform progressive retrieval with quality-based early stopping
        
        Args:
            query: Search query
            final_top_k: Final number of results to return
            max_stage: Maximum stage to reach
            force_stages: Force execution of specific stages (for testing)
            
        Returns:
            ProgressiveResult with final documents and metadata
        """
        start_time = time.time()
        
        # Analyze query to determine starting strategy
        query_analysis = self.query_router.analyze_query(query)
        
        # Determine stage sequence
        if force_stages:
            stages = force_stages
        else:
            stages = self._determine_stage_sequence(query_analysis, max_stage)
        
        stage_results = {}
        quality_scores = {}
        best_documents = []
        best_quality = 0.0
        stage_reached = stages[0]
        early_stop_reason = None
        paths_used = []
        
        for stage in stages:
            stage_start = time.time()
            stage_config = self.stage_configs[stage]
            
            logger.info(f"Starting retrieval stage: {stage.value}")
            
            try:
                # Update configuration for this stage
                stage_documents = await self._retrieve_stage(
                    query, stage_config, query_analysis
                )
                
                # Ensure stage_documents is not None
                if stage_documents is None:
                    stage_documents = []
                    logger.warning(f"Stage {stage.value} returned None, using empty list")
                
                stage_time = time.time() - stage_start
                
                # Assess quality
                quality_score = self.quality_assessor.assess_quality(
                    query, stage_documents, query_analysis
                )
                
                # Store stage results
                stage_results[stage] = {
                    'documents': stage_documents,
                    'time': stage_time,
                    'doc_count': len(stage_documents)
                }
                quality_scores[stage] = quality_score
                stage_reached = stage
                paths_used = stage_config.enabled_paths
                
                logger.info(f"Stage {stage.value}: {len(stage_documents)} docs, "
                          f"quality={quality_score:.3f}, time={stage_time:.2f}s")
                
                # Update best results if quality improved
                if quality_score > best_quality:
                    best_documents = stage_documents[:final_top_k]
                    best_quality = quality_score
                
                # Check early stopping conditions
                should_stop, stop_reason = self._should_stop_early(
                    stage, quality_score, stage_time, start_time
                )
                
                if should_stop:
                    early_stop_reason = stop_reason
                    logger.info(f"Early stopping: {stop_reason}")
                    break
                
                # Check time budget
                total_time = time.time() - start_time
                if total_time > stage_config.time_budget * 2:  # Allow some buffer
                    early_stop_reason = "Time budget exceeded"
                    logger.info(f"Stopping due to time budget: {total_time:.2f}s")
                    break
                    
            except Exception as e:
                logger.error(f"Stage {stage.value} failed: {str(e)}")
                stage_results[stage] = {
                    'documents': [],
                    'time': time.time() - stage_start,
                    'error': str(e)
                }
                quality_scores[stage] = 0.0
                break
        
        total_time = time.time() - start_time
        
        return ProgressiveResult(
            documents=best_documents,
            stage_reached=stage_reached,
            total_time=total_time,
            stage_results=stage_results,
            quality_scores=quality_scores,
            early_stop_reason=early_stop_reason,
            paths_used=paths_used
        )
    
    def _determine_stage_sequence(self, 
                                 query_analysis: QueryAnalysis, 
                                 max_stage: RetrievalStage) -> List[RetrievalStage]:
        """Determine optimal stage sequence based on query analysis"""
        all_stages = [RetrievalStage.FAST, RetrievalStage.STANDARD, 
                     RetrievalStage.DEEP, RetrievalStage.EXHAUSTIVE]
        
        # Find max stage index
        max_index = all_stages.index(max_stage)
        
        # Determine starting stage based on query complexity
        if query_analysis.complexity.value == "simple" and query_analysis.confidence > 0.7:
            start_index = 0  # Start with FAST
        elif query_analysis.complexity.value == "complex" or query_analysis.confidence < 0.5:
            start_index = 1  # Start with STANDARD
        else:
            start_index = 0  # Default to FAST
        
        return all_stages[start_index:max_index + 1]
    
    async def _retrieve_stage(self, 
                             query: str, 
                             stage_config: StageConfig, 
                             query_analysis: QueryAnalysis) -> List[Dict[str, Any]]:
        """Execute retrieval for a specific stage"""
        # Temporarily update base retriever configuration
        original_config = self.base_retriever.config
        
        # Create stage-specific config
        stage_rag_config = AdvancedRAGConfig(
            paths={
                path: original_config.paths[path] 
                for path in stage_config.enabled_paths
                if path in original_config.paths
            },
            fusion=original_config.fusion,
            rerank=original_config.rerank,
            performance=original_config.performance
        )
        
        # Update path weights based on query analysis
        adaptive_weights = self.query_router.get_adaptive_weights(
            query, 
            {path: config.weight for path, config in stage_rag_config.paths.items()}
        )
        
        for path, weight in adaptive_weights.items():
            if path in stage_rag_config.paths:
                stage_rag_config.paths[path].weight = weight
        
        # Temporarily update retriever config
        self.base_retriever.update_config(stage_rag_config)
        
        try:
            # Perform retrieval using basic retrieve method to avoid circular dependency
            documents = await self.base_retriever.retrieve(
                query=query,
                top_k=stage_config.max_total_docs
            )
            
            # Ensure we always return a list
            if documents is None:
                logger.warning(f"Base retriever returned None for query: {query}")
                return []
            
            return documents
            
        finally:
            # Restore original configuration
            self.base_retriever.update_config(original_config)
    
    def _should_stop_early(self, 
                          stage: RetrievalStage, 
                          quality_score: float, 
                          stage_time: float, 
                          total_start_time: float) -> Tuple[bool, Optional[str]]:
        """Determine if retrieval should stop early"""
        stage_config = self.stage_configs[stage]
        
        # Check quality threshold
        if quality_score >= stage_config.quality_threshold:
            return True, f"Quality threshold met: {quality_score:.3f} >= {stage_config.quality_threshold}"
        
        # Check if we've reached excellent quality
        if quality_score >= QualityThreshold.EXCELLENT.value:
            return True, f"Excellent quality achieved: {quality_score:.3f}"
        
        # Check stage time budget
        if stage_time > stage_config.time_budget:
            return True, f"Stage time budget exceeded: {stage_time:.2f}s > {stage_config.time_budget}s"
        
        # Check total time budget (conservative)
        total_time = time.time() - total_start_time
        if total_time > 15.0:  # Hard limit
            return True, f"Total time limit reached: {total_time:.2f}s"
        
        return False, None
    
    def get_stage_stats(self) -> Dict[str, Any]:
        """Get statistics about stage configurations"""
        return {
            'stage_configs': {
                stage.value: {
                    'top_k_per_path': config.top_k_per_path,
                    'enabled_paths': [path.value for path in config.enabled_paths],
                    'time_budget': config.time_budget,
                    'quality_threshold': config.quality_threshold,
                    'max_total_docs': config.max_total_docs
                }
                for stage, config in self.stage_configs.items()
            }
        }
    
    def update_stage_config(self, stage: RetrievalStage, **kwargs):
        """Update configuration for a specific stage"""
        if stage in self.stage_configs:
            config = self.stage_configs[stage]
            for key, value in kwargs.items():
                if hasattr(config, key):
                    setattr(config, key, value)
            logger.info(f"Updated {stage.value} stage configuration")
        else:
            logger.warning(f"Stage {stage.value} not found")