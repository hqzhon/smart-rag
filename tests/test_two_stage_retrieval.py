import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
import numpy as np
from typing import List, Dict, Any

# 添加项目根目录到路径
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.retrieval.retriever import HybridRetriever
from app.retrieval.bm25_retriever import RankBM25Retriever
from app.embeddings.embeddings import QianwenEmbeddings
from app.retrieval.query_transformer import QueryTransformer
from app.storage.vector_store import VectorStore


class TestTwoStageRetrieval:
    """两阶段检索测试类"""
    
    @pytest.fixture
    def mock_vector_store(self):
        """模拟向量存储"""
        mock_store = Mock(spec=VectorStore)
        mock_store.similarity_search = AsyncMock(return_value=[
            {
                'content': '这是第一个测试文档，包含医学相关内容。',
                'metadata': {'source': 'test1.pdf', 'page': 1, 'id': 'doc1'},
                'score': 0.95
            },
            {
                'content': '这是第二个测试文档，讨论治疗方案。',
                'metadata': {'source': 'test2.pdf', 'page': 2, 'id': 'doc2'},
                'score': 0.90
            },
            {
                'content': '第三个文档涉及诊断标准和检查方法。',
                'metadata': {'source': 'test3.pdf', 'page': 1, 'id': 'doc3'},
                'score': 0.85
            }
        ])
        return mock_store
    
    @pytest.fixture
    def mock_embedding_model(self):
        """模拟嵌入模型"""
        mock_model = Mock(spec=QianwenEmbeddings)
        mock_model.embed_query = AsyncMock(return_value=np.random.rand(1536).tolist())
        mock_model.embed_documents = AsyncMock(return_value=[
            np.random.rand(1536).tolist() for _ in range(3)
        ])
        return mock_model
    
    @pytest.fixture
    def mock_query_transformer(self):
        """模拟查询转换器"""
        mock_transformer = Mock(spec=QueryTransformer)
        mock_transformer.extract_keywords = Mock(return_value=['医学', '治疗'])
        mock_transformer.build_where_clause = Mock(return_value={})
        return mock_transformer
    
    @pytest.fixture
    def hybrid_retriever(self, mock_vector_store, mock_embedding_model, mock_query_transformer):
        """创建混合检索器实例"""
        return HybridRetriever(
            vector_store=mock_vector_store,
            query_transformer=mock_query_transformer,
            embedding_model=mock_embedding_model
        )
    
    @pytest.mark.asyncio
    async def test_get_candidate_chunks(self, hybrid_retriever, mock_vector_store):
        """测试第一阶段候选块获取"""
        query = "医学治疗方案"
        
        # 调用候选块获取方法
        candidates = await hybrid_retriever._get_candidate_chunks(query, candidate_k=10, use_filter=False)
        
        # 验证结果
        assert len(candidates) == 3
        assert all('id' in doc for doc in candidates)
        assert all('content' in doc for doc in candidates)
        assert all('metadata' in doc for doc in candidates)
        
        # 验证向量存储被正确调用
        mock_vector_store.similarity_search.assert_called_once_with(query, 10)
    
    @pytest.mark.asyncio
    async def test_get_candidate_chunks_with_filter(self, hybrid_retriever, mock_vector_store):
        """测试带过滤条件的候选块获取"""
        query = "医学治疗方案"
        
        # 模拟_extract_keywords_from_query方法
        with patch.object(hybrid_retriever, '_extract_keywords_from_query', return_value=['医学', '治疗']):
            # 调用候选块获取方法
            candidates = await hybrid_retriever._get_candidate_chunks(
                query, 
                candidate_k=10, 
                use_filter=True
            )
            
            # 验证结果
            assert len(candidates) == 3
            
            # 验证过滤条件被传递
            expected_filter = {"$or": [{"keywords": {"$in": ["医学"]}}, {"keywords": {"$in": ["治疗"]}}]}
            mock_vector_store.similarity_search.assert_called_once_with(query, 10, expected_filter)
    
    def test_calculate_cosine_similarity(self, hybrid_retriever):
        """测试余弦相似度计算"""
        query_vec = [1, 0, 0]
        doc_vecs = [[0, 1, 0], [1, 1, 0], [1, 0, 0]]
        
        # 计算相似度
        similarities = hybrid_retriever._calculate_cosine_similarity(query_vec, doc_vecs)
        
        # 验证结果
        assert len(similarities) == 3
        assert abs(similarities[0] - 0.0) < 1e-6  # 垂直向量
        assert abs(similarities[2] - 1.0) < 1e-6  # 相同向量
        assert 0 <= similarities[1] <= 1  # 45度角向量
    
    def test_fuse_results(self, hybrid_retriever):
        """测试结果融合逻辑"""
        bm25_scores = {'doc1': 0.8, 'doc2': 0.6, 'doc3': 0.4}
        vector_scores = {'doc1': 0.9, 'doc2': 0.5, 'doc3': 0.7}
        
        # 测试默认权重融合
        fused_results = hybrid_retriever._fuse_results(bm25_scores, vector_scores, top_k=3)
        
        # Extract doc_ids from the dictionary-based results
        fused_ids = [result['doc_id'] for result in fused_results]
        
        assert len(fused_ids) == 3
        assert all(doc_id in ['doc1', 'doc2', 'doc3'] for doc_id in fused_ids)
        
        # 验证排序正确性 - doc1应该排在前面（两个分数都很高）
        assert fused_ids[0] == 'doc1'
    
    @pytest.mark.asyncio
    async def test_two_stage_retrieve_full_pipeline(self, hybrid_retriever, mock_vector_store, mock_embedding_model):
        """测试完整的两阶段检索流程"""
        query = "医学治疗方案"
        
        # 模拟BM25检索器
        with patch('app.retrieval.retriever.RankBM25Retriever') as mock_bm25_class:
            mock_bm25 = Mock()
            mock_bm25.get_scores.return_value = [0.8, 0.6, 0.4]
            mock_bm25_class.return_value = mock_bm25
            
            # 执行检索
            results = await hybrid_retriever.retrieve(query, top_k=3)
            
            # 验证结果结构
            assert isinstance(results, list)
            assert len(results) <= 3
            
            for result in results:
                assert 'page_content' in result
                assert 'metadata' in result
                assert 'score' in result
                assert 0 <= result['score'] <= 1
    
    @pytest.mark.asyncio
    async def test_retrieve_with_no_candidates(self, hybrid_retriever, mock_vector_store):
        """测试无候选文档的情况"""
        # 模拟无候选文档
        mock_vector_store.similarity_search.return_value = []
        
        query = "不存在的查询"
        results = await hybrid_retriever.retrieve(query, top_k=5)
        
        # 应该返回空列表
        assert results == []
    
    @pytest.mark.asyncio
    async def test_retrieve_with_metadata_filtering(self, hybrid_retriever):
        """测试带元数据过滤的检索"""
        query = "医学治疗"
        
        # 模拟_extract_keywords_from_query方法
        with patch.object(hybrid_retriever, '_extract_keywords_from_query', return_value=['医学', '治疗']):
            with patch('app.retrieval.retriever.RankBM25Retriever'):
                results = await hybrid_retriever.retrieve(
                    query, 
                    top_k=5, 
                    use_metadata_filter=True
                )
                
                # 验证结果是列表
                assert isinstance(results, list)
    
    @pytest.mark.asyncio
    async def test_retrieve_error_handling(self, hybrid_retriever, mock_vector_store):
        """测试错误处理"""
        # 模拟向量存储抛出异常
        mock_vector_store.similarity_search.side_effect = Exception("Vector store error")
        
        query = "测试查询"
        
        # 应该捕获异常并返回空列表
        results = await hybrid_retriever.retrieve(query, top_k=5)
        assert results == []
    
    def test_bm25_retriever_integration(self):
        """测试BM25检索器集成"""
        documents = [
            {'id': 'doc1', 'content': '这是第一个测试文档'},
            {'id': 'doc2', 'content': '这是第二个测试文档'}, 
            {'id': 'doc3', 'content': '第三个文档内容不同'}
        ]
        
        # 创建BM25检索器
        bm25_retriever = RankBM25Retriever(documents)
        
        # 测试获取分数
        query = "测试文档"
        scores = bm25_retriever.get_scores(query)
        
        assert len(scores) == 3
        assert all(isinstance(score, (int, float)) for score in scores.values())
        assert all(doc_id in ['doc1', 'doc2', 'doc3'] for doc_id in scores.keys())
        
        # 测试获取top文档
        top_docs = bm25_retriever.get_top_n(query, n=2)
        assert len(top_docs) <= 2
        assert all('id' in doc and 'content' in doc for doc in top_docs)


if __name__ == "__main__":
    # 运行测试
    pytest.main([__file__, "-v"])