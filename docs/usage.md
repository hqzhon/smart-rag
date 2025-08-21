# 使用指南

本文档详细介绍医疗文献RAG系统的使用方法，包括Web界面操作和API接口调用。

## Web界面使用

### 启动系统

1. **启动后端服务**
   ```bash
   python run.py
   ```
   后端API将在 http://localhost:8001 启动

2. **启动前端服务**
   ```bash
   cd frontend
   npm run dev
   ```
   前端界面将在 http://localhost:3001 启动

### 界面功能介绍

#### 1. 文档管理

**上传文档**
- 点击"上传文档"按钮
- 选择医疗PDF文件（支持.pdf, .doc, .docx, .txt格式）
- 文件大小限制：100MB
- 系统会自动处理文档并建立索引

**文档列表**
- 查看已上传的文档列表
- 显示文档名称、上传时间、处理状态
- 支持删除不需要的文档

**处理状态**
- 🟡 处理中：文档正在解析和索引
- 🟢 已完成：文档可用于查询
- 🔴 处理失败：文档格式不支持或处理出错

#### 2. 智能问答

**提问方式**
- 在查询框中输入医疗相关问题
- 支持中文和英文查询
- 可以询问症状、治疗方法、药物信息等

**查询示例**
```
高血压的症状有哪些？
糖尿病患者的饮食注意事项
阿司匹林的副作用和禁忌症
心脏病的早期诊断方法
```

**回答特点**
- 基于上传文档的专业回答
- 提供相关文档来源引用
- 支持流式响应，实时显示生成过程
- 包含置信度评分

#### 3. 会话管理

**会话功能**
- 自动保存对话历史
- 支持多轮对话上下文
- 可以创建新会话或继续之前的对话

**会话操作**
- 新建会话：开始全新的对话
- 清空历史：清除当前会话记录
- 导出对话：保存对话记录为文件

### 高级功能

#### 1. 检索设置

**检索参数调整**
- 检索数量：控制返回相关文档的数量（默认10个）
- 相似度阈值：设置文档相关性的最低要求（默认0.7）
- 混合检索：启用向量检索+BM25的混合策略
- RRF融合：使用倒数排名融合优化结果排序

**查询优化**
- 查询扩展：自动扩展查询关键词
- 查询重写：优化查询表达方式
- 多语言支持：支持中英文混合查询

#### 2. 结果分析

**相关性评分**
- 每个回答都包含置信度评分
- 显示引用文档的相关性分数
- 提供检索结果的详细分析

**来源追踪**
- 点击引用可查看原始文档片段
- 显示文档页码和具体位置
- 支持高亮显示相关内容

## API接口使用

### 基础配置

**API基础URL**: `http://localhost:8001/api/v1`

**认证方式**: 当前版本无需认证（开发环境）

**请求格式**: JSON

**响应格式**: JSON

### 核心接口

#### 1. 健康检查

**接口**: `GET /health`

**描述**: 检查系统运行状态

**请求示例**:
```bash
curl -X GET "http://localhost:8001/api/v1/health" \
     -H "accept: application/json"
```

**响应示例**:
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "timestamp": "2024-01-01T12:00:00Z",
  "components": {
    "database": "healthy",
    "vector_store": "healthy",
    "llm_service": "healthy"
  }
}
```

#### 2. 文档上传

**接口**: `POST /documents/upload`

**描述**: 上传并处理医疗文档

**请求参数**:
- `file`: 文档文件（multipart/form-data）
- `metadata`: 可选的文档元数据（JSON字符串）

**请求示例**:
```bash
curl -X POST "http://localhost:8001/api/v1/documents/upload" \
     -H "accept: application/json" \
     -H "Content-Type: multipart/form-data" \
     -F "file=@medical_document.pdf" \
     -F "metadata={\"category\": \"cardiology\", \"language\": \"zh\"}"
```

**响应示例**:
```json
{
  "document_id": "doc_123456",
  "filename": "medical_document.pdf",
  "status": "processing",
  "message": "文档上传成功，正在处理中",
  "estimated_time": "2-5分钟"
}
```

#### 3. 文档列表

**接口**: `GET /documents`

**描述**: 获取已上传文档列表

**请求参数**:
- `page`: 页码（默认1）
- `size`: 每页数量（默认20）
- `status`: 过滤状态（可选）

**请求示例**:
```bash
curl -X GET "http://localhost:8001/api/v1/documents?page=1&size=10" \
     -H "accept: application/json"
```

**响应示例**:
```json
{
  "documents": [
    {
      "document_id": "doc_123456",
      "filename": "medical_document.pdf",
      "status": "completed",
      "upload_time": "2024-01-01T10:00:00Z",
      "process_time": "2024-01-01T10:03:00Z",
      "chunk_count": 156,
      "metadata": {
        "category": "cardiology",
        "language": "zh"
      }
    }
  ],
  "total": 1,
  "page": 1,
  "size": 10
}
```

#### 4. 智能问答

**接口**: `POST /chat/query`

**描述**: 基于文档进行智能问答

**请求参数**:
```json
{
  "query": "用户查询内容",
  "session_id": "会话ID（可选）",
  "retrieval_config": {
    "top_k": 10,
    "score_threshold": 0.7,
    "use_hybrid": true,
    "use_rrf": true
  },
  "generation_config": {
    "model": "gpt-3.5-turbo",
    "temperature": 0.7,
    "max_tokens": 1000
  }
}
```

**请求示例**:
```bash
curl -X POST "http://localhost:8001/api/v1/chat/query" \
     -H "accept: application/json" \
     -H "Content-Type: application/json" \
     -d '{
       "query": "高血压的症状有哪些？",
       "session_id": "session_123"
     }'
```

**响应示例**:
```json
{
  "answer": "高血压的主要症状包括：\n1. 头痛，特别是后脑勺疼痛\n2. 头晕和眩晕\n3. 心悸和胸闷\n4. 疲劳和乏力\n5. 视力模糊\n6. 耳鸣\n\n需要注意的是，很多高血压患者在早期可能没有明显症状，因此定期测量血压非常重要。",
  "sources": [
    {
      "document_id": "doc_123456",
      "chunk_id": "chunk_789",
      "content": "高血压症状相关内容...",
      "score": 0.92,
      "page": 15
    }
  ],
  "session_id": "session_123",
  "response_time": 2.3,
  "confidence": 0.89
}
```

#### 5. 流式问答

**接口**: `POST /chat/stream`

**描述**: 流式响应的智能问答

**请求参数**: 与普通问答相同

**请求示例**:
```bash
curl -X POST "http://localhost:8001/api/v1/chat/stream" \
     -H "accept: text/event-stream" \
     -H "Content-Type: application/json" \
     -d '{
       "query": "糖尿病的治疗方法有哪些？",
       "session_id": "session_456"
     }'
```

**响应格式**: Server-Sent Events (SSE)
```
data: {"type": "start", "session_id": "session_456"}

data: {"type": "chunk", "content": "糖尿病的治疗方法主要包括："}

data: {"type": "chunk", "content": "\n1. 生活方式干预"}

data: {"type": "sources", "sources": [...]}

data: {"type": "end", "confidence": 0.91}
```

### 高级接口

#### 1. 文档删除

**接口**: `DELETE /documents/{document_id}`

**请求示例**:
```bash
curl -X DELETE "http://localhost:8001/api/v1/documents/doc_123456" \
     -H "accept: application/json"
```

#### 2. 会话管理

**获取会话历史**: `GET /chat/sessions/{session_id}`

**删除会话**: `DELETE /chat/sessions/{session_id}`

**会话列表**: `GET /chat/sessions`

#### 3. 系统统计

**接口**: `GET /stats`

**响应示例**:
```json
{
  "documents": {
    "total": 25,
    "processing": 2,
    "completed": 23
  },
  "queries": {
    "total": 1250,
    "today": 45
  },
  "storage": {
    "total_chunks": 15680,
    "disk_usage": "2.3GB"
  }
}
```

## 最佳实践

### 1. 文档准备

**文档质量**
- 使用清晰、高质量的PDF文档
- 确保文本可以正常复制和搜索
- 避免纯图片格式的文档

**文档组织**
- 按医学专科分类上传文档
- 使用有意义的文件名
- 添加适当的元数据标签

### 2. 查询优化

**查询技巧**
- 使用具体、明确的医学术语
- 避免过于宽泛或模糊的问题
- 可以包含症状、疾病名称、药物名称等关键信息

**多轮对话**
- 利用会话上下文进行深入询问
- 可以要求澄清或补充信息
- 支持追问相关细节

### 3. 结果验证

**信息核实**
- 查看引用来源的可靠性
- 对比多个相关文档的信息
- 注意置信度评分

**专业判断**
- 系统提供的信息仅供参考
- 重要医疗决策需咨询专业医生
- 定期更新文档库以获取最新信息

## 故障排除

### 常见问题

1. **文档上传失败**
   - 检查文件格式和大小
   - 确认网络连接稳定
   - 查看后端日志错误信息

2. **查询无结果**
   - 确认相关文档已上传并处理完成
   - 尝试使用不同的关键词
   - 降低相似度阈值

3. **响应速度慢**
   - 检查系统资源使用情况
   - 考虑减少检索数量
   - 优化查询表达方式

### 性能监控

**关键指标**
- 查询响应时间
- 文档处理速度
- 系统资源使用率
- 检索准确率

**优化建议**
- 定期清理无用文档
- 监控内存和存储使用
- 根据使用情况调整配置参数

## 下一步

- [API详细文档](api.md) - 完整的API接口说明
- [架构指南](architecture.md) - 了解系统内部结构
- [安装配置](installation.md) - 系统部署和配置