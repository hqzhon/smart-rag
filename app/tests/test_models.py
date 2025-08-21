"""数据模型单元测试"""

import pytest
from datetime import datetime
from typing import List, Dict, Any
from pydantic import ValidationError

from app.models.document_models import Document, DocumentChunk, ProcessingResult
from app.models.query_models import QueryRequest, QueryResponse, ChatMessage, SearchResult
from app.models.session_models import Session, SessionInfo, SessionStatus, SessionUpdate


class TestDocumentModels:
    """文档模型测试类"""
    
    def test_document_model_creation(self):
        """测试文档模型创建"""
        doc = Document(
            filename="test.pdf",
            file_path="/tmp/test.pdf",
            file_size=1024,
            content_type="application/pdf"
        )
        
        assert doc.filename == "test.pdf"
        assert doc.file_path == "/tmp/test.pdf"
        assert doc.file_size == 1024
        assert doc.content_type == "application/pdf"
        assert doc.processed is False
        assert doc.processing_status == "pending"
        assert doc.vectorized is False
        assert doc.vectorization_status == "pending"
        assert isinstance(doc.upload_time, datetime)
        assert doc.metadata == {}
    
    def test_document_model_with_optional_fields(self):
        """测试带可选字段的文档模型"""
        doc = Document(
            id="doc-123",
            filename="test.pdf",
            file_path="/tmp/test.pdf",
            file_size=1024,
            processed=True,
            processing_status="completed",
            vectorized=True,
            vectorization_status="completed",
            vectorization_time=datetime.now(),
            error_message="No errors",
            metadata={"key": "value"}
        )
        
        assert doc.id == "doc-123"
        assert doc.processed is True
        assert doc.processing_status == "completed"
        assert doc.vectorized is True
        assert doc.vectorization_status == "completed"
        assert doc.vectorization_time is not None
        assert doc.error_message == "No errors"
        assert doc.metadata["key"] == "value"
    
    def test_document_chunk_model(self):
        """测试文档块模型"""
        chunk = DocumentChunk(
            document_id="doc-123",
            chunk_index=0,
            content="This is a test chunk",
            chunk_type="text",
            page_number=1
        )
        
        assert chunk.document_id == "doc-123"
        assert chunk.chunk_index == 0
        assert chunk.content == "This is a test chunk"
        assert chunk.chunk_type == "text"
        assert chunk.page_number == 1
        assert chunk.embedding is None
        assert chunk.metadata == {}
    
    def test_document_chunk_with_embedding(self):
        """测试带嵌入向量的文档块"""
        embedding = [0.1, 0.2, 0.3, 0.4, 0.5]
        chunk = DocumentChunk(
            id="chunk-123",
            document_id="doc-123",
            chunk_index=1,
            content="Test content with embedding",
            embedding=embedding,
            metadata={"source": "page_1"}
        )
        
        assert chunk.id == "chunk-123"
        assert chunk.embedding == embedding
        assert chunk.metadata["source"] == "page_1"
    
    def test_processing_result_model(self):
        """测试处理结果模型"""
        result = ProcessingResult(
            document_id="doc-123",
            success=True,
            total_chunks=10,
            processing_time=5.5,
            extracted_text_length=1000,
            tables_count=2,
            references_count=5,
            images_count=3
        )
        
        assert result.document_id == "doc-123"
        assert result.success is True
        assert result.total_chunks == 10
        assert result.processing_time == 5.5
        assert result.extracted_text_length == 1000
        assert result.tables_count == 2
        assert result.references_count == 5
        assert result.images_count == 3
        assert result.error_message is None
        assert result.metadata == {}
    
    def test_processing_result_with_error(self):
        """测试带错误的处理结果"""
        result = ProcessingResult(
            document_id="doc-123",
            success=False,
            total_chunks=0,
            processing_time=1.0,
            extracted_text_length=0,
            error_message="Processing failed",
            metadata={"error_code": "E001"}
        )
        
        assert result.success is False
        assert result.error_message == "Processing failed"
        assert result.metadata["error_code"] == "E001"


class TestQueryModels:
    """查询模型测试类"""
    
    def test_query_request_model(self):
        """测试查询请求模型"""
        request = QueryRequest(
            query="What is machine learning?",
            session_id="session-123"
        )
        
        assert request.query == "What is machine learning?"
        assert request.session_id == "session-123"
        assert request.stream is False
        assert request.max_tokens == 1000
        assert request.temperature == 0.7
        assert request.metadata == {}
    
    def test_query_request_with_options(self):
        """测试带选项的查询请求"""
        request = QueryRequest(
            query="Explain neural networks",
            session_id="session-456",
            stream=True,
            max_tokens=2000,
            temperature=0.5,
            metadata={"source": "web"}
        )
        
        assert request.stream is True
        assert request.max_tokens == 2000
        assert request.temperature == 0.5
        assert request.metadata["source"] == "web"
    
    def test_query_request_validation(self):
        """测试查询请求验证"""
        # 测试空查询
        with pytest.raises(ValidationError):
            QueryRequest(query="", session_id="session-123")
        
        # 测试空会话ID
        with pytest.raises(ValidationError):
            QueryRequest(query="test", session_id="")
    
    def test_query_response_model(self):
        """测试查询响应模型"""
        response = QueryResponse(
            query="What is AI?",
            response="AI is artificial intelligence",
            session_id="session-123",
            documents=["doc1", "doc2"],
            sources=[{"id": "doc1", "title": "AI Basics"}],
            confidence_score=0.85,
            processing_time=2.5
        )
        
        assert response.query == "What is AI?"
        assert response.response == "AI is artificial intelligence"
        assert response.session_id == "session-123"
        assert len(response.documents) == 2
        assert len(response.sources) == 1
        assert response.confidence_score == 0.85
        assert response.processing_time == 2.5
        assert response.feedback is None
        assert response.metadata == {}
    
    def test_chat_message_model(self):
        """测试聊天消息模型"""
        message = ChatMessage(
            session_id="session-123",
            message_type="user",
            content="Hello, how are you?"
        )
        
        assert message.session_id == "session-123"
        assert message.message_type == "user"
        assert message.content == "Hello, how are you?"
        assert isinstance(message.timestamp, datetime)
        assert message.metadata == {}
    
    def test_chat_message_with_id(self):
        """测试带ID的聊天消息"""
        message = ChatMessage(
            id="msg-123",
            session_id="session-456",
            message_type="assistant",
            content="I'm doing well, thank you!",
            metadata={"model": "gpt-3.5"}
        )
        
        assert message.id == "msg-123"
        assert message.message_type == "assistant"
        assert message.metadata["model"] == "gpt-3.5"
    
    def test_search_result_model(self):
        """测试搜索结果模型"""
        result = SearchResult(
            content="This is relevant content",
            score=0.92,
            source="document1.pdf",
            page=5,
            chunk_type="text"
        )
        
        assert result.content == "This is relevant content"
        assert result.score == 0.92
        assert result.source == "document1.pdf"
        assert result.page == 5
        assert result.chunk_type == "text"
        assert result.metadata == {}
    
    def test_search_result_validation(self):
        """测试搜索结果验证"""
        # 测试无效分数
        with pytest.raises(ValidationError):
            SearchResult(
                content="test",
                score=1.5,  # 超出范围
                source="test.pdf"
            )
        
        with pytest.raises(ValidationError):
            SearchResult(
                content="test",
                score=-0.1,  # 负数
                source="test.pdf"
            )


class TestSessionModels:
    """会话模型测试类"""
    
    def test_session_status_enum(self):
        """测试会话状态枚举"""
        assert SessionStatus.ACTIVE == "active"
        assert SessionStatus.INACTIVE == "inactive"
        assert SessionStatus.EXPIRED == "expired"
        assert SessionStatus.TERMINATED == "terminated"
    
    def test_session_model(self):
        """测试会话模型"""
        session = Session(
            session_id="session-123",
            document_ids=["doc1", "doc2"],
            status=SessionStatus.ACTIVE
        )
        
        assert session.session_id == "session-123"
        assert len(session.document_ids) == 2
        assert session.status == SessionStatus.ACTIVE
        assert isinstance(session.created_at, datetime)
        assert isinstance(session.last_activity, datetime)
        assert session.metadata == {}
    
    def test_session_with_metadata(self):
        """测试带元数据的会话"""
        session = Session(
            session_id="session-456",
            document_ids=[],
            status=SessionStatus.INACTIVE,
            metadata={"user_id": "user123", "source": "web"}
        )
        
        assert session.metadata["user_id"] == "user123"
        assert session.metadata["source"] == "web"
    
    def test_session_info_model(self):
        """测试会话信息模型"""
        now = datetime.now()
        session_info = SessionInfo(
            session_id="session-789",
            document_count=5,
            message_count=10,
            created_at=now,
            last_activity=now,
            status=SessionStatus.ACTIVE,
            processing_status="ready"
        )
        
        assert session_info.session_id == "session-789"
        assert session_info.document_count == 5
        assert session_info.message_count == 10
        assert session_info.created_at == now
        assert session_info.last_activity == now
        assert session_info.status == SessionStatus.ACTIVE
        assert session_info.processing_status == "ready"
    
    def test_session_update_model(self):
        """测试会话更新模型"""
        update = SessionUpdate(
            status=SessionStatus.TERMINATED,
            document_ids=["doc3", "doc4"],
            metadata={"reason": "user_request"}
        )
        
        assert update.status == SessionStatus.TERMINATED
        assert len(update.document_ids) == 2
        assert update.metadata["reason"] == "user_request"
    
    def test_session_update_partial(self):
        """测试部分会话更新"""
        update = SessionUpdate(status=SessionStatus.EXPIRED)
        
        assert update.status == SessionStatus.EXPIRED
        assert update.document_ids is None
        assert update.metadata is None


class TestModelValidation:
    """模型验证测试类"""
    
    def test_document_required_fields(self):
        """测试文档必需字段"""
        with pytest.raises(ValidationError):
            Document()  # 缺少必需字段
        
        with pytest.raises(ValidationError):
            Document(filename="test.pdf")  # 缺少其他必需字段
    
    def test_query_request_constraints(self):
        """测试查询请求约束"""
        # 测试温度范围
        with pytest.raises(ValidationError):
            QueryRequest(
                query="test",
                session_id="session",
                temperature=2.0  # 超出范围
            )
        
        with pytest.raises(ValidationError):
            QueryRequest(
                query="test",
                session_id="session",
                temperature=-0.1  # 负数
            )
    
    def test_confidence_score_validation(self):
        """测试置信度分数验证"""
        # 有效的置信度分数
        response = QueryResponse(
            query="test",
            response="answer",
            session_id="session",
            confidence_score=0.5
        )
        assert response.confidence_score == 0.5
        
        # 无效的置信度分数
        with pytest.raises(ValidationError):
            QueryResponse(
                query="test",
                response="answer",
                session_id="session",
                confidence_score=1.5  # 超出范围
            )


if __name__ == "__main__":
    pytest.main(["-v", __file__])