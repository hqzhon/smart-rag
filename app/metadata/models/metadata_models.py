"""元数据数据模型

定义医学文档元数据增强系统中使用的所有数据结构
"""

from typing import List, Dict, Any, Optional, Union, Tuple
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field, validator


class SummaryMethod(str, Enum):
    """摘要生成方法枚举"""
    QIANWEN_API = "qianwen_api"
    EXTRACTIVE = "extractive"
    FALLBACK = "fallback"
    DIRECT = "direct"


class KeywordMethod(str, Enum):
    """关键词提取方法枚举"""
    KEYBERT = "keybert"
    JIEBA = "jieba"
    JIEBA_FALLBACK = "jieba_fallback"
    MEDICAL_DICT = "medical_dict"
    FREQUENCY = "frequency"
    FALLBACK = "fallback"


class MedicalCategory(str, Enum):
    """医学术语分类"""
    SYMPTOM = "症状"
    DISEASE = "疾病"
    DRUG = "药物"
    EXAMINATION = "检查"
    TREATMENT = "治疗"
    ANATOMY = "解剖"
    GENERAL = "general"


class QualityLevel(str, Enum):
    """质量等级"""
    EXCELLENT = "excellent"  # 0.8-1.0
    GOOD = "good"           # 0.6-0.8
    FAIR = "fair"           # 0.4-0.6
    POOR = "poor"           # 0.0-0.4


class DocumentSummary(BaseModel):
    """文档摘要数据模型"""
    
    chunk_id: Optional[str] = Field(None, description="文档块ID")
    content: str = Field(..., description="摘要内容")
    method: SummaryMethod = Field(..., description="生成方法")
    confidence: float = Field(ge=0.0, le=1.0, description="置信度分数")
    
    # 质量指标
    quality_score: Optional[float] = Field(None, ge=0.0, le=1.0, description="质量分数")
    coherence_score: Optional[float] = Field(None, ge=0.0, le=1.0, description="连贯性分数")
    coverage_score: Optional[float] = Field(None, ge=0.0, le=1.0, description="覆盖度分数")
    
    # 元信息
    length: int = Field(default=0, description="摘要长度")
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")
    processing_time: Optional[float] = Field(None, description="处理时间(秒)")
    
    # 原文信息
    source_length: Optional[int] = Field(None, description="原文长度")
    compression_ratio: Optional[float] = Field(None, description="压缩比")
    
    @validator('content')
    def validate_content(cls, v):
        if not v or not v.strip():
            raise ValueError("摘要内容不能为空")
        if len(v) > 200:
            raise ValueError("摘要长度不能超过200字符")
        return v.strip()
    
    @validator('length', always=True)
    def set_length(cls, v, values):
        if 'content' in values:
            return len(values['content'])
        return v
    
    @validator('compression_ratio', always=True)
    def calculate_compression_ratio(cls, v, values):
        if 'source_length' in values and values['source_length'] and 'length' in values:
            return values['length'] / values['source_length']
        return v
    
    def get_quality_level(self) -> QualityLevel:
        """获取质量等级"""
        if self.quality_score is None:
            return QualityLevel.FAIR
        
        if self.quality_score >= 0.8:
            return QualityLevel.EXCELLENT
        elif self.quality_score >= 0.6:
            return QualityLevel.GOOD
        elif self.quality_score >= 0.4:
            return QualityLevel.FAIR
        else:
            return QualityLevel.POOR


class KeywordInfo(BaseModel):
    """关键词提取结果数据模型"""
    
    # 基本信息
    chunk_id: str = Field(..., description="文档块ID")
    keywords: List[str] = Field(default_factory=list, description="提取的关键词列表")
    keyword_scores: List[float] = Field(default_factory=list, description="关键词分数列表")
    method: KeywordMethod = Field(..., description="提取方法")
    medical_category: MedicalCategory = Field(default=MedicalCategory.GENERAL, description="医学分类")
    
    # 处理信息
    processing_time: Optional[float] = Field(None, description="处理时间（秒）")
    extracted_at: datetime = Field(default_factory=datetime.now, description="提取时间")
    
    # 元数据
    metadata: Dict[str, Any] = Field(default_factory=dict, description="额外元数据")
    
    @validator('keyword_scores')
    def validate_keywords_scores(cls, v, values):
        if 'keywords' in values:
            keywords = values['keywords']
            if len(v) != len(keywords):
                raise ValueError("关键词和分数列表长度必须一致")
        return v
    
    @validator('keywords')
    def validate_keywords_content(cls, v):
        for keyword in v:
            if not keyword or not keyword.strip():
                raise ValueError("关键词不能为空")
            if len(keyword) > 50:
                raise ValueError("关键词长度不能超过50字符")
        return [kw.strip() for kw in v]
    
    def get_top_keywords(self, n: int = 5) -> List[Tuple[str, float]]:
        """获取前N个关键词及其分数"""
        if not self.keywords or not self.keyword_scores:
            return []
        
        paired = list(zip(self.keywords, self.keyword_scores))
        return sorted(paired, key=lambda x: x[1], reverse=True)[:n]
    
    def has_medical_keywords(self) -> bool:
        """判断是否包含医学关键词"""
        return self.medical_category != MedicalCategory.GENERAL


class SummaryQuality(BaseModel):
    """摘要质量评估结果"""
    
    # ROUGE指标
    rouge_1: Optional[float] = Field(None, ge=0.0, le=1.0, description="ROUGE-1分数")
    rouge_2: Optional[float] = Field(None, ge=0.0, le=1.0, description="ROUGE-2分数")
    rouge_l: Optional[float] = Field(None, ge=0.0, le=1.0, description="ROUGE-L分数")
    
    # 语义指标
    semantic_similarity: Optional[float] = Field(None, ge=0.0, le=1.0, description="语义相似度")
    coherence_score: Optional[float] = Field(None, ge=0.0, le=1.0, description="连贯性分数")
    
    # 内容指标
    coverage_score: Optional[float] = Field(None, ge=0.0, le=1.0, description="内容覆盖度")
    informativeness: Optional[float] = Field(None, ge=0.0, le=1.0, description="信息量")
    
    # 综合评分
    overall_score: Optional[float] = Field(None, ge=0.0, le=1.0, description="综合质量分数")
    quality_level: Optional[QualityLevel] = Field(None, description="质量等级")
    
    # 评估元信息
    evaluation_method: Optional[str] = Field(None, description="评估方法")
    evaluated_at: datetime = Field(default_factory=datetime.now, description="评估时间")
    
    def calculate_overall_score(self) -> float:
        """计算综合质量分数"""
        scores = []
        weights = []
        
        if self.rouge_l is not None:
            scores.append(self.rouge_l)
            weights.append(0.3)
        
        if self.semantic_similarity is not None:
            scores.append(self.semantic_similarity)
            weights.append(0.25)
        
        if self.coherence_score is not None:
            scores.append(self.coherence_score)
            weights.append(0.25)
        
        if self.coverage_score is not None:
            scores.append(self.coverage_score)
            weights.append(0.2)
        
        if not scores:
            return 0.0
        
        # 加权平均
        weighted_sum = sum(score * weight for score, weight in zip(scores, weights))
        total_weight = sum(weights)
        
        return weighted_sum / total_weight if total_weight > 0 else 0.0


class KeywordQuality(BaseModel):
    """关键词质量评估结果"""
    
    # 覆盖度指标
    coverage: Optional[float] = Field(None, ge=0.0, le=1.0, description="关键词覆盖度")
    relevance: Optional[float] = Field(None, ge=0.0, le=1.0, description="相关性")
    diversity: Optional[float] = Field(None, ge=0.0, le=1.0, description="多样性")
    
    # 医学术语指标
    medical_accuracy: Optional[float] = Field(None, ge=0.0, le=1.0, description="医学术语准确性")
    terminology_ratio: Optional[float] = Field(None, ge=0.0, le=1.0, description="医学术语比例")
    
    # 统计指标
    keyword_count: Optional[int] = Field(None, description="关键词数量")
    avg_score: Optional[float] = Field(None, ge=0.0, le=1.0, description="平均分数")
    
    # 综合评分
    overall_score: Optional[float] = Field(None, ge=0.0, le=1.0, description="综合质量分数")
    quality_level: Optional[QualityLevel] = Field(None, description="质量等级")
    
    # 评估元信息
    evaluation_method: Optional[str] = Field(None, description="评估方法")
    evaluated_at: datetime = Field(default_factory=datetime.now, description="评估时间")
    
    def calculate_overall_score(self) -> float:
        """计算综合质量分数"""
        scores = []
        weights = []
        
        if self.relevance is not None:
            scores.append(self.relevance)
            weights.append(0.3)
        
        if self.coverage is not None:
            scores.append(self.coverage)
            weights.append(0.25)
        
        if self.diversity is not None:
            scores.append(self.diversity)
            weights.append(0.2)
        
        if self.medical_accuracy is not None:
            scores.append(self.medical_accuracy)
            weights.append(0.25)
        
        if not scores:
            return 0.0
        
        # 加权平均
        weighted_sum = sum(score * weight for score, weight in zip(scores, weights))
        total_weight = sum(weights)
        
        return weighted_sum / total_weight if total_weight > 0 else 0.0


class MetadataInfo(BaseModel):
    """完整的元数据信息"""
    
    # 基础信息
    document_id: str = Field(..., description="文档ID")
    chunk_id: str = Field(..., description="文本块ID")
    
    # 核心元数据
    summary: Optional[DocumentSummary] = Field(None, description="摘要信息")
    keywords: List[KeywordInfo] = Field(default_factory=list, description="关键词列表")
    
    # 质量评估
    summary_quality: Optional[SummaryQuality] = Field(None, description="摘要质量")
    keyword_quality: Optional[KeywordQuality] = Field(None, description="关键词质量")
    
    # 处理信息
    processing_status: str = Field(default="pending", description="处理状态")
    processing_time: Optional[float] = Field(None, description="总处理时间")
    error_message: Optional[str] = Field(None, description="错误信息")
    
    # 元信息
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")
    updated_at: Optional[datetime] = Field(None, description="更新时间")
    version: str = Field(default="1.0", description="版本号")
    
    @validator('keywords')
    def validate_keywords(cls, v):
        if len(v) > 20:
            # 只保留前20个最高分的关键词
            return sorted(v, key=lambda x: x.score, reverse=True)[:20]
        return v
    
    def get_medical_keywords(self) -> List[KeywordInfo]:
        """获取医学相关关键词"""
        return [kw for kw in self.keywords if kw.is_medical_term()]
    
    def get_top_keywords(self, n: int = 5) -> List[KeywordInfo]:
        """获取前N个关键词"""
        return sorted(self.keywords, key=lambda x: x.score, reverse=True)[:n]
    
    def get_keywords_by_category(self, category: MedicalCategory) -> List[KeywordInfo]:
        """按分类获取关键词"""
        return [kw for kw in self.keywords if kw.category == category]
    
    def update_processing_status(self, status: str, error: Optional[str] = None):
        """更新处理状态"""
        self.processing_status = status
        self.updated_at = datetime.now()
        if error:
            self.error_message = error
    
    def is_processing_complete(self) -> bool:
        """检查处理是否完成"""
        return self.processing_status == "completed"
    
    def has_quality_data(self) -> bool:
        """检查是否有质量评估数据"""
        return self.summary_quality is not None or self.keyword_quality is not None


class ProcessingTask(BaseModel):
    """处理任务模型"""
    
    task_id: str = Field(..., description="任务ID")
    document_id: str = Field(..., description="文档ID")
    chunk_id: str = Field(..., description="文本块ID")
    chunk_text: str = Field(..., description="文本内容")
    
    # 任务配置
    generate_summary: bool = Field(default=True, description="是否生成摘要")
    extract_keywords: bool = Field(default=True, description="是否提取关键词")
    evaluate_quality: bool = Field(default=True, description="是否评估质量")
    
    # 任务状态
    status: str = Field(default="pending", description="任务状态")
    priority: int = Field(default=1, description="任务优先级")
    retry_count: int = Field(default=0, description="重试次数")
    max_retries: int = Field(default=3, description="最大重试次数")
    
    # 时间信息
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")
    started_at: Optional[datetime] = Field(None, description="开始时间")
    completed_at: Optional[datetime] = Field(None, description="完成时间")
    
    # 结果
    result: Optional[MetadataInfo] = Field(None, description="处理结果")
    error_message: Optional[str] = Field(None, description="错误信息")
    
    def can_retry(self) -> bool:
        """检查是否可以重试"""
        return self.retry_count < self.max_retries
    
    def mark_started(self):
        """标记任务开始"""
        self.status = "processing"
        self.started_at = datetime.now()
    
    def mark_completed(self, result: MetadataInfo):
        """标记任务完成"""
        self.status = "completed"
        self.completed_at = datetime.now()
        self.result = result
    
    def mark_failed(self, error: str):
        """标记任务失败"""
        self.status = "failed"
        self.error_message = error
        self.retry_count += 1
    
    def get_processing_time(self) -> Optional[float]:
        """获取处理时间"""
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None