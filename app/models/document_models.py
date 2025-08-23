"""
文档相关数据模型
"""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime


class Document(BaseModel):
    """文档模型"""
    id: Optional[str] = None
    filename: str
    file_path: str
    file_size: int
    content_type: str = "application/pdf"
    upload_time: datetime = Field(default_factory=datetime.now)
    processed: bool = False
    processing_status: str = "pending"  # pending, processing, completed, failed
    vectorized: bool = False  # 向量化状态
    vectorization_status: str = "pending"  # pending, processing, completed, failed
    vectorization_time: Optional[datetime] = None  # 向量化完成时间
    # 新增关键字和摘要生成状态
    metadata_generated: bool = False  # 元数据生成状态
    metadata_generation_status: str = "pending"  # pending, processing, completed, failed
    metadata_generation_time: Optional[datetime] = None  # 元数据生成完成时间
    # 聊天交互就绪状态（当所有处理完成后设置为True）
    chat_ready: bool = False  # 是否已具备聊天交互功能
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class DocumentChunk(BaseModel):
    """文档块模型"""
    id: Optional[str] = None
    document_id: str
    chunk_index: int
    content: str
    chunk_type: str = "text"  # text, table, reference, image
    page_number: Optional[int] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    embedding: Optional[List[float]] = None


class ProcessingResult(BaseModel):
    """文档处理结果模型"""
    document_id: str
    success: bool
    total_chunks: int
    processing_time: float
    extracted_text_length: int
    tables_count: int = 0
    references_count: int = 0
    images_count: int = 0
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class TableInfo(BaseModel):
    """表格信息模型"""
    table_index: int
    page: int
    rows: int
    columns: int
    text_description: str
    raw_data: Optional[List[List[str]]] = None


class ReferenceInfo(BaseModel):
    """参考文献信息模型"""
    reference_id: str
    reference_text: str
    page: Optional[int] = None
    authors: Optional[List[str]] = None
    title: Optional[str] = None
    journal: Optional[str] = None
    year: Optional[int] = None
    doi: Optional[str] = None


class ImageInfo(BaseModel):
    """图像信息模型"""
    image_index: int
    page: int
    image_path: str
    caption: Optional[str] = None
    description: Optional[str] = None
    image_type: str = "figure"  # figure, chart, diagram