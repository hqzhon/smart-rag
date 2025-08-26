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
from app.api.v1 import chat, documents, document_progress

# 设置日志
logger = setup_logger(__name__)

# 全局服务实例
document_service: Optional[DocumentService] = None
chat_service: Optional[ChatService] = None
search_service: Optional[SearchService] = None



async def initialize_services():
    """并行初始化所有服务组件"""
    logger.info("开始并行初始化服务...")
    start_time = time.time()
    
    # 定义初始化任务
    async def init_document_service():
        logger.info("初始化文档服务...")
        service = DocumentService()
        # 异步初始化数据库连接
        await service.async_init()
        return service
    
    async def init_chat_service():
        logger.info("初始化聊天服务...")
        service = ChatService()
        await service.async_init()
        return service
    
    async def init_search_service():
        logger.info("初始化搜索服务...")
        service = SearchService()
        await service.async_init()
        return service
    
    # 并行执行初始化任务
    tasks = [
        init_document_service(),
        init_chat_service(),
        init_search_service()
    ]
    
    try:
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 检查初始化结果
        services = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                service_names = ["文档服务", "聊天服务", "搜索服务"]
                logger.error(f"{service_names[i]}初始化失败: {result}")
                raise result
            services.append(result)
        
        init_time = time.time() - start_time
        logger.info(f"所有服务并行初始化完成，耗时: {init_time:.2f}秒")
        
        return services
        
    except Exception as e:
        logger.error(f"服务初始化过程中出现错误: {str(e)}")
        raise

@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时初始化
    logger.info("医疗RAG系统启动中...")
    
    global document_service, chat_service, search_service
    
    try:
        # 并行初始化服务
        services = await initialize_services()
        document_service, chat_service, search_service = services
        
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
        await cleanup_services()

async def cleanup_services():
    """清理服务资源"""
    global document_service, chat_service, search_service
    
    cleanup_tasks = []
    
    if hasattr(document_service, 'cleanup'):
        cleanup_tasks.append(document_service.cleanup())
    if hasattr(chat_service, 'cleanup'):
        cleanup_tasks.append(chat_service.cleanup())
    if hasattr(search_service, 'cleanup'):
        cleanup_tasks.append(search_service.cleanup())
    
    if cleanup_tasks:
        try:
            await asyncio.gather(*cleanup_tasks, return_exceptions=True)
            logger.info("服务资源清理完成")
        except Exception as e:
            logger.error(f"服务清理过程中出现错误: {str(e)}")

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
app.include_router(document_progress.router, prefix="/api/v1", tags=["document_progress"])

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

# 所有聊天相关的路由已移至 /api/v1/chat.py 中

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