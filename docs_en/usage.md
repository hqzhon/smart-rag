# Usage Guide

This document provides detailed instructions on how to use the Medical Literature RAG System, including both the web interface and the API.

## Using the Web Interface

### Starting the System

1.  **Start the Backend Service**
    ```bash
    python run.py
    ```
    The backend API will start at http://localhost:8001.

2.  **Start the Frontend Service**
    ```bash
    cd frontend
    npm run dev
    ```
    The frontend interface will start at http://localhost:3001.

### Interface Features

#### 1. Document Management

**Uploading Documents**
- Click the "Upload Document" button.
- Select medical PDF files (supports .pdf, .doc, .docx, .txt formats).
- File size limit: 100MB.
- The system will automatically process the document and create an index.

**Document List**
- View the list of uploaded documents.
- Displays document name, upload time, and processing status.
- Supports deleting unwanted documents.

**Processing Status**
- 🟡 Processing: The document is being parsed and indexed.
- 🟢 Completed: The document is ready for querying.
- 🔴 Failed: The document format is not supported or a processing error occurred.

#### 2. Intelligent Q&A

**How to Ask**
- Enter medical-related questions in the query box.
- Supports queries in both Chinese and English.
- You can ask about symptoms, treatment methods, drug information, etc.

**Query Examples**
```
What are the symptoms of hypertension?
Dietary considerations for diabetic patients
Side effects and contraindications of aspirin
Early diagnostic methods for heart disease
```

**Answer Features**
- Professional answers based on the uploaded documents.
- Provides citations from source documents.
- Supports streaming responses for a real-time generation process.
- Includes a confidence score.

#### 3. Session Management

**Session Features**
- Automatically saves conversation history.
- Supports multi-turn conversation context.
- You can create a new session or continue a previous one.

**Session Actions**
- New Session: Start a brand new conversation.
- Clear History: Clear the current session's records.
- Export Conversation: Save the conversation history to a file.

### Advanced Features

#### 1. Retrieval Settings

**Adjusting Retrieval Parameters**
- Number of Results: Control the number of relevant documents returned (default 10).
- Similarity Threshold: Set the minimum relevance requirement for documents (default 0.7).
- Hybrid Retrieval: Enable a hybrid strategy of vector search + BM25.
- RRF Fusion: Use Reciprocal Rank Fusion to optimize result ranking.

**Query Optimization**
- Query Expansion: Automatically expand query keywords.
- Query Rewriting: Optimize the phrasing of the query.
- Multi-language Support: Supports mixed queries in Chinese and English.

#### 2. Result Analysis

**Relevance Score**
- Each answer includes a confidence score.
- Displays the relevance score of cited documents.
- Provides a detailed analysis of retrieval results.

**Source Tracing**
- Click on a citation to view the original document snippet.
- Displays the document page number and specific location.
- Supports highlighting of relevant content.

## Using the API

### Basic Configuration

**Base API URL**: `http://localhost:8001/api/v1`

**Authentication**: None required in the current version (development environment).

**Request Format**: JSON

**Response Format**: JSON

### Core Endpoints

#### 1. Health Check

**Endpoint**: `GET /health`

**Description**: Checks the system's operational status.

**Request Example**:
```bash
curl -X GET "http://localhost:8001/api/v1/health" \
     -H "accept: application/json"
```

**Response Example**:
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

#### 2. Document Upload

**Endpoint**: `POST /documents/upload`

**Description**: Uploads and processes a medical document.

**Request Parameters**:
- `file`: The document file (multipart/form-data).
- `metadata`: Optional document metadata (JSON string).

**Request Example**:
```bash
curl -X POST "http://localhost:8001/api/v1/documents/upload" \
     -H "accept: application/json" \
     -H "Content-Type: multipart/form-data" \
     -F "file=@medical_document.pdf" \
     -F "metadata={\"category\": \"cardiology\", \"language\": \"en\"}"
```

**Response Example**:
```json
{
  "document_id": "doc_123456",
  "filename": "medical_document.pdf",
  "status": "processing",
  "message": "Document uploaded successfully, now processing.",
  "estimated_time": "2-5 minutes"
}
```

#### 3. Document List

**Endpoint**: `GET /documents`

**Description**: Retrieves a list of uploaded documents.

**Request Parameters**:
- `page`: Page number (default 1).
- `size`: Items per page (default 20).
- `status`: Filter by status (optional).

**Request Example**:
```bash
curl -X GET "http://localhost:8001/api/v1/documents?page=1&size=10" \
     -H "accept: application/json"
```

**Response Example**:
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
        "language": "en"
      }
    }
  ],
  "total": 1,
  "page": 1,
  "size": 10
}
```

#### 4. Intelligent Q&A

**Endpoint**: `POST /chat/query`

**Description**: Performs intelligent Q&A based on the documents.

**Request Body**:
```json
{
  "query": "User query content",
  "session_id": "Session ID (optional)",
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

**Request Example**:
```bash
curl -X POST "http://localhost:8001/api/v1/chat/query" \
     -H "accept: application/json" \
     -H "Content-Type: application/json" \
     -d '{
       "query": "What are the symptoms of hypertension?",
       "session_id": "session_123"
     }'
```

**Response Example**:
```json
{
  "answer": "The main symptoms of hypertension include:\n1. Headaches, especially in the back of the head\n2. Dizziness and vertigo\n3. Palpitations and chest tightness\n4. Fatigue and weakness\n5. Blurred vision\n6. Tinnitus\n\nIt is important to note that many people with hypertension may not have obvious symptoms in the early stages, so regular blood pressure measurement is very important.",
  "sources": [
    {
      "document_id": "doc_123456",
      "chunk_id": "chunk_789",
      "content": "Hypertension symptoms related content...",
      "score": 0.92,
      "page": 15
    }
  ],
  "session_id": "session_123",
  "response_time": 2.3,
  "confidence": 0.89
}
```

#### 5. Streaming Q&A

**Endpoint**: `POST /chat/stream`

**Description**: Intelligent Q&A with streaming responses.

**Request Body**: Same as standard Q&A.

**Request Example**:
```bash
curl -X POST "http://localhost:8001/api/v1/chat/stream" \
     -H "accept: text/event-stream" \
     -H "Content-Type: application/json" \
     -d '{
       "query": "What are the treatment methods for diabetes?",
       "session_id": "session_456"
     }'
```

**Response Format**: Server-Sent Events (SSE)
```
data: {"type": "start", "session_id": "session_456"}

data: {"type": "chunk", "content": "The treatment methods for diabetes mainly include:"}

data: {"type": "chunk", "content": "\n1. Lifestyle intervention"}

data: {"type": "sources", "sources": [...]}

data: {"type": "end", "confidence": 0.91}
```

### Advanced Endpoints

#### 1. Delete Document

**Endpoint**: `DELETE /documents/{document_id}`

**Request Example**:
```bash
curl -X DELETE "http://localhost:8001/api/v1/documents/doc_123456" \
     -H "accept: application/json"
```

#### 2. Session Management

**Get Session History**: `GET /chat/sessions/{session_id}`

**Delete Session**: `DELETE /chat/sessions/{session_id}`

**List Sessions**: `GET /chat/sessions`

#### 3. System Statistics

**Endpoint**: `GET /stats`

**Response Example**:
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

## Best Practices

### 1. Document Preparation

**Document Quality**
- Use clear, high-quality PDF documents.
- Ensure that text can be copied and searched normally.
- Avoid documents that are purely images.

**Document Organization**
- Upload documents classified by medical specialty.
- Use meaningful filenames.
- Add appropriate metadata tags.

### 2. Query Optimization

**Querying Techniques**
- Use specific and clear medical terms.
- Avoid overly broad or vague questions.
- You can include key information such as symptoms, disease names, drug names, etc.

**Multi-turn Conversation**
- Use the session context for in-depth inquiries.
- You can ask for clarification or additional information.
- Supports follow-up questions on related details.

### 3. Result Verification

**Information Verification**
- Check the reliability of the cited sources.
- Compare information from multiple relevant documents.
- Pay attention to the confidence score.

**Professional Judgment**
- The information provided by the system is for reference only.
- Important medical decisions should be made in consultation with a professional doctor.
- Regularly update the document library to get the latest information.

## Troubleshooting

### Common Issues

1.  **Document Upload Fails**
    - Check the file format and size.
    - Confirm a stable network connection.
    - Check the backend logs for error messages.

2.  **Query Returns No Results**
    - Confirm that relevant documents have been uploaded and processed successfully.
    - Try using different keywords.
    - Lower the similarity threshold.

3.  **Slow Response Time**
    - Check system resource usage.
    - Consider reducing the number of retrieved documents.
    - Optimize the query phrasing.

### Performance Monitoring

**Key Metrics**
- Query response time.
- Document processing speed.
- System resource utilization.
- Retrieval accuracy.

**Optimization Recommendations**
- Regularly clean up unused documents.
- Monitor memory and storage usage.
- Adjust configuration parameters based on usage.

## Next Steps

- [API Reference](api.md) - Complete API interface descriptions.
- [Architecture Guide](architecture.md) - Understand the internal structure of the system.
- [Installation and Configuration](installation.md) - System deployment and configuration.
