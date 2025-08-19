"""
检索系统测试
"""
import pytest
from unittest.mock import Mock, patch, AsyncMock
from app.retrieval.retriever import HybridRetriever
from app.retrieval.query_transformer import QueryTransformer
from app.retrieval.reranker import Reranker

class TestHybridRetriever:
    """混合检索器测试类"""
    
    @pytest.fixture
    def retriever(self):
        """创建检索器实例"""
        return HybridRetriever()
    
    def test_init(self, retriever):
        """测试初始化"""
        assert retriever is not None
        assert hasattr(retriever, 'vector_store')
        assert hasattr(retriever, 'bm25_retriever')
    
    @pytest.mark.asyncio
    async def test_search_empty_query(self, retriever):
        """测试空查询"""
        with pytest.raises(ValueError, match="查询不能为空"):
            await retriever.search("", top_k=5)
    
    @pytest.mark.asyncio
    @patch('app.retrieval.retriever.HybridRetriever._vector_search')
    @patch('app.retrieval.retriever.HybridRetriever._bm25_search')
    async def test_search_valid(self, mock_bm25, mock_vector, retriever):
        """测试有效查询"""
        # 模拟搜索结果
        mock_vector.return_value = [
            {"content": "向量搜索结果", "score": 0.9, "metadata": {}}
        ]
        mock_bm25.return_value = [
            {"content": "BM25搜索结果", "score": 0.8, "metadata": {}}
        ]
        
        result = await retriever.search("测试查询", top_k=5)
        
        assert result is not None
        assert isinstance(result, list)
        mock_vector.assert_called_once()
        mock_bm25.assert_called_once()

class TestQueryTransformer:
    """查询转换器测试类"""
    
    @pytest.fixture
    def transformer(self):
        """创建查询转换器实例"""
        return QueryTransformer()
    
    def test_init(self, transformer):
        """测试初始化"""
        assert transformer is not None
    
    @pytest.mark.asyncio
    async def test_transform_empty_query(self, transformer):
        """测试空查询转换"""
        with pytest.raises(ValueError, match="查询不能为空"):
            await transformer.transform("")
    
    @pytest.mark.asyncio
    async def test_transform_valid_query(self, transformer):
        """测试有效查询转换"""
        query = "什么是高血压？"
        result = await transformer.transform(query)
        
        assert result is not None
        assert isinstance(result, dict)
        assert "original_query" in result
        assert "expanded_queries" in result

class TestReranker:
    """重排序器测试类"""
    
    @pytest.fixture
    def reranker(self):
        """创建重排序器实例"""
        return Reranker()
    
    def test_init(self, reranker):
        """测试初始化"""
        assert reranker is not None
    
    def test_rerank_empty_results(self, reranker):
        """测试空结果重排序"""
        result = reranker.rerank([], "测试查询")
        assert result == []
    
    def test_rerank_valid_results(self, reranker):
        """测试有效结果重排序"""
        documents = [
            {"content": "文档1", "score": 0.5, "metadata": {}},
            {"content": "文档2", "score": 0.8, "metadata": {}},
            {"content": "文档3", "score": 0.3, "metadata": {}}
        ]
        
        result = reranker.rerank(documents, "测试查询")
        
        assert len(result) == len(documents)
        # 检查是否按分数排序
        scores = [doc["score"] for doc in result]
        assert scores == sorted(scores, reverse=True)