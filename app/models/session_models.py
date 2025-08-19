"""
会话相关数据模型
"""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum


class SessionStatus(str, Enum):
    """会话状态枚举"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    EXPIRED = "expired"
    TERMINATED = "terminated"


class Session(BaseModel):
    """会话模型"""
    id: str = Field(..., description="会话ID")
    user_id: Optional[str] = Field(None, description="用户ID")
    document_ids: List[str] = Field(default_factory=list, description="关联的文档ID列表")
    status: SessionStatus = Field(SessionStatus.ACTIVE, description="会话状态")
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")
    last_activity: datetime = Field(default_factory=datetime.now, description="最后活动时间")
    expires_at: Optional[datetime] = Field(None, description="过期时间")
    message_count: int = Field(0, description="消息数量")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="会话元数据")


class SessionInfo(BaseModel):
    """会话信息模型"""
    session_id: str = Field(..., description="会话ID")
    document_count: int = Field(0, description="文档数量")
    message_count: int = Field(0, description="消息数量")
    created_at: datetime = Field(..., description="创建时间")
    last_activity: datetime = Field(..., description="最后活动时间")
    status: SessionStatus = Field(..., description="会话状态")
    processing_status: str = Field("ready", description="处理状态")


class SessionCreate(BaseModel):
    """创建会话请求模型"""
    user_id: Optional[str] = Field(None, description="用户ID")
    document_ids: Optional[List[str]] = Field(None, description="文档ID列表")
    expires_in: Optional[int] = Field(3600, description="过期时间(秒)")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="元数据")


class SessionUpdate(BaseModel):
    """更新会话请求模型"""
    status: Optional[SessionStatus] = Field(None, description="会话状态")
    document_ids: Optional[List[str]] = Field(None, description="文档ID列表")
    metadata: Optional[Dict[str, Any]] = Field(None, description="元数据")