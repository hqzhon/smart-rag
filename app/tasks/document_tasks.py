"""
定义文档处理相关的Celery任务
"""
import asyncio
from app.celery_app import celery_app
from app.services.document_service import DocumentService
from app.utils.logger import setup_logger

logger = setup_logger(__name__)

@celery_app.task(name='app.tasks.document_tasks.process_document_task')
def process_document_task(document_id: str):
    """
    Celery后台任务，用于处理上传的文档。

    Args:
        document_id: 需要处理的文档ID。
    """
    # --- 诊断探针 ---
    print(f"--- CELERY TASK RECEIVED: process_document_task for doc_id: {document_id} ---")
    # ------------------
    logger.info(f"[Celery Task] 开始处理文档: {document_id}")
    
    async def main():
        # 在异步环境中运行文档处理服务
        doc_service = DocumentService()
        await doc_service.async_init()
        
        # 从数据库获取文档对象
        document = await doc_service.get_document(document_id)
        if not document:
            logger.error(f"[Celery Task] 找不到文档: {document_id}")
            return

        await doc_service.process_document(document)

    try:
        # 运行异步主函数
        asyncio.run(main())
        logger.info(f"[Celery Task] 成功完成文档处理: {document_id}")
    except Exception as e:
        logger.error(f"[Celery Task] 文档处理失败: {document_id}, 错误: {e}", exc_info=True)
        # 可以在这里添加失败状态更新的逻辑
        # 例如:
        # doc_service = DocumentService()
        # asyncio.run(doc_service.update_document_status(document_id, 'failed', str(e)))
