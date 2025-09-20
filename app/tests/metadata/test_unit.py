"""元数据模块单元测试"""

import asyncio
import pytest
import os
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime
from typing import List, Dict, Any

# 导入测试目标
from app.metadata.models.metadata_models import (
    DocumentSummary, KeywordInfo, SummaryQuality, KeywordQuality,
    SummaryMethod, KeywordMethod, QualityLevel, MedicalCategory
)
from app.metadata.clients.qianwen_client import QianwenClient
from app.metadata.extractors.keybert_extractor import KeyBERTExtractor
from app.metadata.evaluators.quality_evaluator import QualityEvaluator

class TestQianwenClient:
    """千问客户端单元测试"""
    
    def test_client_initialization(self):
        """测试客户端初始化"""
        client = QianwenClient(api_key="test-key")
        assert client.api_key == "test-key"
        assert client.base_url == "https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation"
        assert client.model == "qwen-turbo"
        assert client.session is None
        assert client.stats["total_requests"] == 0
    
    def test_client_custom_config(self):
        """测试客户端自定义配置"""
        client = QianwenClient(
            api_key="test-key",
            base_url="https://custom.api.com",
            model="custom-model",
            timeout=60
        )
        assert client.base_url == "https://custom.api.com"
        assert client.model == "custom-model"
        assert client.timeout == 60
    
    @pytest.mark.asyncio
    async def test_session_management(self):
        """测试会话管理"""
        client = QianwenClient(api_key="test-key")
        
        # 测试会话创建
        async with client:
            assert client.session is not None
        
        # 测试会话关闭
        assert client.session.closed
    
    def test_build_prompt(self):
        """测试提示词构建"""
        client = QianwenClient(api_key="test-key")
        
        prompt = client._build_prompt(
            text="这是测试文本",
            max_length=100,
            language="中文"
        )
        
        assert "这是测试文本" in prompt
        assert "100" in prompt
        assert "中文" in prompt
    
    def test_stats_tracking(self):
        """测试统计信息跟踪"""
        client = QianwenClient(api_key="test-key")
        
        # 初始统计
        stats = client.get_stats()
        assert stats["total_requests"] == 0
        assert stats["total_tokens"] == 0
        assert stats["success_count"] == 0
        assert stats["error_count"] == 0
        
        # 重置统计
        client.reset_stats()
        stats = client.get_stats()
        assert all(v == 0 for v in stats.values())

class TestQualityEvaluator:
    """质量评估器单元测试"""
    
    def test_evaluator_initialization(self):
        """测试评估器初始化"""
        evaluator = QualityEvaluator(
            min_summary_length=20,
            max_summary_length=500,
            min_keyword_count=3,
            max_keyword_count=15
        )
        
        assert evaluator.min_summary_length == 20
        assert evaluator.max_summary_length == 500
        assert evaluator.min_keyword_count == 3
        assert evaluator.max_keyword_count == 15
        assert evaluator.total_summary_evaluations == 0
    
    def test_calculate_compression_ratio(self):
        """测试压缩比计算"""
        evaluator = QualityEvaluator()
        
        original = "这是一段很长的原始文本内容，包含很多详细信息"
        summary = "这是摘要"
        
        ratio = evaluator._calculate_compression_ratio(original, summary)
        
        assert 0 < ratio < 1
        assert ratio == len(summary) / len(original)
    
    def test_calculate_information_density(self):
        """测试信息密度计算"""
        evaluator = QualityEvaluator()
        
        # 高信息密度文本
        high_density = "心肌梗死、胸痛、心电图异常、肌钙蛋白升高"
        density_high = evaluator._calculate_information_density(high_density)
        
        # 低信息密度文本
        low_density = "这是一段普通的文本内容，没有特别的信息"
        density_low = evaluator._calculate_information_density(low_density)
        
        assert density_high > density_low
        assert 0 <= density_high <= 1
        assert 0 <= density_low <= 1
    
    def test_calculate_readability(self):
        """测试可读性计算"""
        evaluator = QualityEvaluator()
        
        # 简单文本
        simple_text = "这是简单的文本。句子很短。"
        readability_simple = evaluator._calculate_readability(simple_text)
        
        # 复杂文本
        complex_text = "这是一个包含复杂句式结构和多个从句的长句子，其中包含了大量的专业术语和技术词汇。"
        readability_complex = evaluator._calculate_readability(complex_text)
        
        assert 0 <= readability_simple <= 1
        assert 0 <= readability_complex <= 1
        # 简单文本的可读性应该更高
        assert readability_simple >= readability_complex
    
    def test_calculate_medical_relevance(self):
        """测试医学相关性计算"""
        evaluator = QualityEvaluator()
        
        # 医学文本
        medical_text = "患者出现心肌梗死，需要进行冠状动脉介入治疗"
        relevance_medical = evaluator._calculate_medical_relevance(medical_text)
        
        # 非医学文本
        non_medical_text = "今天天气很好，适合出去散步"
        relevance_non_medical = evaluator._calculate_medical_relevance(non_medical_text)
        
        assert 0 <= relevance_medical <= 1
        assert 0 <= relevance_non_medical <= 1
        assert relevance_medical > relevance_non_medical
    
    @pytest.mark.asyncio
    async def test_evaluate_summary_quality(self):
        """测试摘要质量评估"""
        evaluator = QualityEvaluator()
        
        original_text = "患者，男性，65岁，主诉胸痛3小时。心电图显示ST段抬高，诊断为急性心肌梗死。"
        summary = "65岁男性患者胸痛3小时，心电图ST段抬高，诊断急性心肌梗死。"
        
        quality = await evaluator.evaluate_summary_quality(original_text, summary)
        
        # 验证结果
        assert isinstance(quality, SummaryQuality)
        assert 0 <= quality.overall_score <= 1
        assert isinstance(quality.quality_level, QualityLevel)
        assert quality.evaluation_time > 0
        assert 0 <= quality.length_score <= 1
        assert 0 <= quality.coherence_score <= 1
        assert 0 <= quality.coverage_score <= 1
        assert 0 <= quality.readability_score <= 1
    
    @pytest.mark.asyncio
    async def test_evaluate_keyword_quality(self):
        """测试关键词质量评估"""
        evaluator = QualityEvaluator()
        
        original_text = "患者出现急性心肌梗死，进行了冠状动脉介入治疗"
        keywords = ["心肌梗死", "冠状动脉", "介入治疗"]
        
        quality = await evaluator.evaluate_keyword_quality(original_text, keywords)
        
        # 验证结果
        assert isinstance(quality, KeywordQuality)
        assert 0 <= quality.overall_score <= 1
        assert isinstance(quality.quality_level, QualityLevel)
        assert quality.keyword_count == 3
        assert 0 <= quality.quantity_score <= 1
        assert 0 <= quality.relevance_score <= 1
        assert 0 <= quality.diversity_score <= 1
        assert 0 <= quality.coverage_score <= 1
    
    def test_determine_quality_level(self):
        """测试质量等级判定"""
        evaluator = QualityEvaluator()
        
        # 高质量
        assert evaluator._determine_quality_level(0.9) == QualityLevel.EXCELLENT
        
        # 中等质量
        assert evaluator._determine_quality_level(0.7) == QualityLevel.GOOD
        
        # 低质量
        assert evaluator._determine_quality_level(0.4) == QualityLevel.FAIR
        
        # 边界情况
        assert evaluator._determine_quality_level(0.8) == QualityLevel.EXCELLENT
        assert evaluator._determine_quality_level(0.6) == QualityLevel.GOOD
    
    @pytest.mark.asyncio
    async def test_batch_evaluate_quality(self):
        """测试批量质量评估"""
        evaluator = QualityEvaluator()
        
        evaluations = [
            {
                "type": "summary",
                "original_text": "原始文本1",
                "generated_content": "摘要1"
            },
            {
                "type": "keywords",
                "original_text": "原始文本2",
                "generated_content": ["关键词1", "关键词2"]
            }
        ]
        
        results = await evaluator.batch_evaluate_quality(evaluations)
        
        assert len(results) == 2
        assert isinstance(results[0], SummaryQuality)
        assert isinstance(results[1], KeywordQuality)

class TestDataModels:
    """数据模型单元测试"""
    
    def test_document_summary_model(self):
        """测试DocumentSummary模型"""
        summary = DocumentSummary(
            chunk_id="test-chunk",
            content="这是测试摘要",
            method=SummaryMethod.QIANWEN_API,
            created_at=datetime.now(),
            metadata={"test": True}
        )
        
        assert summary.chunk_id == "test-chunk"
        assert summary.content == "这是测试摘要"
        assert summary.method == SummaryMethod.QIANWEN_API
        assert isinstance(summary.created_at, datetime)
        assert summary.metadata["test"] is True
    
    def test_keyword_info_model(self):
        """测试KeywordInfo模型"""
        keywords = KeywordInfo(
            chunk_id="test-chunk",
            keywords=["关键词1", "关键词2"],
            keyword_scores=[0.9, 0.8],
            method=KeywordMethod.KEYBERT,
            medical_category=MedicalCategory.DISEASE,
            extracted_at=datetime.now()
        )
        
        assert keywords.chunk_id == "test-chunk"
        assert len(keywords.keywords) == 2
        assert len(keywords.keyword_scores) == 2
        assert keywords.method == KeywordMethod.KEYBERT
        assert keywords.medical_category == MedicalCategory.DISEASE
    
    def test_summary_quality_model(self):
        """测试SummaryQuality模型"""
        quality = SummaryQuality(
            overall_score=0.85,
            quality_level=QualityLevel.EXCELLENT,
            length_score=0.9,
            coherence_score=0.8,
            coverage_score=0.85,
            readability_score=0.9,
            medical_relevance_score=0.7,
            information_density_score=0.8,
            evaluation_time=0.5
        )
        
        assert quality.overall_score == 0.85
        assert quality.quality_level == QualityLevel.EXCELLENT
        assert quality.evaluation_time == 0.5
    
    def test_keyword_quality_model(self):
        """测试KeywordQuality模型"""
        quality = KeywordQuality(
            overall_score=0.75,
            quality_level=QualityLevel.GOOD,
            keyword_count=5,
            quantity_score=0.8,
            relevance_score=0.7,
            diversity_score=0.75,
            coverage_score=0.8,
            medical_specificity_score=0.6
        )
        
        assert quality.overall_score == 0.75
        assert quality.quality_level == QualityLevel.GOOD
        assert quality.keyword_count == 5
    
    def test_model_validation(self):
        """测试模型验证"""
        # 测试无效数据
        with pytest.raises(ValueError):
            DocumentSummary(
                chunk_id="",  # 空chunk_id应该失败
                content="测试摘要",
                method=SummaryMethod.QIANWEN_API,
                created_at=datetime.now()
            )
        
        # 测试关键词和分数长度不匹配
        with pytest.raises(ValueError):
            KeywordInfo(
                chunk_id="test-chunk",
                keywords=["关键词1", "关键词2"],
                keyword_scores=[0.9],  # 长度不匹配
                method=KeywordMethod.KEYBERT,
                medical_category=MedicalCategory.GENERAL,
                extracted_at=datetime.now()
            )

if __name__ == "__main__":
    # 运行测试
    pytest.main(["-v", __file__])