"""
文档服务测试
"""

import pytest
import asyncio
from unittest.mock import Mock, patch
from app.services.document_service import DocumentService
from app.models.document_models import Document


class TestDocumentService:
    """文档服务测试类"""
    
    @pytest.fixture
    def document_service(self):
        """创建文档服务实例"""
        return DocumentService()
    
    @pytest.fixture
    def sample_pdf_content(self):
        """模拟PDF文件内容"""
        return b"%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n/Pages 2 0 R\n>>\nendobj\n"
    
    def test_parse_file_size(self, document_service):
        """测试文件大小解析"""
        assert document_service._parse_file_size("10MB") == 10 * 1024 * 1024
        assert document_service._parse_file_size("5KB") == 5 * 1024
        assert document_service._parse_file_size("1GB") == 1 * 1024 * 1024 * 1024
        assert document_service._parse_file_size("1024") == 1024
    
    def test_validate_file_success(self, document_service, sample_pdf_content):
        """测试文件验证成功"""
        # 应该不抛出异常
        document_service._validate_file(sample_pdf_content, "test.pdf", "application/pdf")
    
    def test_validate_file_size_limit(self, document_service):
        """测试文件大小限制"""
        large_content = b"x" * (document_service.max_file_size + 1)
        
        with pytest.raises(ValueError, match="文件大小超过限制"):
            document_service._validate_file(large_content, "test.pdf", "application/pdf")
    
    def test_validate_file_type(self, document_service, sample_pdf_content):
        """测试文件类型验证"""
        with pytest.raises(ValueError, match="不支持的文件类型"):
            document_service._validate_file(sample_pdf_content, "test.txt", "text/plain")
    
    def test_validate_file_extension(self, document_service, sample_pdf_content):
        """测试文件扩展名验证"""
        with pytest.raises(ValueError, match="不支持的文件扩展名"):
            document_service._validate_file(sample_pdf_content, "test.txt", "application/pdf")
    
    @pytest.mark.asyncio
    async def test_upload_document_success(self, document_service, sample_pdf_content):
        """测试文档上传成功"""
        document = await document_service.upload_document(
            file_content=sample_pdf_content,
            filename="test.pdf",
            content_type="application/pdf"
        )
        
        assert isinstance(document, Document)
        assert document.filename == "test.pdf"
        assert document.content_type == "application/pdf"
        assert document.file_size == len(sample_pdf_content)
        assert not document.processed
        assert document.processing_status == "uploaded"
    
    @pytest.mark.asyncio
    async def test_upload_document_validation_error(self, document_service):
        """测试文档上传验证错误"""
        with pytest.raises(ValueError):
            await document_service.upload_document(
                file_content=b"invalid content",
                filename="test.txt",
                content_type="text/plain"
            )
    
    def test_get_supported_formats(self, document_service):
        """测试获取支持的格式"""
        formats = document_service.get_supported_formats()
        assert "pdf" in formats
    
    def test_get_upload_limits(self, document_service):
        """测试获取上传限制"""
        limits = document_service.get_upload_limits()
        assert "max_file_size" in limits
        assert "max_file_size_mb" in limits
        assert "supported_formats" in limits