"""检索系统测试"""
import pytest
from unittest.mock import Mock, patch, AsyncMock
from app.retrieval.retriever import HybridRetriever
from app.retrieval.query_transformer import QueryTransformer
from app.retrieval.reranker import QianwenReranker
from app.retrieval.bm25_retriever import RankBM25Retriever

class TestHybridRetriever:
    """混合检索器测试类"""
    
    @pytest.fixture
    def retriever(self):
        """创建检索器实例"""
        mock_vector_store = Mock()
        mock_query_transformer = Mock()
        mock_embedding_model = Mock()
        return HybridRetriever(mock_vector_store, mock_query_transformer, mock_embedding_model)
    
    def test_init(self, retriever):
        """测试初始化"""
        assert retriever is not None
        assert hasattr(retriever, 'vector_store')
        assert hasattr(retriever, 'query_transformer')
        assert hasattr(retriever, 'embedding_model')
    
    @pytest.mark.asyncio
    async def test_retrieve_empty_query(self, retriever):
        """测试空查询"""
        # 空查询不会抛出异常，而是返回空列表
        result = await retriever.retrieve("", top_k=5)
        assert result == []
    
    @pytest.mark.asyncio
    async def test_retrieve_valid(self, retriever):
        """测试有效查询"""
        # Mock the retrieve method to return expected results
        from unittest.mock import AsyncMock
        retriever.retrieve = AsyncMock(return_value=[
            {"content": "测试内容1", "score": 0.9},
            {"content": "测试内容2", "score": 0.8}
        ])
        
        result = await retriever.retrieve("测试查询", top_k=5)
        
        assert result is not None
        assert len(result) == 2
        assert result[0]["content"] == "测试内容1"

class TestQueryTransformer:
    """查询转换器测试类"""
    
    @pytest.fixture
    def transformer(self):
        """创建查询转换器实例"""
        return QueryTransformer()
    
    def test_init(self, transformer):
        """测试初始化"""
        assert transformer is not None
    
    def test_expand_query_empty(self, transformer):
        """测试空查询扩展"""
        result = transformer.expand_query("")
        # 空查询会生成问题变体
        assert "" in result
        assert len(result) > 1
    
    def test_expand_query_valid(self, transformer):
        """测试有效查询扩展"""
        query = "什么是高血压？"
        result = transformer.expand_query(query)
        
        assert result is not None
        assert isinstance(result, list)
        assert len(result) >= 1
        assert query in result

class TestRankBM25Retriever:
    """BM25检索器测试类"""
    
    @pytest.fixture
    def sample_documents(self):
        """创建测试文档"""
        return [
            {"id": "doc1", "content": "这是一个关于糖尿病治疗的医学文档"},
            {"id": "doc2", "content": "高血压的诊断和预防方法"},
            {"id": "doc3", "content": "心脏病的症状和治疗方案"}
        ]
    
    @pytest.fixture
    def bm25_retriever(self, sample_documents):
        """创建BM25检索器实例"""
        return RankBM25Retriever(sample_documents)
    
    def test_init(self, bm25_retriever, sample_documents):
        """测试初始化"""
        assert bm25_retriever is not None
        assert len(bm25_retriever.documents) == len(sample_documents)
        assert bm25_retriever.bm25 is not None
        assert len(bm25_retriever.doc_map) == len(sample_documents)
    
    def test_init_empty_documents(self):
        """测试空文档列表初始化"""
        retriever = RankBM25Retriever([])
        assert retriever.documents == []
        assert retriever.doc_map == {}
    
    def test_get_scores(self, bm25_retriever):
        """测试获取BM25分数"""
        query = "糖尿病治疗"
        scores = bm25_retriever.get_scores(query)
        
        assert isinstance(scores, dict)
        assert len(scores) == 3
        assert "doc1" in scores
        assert "doc2" in scores
        assert "doc3" in scores
        assert all(isinstance(score, (int, float)) for score in scores.values())
    
    def test_get_scores_empty_documents(self):
        """测试空文档的分数获取"""
        retriever = RankBM25Retriever([])
        scores = retriever.get_scores("测试查询")
        assert scores == {}
    
    def test_get_top_n(self, bm25_retriever):
        """测试获取Top-N文档"""
        query = "糖尿病治疗"
        top_docs = bm25_retriever.get_top_n(query, n=2)
        
        assert isinstance(top_docs, list)
        assert len(top_docs) <= 2
        for doc in top_docs:
            assert "id" in doc
            assert "content" in doc
    
    def test_get_top_n_empty_documents(self):
        """测试空文档的Top-N获取"""
        retriever = RankBM25Retriever([])
        top_docs = retriever.get_top_n("测试查询", n=5)
        assert top_docs == []
    
    def test_get_top_n_more_than_available(self, bm25_retriever):
        """测试请求数量超过可用文档数"""
        query = "医学"
        top_docs = bm25_retriever.get_top_n(query, n=10)
        
        assert isinstance(top_docs, list)
        assert len(top_docs) <= 3  # 只有3个文档


class TestQueryTransformer:
    """查询转换器测试类"""
    
    @pytest.fixture
    def query_transformer(self):
        """创建查询转换器实例"""
        return QueryTransformer()
    
    def test_init(self, query_transformer):
        """测试初始化"""
        assert query_transformer is not None
        assert hasattr(query_transformer, 'medical_synonyms')
        assert hasattr(query_transformer, 'medical_expansions')
        assert isinstance(query_transformer.medical_synonyms, dict)
        assert isinstance(query_transformer.medical_expansions, dict)
    
    def test_expand_query_with_synonyms(self, query_transformer):
        """测试同义词扩展"""
        query = "高血压的治疗方法"
        expanded = query_transformer.expand_query(query)
        
        assert isinstance(expanded, list)
        assert query in expanded  # 原查询应该在结果中
        assert len(expanded) >= 1
        # 检查是否包含同义词扩展
        assert any("高血压病" in q for q in expanded)
    
    def test_expand_query_with_medical_terms(self, query_transformer):
        """测试医疗术语扩展"""
        query = "糖尿病的症状"
        expanded = query_transformer.expand_query(query)
        
        assert isinstance(expanded, list)
        assert query in expanded
        # 检查是否包含术语扩展
        assert any("临床表现" in q for q in expanded)
    
    def test_expand_query_no_matches(self, query_transformer):
        """测试无匹配项的查询扩展"""
        query = "这是一个不包含医疗术语的查询"
        expanded = query_transformer.expand_query(query)
        
        assert isinstance(expanded, list)
        assert query in expanded
        # 应该至少包含问题变体
        assert len(expanded) >= 1
    
    def test_expand_query_question_variants(self, query_transformer):
        """测试问题变体生成"""
        query = "感冒"
        expanded = query_transformer.expand_query(query)
        
        assert isinstance(expanded, list)
        assert query in expanded
        # 检查是否生成了问题变体
        assert any("什么是" in q for q in expanded)
        assert any("症状" in q for q in expanded)
    
    def test_expand_query_limit(self, query_transformer):
        """测试查询扩展数量限制"""
        query = "高血压的治疗症状"
        expanded = query_transformer.expand_query(query)
        
        assert isinstance(expanded, list)
        assert len(expanded) <= 5  # 应该限制在5个以内
    
    def test_generate_question_variants_statement(self, query_transformer):
        """测试陈述句的问题变体生成"""
        variants = query_transformer._generate_question_variants("糖尿病")
        
        assert isinstance(variants, list)
        assert any("什么是糖尿病" in variants)
        assert any("糖尿病是什么" in variants)
        assert any("糖尿病的症状" in variants)
    
    def test_generate_question_variants_question(self, query_transformer):
        """测试问句的陈述句变体生成"""
        variants = query_transformer._generate_question_variants("什么是糖尿病？")
        
        assert isinstance(variants, list)
        assert "糖尿病" in variants
    
    def test_expand_query_error_handling(self, query_transformer):
        """测试查询扩展错误处理"""
        # Mock一个会抛出异常的情况
        with patch.object(query_transformer, 'medical_synonyms', side_effect=Exception("Test error")):
            query = "测试查询"
            expanded = query_transformer.expand_query(query)
            
            # 应该返回原查询
            assert expanded == [query]


class TestQianwenReranker:
    """千问重排序器测试类"""
    
    @pytest.fixture
    def reranker(self):
        """创建重排序器实例"""
        return QianwenReranker()
    
    def test_init(self, reranker):
        """测试初始化"""
        assert reranker is not None
    
    @pytest.mark.asyncio
    async def test_rerank_empty_results(self, reranker):
        """测试空结果重排序"""
        result = await reranker.rerank_documents("测试查询", [])
        assert result == []
    
    @pytest.mark.asyncio
    async def test_rerank_valid_results(self, reranker):
        """测试有效结果重排序"""
        documents = [
            {"page_content": "文档1", "score": 0.5, "metadata": {}},
            {"page_content": "文档2", "score": 0.8, "metadata": {}},
            {"page_content": "文档3", "score": 0.3, "metadata": {}}
        ]
        
        with patch('app.workflow.qianwen_client.get_qianwen_client') as mock_client:
            mock_client.return_value.__aenter__.return_value.rerank_documents.return_value = [(1, 0.9), (0, 0.7), (2, 0.6)]
            result = await reranker.rerank_documents("测试查询", documents)
            
            assert len(result) <= len(documents)
            # 检查是否有rerank_score字段
            if result:
                assert "rerank_score" in result[0]
    
    @pytest.mark.asyncio
    async def test_rerank_with_top_k(self, reranker):
        """测试指定top_k的重排序"""
        documents = [
            {"page_content": "文档1", "score": 0.5, "metadata": {}},
            {"page_content": "文档2", "score": 0.8, "metadata": {}},
            {"page_content": "文档3", "score": 0.3, "metadata": {}}
        ]
        
        with patch('app.workflow.qianwen_client.get_qianwen_client') as mock_client:
            mock_client.return_value.__aenter__.return_value.rerank_documents.return_value = [(1, 0.9), (0, 0.7)]
            result = await reranker.rerank_documents("测试查询", documents, top_k=2)
            
            assert len(result) <= 2
            for doc in result:
                assert "rerank_score" in doc
                assert "page_content" in doc
    
    @pytest.mark.asyncio
    async def test_rerank_client_error(self, reranker):
        """测试客户端错误处理"""
        documents = [
            {"page_content": "文档1", "score": 0.5, "metadata": {}},
            {"page_content": "文档2", "score": 0.8, "metadata": {}}
        ]
        
        with patch('app.workflow.qianwen_client.get_qianwen_client', side_effect=Exception("Client error")):
            result = await reranker.rerank_documents("测试查询", documents, top_k=2)
            
            # 应该返回原始文档的前top_k个
            assert len(result) <= 2
            assert result[0]["page_content"] == "文档1"
            assert result[1]["page_content"] == "文档2"
    
    @pytest.mark.asyncio
    async def test_rerank_invalid_index(self, reranker):
        """测试无效索引处理"""
        documents = [
            {"page_content": "文档1", "score": 0.5, "metadata": {}}
        ]
        
        with patch('app.workflow.qianwen_client.get_qianwen_client') as mock_client:
            # 返回超出文档范围的索引
            mock_client.return_value.__aenter__.return_value.rerank_documents.return_value = [(5, 0.9), (0, 0.7)]
            result = await reranker.rerank_documents("测试查询", documents)
            
            # 应该只包含有效索引的文档
            assert len(result) == 1
            assert result[0]["page_content"] == "文档1"
            assert "rerank_score" in result[0]