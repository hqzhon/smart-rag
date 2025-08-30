"""Advanced Fusion Algorithms for Multi-Path RAG Retrieval

This module implements various fusion algorithms for combining results from
multiple retrieval paths, including weighted RRF, score normalization,
and diversity-aware ranking.
"""

from typing import List, Dict, Any, Optional, Tuple, Set
import math
import numpy as np
from collections import defaultdict, Counter
from app.utils.logger import setup_logger
from app.retrieval.advanced_config import FusionMethod, RetrievalPath
import time

logger = setup_logger(__name__)


class ScoreNormalizer:
    """Score normalization utilities"""
    
    @staticmethod
    def min_max_normalize(scores: List[float]) -> List[float]:
        """Min-max normalization to [0, 1] range"""
        if not scores or len(scores) == 1:
            return scores
        
        min_score = min(scores)
        max_score = max(scores)
        
        if max_score == min_score:
            return [1.0] * len(scores)
        
        return [(score - min_score) / (max_score - min_score) for score in scores]
    
    @staticmethod
    def z_score_normalize(scores: List[float]) -> List[float]:
        """Z-score normalization (standardization)"""
        if not scores or len(scores) == 1:
            return scores
        
        mean_score = sum(scores) / len(scores)
        variance = sum((score - mean_score) ** 2 for score in scores) / len(scores)
        std_dev = math.sqrt(variance)
        
        if std_dev == 0:
            return [0.0] * len(scores)
        
        return [(score - mean_score) / std_dev for score in scores]
    
    @staticmethod
    def rank_normalize(scores: List[float]) -> List[float]:
        """Rank-based normalization"""
        if not scores:
            return scores
        
        # Create (score, original_index) pairs and sort by score descending
        indexed_scores = [(score, i) for i, score in enumerate(scores)]
        indexed_scores.sort(key=lambda x: x[0], reverse=True)
        
        # Assign normalized ranks
        normalized_scores = [0.0] * len(scores)
        for rank, (_, original_index) in enumerate(indexed_scores):
            normalized_scores[original_index] = 1.0 - (rank / len(scores))
        
        return normalized_scores


class DiversityCalculator:
    """Calculate diversity metrics for result sets"""
    
    @staticmethod
    def calculate_content_similarity(doc1: Dict[str, Any], doc2: Dict[str, Any]) -> float:
        """Calculate content similarity between two documents
        
        Uses simple token overlap for now, can be enhanced with embeddings
        """
        content1 = doc1.get('content', '').lower()
        content2 = doc2.get('content', '').lower()
        
        if not content1 or not content2:
            return 0.0
        
        # Simple token-based similarity
        tokens1 = set(content1.split())
        tokens2 = set(content2.split())
        
        if not tokens1 or not tokens2:
            return 0.0
        
        intersection = len(tokens1.intersection(tokens2))
        union = len(tokens1.union(tokens2))
        
        return intersection / union if union > 0 else 0.0
    
    @staticmethod
    def calculate_diversity_penalty(results: List[Dict[str, Any]], 
                                  penalty_factor: float = 0.1) -> List[float]:
        """Calculate diversity penalty for each result
        
        Args:
            results: List of result documents
            penalty_factor: Penalty factor for similar documents
            
        Returns:
            List of penalty values (0 = no penalty, 1 = maximum penalty)
        """
        if len(results) <= 1:
            return [0.0] * len(results)
        
        penalties = [0.0] * len(results)
        
        for i in range(len(results)):
            max_similarity = 0.0
            
            # Find maximum similarity with higher-ranked documents
            for j in range(i):
                similarity = DiversityCalculator.calculate_content_similarity(
                    results[i], results[j]
                )
                max_similarity = max(max_similarity, similarity)
            
            penalties[i] = max_similarity * penalty_factor
        
        return penalties


class WeightedRRFFusion:
    """Weighted Reciprocal Rank Fusion algorithm
    
    Enhanced RRF that supports path-specific weights and advanced normalization
    """
    
    def __init__(self, k: int = 60, normalize_scores: bool = True, 
                 diversity_penalty: float = 0.0):
        """
        Initialize Weighted RRF fusion
        
        Args:
            k: RRF parameter (higher k = less aggressive ranking)
            normalize_scores: Whether to normalize scores before fusion
            diversity_penalty: Penalty factor for similar documents (0-1)
        """
        self.k = k
        self.normalize_scores = normalize_scores
        self.diversity_penalty = diversity_penalty
        self.normalizer = ScoreNormalizer()
        self.diversity_calc = DiversityCalculator()
    
    def fuse_results(self, path_results: Dict[RetrievalPath, List[Dict[str, Any]]], 
                    path_weights: Dict[RetrievalPath, float],
                    final_top_k: int = 20) -> List[Dict[str, Any]]:
        """
        Fuse results from multiple retrieval paths using weighted RRF
        
        Args:
            path_results: Dictionary mapping paths to their results
            path_weights: Dictionary mapping paths to their weights
            final_top_k: Number of final results to return
            
        Returns:
            Fused and ranked results
        """
        start_time = time.time()
        
        # Collect all unique documents
        all_docs = {}
        doc_path_ranks = defaultdict(dict)
        doc_path_scores = defaultdict(dict)
        
        # Process each path's results
        for path, results in path_results.items():
            if not results or path not in path_weights:
                continue
            
            weight = path_weights[path]
            if weight <= 0:
                continue
            
            # Extract scores and normalize if needed
            scores = []
            for doc in results:
                # Try different score field names
                score = (doc.get('bm25_score') or 
                        doc.get('similarity_score') or 
                        doc.get('score') or 
                        doc.get('rerank_score', 0.0))
                scores.append(float(score))
            
            if self.normalize_scores and scores:
                normalized_scores = self.normalizer.min_max_normalize(scores)
            else:
                normalized_scores = scores
            
            # Store documents and their ranks/scores
            for rank, (doc, norm_score) in enumerate(zip(results, normalized_scores)):
                doc_id = doc.get('id') or doc.get('chunk_id', f"doc_{rank}")
                
                # Store document
                if doc_id not in all_docs:
                    all_docs[doc_id] = doc.copy()
                
                # Store rank and score for this path
                doc_path_ranks[doc_id][path] = rank + 1  # 1-based ranking
                doc_path_scores[doc_id][path] = norm_score
        
        if not all_docs:
            logger.warning("No documents found in any path results")
            return []
        
        # Calculate weighted RRF scores
        doc_fusion_scores = {}
        
        for doc_id in all_docs:
            fusion_score = 0.0
            
            for path, weight in path_weights.items():
                if weight <= 0 or path not in doc_path_ranks[doc_id]:
                    continue
                
                rank = doc_path_ranks[doc_id][path]
                rrf_score = weight / (self.k + rank)
                fusion_score += rrf_score
            
            doc_fusion_scores[doc_id] = fusion_score
        
        # Sort documents by fusion score
        sorted_doc_ids = sorted(doc_fusion_scores.keys(), 
                               key=lambda x: doc_fusion_scores[x], 
                               reverse=True)
        
        # Create final results
        final_results = []
        for doc_id in sorted_doc_ids[:final_top_k * 2]:  # Get more for diversity filtering
            doc = all_docs[doc_id].copy()
            doc['fusion_score'] = doc_fusion_scores[doc_id]
            doc['path_contributions'] = {
                path.value: {
                    'rank': doc_path_ranks[doc_id].get(path, None),
                    'score': doc_path_scores[doc_id].get(path, 0.0),
                    'weight': path_weights.get(path, 0.0)
                } for path in path_weights.keys()
            }
            final_results.append(doc)
        
        # Apply diversity penalty if enabled
        if self.diversity_penalty > 0 and len(final_results) > 1:
            final_results = self._apply_diversity_penalty(final_results)
        
        # Return final top_k results
        final_results = final_results[:final_top_k]
        
        fusion_time = time.time() - start_time
        logger.info(f"Weighted RRF fusion completed in {fusion_time:.3f}s, "
                   f"fused {len(path_results)} paths into {len(final_results)} results")
        
        return final_results
    
    def _apply_diversity_penalty(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Apply diversity penalty to results"""
        if len(results) <= 1:
            return results
        
        penalties = self.diversity_calc.calculate_diversity_penalty(
            results, self.diversity_penalty
        )
        
        # Adjust fusion scores with penalties
        for i, (result, penalty) in enumerate(zip(results, penalties)):
            original_score = result['fusion_score']
            adjusted_score = original_score * (1.0 - penalty)
            result['fusion_score'] = adjusted_score
            result['diversity_penalty'] = penalty
        
        # Re-sort by adjusted scores
        results.sort(key=lambda x: x['fusion_score'], reverse=True)
        
        return results


class SimpleRRFFusion:
    """Simple RRF fusion without weights"""
    
    def __init__(self, k: int = 60):
        self.k = k
    
    def fuse_results(self, path_results: Dict[RetrievalPath, List[Dict[str, Any]]], 
                    final_top_k: int = 20) -> List[Dict[str, Any]]:
        """Simple RRF fusion treating all paths equally"""
        # Convert to equal weights
        path_weights = {path: 1.0 for path in path_results.keys()}
        
        # Use weighted RRF with equal weights
        weighted_rrf = WeightedRRFFusion(k=self.k, normalize_scores=False)
        return weighted_rrf.fuse_results(path_results, path_weights, final_top_k)


class WeightedSumFusion:
    """Weighted sum fusion algorithm"""
    
    def __init__(self, normalize_scores: bool = True):
        self.normalize_scores = normalize_scores
        self.normalizer = ScoreNormalizer()
    
    def fuse_results(self, path_results: Dict[RetrievalPath, List[Dict[str, Any]]], 
                    path_weights: Dict[RetrievalPath, float],
                    final_top_k: int = 20) -> List[Dict[str, Any]]:
        """Fuse results using weighted sum of normalized scores"""
        all_docs = {}
        doc_weighted_scores = defaultdict(float)
        
        for path, results in path_results.items():
            if not results or path not in path_weights:
                continue
            
            weight = path_weights[path]
            if weight <= 0:
                continue
            
            # Extract and normalize scores
            scores = []
            for doc in results:
                score = (doc.get('bm25_score') or 
                        doc.get('similarity_score') or 
                        doc.get('score') or 
                        doc.get('rerank_score', 0.0))
                scores.append(float(score))
            
            if self.normalize_scores and scores:
                normalized_scores = self.normalizer.min_max_normalize(scores)
            else:
                normalized_scores = scores
            
            # Accumulate weighted scores
            for doc, norm_score in zip(results, normalized_scores):
                doc_id = doc.get('id') or doc.get('chunk_id', f"doc_{len(all_docs)}")
                
                if doc_id not in all_docs:
                    all_docs[doc_id] = doc.copy()
                
                doc_weighted_scores[doc_id] += weight * norm_score
        
        # Sort and return results
        sorted_doc_ids = sorted(doc_weighted_scores.keys(), 
                               key=lambda x: doc_weighted_scores[x], 
                               reverse=True)
        
        final_results = []
        for doc_id in sorted_doc_ids[:final_top_k]:
            doc = all_docs[doc_id].copy()
            doc['fusion_score'] = doc_weighted_scores[doc_id]
            final_results.append(doc)
        
        return final_results


class MaxScoreFusion:
    """Maximum score fusion - takes the best score for each document"""
    
    def fuse_results(self, path_results: Dict[RetrievalPath, List[Dict[str, Any]]], 
                    final_top_k: int = 20) -> List[Dict[str, Any]]:
        """Fuse results by taking maximum score for each document"""
        all_docs = {}
        doc_max_scores = defaultdict(float)
        
        for path, results in path_results.items():
            for doc in results:
                doc_id = doc.get('id') or doc.get('chunk_id', f"doc_{len(all_docs)}")
                
                if doc_id not in all_docs:
                    all_docs[doc_id] = doc.copy()
                
                score = (doc.get('bm25_score') or 
                        doc.get('similarity_score') or 
                        doc.get('score') or 
                        doc.get('rerank_score', 0.0))
                
                doc_max_scores[doc_id] = max(doc_max_scores[doc_id], float(score))
        
        # Sort and return results
        sorted_doc_ids = sorted(doc_max_scores.keys(), 
                               key=lambda x: doc_max_scores[x], 
                               reverse=True)
        
        final_results = []
        for doc_id in sorted_doc_ids[:final_top_k]:
            doc = all_docs[doc_id].copy()
            doc['fusion_score'] = doc_max_scores[doc_id]
            final_results.append(doc)
        
        return final_results


class FusionEngine:
    """Main fusion engine that orchestrates different fusion algorithms"""
    
    def __init__(self):
        self.algorithms = {
            FusionMethod.WEIGHTED_RRF: WeightedRRFFusion,
            FusionMethod.SIMPLE_RRF: SimpleRRFFusion,
            FusionMethod.WEIGHTED_SUM: WeightedSumFusion,
            FusionMethod.MAX_SCORE: MaxScoreFusion
        }
    
    def fuse(self, method: FusionMethod, 
            path_results: Dict[RetrievalPath, List[Dict[str, Any]]], 
            path_weights: Optional[Dict[RetrievalPath, float]] = None,
            final_top_k: int = 20,
            **kwargs) -> List[Dict[str, Any]]:
        """
        Fuse results using specified method
        
        Args:
            method: Fusion method to use
            path_results: Results from different retrieval paths
            path_weights: Weights for each path (required for weighted methods)
            final_top_k: Number of final results
            **kwargs: Additional parameters for fusion algorithms
            
        Returns:
            Fused results
        """
        if method not in self.algorithms:
            raise ValueError(f"Unsupported fusion method: {method}")
        
        # Filter out empty results
        filtered_results = {path: results for path, results in path_results.items() 
                           if results}
        
        if not filtered_results:
            logger.warning("No non-empty results to fuse")
            return []
        
        # Initialize fusion algorithm
        algorithm_class = self.algorithms[method]
        
        if method in [FusionMethod.WEIGHTED_RRF, FusionMethod.WEIGHTED_SUM]:
            if not path_weights:
                # Default equal weights
                path_weights = {path: 1.0 / len(filtered_results) 
                               for path in filtered_results.keys()}
            
            algorithm = algorithm_class(**kwargs)
            return algorithm.fuse_results(filtered_results, path_weights, final_top_k)
        
        else:
            algorithm = algorithm_class(**kwargs)
            return algorithm.fuse_results(filtered_results, final_top_k)
    
    def get_supported_methods(self) -> List[FusionMethod]:
        """Get list of supported fusion methods"""
        return list(self.algorithms.keys())