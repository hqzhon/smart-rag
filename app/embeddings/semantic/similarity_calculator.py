"""Semantic similarity calculator using QianwenEmbeddings."""

import hashlib
import numpy as np
from typing import List, Optional, Dict, Any
from sklearn.metrics.pairwise import cosine_similarity

from ..embeddings import QianwenEmbeddings
from ...utils.logger import get_logger

logger = get_logger(__name__)


class SemanticSimilarityCalculator:
    """Calculate semantic similarity between texts using embeddings."""
    
    def __init__(self, embeddings_model: QianwenEmbeddings, cache_size: int = 1000):
        """Initialize similarity calculator.
        
        Args:
            embeddings_model: QianwenEmbeddings instance
            cache_size: Maximum number of embeddings to cache
        """
        self.embeddings_model = embeddings_model
        self.cache: Dict[str, List[float]] = {}
        self.cache_size = cache_size
        self._cache_order: List[str] = []  # Track insertion order for LRU
    
    def _get_text_hash(self, text: str) -> str:
        """Generate hash for text caching."""
        return hashlib.md5(text.encode('utf-8')).hexdigest()
    
    def _get_cached_embedding(self, text: str) -> Optional[List[float]]:
        """Get embedding from cache if available."""
        text_hash = self._get_text_hash(text)
        if text_hash in self.cache:
            # Move to end for LRU
            self._cache_order.remove(text_hash)
            self._cache_order.append(text_hash)
            return self.cache[text_hash]
        return None
    
    def _cache_embedding(self, text: str, embedding: List[float]) -> None:
        """Cache embedding with LRU eviction."""
        text_hash = self._get_text_hash(text)
        
        # Remove oldest if cache is full
        if len(self.cache) >= self.cache_size and text_hash not in self.cache:
            oldest_hash = self._cache_order.pop(0)
            del self.cache[oldest_hash]
        
        # Add or update cache
        if text_hash in self.cache:
            self._cache_order.remove(text_hash)
        else:
            self.cache[text_hash] = embedding
        
        self._cache_order.append(text_hash)
    
    async def _get_embedding(self, text: str) -> List[float]:
        """Get embedding for text with caching."""
        # Check cache first
        cached = self._get_cached_embedding(text)
        if cached is not None:
            return cached
        
        # Get embedding from model
        try:
            embedding = await self.embeddings_model.embed_query(text)
            self._cache_embedding(text, embedding)
            return embedding
        except Exception as e:
            logger.error(f"Failed to get embedding for text: {e}")
            raise
    
    async def calculate_similarity(self, text1: str, text2: str) -> float:
        """Calculate cosine similarity between two texts.
        
        Args:
            text1: First text
            text2: Second text
            
        Returns:
            Cosine similarity score between 0 and 1
        """
        try:
            # Get embeddings for both texts
            embedding1 = await self._get_embedding(text1)
            embedding2 = await self._get_embedding(text2)
            
            # Calculate cosine similarity
            embedding1_np = np.array(embedding1).reshape(1, -1)
            embedding2_np = np.array(embedding2).reshape(1, -1)
            
            similarity = cosine_similarity(embedding1_np, embedding2_np)[0][0]
            
            # Ensure similarity is between 0 and 1
            return max(0.0, min(1.0, float(similarity)))
            
        except Exception as e:
            logger.error(f"Failed to calculate similarity: {e}")
            # Return low similarity on error to be safe
            return 0.0
    
    async def batch_similarity(self, texts: List[str]) -> List[List[float]]:
        """Calculate similarity matrix for a list of texts.
        
        Args:
            texts: List of texts to compare
            
        Returns:
            Similarity matrix where matrix[i][j] is similarity between texts[i] and texts[j]
        """
        if not texts:
            return []
        
        try:
            # Get all embeddings
            embeddings = []
            for text in texts:
                embedding = await self._get_embedding(text)
                embeddings.append(embedding)
            
            # Convert to numpy array
            embeddings_np = np.array(embeddings)
            
            # Calculate similarity matrix
            similarity_matrix = cosine_similarity(embeddings_np)
            
            # Ensure all values are between 0 and 1
            similarity_matrix = np.clip(similarity_matrix, 0.0, 1.0)
            
            return similarity_matrix.tolist()
            
        except Exception as e:
            logger.error(f"Failed to calculate batch similarity: {e}")
            # Return identity matrix on error
            n = len(texts)
            return [[1.0 if i == j else 0.0 for j in range(n)] for i in range(n)]
    
    async def find_most_similar(self, target_text: str, candidate_texts: List[str]) -> tuple[int, float]:
        """Find the most similar text from candidates.
        
        Args:
            target_text: Text to compare against
            candidate_texts: List of candidate texts
            
        Returns:
            Tuple of (index, similarity_score) of most similar text
        """
        if not candidate_texts:
            return -1, 0.0
        
        max_similarity = -1.0
        max_index = -1
        
        for i, candidate in enumerate(candidate_texts):
            similarity = await self.calculate_similarity(target_text, candidate)
            if similarity > max_similarity:
                max_similarity = similarity
                max_index = i
        
        return max_index, max_similarity
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        return {
            "cache_size": len(self.cache),
            "max_cache_size": self.cache_size,
            "cache_hit_ratio": len(self.cache) / max(1, self.cache_size)
        }
    
    def clear_cache(self) -> None:
        """Clear the embedding cache."""
        self.cache.clear()
        self._cache_order.clear()
        logger.info("Embedding cache cleared")