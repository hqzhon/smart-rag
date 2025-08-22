"""检索模块测试

使用conftest.py中的模拟组件进行测试
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock

from app.retrieval.retriever import HybridRetriever
from app.retrieval.bm25_retriever import RankBM25Retriever
from app.retrieval.reranker import QianwenReranker
from app.retrieval.query_transformer import QueryTransformer


class TestRetriever:
    """检索器测试类"""
    
    @pytest.fixture
    async def retriever(self, mock_vector_store, mock_query_transformer):
        """创建检索器实例"""
        retriever = HybridRetriever(
            vector_store=mock_vector_store, 
            query_transformer=mock_query_transformer,
            embedding_model=Mock()
        )
        return retriever
    
    @pytest.mark.asyncio
    async def test_retrieve(self, retriever, mock_vector_store):
        """测试检索功能"""
        # 设置模拟返回值
        mock_vector_store.search.return_value = [
            {"id": "id1", "content": "相关内容1", "metadata": {"source": "doc1.pdf"}, "score": 0.95},
            {"id": "id2", "content": "相关内容2", "metadata": {"source": "doc2.pdf"}, "score": 0.85}
        ]
        
        # 执行检索
        results = await retriever.retrieve("测试查询", top_k=5)
        
        # 验证结果
        assert len(results) == 2
        assert results[0]["id"] == "id1"
        assert results[0]["content"] == "相关内容1"
        assert results[0]["score"] == 0.95
        
        # 验证调用
        mock_vector_store.search.assert_called_once_with("测试查询", top_k=5)
    
    @pytest.mark.asyncio
    async def test_adaptive_retrieve(self, retriever):
        """测试自适应检索功能"""
        # 模拟基本检索方法
        with patch.object(retriever, 'retrieve') as mock_retrieve:
            mock_retrieve.return_value = [
                {"id": "id1", "content": "相关内容1", "metadata": {"source": "doc1.pdf"}, "score": 0.95},
                {"id": "id2", "content": "相关内容2", "metadata": {"source": "doc2.pdf"}, "score": 0.85}
            ]
            
            # 执行自适应检索
            results = await retriever.adaptive_retrieve("测试查询", top_k=5)
            
            # 验证结果
            assert len(results) == 2
            assert results[0]["id"] == "id1"
            
            # 验证调用
            mock_retrieve.assert_called_once_with("测试查询", top_k=5)
    
    @pytest.mark.asyncio
    async def test_multi_query_retrieve(self, retriever):
        """测试多查询检索功能"""
        # 模拟查询转换器
        mock_query_transformer = Mock()
        mock_query_transformer.expand_query.return_value = ["原始查询", "扩展查询1", "扩展查询2"]
        retriever.query_transformer = mock_query_transformer
        
        # 模拟基本检索方法
        with patch.object(retriever, 'retrieve') as mock_retrieve:
            mock_retrieve.side_effect = [
                [{"id": "id1", "content": "相关内容1", "metadata": {"source": "doc1.pdf"}, "score": 0.95}],
                [{"id": "id2", "content": "相关内容2", "metadata": {"source": "doc2.pdf"}, "score": 0.85}],
                [{"id": "id3", "content": "相关内容3", "metadata": {"source": "doc3.pdf"}, "score": 0.75}]
            ]
            
            # 执行多查询检索
            results = await retriever.multi_query_retrieve("测试查询", top_k=5)
            
            # 验证结果
            assert len(results) == 3
            assert results[0]["id"] == "id1"
            assert results[1]["id"] == "id2"
            assert results[2]["id"] == "id3"
            
            # 验证调用
            mock_query_transformer.expand_query.assert_called_once_with("测试查询")
            assert mock_retrieve.call_count == 3


class TestHybridRetriever:
    """混合检索器测试类"""
    
    @pytest.fixture
    def hybrid_retriever(self, mock_vector_store, mock_query_transformer):
        """创建混合检索器实例"""
        mock_embedding_model = Mock()
        mock_embedding_model.embed_query = AsyncMock(return_value=[0.1, 0.2, 0.3])
        mock_embedding_model.embed_documents = AsyncMock(return_value=[[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]])
        
        retriever = HybridRetriever(
            vector_store=mock_vector_store,
            query_transformer=mock_query_transformer,
            embedding_model=mock_embedding_model
        )
        return retriever
    
    @pytest.mark.asyncio
    async def test_retrieve(self, hybrid_retriever, mock_vector_store):
        """测试混合检索功能"""
        # 设置模拟返回值 - 使用similarity_search方法
        mock_vector_store.similarity_search.return_value = [
            {"id": "id1", "content": "相关内容1", "metadata": {"source": "doc1.pdf"}},
            {"id": "id2", "content": "相关内容2", "metadata": {"source": "doc2.pdf"}}
        ]
        
        # 执行混合检索
        results = await hybrid_retriever.retrieve("测试查询", top_k=2)
        
        # 验证结果
        assert isinstance(results, list)
        # 由于涉及复杂的BM25和向量融合，我们主要验证方法被调用
        mock_vector_store.similarity_search.assert_called()
    
    @pytest.mark.asyncio
    async def test_retrieve_with_metadata_filter(self, hybrid_retriever, mock_vector_store, mock_query_transformer):
        """测试带元数据过滤的混合检索功能"""
        # 设置查询转换器返回关键词
        mock_query_transformer.extract_keywords.return_value = ["高血压", "治疗"]
        
        # 设置模拟返回值
        mock_vector_store.similarity_search.return_value = [
            {"id": "id1", "content": "高血压治疗内容", "metadata": {"source": "doc1.pdf"}},
            {"id": "id2", "content": "相关内容2", "metadata": {"source": "doc2.pdf"}}
        ]
        
        # 执行带元数据过滤的混合检索
        results = await hybrid_retriever.retrieve("高血压治疗", top_k=2, use_metadata_filter=True)
        
        # 验证结果
        assert isinstance(results, list)
        
        # 验证调用了关键词提取
        mock_query_transformer.extract_keywords.assert_called_once_with("高血压治疗")
        # 验证调用了相似性搜索（可能带过滤器）
        mock_vector_store.similarity_search.assert_called()


class TestRankBM25Retriever:
    """BM25检索器测试类"""
    
    @pytest.fixture
    def bm25_retriever(self):
        """创建BM25检索器实例"""
        # 模拟文档集合
        documents = [
            {"id": "doc1", "content": "高血压是一种常见的慢性疾病", "metadata": {"source": "doc1.pdf"}},
            {"id": "doc2", "content": "糖尿病是一种代谢性疾病", "metadata": {"source": "doc2.pdf"}},
            {"id": "doc3", "content": "心脏病是心血管系统的疾病", "metadata": {"source": "doc3.pdf"}}
        ]
        
        # 创建BM25检索器
        retriever = RankBM25Retriever(documents)
        return retriever
    
    def test_get_top_n(self, bm25_retriever):
        """测试BM25检索功能"""
        # 执行检索
        results = bm25_retriever.get_top_n("高血压", n=3)
        
        # 验证结果
        assert len(results) > 0
        assert results[0]["id"] == "doc1"  # 包含"高血压"的文档应该排在前面
    
    def test_get_top_n_no_results(self, bm25_retriever):
        """测试无结果的BM25检索"""
        # 执行检索（空文档集合的情况在初始化时处理）
        results = bm25_retriever.get_top_n("不存在的关键词xyz", n=3)
        
        # 验证结果（BM25会返回最相关的文档，即使相关性很低）
        assert isinstance(results, list)
    
    def test_get_scores(self, bm25_retriever):
        """测试获取BM25分数功能"""
        # 执行分数计算
        scores = bm25_retriever.get_scores("高血压")
        
        # 验证结果
        assert isinstance(scores, dict)
        assert len(scores) == 3  # 应该有3个文档的分数
        assert "doc1" in scores  # 包含"高血压"的文档应该有分数
        assert scores["doc1"] > 0  # 相关文档的分数应该大于0


class TestQianwenReranker:
    """千问重排序器测试类"""
    
    @pytest.fixture
    def reranker(self):
        """创建重排序器实例"""
        return QianwenReranker()
    
    @pytest.mark.asyncio
    async def test_rerank_documents(self, reranker):
        """测试重排序功能"""
        # 准备测试数据
        query = "高血压的治疗方法"
        documents = [
            {"id": "doc1", "content": "高血压的预防措施", "metadata": {"source": "doc1.pdf"}, "score": 0.8},
            {"id": "doc2", "content": "高血压的治疗方法包括药物治疗和生活方式干预", "metadata": {"source": "doc2.pdf"}, "score": 0.7},
            {"id": "doc3", "content": "糖尿病的治疗方法", "metadata": {"source": "doc3.pdf"}, "score": 0.6}
        ]
        
        # 模拟千问客户端
        with patch('app.workflow.qianwen_client.get_qianwen_client') as mock_get_client:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value.rerank_documents.return_value = [
                (1, 0.9),  # doc2应该排在最前面
                (0, 0.5),  # doc1
                (2, 0.3)   # doc3
            ]
            mock_get_client.return_value = mock_client
            
            # 执行重排序
            results = await reranker.rerank_documents(query, documents)
            
            # 验证结果
            assert len(results) == 3
            assert results[0]["id"] == "doc2"  # 相关性最高的文档应该排在前面
            assert abs(results[0]["rerank_score"] - 0.9) < 0.1  # 允许一定的浮点数误差
            assert results[1]["id"] == "doc1"
            assert results[2]["id"] == "doc3"
            
            # 验证调用
            mock_client.__aenter__.return_value.rerank_documents.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_rerank_empty_documents(self, reranker):
        """测试空文档列表的情况"""
        # 执行重排序
        results = await reranker.rerank_documents("测试查询", [])
        
        # 验证结果
        assert results == []
    
    @pytest.mark.asyncio
    async def test_rerank_error_handling(self, reranker):
        """测试错误处理"""
        # 准备测试数据
        query = "高血压的治疗方法"
        documents = [
            {"id": "doc1", "content": "高血压的预防措施", "metadata": {"source": "doc1.pdf"}, "score": 0.8},
            {"id": "doc2", "content": "高血压的治疗方法包括药物治疗和生活方式干预", "metadata": {"source": "doc2.pdf"}, "score": 0.7}
        ]
        
        # 模拟千问客户端抛出异常
        with patch('app.workflow.qianwen_client.get_qianwen_client') as mock_get_client:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value.rerank_documents.side_effect = Exception("API错误")
            mock_get_client.return_value = mock_client
            
            # 执行重排序
            results = await reranker.rerank_documents(query, documents, top_k=1)
            
            # 验证结果 - 应该返回原始排序的前top_k个文档
            assert len(results) == 1
            assert results[0]["id"] == "doc1"


class TestQueryTransformer:
    """查询转换器测试类"""
    
    @pytest.fixture
    def query_transformer(self):
        """创建查询转换器实例"""
        return QueryTransformer()
    
    def test_expand_query(self, query_transformer):
        """测试查询扩展功能"""
        # 模拟LLM客户端
        query_transformer.llm_client = Mock()
        query_transformer.llm_client.generate_response.return_value = """
        1. 高血压的症状有哪些
        2. 高血压的危害
        3. 如何诊断高血压
        """
        
        # 执行查询扩展
        expanded_queries = query_transformer.expand_query("高血压")
        
        # 验证结果
        assert len(expanded_queries) == 4  # 原始查询 + 3个扩展查询
        assert expanded_queries[0] == "高血压"  # 第一个应该是原始查询
        assert "症状" in expanded_queries[1]
        assert "危害" in expanded_queries[2]
        assert "诊断" in expanded_queries[3]
    
    def test_rewrite_query(self, query_transformer):
        """测试查询重写功能"""
        # 模拟LLM客户端
        query_transformer.llm_client = Mock()
        query_transformer.llm_client.generate_response.return_value = "高血压的临床表现和治疗方案"
        
        # 执行查询重写
        rewritten_query = query_transformer.rewrite_query("我想了解高血压")
        
        # 验证结果
        assert rewritten_query == "高血压的临床表现和治疗方案"
    
    def test_extract_medical_entities(self, query_transformer):
        """测试医学实体提取功能"""
        # 模拟LLM客户端
        query_transformer.llm_client = Mock()
        query_transformer.llm_client.generate_response.return_value = """
        {
            "diseases": ["高血压", "冠心病"],
            "symptoms": ["头痛", "头晕"],
            "medications": ["降压药"]
        }
        """
        
        # 执行医学实体提取
        entities = query_transformer.extract_medical_entities("高血压患者经常头痛头晕，需要服用降压药，还可能并发冠心病")
        
        # 验证结果
        assert "diseases" in entities
        assert "symptoms" in entities
        assert "medications" in entities
        assert "高血压" in entities["diseases"]
        assert "头痛" in entities["symptoms"]
        assert "降压药" in entities["medications"]