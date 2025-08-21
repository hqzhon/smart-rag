# RQ集成指南

本指南介绍如何使用基于Redis Queue (RQ)的异步元数据处理功能，实现生产者-消费者模式，避免阻塞主流程。

## 概述

传统的`DocumentProcessor`在处理文档时会同步执行所有步骤，包括元数据生成，这会导致主流程被阻塞。通过RQ集成，我们将元数据生成任务异步化，主流程只负责文档解析、清洗和分块，然后将元数据生成任务推送到Redis队列中，由后台Worker异步处理。

## 架构设计

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  DocumentProcessor │    │   Redis Queue   │    │   RQ Workers    │
│   (生产者)        │───▶│                 │───▶│   (消费者)      │
│                 │    │                 │    │                 │
│ 1. 解析文档      │    │ 元数据生成任务   │    │ 1. 关键词提取    │
│ 2. 文本清洗      │    │                 │    │ 2. 摘要生成      │
│ 3. 术语标准化    │    │                 │    │ 3. 质量评估      │
│ 4. 质量过滤      │    │                 │    │ 4. 结果存储      │
│ 5. 推送任务      │    │                 │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## 前置条件

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 启动Redis服务器

```bash
# macOS (使用Homebrew)
brew install redis
brew services start redis

# 或者直接启动
redis-server
```

### 3. 验证Redis连接

```bash
redis-cli ping
# 应该返回: PONG
```

## 使用方法

### 1. 启动RQ Worker

在后台启动RQ Worker来处理元数据生成任务：

```bash
# 启动Worker（默认2个进程）
python scripts/start_rq_worker.py

# 自定义Worker数量
WORKER_COUNT=4 python scripts/start_rq_worker.py

# 自定义Redis连接
REDIS_HOST=localhost REDIS_PORT=6379 python scripts/start_rq_worker.py
```

### 2. 使用DocumentProcessor（启用RQ）

```python
from app.processors.document_processor import DocumentProcessor

# 初始化DocumentProcessor，启用异步元数据处理
processor = DocumentProcessor(
    input_dir='./input',
    output_dir='./output',
    enable_async_metadata=True,  # 启用RQ集成
    redis_host='localhost',
    redis_port=6379,
    enable_cleaning=True,
    enable_terminology_standardization=True,
    enable_quality_filtering=True
)

# 处理文档（非阻塞）
results = processor.process_all_documents()

# 主流程立即返回，元数据生成在后台异步进行
print(f"处理完成，共 {len(results)} 个文档")
print("元数据生成任务已推送到队列，正在后台处理...")
```

### 3. 监控任务状态

#### 使用RQ Dashboard（推荐）

```bash
# 启动RQ Dashboard
rq-dashboard

# 访问 http://localhost:9181 查看任务状态
```

#### 使用命令行

```bash
# 查看队列状态
rq info

# 查看Worker状态
rq info --only-workers

# 查看失败的任务
rq info --only-failed
```

## 配置选项

### DocumentProcessor配置

```python
processor = DocumentProcessor(
    input_dir='./input',           # 输入目录
    output_dir='./output',         # 输出目录
    enable_async_metadata=True,    # 启用异步元数据处理
    redis_host='localhost',        # Redis服务器地址
    redis_port=6379,              # Redis服务器端口
    use_enhanced_parser=True,      # 使用增强PDF解析器
    enable_cleaning=True,          # 启用文本清洗
    enable_terminology_standardization=True,  # 启用术语标准化
    enable_quality_filtering=True  # 启用质量过滤
)
```

### RQ Worker配置

通过环境变量配置：

```bash
export REDIS_HOST=localhost     # Redis服务器地址
export REDIS_PORT=6379          # Redis服务器端口
export WORKER_COUNT=2           # Worker进程数量
```

## 任务流程

### 1. 文档处理流程

1. **DocumentProcessor**处理文档：
   - 解析PDF/TXT文件
   - 文本清洗和标准化
   - 质量过滤和分块
   - 为每个文本块生成唯一ID

2. **推送任务到队列**：
   - 为每个文本块创建元数据生成任务
   - 推送到Redis队列
   - 主流程立即返回

3. **Worker异步处理**：
   - 从队列中获取任务
   - 执行关键词提取
   - 生成文本摘要
   - 评估内容质量
   - 存储处理结果

### 2. 任务参数

每个元数据生成任务包含以下参数：

```python
{
    'chunk_id': 'uuid',      # 文本块唯一标识
    'chunk_text': 'string',  # 文本块内容
    'document_id': 'uuid',   # 文档唯一标识
    'job_timeout': '10m',    # 任务超时时间
    'result_ttl': 86400,     # 结果保存时间（秒）
    'failure_ttl': 604800    # 失败记录保存时间（秒）
}
```

## 故障处理

### 1. Redis连接失败

如果Redis连接失败，系统会自动禁用异步元数据处理：

```python
# 日志输出
ERROR - 初始化RQ队列失败: [Errno 61] Connection refused
WARNING - 将禁用异步元数据处理
```

### 2. 任务失败重试

RQ会自动重试失败的任务，可以通过RQ Dashboard查看失败原因。

### 3. Worker崩溃恢复

重新启动Worker即可继续处理队列中的任务：

```bash
python scripts/start_rq_worker.py
```

## 性能优化

### 1. Worker数量调优

根据CPU核心数和任务复杂度调整Worker数量：

```bash
# 推荐设置为CPU核心数的1-2倍
WORKER_COUNT=4 python scripts/start_rq_worker.py
```

### 2. Redis配置优化

在`redis.conf`中优化配置：

```conf
# 增加最大内存
maxmemory 2gb
maxmemory-policy allkeys-lru

# 启用持久化
save 900 1
save 300 10
save 60 10000
```

### 3. 任务超时设置

根据任务复杂度调整超时时间：

```python
job = queue.enqueue(
    generate_metadata_for_chunk,
    chunk_id, chunk_text, document_id,
    job_timeout='15m',  # 增加超时时间
    result_ttl=86400,
    failure_ttl=604800
)
```

## 示例代码

完整的使用示例请参考：

- `examples/rq_integration_example.py` - 完整使用示例
- `tests/test_rq_integration.py` - 集成测试
- `scripts/start_rq_worker.py` - Worker启动脚本

## 常见问题

### Q: 如何确认任务是否成功推送到队列？

A: 查看日志输出或使用RQ Dashboard监控队列状态。

### Q: Worker处理任务时出现内存不足怎么办？

A: 减少Worker数量或增加系统内存，也可以调整任务批处理大小。

### Q: 如何清空队列中的所有任务？

A: 使用Redis命令：`redis-cli FLUSHDB`

### Q: 任务结果如何获取？

A: 目前任务结果存储在Redis中，可以通过RQ Dashboard查看或实现自定义的结果处理逻辑。

## 总结

通过RQ集成，我们成功实现了：

1. **非阻塞处理**：主流程不再等待元数据生成完成
2. **可扩展性**：可以启动多个Worker并行处理任务
3. **容错性**：任务失败会自动重试，Worker崩溃不影响队列
4. **监控能力**：通过RQ Dashboard实时监控任务状态
5. **资源隔离**：元数据处理与文档处理分离，互不影响

这种架构特别适合处理大量文档的场景，能够显著提高系统的吞吐量和响应速度。