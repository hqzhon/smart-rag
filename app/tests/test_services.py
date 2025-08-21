"""服务模块测试

Refactored to use fixtures from conftest.py
"""

import pytest
from unittest.mock import Mock, AsyncMock
from fastapi import UploadFile

from app.services.document_service import DocumentService
from app.services.chat_service import ChatService
from app.services.search_service import SearchService
from app.models.query_models import QueryRequest

# --- TestDocumentService ---

@pytest.fixture
def document_service(mock_document_processor):
    """Creates a DocumentService instance with mocked dependencies."""
    # Assume DocumentService takes a processor in its __init__
    # We create a mock for the db_manager dependency
    mock_db_manager = AsyncMock()
    return DocumentService(processor=mock_document_processor, db_manager=mock_db_manager)

class TestDocumentService:
    """文档服务测试类"""

    def test_document_service_initialization(self, document_service):
        """测试文档服务初始化"""
        assert document_service is not None
        assert hasattr(document_service, 'upload_document')

    @pytest.mark.asyncio
    async def test_upload_document_success(self, document_service):
        """测试文档上传成功"""
        mock_file = Mock(spec=UploadFile)
        mock_file.filename = "test.pdf"
        mock_file.read = AsyncMock(return_value=b"PDF content")

        # Mock the return value of the processor
        document_service.processor.process_single_document.return_value = {
            "document_id": "new-doc-id",
            "file_name": "test.pdf"
        }

        result = await document_service.upload_document(mock_file)
        assert result is not None
        assert result["document_id"] == "new-doc-id"

    """服务模块测试

Refactored to use fixtures from conftest.py
"""

import pytest
from unittest.mock import Mock, AsyncMock
from fastapi import UploadFile

from app.services.document_service import DocumentService
from app.services.chat_service import ChatService
from app.services.search_service import SearchService
from app.models.query_models import QueryRequest

# --- TestDocumentService ---

@pytest.fixture
def document_service(mock_document_processor):
    """Creates a DocumentService instance with mocked dependencies."""
    mock_db_manager = AsyncMock()
    return DocumentService(processor=mock_document_processor, db_manager=mock_db_manager)

class TestDocumentService:
    """文档服务测试类"""

    def test_document_service_initialization(self, document_service):
        """测试文档服务初始化"""
        assert document_service is not None
        assert hasattr(document_service, 'upload_document')

    @pytest.mark.asyncio
    async def test_upload_document_success(self, document_service):
        """测试文档上传成功"""
        mock_file = Mock(spec=UploadFile)
        mock_file.filename = "test.pdf"
        mock_file.read = AsyncMock(return_value=b"PDF content")

        document_service.processor.process_single_document.return_value = {
            "document_id": "new-doc-id",
            "file_name": "test.pdf"
        }

        result = await document_service.upload_document(mock_file)
        assert result is not None
        assert result["document_id"] == "new-doc-id"

    @pytest.mark.asyncio
    async def test_upload_document_invalid_type(self, document_service):
        """测试上传无效文件类型"""
        mock_file = Mock(spec=UploadFile)
        mock_file.filename = "test.exe"
        mock_file.content_type = "application/x-executable"

        with pytest.raises(ValueError, match="Unsupported file type"):
            await document_service.upload_document(mock_file)

# --- TestChatService ---

@pytest.fixture
def chat_service(mock_rag_workflow):
    """Creates a ChatService instance with mocked dependencies."""
    mock_db_manager = AsyncMock()
    return ChatService(rag_workflow=mock_rag_workflow, db_manager=mock_db_manager)

class TestChatService:
    """聊天服务测试类"""

    def test_chat_service_initialization(self, chat_service):
        """测试聊天服务初始化"""
        assert chat_service is not None
        assert hasattr(chat_service, 'process_query')

    @pytest.mark.asyncio
    async def test_process_query_success(self, chat_service):
        """测试查询处理成功"""
        request = QueryRequest(query="什么是高血压？", session_id="test-session")
        
        result = await chat_service.process_query(request)
        
        assert result is not None
        assert result["query"] == "test query"
        assert result["response"] == "test response"

# --- TestSearchService ---

@pytest.fixture
def search_service(mock_retriever):
    """Creates a SearchService instance with mocked dependencies."""
    return SearchService(retriever=mock_retriever)

class TestSearchService:
    """搜索服务测试类"""

    def test_search_service_initialization(self, search_service):
        """测试搜索服务初始化"""
        assert search_service is not None
        assert hasattr(search_service, 'search_documents')

    @pytest.mark.asyncio
    async def test_search_documents_success(self, search_service):
        """测试文档搜索成功"""
        result = await search_service.search_documents("高血压")
        
        assert len(result) == 1
        assert result[0]['id'] == 'doc1'

    @pytest.mark.asyncio
    async def test_search_documents_empty_query(self, search_service):
        """测试空查询搜索"""
        with pytest.raises(ValueError, match="搜索查询不能为空"):
            await search_service.search_documents("")

# --- TestChatService ---

@pytest.fixture
def chat_service(mock_rag_workflow):
    """Creates a ChatService instance with mocked dependencies."""
    mock_db_manager = AsyncMock()
    # Assume ChatService takes the workflow in its __init__
    return ChatService(rag_workflow=mock_rag_workflow, db_manager=mock_db_manager)

class TestChatService:
    """聊天服务测试类"""

    def test_chat_service_initialization(self, chat_service):
        """测试聊天服务初始化"""
        assert chat_service is not None
        assert hasattr(chat_service, 'process_query')

    @pytest.mark.asyncio
    async def test_process_query_success(self, chat_service):
        """测试查询处理成功"""
        request = QueryRequest(query="什么是高血压？", session_id="test-session")
        
        # The mock_rag_workflow from conftest already has a mocked process_query
        result = await chat_service.process_query(request)
        
        assert result is not None
        assert result["query"] == "test query"
        assert result["response"] == "test response"

# --- TestSearchService ---

@pytest.fixture
def search_service(mock_retriever):
    """Creates a SearchService instance with mocked dependencies."""
    # Assume SearchService takes a retriever in its __init__
    return SearchService(retriever=mock_retriever)

class TestSearchService:
    """搜索服务测试类"""

    def test_search_service_initialization(self, search_service):
        """测试搜索服务初始化"""
        assert search_service is not None
        assert hasattr(search_service, 'search_documents')

    @pytest.mark.asyncio
    async def test_search_documents_success(self, search_service):
        """测试文档搜索成功"""
        # The mock_retriever from conftest already has a mocked retrieve method
        result = await search_service.search_documents("高血压")
        
        assert len(result) == 1
        assert result[0]['id'] == 'doc1'

    @pytest.mark.asyncio
    async def test_search_documents_empty_query(self, search_service):
        """测试空查询搜索"""
        with pytest.raises(ValueError, match="搜索查询不能为空"):
            await search_service.search_documents("")
