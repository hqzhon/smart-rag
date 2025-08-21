#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RRF性能基准测试
"""

import unittest
import time
import statistics
from unittest.mock import Mock
from typing import Dict, List
import random

# Import the HybridRetriever class
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.retrieval.retriever import HybridRetriever


class TestRRFPerformance(unittest.TestCase):
    """RRF性能基准测试类"""
    
    def setUp(self):
        """测试初始化"""
        # Mock dependencies
        self.mock_vector_store = Mock()
        self.mock_query_transformer = Mock()
        self.mock_embedding_model = Mock()
        
        # Create retriever instance
        self.retriever = HybridRetriever(
            vector_store=self.mock_vector_store,
            query_transformer=self.mock_query_transformer,
            embedding_model=self.mock_embedding_model,
            fusion_method="rrf",
            rrf_k=60
        )
        
        # Generate test data
        self.test_data_small = self._generate_test_data(50)
        self.test_data_medium = self._generate_test_data(200)
        self.test_data_large = self._generate_test_data(1000)
    
    def _generate_test_data(self, num_docs: int) -> tuple:
        """生成测试数据
        
        Args:
            num_docs: 文档数量
            
        Returns:
            (bm25_scores, vector_scores) 元组
        """
        doc_ids = [f"doc_{i}" for i in range(num_docs)]
        
        # Generate random scores with some overlap
        bm25_docs = random.sample(doc_ids, min(num_docs, int(num_docs * 0.8)))
        vector_docs = random.sample(doc_ids, min(num_docs, int(num_docs * 0.8)))
        
        bm25_scores = {doc_id: random.uniform(0.1, 1.0) for doc_id in bm25_docs}
        vector_scores = {doc_id: random.uniform(0.1, 1.0) for doc_id in vector_docs}
        
        return bm25_scores, vector_scores
    
    def _benchmark_fusion_method(self, method_name: str, fusion_func, test_data: tuple, iterations: int = 100) -> Dict:
        """基准测试融合方法
        
        Args:
            method_name: 方法名称
            fusion_func: 融合函数
            test_data: 测试数据
            iterations: 迭代次数
            
        Returns:
            性能统计字典
        """
        bm25_scores, vector_scores = test_data
        execution_times = []
        
        # Warm up
        for _ in range(5):
            fusion_func(bm25_scores, vector_scores, 10)
        
        # Benchmark
        for _ in range(iterations):
            start_time = time.perf_counter()
            result = fusion_func(bm25_scores, vector_scores, 10)
            end_time = time.perf_counter()
            
            execution_times.append((end_time - start_time) * 1000)  # Convert to milliseconds
        
        return {
            "method": method_name,
            "data_size": len(set(bm25_scores.keys()) | set(vector_scores.keys())),
            "iterations": iterations,
            "avg_time_ms": statistics.mean(execution_times),
            "median_time_ms": statistics.median(execution_times),
            "min_time_ms": min(execution_times),
            "max_time_ms": max(execution_times),
            "std_dev_ms": statistics.stdev(execution_times) if len(execution_times) > 1 else 0
        }
    
    def test_rrf_performance_small_dataset(self):
        """测试小数据集上的RRF性能"""
        print("\n=== Small Dataset Performance Test (50 docs) ===")
        
        # Test RRF
        rrf_stats = self._benchmark_fusion_method(
            "RRF", 
            self.retriever._fuse_results_rrf, 
            self.test_data_small
        )
        
        # Test weighted fusion
        weighted_stats = self._benchmark_fusion_method(
            "Weighted", 
            self.retriever._fuse_results, 
            self.test_data_small
        )
        
        self._print_performance_comparison(rrf_stats, weighted_stats)
        
        # Performance assertions
        self.assertLess(rrf_stats["avg_time_ms"], 10.0, "RRF should be fast on small datasets")
        self.assertLess(weighted_stats["avg_time_ms"], 10.0, "Weighted fusion should be fast on small datasets")
    
    def test_rrf_performance_medium_dataset(self):
        """测试中等数据集上的RRF性能"""
        print("\n=== Medium Dataset Performance Test (200 docs) ===")
        
        # Test RRF
        rrf_stats = self._benchmark_fusion_method(
            "RRF", 
            self.retriever._fuse_results_rrf, 
            self.test_data_medium
        )
        
        # Test weighted fusion
        weighted_stats = self._benchmark_fusion_method(
            "Weighted", 
            self.retriever._fuse_results, 
            self.test_data_medium
        )
        
        self._print_performance_comparison(rrf_stats, weighted_stats)
        
        # Performance assertions
        self.assertLess(rrf_stats["avg_time_ms"], 50.0, "RRF should be reasonably fast on medium datasets")
        self.assertLess(weighted_stats["avg_time_ms"], 50.0, "Weighted fusion should be reasonably fast on medium datasets")
    
    def test_rrf_performance_large_dataset(self):
        """测试大数据集上的RRF性能"""
        print("\n=== Large Dataset Performance Test (1000 docs) ===")
        
        # Test RRF
        rrf_stats = self._benchmark_fusion_method(
            "RRF", 
            self.retriever._fuse_results_rrf, 
            self.test_data_large,
            iterations=50  # Fewer iterations for large dataset
        )
        
        # Test weighted fusion
        weighted_stats = self._benchmark_fusion_method(
            "Weighted", 
            self.retriever._fuse_results, 
            self.test_data_large,
            iterations=50
        )
        
        self._print_performance_comparison(rrf_stats, weighted_stats)
        
        # Performance assertions
        self.assertLess(rrf_stats["avg_time_ms"], 200.0, "RRF should complete within reasonable time on large datasets")
        self.assertLess(weighted_stats["avg_time_ms"], 200.0, "Weighted fusion should complete within reasonable time on large datasets")
    
    def test_rrf_k_parameter_performance_impact(self):
        """测试RRF参数k对性能的影响"""
        print("\n=== RRF K Parameter Performance Impact ===")
        
        k_values = [10, 30, 60, 100]
        results = []
        
        for k in k_values:
            self.retriever.set_rrf_k(k)
            stats = self._benchmark_fusion_method(
                f"RRF (k={k})", 
                self.retriever._fuse_results_rrf, 
                self.test_data_medium,
                iterations=50
            )
            results.append(stats)
            print(f"k={k}: {stats['avg_time_ms']:.3f}ms (avg)")
        
        # K parameter should not significantly impact performance
        avg_times = [r["avg_time_ms"] for r in results]
        performance_variance = max(avg_times) - min(avg_times)
        self.assertLess(performance_variance, 5.0, "K parameter should not significantly impact performance")
    
    def test_memory_usage_comparison(self):
        """测试内存使用对比"""
        import tracemalloc
        
        print("\n=== Memory Usage Comparison ===")
        
        # Test RRF memory usage
        tracemalloc.start()
        for _ in range(10):
            self.retriever._fuse_results_rrf(*self.test_data_large, 10)
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        rrf_memory_kb = peak / 1024
        
        # Test weighted fusion memory usage
        tracemalloc.start()
        for _ in range(10):
            self.retriever._fuse_results(*self.test_data_large, 10)
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        weighted_memory_kb = peak / 1024
        
        print(f"RRF Memory Usage: {rrf_memory_kb:.2f} KB")
        print(f"Weighted Memory Usage: {weighted_memory_kb:.2f} KB")
        
        # Memory usage should be reasonable
        self.assertLess(rrf_memory_kb, 1000, "RRF memory usage should be reasonable")
        self.assertLess(weighted_memory_kb, 1000, "Weighted fusion memory usage should be reasonable")
    
    def test_scalability_analysis(self):
        """测试可扩展性分析"""
        print("\n=== Scalability Analysis ===")
        
        dataset_sizes = [50, 100, 200, 500, 1000]
        rrf_times = []
        weighted_times = []
        
        for size in dataset_sizes:
            test_data = self._generate_test_data(size)
            
            # Test RRF
            rrf_stats = self._benchmark_fusion_method(
                "RRF", 
                self.retriever._fuse_results_rrf, 
                test_data,
                iterations=20
            )
            rrf_times.append(rrf_stats["avg_time_ms"])
            
            # Test weighted fusion
            weighted_stats = self._benchmark_fusion_method(
                "Weighted", 
                self.retriever._fuse_results, 
                test_data,
                iterations=20
            )
            weighted_times.append(weighted_stats["avg_time_ms"])
            
            print(f"Size {size}: RRF={rrf_stats['avg_time_ms']:.3f}ms, Weighted={weighted_stats['avg_time_ms']:.3f}ms")
        
        # Check that performance scales reasonably
        # Time complexity should be roughly O(n log n) due to sorting
        for i in range(1, len(rrf_times)):
            scale_factor = dataset_sizes[i] / dataset_sizes[i-1]
            time_factor = rrf_times[i] / rrf_times[i-1]
            
            # Time should not increase more than quadratically with data size
            self.assertLess(time_factor, scale_factor ** 2, 
                          f"RRF performance should scale reasonably (size factor: {scale_factor}, time factor: {time_factor})")
    
    def _print_performance_comparison(self, rrf_stats: Dict, weighted_stats: Dict):
        """打印性能对比结果"""
        print(f"\nPerformance Comparison (Data Size: {rrf_stats['data_size']} docs):")
        print(f"{'Method':<12} {'Avg (ms)':<10} {'Median (ms)':<12} {'Min (ms)':<10} {'Max (ms)':<10} {'Std Dev':<10}")
        print("-" * 70)
        
        for stats in [rrf_stats, weighted_stats]:
            print(f"{stats['method']:<12} {stats['avg_time_ms']:<10.3f} {stats['median_time_ms']:<12.3f} "
                  f"{stats['min_time_ms']:<10.3f} {stats['max_time_ms']:<10.3f} {stats['std_dev_ms']:<10.3f}")
        
        # Calculate performance improvement
        if weighted_stats['avg_time_ms'] > 0:
            improvement = ((weighted_stats['avg_time_ms'] - rrf_stats['avg_time_ms']) / weighted_stats['avg_time_ms']) * 100
            print(f"\nRRF Performance: {improvement:+.1f}% vs Weighted Fusion")


if __name__ == '__main__':
    # Run with verbose output
    unittest.main(verbosity=2)