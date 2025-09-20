"""测试配置和模拟组件

为测试提供共享的模拟组件和夹具
"""

import pytest
import os
import tempfile
from unittest.mock import Mock, AsyncMock, MagicMock

from app.storage.database import DatabaseManager
from app.storage.vector_store import VectorStore
from app.retrieval.fusion_retriever import AdvancedFusionRetriever
from app.retrieval.multi_field_bm25 import RankBM25Retriever
from app.retrieval.reranker import QianwenReranker
from app.retrieval.query_transformer import QueryTransformer
from app.workflow.deepseek_client import DeepseekClient
from app.workflow.qianwen_client import QianwenClient
from app.metadata.extractors.keybert_extractor import KeyBERTExtractor


@pytest.fixture
def tmp_dirs():
    """创建临时输入和输出目录"""
    with tempfile.TemporaryDirectory() as input_dir:
        with tempfile.TemporaryDirectory() as output_dir:
            yield input_dir, output_dir


@pytest.fixture
def mock_db_manager():
    """创建模拟数据库管理器"""
    mock = AsyncMock()  # 移除spec限制，允许任意方法
    
    # 模拟方法
    mock.save_document.return_value = "doc_123"
    mock.get_document.return_value = {"id": "doc_123", "content": "测试内容"}
    mock.save_chunks.return_value = ["chunk_1", "chunk_2"]
    mock.get_chunks.return_value = [{"id": "chunk_1", "content": "块1"}, {"id": "chunk_2", "content": "块2"}]
    mock.save_chat_history.return_value = "chat_123"
    mock.get_chat_history.return_value = {"id": "chat_123", "messages": []}
    mock.save_metadata.return_value = "meta_123"
    mock.get_metadata.return_value = {"id": "meta_123", "keywords": ["测试"], "summary": "测试摘要"}
    
    return mock


@pytest.fixture
def mock_vector_store():
    """创建模拟向量存储"""
    mock = AsyncMock(spec=VectorStore)
    
    # 模拟方法
    mock.add_documents = AsyncMock(return_value=["id1", "id2"])
    mock.search = AsyncMock(return_value=[
        {"id": "id1", "content": "相关内容1", "metadata": {"source": "doc1.pdf"}, "score": 0.95},
        {"id": "id2", "content": "相关内容2", "metadata": {"source": "doc2.pdf"}, "score": 0.85}
    ])
    mock.similarity_search = AsyncMock(return_value=[
        {"id": "id1", "content": "相关内容1", "metadata": {"source": "doc1.pdf"}},
        {"id": "id2", "content": "相关内容2", "metadata": {"source": "doc2.pdf"}}
    ])
    mock.update_document = AsyncMock(return_value=True)
    mock.delete_document = AsyncMock(return_value=True)
    mock.get_collection_stats = AsyncMock(return_value={"document_count": 10, "embedding_dimension": 768})
    
    return mock


@pytest.fixture
def mock_retriever():
    """创建模拟检索器"""
    from app.retrieval.fusion_retriever import OptimizedFusionResult
    from app.retrieval.advanced_config import RetrievalPath, FusionMethod
    
    mock = AsyncMock(spec=AdvancedFusionRetriever)
    
    # 模拟文档结果
    mock_documents = [
        {"id": "id1", "content": "相关内容1", "metadata": {"source": "doc1.pdf"}, "score": 0.95},
        {"id": "id2", "content": "相关内容2", "metadata": {"source": "doc2.pdf"}, "score": 0.85}
    ]
    
    # 创建模拟的 OptimizedFusionResult 对象
    mock_optimized_result = OptimizedFusionResult(
        documents=mock_documents,
        total_time=0.1,
        path_results={},
        fusion_method=FusionMethod.WEIGHTED_RRF,
        query_analysis=None,
        progressive_stages=None,
        weight_adjustments=None,
        optimization_stats={},
        config_used={}
    )
    
    mock.retrieve_optimized = AsyncMock(return_value=mock_optimized_result)
    mock.retrieve = AsyncMock(return_value=mock_documents)
    mock.adaptive_retrieve = AsyncMock(return_value=mock_documents)
    mock.retrieve_single_path = AsyncMock(return_value=mock_documents)
    mock.multi_query_retrieve = AsyncMock(return_value=mock_documents)
    mock.update_config = Mock()
    mock.get_performance_stats = Mock(return_value={})
    
    return mock


@pytest.fixture
def mock_qianwen_embedding_rerank_client():
    """创建模拟千问客户端，用于embedding和rerank"""
    mock = AsyncMock()
    
    # 模拟方法 - 不使用spec限制，允许任意方法
    mock.get_embeddings.return_value = [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]]
    mock.rerank_documents.return_value = [
        {"page_content": "重排序内容", "metadata": {"source": "doc1.pdf", "score": 0.98}}
    ]
    mock.generate_summary.return_value = "这是生成的摘要"
    mock.extract_keywords.return_value = ["关键词1", "关键词2"]
    
    return mock


@pytest.fixture
def mock_reranker():
    """创建模拟增强重排序器"""
    from app.retrieval.enhanced_reranker import RerankResult, RerankStrategy
    
    mock = AsyncMock()
    
    # 创建模拟的 RerankResult 对象
    mock_rerank_result = RerankResult(
        documents=[
            {"id": "id2", "content": "相关内容2", "page_content": "相关内容2", "metadata": {"source": "doc2.pdf"}, "score": 0.95, "rerank_score": 0.98},
            {"id": "id1", "content": "相关内容1", "page_content": "相关内容1", "metadata": {"source": "doc1.pdf"}, "score": 0.85, "rerank_score": 0.88}
        ],
        rerank_time=0.1,
        strategy_used=RerankStrategy.QIANWEN_API,
        cache_hit=False,
        api_calls=1
    )
    
    # 模拟方法
    mock.rerank_documents.return_value = mock_rerank_result
    
    return mock


@pytest.fixture
def mock_query_transformer():
    """创建模拟查询转换器"""
    mock = Mock()
    
    # 模拟方法 - 不使用spec限制，避免方法不存在的问题
    mock.expand_query.return_value = ["原始查询", "扩展查询1", "扩展查询2"]
    mock.rewrite_query.return_value = "重写后的查询"
    mock.extract_keywords.return_value = ["关键词1", "关键词2", "关键词3"]
    mock.extract_medical_entities.return_value = {
        "diseases": ["高血压"],
        "symptoms": ["头痛"],
        "medications": ["降压药"]
    }
    
    return mock


@pytest.fixture
def mock_deepseek_client():
    """创建模拟DeepSeek客户端"""
    mock = AsyncMock()
    
    # 模拟方法 - 不使用spec限制，允许任意方法
    mock.generate_response.return_value = "这是DeepSeek生成的回复"
    mock.generate_stream_response.return_value = AsyncMock()
    mock.chat_completion.return_value = {
        "choices": [{"message": {"content": "DeepSeek回复"}}]
    }
    
    return mock





@pytest.fixture
def mock_keybert_extractor():
    """创建模拟KeyBERT关键词提取器，避免模型加载"""
    from app.metadata.models.metadata_models import KeywordInfo, KeywordMethod, MedicalCategory
    
    mock = AsyncMock(spec=KeyBERTExtractor)
    
    # 模拟extract_keywords方法返回KeywordInfo对象
    async def mock_extract_keywords(text, chunk_id=None, metadata=None):
        return KeywordInfo(
            chunk_id=chunk_id or "test_chunk",
            keywords=["关键词1", "关键词2", "关键词3"],
            keyword_scores=[0.9, 0.8, 0.7],
            method=KeywordMethod.KEYBERT,
            medical_category=MedicalCategory.GENERAL,
            processing_time=0.1,
            metadata=metadata or {}
        )
    
    mock.extract_keywords = mock_extract_keywords
    mock.model_available = True
    mock._models_initialized = True
    
    return mock


@pytest.fixture
def sample_document():
    """创建示例文档数据"""
    return {
        "document_id": "doc_123",
        "filename": "test.pdf",
        "raw_text": "这是原始文本内容",
        "cleaned_text": "这是清理后的文本内容",
        "standardized_text": "这是标准化后的文本内容",
        "chunks": ["这是第一个文本块", "这是第二个文本块"],
        "metadata": {
            "title": "测试文档",
            "keywords": ["关键词1", "关键词2"],
            "summary": "这是文档摘要"
        }
    }


@pytest.fixture
def sample_query_result():
    """创建示例查询结果数据"""
    return {
        "query": "测试查询",
        "response": "这是查询的回复内容",
        "documents": [
            {"id": "id1", "content": "相关内容1", "metadata": {"source": "doc1.pdf"}, "score": 0.95},
            {"id": "id2", "content": "相关内容2", "metadata": {"source": "doc2.pdf"}, "score": 0.85}
        ],
        "processing_time": 0.5
    }