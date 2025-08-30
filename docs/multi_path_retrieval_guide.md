# 多路召回RAG检索系统使用指南

## 概述

多路召回RAG检索系统是一个高性能、可配置的文档检索解决方案，支持四路并行召回策略：

- **向量检索**：基于语义相似度的密集向量检索
- **关键词检索**：基于BM25算法的关键词匹配
- **摘要检索**：针对文档摘要的专门检索
- **全文检索**：全文内容的BM25检索

系统通过加权RRF（Reciprocal Rank Fusion）算法融合多路结果，并支持千问API重排序，实现高质量的检索效果。

## 系统架构

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Query Input   │───▶│  FusionRetriever │───▶│ Enhanced Rerank │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                │
                                ▼
                    ┌───────────────────────┐
                    │    Parallel Paths     │
                    └───────────────────────┘
                                │
                ┌───────┬───────┼───────┬───────┐
                ▼       ▼       ▼       ▼       ▼
        ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐
        │ Vector  │ │Keywords │ │Summary  │ │Fulltext │
        │Retrieval│ │Retrieval│ │Retrieval│ │Retrieval│
        └─────────┘ └─────────┘ └─────────┘ └─────────┘
                │       │       │       │
                └───────┼───────┼───────┘
                        ▼
                ┌─────────────────┐
                │ Fusion Engine   │
                │ (Weighted RRF)  │
                └─────────────────┘
```

## 快速开始

### 1. 基本使用

```python
import asyncio
from app.retrieval.integrated_retriever import IntegratedRetriever, RetrievalRequest
from app.retrieval.advanced_config import AdvancedRAGConfig

# 创建检索器实例
retriever = IntegratedRetriever(
    vector_store=your_vector_store,
    documents=your_documents,
    qianwen_client=your_qianwen_client
)

# 创建检索请求
request = RetrievalRequest(
    query="机器学习算法优化",
    top_k=10,
    enable_rerank=True,
    rerank_top_k=5
)

# 执行检索
response = await retriever.retrieve(request)

# 获取结果
for doc in response.documents:
    print(f"Score: {doc.score}, Content: {doc.page_content[:100]}...")
```

### 2. 配置管理

```python
# 使用预设配置
balanced_config = AdvancedRAGConfig.create_balanced_config()
vector_focused_config = AdvancedRAGConfig.create_vector_focused_config()
keyword_focused_config = AdvancedRAGConfig.create_keyword_focused_config()

# 更新检索器配置
await retriever.update_config(balanced_config)

# 自定义配置
custom_config = AdvancedRAGConfig.create_balanced_config()
custom_config.fusion.path_weights = {
    "vector": 0.4,
    "keywords": 0.3,
    "summary": 0.2,
    "fulltext": 0.1
}
await retriever.update_config(custom_config)
```

## 配置详解

### 核心配置类

#### AdvancedRAGConfig

主配置类，包含所有子配置模块：

```python
@dataclass
class AdvancedRAGConfig:
    paths: PathConfig          # 各路径配置
    fusion: FusionConfig       # 融合算法配置
    rerank: RerankConfig       # 重排序配置
    performance: PerformanceConfig  # 性能配置
```

#### PathConfig - 检索路径配置

```python
# 各路径独立配置
config.paths.vector.enabled = True
config.paths.vector.top_k = 20
config.paths.vector.weight = 0.4

config.paths.keywords.enabled = True
config.paths.keywords.top_k = 15
config.paths.keywords.weight = 0.3

config.paths.summary.enabled = True
config.paths.summary.top_k = 10
config.paths.summary.weight = 0.2

config.paths.fulltext.enabled = True
config.paths.fulltext.top_k = 10
config.paths.fulltext.weight = 0.1
```

#### FusionConfig - 融合算法配置

```python
# 融合方法选择
config.fusion.method = FusionMethod.WEIGHTED_RRF  # 加权RRF
config.fusion.method = FusionMethod.SIMPLE_RRF    # 简单RRF
config.fusion.method = FusionMethod.WEIGHTED_SUM  # 加权求和
config.fusion.method = FusionMethod.MAX_SCORE    # 最大分数

# RRF参数
config.fusion.rrf_k = 60  # RRF常数
config.fusion.enable_score_normalization = True
config.fusion.enable_diversity_penalty = True
config.fusion.diversity_threshold = 0.8
```

#### RerankConfig - 重排序配置

```python
# 重排序策略
config.rerank.strategy = RerankStrategy.QIANWEN_API
config.rerank.top_k = 10
config.rerank.batch_size = 5
config.rerank.enable_caching = True
config.rerank.cache_ttl = 3600
```

#### PerformanceConfig - 性能配置

```python
# 性能优化
config.performance.enable_caching = True
config.performance.cache_ttl = 1800
config.performance.max_concurrent_requests = 10
config.performance.request_timeout = 30.0
config.performance.enable_monitoring = True
```

### 预设配置场景

#### 1. 均衡配置 (Balanced)

适用于大多数场景的均衡配置：

```python
config = AdvancedRAGConfig.create_balanced_config()
# 权重分配: vector=0.35, keywords=0.3, summary=0.25, fulltext=0.1
```

#### 2. 向量优先配置 (Vector Focused)

适用于语义相似度要求高的场景：

```python
config = AdvancedRAGConfig.create_vector_focused_config()
# 权重分配: vector=0.6, keywords=0.2, summary=0.15, fulltext=0.05
```

#### 3. 关键词优先配置 (Keyword Focused)

适用于精确匹配要求高的场景：

```python
config = AdvancedRAGConfig.create_keyword_focused_config()
# 权重分配: vector=0.2, keywords=0.5, summary=0.2, fulltext=0.1
```

#### 4. 快速检索配置 (Fast Retrieval)

适用于对响应时间要求高的场景：

```python
config = AdvancedRAGConfig.create_fast_config()
# 较小的top_k值，启用缓存，禁用重排序
```

#### 5. 高精度配置 (High Precision)

适用于对检索质量要求极高的场景：

```python
config = AdvancedRAGConfig.create_high_precision_config()
# 较大的top_k值，启用所有优化功能
```

## 高级功能

### 1. 批量检索

```python
requests = [
    RetrievalRequest(query="查询1", top_k=5),
    RetrievalRequest(query="查询2", top_k=5),
    RetrievalRequest(query="查询3", top_k=5)
]

responses = await retriever.batch_retrieve(requests)
```

### 2. 性能监控

```python
# 获取性能统计
stats = await retriever.get_performance_stats()
print(f"平均检索时间: {stats.avg_retrieval_time:.3f}s")
print(f"缓存命中率: {stats.cache_hit_rate:.2%}")

# 健康检查
health = await retriever.health_check()
print(f"系统状态: {health.status}")
```

### 3. 动态配置更新

```python
# 运行时更新权重
new_weights = {
    "vector": 0.5,
    "keywords": 0.3,
    "summary": 0.15,
    "fulltext": 0.05
}

config = await retriever.get_config()
config.fusion.path_weights = new_weights
await retriever.update_config(config)
```

### 4. 文档更新

```python
# 添加新文档
new_documents = [doc1, doc2, doc3]
await retriever.update_documents(new_documents, mode="add")

# 替换文档
await retriever.update_documents(updated_documents, mode="replace")

# 删除文档
await retriever.update_documents(doc_ids_to_remove, mode="remove")
```

## 性能优化

### 1. 缓存策略

```python
# 启用多级缓存
config.performance.enable_caching = True
config.performance.cache_ttl = 3600  # 1小时
config.rerank.enable_caching = True
config.rerank.cache_ttl = 1800  # 30分钟
```

### 2. 并发控制

```python
# 控制并发请求数
config.performance.max_concurrent_requests = 20
config.performance.request_timeout = 30.0

# 批处理优化
config.rerank.batch_size = 10
```

### 3. 索引优化

```python
# 多字段BM25索引
from app.retrieval.multi_field_bm25 import MultiFieldBM25Retriever

bm25_retriever = MultiFieldBM25Retriever(documents)

# 预热索引
await bm25_retriever.build_indices()
```

## 基准测试和调优

### 1. 运行基准测试

```python
from tools.benchmark_retrieval import RetrievalBenchmark
from tools.benchmark_config import BenchmarkRunner

# 创建基准测试
benchmark = RetrievalBenchmark(retriever)
runner = BenchmarkRunner(retriever)

# 运行完整测试套件
results = await runner.run_full_benchmark_suite()

# 快速性能测试
quick_results = await runner.run_quick_performance_test()
```

### 2. 权重自动优化

```python
# 自动权重优化
optimization_result = await runner.run_weight_optimization(
    metric="ndcg_5",  # 优化目标：NDCG@5
    max_iterations=50
)

# 应用优化结果
optimized_config = AdvancedRAGConfig.create_balanced_config()
optimized_config.fusion.path_weights = optimization_result.best_weights
await retriever.update_config(optimized_config)
```

### 3. 性能分析

```python
from tools.benchmark_retrieval import BenchmarkVisualizer

# 创建可视化
visualizer = BenchmarkVisualizer()

# 性能对比图
visualizer.plot_performance_comparison(results)

# 优化历史图
visualizer.plot_optimization_history(optimization_result)
```

## 错误处理和监控

### 1. 异常处理

```python
from app.retrieval.monitoring import RetrievalError, PathRetrievalError

try:
    response = await retriever.retrieve(request)
except PathRetrievalError as e:
    print(f"路径检索错误: {e.path} - {e.message}")
except RetrievalError as e:
    print(f"检索错误: {e.message}")
```

### 2. 监控和告警

```python
from app.retrieval.monitoring import get_monitor

# 获取监控实例
monitor = get_monitor()

# 检查系统健康状态
health_status = monitor.get_health_status()
for component, status in health_status.items():
    print(f"{component}: {status.status}")

# 获取性能指标
metrics = monitor.get_performance_metrics()
print(f"平均响应时间: {metrics.avg_response_time:.3f}s")
print(f"错误率: {metrics.error_rate:.2%}")
```

### 3. 熔断器

```python
# 熔断器会自动处理故障
# 当某个组件连续失败时，会暂时跳过该组件
# 系统会定期尝试恢复

# 检查熔断器状态
circuit_status = monitor.get_circuit_breaker_status()
for component, is_open in circuit_status.items():
    if is_open:
        print(f"警告: {component} 熔断器已开启")
```

## 最佳实践

### 1. 配置选择指南

| 场景 | 推荐配置 | 说明 |
|------|----------|------|
| 通用问答 | balanced | 均衡的语义和关键词匹配 |
| 技术文档检索 | keyword_focused | 精确的术语匹配 |
| 语义搜索 | vector_focused | 强调语义相似度 |
| 实时应用 | fast_retrieval | 优化响应时间 |
| 研究分析 | high_precision | 最高检索质量 |

### 2. 性能调优建议

1. **根据数据规模调整top_k**：
   - 小数据集（<1万文档）：top_k=10-20
   - 中等数据集（1-10万文档）：top_k=20-50
   - 大数据集（>10万文档）：top_k=50-100

2. **权重分配策略**：
   - 结构化数据：增加keywords权重
   - 长文本数据：增加vector和summary权重
   - 混合数据：使用balanced配置

3. **缓存策略**：
   - 高频查询：启用缓存，TTL=1-2小时
   - 实时数据：禁用缓存或短TTL（5-10分钟）
   - 静态数据：长TTL（6-24小时）

### 3. 监控指标

重要监控指标：

- **响应时间**：平均<500ms，P95<1s
- **缓存命中率**：>70%
- **错误率**：<1%
- **各路径成功率**：>95%
- **重排序成功率**：>90%

### 4. 故障排查

常见问题和解决方案：

1. **检索速度慢**：
   - 检查缓存配置
   - 减少top_k值
   - 禁用重排序
   - 增加并发限制

2. **检索质量差**：
   - 调整权重分配
   - 启用重排序
   - 检查文档质量
   - 运行权重优化

3. **系统不稳定**：
   - 检查监控指标
   - 查看错误日志
   - 检查熔断器状态
   - 调整超时设置

## 示例代码

### 完整使用示例

```python
import asyncio
from app.retrieval.integrated_retriever import IntegratedRetriever, RetrievalRequest
from app.retrieval.advanced_config import AdvancedRAGConfig
from tools.benchmark_config import BenchmarkRunner

async def main():
    # 1. 初始化检索器
    retriever = IntegratedRetriever(
        vector_store=your_vector_store,
        documents=your_documents,
        qianwen_client=your_qianwen_client
    )
    
    # 2. 配置系统
    config = AdvancedRAGConfig.create_balanced_config()
    config.performance.enable_caching = True
    config.performance.cache_ttl = 3600
    await retriever.update_config(config)
    
    # 3. 执行检索
    request = RetrievalRequest(
        query="深度学习神经网络优化算法",
        top_k=10,
        enable_rerank=True,
        rerank_top_k=5
    )
    
    response = await retriever.retrieve(request)
    
    # 4. 处理结果
    print(f"检索到 {len(response.documents)} 个文档")
    print(f"检索时间: {response.retrieval_time:.3f}s")
    print(f"重排序时间: {response.rerank_time:.3f}s")
    
    for i, doc in enumerate(response.documents):
        print(f"{i+1}. Score: {doc.score:.4f}")
        print(f"   Content: {doc.page_content[:100]}...")
        print()
    
    # 5. 性能监控
    stats = await retriever.get_performance_stats()
    print(f"系统统计:")
    print(f"  平均检索时间: {stats.avg_retrieval_time:.3f}s")
    print(f"  缓存命中率: {stats.cache_hit_rate:.2%}")
    print(f"  总请求数: {stats.total_requests}")
    
    # 6. 运行基准测试（可选）
    runner = BenchmarkRunner(retriever)
    quick_results = await runner.run_quick_performance_test()
    
    print("\n基准测试结果:")
    for config_name, metrics in quick_results.items():
        print(f"{config_name}: 时间={metrics['avg_time']:.3f}s, NDCG@5={metrics['avg_ndcg_5']:.3f}")

if __name__ == "__main__":
    asyncio.run(main())
```

## 总结

多路召回RAG检索系统提供了：

1. **灵活的配置**：支持多种预设和自定义配置
2. **高性能**：并行检索、智能缓存、熔断保护
3. **高质量**：多路融合、智能重排序
4. **可监控**：全面的性能指标和健康检查
5. **易调优**：自动化基准测试和权重优化

通过合理配置和使用，可以显著提升RAG系统的检索效果和用户体验。