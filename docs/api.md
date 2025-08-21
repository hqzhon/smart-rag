# API接口文档

医疗文献RAG系统提供完整的RESTful API接口，支持文档管理、智能问答、会话管理等功能。

## 基础信息

**Base URL**: `http://localhost:8001/api/v1`

**API版本**: v1

**认证方式**: 无需认证（开发环境）

**请求格式**: JSON

**响应格式**: JSON

**字符编码**: UTF-8

## 通用响应格式

### 成功响应
```json
{
  "success": true,
  "data": {},
  "message": "操作成功",
  "timestamp": "2024-01-01T12:00:00Z"
}
```

### 错误响应
```json
{
  "success": false,
  "error": {
    "code": "ERROR_CODE",
    "message": "错误描述",
    "details": {}
  },
  "timestamp": "2024-01-01T12:00:00Z"
}
```

### HTTP状态码
- `200` - 请求成功
- `201` - 创建成功
- `400` - 请求参数错误
- `404` - 资源不存在
- `500` - 服务器内部错误
- `503` - 服务不可用

## 系统接口

### 健康检查

**接口**: `GET /health`

**描述**: 检查系统运行状态和各组件健康状况

**请求参数**: 无

**响应示例**:
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "timestamp": "2024-01-01T12:00:00Z",
  "uptime": "2d 5h 30m",
  "components": {
    "database": {
      "status": "healthy",
      "response_time": "5ms"
    },
    "vector_store": {
      "status": "healthy",
      "collections": 3,
      "total_documents": 1250
    },
    "llm_service": {
      "status": "healthy",
      "provider": "openai",
      "model": "gpt-3.5-turbo"
    },
    "embedding_service": {
      "status": "healthy",
      "provider": "openai",
      "model": "text-embedding-ada-002"
    }
  },
  "system_info": {
    "cpu_usage": "45%",
    "memory_usage": "8.2GB/16GB",
    "disk_usage": "25.6GB/100GB"
  }
}
```

**cURL示例**:
```bash
curl -X GET "http://localhost:8001/api/v1/health" \
     -H "accept: application/json"
```

### 系统统计

**接口**: `GET /stats`

**描述**: 获取系统使用统计信息

**请求参数**:
- `period` (可选): 统计周期 (`day`, `week`, `month`)

**响应示例**:
```json
{
  "documents": {
    "total": 125,
    "processing": 3,
    "completed": 120,
    "failed": 2,
    "total_size": "2.5GB",
    "total_chunks": 15680
  },
  "queries": {
    "total": 5420,
    "today": 89,
    "this_week": 634,
    "this_month": 2156,
    "avg_response_time": "2.3s",
    "success_rate": "98.5%"
  },
  "sessions": {
    "total": 456,
    "active": 12,
    "avg_duration": "15m 30s"
  },
  "storage": {
    "vector_db_size": "1.8GB",
    "document_storage": "2.5GB",
    "log_files": "150MB",
    "cache_size": "256MB"
  }
}
```

## 文档管理接口

### 上传文档

**接口**: `POST /documents/upload`

**描述**: 上传医疗文档并进行处理

**请求格式**: `multipart/form-data`

**请求参数**:
- `file` (必需): 文档文件
- `metadata` (可选): 文档元数据 (JSON字符串)
- `processing_options` (可选): 处理选项 (JSON字符串)

**元数据字段**:
```json
{
  "title": "文档标题",
  "category": "医学分类",
  "language": "zh|en",
  "author": "作者",
  "publication_date": "2024-01-01",
  "tags": ["标签1", "标签2"],
  "description": "文档描述"
}
```

**处理选项**:
```json
{
  "chunk_size": 1000,
  "chunk_overlap": 200,
  "extract_tables": true,
  "extract_images": false,
  "ocr_enabled": true,
  "language_detection": true
}
```

**响应示例**:
```json
{
  "document_id": "doc_1704110400_abc123",
  "filename": "cardiology_guidelines.pdf",
  "original_filename": "心脏病诊疗指南.pdf",
  "file_size": 5242880,
  "mime_type": "application/pdf",
  "status": "processing",
  "upload_time": "2024-01-01T12:00:00Z",
  "estimated_processing_time": "3-5分钟",
  "metadata": {
    "category": "cardiology",
    "language": "zh"
  },
  "processing_info": {
    "total_pages": 156,
    "estimated_chunks": 180,
    "processing_queue_position": 2
  }
}
```

**cURL示例**:
```bash
curl -X POST "http://localhost:8001/api/v1/documents/upload" \
     -H "accept: application/json" \
     -F "file=@cardiology_guidelines.pdf" \
     -F "metadata={\"category\": \"cardiology\", \"language\": \"zh\", \"tags\": [\"心脏病\", \"诊疗指南\"]}"
```

### 获取文档列表

**接口**: `GET /documents`

**描述**: 获取已上传文档的列表

**请求参数**:
- `page` (可选): 页码，默认1
- `size` (可选): 每页数量，默认20，最大100
- `status` (可选): 过滤状态 (`processing`, `completed`, `failed`)
- `category` (可选): 过滤分类
- `search` (可选): 搜索关键词
- `sort` (可选): 排序字段 (`upload_time`, `filename`, `file_size`)
- `order` (可选): 排序方向 (`asc`, `desc`)

**响应示例**:
```json
{
  "documents": [
    {
      "document_id": "doc_1704110400_abc123",
      "filename": "cardiology_guidelines.pdf",
      "original_filename": "心脏病诊疗指南.pdf",
      "status": "completed",
      "file_size": 5242880,
      "upload_time": "2024-01-01T12:00:00Z",
      "process_time": "2024-01-01T12:03:45Z",
      "processing_duration": "3m 45s",
      "chunk_count": 187,
      "page_count": 156,
      "metadata": {
        "category": "cardiology",
        "language": "zh",
        "tags": ["心脏病", "诊疗指南"]
      },
      "statistics": {
        "query_count": 45,
        "last_queried": "2024-01-01T15:30:00Z"
      }
    }
  ],
  "pagination": {
    "total": 125,
    "page": 1,
    "size": 20,
    "pages": 7
  },
  "filters": {
    "status": "completed",
    "category": null,
    "search": null
  }
}
```

### 获取文档详情

**接口**: `GET /documents/{document_id}`

**描述**: 获取指定文档的详细信息

**路径参数**:
- `document_id`: 文档ID

**响应示例**:
```json
{
  "document_id": "doc_1704110400_abc123",
  "filename": "cardiology_guidelines.pdf",
  "original_filename": "心脏病诊疗指南.pdf",
  "status": "completed",
  "file_info": {
    "size": 5242880,
    "mime_type": "application/pdf",
    "md5_hash": "d41d8cd98f00b204e9800998ecf8427e"
  },
  "timestamps": {
    "upload_time": "2024-01-01T12:00:00Z",
    "process_start": "2024-01-01T12:00:30Z",
    "process_complete": "2024-01-01T12:03:45Z",
    "last_accessed": "2024-01-01T15:30:00Z"
  },
  "processing_info": {
    "total_pages": 156,
    "total_chunks": 187,
    "processing_duration": "3m 45s",
    "extraction_stats": {
      "text_blocks": 1245,
      "tables": 23,
      "images": 45,
      "footnotes": 67
    }
  },
  "metadata": {
    "title": "心脏病诊疗指南",
    "category": "cardiology",
    "language": "zh",
    "author": "中华医学会心血管病学分会",
    "tags": ["心脏病", "诊疗指南"],
    "description": "最新心脏病诊疗指南"
  },
  "usage_statistics": {
    "query_count": 45,
    "unique_sessions": 23,
    "avg_relevance_score": 0.87,
    "most_queried_topics": ["症状", "治疗", "药物"]
  }
}
```

### 删除文档

**接口**: `DELETE /documents/{document_id}`

**描述**: 删除指定文档及其相关数据

**路径参数**:
- `document_id`: 文档ID

**请求参数**:
- `force` (可选): 强制删除，默认false

**响应示例**:
```json
{
  "message": "文档删除成功",
  "document_id": "doc_1704110400_abc123",
  "deleted_items": {
    "document_file": true,
    "vector_embeddings": 187,
    "metadata_records": 1,
    "cache_entries": 12
  },
  "freed_space": "5.2MB"
}
```

### 获取文档处理状态

**接口**: `GET /documents/{document_id}/status`

**描述**: 获取文档处理的实时状态

**响应示例**:
```json
{
  "document_id": "doc_1704110400_abc123",
  "status": "processing",
  "progress": {
    "current_step": "embedding_generation",
    "completed_steps": ["text_extraction", "chunking"],
    "remaining_steps": ["vector_storage"],
    "percentage": 75
  },
  "processing_info": {
    "start_time": "2024-01-01T12:00:30Z",
    "elapsed_time": "2m 15s",
    "estimated_remaining": "1m 30s",
    "current_operation": "生成文本嵌入向量",
    "processed_chunks": 140,
    "total_chunks": 187
  },
  "errors": [],
  "warnings": [
    "检测到部分图片质量较低，OCR结果可能不准确"
  ]
}
```

## 智能问答接口

### 标准问答

**接口**: `POST /chat/query`

**描述**: 基于文档库进行智能问答

**请求参数**:
```json
{
  "query": "用户查询内容",
  "session_id": "会话ID（可选）",
  "document_filters": {
    "document_ids": ["doc_123", "doc_456"],
    "categories": ["cardiology", "neurology"],
    "tags": ["治疗", "药物"]
  },
  "retrieval_config": {
    "top_k": 10,
    "score_threshold": 0.7,
    "use_hybrid_search": true,
    "use_rrf_fusion": true,
    "rrf_k": 60,
    "rerank_results": true
  },
  "generation_config": {
    "model": "gpt-3.5-turbo",
    "temperature": 0.7,
    "max_tokens": 1000,
    "top_p": 0.9,
    "frequency_penalty": 0.0,
    "presence_penalty": 0.0
  },
  "response_config": {
    "include_sources": true,
    "include_confidence": true,
    "include_reasoning": false,
    "language": "zh"
  }
}
```

**响应示例**:
```json
{
  "query_id": "query_1704110400_xyz789",
  "session_id": "session_123",
  "answer": "高血压的主要症状包括：\n\n1. **头痛**：特别是后脑勺和太阳穴区域的疼痛，通常在早晨较为明显。\n\n2. **头晕和眩晕**：由于血压升高影响脑部血液循环。\n\n3. **心悸**：感觉心跳加快或不规律。\n\n4. **胸闷**：胸部有压迫感或不适。\n\n5. **疲劳乏力**：容易感到疲倦，精力不足。\n\n6. **视力问题**：可能出现视力模糊或眼前有黑点。\n\n需要注意的是，许多高血压患者在早期可能没有明显症状，这就是为什么高血压被称为'沉默杀手'的原因。定期测量血压是早期发现和控制高血压的关键。",
  "sources": [
    {
      "document_id": "doc_1704110400_abc123",
      "document_title": "心脏病诊疗指南",
      "chunk_id": "chunk_789",
      "content": "高血压患者常见症状包括头痛、头晕、心悸等...",
      "page_number": 45,
      "relevance_score": 0.92,
      "chunk_index": 67
    },
    {
      "document_id": "doc_1704110400_def456",
      "document_title": "高血压防治手册",
      "chunk_id": "chunk_456",
      "content": "早期高血压症状不明显，需要定期监测...",
      "page_number": 23,
      "relevance_score": 0.88,
      "chunk_index": 34
    }
  ],
  "metadata": {
    "confidence_score": 0.91,
    "response_time": 2.34,
    "tokens_used": {
      "prompt_tokens": 1250,
      "completion_tokens": 280,
      "total_tokens": 1530
    },
    "retrieval_stats": {
      "total_candidates": 50,
      "filtered_candidates": 10,
      "reranked_results": 5
    },
    "query_analysis": {
      "detected_language": "zh",
      "query_type": "symptom_inquiry",
      "medical_entities": ["高血压", "症状"],
      "query_complexity": "simple"
    }
  },
  "suggestions": [
    "您还想了解高血压的治疗方法吗？",
    "需要了解高血压的预防措施吗？",
    "想知道高血压的诊断标准吗？"
  ],
  "timestamp": "2024-01-01T12:05:00Z"
}
```

### 流式问答

**接口**: `POST /chat/stream`

**描述**: 流式响应的智能问答，实时返回生成内容

**请求参数**: 与标准问答相同

**响应格式**: Server-Sent Events (SSE)

**事件类型**:
- `start`: 开始生成
- `chunk`: 内容片段
- `sources`: 引用来源
- `metadata`: 元数据信息
- `suggestion`: 相关建议
- `end`: 生成结束
- `error`: 错误信息

**响应示例**:
```
data: {"type": "start", "query_id": "query_123", "session_id": "session_456"}

data: {"type": "chunk", "content": "高血压的主要症状包括："}

data: {"type": "chunk", "content": "\n\n1. **头痛**：特别是后脑勺"}

data: {"type": "chunk", "content": "和太阳穴区域的疼痛"}

data: {"type": "sources", "sources": [{"document_id": "doc_123", "relevance_score": 0.92}]}

data: {"type": "metadata", "confidence_score": 0.91, "tokens_used": 1530}

data: {"type": "suggestion", "suggestions": ["您还想了解高血压的治疗方法吗？"]}

data: {"type": "end", "query_id": "query_123", "total_time": 2.34}
```

**cURL示例**:
```bash
curl -X POST "http://localhost:8001/api/v1/chat/stream" \
     -H "accept: text/event-stream" \
     -H "Content-Type: application/json" \
     -d '{
       "query": "糖尿病的治疗方法有哪些？",
       "session_id": "session_456"
     }'
```

## 会话管理接口

### 创建会话

**接口**: `POST /chat/sessions`

**描述**: 创建新的对话会话

**请求参数**:
```json
{
  "title": "会话标题（可选）",
  "metadata": {
    "user_id": "用户ID",
    "department": "科室",
    "tags": ["标签1", "标签2"]
  }
}
```

**响应示例**:
```json
{
  "session_id": "session_1704110400_abc123",
  "title": "心血管疾病咨询",
  "created_time": "2024-01-01T12:00:00Z",
  "status": "active",
  "metadata": {
    "user_id": "user_123",
    "department": "cardiology"
  }
}
```

### 获取会话列表

**接口**: `GET /chat/sessions`

**描述**: 获取会话列表

**请求参数**:
- `page`: 页码
- `size`: 每页数量
- `status`: 会话状态过滤
- `user_id`: 用户ID过滤

**响应示例**:
```json
{
  "sessions": [
    {
      "session_id": "session_123",
      "title": "心血管疾病咨询",
      "created_time": "2024-01-01T12:00:00Z",
      "last_activity": "2024-01-01T12:30:00Z",
      "message_count": 8,
      "status": "active",
      "duration": "30m 15s"
    }
  ],
  "pagination": {
    "total": 45,
    "page": 1,
    "size": 20,
    "pages": 3
  }
}
```

### 获取会话详情

**接口**: `GET /chat/sessions/{session_id}`

**描述**: 获取指定会话的详细信息和消息历史

**请求参数**:
- `include_messages`: 是否包含消息历史，默认true
- `message_limit`: 消息数量限制，默认50

**响应示例**:
```json
{
  "session_id": "session_123",
  "title": "心血管疾病咨询",
  "created_time": "2024-01-01T12:00:00Z",
  "last_activity": "2024-01-01T12:30:00Z",
  "status": "active",
  "statistics": {
    "message_count": 8,
    "query_count": 4,
    "total_tokens": 5420,
    "avg_response_time": "2.1s",
    "duration": "30m 15s"
  },
  "messages": [
    {
      "message_id": "msg_123",
      "type": "user",
      "content": "高血压的症状有哪些？",
      "timestamp": "2024-01-01T12:05:00Z"
    },
    {
      "message_id": "msg_124",
      "type": "assistant",
      "content": "高血压的主要症状包括...",
      "timestamp": "2024-01-01T12:05:03Z",
      "metadata": {
        "confidence": 0.91,
        "sources_count": 3,
        "response_time": 2.34
      }
    }
  ]
}
```

### 删除会话

**接口**: `DELETE /chat/sessions/{session_id}`

**描述**: 删除指定会话及其所有消息

**响应示例**:
```json
{
  "message": "会话删除成功",
  "session_id": "session_123",
  "deleted_messages": 8
}
```

## 错误处理

### 错误代码

| 错误代码 | HTTP状态码 | 描述 |
|---------|-----------|------|
| `INVALID_REQUEST` | 400 | 请求参数无效 |
| `UNAUTHORIZED` | 401 | 未授权访问 |
| `FORBIDDEN` | 403 | 禁止访问 |
| `NOT_FOUND` | 404 | 资源不存在 |
| `METHOD_NOT_ALLOWED` | 405 | 请求方法不允许 |
| `REQUEST_TIMEOUT` | 408 | 请求超时 |
| `PAYLOAD_TOO_LARGE` | 413 | 请求体过大 |
| `UNSUPPORTED_MEDIA_TYPE` | 415 | 不支持的媒体类型 |
| `RATE_LIMIT_EXCEEDED` | 429 | 请求频率超限 |
| `INTERNAL_SERVER_ERROR` | 500 | 服务器内部错误 |
| `SERVICE_UNAVAILABLE` | 503 | 服务不可用 |

### 详细错误信息

```json
{
  "success": false,
  "error": {
    "code": "INVALID_REQUEST",
    "message": "请求参数验证失败",
    "details": {
      "field": "query",
      "issue": "查询内容不能为空",
      "received": "",
      "expected": "非空字符串"
    },
    "request_id": "req_1704110400_xyz789"
  },
  "timestamp": "2024-01-01T12:00:00Z"
}
```

## 速率限制

### 限制规则

| 接口类型 | 限制 | 时间窗口 |
|---------|------|----------|
| 文档上传 | 10次 | 1小时 |
| 标准问答 | 100次 | 1小时 |
| 流式问答 | 50次 | 1小时 |
| 其他接口 | 1000次 | 1小时 |

### 限制响应头

```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1704114000
X-RateLimit-Window: 3600
```

## SDK和示例

### Python SDK示例

```python
import requests
import json

class MedicalRAGClient:
    def __init__(self, base_url="http://localhost:8001/api/v1"):
        self.base_url = base_url
        self.session = requests.Session()
    
    def upload_document(self, file_path, metadata=None):
        url = f"{self.base_url}/documents/upload"
        files = {'file': open(file_path, 'rb')}
        data = {}
        if metadata:
            data['metadata'] = json.dumps(metadata)
        
        response = self.session.post(url, files=files, data=data)
        return response.json()
    
    def query(self, question, session_id=None, **kwargs):
        url = f"{self.base_url}/chat/query"
        payload = {
            "query": question,
            "session_id": session_id,
            **kwargs
        }
        
        response = self.session.post(url, json=payload)
        return response.json()
    
    def stream_query(self, question, session_id=None, **kwargs):
        url = f"{self.base_url}/chat/stream"
        payload = {
            "query": question,
            "session_id": session_id,
            **kwargs
        }
        
        response = self.session.post(url, json=payload, stream=True)
        for line in response.iter_lines():
            if line.startswith(b'data: '):
                data = json.loads(line[6:])
                yield data

# 使用示例
client = MedicalRAGClient()

# 上传文档
result = client.upload_document(
    "medical_document.pdf",
    metadata={"category": "cardiology", "language": "zh"}
)
print(f"文档上传: {result['document_id']}")

# 标准查询
response = client.query("高血压的症状有哪些？")
print(f"回答: {response['answer']}")

# 流式查询
for chunk in client.stream_query("糖尿病的治疗方法"):
    if chunk['type'] == 'chunk':
        print(chunk['content'], end='', flush=True)
```

### JavaScript SDK示例

```javascript
class MedicalRAGClient {
    constructor(baseUrl = 'http://localhost:8001/api/v1') {
        this.baseUrl = baseUrl;
    }
    
    async uploadDocument(file, metadata = {}) {
        const formData = new FormData();
        formData.append('file', file);
        formData.append('metadata', JSON.stringify(metadata));
        
        const response = await fetch(`${this.baseUrl}/documents/upload`, {
            method: 'POST',
            body: formData
        });
        
        return await response.json();
    }
    
    async query(question, sessionId = null, options = {}) {
        const response = await fetch(`${this.baseUrl}/chat/query`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                query: question,
                session_id: sessionId,
                ...options
            })
        });
        
        return await response.json();
    }
    
    async* streamQuery(question, sessionId = null, options = {}) {
        const response = await fetch(`${this.baseUrl}/chat/stream`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                query: question,
                session_id: sessionId,
                ...options
            })
        });
        
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        
        while (true) {
            const { done, value } = await reader.read();
            if (done) break;
            
            const chunk = decoder.decode(value);
            const lines = chunk.split('\n');
            
            for (const line of lines) {
                if (line.startsWith('data: ')) {
                    const data = JSON.parse(line.slice(6));
                    yield data;
                }
            }
        }
    }
}

// 使用示例
const client = new MedicalRAGClient();

// 上传文档
const fileInput = document.getElementById('file-input');
const file = fileInput.files[0];
const result = await client.uploadDocument(file, {
    category: 'cardiology',
    language: 'zh'
});
console.log('文档上传:', result.document_id);

// 标准查询
const response = await client.query('高血压的症状有哪些？');
console.log('回答:', response.answer);

// 流式查询
for await (const chunk of client.streamQuery('糖尿病的治疗方法')) {
    if (chunk.type === 'chunk') {
        console.log(chunk.content);
    }
}
```

## 版本更新

### v1.0.0 (当前版本)
- 基础文档管理功能
- 智能问答和流式响应
- 会话管理
- 混合检索和RRF融合
- 完整的错误处理和监控

### 计划功能
- 用户认证和权限管理
- 多租户支持
- 高级分析和报告
- 批量操作接口
- WebSocket实时通信

## 技术支持

如有API使用问题，请参考：
- [安装配置指南](installation.md)
- [使用指南](usage.md)
- [架构文档](architecture.md)
- [故障排除指南](troubleshooting.md)