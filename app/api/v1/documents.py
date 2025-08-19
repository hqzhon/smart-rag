"""
文档管理API
"""

import os
import uuid
from typing import Optional, List
from fastapi import APIRouter, UploadFile, File, BackgroundTasks, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import logging

from app.utils.logger import setup_logger
from app.models.document_models import Document
from app.services.document_service import DocumentService

logger = setup_logger(__name__)

router = APIRouter()


class DocumentUploadResponse(BaseModel):
    """文档上传响应模型"""
    session_id: str
    status: str
    filename: str
    message: str


@router.post("/documents/upload", response_model=DocumentUploadResponse)
async def upload_document(
    file: UploadFile = File(...), 
    background_tasks: BackgroundTasks = None
):
    """上传PDF文档"""
    from app.services.chat_service import ChatService
    
    try:
        # 初始化服务
        document_service = DocumentService()
        chat_service = ChatService()
        
        # 读取文件内容
        file_content = await file.read()
        
        # 上传文档
        document = await document_service.upload_document(
            file_content=file_content,
            filename=file.filename,
            content_type=file.content_type
        )
        
        # 后台处理文档
        if background_tasks:
            background_tasks.add_task(process_document_background, document, document_service)
        
        # 创建会话
        session_id = await chat_service.create_session()
        
        logger.info(f"文件上传成功: {file.filename}, 文档ID: {document.id}, 会话ID: {session_id}")
        
        return DocumentUploadResponse(
            session_id=session_id,
            status="uploaded",
            filename=document.filename,
            message="PDF上传成功，正在处理中..."
        )
        
    except Exception as e:
        logger.error(f"上传PDF时出错: {str(e)}")
        raise HTTPException(status_code=500, detail=f"上传PDF时出错: {str(e)}")


async def process_document_background(document: Document, document_service: DocumentService):
    """后台处理文档"""
    try:
        result = await document_service.process_document(document)
        logger.info(f"文档处理完成: {document.filename}")
    except Exception as e:
        logger.error(f"后台文档处理失败: {str(e)}")


@router.get("/documents")
async def get_documents():
    """获取所有文档列表"""
    from app.storage.database import get_db_manager
    db = get_db_manager()
    
    try:
        documents = db.list_documents(limit=100)
        
        # 转换为前端需要的格式
        result = []
        for doc in documents:
            result.append({
                "id": doc["id"],
                "name": doc["title"],
                "size": doc["file_size"] or 0,
                "uploadTime": doc["created_at"].isoformat() if doc["created_at"] else None,
                "type": doc["file_type"] or "pdf"
            })
        
        logger.info(f"获取文档列表成功，共 {len(result)} 个文档")
        return result
        
    except Exception as e:
        logger.error(f"获取文档列表时出错: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取文档列表时出错: {str(e)}")


@router.get("/documents/{document_id}")
async def get_document(document_id: str):
    """获取文档信息"""
    # 获取文档信息
    from app.storage.database import get_db_manager
    db = get_db_manager()
    
    document = db.get_document(document_id)
    if not document:
        raise HTTPException(status_code=404, detail="文档不存在")
    
    return {
        "document_id": document_id,
        "title": document["title"],
        "file_type": document["file_type"],
        "file_size": document["file_size"],
        "created_at": document["created_at"],
        "status": "active"
    }


@router.post("/documents/vectorize")
async def vectorize_documents():
    """触发增量向量化更新"""
    try:
        # 获取文档服务实例
        from app.main import document_service
        
        if not document_service:
            raise HTTPException(status_code=500, detail="文档服务未初始化")
        
        # 执行增量向量化
        updated_count = await document_service.update_vectorization_for_new_documents()
        
        return {
            "status": "success",
            "message": f"增量向量化完成，共处理 {updated_count} 个文档",
            "updated_count": updated_count
        }
        
    except Exception as e:
        logger.error(f"增量向量化失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"增量向量化失败: {str(e)}")


@router.delete("/documents/{document_id}")
async def delete_document(document_id: str):
    """删除文档"""
    # 实现文档删除
    from app.services.document_service import DocumentService
    
    document_service = DocumentService()
    success = await document_service.delete_document(document_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="文档不存在或删除失败")
    
    return {"document_id": document_id, "status": "deleted", "message": "文档删除成功"}


@router.get("/documents/chunking/stats")
async def get_chunking_stats():
    """获取智能分块统计信息"""
    try:
        document_service = DocumentService()
        stats = document_service.get_chunking_stats()
        
        return {
            "status": "success",
            "data": stats
        }
        
    except Exception as e:
        logger.error(f"获取分块统计失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取分块统计失败: {str(e)}")


@router.post("/documents/chunking/reset-stats")
async def reset_chunking_stats():
    """重置智能分块统计"""
    try:
        document_service = DocumentService()
        success = document_service.reset_chunking_stats()
        
        if not success:
            raise HTTPException(status_code=500, detail="重置分块统计失败")
        
        return {
            "status": "success",
            "message": "分块统计已重置"
        }
        
    except Exception as e:
        logger.error(f"重置分块统计失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"重置分块统计失败: {str(e)}")


class ChunkingConfigUpdate(BaseModel):
    """分块配置更新模型"""
    chunk_size: Optional[int] = None
    chunk_overlap: Optional[int] = None
    enable_semantic: Optional[bool] = None


@router.post("/documents/chunking/config")
async def update_chunking_config(config: ChunkingConfigUpdate):
    """更新智能分块配置"""
    try:
        document_service = DocumentService()
        
        # 过滤掉None值
        config_dict = {k: v for k, v in config.dict().items() if v is not None}
        
        if not config_dict:
            raise HTTPException(status_code=400, detail="至少需要提供一个配置参数")
        
        success = document_service.update_chunking_config(**config_dict)
        
        if not success:
            raise HTTPException(status_code=500, detail="更新分块配置失败")
        
        return {
            "status": "success",
            "message": "分块配置已更新",
            "updated_config": config_dict
        }
        
    except Exception as e:
        logger.error(f"更新分块配置失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"更新分块配置失败: {str(e)}")
