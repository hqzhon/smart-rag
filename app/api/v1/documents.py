"""
文档管理API
"""

import os
import uuid
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, UploadFile, File, BackgroundTasks, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import logging

from app.utils.logger import setup_logger
from app.models.document_models import Document
from app.services.document_service import DocumentService

logger = setup_logger(__name__)

# 获取全局服务实例
def get_document_service():
    """获取全局文档服务实例"""
    from app.main import document_service
    if document_service is None:
        raise HTTPException(status_code=500, detail="文档服务未初始化")
    return document_service

router = APIRouter()


class DocumentUploadResponse(BaseModel):
    """文档上传响应模型"""
    session_id: str
    status: str
    filename: str
    message: str


class SupportedFormatInfo(BaseModel):
    """支持格式信息模型"""
    extension: str
    mime_type: str
    format_name: str
    description: str
    max_size: int
    features: List[str]


class SupportedFormatsResponse(BaseModel):
    """支持格式响应模型"""
    formats: List[SupportedFormatInfo]
    max_file_size: int
    processing_timeout: int
    total_formats: int


class DocumentStatusResponse(BaseModel):
    """文档状态响应模型"""
    document_id: str
    filename: str
    file_format: str
    file_size: int
    processing_status: str
    vectorization_status: str
    metadata_generation_status: str
    processing_start_time: Optional[str] = None
    processing_end_time: Optional[str] = None
    total_pages: Optional[int] = None
    total_sheets: Optional[int] = None
    total_slides: Optional[int] = None
    element_types: Optional[List[str]] = None
    error_message: Optional[str] = None


@router.post("/documents/upload", response_model=DocumentUploadResponse)
async def upload_document(
    file: UploadFile = File(...), 
    background_tasks: BackgroundTasks = None
):
    """上传PDF文档"""
    from app.services.chat_service import ChatService
    
    try:
        # 获取全局服务实例
        document_service = get_document_service()
        from app.main import chat_service as global_chat_service
        if global_chat_service is None:
            raise HTTPException(status_code=500, detail="聊天服务未初始化")
        chat_service = global_chat_service
        
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
            message="文件上传成功，正在处理中..."
        )
        
    except ValueError as e:
        logger.warning(f"文件验证失败: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
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





@router.get("/documents/supported-formats", response_model=SupportedFormatsResponse)
async def get_supported_formats():
    """获取支持的文档格式信息"""
    try:
        document_service = get_document_service()
        formats_info = document_service.get_supported_formats_info()
        
        return SupportedFormatsResponse(
            formats=formats_info["formats"],
            max_file_size=formats_info["max_file_size"],
            processing_timeout=formats_info["processing_timeout"],
            total_formats=len(formats_info["formats"])
        )
        
    except Exception as e:
        logger.error(f"获取支持格式失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取支持格式失败: {str(e)}")


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
    try:
        document_service = get_document_service()
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
    except Exception as e:
        logger.error(f"获取文档失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取文档失败: {str(e)}")


@router.post("/documents/vectorize")
async def vectorize_documents():
    """触发增量向量化更新"""
    try:
        # 获取文档服务实例
        document_service = get_document_service()
        
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
    try:
        # 实现文档删除
        document_service = get_document_service()
        success = await document_service.delete_document(document_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="文档不存在或删除失败")
        
        return {"document_id": document_id, "status": "deleted", "message": "文档删除成功"}
    except Exception as e:
        logger.error(f"删除文档失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"删除文档失败: {str(e)}")


@router.get("/documents/chunking/stats")
async def get_chunking_stats():
    """获取智能分块统计信息"""
    try:
        document_service = get_document_service()
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
        document_service = get_document_service()
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
        document_service = get_document_service()
        
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





@router.get("/documents/{document_id}/status", response_model=DocumentStatusResponse)
async def get_document_status(document_id: str):
    """获取文档处理状态详情"""
    try:
        from app.storage.database import get_db_manager
        db = get_db_manager()
        
        document = db.get_document(document_id)
        if not document:
            raise HTTPException(status_code=404, detail="文档不存在")
        
        return DocumentStatusResponse(
            document_id=document_id,
            filename=document["filename"] or "",
            file_format=document["file_format"] or "unknown",
            file_size=document["file_size"] or 0,
            processing_status=document["processing_status"] or "unknown",
            vectorization_status=document["vectorization_status"] or "unknown",
            metadata_generation_status=document["metadata_generation_status"] or "unknown",
            processing_start_time=document["processing_start_time"].isoformat() if document.get("processing_start_time") else None,
            processing_end_time=document["processing_end_time"].isoformat() if document.get("processing_end_time") else None,
            total_pages=document.get("total_pages"),
            total_sheets=document.get("total_sheets"),
            total_slides=document.get("total_slides"),
            element_types=document.get("element_types"),
            error_message=document.get("error_message")
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取文档状态失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取文档状态失败: {str(e)}")


@router.get("/documents/formats/validate/{filename}")
async def validate_file_format(filename: str):
    """验证文件格式是否支持"""
    try:
        document_service = get_document_service()
        
        # 从文件名提取扩展名
        import os
        _, ext = os.path.splitext(filename.lower())
        
        if not ext:
            return {
                "supported": False,
                "message": "无法识别文件格式",
                "extension": None
            }
        
        # 检查是否支持
        is_supported = document_service.multi_format_processor.is_supported_format(ext)
        
        if is_supported:
            # 获取格式信息
            formats_info = document_service.get_supported_formats_info()
            format_info = next((f for f in formats_info["formats"] if f["extension"] == ext), None)
            
            return {
                "supported": True,
                "message": f"支持 {ext} 格式",
                "extension": ext,
                "format_info": format_info
            }
        else:
            return {
                "supported": False,
                "message": f"不支持 {ext} 格式",
                "extension": ext,
                "supported_formats": document_service.multi_format_processor.get_supported_extensions()
            }
        
    except Exception as e:
        logger.error(f"验证文件格式失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"验证文件格式失败: {str(e)}")


@router.get("/documents/processing/stats")
async def get_processing_stats():
    """获取文档处理统计信息"""
    try:
        from app.storage.database import get_db_manager
        db = get_db_manager()
        
        # 获取各种状态的文档数量
        stats = {
            "total_documents": 0,
            "by_status": {
                "pending": 0,
                "processing": 0,
                "completed": 0,
                "error": 0
            },
            "by_format": {},
            "total_size": 0,
            "processing_queue": 0
        }
        
        # 这里应该实现实际的统计查询
        # 暂时返回示例数据
        documents = db.list_documents(limit=1000)
        
        stats["total_documents"] = len(documents)
        
        for doc in documents:
            # 统计状态
            status = doc.get("processing_status", "unknown")
            if status in stats["by_status"]:
                stats["by_status"][status] += 1
            
            # 统计格式
            file_format = doc.get("file_format", "unknown")
            stats["by_format"][file_format] = stats["by_format"].get(file_format, 0) + 1
            
            # 统计大小
            file_size = doc.get("file_size", 0) or 0
            stats["total_size"] += file_size
            
            # 统计处理队列
            if status == "processing":
                stats["processing_queue"] += 1
        
        return {
            "status": "success",
            "data": stats
        }
        
    except Exception as e:
        logger.error(f"获取处理统计失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取处理统计失败: {str(e)}")
