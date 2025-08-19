"""
健康检查API
"""

from fastapi import APIRouter
from pydantic import BaseModel
from typing import Dict, Any
import time
import os

router = APIRouter()


class HealthResponse(BaseModel):
    """健康检查响应模型"""
    status: str
    timestamp: float
    version: str
    environment: str


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """健康检查端点"""
    return HealthResponse(
        status="healthy",
        timestamp=time.time(),
        version="1.0.0",
        environment=os.getenv("ENVIRONMENT", "development")
    )


@router.get("/sessions/count")
async def get_session_count():
    """获取当前活跃会话数量"""
    # 这里需要导入session_manager，但为了避免循环导入，我们先返回模拟数据
    return {"active_sessions": 0, "message": "Session manager not initialized"}