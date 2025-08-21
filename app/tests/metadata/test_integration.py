"""元数据模块集成测试"""

import asyncio
import pytest
import os
from typing import List, Dict, Any
from datetime import datetime
import tempfile
import json

# 导入元数据模块组件
from app.metadata.models.metadata_models import (
    DocumentSummary, KeywordInfo, MetadataInfo, ProcessingTask,
    SummaryMethod, KeywordMethod, QualityLevel, MedicalCategory
)
from app.metadata.clients.qianwen_client import QianwenClient
from app.metadata.summarizers.lightweight_summarizer import LightweightSummaryGenerator
from app.metadata.extractors.keybert_extractor import KeyBERTExtractor
from app.metadata.evaluators.quality_evaluator import QualityEvaluator
from app.metadata.processors.async_processor import AsyncMetadataProcessor, TaskPriority

class TestMetadataIntegration:
    """元数据模块集成测试类"""
    
    @pytest.fixture
    def sample_medical_text(self):
        """医学文本样本"""
        return """
        患者，男性，65岁，主诉胸痛3小时。患者3小时前无明显诱因出现胸骨后疼痛，
        呈压榨性，向左肩背部放射，伴有出汗、恶心。既往有高血压病史10年，
        糖尿病史5年，长期服用降压药和降糖药。体格检查：血压160/95mmHg，
        心率98次/分，心律齐，心音低钝。心电图显示ST段抬高，肌钙蛋白升高。
        诊断为急性ST段抬高型心肌梗死。给予阿司匹林、氯吡格雷双联抗血小板治疗，
        阿托伐他汀调脂治疗，并急诊行冠状动脉介入治疗。
        """
    
    @pytest.fixture
    def sample_general_text(self):
        """一般文本样本"""
        return """
        人工智能技术在医疗领域的应用越来越广泛。机器学习算法可以帮助医生
        进行疾病诊断，深度学习模型能够分析医学影像，自然语言处理技术可以
        处理电子病历。这些技术的发展为医疗行业带来了革命性的变化，
        提高了诊断准确性，降低了医疗成本，改善了患者体验。
        """
    
    @pytest.fixture
    def qianwen_client(self):
        """千问客户端"""
        # 使用环境变量或测试配置
        api_key = os.getenv("QIANWEN_API_KEY", "test-api-key")
        return QianwenClient(api_key=api_key)
    
    @pytest.fixture
    def summarizer(self):
        """摘要生成器"""
        return LightweightSummaryGenerator()
    
    @pytest.fixture
    def extractor(self):
        """关键词提取器"""
        return KeyBERTExtractor(top_k=2)
    
    @pytest.fixture
    def evaluator(self):
        """质量评估器"""
        return QualityEvaluator()
    
    @pytest.fixture
    async def processor(self, summarizer, extractor, evaluator):
        """异步处理器"""
        processor = AsyncMetadataProcessor(
            summarizer=summarizer,
            extractor=extractor,
            evaluator=evaluator,
            max_workers=2,
            batch_size=5
        )
        await processor.start()
        yield processor
        await processor.stop()
    
    @pytest.mark.asyncio
    async def test_qianwen_client_basic(self, qianwen_client):
        """测试千问客户端基本功能"""
        # 健康检查
        health_status = await qianwen_client.health_check()
        assert isinstance(health_status, bool)
        
        # 获取统计信息
        stats = qianwen_client.get_stats()
        assert isinstance(stats, dict)
        assert "total_requests" in stats
        assert "total_tokens" in stats
    
    @pytest.mark.asyncio
    async def test_summarizer_integration(self, summarizer, sample_medical_text):
        """测试摘要生成器集成"""
        # 生成摘要
        summary = await summarizer.generate_summary(
            text=sample_medical_text,
            chunk_id="test-chunk-001"
        )
        
        # 验证结果
        assert isinstance(summary, DocumentSummary)
        assert summary.chunk_id == "test-chunk-001"
        assert len(summary.content) > 0
        assert summary.method in [SummaryMethod.QIANWEN_API, SummaryMethod.FALLBACK]
        assert isinstance(summary.created_at, datetime)
        
        # 验证摘要质量
        assert len(summary.content) >= 20  # 最小长度
        assert len(summary.content) <= 500  # 最大长度
    
    @pytest.mark.asyncio
    async def test_extractor_integration(self, extractor, sample_medical_text):
        """测试关键词提取器集成"""
        # 提取关键词
        keywords = await extractor.extract_keywords(
            text=sample_medical_text,
            chunk_id="test-chunk-002"
        )
        
        # 验证结果
        assert isinstance(keywords, KeywordInfo)
        assert keywords.chunk_id == "test-chunk-002"
        assert len(keywords.keywords) > 0
        assert keywords.method in [KeywordMethod.KEYBERT, KeywordMethod.JIEBA_FALLBACK]
        assert isinstance(keywords.medical_category, MedicalCategory)
        assert isinstance(keywords.extracted_at, datetime)
        
        # 验证关键词质量
        assert 2 <= len(keywords.keywords) <= 15
        assert all(len(kw) > 1 for kw in keywords.keywords)  # 关键词长度
    
    @pytest.mark.asyncio
    async def test_evaluator_integration(self, evaluator, sample_medical_text):
        """测试质量评估器集成"""
        # 模拟摘要和关键词
        test_summary = "65岁男性患者出现急性胸痛，诊断为ST段抬高型心肌梗死，给予双联抗血小板和介入治疗。"
        test_keywords = ["心肌梗死", "胸痛", "ST段抬高", "介入治疗", "抗血小板"]
        
        # 摘要质量评估
        summary_quality = await evaluator.evaluate_summary_quality(
            original_text=sample_medical_text,
            summary=test_summary
        )
        
        # 关键词质量评估
        keyword_quality = await evaluator.evaluate_keyword_quality(
            original_text=sample_medical_text,
            keywords=test_keywords
        )
        
        # 验证摘要质量结果
        assert 0.0 <= summary_quality.overall_score <= 1.0
        assert isinstance(summary_quality.quality_level, QualityLevel)
        assert summary_quality.evaluated_at is not None
        
        # 验证关键词质量结果
        assert 0.0 <= keyword_quality.overall_score <= 1.0
        assert isinstance(keyword_quality.quality_level, QualityLevel)
        assert keyword_quality.keyword_count == len(test_keywords)
    
    @pytest.mark.asyncio
    async def test_processor_single_task(self, processor, sample_medical_text):
        """测试异步处理器单任务处理"""
        # 提交任务
        task_id = await processor.submit_task(
            chunk_id="test-chunk-003",
            text=sample_medical_text,
            priority=TaskPriority.HIGH
        )
        
        assert task_id is not None
        
        # 等待任务完成
        max_wait = 30  # 最大等待30秒
        wait_time = 0
        result = None
        
        while wait_time < max_wait:
            status = await processor.get_task_status(task_id)
            if status and status.get("status") == "completed":
                result = await processor.get_task_result(task_id)
                break
            elif status and status.get("status") == "failed":
                pytest.fail(f"任务处理失败: {status.get('error')}")
            
            await asyncio.sleep(1)
            wait_time += 1
        
        # 验证结果
        assert result is not None, "任务处理超时"
        assert isinstance(result, MetadataInfo)
        assert result.chunk_id == "test-chunk-003"
        assert result.summary is not None
        assert result.keywords is not None
        assert result.summary_quality is not None
        assert result.keyword_quality is not None
        assert result.processing_time > 0
    
    @pytest.mark.asyncio
    async def test_processor_batch_tasks(self, processor, sample_medical_text, sample_general_text):
        """测试异步处理器批量任务处理"""
        # 准备批量任务
        tasks = [
            {
                "chunk_id": f"batch-chunk-{i:03d}",
                "text": sample_medical_text if i % 2 == 0 else sample_general_text,
                "priority": TaskPriority.MEDIUM,
                "metadata": {"batch_id": "test-batch-001", "index": i}
            }
            for i in range(5)
        ]
        
        # 提交批量任务
        task_ids = await processor.submit_batch_tasks(tasks)
        assert len(task_ids) == 5
        
        # 等待所有任务完成
        max_wait = 60  # 最大等待60秒
        wait_time = 0
        completed_count = 0
        
        while wait_time < max_wait and completed_count < len(task_ids):
            completed_count = 0
            for task_id in task_ids:
                status = await processor.get_task_status(task_id)
                if status and status.get("status") in ["completed", "failed"]:
                    completed_count += 1
            
            if completed_count < len(task_ids):
                await asyncio.sleep(2)
                wait_time += 2
        
        # 验证结果
        results = []
        for task_id in task_ids:
            result = await processor.get_task_result(task_id)
            if result:
                results.append(result)
        
        assert len(results) >= 3, f"批量处理成功率过低: {len(results)}/{len(task_ids)}"
        
        # 验证每个结果
        for result in results:
            assert isinstance(result, MetadataInfo)
            assert result.summary is not None
            assert result.keywords is not None
            assert "batch_id" in result.metadata
    
    @pytest.mark.asyncio
    async def test_processor_statistics(self, processor, sample_medical_text):
        """测试异步处理器统计功能"""
        # 提交几个任务
        task_ids = []
        for i in range(3):
            task_id = await processor.submit_task(
                chunk_id=f"stats-chunk-{i:03d}",
                text=sample_medical_text,
                priority=TaskPriority.LOW
            )
            task_ids.append(task_id)
        
        # 等待任务完成
        await asyncio.sleep(10)
        
        # 获取统计信息
        stats = processor.get_stats()
        
        # 验证统计信息
        assert isinstance(stats, dict)
        assert "total_submitted" in stats
        assert "total_completed" in stats
        assert "current_queue_size" in stats
        assert stats["total_submitted"] >= 3
    
    @pytest.mark.asyncio
    async def test_end_to_end_workflow(self, sample_medical_text):
        """端到端工作流测试"""
        # 创建所有组件
        api_key = os.getenv("QIANWEN_API_KEY", "test-api-key")
        client = QianwenClient(api_key=api_key)
        
        try:
            summarizer = LightweightSummaryGenerator()
            extractor = KeyBERTExtractor()
            evaluator = QualityEvaluator()
            
            processor = AsyncMetadataProcessor(
                summarizer=summarizer,
                extractor=extractor,
                evaluator=evaluator,
                max_workers=1,
                enable_quality_check=True
            )
            
            await processor.start()
            
            try:
                # 提交任务
                task_id = await processor.submit_task(
                    chunk_id="e2e-test-chunk",
                    text=sample_medical_text,
                    priority=TaskPriority.HIGH,
                    metadata={"test_type": "end_to_end"}
                )
                
                # 等待完成
                max_wait = 30
                wait_time = 0
                result = None
                
                while wait_time < max_wait:
                    status = await processor.get_task_status(task_id)
                    if status and status.get("status") == "completed":
                        result = await processor.get_task_result(task_id)
                        break
                    elif status and status.get("status") == "failed":
                        pytest.fail(f"端到端测试失败: {status.get('error')}")
                    
                    await asyncio.sleep(1)
                    wait_time += 1
                
                # 全面验证结果
                assert result is not None, "端到端测试超时"
                assert isinstance(result, MetadataInfo)
                
                # 验证摘要
                assert result.summary is not None
                assert len(result.summary.content) > 20
                assert result.summary.method in [SummaryMethod.QIANWEN_API, SummaryMethod.FALLBACK]
                
                # 验证关键词
                assert result.keywords is not None
                assert len(result.keywords.keywords) >= 3
                assert result.keywords.method in [KeywordMethod.KEYBERT, KeywordMethod.JIEBA_FALLBACK]
                
                # 验证质量评估
                assert result.summary_quality is not None
                assert 0.0 <= result.summary_quality.overall_score <= 1.0
                assert result.keyword_quality is not None
                assert 0.0 <= result.keyword_quality.overall_score <= 1.0
                
                # 验证元数据
                assert result.processing_time > 0
                assert isinstance(result.processed_at, datetime)
                assert "test_type" in result.metadata
                assert result.metadata["test_type"] == "end_to_end"
                
                print(f"\n端到端测试成功完成:")
                print(f"摘要: {result.summary.content[:100]}...")
                print(f"关键词: {', '.join(result.keywords.keywords[:5])}")
                print(f"摘要质量分数: {result.summary_quality.overall_score:.3f}")
                print(f"关键词质量分数: {result.keyword_quality.overall_score:.3f}")
                print(f"处理时间: {result.processing_time:.2f}秒")
                
            finally:
                await processor.stop()
        
        finally:
            await client.close()
    
    def test_data_models_validation(self):
        """测试数据模型验证"""
        # 测试DocumentSummary
        summary = DocumentSummary(
            chunk_id="test-chunk",
            content="这是一个测试摘要",
            method=SummaryMethod.QIANWEN_API,
            confidence=0.8
        )
        assert summary.chunk_id == "test-chunk"
        assert summary.content == "这是一个测试摘要"
        assert summary.method == SummaryMethod.QIANWEN_API
        assert summary.confidence == 0.8
        
        # 测试KeywordInfo
        keywords = KeywordInfo(
            chunk_id="test-chunk",
            keywords=["关键词1", "关键词2", "关键词3"],
            keyword_scores=[0.9, 0.8, 0.7],
            method=KeywordMethod.KEYBERT,
            medical_category=MedicalCategory.DISEASE,
            extracted_at=datetime.now()
        )
        assert len(keywords.keywords) == 3
        assert len(keywords.keyword_scores) == 3
        assert keywords.medical_category == MedicalCategory.DISEASE
    
    @pytest.mark.asyncio
    async def test_error_handling(self, processor):
        """测试错误处理"""
        # 提交空文本任务
        task_id = await processor.submit_task(
            chunk_id="error-test-chunk",
            text="",  # 空文本
            priority=TaskPriority.LOW
        )
        
        # 等待任务完成或失败
        max_wait = 15
        wait_time = 0
        final_status = None
        
        while wait_time < max_wait:
            status = await processor.get_task_status(task_id)
            if status and status.get("status") in ["completed", "failed"]:
                final_status = status
                break
            
            await asyncio.sleep(1)
            wait_time += 1
        
        # 验证错误处理
        assert final_status is not None
        # 空文本应该被处理（可能生成默认结果）或失败
        assert final_status.get("status") in ["completed", "failed"]
    
    @pytest.mark.asyncio
    async def test_concurrent_processing(self, processor, sample_medical_text):
        """测试并发处理能力"""
        # 同时提交多个任务
        task_ids = []
        for i in range(10):
            task_id = await processor.submit_task(
                chunk_id=f"concurrent-chunk-{i:03d}",
                text=sample_medical_text,
                priority=TaskPriority.MEDIUM
            )
            task_ids.append(task_id)
        
        # 等待所有任务完成
        max_wait = 60
        wait_time = 0
        completed_tasks = 0
        
        while wait_time < max_wait:
            completed_tasks = 0
            for task_id in task_ids:
                status = await processor.get_task_status(task_id)
                if status and status.get("status") in ["completed", "failed"]:
                    completed_tasks += 1
            
            if completed_tasks >= len(task_ids) * 0.8:  # 80%完成率
                break
            
            await asyncio.sleep(2)
            wait_time += 2
        
        # 验证并发处理效果
        assert completed_tasks >= len(task_ids) * 0.7, f"并发处理成功率过低: {completed_tasks}/{len(task_ids)}"
        
        # 获取统计信息
        stats = processor.get_stats()
        assert stats["total_submitted"] >= 10

if __name__ == "__main__":
    # 运行测试
    pytest.main(["-v", __file__])