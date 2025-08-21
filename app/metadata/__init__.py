"""元数据增强模块

本模块提供文档元数据的自动提取和增强功能，包括：
- 文档摘要生成
- 关键词提取
- 质量评估
- 异步处理
"""

from .models.metadata_models import (
    DocumentSummary,
    KeywordInfo,
    MetadataInfo,
    SummaryQuality,
    KeywordQuality
)
from .clients.qianwen_client import QianwenClient
from .summarizers.lightweight_summarizer import LightweightSummaryGenerator
from .extractors.keybert_extractor import KeyBERTExtractor
from .processors.async_processor import AsyncMetadataProcessor
from .evaluators.quality_evaluator import QualityEvaluator

__all__ = [
    # 数据模型
    'DocumentSummary',
    'KeywordInfo',
    'MetadataInfo',
    'SummaryQuality',
    'KeywordQuality',
    # API客户端
    'QianwenClient',
    # 核心组件
    'LightweightSummaryGenerator',
    'KeyBERTExtractor',
    'AsyncMetadataProcessor',
    'QualityEvaluator'
]

__version__ = '1.0.0'
__author__ = 'Smart RAG Team'
__description__ = '医学RAG系统元数据增强MVP模块'