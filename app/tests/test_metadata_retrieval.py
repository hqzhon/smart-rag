"""元数据检索功能测试"""
import pytest
from unittest.mock import Mock, AsyncMock, patch
from app.retrieval.retriever import HybridRetriever
from app.retrieval.query_transformer import QueryTransformer
from app.storage.vector_store import VectorStore


class TestMetadataRetrieval:
    """元数据检索功能测试类"""
    
    @pytest.fixture
    def mock_vector_store(self):
        """创建模拟向量存储"""
        mock_store = Mock(spec=VectorStore)
        mock_retriever = Mock()
        mock_retriever.get_relevant_documents = AsyncMock(return_value=[
            {
                'page_content': '糖尿病是一种慢性疾病',
                'metadata': {
                    'medical_entities': ['糖尿病'],
                    'keywords': ['慢性疾病', '血糖'],
                    'document_id': 'doc1'
                }
            },
            {
                'page_content': '高血压的治疗方法',
                'metadata': {
                    'medical_entities': ['高血压'],
                    'keywords': ['治疗', '药物'],
                    'document_id': 'doc2'
                }
            }
        ])
        mock_store.get_retriever.return_value = mock_retriever
        return mock_store
    
    @pytest.fixture
    def mock_query_transformer(self):
        """创建模拟查询转换器"""
        mock_transformer = Mock(spec=QueryTransformer)
        mock_transformer.extract_medical_entities.return_value = {
            'diseases': ['糖尿病'],
            'symptoms': ['血糖高'],
            'treatments': []
        }
        return mock_transformer
    
    @pytest.fixture
    def sample_documents(self):
        """创建示例文档"""
        return [
            {
                'content': '糖尿病是一种慢性疾病，需要长期管理',
                'metadata': {
                    'medical_entities': ['糖尿病'],
                    'keywords': ['慢性疾病', '血糖'],
                    'document_id': 'doc1'
                }
            },
            {
                'content': '高血压的治疗需要综合管理',
                'metadata': {
                    'medical_entities': ['高血压'],
                    'keywords': ['治疗', '药物'],
                    'document_id': 'doc2'
                }
            }
        ]
    
    @pytest.fixture
    def hybrid_retriever(self, mock_vector_store, mock_query_transformer):
        """创建混合检索器实例"""
        mock_embedding_model = Mock()
        return HybridRetriever(
            vector_store=mock_vector_store,
            query_transformer=mock_query_transformer,
            embedding_model=mock_embedding_model
        )
    
    @pytest.mark.asyncio
    async def test_extract_keywords_from_query(self, hybrid_retriever, mock_query_transformer):
        """测试从查询中提取关键词"""
        query = "糖尿病的症状有哪些"
        
        keywords = await hybrid_retriever._extract_keywords_from_query(query)
        
        # 验证调用了查询转换器
        mock_query_transformer.extract_medical_entities.assert_called_once_with(query)
        
        # 验证返回的关键词
        assert isinstance(keywords, list)
        assert '糖尿病' in keywords
        assert '血糖高' in keywords
    
    def test_build_where_clause_single_keyword(self, hybrid_retriever):
        """测试构建单个关键词的where子句"""
        keywords = ['糖尿病']
        
        where_clause = hybrid_retriever._build_where_clause(keywords)
        
        expected = {
            "$or": [
                {"medical_entities": {"$contains": "糖尿病"}},
                {"keywords": {"$contains": "糖尿病"}},
                {"content": {"$contains": "糖尿病"}}
            ]
        }
        
        assert where_clause == expected
    
    def test_build_where_clause_multiple_keywords(self, hybrid_retriever):
        """测试构建多个关键词的where子句"""
        keywords = ['糖尿病', '血糖']
        
        where_clause = hybrid_retriever._build_where_clause(keywords)
        
        # 验证包含所有关键词的$or条件
        assert "$or" in where_clause
        or_conditions = where_clause["$or"]
        
        # 每个关键词应该有3个匹配条件（medical_entities, keywords, content）
        assert len(or_conditions) == 6  # 2个关键词 * 3个字段
        
        # 验证包含糖尿病的条件
        diabetes_conditions = [cond for cond in or_conditions if '糖尿病' in str(cond)]
        assert len(diabetes_conditions) == 3
        
        # 验证包含血糖的条件
        blood_sugar_conditions = [cond for cond in or_conditions if '血糖' in str(cond)]
        assert len(blood_sugar_conditions) == 3
    
    def test_build_where_clause_empty_keywords(self, hybrid_retriever):
        """测试空关键词列表的where子句构建"""
        keywords = []
        
        where_clause = hybrid_retriever._build_where_clause(keywords)
        
        assert where_clause is None
    
    @pytest.mark.asyncio
    async def test_adaptive_retrieve_with_metadata_filter(self, hybrid_retriever, mock_vector_store):
        """测试带元数据过滤的自适应检索"""
        query = "糖尿病的治疗方法"
        
        # Mock the retrieve method to return expected results
        from unittest.mock import AsyncMock
        hybrid_retriever.retrieve = AsyncMock(return_value=[
            {"content": "糖尿病治疗内容1", "score": 0.9},
            {"content": "糖尿病治疗内容2", "score": 0.8}
        ])
        
        # 执行检索
        results = await hybrid_retriever.adaptive_retrieve(
            query=query,
            top_k=5,
            use_metadata_filter=True
        )
        
        # 验证调用了retrieve方法
        hybrid_retriever.retrieve.assert_called_once_with(query, 5, True)
        
        # 验证返回结果
        assert isinstance(results, list)
        assert len(results) == 2
    
    @pytest.mark.asyncio
    async def test_adaptive_retrieve_without_metadata_filter(self, hybrid_retriever, mock_vector_store):
        """测试不使用元数据过滤的自适应检索"""
        query = "糖尿病的治疗方法"
        
        # Mock the retrieve method to return expected results
        from unittest.mock import AsyncMock
        hybrid_retriever.retrieve = AsyncMock(return_value=[
            {"content": "糖尿病治疗内容1", "score": 0.9}
        ])
        
        # 执行检索
        results = await hybrid_retriever.adaptive_retrieve(
            query=query,
            top_k=5,
            use_metadata_filter=False
        )
        
        # 验证调用了retrieve方法
        hybrid_retriever.retrieve.assert_called_once_with(query, 5, False)
        
        # 验证返回结果
        assert isinstance(results, list)
        assert len(results) == 1
    
    @pytest.mark.asyncio
    async def test_adaptive_retrieve_no_keywords_extracted(self, hybrid_retriever, mock_query_transformer):
        """测试没有提取到关键词时的检索行为"""
        # 模拟没有提取到关键词的情况
        mock_query_transformer.extract_medical_entities.return_value = {
            'diseases': [],
            'symptoms': [],
            'treatments': []
        }
        
        query = "一般性问题"
        
        # 执行检索
        results = await hybrid_retriever.adaptive_retrieve(
            query=query,
            top_k=5,
            use_metadata_filter=True
        )
        
        # 验证即使开启了元数据过滤，但由于没有关键词，应该正常执行检索
        assert isinstance(results, list)
    
    @pytest.mark.asyncio
    async def test_metadata_filter_integration_with_vector_store(self, mock_vector_store, sample_documents, mock_query_transformer):
        """测试元数据过滤与向量存储的集成"""
        # 创建mock embedding model
        from unittest.mock import Mock, AsyncMock
        mock_embedding_model = Mock()
        
        # 创建检索器
        retriever = HybridRetriever(
            vector_store=mock_vector_store,
            query_transformer=mock_query_transformer,
            embedding_model=mock_embedding_model
        )
        
        # Mock the retrieve method to return expected results
        retriever.retrieve = AsyncMock(return_value=[
            {"content": "糖尿病治疗内容", "score": 0.9}
        ])
        
        query = "糖尿病相关信息"
        
        # 执行带过滤的检索
        results = await retriever.adaptive_retrieve(query, use_metadata_filter=True)
        
        # 验证调用了retrieve方法
        retriever.retrieve.assert_called_once_with(query, 5, True)
        
        # 验证返回结果
        assert isinstance(results, list)
        assert len(results) == 1
        assert results[0]["content"] == "糖尿病治疗内容"