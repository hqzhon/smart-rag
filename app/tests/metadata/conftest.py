"""元数据模块测试配置文件"""

import pytest
import asyncio
import os
import tempfile
import shutil
import gc
from typing import Generator, AsyncGenerator
from unittest.mock import Mock, AsyncMock

# 导入测试配置
from .test_config import set_test_env_vars, clear_test_env_vars, get_test_config

# 导入测试所需的模块
from app.metadata.clients.qianwen_client import QianwenClient
from app.metadata.extractors.keybert_extractor import KeyBERTExtractor
from app.metadata.evaluators.quality_evaluator import QualityEvaluator


@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """设置测试环境"""
    # 设置测试环境变量
    set_test_env_vars()
    yield
    # 清理测试环境变量
    clear_test_env_vars()

# 测试配置
TEST_CONFIG = {
    "qianwen_api_key": os.getenv("QIANWEN_API_KEY", "test-api-key"),
    "test_timeout": 30,
    "batch_size": 5,
    "max_workers": 2,
    "enable_real_api": os.getenv("ENABLE_REAL_API", "false").lower() == "true",
    "test_data_dir": os.path.join(os.path.dirname(__file__), "test_data"),
    "temp_dir": None
}

@pytest.fixture(scope="session")
def event_loop():
    """创建事件循环"""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope="session")
def test_config():
    """测试配置"""
    return TEST_CONFIG.copy()

@pytest.fixture(scope="session")
def temp_directory():
    """临时目录"""
    temp_dir = tempfile.mkdtemp(prefix="metadata_test_")
    TEST_CONFIG["temp_dir"] = temp_dir
    yield temp_dir
    shutil.rmtree(temp_dir, ignore_errors=True)

@pytest.fixture
def sample_medical_texts():
    """医学文本样本"""
    return [
        {
            "chunk_id": "medical_001",
            "text": "患者，男性，65岁，主诉胸痛3小时。患者3小时前无明显诱因出现胸骨后疼痛，呈压榨性，向左肩背部放射，伴有出汗、恶心。既往有高血压病史10年，糖尿病史5年，长期服用降压药和降糖药。体格检查：血压160/95mmHg，心率98次/分，心律齐，心音低钝。心电图显示ST段抬高，肌钙蛋白升高。诊断为急性ST段抬高型心肌梗死。给予阿司匹林、氯吡格雷双联抗血小板治疗，阿托伐他汀调脂治疗，并急诊行冠状动脉介入治疗。"
        },
        {
            "chunk_id": "medical_002",
            "text": "患者，女性，45岁，因反复咳嗽、咳痰2个月就诊。患者2个月前开始出现干咳，逐渐出现白色泡沫样痰，偶有血丝。伴有低热、乏力、食欲减退、体重下降约5kg。既往体健，无结核病接触史。胸部CT显示右上肺空洞性病变，痰涂片抗酸杆菌阳性。诊断为肺结核。给予异烟肼、利福平、乙胺丁醇、吡嗪酰胺四联抗结核治疗。"
        },
        {
            "chunk_id": "medical_003",
            "text": "患者，男性，28岁，因车祸致头部外伤2小时急诊入院。患者2小时前骑摩托车与汽车相撞，当时意识丧失约5分钟，醒后诉头痛、恶心、呕吐。体格检查：神志清楚，右侧颞部可见长约8cm的挫裂伤，GCS评分14分。头颅CT显示右侧颞叶脑挫裂伤，少量硬膜下血肿。给予止血、脱水降颅压、预防感染等治疗。"
        }
    ]

@pytest.fixture
def sample_general_texts():
    """一般文本样本"""
    return [
        {
            "chunk_id": "general_001",
            "text": "人工智能技术在医疗领域的应用越来越广泛。机器学习算法可以帮助医生进行疾病诊断，深度学习模型能够分析医学影像，自然语言处理技术可以处理电子病历。这些技术的发展为医疗行业带来了革命性的变化，提高了诊断准确性，降低了医疗成本，改善了患者体验。"
        },
        {
            "chunk_id": "general_002",
            "text": "云计算技术为现代企业提供了灵活、可扩展的IT基础设施解决方案。通过云服务，企业可以按需获取计算资源，降低硬件投资成本，提高业务敏捷性。主要的云服务模式包括基础设施即服务(IaaS)、平台即服务(PaaS)和软件即服务(SaaS)。"
        },
        {
            "chunk_id": "general_003",
            "text": "区块链技术是一种分布式账本技术，具有去中心化、不可篡改、透明公开等特点。它在数字货币、供应链管理、身份认证、智能合约等领域有着广泛的应用前景。区块链技术的核心是通过密码学和共识机制确保数据的安全性和一致性。"
        }
    ]

@pytest.fixture
def mock_qianwen_client():
    """模拟千问客户端"""
    client = Mock(spec=QianwenClient)
    
    # 模拟API响应
    async def mock_generate_text(prompt, **kwargs):
        if "摘要" in prompt:
            return "这是一个生成的摘要，包含了原文的主要信息和关键点。"
        else:
            return "这是生成的文本内容。"
    
    client.generate_text = AsyncMock(side_effect=mock_generate_text)
    client.generate_summary = AsyncMock(return_value="生成的摘要内容")
    client.batch_generate_summaries = AsyncMock(return_value=["摘要1", "摘要2", "摘要3"])
    client.health_check = AsyncMock(return_value=True)
    client.get_stats = Mock(return_value={
        "total_requests": 0,
        "total_tokens": 0,
        "success_count": 0,
        "error_count": 0,
        "average_response_time": 0.0
    })
    client.reset_stats = Mock()
    client.close = AsyncMock()
    
    # 模拟上下文管理器
    async def mock_aenter():
        return client
    
    async def mock_aexit(exc_type, exc_val, exc_tb):
        pass
    
    client.__aenter__ = AsyncMock(side_effect=mock_aenter)
    client.__aexit__ = AsyncMock(side_effect=mock_aexit)
    
    return client

@pytest.fixture
def mock_keybert_extractor():
    """模拟KeyBERT提取器"""
    extractor = Mock(spec=KeyBERTExtractor)
    
    # 模拟关键词提取结果
    async def mock_extract_keywords(text, chunk_id, **kwargs):
        from ..models.metadata_models import KeywordInfo, KeywordMethod, MedicalCategory
        from datetime import datetime
        
        # 根据文本内容生成不同的关键词
        if "心肌梗死" in text or "胸痛" in text:
            keywords = ["心肌梗死", "胸痛", "心电图", "介入治疗"]
            category = MedicalCategory.DISEASE
        elif "肺结核" in text or "咳嗽" in text:
            keywords = ["肺结核", "咳嗽", "抗结核治疗", "胸部CT"]
            category = MedicalCategory.SYMPTOM
        elif "人工智能" in text:
            keywords = ["人工智能", "机器学习", "深度学习", "医疗"]
            category = MedicalCategory.GENERAL
        else:
            keywords = ["关键词1", "关键词2", "关键词3"]
            category = MedicalCategory.GENERAL
        
        return KeywordInfo(
            chunk_id=chunk_id,
            keywords=keywords,
            keyword_scores=[0.9, 0.8, 0.7, 0.6][:len(keywords)],
            method=KeywordMethod.KEYBERT,
            medical_category=category,
            extracted_at=datetime.now()
        )
    
    extractor.extract_keywords = AsyncMock(side_effect=mock_extract_keywords)
    extractor.batch_extract_keywords = AsyncMock()
    extractor.health_check = AsyncMock(return_value=True)
    extractor.get_stats = Mock(return_value={
        "total_extracted": 0,
        "keybert_success": 0,
        "jieba_fallback": 0,
        "average_extraction_time": 0.0
    })
    extractor.reset_stats = Mock()
    
    return extractor

@pytest.fixture
def mock_quality_evaluator():
    """模拟质量评估器"""
    evaluator = Mock(spec=QualityEvaluator)
    
    # 模拟质量评估结果
    async def mock_evaluate_summary_quality(original_text, summary, **kwargs):
        from ..models.metadata_models import SummaryQuality, QualityLevel
        
        return SummaryQuality(
            overall_score=0.85,
            quality_level=QualityLevel.EXCELLENT,
            length_score=0.9,
            coherence_score=0.8,
            coverage_score=0.85,
            readability_score=0.9,
            medical_relevance_score=0.7,
            information_density_score=0.8,
            evaluation_time=0.1
        )
    
    async def mock_evaluate_keyword_quality(original_text, keywords, **kwargs):
        from ..models.metadata_models import KeywordQuality, QualityLevel
        
        return KeywordQuality(
            overall_score=0.75,
            quality_level=QualityLevel.GOOD,
            keyword_count=len(keywords),
            quantity_score=0.8,
            relevance_score=0.7,
            diversity_score=0.75,
            coverage_score=0.8,
            medical_specificity_score=0.6
        )
    
    evaluator.evaluate_summary_quality = AsyncMock(side_effect=mock_evaluate_summary_quality)
    evaluator.evaluate_keyword_quality = AsyncMock(side_effect=mock_evaluate_keyword_quality)
    evaluator.batch_evaluate_quality = AsyncMock()
    evaluator.health_check = AsyncMock(return_value=True)
    evaluator.get_stats = Mock(return_value={
        "total_evaluated": 0,
        "summary_evaluations": 0,
        "keyword_evaluations": 0,
        "average_evaluation_time": 0.0
    })
    evaluator.reset_stats = Mock()
    
    return evaluator

@pytest.fixture
async def real_qianwen_client(test_config):
    """真实的千问客户端（仅在启用真实API时使用）"""
    if not test_config["enable_real_api"]:
        pytest.skip("真实API测试被禁用")
    
    client = QianwenClient(api_key=test_config["qianwen_api_key"])
    yield client
    await client.close()


@pytest.fixture
def test_data_files(temp_directory):
    """创建测试数据文件"""
    test_files = {}
    
    # 创建医学词典文件
    medical_terms_file = os.path.join(temp_directory, "medical_terms.txt")
    with open(medical_terms_file, "w", encoding="utf-8") as f:
        f.write("心肌梗死\n冠心病\n高血压\n糖尿病\n肺结核\n")
    test_files["medical_terms"] = medical_terms_file
    
    # 创建停用词文件
    stop_words_file = os.path.join(temp_directory, "stop_words.txt")
    with open(stop_words_file, "w", encoding="utf-8") as f:
        f.write("的\n了\n在\n是\n我\n有\n和\n就\n不\n人\n")
    test_files["stop_words"] = stop_words_file
    
    # 创建测试配置文件
    config_file = os.path.join(temp_directory, "test_config.json")
    import json
    with open(config_file, "w", encoding="utf-8") as f:
        json.dump({
            "qianwen_api_key": "test-key",
            "max_length": 200,
            "language": "中文",
            "max_keywords": 10,
            "min_keyword_length": 2
        }, f, ensure_ascii=False, indent=2)
    test_files["config"] = config_file
    
    return test_files

# 测试标记
pytestmark = [
    pytest.mark.asyncio,
    pytest.mark.timeout(300)  # 5分钟超时
]

# 测试钩子
def pytest_configure(config):
    """配置pytest"""
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m 'not slow'')"
    )
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests"
    )
    config.addinivalue_line(
        "markers", "performance: marks tests as performance tests"
    )
    config.addinivalue_line(
        "markers", "real_api: marks tests that require real API access"
    )

def pytest_collection_modifyitems(config, items):
    """修改测试项目"""
    # 为性能测试添加slow标记
    for item in items:
        if "performance" in item.nodeid or "stress" in item.nodeid:
            item.add_marker(pytest.mark.slow)
        
        # 为集成测试添加integration标记
        if "integration" in item.nodeid or "end_to_end" in item.nodeid:
            item.add_marker(pytest.mark.integration)
        
        # 为需要真实API的测试添加real_api标记
        if "real_" in item.name or "ENABLE_REAL_API" in str(item.function):
            item.add_marker(pytest.mark.real_api)

@pytest.fixture(autouse=True)
def cleanup_after_test():
    """测试后清理"""
    yield
    # 测试完成后的清理工作
    import gc
    gc.collect()