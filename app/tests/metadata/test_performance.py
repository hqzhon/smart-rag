"""元数据模块性能测试"""

import asyncio
import pytest
import time
import statistics
import os
from typing import List, Dict, Any
from concurrent.futures import ThreadPoolExecutor
import psutil
import gc

# 导入测试目标
from app.metadata.models.metadata_models import MetadataInfo
from app.metadata.processors.async_processor import TaskPriority
from app.metadata.clients.qianwen_client import QianwenClient
from app.metadata.summarizers.lightweight_summarizer import LightweightSummaryGenerator
from app.metadata.extractors.keybert_extractor import KeyBERTExtractor
from app.metadata.evaluators.quality_evaluator import QualityEvaluator
from app.metadata.processors.async_processor import AsyncMetadataProcessor

class TestPerformance:
    """性能测试类"""
    
    @pytest.fixture
    def sample_texts(self):
        """性能测试用文本样本"""
        return [
            "患者，男性，65岁，主诉胸痛3小时。患者3小时前无明显诱因出现胸骨后疼痛，呈压榨性，向左肩背部放射，伴有出汗、恶心。既往有高血压病史10年，糖尿病史5年。",
            "人工智能技术在医疗领域的应用越来越广泛。机器学习算法可以帮助医生进行疾病诊断，深度学习模型能够分析医学影像，自然语言处理技术可以处理电子病历。",
            "新冠肺炎疫情对全球医疗系统造成了巨大冲击。医院床位紧张，医护人员短缺，医疗资源分配不均。疫苗接种成为控制疫情的关键措施。",
            "糖尿病是一种慢性代谢性疾病，主要特征是血糖水平持续升高。2型糖尿病占糖尿病患者的90%以上，主要与胰岛素抵抗和胰岛β细胞功能缺陷有关。",
            "心血管疾病是全球死亡率最高的疾病之一。冠心病、高血压、心力衰竭是常见的心血管疾病。预防措施包括健康饮食、规律运动、戒烟限酒。"
        ] * 20  # 扩展到100个文本样本
    
    @pytest.fixture
    async def performance_processor(self):
        """性能测试用处理器"""
        api_key = os.getenv("QIANWEN_API_KEY", "test-api-key")
        client = QianwenClient(api_key=api_key)
        
        summarizer = LightweightSummaryGenerator()
        extractor = KeyBERTExtractor()
        evaluator = QualityEvaluator()
        
        processor = AsyncMetadataProcessor(
            summarizer=summarizer,
            extractor=extractor,
            evaluator=evaluator,
            max_workers=4,  # 增加并发数
            batch_size=10,
            enable_quality_check=True
        )
        
        await processor.start()
        yield processor
        await processor.stop()
        await client.close()
    
    def measure_memory_usage(self):
        """测量内存使用情况"""
        process = psutil.Process()
        memory_info = process.memory_info()
        return {
            "rss": memory_info.rss / 1024 / 1024,  # MB
            "vms": memory_info.vms / 1024 / 1024,  # MB
            "percent": process.memory_percent()
        }
    
    def measure_cpu_usage(self):
        """测量CPU使用情况"""
        return psutil.cpu_percent(interval=1)
    
    @pytest.mark.asyncio
    async def test_single_task_performance(self, performance_processor, sample_texts):
        """测试单任务处理性能"""
        text = sample_texts[0]
        
        # 预热
        await performance_processor.submit_task(
            chunk_id="warmup",
            text=text,
            priority=TaskPriority.HIGH
        )
        await asyncio.sleep(2)
        
        # 性能测试
        times = []
        memory_usage = []
        
        for i in range(10):
            start_memory = self.measure_memory_usage()
            start_time = time.time()
            
            task_id = await performance_processor.submit_task(
                chunk_id=f"perf-single-{i:03d}",
                text=text,
                priority=TaskPriority.HIGH
            )
            
            # 等待任务完成
            max_wait = 30
            wait_time = 0
            result = None
            
            while wait_time < max_wait:
                status = await performance_processor.get_task_status(task_id)
                if status and status.get("status") == "completed":
                    result = await performance_processor.get_task_result(task_id)
                    break
                elif status and status.get("status") == "failed":
                    break
                
                await asyncio.sleep(0.1)
                wait_time += 0.1
            
            end_time = time.time()
            end_memory = self.measure_memory_usage()
            
            if result:
                processing_time = end_time - start_time
                times.append(processing_time)
                memory_usage.append(end_memory["rss"] - start_memory["rss"])
        
        # 分析结果
        if times:
            avg_time = statistics.mean(times)
            min_time = min(times)
            max_time = max(times)
            std_time = statistics.stdev(times) if len(times) > 1 else 0
            
            avg_memory = statistics.mean(memory_usage) if memory_usage else 0
            
            print(f"\n单任务性能测试结果:")
            print(f"平均处理时间: {avg_time:.3f}秒")
            print(f"最快处理时间: {min_time:.3f}秒")
            print(f"最慢处理时间: {max_time:.3f}秒")
            print(f"时间标准差: {std_time:.3f}秒")
            print(f"平均内存增长: {avg_memory:.2f}MB")
            
            # 性能断言
            assert avg_time < 10.0, f"平均处理时间过长: {avg_time:.3f}秒"
            assert max_time < 20.0, f"最大处理时间过长: {max_time:.3f}秒"
            assert avg_memory < 50.0, f"内存使用过多: {avg_memory:.2f}MB"
    
    @pytest.mark.asyncio
    async def test_batch_processing_performance(self, performance_processor, sample_texts):
        """测试批量处理性能"""
        batch_sizes = [5, 10, 20, 50]
        results = {}
        
        for batch_size in batch_sizes:
            print(f"\n测试批量大小: {batch_size}")
            
            # 准备批量任务
            tasks = [
                {
                    "chunk_id": f"batch-{batch_size}-{i:03d}",
                    "text": sample_texts[i % len(sample_texts)],
                    "priority": TaskPriority.MEDIUM,
                    "metadata": {"batch_size": batch_size, "index": i}
                }
                for i in range(batch_size)
            ]
            
            start_memory = self.measure_memory_usage()
            start_time = time.time()
            
            # 提交批量任务
            task_ids = await performance_processor.submit_batch_tasks(tasks)
            
            # 等待所有任务完成
            max_wait = 120  # 2分钟超时
            wait_time = 0
            completed_count = 0
            
            while wait_time < max_wait:
                completed_count = 0
                for task_id in task_ids:
                    status = await performance_processor.get_task_status(task_id)
                    if status and status.get("status") in ["completed", "failed"]:
                        completed_count += 1
                
                if completed_count >= len(task_ids) * 0.9:  # 90%完成率
                    break
                
                await asyncio.sleep(1)
                wait_time += 1
            
            end_time = time.time()
            end_memory = self.measure_memory_usage()
            
            # 计算性能指标
            total_time = end_time - start_time
            throughput = completed_count / total_time if total_time > 0 else 0
            memory_growth = end_memory["rss"] - start_memory["rss"]
            
            results[batch_size] = {
                "total_time": total_time,
                "completed_count": completed_count,
                "throughput": throughput,
                "memory_growth": memory_growth,
                "success_rate": completed_count / len(task_ids)
            }
            
            print(f"总处理时间: {total_time:.2f}秒")
            print(f"完成任务数: {completed_count}/{len(task_ids)}")
            print(f"处理吞吐量: {throughput:.2f}任务/秒")
            print(f"内存增长: {memory_growth:.2f}MB")
            print(f"成功率: {results[batch_size]['success_rate']:.2%}")
            
            # 清理内存
            gc.collect()
            await asyncio.sleep(2)
        
        # 分析批量处理性能趋势
        print(f"\n批量处理性能分析:")
        for batch_size, result in results.items():
            print(f"批量大小 {batch_size}: 吞吐量 {result['throughput']:.2f}任务/秒, 成功率 {result['success_rate']:.2%}")
        
        # 性能断言
        for batch_size, result in results.items():
            assert result["success_rate"] >= 0.8, f"批量大小{batch_size}的成功率过低: {result['success_rate']:.2%}"
            assert result["throughput"] > 0.1, f"批量大小{batch_size}的吞吐量过低: {result['throughput']:.2f}任务/秒"
    
    @pytest.mark.asyncio
    async def test_concurrent_processing_performance(self, performance_processor, sample_texts):
        """测试并发处理性能"""
        concurrent_levels = [1, 2, 4, 8]
        results = {}
        
        for concurrent_level in concurrent_levels:
            print(f"\n测试并发级别: {concurrent_level}")
            
            start_memory = self.measure_memory_usage()
            start_time = time.time()
            
            # 创建并发任务
            async def submit_concurrent_tasks(level_id):
                task_ids = []
                for i in range(10):  # 每个并发级别提交10个任务
                    task_id = await performance_processor.submit_task(
                        chunk_id=f"concurrent-{concurrent_level}-{level_id}-{i:03d}",
                        text=sample_texts[i % len(sample_texts)],
                        priority=TaskPriority.MEDIUM
                    )
                    task_ids.append(task_id)
                return task_ids
            
            # 并发提交任务
            all_task_ids = []
            concurrent_tasks = [
                submit_concurrent_tasks(level_id)
                for level_id in range(concurrent_level)
            ]
            
            task_id_groups = await asyncio.gather(*concurrent_tasks)
            for group in task_id_groups:
                all_task_ids.extend(group)
            
            # 等待所有任务完成
            max_wait = 180  # 3分钟超时
            wait_time = 0
            completed_count = 0
            
            while wait_time < max_wait:
                completed_count = 0
                for task_id in all_task_ids:
                    status = await performance_processor.get_task_status(task_id)
                    if status and status.get("status") in ["completed", "failed"]:
                        completed_count += 1
                
                if completed_count >= len(all_task_ids) * 0.9:
                    break
                
                await asyncio.sleep(2)
                wait_time += 2
            
            end_time = time.time()
            end_memory = self.measure_memory_usage()
            
            # 计算性能指标
            total_time = end_time - start_time
            throughput = completed_count / total_time if total_time > 0 else 0
            memory_growth = end_memory["rss"] - start_memory["rss"]
            
            results[concurrent_level] = {
                "total_time": total_time,
                "completed_count": completed_count,
                "total_tasks": len(all_task_ids),
                "throughput": throughput,
                "memory_growth": memory_growth,
                "success_rate": completed_count / len(all_task_ids)
            }
            
            print(f"总处理时间: {total_time:.2f}秒")
            print(f"完成任务数: {completed_count}/{len(all_task_ids)}")
            print(f"处理吞吐量: {throughput:.2f}任务/秒")
            print(f"内存增长: {memory_growth:.2f}MB")
            print(f"成功率: {results[concurrent_level]['success_rate']:.2%}")
            
            # 清理内存
            gc.collect()
            await asyncio.sleep(3)
        
        # 分析并发性能
        print(f"\n并发处理性能分析:")
        for level, result in results.items():
            print(f"并发级别 {level}: 吞吐量 {result['throughput']:.2f}任务/秒, 成功率 {result['success_rate']:.2%}")
        
        # 性能断言
        for level, result in results.items():
            assert result["success_rate"] >= 0.7, f"并发级别{level}的成功率过低: {result['success_rate']:.2%}"
    
    @pytest.mark.asyncio
    async def test_memory_leak_detection(self, performance_processor, sample_texts):
        """测试内存泄漏检测"""
        print("\n内存泄漏检测测试")
        
        initial_memory = self.measure_memory_usage()
        memory_samples = [initial_memory["rss"]]
        
        # 运行多轮任务
        for round_num in range(5):
            print(f"第 {round_num + 1} 轮任务")
            
            # 提交一批任务
            task_ids = []
            for i in range(20):
                task_id = await performance_processor.submit_task(
                    chunk_id=f"memory-test-{round_num}-{i:03d}",
                    text=sample_texts[i % len(sample_texts)],
                    priority=TaskPriority.LOW
                )
                task_ids.append(task_id)
            
            # 等待任务完成
            max_wait = 60
            wait_time = 0
            
            while wait_time < max_wait:
                completed_count = 0
                for task_id in task_ids:
                    status = await performance_processor.get_task_status(task_id)
                    if status and status.get("status") in ["completed", "failed"]:
                        completed_count += 1
                
                if completed_count >= len(task_ids) * 0.9:
                    break
                
                await asyncio.sleep(1)
                wait_time += 1
            
            # 强制垃圾回收
            gc.collect()
            await asyncio.sleep(2)
            
            # 记录内存使用
            current_memory = self.measure_memory_usage()
            memory_samples.append(current_memory["rss"])
            
            print(f"当前内存使用: {current_memory['rss']:.2f}MB")
        
        # 分析内存趋势
        memory_growth = memory_samples[-1] - memory_samples[0]
        max_memory = max(memory_samples)
        min_memory = min(memory_samples)
        
        print(f"\n内存使用分析:")
        print(f"初始内存: {memory_samples[0]:.2f}MB")
        print(f"最终内存: {memory_samples[-1]:.2f}MB")
        print(f"内存增长: {memory_growth:.2f}MB")
        print(f"最大内存: {max_memory:.2f}MB")
        print(f"最小内存: {min_memory:.2f}MB")
        
        # 内存泄漏检测
        memory_growth_rate = memory_growth / memory_samples[0] if memory_samples[0] > 0 else 0
        print(f"内存增长率: {memory_growth_rate:.2%}")
        
        # 断言：内存增长不应超过50%
        assert memory_growth_rate < 0.5, f"检测到可能的内存泄漏，内存增长率: {memory_growth_rate:.2%}"
        assert memory_growth < 200, f"内存增长过多: {memory_growth:.2f}MB"
    
    @pytest.mark.asyncio
    async def test_stress_testing(self, performance_processor, sample_texts):
        """压力测试"""
        print("\n压力测试开始")
        
        start_memory = self.measure_memory_usage()
        start_time = time.time()
        
        # 大量任务提交
        total_tasks = 200
        task_ids = []
        
        print(f"提交 {total_tasks} 个任务")
        
        # 分批提交任务以避免过载
        batch_size = 20
        for batch_start in range(0, total_tasks, batch_size):
            batch_end = min(batch_start + batch_size, total_tasks)
            batch_tasks = []
            
            for i in range(batch_start, batch_end):
                task = {
                    "chunk_id": f"stress-test-{i:04d}",
                    "text": sample_texts[i % len(sample_texts)],
                    "priority": TaskPriority.LOW,
                    "metadata": {"stress_test": True, "batch": batch_start // batch_size}
                }
                batch_tasks.append(task)
            
            batch_task_ids = await performance_processor.submit_batch_tasks(batch_tasks)
            task_ids.extend(batch_task_ids)
            
            # 短暂等待避免过载
            await asyncio.sleep(0.5)
        
        print(f"已提交 {len(task_ids)} 个任务")
        
        # 监控任务完成情况
        max_wait = 600  # 10分钟超时
        wait_time = 0
        last_completed = 0
        
        while wait_time < max_wait:
            completed_count = 0
            failed_count = 0
            
            for task_id in task_ids:
                status = await performance_processor.get_task_status(task_id)
                if status:
                    if status.get("status") == "completed":
                        completed_count += 1
                    elif status.get("status") == "failed":
                        failed_count += 1
            
            # 进度报告
            if completed_count > last_completed:
                progress = (completed_count + failed_count) / len(task_ids)
                current_memory = self.measure_memory_usage()
                print(f"进度: {progress:.1%} ({completed_count + failed_count}/{len(task_ids)}), "
                      f"成功: {completed_count}, 失败: {failed_count}, "
                      f"内存: {current_memory['rss']:.1f}MB")
                last_completed = completed_count
            
            # 检查完成条件
            if (completed_count + failed_count) >= len(task_ids) * 0.95:
                break
            
            await asyncio.sleep(5)
            wait_time += 5
        
        end_time = time.time()
        end_memory = self.measure_memory_usage()
        
        # 最终统计
        final_completed = 0
        final_failed = 0
        
        for task_id in task_ids:
            status = await performance_processor.get_task_status(task_id)
            if status:
                if status.get("status") == "completed":
                    final_completed += 1
                elif status.get("status") == "failed":
                    final_failed += 1
        
        total_time = end_time - start_time
        throughput = final_completed / total_time if total_time > 0 else 0
        success_rate = final_completed / len(task_ids)
        memory_growth = end_memory["rss"] - start_memory["rss"]
        
        print(f"\n压力测试结果:")
        print(f"总任务数: {len(task_ids)}")
        print(f"成功完成: {final_completed}")
        print(f"失败任务: {final_failed}")
        print(f"总处理时间: {total_time:.2f}秒")
        print(f"平均吞吐量: {throughput:.2f}任务/秒")
        print(f"成功率: {success_rate:.2%}")
        print(f"内存增长: {memory_growth:.2f}MB")
        
        # 获取处理器统计信息
        processor_stats = performance_processor.get_stats()
        print(f"\n处理器统计:")
        for key, value in processor_stats.items():
            print(f"{key}: {value}")
        
        # 压力测试断言
        assert success_rate >= 0.8, f"压力测试成功率过低: {success_rate:.2%}"
        assert throughput > 0.5, f"压力测试吞吐量过低: {throughput:.2f}任务/秒"
        assert memory_growth < 500, f"压力测试内存增长过多: {memory_growth:.2f}MB"
        
        print("\n压力测试通过！")

if __name__ == "__main__":
    # 运行性能测试
    pytest.main(["-v", "-s", __file__])