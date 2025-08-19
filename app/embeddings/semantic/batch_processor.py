"""Batch processor for efficient document chunking."""

import asyncio
from typing import List, Optional, Callable, Any, Dict
from concurrent.futures import ThreadPoolExecutor
import time

from ...utils.logger import get_logger

logger = get_logger(__name__)


class BatchProcessor:
    """Batch processor for handling multiple documents efficiently."""
    
    def __init__(
        self,
        batch_size: int = 10,
        max_workers: Optional[int] = None,
        timeout_seconds: float = 300.0
    ):
        """Initialize batch processor.
        
        Args:
            batch_size: Number of documents to process in each batch
            max_workers: Maximum number of worker threads (None for auto)
            timeout_seconds: Timeout for batch processing
        """
        self.batch_size = batch_size
        self.max_workers = max_workers
        self.timeout_seconds = timeout_seconds
        self._executor: Optional[ThreadPoolExecutor] = None
        self._stats = {
            'total_processed': 0,
            'total_batches': 0,
            'total_time': 0.0,
            'errors': 0
        }
    
    def _get_executor(self) -> ThreadPoolExecutor:
        """Get or create thread pool executor."""
        if self._executor is None:
            self._executor = ThreadPoolExecutor(max_workers=self.max_workers)
        return self._executor
    
    async def process_documents_batch(
        self,
        documents: List[str],
        processor_func: Callable[[str], Any],
        progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> List[Any]:
        """Process documents in batches.
        
        Args:
            documents: List of documents to process
            processor_func: Function to process each document
            progress_callback: Optional callback for progress updates (current, total)
            
        Returns:
            List of processing results
        """
        if not documents:
            return []
        
        start_time = time.time()
        results = []
        total_docs = len(documents)
        processed_count = 0
        
        logger.info(f"Starting batch processing of {total_docs} documents with batch_size={self.batch_size}")
        
        try:
            # Process documents in batches
            for i in range(0, total_docs, self.batch_size):
                batch = documents[i:i + self.batch_size]
                batch_start_time = time.time()
                
                # Process batch concurrently
                batch_results = await self._process_batch(
                    batch, processor_func
                )
                
                results.extend(batch_results)
                processed_count += len(batch)
                
                batch_time = time.time() - batch_start_time
                logger.debug(
                    f"Processed batch {i//self.batch_size + 1}/{(total_docs-1)//self.batch_size + 1} "
                    f"({len(batch)} docs) in {batch_time:.2f}s"
                )
                
                # Update progress
                if progress_callback:
                    progress_callback(processed_count, total_docs)
                
                self._stats['total_batches'] += 1
            
            total_time = time.time() - start_time
            self._stats['total_processed'] += total_docs
            self._stats['total_time'] += total_time
            
            logger.info(
                f"Completed batch processing: {total_docs} documents in {total_time:.2f}s "
                f"({total_docs/total_time:.1f} docs/sec)"
            )
            
            return results
            
        except Exception as e:
            self._stats['errors'] += 1
            logger.error(f"Batch processing failed: {e}")
            raise
    
    async def _process_batch(
        self,
        batch: List[str],
        processor_func: Callable[[str], Any]
    ) -> List[Any]:
        """Process a single batch of documents.
        
        Args:
            batch: Batch of documents to process
            processor_func: Processing function
            
        Returns:
            List of processing results
        """
        try:
            # Create tasks for concurrent processing
            tasks = []
            for doc in batch:
                if asyncio.iscoroutinefunction(processor_func):
                    # Async function
                    task = processor_func(doc)
                else:
                    # Sync function - run in executor
                    executor = self._get_executor()
                    task = asyncio.get_event_loop().run_in_executor(
                        executor, processor_func, doc
                    )
                tasks.append(task)
            
            # Wait for all tasks to complete with timeout
            results = await asyncio.wait_for(
                asyncio.gather(*tasks, return_exceptions=True),
                timeout=self.timeout_seconds
            )
            
            # Handle exceptions in results
            processed_results = []
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    logger.error(f"Error processing document {i} in batch: {result}")
                    self._stats['errors'] += 1
                    processed_results.append(None)  # or some default value
                else:
                    processed_results.append(result)
            
            return processed_results
            
        except asyncio.TimeoutError:
            logger.error(f"Batch processing timed out after {self.timeout_seconds}s")
            self._stats['errors'] += 1
            raise
        except Exception as e:
            logger.error(f"Error in batch processing: {e}")
            self._stats['errors'] += 1
            raise
    
    async def process_with_chunking(
        self,
        documents: List[str],
        chunker_func: Callable[[str], List[str]],
        progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> List[List[str]]:
        """Process documents with chunking function.
        
        Args:
            documents: List of documents to chunk
            chunker_func: Function that chunks a document into list of chunks
            progress_callback: Optional progress callback
            
        Returns:
            List of chunk lists (one per document)
        """
        return await self.process_documents_batch(
            documents, chunker_func, progress_callback
        )
    
    def get_stats(self) -> Dict[str, Any]:
        """Get processing statistics.
        
        Returns:
            Dictionary with processing stats
        """
        avg_time_per_doc = (
            self._stats['total_time'] / max(1, self._stats['total_processed'])
        )
        avg_time_per_batch = (
            self._stats['total_time'] / max(1, self._stats['total_batches'])
        )
        
        return {
            'total_processed': self._stats['total_processed'],
            'total_batches': self._stats['total_batches'],
            'total_time': self._stats['total_time'],
            'errors': self._stats['errors'],
            'avg_time_per_doc': avg_time_per_doc,
            'avg_time_per_batch': avg_time_per_batch,
            'batch_size': self.batch_size,
            'max_workers': self.max_workers
        }
    
    def reset_stats(self) -> None:
        """Reset processing statistics."""
        self._stats = {
            'total_processed': 0,
            'total_batches': 0,
            'total_time': 0.0,
            'errors': 0
        }
        logger.info("Batch processor stats reset")
    
    def close(self) -> None:
        """Close the batch processor and cleanup resources."""
        if self._executor is not None:
            self._executor.shutdown(wait=True)
            self._executor = None
        logger.info("Batch processor closed")
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()


class ProgressTracker:
    """Simple progress tracker for batch processing."""
    
    def __init__(self, total: int, log_interval: int = 10):
        """Initialize progress tracker.
        
        Args:
            total: Total number of items to process
            log_interval: Log progress every N percent
        """
        self.total = total
        self.log_interval = log_interval
        self.current = 0
        self.start_time = time.time()
        self.last_logged_percent = 0
    
    def update(self, current: int, total: int) -> None:
        """Update progress.
        
        Args:
            current: Current number of processed items
            total: Total number of items
        """
        self.current = current
        self.total = total
        
        if total == 0:
            return
        
        percent = int((current / total) * 100)
        
        # Log progress at intervals
        if percent >= self.last_logged_percent + self.log_interval or current == total:
            elapsed = time.time() - self.start_time
            rate = current / max(elapsed, 0.001)  # Avoid division by zero
            
            if current == total:
                logger.info(f"Progress: {percent}% ({current}/{total}) - Completed in {elapsed:.1f}s")
            else:
                eta = (total - current) / max(rate, 0.001)
                logger.info(
                    f"Progress: {percent}% ({current}/{total}) - "
                    f"Rate: {rate:.1f} items/sec - ETA: {eta:.1f}s"
                )
            
            self.last_logged_percent = percent