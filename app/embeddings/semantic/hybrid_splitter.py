"""Hybrid text splitter combining recursive character splitting with semantic chunking."""

import asyncio
from typing import List, Dict, Any, Optional, Tuple
import time
from dataclasses import dataclass

from .similarity_calculator import SemanticSimilarityCalculator
from .cache import GlobalEmbeddingCache
from .batch_processor import BatchProcessor
from ...utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class ChunkingConfig:
    """Configuration for hybrid chunking."""
    # Base chunking settings
    chunk_size: int = 1000
    chunk_overlap: int = 200
    separators: List[str] = None
    
    # Semantic chunking settings
    semantic_threshold: float = 0.75
    enable_semantic_fallback: bool = True
    max_semantic_chunk_size: int = 2000
    min_chunk_size: int = 100
    
    # Performance settings
    batch_size: int = 10
    cache_enabled: bool = True
    cache_ttl: int = 3600  # 1 hour
    
    def __post_init__(self):
        """Set default separators if not provided."""
        if self.separators is None:
            self.separators = [
                "\n##SECTION_START_",  # Section markers
                "\n\n",              # Double newlines
                "。\n",               # Chinese sentence end
                ".\n\n",               # English paragraph end
                ".\n",                # English sentence end
                "。\n\n",              # Chinese paragraph end
            ]


class HybridTextSplitter:
    """Hybrid text splitter with recursive character splitting and semantic fallback."""
    
    def __init__(
        self,
        config: Optional[ChunkingConfig] = None,
        similarity_calculator: Optional[SemanticSimilarityCalculator] = None
    ):
        """Initialize hybrid text splitter.
        
        Args:
            config: Chunking configuration
            similarity_calculator: Semantic similarity calculator
        """
        self.config = config or ChunkingConfig()
        self.similarity_calculator = similarity_calculator or SemanticSimilarityCalculator()
        self.batch_processor = BatchProcessor(batch_size=self.config.batch_size)
        
        # Initialize cache if enabled
        if self.config.cache_enabled:
            self.cache = GlobalEmbeddingCache.get_instance()
            self.cache.resize(new_max_size=1000)  # Adjust as needed
        else:
            self.cache = None
        
        self._stats = {
            'total_chunks': 0,
            'semantic_merges': 0,
            'recursive_splits': 0,
            'cache_hits': 0,
            'processing_time': 0.0
        }
        
        logger.info(f"HybridTextSplitter initialized with config: {self.config}")
    
    async def split_text(self, text: str) -> List[str]:
        """Split text using hybrid approach.
        
        Args:
            text: Text to split
            
        Returns:
            List of text chunks
        """
        if not text or not text.strip():
            return []
        
        start_time = time.time()
        
        try:
            # Step 1: Recursive character splitting
            base_chunks = self._recursive_split(text)
            logger.debug(f"Recursive splitting produced {len(base_chunks)} chunks")
            
            # Step 2: Apply semantic optimization if enabled
            if self.config.enable_semantic_fallback and len(base_chunks) > 1:
                optimized_chunks = await self._semantic_optimize(base_chunks)
                logger.debug(f"Semantic optimization produced {len(optimized_chunks)} chunks")
            else:
                optimized_chunks = base_chunks
            
            # Step 3: Final validation and cleanup
            final_chunks = self._validate_chunks(optimized_chunks)
            
            # Update statistics
            processing_time = time.time() - start_time
            self._stats['total_chunks'] += len(final_chunks)
            self._stats['processing_time'] += processing_time
            
            logger.info(
                f"Text splitting completed: {len(final_chunks)} chunks in {processing_time:.3f}s"
            )
            
            return final_chunks
            
        except Exception as e:
            logger.error(f"Error in hybrid text splitting: {e}")
            # Fallback to simple recursive splitting
            return self._recursive_split(text)
    
    def _recursive_split(self, text: str) -> List[str]:
        """Perform recursive character splitting.
        
        Args:
            text: Text to split
            
        Returns:
            List of text chunks
        """
        chunks = []
        current_text = text
        
        while len(current_text) > self.config.chunk_size:
            # Find the best separator
            split_point = self._find_split_point(current_text)
            
            if split_point == -1:
                # No separator found, force split at chunk_size
                split_point = self.config.chunk_size
            
            # Extract chunk with overlap consideration
            chunk = current_text[:split_point].strip()
            if chunk:
                chunks.append(chunk)
            
            # Move to next position with overlap
            overlap_start = max(0, split_point - self.config.chunk_overlap)
            current_text = current_text[overlap_start:]
            
            self._stats['recursive_splits'] += 1
        
        # Add remaining text
        if current_text.strip():
            chunks.append(current_text.strip())
        
        return chunks
    
    def _find_split_point(self, text: str) -> int:
        """Find the best split point using configured separators.
        
        Args:
            text: Text to find split point in
            
        Returns:
            Split point index, -1 if no good split point found
        """
        max_search_length = min(len(text), self.config.chunk_size + self.config.chunk_overlap)
        
        # Try each separator in order of preference
        for separator in self.config.separators:
            # Find the last occurrence of separator within search range
            search_text = text[:max_search_length]
            last_index = search_text.rfind(separator)
            
            if last_index != -1 and last_index >= self.config.min_chunk_size:
                return last_index + len(separator)
        
        return -1
    
    async def _semantic_optimize(self, chunks: List[str]) -> List[str]:
        """Optimize chunks using semantic similarity.
        
        Args:
            chunks: List of chunks to optimize
            
        Returns:
            Optimized list of chunks
        """
        if len(chunks) <= 1:
            return chunks
        
        optimized_chunks = []
        current_chunk = chunks[0]
        
        for i in range(1, len(chunks)):
            next_chunk = chunks[i]
            
            # Check if chunks should be merged based on semantic similarity
            should_merge = await self._should_merge_chunks(current_chunk, next_chunk)
            
            if should_merge:
                # Merge chunks
                merged_chunk = self._merge_chunks(current_chunk, next_chunk)
                
                # Check if merged chunk is not too large
                if len(merged_chunk) <= self.config.max_semantic_chunk_size:
                    current_chunk = merged_chunk
                    self._stats['semantic_merges'] += 1
                    logger.debug(f"Merged chunks: similarity above threshold")
                    continue
            
            # Don't merge - add current chunk and move to next
            optimized_chunks.append(current_chunk)
            current_chunk = next_chunk
        
        # Add the last chunk
        optimized_chunks.append(current_chunk)
        
        return optimized_chunks
    
    async def _should_merge_chunks(self, chunk1: str, chunk2: str) -> bool:
        """Determine if two chunks should be merged based on semantic similarity.
        
        Args:
            chunk1: First chunk
            chunk2: Second chunk
            
        Returns:
            True if chunks should be merged
        """
        try:
            # Use cache if available
            cache_key = None
            if self.cache:
                cache_key = f"merge_{hash(chunk1)}_{hash(chunk2)}"
                cached_result = self.cache.get(cache_key)
                if cached_result is not None:
                    self._stats['cache_hits'] += 1
                    return cached_result > self.config.semantic_threshold
            
            # Calculate semantic similarity
            similarity = await self.similarity_calculator.calculate_similarity(
                chunk1, chunk2
            )
            
            # Cache the result
            if self.cache and cache_key:
                self.cache.set(cache_key, similarity, ttl=self.config.cache_ttl)
            
            should_merge = similarity >= self.config.semantic_threshold
            logger.debug(
                f"Semantic similarity: {similarity:.3f}, threshold: {self.config.semantic_threshold}, "
                f"merge: {should_merge}"
            )
            
            return should_merge
            
        except Exception as e:
            logger.error(f"Error calculating semantic similarity: {e}")
            return False
    
    def _merge_chunks(self, chunk1: str, chunk2: str) -> str:
        """Merge two chunks intelligently.
        
        Args:
            chunk1: First chunk
            chunk2: Second chunk
            
        Returns:
            Merged chunk
        """
        # Simple merge with overlap handling
        # TODO: Implement more sophisticated overlap detection
        
        # Check for potential overlap at the end of chunk1 and start of chunk2
        overlap_size = min(len(chunk1), len(chunk2), self.config.chunk_overlap)
        
        for i in range(overlap_size, 0, -1):
            if chunk1[-i:] == chunk2[:i]:
                # Found overlap, merge without duplication
                return chunk1 + chunk2[i:]
        
        # No overlap found, simple concatenation with separator
        separator = "\n" if not chunk1.endswith("\n") and not chunk2.startswith("\n") else ""
        return chunk1 + separator + chunk2
    
    def _validate_chunks(self, chunks: List[str]) -> List[str]:
        """Validate and clean up chunks.
        
        Args:
            chunks: List of chunks to validate
            
        Returns:
            Validated list of chunks
        """
        validated_chunks = []
        
        for chunk in chunks:
            # Clean up chunk
            cleaned_chunk = chunk.strip()
            
            # Skip empty or too small chunks
            if len(cleaned_chunk) < self.config.min_chunk_size:
                continue
            
            # Truncate if too large (shouldn't happen but safety check)
            if len(cleaned_chunk) > self.config.max_semantic_chunk_size:
                cleaned_chunk = cleaned_chunk[:self.config.max_semantic_chunk_size]
                logger.warning(f"Truncated oversized chunk to {self.config.max_semantic_chunk_size} chars")
            
            validated_chunks.append(cleaned_chunk)
        
        return validated_chunks
    
    async def split_documents(self, documents: List[str]) -> List[List[str]]:
        """Split multiple documents using batch processing.
        
        Args:
            documents: List of documents to split
            
        Returns:
            List of chunk lists (one per document)
        """
        if not documents:
            return []
        
        logger.info(f"Starting batch document splitting for {len(documents)} documents")
        
        # Use batch processor for efficient processing
        results = await self.batch_processor.process_with_chunking(
            documents,
            self.split_text,
            progress_callback=self._log_progress
        )
        
        return results
    
    def _log_progress(self, current: int, total: int) -> None:
        """Log processing progress.
        
        Args:
            current: Current number of processed documents
            total: Total number of documents
        """
        percent = int((current / total) * 100) if total > 0 else 0
        logger.info(f"Document splitting progress: {percent}% ({current}/{total})")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get splitting statistics.
        
        Returns:
            Dictionary with splitting stats
        """
        batch_stats = self.batch_processor.get_stats()
        
        return {
            **self._stats,
            'batch_stats': batch_stats,
            'config': {
                'chunk_size': self.config.chunk_size,
                'chunk_overlap': self.config.chunk_overlap,
                'semantic_threshold': self.config.semantic_threshold,
                'separators': self.config.separators
            }
        }
    
    def reset_stats(self) -> None:
        """Reset splitting statistics."""
        self._stats = {
            'total_chunks': 0,
            'semantic_merges': 0,
            'recursive_splits': 0,
            'cache_hits': 0,
            'processing_time': 0.0
        }
        self.batch_processor.reset_stats()
        logger.info("HybridTextSplitter stats reset")
    
    def close(self) -> None:
        """Close the splitter and cleanup resources."""
        self.batch_processor.close()
        if self.cache:
            self.cache.clear()
        logger.info("HybridTextSplitter closed")
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()