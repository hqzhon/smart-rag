"""Query Router for Intelligent Path Selection

This module implements intelligent query routing that analyzes query characteristics
and selects optimal retrieval paths to improve efficiency and accuracy.
"""

from typing import List, Dict, Any, Optional, Set, Tuple
import re
import asyncio
from dataclasses import dataclass
from enum import Enum
from collections import Counter

from app.retrieval.advanced_config import RetrievalPath
from app.utils.logger import setup_logger

logger = setup_logger(__name__)


class QueryType(Enum):
    """Query type classification"""
    FACTUAL = "factual"  # Specific facts or entities
    CONCEPTUAL = "conceptual"  # Abstract concepts or explanations
    PROCEDURAL = "procedural"  # How-to or step-by-step
    COMPARATIVE = "comparative"  # Comparisons between entities
    TEMPORAL = "temporal"  # Time-related queries
    NUMERICAL = "numerical"  # Queries involving numbers or calculations
    MIXED = "mixed"  # Multiple query types


class QueryComplexity(Enum):
    """Query complexity levels"""
    SIMPLE = "simple"  # Single concept, short query
    MODERATE = "moderate"  # Multiple concepts, medium length
    COMPLEX = "complex"  # Multiple concepts, long query, complex relationships


@dataclass
class QueryAnalysis:
    """Query analysis result"""
    query_type: QueryType
    complexity: QueryComplexity
    key_entities: List[str]
    keywords: List[str]
    semantic_density: float  # 0-1, higher means more semantic content
    keyword_density: float   # 0-1, higher means more keyword-searchable
    confidence: float        # 0-1, confidence in the analysis
    recommended_paths: List[RetrievalPath]
    path_weights: Dict[RetrievalPath, float]


class QueryRouter:
    """Intelligent query router for path selection
    
    Analyzes query characteristics and recommends optimal retrieval paths
    with dynamic weight adjustments based on query type and complexity.
    """
    
    def __init__(self):
        """Initialize query router"""
        # Patterns for query type detection
        self.factual_patterns = [
            r'\bwhat is\b', r'\bwho is\b', r'\bwhen did\b', r'\bwhere is\b',
            r'\bdefine\b', r'\bdefinition\b', r'\bmeaning\b'
        ]
        
        self.procedural_patterns = [
            r'\bhow to\b', r'\bsteps\b', r'\bprocess\b', r'\bprocedure\b',
            r'\bmethod\b', r'\bway to\b', r'\bguide\b', r'\btutorial\b'
        ]
        
        self.comparative_patterns = [
            r'\bcompare\b', r'\bversus\b', r'\bvs\b', r'\bdifference\b',
            r'\bbetter\b', r'\bworse\b', r'\bsimilar\b', r'\bunlike\b'
        ]
        
        self.temporal_patterns = [
            r'\bhistory\b', r'\btimeline\b', r'\bevolution\b', r'\btrend\b',
            r'\brecent\b', r'\blatest\b', r'\bcurrent\b', r'\bfuture\b'
        ]
        
        self.numerical_patterns = [
            r'\d+', r'\bnumber\b', r'\bcount\b', r'\bstatistics\b',
            r'\bpercentage\b', r'\brate\b', r'\bmeasure\b'
        ]
        
        # Entity extraction patterns
        self.entity_patterns = [
            r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b',  # Proper nouns
            r'\b\d{4}\b',  # Years
            r'\b[A-Z]{2,}\b'  # Acronyms
        ]
        
        # Stop words for keyword extraction
        self.stop_words = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
            'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'being',
            'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could',
            'should', 'may', 'might', 'can', 'this', 'that', 'these', 'those'
        }
        
        logger.info("QueryRouter initialized")
    
    def analyze_query(self, query: str) -> QueryAnalysis:
        """Analyze query characteristics and recommend retrieval strategy
        
        Args:
            query: Input query string
            
        Returns:
            QueryAnalysis with recommendations
        """
        query_lower = query.lower().strip()
        
        # Detect query type
        query_type = self._detect_query_type(query_lower)
        
        # Assess complexity
        complexity = self._assess_complexity(query)
        
        # Extract entities and keywords
        entities = self._extract_entities(query)
        keywords = self._extract_keywords(query_lower)
        
        # Calculate densities
        semantic_density = self._calculate_semantic_density(query_lower)
        keyword_density = self._calculate_keyword_density(query_lower)
        
        # Generate recommendations
        recommended_paths, path_weights = self._recommend_paths(
            query_type, complexity, semantic_density, keyword_density
        )
        
        # Calculate confidence
        confidence = self._calculate_confidence(
            query_type, complexity, len(entities), len(keywords)
        )
        
        return QueryAnalysis(
            query_type=query_type,
            complexity=complexity,
            key_entities=entities,
            keywords=keywords,
            semantic_density=semantic_density,
            keyword_density=keyword_density,
            confidence=confidence,
            recommended_paths=recommended_paths,
            path_weights=path_weights
        )
    
    def _detect_query_type(self, query: str) -> QueryType:
        """Detect the primary type of the query"""
        type_scores = {
            QueryType.FACTUAL: 0,
            QueryType.PROCEDURAL: 0,
            QueryType.COMPARATIVE: 0,
            QueryType.TEMPORAL: 0,
            QueryType.NUMERICAL: 0,
            QueryType.CONCEPTUAL: 0
        }
        
        # Check patterns
        for pattern in self.factual_patterns:
            if re.search(pattern, query):
                type_scores[QueryType.FACTUAL] += 1
        
        for pattern in self.procedural_patterns:
            if re.search(pattern, query):
                type_scores[QueryType.PROCEDURAL] += 1
        
        for pattern in self.comparative_patterns:
            if re.search(pattern, query):
                type_scores[QueryType.COMPARATIVE] += 1
        
        for pattern in self.temporal_patterns:
            if re.search(pattern, query):
                type_scores[QueryType.TEMPORAL] += 1
        
        for pattern in self.numerical_patterns:
            if re.search(pattern, query):
                type_scores[QueryType.NUMERICAL] += 1
        
        # Default to conceptual if no specific patterns
        max_score = max(type_scores.values())
        if max_score == 0:
            return QueryType.CONCEPTUAL
        
        # Check for mixed type
        high_scores = [t for t, s in type_scores.items() if s == max_score]
        if len(high_scores) > 1:
            return QueryType.MIXED
        
        return high_scores[0]
    
    def _assess_complexity(self, query: str) -> QueryComplexity:
        """Assess query complexity based on length and structure"""
        words = query.split()
        word_count = len(words)
        
        # Count conjunctions and complex structures
        conjunctions = len(re.findall(r'\b(and|or|but|however|therefore|because)\b', query.lower()))
        questions = len(re.findall(r'\?', query))
        
        complexity_score = word_count + conjunctions * 2 + questions
        
        if complexity_score <= 5:
            return QueryComplexity.SIMPLE
        elif complexity_score <= 15:
            return QueryComplexity.MODERATE
        else:
            return QueryComplexity.COMPLEX
    
    def _extract_entities(self, query: str) -> List[str]:
        """Extract named entities from query"""
        entities = []
        
        for pattern in self.entity_patterns:
            matches = re.findall(pattern, query)
            entities.extend(matches)
        
        # Remove duplicates and filter
        entities = list(set(entities))
        entities = [e for e in entities if len(e) > 1 and e.lower() not in self.stop_words]
        
        return entities[:10]  # Limit to top 10
    
    def _extract_keywords(self, query: str) -> List[str]:
        """Extract keywords from query"""
        # Simple keyword extraction
        words = re.findall(r'\b\w+\b', query)
        words = [w for w in words if len(w) > 2 and w not in self.stop_words]
        
        # Count frequency and return most common
        word_counts = Counter(words)
        keywords = [word for word, count in word_counts.most_common(10)]
        
        return keywords
    
    def _calculate_semantic_density(self, query: str) -> float:
        """Calculate semantic density (abstract vs concrete content)"""
        words = query.split()
        if not words:
            return 0.0
        
        # Abstract/semantic indicators
        semantic_words = [
            'concept', 'idea', 'theory', 'principle', 'approach', 'method',
            'understand', 'explain', 'analyze', 'evaluate', 'compare',
            'relationship', 'connection', 'impact', 'effect', 'influence'
        ]
        
        semantic_count = sum(1 for word in words if word in semantic_words)
        return min(semantic_count / len(words) * 3, 1.0)  # Scale and cap at 1.0
    
    def _calculate_keyword_density(self, query: str) -> float:
        """Calculate keyword density (specific terms vs general language)"""
        words = query.split()
        if not words:
            return 0.0
        
        # Count specific/technical terms (longer words, proper nouns)
        specific_count = sum(1 for word in words if len(word) > 6 or word[0].isupper())
        return min(specific_count / len(words) * 2, 1.0)  # Scale and cap at 1.0
    
    def _recommend_paths(self, 
                        query_type: QueryType, 
                        complexity: QueryComplexity,
                        semantic_density: float, 
                        keyword_density: float) -> Tuple[List[RetrievalPath], Dict[RetrievalPath, float]]:
        """Recommend retrieval paths and weights based on analysis"""
        
        # Base weights for all paths
        base_weights = {
            RetrievalPath.VECTOR: 0.3,
            RetrievalPath.KEYWORDS: 0.25,
            RetrievalPath.SUMMARY: 0.25,
            RetrievalPath.CONTENT: 0.2
        }
        
        # Adjust weights based on query type
        if query_type == QueryType.FACTUAL:
            base_weights[RetrievalPath.KEYWORDS] += 0.2
            base_weights[RetrievalPath.SUMMARY] += 0.1
            base_weights[RetrievalPath.VECTOR] -= 0.1
            
        elif query_type == QueryType.CONCEPTUAL:
            base_weights[RetrievalPath.VECTOR] += 0.2
            base_weights[RetrievalPath.CONTENT] += 0.1
            base_weights[RetrievalPath.KEYWORDS] -= 0.1
            
        elif query_type == QueryType.PROCEDURAL:
            base_weights[RetrievalPath.CONTENT] += 0.2
            base_weights[RetrievalPath.SUMMARY] += 0.1
            base_weights[RetrievalPath.VECTOR] -= 0.1
            
        elif query_type == QueryType.COMPARATIVE:
            base_weights[RetrievalPath.VECTOR] += 0.15
            base_weights[RetrievalPath.CONTENT] += 0.15
            base_weights[RetrievalPath.KEYWORDS] -= 0.1
        
        # Adjust based on complexity
        if complexity == QueryComplexity.SIMPLE:
            base_weights[RetrievalPath.KEYWORDS] += 0.1
            base_weights[RetrievalPath.SUMMARY] += 0.05
        elif complexity == QueryComplexity.COMPLEX:
            base_weights[RetrievalPath.VECTOR] += 0.1
            base_weights[RetrievalPath.CONTENT] += 0.1
        
        # Adjust based on densities
        semantic_adjustment = semantic_density * 0.2
        keyword_adjustment = keyword_density * 0.2
        
        base_weights[RetrievalPath.VECTOR] += semantic_adjustment
        base_weights[RetrievalPath.KEYWORDS] += keyword_adjustment
        
        # Normalize weights
        total_weight = sum(base_weights.values())
        if total_weight > 0:
            normalized_weights = {path: weight / total_weight 
                                for path, weight in base_weights.items()}
        else:
            normalized_weights = base_weights
        
        # Select paths with significant weights (> 0.1)
        recommended_paths = [path for path, weight in normalized_weights.items() 
                           if weight > 0.1]
        
        # Ensure at least 2 paths are recommended
        if len(recommended_paths) < 2:
            sorted_paths = sorted(normalized_weights.items(), key=lambda x: x[1], reverse=True)
            recommended_paths = [path for path, _ in sorted_paths[:2]]
        
        return recommended_paths, normalized_weights
    
    def _calculate_confidence(self, 
                            query_type: QueryType, 
                            complexity: QueryComplexity,
                            entity_count: int, 
                            keyword_count: int) -> float:
        """Calculate confidence in the analysis"""
        confidence = 0.5  # Base confidence
        
        # Higher confidence for clear query types
        if query_type != QueryType.MIXED:
            confidence += 0.2
        
        # Higher confidence for simpler queries
        if complexity == QueryComplexity.SIMPLE:
            confidence += 0.2
        elif complexity == QueryComplexity.MODERATE:
            confidence += 0.1
        
        # Higher confidence with more entities/keywords
        confidence += min(entity_count * 0.05, 0.2)
        confidence += min(keyword_count * 0.03, 0.15)
        
        return min(confidence, 1.0)
    
    def get_adaptive_weights(self, 
                           query: str, 
                           base_weights: Dict[RetrievalPath, float]) -> Dict[RetrievalPath, float]:
        """Get adaptive weights based on query analysis
        
        Args:
            query: Input query
            base_weights: Base weights from configuration
            
        Returns:
            Adjusted weights based on query characteristics
        """
        analysis = self.analyze_query(query)
        
        # Blend recommended weights with base weights
        adaptive_weights = {}
        for path in RetrievalPath:
            base_weight = base_weights.get(path, 0.0)
            recommended_weight = analysis.path_weights.get(path, 0.0)
            
            # Weighted average based on confidence
            confidence = analysis.confidence
            adaptive_weight = (base_weight * (1 - confidence) + 
                             recommended_weight * confidence)
            
            adaptive_weights[path] = adaptive_weight
        
        # Normalize
        total_weight = sum(adaptive_weights.values())
        if total_weight > 0:
            adaptive_weights = {path: weight / total_weight 
                              for path, weight in adaptive_weights.items()}
        
        return adaptive_weights