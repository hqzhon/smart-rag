"""Multi-Field BM25 Retriever for Advanced RAG

This module provides enhanced BM25 retrieval capabilities with support for
multiple field indexing (keywords, summary, content) and field-specific scoring.
"""

from typing import List, Dict, Any, Optional, Union
import jieba
from rank_bm25 import BM25Okapi
from app.utils.logger import setup_logger
from app.retrieval.advanced_config import RetrievalPath
import time
import asyncio
from concurrent.futures import ThreadPoolExecutor

logger = setup_logger(__name__)


class FieldBM25Index:
    """Single field BM25 index wrapper"""
    
    def __init__(self, field_name: str, documents: List[Dict[str, Any]], 
                 tokenizer_func=None):
        """
        Initialize BM25 index for a specific field
        
        Args:
            field_name: Name of the field to index
            documents: List of documents
            tokenizer_func: Custom tokenizer function, defaults to jieba.cut
        """
        self.field_name = field_name
        self.documents = documents
        self.doc_map = {doc['id']: doc for doc in documents}
        self.tokenizer = tokenizer_func or (lambda text: list(jieba.cut(text)))
        
        # Build tokenized corpus for this field
        self.tokenized_corpus = self._build_corpus()
        
        # Create BM25 index
        if self.tokenized_corpus:
            self.bm25 = BM25Okapi(self.tokenized_corpus)
            logger.info(f"BM25 index created for field '{field_name}' with {len(self.tokenized_corpus)} documents")
        else:
            self.bm25 = None
            logger.warning(f"No valid documents found for field '{field_name}'")
    
    def _build_corpus(self) -> List[List[str]]:
        """Build tokenized corpus for the specific field"""
        corpus = []
        
        for doc in self.documents:
            text = self._extract_field_text(doc)
            if text:
                tokens = self.tokenizer(text)
                corpus.append(tokens)
            else:
                # Add empty token list for documents without this field
                corpus.append([])
        
        return corpus
    
    def _extract_field_text(self, doc: Dict[str, Any]) -> str:
        """Extract text from document for the specific field"""
        if self.field_name == 'content':
            return doc.get('content', '')
        elif self.field_name == 'keywords':
            metadata = doc.get('metadata', {})
            keywords = metadata.get('keywords', [])
            if isinstance(keywords, list):
                return ' '.join(keywords)
            elif isinstance(keywords, str):
                return keywords
            return ''
        elif self.field_name == 'summary':
            metadata = doc.get('metadata', {})
            return metadata.get('summary', '')
        else:
            # Generic field extraction from metadata
            metadata = doc.get('metadata', {})
            return str(metadata.get(self.field_name, ''))
    
    def search(self, query: str, top_k: int = 50) -> List[Dict[str, Any]]:
        """Search documents using BM25 for this field"""
        if not self.bm25 or not self.documents:
            return []
        
        tokenized_query = self.tokenizer(query)
        if not tokenized_query:
            return []
        
        # Get BM25 scores
        doc_scores = self.bm25.get_scores(tokenized_query)
        
        # Create scored results
        results = []
        for i, (doc, score) in enumerate(zip(self.documents, doc_scores)):
            if score > 0:  # Only include documents with positive scores
                result = doc.copy()
                result['bm25_score'] = float(score)
                result['field_source'] = self.field_name
                results.append(result)
        
        # Sort by score and return top_k
        results.sort(key=lambda x: x['bm25_score'], reverse=True)
        return results[:top_k]
    
    def get_scores(self, query: str) -> Dict[str, float]:
        """Get BM25 scores for all documents"""
        if not self.bm25:
            return {}
        
        tokenized_query = self.tokenizer(query)
        if not tokenized_query:
            return {}
        
        doc_scores = self.bm25.get_scores(tokenized_query)
        return {doc['id']: float(score) for doc, score in zip(self.documents, doc_scores)}


class MultiFieldBM25Retriever:
    """Enhanced BM25 retriever with multi-field support
    
    Supports independent BM25 indexing on keywords, summary, and content fields
    with field-specific scoring and retrieval.
    """
    
    def __init__(self, documents: List[Dict[str, Any]], 
                 fields: Optional[List[str]] = None,
                 custom_tokenizer: Optional[callable] = None):
        """
        Initialize multi-field BM25 retriever
        
        Args:
            documents: List of document dictionaries
            fields: List of fields to index (defaults to ['keywords', 'summary', 'content'])
            custom_tokenizer: Custom tokenizer function
        """
        self.documents = documents
        self.fields = fields or ['keywords', 'summary', 'content']
        self.tokenizer = custom_tokenizer or (lambda text: list(jieba.cut(text)))
        
        # Build field indexes
        self.field_indexes = {}
        self._build_indexes()
        
        # Performance tracking
        self.search_stats = {
            'total_searches': 0,
            'field_search_times': {field: [] for field in self.fields},
            'avg_search_time': 0.0
        }
        
        logger.info(f"MultiFieldBM25Retriever initialized with {len(documents)} documents and fields: {self.fields}")
    
    def _build_indexes(self):
        """Build BM25 indexes for all specified fields"""
        for field in self.fields:
            try:
                start_time = time.time()
                self.field_indexes[field] = FieldBM25Index(
                    field_name=field,
                    documents=self.documents,
                    tokenizer_func=self.tokenizer
                )
                build_time = time.time() - start_time
                logger.info(f"Built BM25 index for field '{field}' in {build_time:.3f}s")
            except Exception as e:
                logger.error(f"Failed to build index for field '{field}': {str(e)}")
                self.field_indexes[field] = None
    
    def search_field(self, query: str, field: str, top_k: int = 50) -> List[Dict[str, Any]]:
        """Search using BM25 on a specific field
        
        Args:
            query: Search query
            field: Field name to search ('keywords', 'summary', 'content')
            top_k: Number of top results to return
            
        Returns:
            List of documents with BM25 scores
        """
        if field not in self.field_indexes or self.field_indexes[field] is None:
            logger.warning(f"No index available for field '{field}'")
            return []
        
        start_time = time.time()
        
        try:
            results = self.field_indexes[field].search(query, top_k)
            
            # Update performance stats
            search_time = time.time() - start_time
            self.search_stats['field_search_times'][field].append(search_time)
            self.search_stats['total_searches'] += 1
            
            logger.debug(f"Field '{field}' search completed in {search_time:.3f}s, found {len(results)} results")
            return results
            
        except Exception as e:
            logger.error(f"Error searching field '{field}': {str(e)}")
            return []
    
    async def search_field_async(self, query: str, field: str, top_k: int = 50) -> List[Dict[str, Any]]:
        """Async wrapper for field search"""
        loop = asyncio.get_event_loop()
        with ThreadPoolExecutor() as executor:
            return await loop.run_in_executor(
                executor, self.search_field, query, field, top_k
            )
    
    def search_all_fields(self, query: str, top_k_per_field: int = 50) -> Dict[str, List[Dict[str, Any]]]:
        """Search all fields and return results grouped by field
        
        Args:
            query: Search query
            top_k_per_field: Number of top results per field
            
        Returns:
            Dictionary mapping field names to result lists
        """
        results = {}
        
        for field in self.fields:
            if field in self.field_indexes and self.field_indexes[field] is not None:
                field_results = self.search_field(query, field, top_k_per_field)
                results[field] = field_results
            else:
                results[field] = []
        
        return results
    
    async def search_all_fields_async(self, query: str, top_k_per_field: int = 50, 
                                    max_concurrent: int = 3) -> Dict[str, List[Dict[str, Any]]]:
        """Async search all fields concurrently
        
        Args:
            query: Search query
            top_k_per_field: Number of top results per field
            max_concurrent: Maximum concurrent field searches
            
        Returns:
            Dictionary mapping field names to result lists
        """
        # Create semaphore to limit concurrency
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def search_with_semaphore(field: str):
            async with semaphore:
                return await self.search_field_async(query, field, top_k_per_field)
        
        # Create tasks for all fields
        tasks = []
        for field in self.fields:
            if field in self.field_indexes and self.field_indexes[field] is not None:
                task = asyncio.create_task(search_with_semaphore(field))
                tasks.append((field, task))
        
        # Wait for all tasks to complete
        results = {}
        for field, task in tasks:
            try:
                field_results = await task
                results[field] = field_results
            except Exception as e:
                logger.error(f"Error in async search for field '{field}': {str(e)}")
                results[field] = []
        
        # Add empty results for fields without indexes
        for field in self.fields:
            if field not in results:
                results[field] = []
        
        return results
    
    def get_field_scores(self, query: str, field: str) -> Dict[str, float]:
        """Get BM25 scores for all documents in a specific field"""
        if field not in self.field_indexes or self.field_indexes[field] is None:
            return {}
        
        return self.field_indexes[field].get_scores(query)
    
    def get_all_field_scores(self, query: str) -> Dict[str, Dict[str, float]]:
        """Get BM25 scores for all documents across all fields"""
        all_scores = {}
        
        for field in self.fields:
            if field in self.field_indexes and self.field_indexes[field] is not None:
                all_scores[field] = self.get_field_scores(query, field)
            else:
                all_scores[field] = {}
        
        return all_scores
    
    def get_available_fields(self) -> List[str]:
        """Get list of available indexed fields"""
        return [field for field in self.fields 
                if field in self.field_indexes and self.field_indexes[field] is not None]
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get performance statistics"""
        stats = self.search_stats.copy()
        
        # Calculate average search times per field
        for field, times in stats['field_search_times'].items():
            if times:
                stats[f'avg_{field}_search_time'] = sum(times) / len(times)
                stats[f'max_{field}_search_time'] = max(times)
                stats[f'min_{field}_search_time'] = min(times)
            else:
                stats[f'avg_{field}_search_time'] = 0.0
                stats[f'max_{field}_search_time'] = 0.0
                stats[f'min_{field}_search_time'] = 0.0
        
        # Calculate overall average
        all_times = []
        for times in stats['field_search_times'].values():
            all_times.extend(times)
        
        if all_times:
            stats['overall_avg_search_time'] = sum(all_times) / len(all_times)
        else:
            stats['overall_avg_search_time'] = 0.0
        
        return stats
    
    def reset_stats(self):
        """Reset performance statistics"""
        self.search_stats = {
            'total_searches': 0,
            'field_search_times': {field: [] for field in self.fields},
            'avg_search_time': 0.0
        }
    
    def update_documents(self, new_documents: List[Dict[str, Any]]):
        """Update the retriever with new documents
        
        Args:
            new_documents: New list of documents to index
        """
        logger.info(f"Updating MultiFieldBM25Retriever with {len(new_documents)} documents")
        
        self.documents = new_documents
        self.reset_stats()
        
        # Rebuild all indexes
        self._build_indexes()
        
        logger.info("MultiFieldBM25Retriever update completed")
    
    def retrieve(self, query: str, top_k: int = 10) -> List[Dict[str, Any]]:
        """Retrieve documents using all fields (compatibility method)
        
        Args:
            query: Search query
            top_k: Number of top results to return
            
        Returns:
            List of documents with scores
        """
        results = self.search_all_fields(query, top_k_per_field=top_k)
        
        # Flatten results from all fields and deduplicate by document ID
        all_results = []
        seen_ids = set()
        
        for field, field_results in results.items():
            for result in field_results:
                doc_id = result.get('id')
                if doc_id and doc_id not in seen_ids:
                    seen_ids.add(doc_id)
                    # Rename bm25_score to score for compatibility
                    if 'bm25_score' in result:
                        result['score'] = result['bm25_score']
                    all_results.append(result)
        
        # Sort by score and return top_k
        all_results.sort(key=lambda x: x.get('score', 0), reverse=True)
        return all_results[:top_k]


# Compatibility wrapper for existing code
class RankBM25Retriever(MultiFieldBM25Retriever):
    """Backward compatibility wrapper for existing RankBM25Retriever
    
    This class maintains the same interface as the original RankBM25Retriever
    while providing enhanced multi-field capabilities.
    """
    
    def __init__(self, documents: List[Dict[str, Any]]):
        """Initialize with backward compatibility"""
        # Initialize with keywords field as primary (matching original behavior)
        super().__init__(documents, fields=['keywords'])
        
        # Store original documents for compatibility
        self.doc_map = {doc['id']: doc for doc in documents}
        
        logger.info(f"RankBM25Retriever (compatibility mode) initialized with {len(documents)} documents")
    
    def get_top_n(self, query: str, n: int = 5) -> List[Dict[str, Any]]:
        """Get top N documents (backward compatibility method)"""
        results = self.search_field(query, 'keywords', n)
        
        # Remove the added fields to maintain original interface
        clean_results = []
        for result in results:
            clean_result = {k: v for k, v in result.items() 
                          if k not in ['bm25_score', 'field_source']}
            clean_results.append(clean_result)
        
        return clean_results
    
    def get_scores(self, query: str) -> Dict[str, float]:
        """Get BM25 scores for all documents (backward compatibility method)"""
        return self.get_field_scores(query, 'keywords')