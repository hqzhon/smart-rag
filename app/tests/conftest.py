
import pytest
from unittest.mock import Mock, AsyncMock
from pathlib import Path
import os

# Import the actual classes to be mocked
from app.processors.document_processor import DocumentProcessor
from app.processors.pdf_processor import PDFProcessor
from app.processors.enhanced_pdf_processor import EnhancedPDFProcessor
from app.retrieval.retriever import HybridRetriever
from app.retrieval.query_transformer import QueryTransformer
from app.retrieval.reranker import QianwenReranker
from app.embeddings.embeddings import QianwenEmbeddings
from app.storage.vector_store import VectorStore
from app.workflow.rag_graph import RAGWorkflow

# --- Path Fixtures ---

@pytest.fixture(scope="session")
def root_path():
    """Provides the project root path."""
    return Path(__file__).parent.parent.parent

@pytest.fixture(scope="session")
def test_pdf_path(root_path):
    """Provides the path to the test PDF document."""
    return root_path / "test_medical_document.pdf"

@pytest.fixture
def tmp_dirs(tmp_path):
    """Creates temporary input and output directories for tests."""
    input_dir = tmp_path / "input"
    output_dir = tmp_path / "output"
    input_dir.mkdir()
    output_dir.mkdir()
    return str(input_dir), str(output_dir)

# --- Mock Service Fixtures ---

@pytest.fixture
def mock_vector_store():
    """Mocks the VectorStore."""
    mock = Mock(spec=VectorStore)
    mock.add_documents = AsyncMock()
    mock.update_document = AsyncMock()
    mock.get_retriever.return_value = AsyncMock()
    return mock

@pytest.fixture
def mock_document_processor(tmp_dirs, mock_vector_store):
    """Mocks the DocumentProcessor."""
    input_dir, output_dir = tmp_dirs
    # We instantiate the real class but with mocked dependencies if needed
    # For this fixture, we mock the entire class behavior for simplicity
    mock = Mock(spec=DocumentProcessor)
    mock.input_dir = input_dir
    mock.output_dir = output_dir
    mock.vector_store = mock_vector_store
    mock.process_single_document = AsyncMock(return_value={"status": "processed"})
    return mock

@pytest.fixture
def mock_pdf_processor(test_pdf_path):
    """Provides a mock PDFProcessor initialized with a valid path."""
    # In tests for this class, you might want the real instance
    # For other tests, a simple mock is enough
    mock = Mock(spec=PDFProcessor)
    mock.pdf_path = test_pdf_path
    mock.extract_text.return_value = "This is sample text from the PDF."
    return mock

@pytest.fixture
def mock_query_transformer():
    """Mocks the QueryTransformer."""
    mock = Mock(spec=QueryTransformer)
    mock.expand_query.return_value = ["test query"]
    mock.rewrite_query.return_value = "rewritten test query"
    mock.extract_medical_entities.return_value = {"diseases": ["hypertension"]}
    return mock

@pytest.fixture
def mock_embedding_model():
    """Mocks the QianwenEmbeddings model."""
    mock = Mock(spec=QianwenEmbeddings)
    mock.embed_query = AsyncMock(return_value=[0.1, 0.2, 0.3, 0.4])
    mock.embed_documents = AsyncMock(return_value=[[0.1, 0.2, 0.3, 0.4]])
    return mock

@pytest.fixture
def mock_retriever(mock_vector_store, mock_query_transformer, mock_embedding_model):
    """Mocks the HybridRetriever."""
    mock = Mock(spec=HybridRetriever)
    mock.vector_store = mock_vector_store
    mock.query_transformer = mock_query_transformer
    mock.embedding_model = mock_embedding_model
    mock.retrieve.return_value = [{"id": "doc1", "content": "dummy content", "metadata": {}}]
    return mock

@pytest.fixture
def mock_reranker():
    """Mocks the QianwenReranker."""
    mock = Mock(spec=QianwenReranker)
    # The reranker should return the same documents it receives, possibly reordered
    mock.rerank_documents.side_effect = lambda query, docs, top_k: docs[:top_k]
    return mock

@pytest.fixture
def mock_rag_workflow(mock_retriever, mock_reranker, mock_query_transformer):
    """Mocks the RAGWorkflow."""
    mock = Mock(spec=RAGWorkflow)
    mock.retriever = mock_retriever
    mock.reranker = mock_reranker
    mock.query_transformer = mock_query_transformer
    mock.process_query = AsyncMock(return_value={
        "query": "test query",
        "response": "test response",
        "documents": []
    })
    return mock
