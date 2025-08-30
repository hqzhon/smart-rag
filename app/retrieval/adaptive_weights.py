"""Adaptive Weight Adjustment System

This module implements dynamic weight adjustment for multi-path retrieval
based on query characteristics and historical performance.
"""

from typing import Dict, List, Any, Optional, Tuple
import json
import time
import math
from dataclasses import dataclass, asdict
from collections import defaultdict, deque
from enum import Enum

from app.retrieval.advanced_config import RetrievalPath
from app.retrieval.query_router import QueryType, QueryComplexity
from app.utils.logger import setup_logger

logger = setup_logger(__name__)


class AdaptationStrategy(Enum):
    """Weight adaptation strategies"""
    PERFORMANCE_BASED = "performance_based"  # Based on historical performance
    QUERY_AWARE = "query_aware"  # Based on query characteristics
    HYBRID = "hybrid"  # Combination of both
    REINFORCEMENT = "reinforcement"  # Reinforcement learning approach


@dataclass
class PerformanceMetrics:
    """Performance metrics for a retrieval path"""
    precision_at_k: float = 0.0
    recall_at_k: float = 0.0
    response_time: float = 0.0
    success_rate: float = 0.0
    user_satisfaction: float = 0.0
    relevance_score: float = 0.0
    diversity_score: float = 0.0
    
    def overall_score(self) -> float:
        """Calculate overall performance score"""
        return (
            self.precision_at_k * 0.25 +
            self.recall_at_k * 0.20 +
            (1.0 - min(self.response_time / 5.0, 1.0)) * 0.15 +  # Penalize slow responses
            self.success_rate * 0.15 +
            self.user_satisfaction * 0.10 +
            self.relevance_score * 0.10 +
            self.diversity_score * 0.05
        )


@dataclass
class QueryContext:
    """Context information for a query"""
    query_type: QueryType
    complexity: QueryComplexity
    length: int
    has_entities: bool
    has_numbers: bool
    has_dates: bool
    semantic_density: float
    keyword_density: float
    domain: Optional[str] = None
    language: str = "zh"


@dataclass
class WeightAdjustment:
    """Weight adjustment record"""
    timestamp: float
    query_context: QueryContext
    original_weights: Dict[RetrievalPath, float]
    adjusted_weights: Dict[RetrievalPath, float]
    performance_feedback: Optional[Dict[RetrievalPath, PerformanceMetrics]] = None
    strategy_used: AdaptationStrategy = AdaptationStrategy.HYBRID
    confidence: float = 0.5


class PerformanceTracker:
    """Track performance metrics for each retrieval path"""
    
    def __init__(self, window_size: int = 100):
        """Initialize performance tracker
        
        Args:
            window_size: Size of sliding window for metrics
        """
        self.window_size = window_size
        self.metrics_history: Dict[RetrievalPath, deque] = defaultdict(
            lambda: deque(maxlen=window_size)
        )
        self.query_context_history: deque = deque(maxlen=window_size)
        self.adjustment_history: deque = deque(maxlen=window_size)
        
    def record_performance(self, 
                          path: RetrievalPath, 
                          metrics: PerformanceMetrics,
                          query_context: QueryContext):
        """Record performance metrics for a path"""
        self.metrics_history[path].append({
            'timestamp': time.time(),
            'metrics': metrics,
            'query_context': query_context
        })
        
    def get_average_performance(self, 
                               path: RetrievalPath, 
                               query_filter: Optional[QueryContext] = None) -> PerformanceMetrics:
        """Get average performance for a path, optionally filtered by query context"""
        history = self.metrics_history[path]
        if not history:
            return PerformanceMetrics()
        
        # Filter by query context if provided
        filtered_records = []
        if query_filter:
            for record in history:
                if self._context_matches(record['query_context'], query_filter):
                    filtered_records.append(record)
        else:
            filtered_records = list(history)
        
        if not filtered_records:
            return PerformanceMetrics()
        
        # Calculate averages
        metrics_list = [record['metrics'] for record in filtered_records]
        avg_metrics = PerformanceMetrics(
            precision_at_k=sum(m.precision_at_k for m in metrics_list) / len(metrics_list),
            recall_at_k=sum(m.recall_at_k for m in metrics_list) / len(metrics_list),
            response_time=sum(m.response_time for m in metrics_list) / len(metrics_list),
            success_rate=sum(m.success_rate for m in metrics_list) / len(metrics_list),
            user_satisfaction=sum(m.user_satisfaction for m in metrics_list) / len(metrics_list),
            relevance_score=sum(m.relevance_score for m in metrics_list) / len(metrics_list),
            diversity_score=sum(m.diversity_score for m in metrics_list) / len(metrics_list)
        )
        
        return avg_metrics
    
    def _context_matches(self, context1: QueryContext, context2: QueryContext) -> bool:
        """Check if two query contexts are similar enough"""
        # Simple matching based on key attributes
        return (
            context1.query_type == context2.query_type and
            context1.complexity == context2.complexity and
            abs(context1.semantic_density - context2.semantic_density) < 0.3
        )
    
    def get_path_rankings(self, query_context: Optional[QueryContext] = None) -> List[Tuple[RetrievalPath, float]]:
        """Get paths ranked by performance"""
        path_scores = []
        
        for path in RetrievalPath:
            avg_metrics = self.get_average_performance(path, query_context)
            score = avg_metrics.overall_score()
            path_scores.append((path, score))
        
        # Sort by score descending
        path_scores.sort(key=lambda x: x[1], reverse=True)
        return path_scores


class AdaptiveWeightAdjuster:
    """Adaptive weight adjustment system"""
    
    def __init__(self, 
                 strategy: AdaptationStrategy = AdaptationStrategy.HYBRID,
                 learning_rate: float = 0.1,
                 min_weight: float = 0.05,
                 max_weight: float = 0.7):
        """Initialize adaptive weight adjuster
        
        Args:
            strategy: Adaptation strategy to use
            learning_rate: Rate of weight adjustment
            min_weight: Minimum weight for any path
            max_weight: Maximum weight for any path
        """
        self.strategy = strategy
        self.learning_rate = learning_rate
        self.min_weight = min_weight
        self.max_weight = max_weight
        
        self.performance_tracker = PerformanceTracker()
        self.base_weights = {
            RetrievalPath.VECTOR: 0.35,
            RetrievalPath.KEYWORDS: 0.25,
            RetrievalPath.SUMMARY: 0.25,
            RetrievalPath.CONTENT: 0.15
        }
        
        # Query-specific weight patterns
        self.query_patterns = {
            QueryType.FACTUAL: {
                RetrievalPath.KEYWORDS: 0.4,
                RetrievalPath.CONTENT: 0.3,
                RetrievalPath.VECTOR: 0.2,
                RetrievalPath.SUMMARY: 0.1
            },
            QueryType.CONCEPTUAL: {
                RetrievalPath.VECTOR: 0.45,
                RetrievalPath.SUMMARY: 0.3,
                RetrievalPath.KEYWORDS: 0.15,
                RetrievalPath.CONTENT: 0.1
            },
            QueryType.PROCEDURAL: {
                RetrievalPath.CONTENT: 0.4,
                RetrievalPath.KEYWORDS: 0.3,
                RetrievalPath.VECTOR: 0.2,
                RetrievalPath.SUMMARY: 0.1
            },
            QueryType.COMPARATIVE: {
                RetrievalPath.VECTOR: 0.35,
                RetrievalPath.SUMMARY: 0.35,
                RetrievalPath.KEYWORDS: 0.2,
                RetrievalPath.CONTENT: 0.1
            }
        }
        
        logger.info(f"AdaptiveWeightAdjuster initialized with strategy: {strategy.value}")
    
    def adjust_weights(self, 
                      query: str,
                      query_context: QueryContext,
                      base_weights: Dict[RetrievalPath, float],
                      historical_performance: Optional[Dict[RetrievalPath, PerformanceMetrics]] = None) -> Dict[RetrievalPath, float]:
        """Adjust weights based on query context and performance
        
        Args:
            query: Original query
            query_context: Query context information
            base_weights: Base weights to adjust
            historical_performance: Optional historical performance data
            
        Returns:
            Adjusted weights dictionary
        """
        if self.strategy == AdaptationStrategy.PERFORMANCE_BASED:
            adjusted_weights = self._adjust_by_performance(base_weights, query_context)
        elif self.strategy == AdaptationStrategy.QUERY_AWARE:
            adjusted_weights = self._adjust_by_query(base_weights, query_context)
        elif self.strategy == AdaptationStrategy.HYBRID:
            adjusted_weights = self._adjust_hybrid(base_weights, query_context, historical_performance)
        elif self.strategy == AdaptationStrategy.REINFORCEMENT:
            adjusted_weights = self._adjust_reinforcement(base_weights, query_context)
        else:
            adjusted_weights = base_weights.copy()
        
        # Normalize and constrain weights
        adjusted_weights = self._normalize_weights(adjusted_weights)
        adjusted_weights = self._constrain_weights(adjusted_weights)
        
        # Record adjustment
        adjustment = WeightAdjustment(
            timestamp=time.time(),
            query_context=query_context,
            original_weights=base_weights.copy(),
            adjusted_weights=adjusted_weights.copy(),
            performance_feedback=historical_performance,
            strategy_used=self.strategy
        )
        self.performance_tracker.adjustment_history.append(adjustment)
        
        logger.debug(f"Weights adjusted: {base_weights} -> {adjusted_weights}")
        return adjusted_weights
    
    def _adjust_by_performance(self, 
                              base_weights: Dict[RetrievalPath, float],
                              query_context: QueryContext) -> Dict[RetrievalPath, float]:
        """Adjust weights based on historical performance"""
        adjusted_weights = base_weights.copy()
        
        # Get performance rankings
        path_rankings = self.performance_tracker.get_path_rankings(query_context)
        
        if not path_rankings:
            return adjusted_weights
        
        # Boost weights for better performing paths
        total_adjustment = 0.0
        for i, (path, score) in enumerate(path_rankings):
            if path in adjusted_weights:
                # Higher performing paths get positive adjustment
                rank_factor = (len(path_rankings) - i) / len(path_rankings)
                performance_factor = score
                adjustment = self.learning_rate * rank_factor * performance_factor
                
                adjusted_weights[path] += adjustment
                total_adjustment += adjustment
        
        return adjusted_weights
    
    def _adjust_by_query(self, 
                        base_weights: Dict[RetrievalPath, float],
                        query_context: QueryContext) -> Dict[RetrievalPath, float]:
        """Adjust weights based on query characteristics"""
        adjusted_weights = base_weights.copy()
        
        # Get query-specific pattern
        if query_context.query_type in self.query_patterns:
            pattern_weights = self.query_patterns[query_context.query_type]
            
            # Blend with base weights
            blend_factor = 0.3  # How much to blend with pattern
            for path in adjusted_weights:
                if path in pattern_weights:
                    pattern_weight = pattern_weights[path]
                    adjusted_weights[path] = (
                        adjusted_weights[path] * (1 - blend_factor) +
                        pattern_weight * blend_factor
                    )
        
        # Adjust based on complexity
        if query_context.complexity == QueryComplexity.SIMPLE:
            # Simple queries: boost keywords and exact matching
            adjusted_weights[RetrievalPath.KEYWORDS] *= 1.2
            adjusted_weights[RetrievalPath.VECTOR] *= 0.9
        elif query_context.complexity == QueryComplexity.COMPLEX:
            # Complex queries: boost semantic understanding
            adjusted_weights[RetrievalPath.VECTOR] *= 1.3
            adjusted_weights[RetrievalPath.SUMMARY] *= 1.1
            adjusted_weights[RetrievalPath.KEYWORDS] *= 0.8
        
        # Adjust based on semantic density
        if query_context.semantic_density > 0.7:
            # High semantic density: boost vector search
            adjusted_weights[RetrievalPath.VECTOR] *= 1.2
        elif query_context.semantic_density < 0.3:
            # Low semantic density: boost keyword search
            adjusted_weights[RetrievalPath.KEYWORDS] *= 1.2
        
        # Adjust based on special features
        if query_context.has_entities:
            adjusted_weights[RetrievalPath.KEYWORDS] *= 1.1
        
        if query_context.has_numbers or query_context.has_dates:
            adjusted_weights[RetrievalPath.CONTENT] *= 1.2
        
        return adjusted_weights
    
    def _adjust_hybrid(self, 
                      base_weights: Dict[RetrievalPath, float],
                      query_context: QueryContext,
                      historical_performance: Optional[Dict[RetrievalPath, PerformanceMetrics]]) -> Dict[RetrievalPath, float]:
        """Hybrid adjustment combining performance and query-aware strategies"""
        # Get adjustments from both strategies
        performance_weights = self._adjust_by_performance(base_weights, query_context)
        query_weights = self._adjust_by_query(base_weights, query_context)
        
        # Blend the two approaches
        performance_factor = 0.6 if historical_performance else 0.3
        query_factor = 1.0 - performance_factor
        
        hybrid_weights = {}
        for path in base_weights:
            hybrid_weights[path] = (
                performance_weights.get(path, base_weights[path]) * performance_factor +
                query_weights.get(path, base_weights[path]) * query_factor
            )
        
        return hybrid_weights
    
    def _adjust_reinforcement(self, 
                             base_weights: Dict[RetrievalPath, float],
                             query_context: QueryContext) -> Dict[RetrievalPath, float]:
        """Reinforcement learning-based adjustment (simplified)"""
        # This is a simplified version - in practice, you'd use more sophisticated RL
        adjusted_weights = base_weights.copy()
        
        # Get recent performance data
        recent_adjustments = list(self.performance_tracker.adjustment_history)[-10:]
        
        if not recent_adjustments:
            return adjusted_weights
        
        # Simple reward-based adjustment
        path_rewards = defaultdict(list)
        for adjustment in recent_adjustments:
            if adjustment.performance_feedback:
                for path, metrics in adjustment.performance_feedback.items():
                    reward = metrics.overall_score()
                    path_rewards[path].append(reward)
        
        # Update weights based on average rewards
        for path, rewards in path_rewards.items():
            if path in adjusted_weights and rewards:
                avg_reward = sum(rewards) / len(rewards)
                # Simple policy gradient-like update
                adjustment = self.learning_rate * (avg_reward - 0.5)  # 0.5 as baseline
                adjusted_weights[path] += adjustment
        
        return adjusted_weights
    
    def _normalize_weights(self, weights: Dict[RetrievalPath, float]) -> Dict[RetrievalPath, float]:
        """Normalize weights to sum to 1.0"""
        total = sum(weights.values())
        if total <= 0:
            # Fallback to equal weights
            equal_weight = 1.0 / len(weights)
            return {path: equal_weight for path in weights}
        
        return {path: weight / total for path, weight in weights.items()}
    
    def _constrain_weights(self, weights: Dict[RetrievalPath, float]) -> Dict[RetrievalPath, float]:
        """Constrain weights to be within min/max bounds"""
        constrained = {}
        
        for path, weight in weights.items():
            constrained[path] = max(self.min_weight, min(self.max_weight, weight))
        
        # Re-normalize after constraining
        return self._normalize_weights(constrained)
    
    def record_feedback(self, 
                       query_context: QueryContext,
                       path_performance: Dict[RetrievalPath, PerformanceMetrics]):
        """Record performance feedback for learning"""
        for path, metrics in path_performance.items():
            self.performance_tracker.record_performance(path, metrics, query_context)
        
        logger.debug(f"Recorded feedback for {len(path_performance)} paths")
    
    def get_adaptation_stats(self) -> Dict[str, Any]:
        """Get statistics about weight adaptations"""
        adjustments = list(self.performance_tracker.adjustment_history)
        
        if not adjustments:
            return {'total_adjustments': 0}
        
        # Calculate statistics
        strategy_counts = defaultdict(int)
        avg_adjustments = defaultdict(list)
        
        for adj in adjustments:
            strategy_counts[adj.strategy_used.value] += 1
            
            for path, orig_weight in adj.original_weights.items():
                adj_weight = adj.adjusted_weights.get(path, orig_weight)
                change = adj_weight - orig_weight
                avg_adjustments[path.value].append(change)
        
        # Calculate average changes
        avg_changes = {}
        for path, changes in avg_adjustments.items():
            avg_changes[path] = sum(changes) / len(changes) if changes else 0.0
        
        return {
            'total_adjustments': len(adjustments),
            'strategy_distribution': dict(strategy_counts),
            'average_weight_changes': avg_changes,
            'recent_adjustments': len([adj for adj in adjustments if time.time() - adj.timestamp < 3600])  # Last hour
        }
    
    def update_strategy(self, new_strategy: AdaptationStrategy):
        """Update adaptation strategy"""
        self.strategy = new_strategy
        logger.info(f"Adaptation strategy updated to: {new_strategy.value}")
    
    def reset_learning(self):
        """Reset learning history"""
        self.performance_tracker = PerformanceTracker()
        logger.info("Learning history reset")


def create_adaptive_weight_adjuster(strategy: str = "hybrid", **kwargs) -> AdaptiveWeightAdjuster:
    """Factory function to create adaptive weight adjuster
    
    Args:
        strategy: Adaptation strategy name
        **kwargs: Additional configuration parameters
        
    Returns:
        AdaptiveWeightAdjuster instance
    """
    strategy_enum = AdaptationStrategy(strategy.lower())
    return AdaptiveWeightAdjuster(strategy=strategy_enum, **kwargs)