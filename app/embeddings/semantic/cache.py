"""Embedding cache management for semantic chunking."""

import hashlib
import time
from typing import Dict, List, Optional, Any
from collections import OrderedDict

from ...utils.logger import get_logger

logger = get_logger(__name__)


class EmbeddingCache:
    """LRU cache for embedding vectors with TTL support."""
    
    def __init__(self, max_size: int = 1000, ttl_seconds: Optional[int] = None):
        """Initialize embedding cache.
        
        Args:
            max_size: Maximum number of embeddings to cache
            ttl_seconds: Time-to-live for cache entries in seconds (None for no expiration)
        """
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self.cache: OrderedDict[str, Dict[str, Any]] = OrderedDict()
        self._hits = 0
        self._misses = 0
    
    def _get_text_hash(self, text: str) -> str:
        """Generate hash for text."""
        return hashlib.md5(text.encode('utf-8')).hexdigest()
    
    def _is_expired(self, entry: Dict[str, Any]) -> bool:
        """Check if cache entry is expired."""
        if self.ttl_seconds is None:
            return False
        return time.time() - entry['timestamp'] > self.ttl_seconds
    
    def _evict_expired(self) -> None:
        """Remove expired entries from cache."""
        if self.ttl_seconds is None:
            return
        
        current_time = time.time()
        expired_keys = [
            key for key, entry in self.cache.items()
            if current_time - entry['timestamp'] > self.ttl_seconds
        ]
        
        for key in expired_keys:
            del self.cache[key]
        
        if expired_keys:
            logger.debug(f"Evicted {len(expired_keys)} expired cache entries")
    
    def get(self, text: str) -> Optional[List[float]]:
        """Get embedding from cache.
        
        Args:
            text: Text to get embedding for
            
        Returns:
            Cached embedding or None if not found/expired
        """
        text_hash = self._get_text_hash(text)
        
        if text_hash in self.cache:
            entry = self.cache[text_hash]
            
            # Check if expired
            if self._is_expired(entry):
                del self.cache[text_hash]
                self._misses += 1
                return None
            
            # Move to end (most recently used)
            self.cache.move_to_end(text_hash)
            self._hits += 1
            return entry['embedding']
        
        self._misses += 1
        return None
    
    def set(self, text: str, embedding: List[float]) -> None:
        """Set embedding in cache.
        
        Args:
            text: Text key
            embedding: Embedding vector to cache
        """
        text_hash = self._get_text_hash(text)
        
        # Remove expired entries periodically
        if len(self.cache) % 100 == 0:  # Check every 100 operations
            self._evict_expired()
        
        # Remove oldest entry if cache is full
        if len(self.cache) >= self.max_size and text_hash not in self.cache:
            oldest_key, _ = self.cache.popitem(last=False)
            logger.debug(f"Evicted oldest cache entry: {oldest_key[:8]}...")
        
        # Add or update entry
        entry = {
            'embedding': embedding,
            'timestamp': time.time()
        }
        
        if text_hash in self.cache:
            # Update existing entry
            self.cache[text_hash] = entry
            self.cache.move_to_end(text_hash)
        else:
            # Add new entry
            self.cache[text_hash] = entry
    
    def remove(self, text: str) -> bool:
        """Remove embedding from cache.
        
        Args:
            text: Text key to remove
            
        Returns:
            True if entry was removed, False if not found
        """
        text_hash = self._get_text_hash(text)
        if text_hash in self.cache:
            del self.cache[text_hash]
            return True
        return False
    
    def clear(self) -> None:
        """Clear all cache entries."""
        self.cache.clear()
        self._hits = 0
        self._misses = 0
        logger.info("Embedding cache cleared")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics.
        
        Returns:
            Dictionary with cache statistics
        """
        total_requests = self._hits + self._misses
        hit_ratio = self._hits / max(1, total_requests)
        
        return {
            'size': len(self.cache),
            'max_size': self.max_size,
            'hits': self._hits,
            'misses': self._misses,
            'hit_ratio': hit_ratio,
            'ttl_seconds': self.ttl_seconds
        }
    
    def resize(self, new_max_size: int) -> None:
        """Resize cache to new maximum size.
        
        Args:
            new_max_size: New maximum cache size
        """
        self.max_size = new_max_size
        
        # Remove oldest entries if current size exceeds new max
        while len(self.cache) > new_max_size:
            oldest_key, _ = self.cache.popitem(last=False)
            logger.debug(f"Evicted entry during resize: {oldest_key[:8]}...")
        
        logger.info(f"Cache resized to max_size={new_max_size}")
    
    def __len__(self) -> int:
        """Get current cache size."""
        return len(self.cache)
    
    def __contains__(self, text: str) -> bool:
        """Check if text is in cache (without updating LRU order)."""
        text_hash = self._get_text_hash(text)
        if text_hash in self.cache:
            return not self._is_expired(self.cache[text_hash])
        return False


class GlobalEmbeddingCache:
    """Global singleton cache for embeddings."""
    
    _instance: Optional[EmbeddingCache] = None
    
    @classmethod
    def get_instance(cls, max_size: int = 1000, ttl_seconds: Optional[int] = None) -> EmbeddingCache:
        """Get global cache instance.
        
        Args:
            max_size: Maximum cache size (only used on first call)
            ttl_seconds: TTL in seconds (only used on first call)
            
        Returns:
            Global EmbeddingCache instance
        """
        if cls._instance is None:
            cls._instance = EmbeddingCache(max_size, ttl_seconds)
            logger.info(f"Created global embedding cache with max_size={max_size}, ttl={ttl_seconds}")
        return cls._instance
    
    @classmethod
    def clear_instance(cls) -> None:
        """Clear global cache instance."""
        if cls._instance is not None:
            cls._instance.clear()
            cls._instance = None
            logger.info("Cleared global embedding cache instance")