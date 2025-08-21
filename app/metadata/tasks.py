# app/metadata/tasks.py
import asyncio
from typing import Optional
from app.metadata.processors.async_processor import AsyncMetadataProcessor
from app.storage.vector_store import VectorStore
from app.utils.logger import setup_logger
from app.core.config import get_settings

logger = setup_logger(__name__)

# 全局变量，用于缓存处理器实例
_metadata_processor: Optional[AsyncMetadataProcessor] = None

def get_metadata_processor() -> AsyncMetadataProcessor:
    """获取或创建AsyncMetadataProcessor实例"""
    global _metadata_processor
    if _metadata_processor is None:
        settings = get_settings()
        vector_store = VectorStore(
            collection_name=settings.chroma_collection_name,
            persist_directory=settings.chroma_persist_directory
        )
        _metadata_processor = AsyncMetadataProcessor(
            chroma_client=vector_store.client,
            collection_name=settings.chroma_collection_name
        )
        logger.info("AsyncMetadataProcessor实例已创建")
    return _metadata_processor

async def _generate_metadata_async(chunk_id: str, text: str, document_id: str):
    """异步执行元数据生成和更新的包装函数
    
    实现"先计算后更新"策略：
    1. 计算元数据（摘要、关键词、质量评估）
    2. 更新ChromaDB中已存储的文档块
    """
    metadata_processor = get_metadata_processor()
    
    if not metadata_processor.is_running:
        logger.info("AsyncMetadataProcessor尚未运行，正在启动...")
        await metadata_processor.start()
    
    logger.info(f"开始为块 {chunk_id} 计算元数据并更新ChromaDB...")
    
    try:
        # 调用update_chunk_in_chroma方法实现"先计算后更新"策略
        await metadata_processor.update_chunk_in_chroma(
            chunk_id=chunk_id, 
            text=text,
            document_id=document_id
        )
        logger.info(f"块 {chunk_id} 的元数据已成功计算并更新到ChromaDB")
    except Exception as e:
        logger.error(f"为块 {chunk_id} 计算元数据或更新ChromaDB时发生错误: {e}", exc_info=True)
        raise

def generate_metadata_for_chunk(chunk_id: str, text: str, document_id: str):
    """RQ Worker将调用的同步入口函数
    
    Args:
        chunk_id: 文本块的唯一标识符
        text: 文本块内容
        document_id: 文档ID
    """
    try:
        logger.info(f"开始处理块 {chunk_id} 的元数据生成任务")
        
        # RQ Worker是同步的，使用asyncio.run来执行异步逻辑
        asyncio.run(_generate_metadata_async(chunk_id, text, document_id))
        
        logger.info(f"块 {chunk_id} 的元数据生成任务已成功处理")
        
    except Exception as e:
        logger.error(f"处理块 {chunk_id} 时发生严重错误: {e}", exc_info=True)
        # 异常会被RQ捕获并放入失败队列
        raise

def cleanup_metadata_processor():
    """清理元数据处理器资源"""
    global _metadata_processor
    if _metadata_processor is not None:
        try:
            # 如果处理器正在运行，需要异步停止
            if _metadata_processor.is_running:
                asyncio.run(_metadata_processor.stop())
            logger.info("AsyncMetadataProcessor已清理")
        except Exception as e:
            logger.error(f"清理AsyncMetadataProcessor时发生错误: {e}")
        finally:
            _metadata_processor = None