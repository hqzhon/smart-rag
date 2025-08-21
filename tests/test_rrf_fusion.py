#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RRF融合算法单元测试
"""

import unittest
from unittest.mock import Mock, AsyncMock
import asyncio
from typing import Dict, List

# Import the HybridRetriever class
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.retrieval.retriever import HybridRetriever


class TestRRFFusion(unittest.TestCase):
    """RRF融合算法测试类"""
    
    def setUp(self):
        """测试初始化"""
        # Mock dependencies
        self.mock_vector_store = Mock()
        self.mock_query_transformer = Mock()
        self.mock_embedding_model = Mock()
        
        # Create retriever instance with RRF fusion
        self.retriever = HybridRetriever(
            vector_store=self.mock_vector_store,
            query_transformer=self.mock_query_transformer,
            embedding_model=self.mock_embedding_model,
            fusion_method="rrf",
            rrf_k=60
        )
    
    def test_rrf_fusion_basic(self):
        """测试RRF融合基本功能"""
        # Test data
        bm25_scores = {
            "doc1": 0.9,
            "doc2": 0.7,
            "doc3": 0.5,
            "doc4": 0.3
        }
        
        vector_scores = {
            "doc1": 0.8,
            "doc2": 0.6,
            "doc3": 0.9,  # Higher vector score than BM25
            "doc5": 0.7   # Only in vector results
        }
        
        # Execute RRF fusion
        result = self.retriever._fuse_results_rrf(bm25_scores, vector_scores, top_k=3)
        
        # Verify results
        self.assertEqual(len(result), 3)
        self.assertIsInstance(result, list)
        
        # Extract doc_ids from result dictionaries
        result_doc_ids = [item['doc_id'] for item in result]
        
        # doc1 should be ranked high (appears in both with good scores)
        self.assertIn("doc1", result_doc_ids)
        
        # Verify all returned IDs are valid
        all_doc_ids = set(bm25_scores.keys()) | set(vector_scores.keys())
        for doc_id in result_doc_ids:
            self.assertIn(doc_id, all_doc_ids)
            
        # Verify each result has required fields
        for item in result:
            self.assertIn('doc_id', item)
            self.assertIn('score', item)
            self.assertIn('content', item)
            self.assertIn('metadata', item)
    
    def test_rrf_fusion_ranking_logic(self):
        """测试RRF排名逻辑的正确性"""
        # Simple test case where we can manually verify RRF scores
        bm25_scores = {
            "doc1": 1.0,  # Rank 1 in BM25
            "doc2": 0.5   # Rank 2 in BM25
        }
        
        vector_scores = {
            "doc2": 1.0,  # Rank 1 in vector
            "doc1": 0.5   # Rank 2 in vector
        }
        
        result = self.retriever._fuse_results_rrf(bm25_scores, vector_scores, top_k=2)
        
        # Manual RRF calculation with k=60:
        # doc1: 1/(60+1) + 1/(60+2) = 1/61 + 1/62 ≈ 0.0164 + 0.0161 = 0.0325
        # doc2: 1/(60+2) + 1/(60+1) = 1/62 + 1/61 ≈ 0.0161 + 0.0164 = 0.0325
        # Both should have very similar scores, but doc1 might have slight edge due to floating point precision
        
        self.assertEqual(len(result), 2)
        result_doc_ids = [item['doc_id'] for item in result]
        self.assertIn("doc1", result_doc_ids)
        self.assertIn("doc2", result_doc_ids)
    
    def test_rrf_fusion_single_source(self):
        """测试只有单一检索源的情况"""
        # Only BM25 scores
        bm25_scores = {
            "doc1": 0.9,
            "doc2": 0.7,
            "doc3": 0.5
        }
        vector_scores = {}
        
        result = self.retriever._fuse_results_rrf(bm25_scores, vector_scores, top_k=2)
        
        self.assertEqual(len(result), 2)
        result_doc_ids = [item['doc_id'] for item in result]
        self.assertEqual(result_doc_ids[0], "doc1")  # Highest BM25 score
        self.assertEqual(result_doc_ids[1], "doc2")  # Second highest BM25 score
        
        # Only vector scores
        bm25_scores = {}
        vector_scores = {
            "doc1": 0.9,
            "doc2": 0.7,
            "doc3": 0.5
        }
        
        result = self.retriever._fuse_results_rrf(bm25_scores, vector_scores, top_k=2)
        
        self.assertEqual(len(result), 2)
        result_doc_ids = [item['doc_id'] for item in result]
        self.assertEqual(result_doc_ids[0], "doc1")  # Highest vector score
        self.assertEqual(result_doc_ids[1], "doc2")  # Second highest vector score
    
    def test_rrf_fusion_empty_input(self):
        """测试空输入的情况"""
        result = self.retriever._fuse_results_rrf({}, {}, top_k=5)
        self.assertEqual(result, [])
    
    def test_rrf_k_parameter_effect(self):
        """测试RRF参数k对结果的影响"""
        bm25_scores = {"doc1": 1.0, "doc2": 0.5}
        vector_scores = {"doc2": 1.0, "doc1": 0.5}
        
        # Test with different k values
        original_k = self.retriever.rrf_k
        
        # Small k (more sensitive to rank differences)
        self.retriever.set_rrf_k(10)
        result_small_k = self.retriever._fuse_results_rrf(bm25_scores, vector_scores, top_k=2)
        
        # Large k (less sensitive to rank differences)
        self.retriever.set_rrf_k(100)
        result_large_k = self.retriever._fuse_results_rrf(bm25_scores, vector_scores, top_k=2)
        
        # Both should return same documents but potentially different order
        small_k_doc_ids = set(item['doc_id'] for item in result_small_k)
        large_k_doc_ids = set(item['doc_id'] for item in result_large_k)
        self.assertEqual(small_k_doc_ids, large_k_doc_ids)
        self.assertEqual(len(result_small_k), 2)
        self.assertEqual(len(result_large_k), 2)
        
        # Restore original k
        self.retriever.set_rrf_k(original_k)
    
    def test_fusion_method_switching(self):
        """测试融合方法切换功能"""
        # Test initial method
        self.assertEqual(self.retriever.fusion_method, "rrf")
        
        # Test switching to weighted
        self.retriever.set_fusion_method("weighted")
        self.assertEqual(self.retriever.fusion_method, "weighted")
        
        # Test switching back to RRF
        self.retriever.set_fusion_method("rrf")
        self.assertEqual(self.retriever.fusion_method, "rrf")
        
        # Test invalid method
        with self.assertRaises(ValueError):
            self.retriever.set_fusion_method("invalid_method")
    
    def test_rrf_k_parameter_validation(self):
        """测试RRF参数k的验证"""
        # Test valid k values
        self.retriever.set_rrf_k(30)
        self.assertEqual(self.retriever.rrf_k, 30)
        
        self.retriever.set_rrf_k(100)
        self.assertEqual(self.retriever.rrf_k, 100)
        
        # Test invalid k values
        with self.assertRaises(ValueError):
            self.retriever.set_rrf_k(0)
        
        with self.assertRaises(ValueError):
            self.retriever.set_rrf_k(-10)
    
    def test_get_fusion_config(self):
        """测试获取融合配置功能"""
        config = self.retriever.get_fusion_config()
        
        self.assertIsInstance(config, dict)
        self.assertIn("fusion_method", config)
        self.assertIn("rrf_k", config)
        self.assertEqual(config["fusion_method"], "rrf")
        self.assertEqual(config["rrf_k"], 60)
        
        # Test after changing configuration
        self.retriever.set_fusion_method("weighted")
        self.retriever.set_rrf_k(40)
        
        updated_config = self.retriever.get_fusion_config()
        self.assertEqual(updated_config["fusion_method"], "weighted")
        self.assertEqual(updated_config["rrf_k"], 40)
    
    def test_rrf_vs_weighted_fusion_comparison(self):
        """测试RRF与传统加权融合的对比"""
        bm25_scores = {
            "doc1": 0.9,
            "doc2": 0.7,
            "doc3": 0.5
        }
        
        vector_scores = {
            "doc1": 0.6,
            "doc2": 0.8,
            "doc3": 0.9
        }
        
        # Test RRF fusion
        self.retriever.set_fusion_method("rrf")
        rrf_result = self.retriever._fuse_results_rrf(bm25_scores, vector_scores, top_k=3)
        
        # Test weighted fusion
        weighted_result = self.retriever._fuse_results(bm25_scores, vector_scores, top_k=3)
        
        # Both should return same number of results
        self.assertEqual(len(rrf_result), 3)
        self.assertEqual(len(weighted_result), 3)
        
        # Both should contain same documents (though potentially different order)
        rrf_doc_ids = set(item['doc_id'] for item in rrf_result)
        weighted_doc_ids = set(item['doc_id'] for item in weighted_result)
        self.assertEqual(rrf_doc_ids, weighted_doc_ids)


if __name__ == '__main__':
    unittest.main()