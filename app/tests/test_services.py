"""服务模块测试

使用conftest.py中的模拟组件进行测试
"""

import pytest
import os
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime

from app.services.search_service import SearchService
from app.services.document_service import DocumentService
from app.models.document_models import Document
from app.models.query_models import SearchResult


class TestSearchService:
    """搜索服务测试类"""
    
    @pytest.fixture
    def search_service(self, mock_db_manager, mock_vector_store, mock_retriever):
        """创建搜索服务实例"""
        # 创建服务实例
        service = SearchService()
        
        # 手动注入模拟组件，模拟async_init的效果
        service.db_manager = mock_db_manager
        service.vector_store = mock_vector_store
        service.retriever = mock_retriever
        service.embeddings = Mock()
        service.documents_content = ["文档1内容", "文档2内容"]
        
        # 设置查询转换器模拟
        service.query_transformer = Mock()
        service.query_transformer.extract_medical_entities.return_value = {
            "diseases": ["高血压"],
            "symptoms": ["头痛"]
        }
        
        return service
    
    @pytest.mark.asyncio
    async def test_search_documents(self, search_service, mock_retriever):
        """测试搜索文档功能"""
        # 设置模拟返回值
        mock_retriever.retrieve.return_value = [
            {"page_content": "高血压内容", "metadata": {"source": "doc1.pdf", "score": 0.95}},
            {"page_content": "低血压内容", "metadata": {"source": "doc2.pdf", "score": 0.85}}
        ]
        
        # 执行搜索
        results = await search_service.search_documents("高血压", limit=5)
        
        # 验证结果
        assert len(results) == 2
        assert isinstance(results[0], SearchResult)
        assert results[0].content == "高血压内容"
        assert results[0].score == 0.95
        assert results[0].source == "doc1.pdf"
        
        # 验证调用
        mock_retriever.retrieve.assert_called_once_with("高血压", top_k=5)
    
    @pytest.mark.asyncio
    async def test_search_documents_with_threshold(self, search_service, mock_retriever):
        """测试带阈值的搜索文档功能"""
        # 设置模拟返回值
        mock_retriever.retrieve.return_value = [
            {"page_content": "高血压内容", "metadata": {"source": "doc1.pdf", "score": 0.95}},
            {"page_content": "低血压内容", "metadata": {"source": "doc2.pdf", "score": 0.55}},
            {"page_content": "心脏病内容", "metadata": {"source": "doc3.pdf", "score": 0.45}}
        ]
        
        # 执行搜索，设置阈值为0.6
        results = await search_service.search_documents("高血压", threshold=0.6)
        
        # 验证结果，应该只返回分数高于阈值的结果
        assert len(results) == 1
        assert results[0].content == "高血压内容"
        assert results[0].score == 0.95
    
    @pytest.mark.asyncio
    async def test_search_documents_empty_result(self, search_service, mock_retriever):
        """测试搜索文档无结果的情况"""
        # 设置模拟返回空结果
        mock_retriever.retrieve.return_value = []
        
        # 执行搜索
        results = await search_service.search_documents("不存在的查询")
        
        # 验证结果
        assert len(results) == 0
    
    @pytest.mark.asyncio
    async def test_search_documents_error_handling(self, search_service, mock_retriever):
        """测试搜索文档错误处理"""
        # 设置模拟抛出异常
        mock_retriever.retrieve.side_effect = Exception("检索失败")
        
        # 执行搜索，应该返回空列表而不是抛出异常
        results = await search_service.search_documents("高血压")
        
        # 验证结果
        assert len(results) == 0
    
    @pytest.mark.asyncio
    async def test_analyze_query(self, search_service):
        """测试查询分析功能"""
        # 执行查询分析
        analysis = await search_service.analyze_query("高血压的症状是什么？")
        
        # 验证结果
        assert analysis is not None
        assert analysis.query_type == "symptom"
        assert "高血压" in analysis.entities
        assert "头痛" in analysis.entities
        assert analysis.intent == "question"
        assert analysis.language == "zh"
    
    @pytest.mark.asyncio
    async def test_analyze_query_error_handling(self, search_service):
        """测试查询分析错误处理"""
        # 设置模拟抛出异常
        search_service.query_transformer.extract_medical_entities.side_effect = Exception("分析失败")
        
        # 执行查询分析，应该返回默认分析结果而不是抛出异常
        analysis = await search_service.analyze_query("高血压")
        
        # 验证结果
        assert analysis is not None
        assert analysis.query_type == "unknown"
        assert len(analysis.entities) == 0
    
    @pytest.mark.asyncio
    async def test_get_search_suggestions(self, search_service):
        """测试获取搜索建议功能"""
        # 执行获取搜索建议
        suggestions = await search_service.get_search_suggestions("高血压")
        
        # 验证结果
        assert len(suggestions) > 0
        assert "高血压的症状" in suggestions
    
    @pytest.mark.asyncio
    async def test_get_search_history(self, search_service, mock_db_manager):
        """测试获取搜索历史功能"""
        # 设置模拟返回值
        mock_db_manager.get_search_history.return_value = [
            {"query": "高血压", "timestamp": datetime.now()},
            {"query": "糖尿病", "timestamp": datetime.now()}
        ]
        
        # 执行获取搜索历史
        history = await search_service.get_search_history(user_id="user123")
        
        # 验证结果
        assert len(history) == 2
        assert history[0]["query"] == "高血压"
        
        # 验证调用
        mock_db_manager.get_search_history.assert_called_once_with(session_id="user123", limit=10)


class TestDocumentService:
    """文档服务测试类"""
    
    @pytest.fixture
    def document_service(self, mock_db_manager, mock_vector_store, tmp_dirs):
        """创建文档服务实例"""
        input_dir, output_dir = tmp_dirs
        
        service = DocumentService()
        # 手动注入模拟组件，模拟async_init的效果
        service.db_manager = mock_db_manager
        service.upload_dir = input_dir
        service.processed_dir = output_dir
        
        # 模拟文档处理器
        service.document_processor = Mock()
        service.document_processor.process_single_document.return_value = {
            "document_id": "doc_123",
            "raw_text": "原始文本",
            "cleaned_text": "清理后的文本",
            "standardized_text": "标准化后的文本",
            "title": "测试文档",
            "tables": [],
            "references": [],
            "metadata": {
                "tables": [],
                "references": []
            }
        }
        
        # 模拟文本分割器
        service.text_splitter = Mock()
        service.text_splitter.split_documents.return_value = [
            {"content": "块1", "metadata": {}},
            {"content": "块2", "metadata": {}},
            {"content": "块3", "metadata": {}}
        ]
        
        return service
    
    def test_parse_file_size(self, document_service):
        """测试解析文件大小字符串"""
        assert document_service._parse_file_size("10MB") == 10 * 1024 * 1024
        assert document_service._parse_file_size("500KB") == 500 * 1024
        assert document_service._parse_file_size("2GB") == 2 * 1024 * 1024 * 1024
        assert document_service._parse_file_size("1000") == 1000
    
    @pytest.mark.asyncio
    async def test_upload_document(self, document_service):
        """测试上传文档功能"""
        # 准备测试数据
        file_content = b"%PDF-1.4\ntest content"
        filename = "test.pdf"
        content_type = "application/pdf"
        
        # 执行上传
        with patch('uuid.uuid4', return_value="test-uuid"):
            document = await document_service.upload_document(file_content, filename, content_type)
        
        # 验证结果
        assert document is not None
        assert document.id == "test-uuid"
        assert document.filename == filename
        assert document.content_type == content_type
        assert document.file_size == len(file_content)
        assert document.processed is False
        assert document.processing_status == "uploaded"
        
        # 验证文件是否已保存
        expected_path = os.path.join(document_service.upload_dir, "test-uuid.pdf")
        assert os.path.exists(expected_path)
        
        # 清理测试文件
        os.remove(expected_path)
    
    @pytest.mark.asyncio
    async def test_upload_document_invalid_type(self, document_service):
        """测试上传无效类型文档"""
        # 准备测试数据
        file_content = b"test content"
        filename = "test.txt"
        content_type = "text/plain"
        
        # 执行上传，应该抛出异常
        with pytest.raises(ValueError, match="不支持的文件类型"):
            await document_service.upload_document(file_content, filename, content_type)
    
    @pytest.mark.asyncio
    async def test_upload_document_size_limit(self, document_service):
        """测试上传超过大小限制的文档"""
        # 设置大小限制
        document_service.max_file_size = 10
        
        # 准备测试数据
        file_content = b"%PDF-1.4\ntest content" * 100  # 超过限制
        filename = "test.pdf"
        content_type = "application/pdf"
        
        # 执行上传，应该抛出异常
        with pytest.raises(ValueError, match="文件大小超过限制"):
            await document_service.upload_document(file_content, filename, content_type)
    
    @pytest.mark.asyncio
    async def test_process_document(self, document_service, mock_db_manager):
        """测试处理文档功能"""
        # 准备测试数据
        document = Document(
            id="doc_123",
            filename="test.pdf",
            file_path="/path/to/test.pdf",
            file_size=1000,
            content_type="application/pdf",
            upload_time=datetime.now(),
            processed=False,
            processing_status="uploaded"
        )
        
        # 模拟向量化方法
        with patch.object(document_service, '_vectorize_document_chunks') as mock_vectorize:
            # 执行处理
            result = await document_service.process_document(document)
            
            # 验证结果
            assert result is not None
            assert result.document_id == "doc_123"
            assert result.success is True
            assert result.total_chunks == 3
            assert result.extracted_text_length > 0
            
            # 验证调用
            document_service.document_processor.process_single_document.assert_called_once_with(document.file_path)
            document_service.text_splitter.split_documents.assert_called_once()
            mock_vectorize.assert_called_once()
            mock_db_manager.save_document.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_process_document_error(self, document_service):
        """测试处理文档错误处理"""
        # 准备测试数据
        document = Document(
            id="doc_123",
            filename="test.pdf",
            file_path="/path/to/test.pdf",
            file_size=1000,
            content_type="application/pdf",
            upload_time=datetime.now(),
            processed=False,
            processing_status="uploaded"
        )
        
        # 设置模拟抛出异常
        document_service.document_processor.process_single_document.side_effect = Exception("处理失败")
        
        # 执行处理
        result = await document_service.process_document(document)
        
        # 验证结果
        assert result is not None
        assert result.document_id == "doc_123"
        assert result.success is False
        assert result.error_message == "处理失败"
        assert document.processing_status == "failed"
    
    @pytest.mark.asyncio
    async def test_get_document(self, document_service, mock_db_manager):
        """测试获取文档信息功能"""
        # 设置模拟返回值
        mock_db_manager.get_document.return_value = {
            "id": "doc_123",
            "title": "test.pdf",
            "file_path": "/path/to/test.pdf",
            "file_size": 1000,
            "file_type": "application/pdf",
            "created_at": datetime.now()
        }
        
        # 执行获取文档信息
        document = await document_service.get_document("doc_123")
        
        # 验证结果
        assert document is not None
        assert document.id == "doc_123"
        assert document.filename == "test.pdf"
        assert document.file_path == "/path/to/test.pdf"
        assert document.processed is True
        
        # 验证调用
        mock_db_manager.get_document.assert_called_once_with("doc_123")
    
    @pytest.mark.asyncio
    async def test_get_document_not_found(self, document_service, mock_db_manager):
        """测试获取不存在的文档信息"""
        # 设置模拟返回None
        mock_db_manager.get_document.return_value = None
        
        # 执行获取文档信息
        document = await document_service.get_document("not_exist")
        
        # 验证结果
        assert document is None
    
    @pytest.mark.asyncio
    async def test_list_documents(self, document_service, mock_db_manager):
        """测试获取文档列表功能"""
        # 设置模拟返回值
        mock_db_manager.list_documents.return_value = {
            'documents': [
                {
                    "id": "doc_1",
                    "title": "test1.pdf",
                    "file_path": "/path/to/test1.pdf",
                    "file_size": 1000,
                    "file_type": "application/pdf",
                    "created_at": datetime.now()
                },
                {
                    "id": "doc_2",
                    "title": "test2.pdf",
                    "file_path": "/path/to/test2.pdf",
                    "file_size": 2000,
                    "file_type": "application/pdf",
                    "created_at": datetime.now()
                }
            ],
            'total': 2,
            'page': 1,
            'page_size': 10,
            'total_pages': 1
        }
        
        # 执行获取文档列表
        result = await document_service.list_documents(limit=10)
        
        # 验证结果
        assert 'documents' in result
        assert 'total' in result
        assert len(result['documents']) == 2
        assert result['documents'][0].id == "doc_1"
        assert result['documents'][0].filename == "test1.pdf"
        assert result['documents'][1].id == "doc_2"
        assert result['documents'][1].filename == "test2.pdf"
        assert result['total'] == 2
        
        # 验证调用
        mock_db_manager.list_documents.assert_called_once_with(limit=10, offset=0)
    
    def test_get_supported_formats(self, document_service):
        """测试获取支持的文件格式功能"""
        formats = document_service.get_supported_formats()
        assert "pdf" in formats
    
    def test_get_upload_limits(self, document_service):
        """测试获取上传限制功能"""
        limits = document_service.get_upload_limits()
        assert "max_file_size" in limits
        assert "supported_formats" in limits
        assert "pdf" in limits["supported_formats"]