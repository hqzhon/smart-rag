#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RRF集成测试
验证RRF与现有系统的兼容性
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import numpy as np
from typing import List, Dict, Any

# Import the HybridRetriever class
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.retrieval.retriever import HybridRetriever


class TestRRFIntegration(unittest.TestCase):
    """RRF集成测试类"""
    
    def setUp(self):
        """测试初始化"""
        # Mock dependencies
        self.mock_vector_store = Mock()
        self.mock_query_transformer = Mock()
        self.mock_embedding_model = Mock()
        
        # Mock vector store methods
        self.mock_vector_store.similarity_search_with_score.return_value = [
            (Mock(page_content="Test content 1", metadata={"doc_id": "doc_1"}), 0.9),
            (Mock(page_content="Test content 2", metadata={"doc_id": "doc_2"}), 0.8),
            (Mock(page_content="Test content 3", metadata={"doc_id": "doc_3"}), 0.7)
        ]
        
        # Mock query transformer
        self.mock_query_transformer.extract_keywords.return_value = ["test", "query"]
        
        # Mock embedding model
        self.mock_embedding_model.embed_query.return_value = [0.1, 0.2, 0.3]
        
        # Create retriever instances
        self.rrf_retriever = HybridRetriever(
            vector_store=self.mock_vector_store,
            query_transformer=self.mock_query_transformer,
            embedding_model=self.mock_embedding_model,
            fusion_method="rrf",
            rrf_k=60
        )
        
        self.weighted_retriever = HybridRetriever(
            vector_store=self.mock_vector_store,
            query_transformer=self.mock_query_transformer,
            embedding_model=self.mock_embedding_model,
            fusion_method="weighted"
        )
    
    def test_rrf_retriever_initialization(self):
        """测试RRF检索器初始化"""
        # Test RRF initialization
        self.assertEqual(self.rrf_retriever.fusion_method, "rrf")
        self.assertEqual(self.rrf_retriever.rrf_k, 60)
        
        # Test weighted initialization
        self.assertEqual(self.weighted_retriever.fusion_method, "weighted")
        self.assertEqual(self.weighted_retriever.rrf_k, 60)  # Default value
    
    def test_fusion_method_switching(self):
        """测试融合方法切换"""
        # Initially RRF
        self.assertEqual(self.rrf_retriever.fusion_method, "rrf")
        
        # Switch to weighted
        self.rrf_retriever.set_fusion_method("weighted")
        self.assertEqual(self.rrf_retriever.fusion_method, "weighted")
        
        # Switch back to RRF
        self.rrf_retriever.set_fusion_method("rrf")
        self.assertEqual(self.rrf_retriever.fusion_method, "rrf")
        
        # Test invalid method
        with self.assertRaises(ValueError):
            self.rrf_retriever.set_fusion_method("invalid")
    
    def test_rrf_k_parameter_configuration(self):
        """测试RRF参数k的配置"""
        # Test initial value
        self.assertEqual(self.rrf_retriever.rrf_k, 60)
        
        # Test setting new value
        self.rrf_retriever.set_rrf_k(100)
        self.assertEqual(self.rrf_retriever.rrf_k, 100)
        
        # Test invalid values
        with self.assertRaises(ValueError):
            self.rrf_retriever.set_rrf_k(0)
        
        with self.assertRaises(ValueError):
            self.rrf_retriever.set_rrf_k(-10)
    
    def test_fusion_config_retrieval(self):
        """测试融合配置获取"""
        config = self.rrf_retriever.get_fusion_config()
        
        self.assertIn("fusion_method", config)
        self.assertIn("rrf_k", config)
        self.assertEqual(config["fusion_method"], "rrf")
        self.assertEqual(config["rrf_k"], 60)
        
        # Test after configuration change
        self.rrf_retriever.set_fusion_method("weighted")
        self.rrf_retriever.set_rrf_k(80)
        
        updated_config = self.rrf_retriever.get_fusion_config()
        self.assertEqual(updated_config["fusion_method"], "weighted")
        self.assertEqual(updated_config["rrf_k"], 80)
    
    @patch('app.retrieval.retriever.HybridRetriever._build_chromadb_where_clause')
    @patch('app.retrieval.retriever.HybridRetriever._get_candidate_chunks')
    def test_rrf_end_to_end_retrieval(self, mock_get_candidates, mock_build_where):
        """测试RRF端到端检索流程"""
        # Mock candidate chunks
        mock_candidates = [
            {"doc_id": "doc_1", "content": "Test content 1", "metadata": {}},
            {"doc_id": "doc_2", "content": "Test content 2", "metadata": {}},
            {"doc_id": "doc_3", "content": "Test content 3", "metadata": {}}
        ]
        mock_get_candidates.return_value = mock_candidates
        mock_build_where.return_value = {}
        
        # Mock BM25 scoring
        with patch('app.retrieval.bm25_retriever.RankBM25Retriever.get_scores') as mock_bm25:
            mock_bm25.return_value = {
                "doc_1": 0.8,
                "doc_2": 0.6,
                "doc_3": 0.4
            }
            
            # Mock vector scoring
            with patch.object(self.rrf_retriever, '_calculate_cosine_similarity') as mock_vector:
                mock_vector.return_value = [0.7, 0.9, 0.5]  # 返回列表而不是字典
                
                # Perform retrieval (需要使用asyncio.run因为retrieve是async方法)
                import asyncio
                results = asyncio.run(self.rrf_retriever.retrieve(
                    query="test query",
                    top_k=3,
                    use_metadata_filter=False
                ))
                
                # Verify results structure
                self.assertIsInstance(results, list)
                self.assertLessEqual(len(results), 3)
                
                # Verify each result has required fields
                for result in results:
                    self.assertIn("doc_id", result)
                    self.assertIn("content", result)
                    self.assertIn("score", result)
                    self.assertIn("metadata", result)
                    self.assertIsInstance(result["score"], (int, float))
    
    def test_rrf_vs_weighted_consistency(self):
        """测试RRF与加权融合的一致性"""
        # Test data
        bm25_scores = {"doc_1": 0.8, "doc_2": 0.6, "doc_3": 0.4}
        vector_scores = {"doc_1": 0.7, "doc_2": 0.9, "doc_3": 0.5}
        top_k = 3
        
        # Get RRF results
        rrf_results = self.rrf_retriever._fuse_results_rrf(bm25_scores, vector_scores, top_k)
        
        # Get weighted results
        weighted_results = self.weighted_retriever._fuse_results(bm25_scores, vector_scores, top_k)
        
        # Both should return the same number of results
        self.assertEqual(len(rrf_results), len(weighted_results))
        
        # Both should contain the same documents (though potentially in different order)
        rrf_doc_ids = {result["doc_id"] for result in rrf_results}
        weighted_doc_ids = {result["doc_id"] for result in weighted_results}
        self.assertEqual(rrf_doc_ids, weighted_doc_ids)
        
        # All scores should be positive
        for result in rrf_results:
            self.assertGreater(result["score"], 0)
        
        for result in weighted_results:
            self.assertGreater(result["score"], 0)
    
    def test_rrf_with_empty_scores(self):
        """测试RRF处理空分数的情况"""
        # Test with empty BM25 scores
        empty_bm25 = {}
        vector_scores = {"doc_1": 0.8, "doc_2": 0.6}
        
        results = self.rrf_retriever._fuse_results_rrf(empty_bm25, vector_scores, 2)
        self.assertEqual(len(results), 2)
        
        # Test with empty vector scores
        bm25_scores = {"doc_1": 0.8, "doc_2": 0.6}
        empty_vector = {}
        
        results = self.rrf_retriever._fuse_results_rrf(bm25_scores, empty_vector, 2)
        self.assertEqual(len(results), 2)
        
        # Test with both empty
        results = self.rrf_retriever._fuse_results_rrf({}, {}, 2)
        self.assertEqual(len(results), 0)
    
    def test_rrf_with_large_k_values(self):
        """测试RRF处理大k值的情况"""
        bm25_scores = {"doc_1": 0.8, "doc_2": 0.6, "doc_3": 0.4}
        vector_scores = {"doc_1": 0.7, "doc_2": 0.9, "doc_3": 0.5}
        
        # Test with very large k
        self.rrf_retriever.set_rrf_k(10000)
        results = self.rrf_retriever._fuse_results_rrf(bm25_scores, vector_scores, 3)
        
        self.assertEqual(len(results), 3)
        for result in results:
            self.assertGreater(result["score"], 0)
    
    def test_rrf_with_small_k_values(self):
        """测试RRF处理小k值的情况"""
        bm25_scores = {"doc_1": 0.8, "doc_2": 0.6, "doc_3": 0.4}
        vector_scores = {"doc_1": 0.7, "doc_2": 0.9, "doc_3": 0.5}
        
        # Test with small k
        self.rrf_retriever.set_rrf_k(1)
        results = self.rrf_retriever._fuse_results_rrf(bm25_scores, vector_scores, 3)
        
        self.assertEqual(len(results), 3)
        for result in results:
            self.assertGreater(result["score"], 0)
    
    def test_rrf_ranking_stability(self):
        """测试RRF排序稳定性"""
        bm25_scores = {"doc_1": 0.8, "doc_2": 0.6, "doc_3": 0.4}
        vector_scores = {"doc_1": 0.7, "doc_2": 0.9, "doc_3": 0.5}
        
        # Run multiple times and check consistency
        results_list = []
        for _ in range(10):
            results = self.rrf_retriever._fuse_results_rrf(bm25_scores, vector_scores, 3)
            results_list.append([r["doc_id"] for r in results])
        
        # All results should be identical (stable sorting)
        first_result = results_list[0]
        for result in results_list[1:]:
            self.assertEqual(result, first_result)
    
    def test_rrf_backward_compatibility(self):
        """测试RRF向后兼容性"""
        # Create retriever without specifying fusion method (should default to weighted)
        default_retriever = HybridRetriever(
            vector_store=self.mock_vector_store,
            query_transformer=self.mock_query_transformer,
            embedding_model=self.mock_embedding_model
        )
        
        # Should default to weighted fusion
        self.assertEqual(default_retriever.fusion_method, "weighted")
        self.assertEqual(default_retriever.rrf_k, 60)  # Default k value
        
        # Should be able to switch to RRF
        default_retriever.set_fusion_method("rrf")
        self.assertEqual(default_retriever.fusion_method, "rrf")
    
    def test_rrf_error_handling(self):
        """测试RRF错误处理"""
        # Test invalid fusion method
        with self.assertRaises(ValueError):
            HybridRetriever(
                vector_store=self.mock_vector_store,
                query_transformer=self.mock_query_transformer,
                embedding_model=self.mock_embedding_model,
                fusion_method="invalid_method"
            )
        
        # Test invalid k value during initialization
        with self.assertRaises(ValueError):
            HybridRetriever(
                vector_store=self.mock_vector_store,
                query_transformer=self.mock_query_transformer,
                embedding_model=self.mock_embedding_model,
                fusion_method="rrf",
                rrf_k=0
            )
    
    def test_rrf_configuration_persistence(self):
        """测试RRF配置持久性"""
        # Set configuration
        self.rrf_retriever.set_fusion_method("weighted")
        self.rrf_retriever.set_rrf_k(100)
        
        # Configuration should persist across multiple operations
        for _ in range(5):
            config = self.rrf_retriever.get_fusion_config()
            self.assertEqual(config["fusion_method"], "weighted")
            self.assertEqual(config["rrf_k"], 100)
        
        # Change configuration
        self.rrf_retriever.set_fusion_method("rrf")
        self.rrf_retriever.set_rrf_k(50)
        
        # New configuration should persist
        for _ in range(5):
            config = self.rrf_retriever.get_fusion_config()
            self.assertEqual(config["fusion_method"], "rrf")
            self.assertEqual(config["rrf_k"], 50)


if __name__ == '__main__':
    # Run with verbose output
    unittest.main(verbosity=2)