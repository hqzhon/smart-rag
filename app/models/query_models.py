"""
查询相关数据模型
"""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime


class QueryRequest(BaseModel):
    """查询请求模型"""
    query: str = Field(..., min_length=1, max_length=1000, description="用户查询内容")
    session_id: str = Field(..., description="会话ID")
    context: Optional[str] = Field(None, description="上下文信息")
    language: Optional[str] = Field("auto", description="查询语言")
    max_results: Optional[int] = Field(5, ge=1, le=20, description="最大返回结果数")
    include_sources: bool = Field(True, description="是否包含来源信息")


class QueryResponse(BaseModel):
    """查询响应模型"""
    query: str = Field(..., description="原始查询")
    response: str = Field(..., description="生成的回答")
    documents: List[str] = Field(default_factory=list, description="参考文档片段")
    sources: List[Dict[str, Any]] = Field(default_factory=list, description="来源信息")
    session_id: str = Field(..., description="会话ID")
    confidence_score: Optional[float] = Field(None, ge=0.0, le=1.0, description="置信度分数")
    processing_time: Optional[float] = Field(None, description="处理时间(秒)")
    feedback: Optional[str] = Field(None, description="反馈信息")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="元数据")


class ChatMessage(BaseModel):
    """聊天消息模型"""
    id: Optional[str] = None
    session_id: str
    message_type: str = "user"  # user, assistant, system
    content: str
    timestamp: datetime = Field(default_factory=datetime.now)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class SearchResult(BaseModel):
    """搜索结果模型"""
    content: str = Field(..., description="文档内容")
    score: float = Field(..., ge=0.0, le=1.0, description="相关性分数")
    source: str = Field(..., description="来源文档")
    page: Optional[int] = Field(None, description="页码")
    chunk_type: str = Field("text", description="块类型")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="元数据")


class FeedbackRequest(BaseModel):
    """反馈请求模型"""
    message_id: str = Field(..., description="消息ID")
    rating: int = Field(..., ge=1, le=5, description="评分(1-5)")
    comment: Optional[str] = Field(None, max_length=500, description="评论")
    feedback_type: str = Field("quality", description="反馈类型")


class QueryAnalysis(BaseModel):
    """查询分析结果"""
    query_type: str = Field(..., description="查询类型")
    entities: List[str] = Field(default_factory=list, description="识别的实体")
    intent: str = Field(..., description="查询意图")
    language: str = Field(..., description="查询语言")
    complexity: str = Field("medium", description="查询复杂度")
    keywords: List[str] = Field(default_factory=list, description="关键词")