from celery import current_app
from app.celery_app import app
from app.metadata.summarizers.lightweight_summarizer import LightweightSummaryGenerator
from app.metadata.extractors.keybert_extractor import KeyBERTExtractor
from app.storage.vector_store import VectorStore
import logging
import os
import asyncio
import concurrent.futures
from typing import Any, Coroutine

logger = logging.getLogger(__name__)

# Initialize components
summary_generator = None
keyword_extractor = None
vector_store = None

def run_async_safely(coro: Coroutine) -> Any:
    """
    安全地运行异步协程，避免事件循环冲突
    
    Args:
        coro: 要运行的协程
        
    Returns:
        协程的执行结果
    """
    try:
        # 检查是否已有运行的事件循环
        try:
            loop = asyncio.get_running_loop()
            # 如果有运行的循环，使用线程池执行新的事件循环
            def run_in_thread():
                # 在新线程中创建新的事件循环
                new_loop = asyncio.new_event_loop()
                asyncio.set_event_loop(new_loop)
                try:
                    return new_loop.run_until_complete(coro)
                finally:
                    new_loop.close()
                    
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(run_in_thread)
                return future.result(timeout=60)  # 60秒超时
        except RuntimeError:
            # 没有运行的循环，直接运行
            return asyncio.run(coro)
    except Exception as e:
        logger.error(f"异步执行失败: {e}")
        raise

def get_components():
    """获取组件实例（懒加载）"""
    global summary_generator, keyword_extractor, vector_store
    
    if summary_generator is None:
        summary_generator = LightweightSummaryGenerator()
    
    if keyword_extractor is None:
        keyword_extractor = KeyBERTExtractor()
    
    if vector_store is None:
        vector_store = VectorStore()
        # 同步初始化 VectorStore
        import asyncio
        try:
            # 检查是否已有运行的事件循环
            try:
                loop = asyncio.get_running_loop()
                # 如果有运行的循环，使用线程池执行
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(asyncio.run, vector_store.async_init())
                    future.result(timeout=30)  # 30秒超时
            except RuntimeError:
                # 没有运行的循环，创建新的
                asyncio.run(vector_store.async_init())
        except Exception as e:
            logger.error(f"Failed to initialize vector store: {e}")
    
    return summary_generator, keyword_extractor, vector_store

@app.task(bind=True, max_retries=3, default_retry_delay=60, queue='metadata')
def generate_metadata_for_chunk(self, chunk_id: str, content: str, document_id: str):
    """
    MVP Celery task for generating metadata (summary and keywords) for a text chunk.
    
    Args:
        chunk_id: Unique identifier for the chunk
        content: Text content to process
        document_id: Parent document identifier
    
    Returns:
        dict: Generated metadata with summary and keywords
    """
    try:
        logger.info(f"Processing chunk {chunk_id} for document {document_id}")
        
        # Get initialized components
        summary_gen, keyword_ext, vs = get_components()
        
        # Generate summary and keywords with fallback
        import asyncio
        
        # Try to generate summary, fallback to truncated content if API fails
        try:
            summary_result = run_async_safely(summary_gen.generate_summary(content))
            summary = summary_result.content if hasattr(summary_result, 'content') else str(summary_result)
        except Exception as e:
            logger.warning(f"Summary generation failed for chunk {chunk_id}: {e}")
            # Fallback: use first 200 characters as summary
            summary = content[:200] + "..." if len(content) > 200 else content
        
        # Try to extract keywords, fallback to simple extraction if fails
        try:
            keyword_result = run_async_safely(keyword_ext.extract_keywords(content))
            keywords = keyword_result.keywords if hasattr(keyword_result, 'keywords') else []
        except Exception as e:
            logger.warning(f"Keyword extraction failed for chunk {chunk_id}: {e}")
            # Fallback: simple keyword extraction using basic text processing
            import re
            words = re.findall(r'\b\w{3,}\b', content.lower())
            keywords = list(set(words))[:10]  # Take first 10 unique words
        
        # Prepare metadata
        metadata = {
            'summary': summary,
            'keywords': keywords,
            'chunk_id': chunk_id,
            'document_id': document_id
        }
        
        # Update ChromaDB with generated metadata
        try:
            success = run_async_safely(vs.update_document(
                chunk_id=chunk_id,
                keywords=','.join(keywords) if keywords else '',
                summary=summary
            ))
            if success:
                logger.info(f"Updated ChromaDB for document {document_id}, chunk {chunk_id}")
            else:
                logger.warning(f"Failed to update ChromaDB for document {document_id}, chunk {chunk_id}")
        except Exception as e:
            logger.warning(f"Failed to update ChromaDB for document {document_id}, chunk {chunk_id}: {e}")
            # Don't fail the task if ChromaDB update fails
        
        logger.info(f"Successfully processed chunk {chunk_id}")
        return metadata
        
    except Exception as exc:
        logger.error(f"Error processing chunk {chunk_id}: {exc}")
        
        # Retry logic
        if self.request.retries < self.max_retries:
            logger.info(f"Retrying chunk {chunk_id} (attempt {self.request.retries + 1})")
            raise self.retry(exc=exc)
        else:
            logger.error(f"Max retries exceeded for chunk {chunk_id}")
            raise exc

@app.task(queue='metadata')
def health_check():
    """Simple health check task"""
    try:
        summary_gen, keyword_ext, vs = get_components()
        return {
            'status': 'healthy',
            'components': {
                'summary_generator': summary_gen is not None,
                'keyword_extractor': keyword_ext is not None,
                'vector_store': vs is not None
            }
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {'status': 'unhealthy', 'error': str(e)}