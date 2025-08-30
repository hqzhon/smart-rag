"""Core module tests"""

import os
import tempfile
import time
from unittest.mock import Mock, patch, MagicMock
import pytest
from pydantic import ValidationError

from app.core.config import Settings, get_settings, reload_settings
from app.core.session_manager import SessionManager


class TestSettings:
    """Test Settings configuration class"""
    
    def test_settings_initialization(self):
        """Test Settings class initialization with default values"""
        with patch.dict(os.environ, {
            'APP_NAME': 'test_app',
            'APP_VERSION': '1.0.0',
            'DEBUG': 'true',
            'LOG_LEVEL': 'INFO'
        }):
            settings = Settings()
            assert settings.app_name == 'test_app'
            assert settings.app_version == '1.0.0'
            assert settings.debug is True
            assert settings.log_level == 'INFO'
    
    def test_settings_with_custom_values(self):
        """Test Settings with custom environment variables"""
        env_vars = {
            'APP_NAME': 'custom_app',
            'API_HOST': 'localhost',
            'API_PORT': '8080',
            'DEEPSEEK_API_KEY': 'test_key',
            'QIANWEN_API_KEY': 'qianwen_key',
            'DATABASE_URL': 'sqlite:///test.db',
            'REDIS_URL': 'redis://localhost:6379',
            'CHROMA_PERSIST_DIRECTORY': '/tmp/chroma',
            'MAX_FILE_SIZE': '10485760',
            'ALLOWED_EXTENSIONS': '.pdf,.txt,.docx',
            'SECRET_KEY': 'test_secret',
            'RETRIEVAL_TOP_K': '10',
            'CHUNK_SIZE': '1000',
            'TEMPERATURE': '0.7'
        }
        
        with patch.dict(os.environ, env_vars):
            settings = Settings()
            assert settings.app_name == 'custom_app'
            assert settings.api_host == 'localhost'
            assert settings.api_port == 8080
            assert settings.deepseek_api_key == 'test_key'
            assert settings.qianwen_api_key == 'qianwen_key'
            assert settings.database_url == 'sqlite:///test.db'
            assert settings.redis_url == 'redis://localhost:6379'
            assert settings.chroma_persist_directory == '/tmp/chroma'
            assert settings.max_file_size == 10485760
            assert settings.allowed_extensions == '.pdf,.txt,.docx'
            assert settings.secret_key == 'test_secret'
            assert settings.retrieval_top_k == 10
            assert settings.chunk_size == 1000
            assert settings.temperature == 0.7
    
    def test_allowed_extensions_list_property(self):
        """Test allowed_extensions_list property"""
        with patch.dict(os.environ, {'ALLOWED_EXTENSIONS': '.pdf,.txt,.docx'}):
            settings = Settings()
            extensions = settings.allowed_extensions_list
            assert extensions == ['.pdf', '.txt', '.docx']
    
    def test_chunking_separators_list_property(self):
        """Test chunking_separators_list property"""
        with patch.dict(os.environ, {'CHUNKING_SEPARATORS': '\n##SECTION_START_,\n\n,。\n,.\n\n'}):
            settings = Settings()
            separators = settings.chunking_separators_list
            assert separators == ['\n##SECTION_START_', '\n\n', '。\n', '.\n\n']
    
    def test_settings_validation_error(self):
        """Test Settings validation with invalid values"""
        with patch.dict(os.environ, {'API_PORT': 'invalid_port'}):
            with pytest.raises(ValidationError):
                Settings()
    
    def test_get_settings_singleton(self):
        """Test get_settings returns singleton instance"""
        settings1 = get_settings()
        settings2 = get_settings()
        assert settings1 is settings2
    
    @patch('app.core.config._settings', None)
    def test_reload_settings(self):
        """Test reload_settings function"""
        with patch.dict(os.environ, {'APP_NAME': 'reloaded_app'}):
            reload_settings()
            settings = get_settings()
            assert settings.app_name == 'reloaded_app'
    
    def test_optional_fields(self):
        """Test optional configuration fields"""
        with patch.dict(os.environ, {
            'DEEPSEEK_API_KEY': '',
            'OPENAI_API_KEY': 'openai_key',
            'OPENAI_MODEL': 'gpt-4',
            'OPENAI_BASE_URL': 'https://api.openai.com'
        }):
            settings = Settings()
            assert settings.deepseek_api_key == ''
            assert settings.openai_api_key == 'openai_key'
            assert settings.openai_model == 'gpt-4'
            assert settings.openai_base_url == 'https://api.openai.com'


class TestSessionManager:
    """Test SessionManager class"""
    
    def setup_method(self):
        """Setup test method"""
        self.session_manager = SessionManager()
    
    def test_session_manager_initialization(self):
        """Test SessionManager initialization"""
        assert self.session_manager.sessions == {}
        assert self.session_manager.cleanup_interval == 300
        assert isinstance(self.session_manager.last_cleanup, float)
    
    @patch('app.core.session_manager.get_embeddings')
    @patch('app.core.session_manager.VectorStore')
    @patch('app.core.session_manager.create_advanced_fusion_retriever')
    @patch('app.core.session_manager.create_enhanced_reranker')
    @patch('app.core.session_manager.QueryTransformer')
    @patch('app.core.session_manager.EnhancedRAGWorkflow')
    def test_create_session_success(self, mock_workflow, mock_transformer, 
                                   mock_create_reranker, mock_create_retriever, 
                                   mock_vector_store, mock_embeddings):
        """Test successful session creation"""
        # Mock dependencies
        mock_embedding_model = Mock()
        mock_embeddings.return_value = mock_embedding_model
        
        mock_vector_store_instance = Mock()
        mock_vector_store.return_value = mock_vector_store_instance
        
        mock_retriever_instance = Mock()
        mock_retriever.return_value = mock_retriever_instance
        
        mock_reranker_instance = Mock()
        mock_reranker.return_value = mock_reranker_instance
        
        mock_transformer_instance = Mock()
        mock_transformer.return_value = mock_transformer_instance
        
        mock_workflow_instance = Mock()
        mock_workflow.return_value = mock_workflow_instance
        
        # Test data
        session_id = 'test_session'
        documents = [
            {
                'id': 'doc1',
                'content': 'Test content',
                'title': 'Test Document',
                'file_type': 'pdf',
                'file_path': '/test/doc.pdf',
                'vectorized': True,
                'created_at': '2024-01-01T00:00:00',
                'metadata': {
                    'author': 'Test Author',
                    'pages': 10,
                    'keywords': ['test', 'document']
                }
            }
        ]
        
        # Create session
        result = self.session_manager.create_session(session_id, documents)
        
        # Assertions
        assert result is True
        assert session_id in self.session_manager.sessions
        assert 'workflow' in self.session_manager.sessions[session_id]
        assert 'documents' in self.session_manager.sessions[session_id]
        assert 'created_at' in self.session_manager.sessions[session_id]
        
        # Verify mocks were called
        mock_embeddings.assert_called_once()
        mock_vector_store.assert_called_once_with(mock_embedding_model)
        mock_retriever.assert_called_once()
        mock_reranker.assert_called_once()
        mock_transformer.assert_called_once()
        mock_workflow.assert_called_once()
    
    @patch('app.core.session_manager.get_embeddings')
    def test_create_session_with_exception(self, mock_embeddings):
        """Test session creation with exception"""
        mock_embeddings.side_effect = Exception('Test error')
        
        session_id = 'test_session'
        documents = []
        
        result = self.session_manager.create_session(session_id, documents)
        
        assert result is False
        assert session_id not in self.session_manager.sessions
    
    def test_create_session_with_no_vectorized_documents(self):
        """Test session creation with no vectorized documents"""
        with patch('app.core.session_manager.get_embeddings') as mock_embeddings, \
             patch('app.core.session_manager.VectorStore') as mock_vector_store, \
             patch('app.core.session_manager.HybridRetriever') as mock_retriever, \
             patch('app.core.session_manager.QianwenReranker') as mock_reranker, \
             patch('app.core.session_manager.QueryTransformer') as mock_transformer, \
             patch('app.core.session_manager.EnhancedRAGWorkflow') as mock_workflow:
            
            session_id = 'test_session'
            documents = [
                {
                    'id': 'doc1',
                    'content': 'Test content',
                    'vectorized': False
                }
            ]
            
            result = self.session_manager.create_session(session_id, documents)
            
            assert result is True
            assert session_id in self.session_manager.sessions
    
    def test_get_workflow_existing_session(self):
        """Test getting workflow for existing session"""
        session_id = 'test_session'
        mock_workflow = Mock()
        
        self.session_manager.sessions[session_id] = {
            'workflow': mock_workflow,
            'documents': [],
            'created_at': time.time()
        }
        
        workflow = self.session_manager.get_workflow(session_id)
        assert workflow is mock_workflow
    
    def test_get_workflow_nonexistent_session(self):
        """Test getting workflow for non-existent session"""
        workflow = self.session_manager.get_workflow('nonexistent_session')
        assert workflow is None
    
    def test_cleanup_expired_sessions(self):
        """Test cleanup of expired sessions"""
        current_time = time.time()
        
        # Add sessions with different ages
        self.session_manager.sessions['old_session'] = {
            'workflow': Mock(),
            'documents': [],
            'created_at': current_time - 7200  # 2 hours ago
        }
        
        self.session_manager.sessions['new_session'] = {
            'workflow': Mock(),
            'documents': [],
            'created_at': current_time - 1800  # 30 minutes ago
        }
        
        # Set last cleanup to force cleanup
        self.session_manager.last_cleanup = current_time - 400
        
        # Cleanup with 1 hour max age
        self.session_manager.cleanup_expired_sessions(max_age=3600)
        
        # Old session should be removed, new session should remain
        assert 'old_session' not in self.session_manager.sessions
        assert 'new_session' in self.session_manager.sessions
    
    def test_cleanup_no_cleanup_needed(self):
        """Test cleanup when no cleanup is needed"""
        current_time = time.time()
        
        # Add a session
        self.session_manager.sessions['test_session'] = {
            'workflow': Mock(),
            'documents': [],
            'created_at': current_time
        }
        
        # Set last cleanup to recent time
        self.session_manager.last_cleanup = current_time - 100
        
        initial_count = len(self.session_manager.sessions)
        self.session_manager.cleanup_expired_sessions()
        
        # No sessions should be removed
        assert len(self.session_manager.sessions) == initial_count
    
    def test_get_session_count(self):
        """Test getting session count"""
        assert self.session_manager.get_session_count() == 0
        
        # Add sessions
        self.session_manager.sessions['session1'] = {
            'workflow': Mock(),
            'documents': [],
            'created_at': time.time()
        }
        
        self.session_manager.sessions['session2'] = {
            'workflow': Mock(),
            'documents': [],
            'created_at': time.time()
        }
        
        assert self.session_manager.get_session_count() == 2
    
    def test_document_metadata_processing(self):
        """Test document metadata processing in session creation"""
        with patch('app.core.session_manager.get_embeddings') as mock_embeddings, \
             patch('app.core.session_manager.VectorStore') as mock_vector_store, \
             patch('app.core.session_manager.HybridRetriever') as mock_retriever, \
             patch('app.core.session_manager.QianwenReranker') as mock_reranker, \
             patch('app.core.session_manager.QueryTransformer') as mock_transformer, \
             patch('app.core.session_manager.EnhancedRAGWorkflow') as mock_workflow:
            
            session_id = 'test_session'
            documents = [
                {
                    'id': 'doc1',
                    'content': 'Test content',
                    'title': 'Test Document',
                    'vectorized': True,
                    'metadata': {
                        'author': 'Test Author',
                        'pages': 10,
                        'keywords': ['test', 'document'],  # List should be converted to count
                        'valid_field': 'valid_value'
                    }
                }
            ]
            
            result = self.session_manager.create_session(session_id, documents)
            
            assert result is True
            
            # Check that the retriever was called with properly formatted documents
            call_args = mock_retriever.call_args
            formatted_documents = call_args[0][1]  # Second argument
            
            assert len(formatted_documents) == 1
            doc = formatted_documents[0]
            assert doc['content'] == 'Test content'
            assert doc['metadata']['author'] == 'Test Author'
            assert doc['metadata']['pages'] == 10
            assert doc['metadata']['keywords_count'] == 2  # List converted to count
            assert doc['metadata']['valid_field'] == 'valid_value'