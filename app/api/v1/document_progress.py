#!/usr/bin/env python3
"""
文档处理进度SSE端点
"""

import json
import asyncio
import logging
from typing import AsyncGenerator
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from app.core.redis_client import get_redis_client
from app.storage.database import DatabaseManager

logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("/documents/{document_id}/status-stream")
async def stream_document_progress(document_id: str):
    """
    SSE端点，实时推送文档处理进度
    
    Args:
        document_id: 文档ID
        
    Returns:
        SSE流响应
    """
    try:
        # 验证文档是否存在
        db_manager = DatabaseManager()
        document = db_manager.get_document(document_id)
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")
        
        logger.info(f"Starting SSE stream for document: {document_id}")
        
        async def event_generator() -> AsyncGenerator[str, None]:
            redis_client = get_redis_client()
            channel = f"document_progress_{document_id}"
            pubsub = None
            
            try:
                # 订阅Redis频道
                pubsub = redis_client.subscribe(channel)
                if not pubsub:
                    logger.error(f"Failed to subscribe to channel: {channel}")
                    yield f"data: {{\"error\": \"Failed to subscribe to progress updates\"}}\n\n"
                    return
                
                logger.info(f"Subscribed to Redis channel: {channel}")
                
                # 发送初始连接确认
                initial_data = {
                    "document_id": document_id,
                    "status": "connected",
                    "message": "Connected to progress stream",
                    "timestamp": document.get('created_at', '').isoformat() if document.get('created_at') else None
                }
                yield f"data: {json.dumps(initial_data, ensure_ascii=False)}\n\n"
                
                # 检查文档当前状态，如果已完成则发送完成状态
                metadata = document.get('metadata', {})
                document_status = document.get('status', '')
                
                if metadata.get('processing_status') == 'completed' or document_status == 'chat_ready':
                    completed_data = {
                        "document_id": document_id,
                        "status": "chat_ready",
                        "progress": 100,
                        "message": "文档处理已完成，可以开始对话",
                        "timestamp": document.get('updated_at', '').isoformat() if document.get('updated_at') else None
                    }
                    yield f"data: {json.dumps(completed_data, ensure_ascii=False)}\n\n"
                    return
                elif metadata.get('processing_status') == 'failed':
                    error_data = {
                        "document_id": document_id,
                        "status": "failed",
                        "progress": 0,
                        "message": metadata.get('error_message', '处理失败'),
                        "timestamp": document.get('updated_at', '').isoformat() if document.get('updated_at') else None
                    }
                    yield f"data: {json.dumps(error_data, ensure_ascii=False)}\n\n"
                    return
                
                # 监听Redis消息
                timeout_count = 0
                max_timeout = 300  # 5分钟超时
                
                while timeout_count < max_timeout:
                    try:
                        # 获取消息，设置1秒超时
                        message = redis_client.get_message(pubsub, timeout=1.0)
                        
                        if message:
                            timeout_count = 0  # 重置超时计数
                            logger.debug(f"Received progress message: {message}")
                            
                            # 发送SSE数据
                            yield f"data: {json.dumps(message, ensure_ascii=False)}\n\n"
                            
                            # 如果是完成或失败状态，结束流
                            if message.get('status') in ['completed', 'failed', 'error', 'chat_ready']:
                                logger.info(f"Document processing finished: {document_id}, status: {message.get('status')}")
                                break
                        else:
                            # 没有消息，发送心跳
                            timeout_count += 1
                            if timeout_count % 30 == 0:  # 每30秒发送一次心跳
                                heartbeat = {
                                    "document_id": document_id,
                                    "status": "heartbeat",
                                    "message": "Connection alive"
                                }
                                yield f"data: {json.dumps(heartbeat, ensure_ascii=False)}\n\n"
                        
                        # 短暂休眠，避免CPU占用过高
                        await asyncio.sleep(0.1)
                        
                    except Exception as msg_error:
                        logger.error(f"Error getting message from Redis: {msg_error}")
                        error_data = {
                            "document_id": document_id,
                            "status": "error",
                            "message": f"Stream error: {str(msg_error)}"
                        }
                        yield f"data: {json.dumps(error_data, ensure_ascii=False)}\n\n"
                        break
                
                if timeout_count >= max_timeout:
                    logger.warning(f"SSE stream timeout for document: {document_id}")
                    timeout_data = {
                        "document_id": document_id,
                        "status": "timeout",
                        "message": "Stream timeout"
                    }
                    yield f"data: {json.dumps(timeout_data, ensure_ascii=False)}\n\n"
                
            except Exception as stream_error:
                logger.error(f"SSE stream error for document {document_id}: {stream_error}")
                error_data = {
                    "document_id": document_id,
                    "status": "error",
                    "message": f"Stream error: {str(stream_error)}"
                }
                yield f"data: {json.dumps(error_data, ensure_ascii=False)}\n\n"
            
            finally:
                # 清理资源
                if pubsub:
                    try:
                        pubsub.close()
                        logger.info(f"Closed Redis subscription for document: {document_id}")
                    except Exception as close_error:
                        logger.error(f"Error closing Redis subscription: {close_error}")
        
        # 返回SSE响应
        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "Cache-Control"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error setting up SSE stream for document {document_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to setup progress stream: {str(e)}")

@router.get("/documents/{document_id}/status")
async def get_document_status(document_id: str):
    """
    获取文档当前处理状态（非流式）
    
    Args:
        document_id: 文档ID
        
    Returns:
        文档状态信息
    """
    try:
        db_manager = DatabaseManager()
        document = db_manager.get_document(document_id)
        
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")
        
        metadata = document.get('metadata', {})
        
        status_info = {
            "document_id": document_id,
            "filename": document.get('title', ''),
            "status": document.get('status', 'unknown'),
            "processing_status": metadata.get('processing_status', 'unknown'),
            "vectorized": metadata.get('vectorized', False),
            "vectorization_status": metadata.get('vectorization_status', 'unknown'),
            "created_at": document.get('created_at', '').isoformat() if document.get('created_at') else None,
            "updated_at": document.get('updated_at', '').isoformat() if document.get('updated_at') else None,
            "error_message": metadata.get('error_message')
        }
        
        return status_info
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting document status for {document_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get document status: {str(e)}")