"""
文档管理API
"""

import os
import uuid
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, UploadFile, File, BackgroundTasks, HTTPException, Query
from fastapi.responses import JSONResponse, FileResponse
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
    document_id: str  # 添加document_id字段
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
    file: UploadFile = File(...)
):
    """上传文档并将其处理任务推送到Celery队列"""
    from app.services.chat_service import ChatService
    from app.tasks.document_tasks import process_document_task
    
    try:
        # 获取全局服务实例
        document_service = get_document_service()
        from app.main import chat_service as global_chat_service
        if global_chat_service is None:
            raise HTTPException(status_code=500, detail="聊天服务未初始化")
        chat_service = global_chat_service
        
        # 读取文件内容
        file_content = await file.read()
        
        # 上传文档（仅创建记录和保存文件）
        document = await document_service.upload_document(
            file_content=file_content,
            filename=file.filename,
            content_type=file.content_type
        )
        
        # 将文档处理任务推送到Celery队列
        process_document_task.delay(document.id)
        logger.info(f"文档处理任务已推送到Celery队列: {document.id}")
        
        # 创建会话
        session_id = await chat_service.create_session()
        
        logger.info(f"文件上传成功: {file.filename}, 文档ID: {document.id}, 会话ID: {session_id}")
        
        return DocumentUploadResponse(
            session_id=session_id,
            document_id=document.id,
            status="processing_queued", # 更新状态为“已进入处理队列”
            filename=document.filename,
            message="文件上传成功，已加入后台处理队列..."
        )
        
    except ValueError as e:
        logger.warning(f"文件验证失败: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"上传文档时出错: {str(e)}")
        raise HTTPException(status_code=500, detail=f"上传文档时出错: {str(e)}")


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
async def get_documents(page: int = 1, page_size: int = 10):
    """获取文档列表（支持分页）
    
    Args:
        page: 页码，从1开始
        page_size: 每页数量，默认10条
    """
    try:
        # 获取文档服务实例
        document_service = get_document_service()
        
        # 计算偏移量
        offset = (page - 1) * page_size
        
        # 通过DocumentService获取分页数据
        result_data = await document_service.list_documents(limit=page_size, offset=offset)
        documents = result_data['documents']
        
        # 转换为前端需要的格式
        result = []
        for doc in documents:
            result.append({
                "id": doc.id,
                "name": doc.filename,
                "size": doc.file_size or 0,
                "uploadTime": doc.upload_time.isoformat() if doc.upload_time else None,
                "type": doc.content_type or "application/pdf",
                "status": getattr(doc, 'status', 'ready')  # 添加status字段，默认为ready
            })
        
        # 构建返回数据
        response_data = {
            "documents": result,
            "total": result_data['total'],
            "page": result_data['page'],
            "page_size": result_data['page_size'],
            "total_pages": result_data['total_pages']
        }
        
        logger.info(f"获取文档列表成功，第{page}页，共 {len(result)} 个文档，返回数据类型: {type(response_data)}")
        logger.debug(f"返回数据结构: {list(response_data.keys())}")
        
        return response_data
        
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
            "status": document.get("status", "ready")  # 从数据库获取status字段，默认为ready
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
        
        # 从metadata中获取详细信息
        metadata = document.get('metadata', {}) or {}
        
        return DocumentStatusResponse(
            document_id=document_id,
            filename=document["title"] or "",
            file_format=metadata.get("file_format", "unknown"),
            file_size=document["file_size"] or 0,
            processing_status=metadata.get("processing_status", "unknown"),
            vectorization_status=document["vectorization_status"] or "unknown",
            metadata_generation_status=metadata.get("metadata_generation_status", "unknown"),
            processing_start_time=metadata.get("processing_start_time"),
            processing_end_time=metadata.get("processing_end_time"),
            total_pages=metadata.get("total_pages"),
            total_sheets=metadata.get("total_sheets"),
            total_slides=metadata.get("total_slides"),
            element_types=metadata.get("element_types"),
            error_message=metadata.get("error_message")
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


@router.get("/documents/{document_id}/download")
async def download_document(document_id: str):
    """下载PDF原始文件"""
    try:
        from app.storage.database import get_db_manager
        db = get_db_manager()
        
        # 获取文档信息
        document = db.get_document(document_id)
        if not document:
            raise HTTPException(status_code=404, detail="文档不存在")
        
        # 获取文件路径
        file_path = document.get("file_path")
        if not file_path or not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="文件不存在或已被删除")
        
        # 获取文件名
        filename = document.get("filename", "document.pdf")
        
        # 返回文件
        return FileResponse(
            path=file_path,
            filename=filename,
            media_type="application/octet-stream"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"下载文档失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"下载文档失败: {str(e)}")


@router.get("/documents/{document_id}/raw")
async def get_document_raw(document_id: str):
    """获取PDF原始文件的二进制流，供前端react-pdf加载"""
    try:
        from app.storage.database import get_db_manager
        db = get_db_manager()
        
        # 获取文档信息
        document = db.get_document(document_id)
        if not document:
            raise HTTPException(status_code=404, detail="文档不存在")
        
        # 获取文件路径
        file_path = document.get("file_path")
        if not file_path or not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="文件不存在或已被删除")
        
        # 检查是否为PDF文件
        if not file_path.lower().endswith('.pdf'):
            raise HTTPException(status_code=400, detail="只支持PDF文件预览")
        
        # 返回PDF文件流
        return FileResponse(
            path=file_path,
            media_type="application/pdf",
            headers={"Content-Disposition": "inline"}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取PDF原始文件失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取PDF原始文件失败: {str(e)}")


@router.get("/documents/{document_id}/chunks")
async def get_document_chunks(document_id: str, page: int = Query(1, ge=1), limit: int = Query(20, ge=1, le=100)):
    """获取文档的分块信息"""
    try:
        from app.storage.database import get_db_manager
        
        db = get_db_manager()
        
        # 验证文档是否存在并获取文档信息
        document = db.get_document(document_id)
        if not document:
            raise HTTPException(status_code=404, detail="文档不存在")
        
        # 从MySQL获取分块信息
        parent_chunks = db.get_parent_chunks_by_document_id(document_id)
        
        if not parent_chunks:
            return {
                "status": "success",
                "document_id": document_id,
                "document_info": {
                    "id": document.get("id"),
                    "title": document.get("title", ""),
                    "file_type": document.get("file_type", ""),
                    "file_size": document.get("file_size"),
                    "created_at": document.get("created_at").isoformat() if document.get("created_at") else None
                },
                "total_chunks": 0,
                "page": page,
                "limit": limit,
                "total_pages": 0,
                "chunks": [],
                "message": "该文档暂无分块信息"
            }
        
        # 转换为前端需要的格式
        chunks = []
        for idx, chunk_data in enumerate(parent_chunks):
            # 处理关键词字段
            keywords = chunk_data.get("keywords", "")
            if isinstance(keywords, str) and keywords.strip():
                # 尝试解析为数组
                try:
                    import json
                    keywords_list = json.loads(keywords)
                    if not isinstance(keywords_list, list):
                        keywords_list = [k.strip() for k in keywords.split(',') if k.strip()]
                except (json.JSONDecodeError, AttributeError):
                    keywords_list = [k.strip() for k in keywords.split(',') if k.strip()]
            else:
                keywords_list = []
            
            chunk_info = {
                "id": chunk_data["id"],
                "chunk_index": idx,
                "type": "parent",
                "content": chunk_data["content"],
                "created_at": chunk_data.get("created_at").isoformat() if chunk_data.get("created_at") else None,
                "content_length": len(chunk_data["content"]),
                "metadata": {
                    "document_id": chunk_data["document_id"],
                    "chunk_type": "parent",
                    "source": "mysql_parent_chunks",
                    "summary": chunk_data.get("summary", ""),
                    "keywords": keywords_list
                }
            }
            chunks.append(chunk_info)
        
        # 分页处理
        total_chunks = len(chunks)
        start_idx = (page - 1) * limit
        end_idx = start_idx + limit
        paginated_chunks = chunks[start_idx:end_idx]
        
        return {
            "status": "success",
            "document_id": document_id,
            "document_info": {
                "id": document.get("id"),
                "title": document.get("title", ""),
                "file_type": document.get("file_type", ""),
                "file_size": document.get("file_size"),
                "created_at": document.get("created_at").isoformat() if document.get("created_at") else None
            },
            "total_chunks": total_chunks,
            "page": page,
            "limit": limit,
            "total_pages": (total_chunks + limit - 1) // limit,
            "chunks": paginated_chunks
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取文档分块信息失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取文档分块信息失败: {str(e)}")
