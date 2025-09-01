# API Reference

The Medical Literature RAG System provides a complete RESTful API that supports document management, intelligent Q&A, session management, and more.

## Basic Information

**Base URL**: `http://localhost:8001/api/v1`

**API Version**: v1

**Authentication**: None required (for development environment)

**Request Format**: JSON

**Response Format**: JSON

**Character Encoding**: UTF-8

## Common Response Format

### Success Response
```json
{
  "success": true,
  "data": {},
  "message": "Operation successful",
  "timestamp": "2024-01-01T12:00:00Z"
}
```

### Error Response
```json
{
  "success": false,
  "error": {
    "code": "ERROR_CODE",
    "message": "Error description",
    "details": {}
  },
  "timestamp": "2024-01-01T12:00:00Z"
}
```

### HTTP Status Codes
- `200` - OK
- `201` - Created
- `400` - Bad Request
- `404` - Not Found
- `500` - Internal Server Error
- `503` - Service Unavailable

## System Endpoints

### Health Check

**Endpoint**: `GET /health`

**Description**: Checks the system's running status and the health of its components.

**Request Parameters**: None

**Response Example**:
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

**cURL Example**:
```bash
curl -X GET "http://localhost:8001/api/v1/health" \
     -H "accept: application/json"
```

### System Statistics

**Endpoint**: `GET /stats`

**Description**: Retrieves system usage statistics.

**Request Parameters**:
- `period` (optional): Time period for stats (`day`, `week`, `month`)

**Response Example**:
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

## Document Management Endpoints

### Upload Document

**Endpoint**: `POST /documents/upload`

**Description**: Uploads and processes a medical document.

**Request Format**: `multipart/form-data`

**Request Parameters**:
- `file` (required): The document file.
- `metadata` (optional): Document metadata (JSON string).
- `processing_options` (optional): Processing options (JSON string).

**Metadata Fields**:
```json
{
  "title": "Document Title",
  "category": "Medical Category",
  "language": "zh|en",
  "author": "Author",
  "publication_date": "2024-01-01",
  "tags": ["Tag1", "Tag2"],
  "description": "Document description"
}
```

**Processing Options**:
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

**Response Example**:
```json
{
  "document_id": "doc_1704110400_abc123",
  "filename": "cardiology_guidelines.pdf",
  "original_filename": "Cardiology Treatment Guidelines.pdf",
  "file_size": 5242880,
  "mime_type": "application/pdf",
  "status": "processing",
  "upload_time": "2024-01-01T12:00:00Z",
  "estimated_processing_time": "3-5 minutes",
  "metadata": {
    "category": "cardiology",
    "language": "en"
  },
  "processing_info": {
    "total_pages": 156,
    "estimated_chunks": 180,
    "processing_queue_position": 2
  }
}
```

**cURL Example**:
```bash
curl -X POST "http://localhost:8001/api/v1/documents/upload" \
     -H "accept: application/json" \
     -F "file=@cardiology_guidelines.pdf" \
     -F "metadata={\"category\": \"cardiology\", \"language\": \"en\", \"tags\": [\"Cardiology\", \"Guidelines\"]}"
```

### Get Document List

**Endpoint**: `GET /documents`

**Description**: Retrieves a list of uploaded documents.

**Request Parameters**:
- `page` (optional): Page number, default 1.
- `size` (optional): Items per page, default 20, max 100.
- `status` (optional): Filter by status (`processing`, `completed`, `failed`).
- `category` (optional): Filter by category.
- `search` (optional): Search keyword.
- `sort` (optional): Sort field (`upload_time`, `filename`, `file_size`).
- `order` (optional): Sort direction (`asc`, `desc`).

**Response Example**:
```json
{
  "documents": [
    {
      "document_id": "doc_1704110400_abc123",
      "filename": "cardiology_guidelines.pdf",
      "original_filename": "Cardiology Treatment Guidelines.pdf",
      "status": "completed",
      "file_size": 5242880,
      "upload_time": "2024-01-01T12:00:00Z",
      "process_time": "2024-01-01T12:03:45Z",
      "processing_duration": "3m 45s",
      "chunk_count": 187,
      "page_count": 156,
      "metadata": {
        "category": "cardiology",
        "language": "en",
        "tags": ["Cardiology", "Guidelines"]
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

### Get Document Details

**Endpoint**: `GET /documents/{document_id}`

**Description**: Retrieves detailed information for a specific document.

**Path Parameters**:
- `document_id`: The document ID.

**Response Example**:
```json
{
  "document_id": "doc_1704110400_abc123",
  "filename": "cardiology_guidelines.pdf",
  "original_filename": "Cardiology Treatment Guidelines.pdf",
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
    "title": "Cardiology Treatment Guidelines",
    "category": "cardiology",
    "language": "en",
    "author": "American Heart Association",
    "tags": ["Cardiology", "Guidelines"],
    "description": "The latest guidelines for treating heart disease."
  },
  "usage_statistics": {
    "query_count": 45,
    "unique_sessions": 23,
    "avg_relevance_score": 0.87,
    "most_queried_topics": ["symptoms", "treatment", "medication"]
  }
}
```

### Delete Document

**Endpoint**: `DELETE /documents/{document_id}`

**Description**: Deletes a specific document and its related data.

**Path Parameters**:
- `document_id`: The document ID.

**Request Parameters**:
- `force` (optional): Force delete, default is false.

**Response Example**:
```json
{
  "message": "Document deleted successfully",
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

### Get Document Processing Status

**Endpoint**: `GET /documents/{document_id}/status`

**Description**: Retrieves the real-time processing status of a document.

**Response Example**:
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
    "current_operation": "Generating text embedding vectors",
    "processed_chunks": 140,
    "total_chunks": 187
  },
  "errors": [],
  "warnings": [
    "Detected some low-quality images, OCR results may be inaccurate."
  ]
}
```

## Intelligent Q&A Endpoints

### Standard Q&A

**Endpoint**: `POST /chat/query`

**Description**: Performs intelligent Q&A based on the document library.

**Request Body**:
```json
{
  "query": "User query content",
  "session_id": "Session ID (optional)",
  "document_filters": {
    "document_ids": ["doc_123", "doc_456"],
    "categories": ["cardiology", "neurology"],
    "tags": ["treatment", "medication"]
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
    "language": "en"
  }
}
```

**Response Example**:
```json
{
  "query_id": "query_1704110400_xyz789",
  "session_id": "session_123",
  "answer": "The main symptoms of hypertension include:\n\n1. **Headaches**: Especially in the back of the head and temples, often more pronounced in the morning.\n\n2. **Dizziness and Vertigo**: Due to high blood pressure affecting blood circulation in the brain.\n\n3. **Palpitations**: A feeling of a rapid or irregular heartbeat.\n\n4. **Chest Tightness**: A feeling of pressure or discomfort in the chest.\n\n5. **Fatigue**: Feeling tired easily and lacking energy.\n\n6. **Vision Problems**: May experience blurred vision or black spots.\n
It is important to note that many people with hypertension may have no obvious symptoms in the early stages, which is known as the 'silent killer.' Regular blood pressure measurement is key to early detection and control.",
  "sources": [
    {
      "document_id": "doc_1704110400_abc123",
      "document_title": "Cardiology Treatment Guidelines",
      "chunk_id": "chunk_789",
      "content": "Common symptoms in patients with hypertension include headache, dizziness, palpitations...",
      "page_number": 45,
      "relevance_score": 0.92,
      "chunk_index": 67
    },
    {
      "document_id": "doc_1704110400_def456",
      "document_title": "Hypertension Prevention Handbook",
      "chunk_id": "chunk_456",
      "content": "Early symptoms of hypertension are not obvious and require regular monitoring...",
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
      "detected_language": "en",
      "query_type": "symptom_inquiry",
      "medical_entities": ["hypertension", "symptoms"],
      "query_complexity": "simple"
    }
  },
  "suggestions": [
    "Would you also like to know about treatment methods for hypertension?",
    "Need to know about preventive measures for hypertension?",
    "Want to know the diagnostic criteria for hypertension?"
  ],
  "timestamp": "2024-01-01T12:05:00Z"
}
```

### Streaming Q&A

**Endpoint**: `POST /chat/stream`

**Description**: Intelligent Q&A with streaming response, returning generated content in real-time.

**Request Body**: Same as Standard Q&A.

**Response Format**: Server-Sent Events (SSE)

**Event Types**:
- `start`: Generation started.
- `chunk`: A piece of the content.
- `sources`: Reference sources.
- `metadata`: Metadata information.
- `suggestion`: Related suggestions.
- `end`: Generation finished.
- `error`: Error information.

**Response Example**:
```
data: {"type": "start", "query_id": "query_123", "session_id": "session_456"}

data: {"type": "chunk", "content": "The main symptoms of hypertension include:"}

data: {"type": "chunk", "content": "\n\n1. **Headaches**: especially in the back of the head"}

data: {"type": "chunk", "content": " and temples."}

data: {"type": "sources", "sources": [{"document_id": "doc_123", "relevance_score": 0.92}]}

data: {"type": "metadata", "confidence_score": 0.91, "tokens_used": 1530}

data: {"type": "suggestion", "suggestions": ["Would you also like to know about treatment methods for hypertension?"]}

data: {"type": "end", "query_id": "query_123", "total_time": 2.34}
```

**cURL Example**:
```bash
curl -X POST "http://localhost:8001/api/v1/chat/stream" \
     -H "accept: text/event-stream" \
     -H "Content-Type: application/json" \
     -d '{
       "query": "What are the treatment methods for diabetes?",
       "session_id": "session_456"
     }'
```

## Session Management Endpoints

### Create Session

**Endpoint**: `POST /chat/sessions`

**Description**: Creates a new chat session.

**Request Body**:
```json
{
  "title": "Session Title (optional)",
  "metadata": {
    "user_id": "User ID",
    "department": "Department",
    "tags": ["Tag1", "Tag2"]
  }
}
```

**Response Example**:
```json
{
  "session_id": "session_1704110400_abc123",
  "title": "Cardiovascular Disease Consultation",
  "created_time": "2024-01-01T12:00:00Z",
  "status": "active",
  "metadata": {
    "user_id": "user_123",
    "department": "cardiology"
  }
}
```

### Get Session List

**Endpoint**: `GET /chat/sessions`

**Description**: Retrieves a list of chat sessions.

**Request Parameters**:
- `page`: Page number.
- `size`: Items per page.
- `status`: Filter by session status.
- `user_id`: Filter by user ID.

**Response Example**:
```json
{
  "sessions": [
    {
      "session_id": "session_123",
      "title": "Cardiovascular Disease Consultation",
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

### Get Session Details

**Endpoint**: `GET /chat/sessions/{session_id}`

**Description**: Retrieves detailed information and message history for a specific session.

**Request Parameters**:
- `include_messages`: Whether to include message history, default is true.
- `message_limit`: Limit on the number of messages, default is 50.

**Response Example**:
```json
{
  "session_id": "session_123",
  "title": "Cardiovascular Disease Consultation",
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
      "content": "What are the symptoms of hypertension?",
      "timestamp": "2024-01-01T12:05:00Z"
    },
    {
      "message_id": "msg_124",
      "type": "assistant",
      "content": "The main symptoms of hypertension include...",
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

### Delete Session

**Endpoint**: `DELETE /chat/sessions/{session_id}`

**Description**: Deletes a specific session and all its messages.

**Response Example**:
```json
{
  "message": "Session deleted successfully",
  "session_id": "session_123",
  "deleted_messages": 8
}
```

## Error Handling

### Error Codes

| Error Code             | HTTP Status | Description                   |
|------------------------|-------------|-------------------------------|
| `INVALID_REQUEST`      | 400         | Invalid request parameters.   |
| `UNAUTHORIZED`         | 401         | Unauthorized access.          |
| `FORBIDDEN`            | 403         | Forbidden access.             |
| `NOT_FOUND`            | 404         | Resource not found.           |
| `METHOD_NOT_ALLOWED`   | 405         | Request method not allowed.   |
| `REQUEST_TIMEOUT`      | 408         | Request timeout.              |
| `PAYLOAD_TOO_LARGE`    | 413         | Request body too large.       |
| `UNSUPPORTED_MEDIA_TYPE` | 415         | Unsupported media type.       |
| `RATE_LIMIT_EXCEEDED`  | 429         | Rate limit exceeded.          |
| `INTERNAL_SERVER_ERROR`| 500         | Internal server error.        |
| `SERVICE_UNAVAILABLE`  | 503         | Service unavailable.          |

### Detailed Error Information

```json
{
  "success": false,
  "error": {
    "code": "INVALID_REQUEST",
    "message": "Request parameter validation failed",
    "details": {
      "field": "query",
      "issue": "Query content cannot be empty",
      "received": "",
      "expected": "non-empty string"
    },
    "request_id": "req_1704110400_xyz789"
  },
  "timestamp": "2024-01-01T12:00:00Z"
}
```

## Rate Limiting

### Limit Rules

| Endpoint Type      | Limit     | Time Window | 
|--------------------|-----------|-------------|
| Document Upload    | 10 times  | 1 hour      |
| Standard Q&A       | 100 times | 1 hour      |
| Streaming Q&A      | 50 times  | 1 hour      |
| Other Endpoints    | 1000 times| 1 hour      |

### Limit Response Headers

```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1704114000
X-RateLimit-Window: 3600
```

## SDK and Examples

### Python SDK Example

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

# Example Usage
client = MedicalRAGClient()

# Upload document
result = client.upload_document(
    "medical_document.pdf",
    metadata={"category": "cardiology", "language": "en"}
)
print(f"Document uploaded: {result['document_id']}")

# Standard query
response = client.query("What are the symptoms of hypertension?")
print(f"Answer: {response['answer']}")

# Streaming query
for chunk in client.stream_query("What are the treatments for diabetes?"):
    if chunk['type'] == 'chunk':
        print(chunk['content'], end='', flush=True)
```

### JavaScript SDK Example

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

// Example Usage
const client = new MedicalRAGClient();

// Upload document
const fileInput = document.getElementById('file-input');
const file = fileInput.files[0];
const result = await client.uploadDocument(file, {
    category: 'cardiology',
    language: 'en'
});
console.log('Document uploaded:', result.document_id);

// Standard query
const response = await client.query('What are the symptoms of hypertension?');
console.log('Answer:', response.answer);

// Streaming query
for await (const chunk of client.streamQuery('What are the treatments for diabetes?')) {
    if (chunk.type === 'chunk') {
        console.log(chunk.content);
    }
}
```

## Version History

### v1.0.0 (Current Version)
- Basic document management features
- Intelligent Q&A and streaming responses
- Session management
- Hybrid retrieval and RRF fusion
- Complete error handling and monitoring

### Planned Features
- User authentication and permission management
- Multi-tenancy support
- Advanced analytics and reporting
- Bulk operation endpoints
- WebSocket real-time communication

## Technical Support

If you have issues using the API, please refer to:
- [Installation and Configuration Guide](installation.md)
- [Usage Guide](usage.md)
- [Architecture Guide](architecture.md)
- [Troubleshooting Guide](troubleshooting.md)
