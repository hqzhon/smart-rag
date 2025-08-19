"""
FastAPI应用主入口
"""

import os
import asyncio
import time
import json
from typing import List, Dict, Any, Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, UploadFile, File, BackgroundTasks, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from pydantic import BaseModel
import uuid
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 导入应用模块
from app.utils.logger import setup_logger
from app.services.document_service import DocumentService
from app.services.chat_service import ChatService
from app.services.search_service import SearchService
from app.models.query_models import QueryRequest, QueryResponse
from app.models.document_models import Document
from app.api.v1 import chat, documents

# 设置日志
logger = setup_logger(__name__)

# 全局服务实例
document_service: Optional[DocumentService] = None
chat_service: Optional[ChatService] = None
search_service: Optional[SearchService] = None



@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时初始化
    logger.info("医疗RAG系统启动中...")
    
    global document_service, chat_service, search_service
    
    try:
        # 初始化服务
        document_service = DocumentService()
        chat_service = ChatService()
        search_service = SearchService()
        
        logger.info("所有服务初始化完成")
        
        # 启动后台任务
        asyncio.create_task(cleanup_task())
        
        yield
        
    except Exception as e:
        logger.error(f"应用启动失败: {str(e)}")
        raise
    finally:
        # 关闭时清理
        logger.info("医疗RAG系统关闭中...")

# 创建FastAPI应用
app = FastAPI(
    title="医疗RAG系统",
    description="基于检索增强生成的智能医疗问答系统",
    version="1.0.0",
    lifespan=lifespan
)

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应该限制具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册API路由
app.include_router(chat.router, prefix="/api/v1", tags=["chat"])
app.include_router(documents.router, prefix="/api/v1", tags=["documents"])

# 后台清理任务
async def cleanup_task():
    """后台清理任务"""
    while True:
        try:
            await asyncio.sleep(300)  # 每5分钟执行一次
            if chat_service:
                await chat_service.cleanup_expired_sessions()
        except Exception as e:
            logger.error(f"后台清理任务出错: {str(e)}")

# 根路径 - 返回前端页面
@app.get("/")
async def read_root():
    """API根路径"""
    return {"message": "医疗RAG系统API", "docs": "/docs"}

# 健康检查
@app.get("/api/v1/health")
async def health_check():
    """健康检查接口"""
    return {
        "status": "healthy",
        "timestamp": time.time(),
        "version": "1.0.0",
        "services": {
            "document_service": document_service is not None,
            "chat_service": chat_service is not None,
            "search_service": search_service is not None
        }
    }

# 文档上传接口
# 文档上传端点已移至 /api/v1/documents.py 路由中

# 查询接口
@app.post("/api/v1/chat/query", response_model=QueryResponse)
async def query_chat(request: QueryRequest):
    """处理用户查询"""
    try:
        if not chat_service:
            raise HTTPException(status_code=500, detail="聊天服务未初始化")
        
        if not request.session_id:
            raise HTTPException(status_code=400, detail="会话ID不能为空")
        
        # 处理查询
        response = await chat_service.process_query(request)
        
        return response
        
    except Exception as e:
        logger.error(f"查询处理失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))



# 搜索接口
@app.post("/api/v1/search")
async def search_documents(query: str, session_id: Optional[str] = None, limit: int = 10):
    """搜索文档"""
    try:
        if not search_service:
            raise HTTPException(status_code=500, detail="搜索服务未初始化")
        
        results = await search_service.search_documents(
            query=query,
            session_id=session_id,
            limit=limit
        )
        
        return {
            "query": query,
            "results": results,
            "total": len(results)
        }
        
    except Exception as e:
        logger.error(f"搜索失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# 会话信息接口
@app.get("/api/v1/sessions/{session_id}")
async def get_session_info(session_id: str):
    """获取会话信息"""
    try:
        if not chat_service:
            raise HTTPException(status_code=500, detail="聊天服务未初始化")
        
        info = await chat_service.get_session_info(session_id)
        
        if not info:
            raise HTTPException(status_code=404, detail="会话不存在")
        
        return info
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取会话信息失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# 聊天历史接口
@app.get("/api/v1/chat/history/{session_id}")
async def get_chat_history(session_id: str, limit: int = 50):
    """获取聊天历史"""
    try:
        if not chat_service:
            raise HTTPException(status_code=500, detail="聊天服务未初始化")
        
        history = await chat_service.get_chat_history(session_id, limit)
        return history
        
    except Exception as e:
        logger.error(f"获取聊天历史失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# 系统信息接口
@app.get("/api/v1/system/info")
async def get_system_info():
    """获取系统信息"""
    return {
        "name": "医疗RAG系统",
        "version": "1.0.0",
        "description": "基于检索增强生成的智能医疗问答系统",
        "features": [
            "PDF文档处理",
            "智能问答",
            "实时对话",
            "混合检索",
            "多语言支持"
        ],
        "supported_formats": ["pdf"],
        "max_file_size": "50MB"
    }

if __name__ == "__main__":
    # 直接运行时的配置
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8001,
        reload=True
    )