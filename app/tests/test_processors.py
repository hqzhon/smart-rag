"""文档处理器测试"""

import pytest
import tempfile
import os
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

from app.processors.document_processor import DocumentProcessor
from app.processors.pdf_processor import PDFProcessor
from app.processors.enhanced_pdf_processor import EnhancedPDFProcessor
from app.processors.cleaners import TextCleaner
from app.processors.quality_filter import TextQualityFilter as QualityFilter
from app.processors.medical_terminology import MedicalTerminologyStandardizer as MedicalTerminologyProcessor
from app.models.document_models import Document


class TestDocumentProcessor:
    """文档处理器测试类"""
    
    @pytest.fixture
    def document_processor(self, tmp_path):
        """创建文档处理器实例"""
        input_dir = tmp_path / "input"
        output_dir = tmp_path / "output"
        input_dir.mkdir()
        output_dir.mkdir()
        mock_vector_store = Mock()
        return DocumentProcessor(
            input_dir=str(input_dir),
            output_dir=str(output_dir),
            vector_store=mock_vector_store
        )
    
    @pytest.fixture
    def sample_document(self):
        """创建示例文档"""
        return Document(
            id="test-doc-1",
            title="测试文档",
            content="这是一个测试文档的内容。包含医疗相关信息。",
            file_path="/tmp/test.pdf",
            file_type="pdf",
            file_size=1024,
            metadata={"source": "test"}
        )
    
    def test_processor_initialization(self, document_processor):
        """测试处理器初始化"""
        assert document_processor is not None
        assert hasattr(document_processor, 'process_document')
    
    @pytest.mark.asyncio
    async def test_process_document_success(self, document_processor, sample_document):
        """测试文档处理成功"""
        with patch.object(document_processor, '_extract_text') as mock_extract:
            mock_extract.return_value = "提取的文本内容"
            
            result = await document_processor.process_document(sample_document)
            
            assert result is not None
            assert result.success is True
            mock_extract.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_process_document_failure(self, document_processor, sample_document):
        """测试文档处理失败"""
        with patch.object(document_processor, '_extract_text') as mock_extract:
            mock_extract.side_effect = Exception("处理失败")
            
            result = await document_processor.process_document(sample_document)
            
            assert result is not None
            assert result.success is False
            assert "处理失败" in result.error_message


class TestPDFProcessor:
    """PDF处理器测试类"""
    
    @pytest.fixture
    def pdf_processor(self):
        """创建PDF处理器实例"""
        # The actual path will be provided by each test, this is just for initialization
        return PDFProcessor(pdf_path="/tmp/dummy.pdf")
    
    def test_processor_initialization(self, pdf_processor):
        """测试PDF处理器初始化"""
        assert pdf_processor is not None
        assert hasattr(pdf_processor, 'extract_text')
    
    def test_extract_text_from_valid_pdf(self, pdf_processor):
        """测试从有效PDF提取文本"""
        # 创建临时PDF文件
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp_file:
            # 写入简单的PDF内容
            tmp_file.write(b"%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n/Pages 2 0 R\n>>\nendobj\n")
            tmp_file.flush()
            
            try:
                with patch('PyPDF2.PdfReader') as mock_reader:
                    mock_page = Mock()
                    mock_page.extract_text.return_value = "测试PDF内容"
                    mock_reader.return_value.pages = [mock_page]
                    
                    text = pdf_processor.extract_text(tmp_file.name)
                    assert text == "测试PDF内容"
            finally:
                os.unlink(tmp_file.name)
    
    def test_extract_text_from_invalid_file(self, pdf_processor):
        """测试从无效文件提取文本"""
        with pytest.raises(Exception):
            pdf_processor.extract_text("/nonexistent/file.pdf")


class TestTextCleaner:
    """文本清理器测试类"""
    
    @pytest.fixture
    def text_cleaner(self):
        """创建文本清理器实例"""
        return TextCleaner()
    
    def test_clean_text_basic(self, text_cleaner):
        """测试基本文本清理"""
        dirty_text = "  这是一个\n\n包含多余空格和换行的\t\t文本  \n"
        clean_text = text_cleaner.clean_comprehensive(dirty_text)
        
        assert clean_text == "这是一个 包含多余空格和换行的 文本"
    
    def test_clean_text_empty(self, text_cleaner):
        """测试空文本清理"""
        assert text_cleaner.clean_comprehensive("") == ""
        assert text_cleaner.clean_comprehensive("   ") == ""
        assert text_cleaner.clean_comprehensive("\n\t\r") == ""
    
    def test_clean_text_special_characters(self, text_cleaner):
        """测试特殊字符清理"""
        text_with_special = "文本包含特殊字符：@#$%^&*()_+{}|:<>?[]"
        cleaned = text_cleaner.clean_comprehensive(text_with_special)
        
        # 应该保留中文和基本标点，移除特殊符号
        assert "文本包含特殊字符" in cleaned



class TestQualityFilter:
    """质量过滤器测试类"""
    
    @pytest.fixture
    def quality_filter(self):
        """创建质量过滤器实例"""
        return QualityFilter()
    
    def test_filter_high_quality_text(self, quality_filter):
        """测试高质量文本过滤"""
        high_quality_text = "这是一段高质量的医疗文档内容，包含了详细的病症描述和治疗方案。内容结构清晰，信息完整。"
        
        filtered_chunks, _ = quality_filter.filter_text_chunks([high_quality_text])
        assert len(filtered_chunks) == 1
        assert filtered_chunks[0] == high_quality_text
    
    def test_filter_low_quality_text(self, quality_filter):
        """测试低质量文本过滤"""
        low_quality_text = "abc 123 !@# 短文本"
        
        filtered_chunks, _ = quality_filter.filter_text_chunks([low_quality_text])
        assert len(filtered_chunks) == 0
    
    def test_filter_empty_text(self, quality_filter):
        """测试空文本过滤"""
        filtered_chunks, _ = quality_filter.filter_text_chunks([""])
        assert len(filtered_chunks) == 0


class TestMedicalTerminologyProcessor:
    """医疗术语处理器测试类"""
    
    @pytest.fixture
    def medical_processor(self):
        """创建医疗术语处理器实例"""
        return MedicalTerminologyProcessor()
    
    def test_extract_medical_terms(self, medical_processor):
        """测试医疗术语提取"""
        medical_text = "患者出现高血压、糖尿病症状，需要进行心电图检查和血糖监测。"
        
        # The new method returns a dictionary of entities
        entities = medical_processor.extract_medical_entities(medical_text)
        
        assert "高血压" in entities["diseases"]
        assert "糖尿病" in entities["diseases"]
        # This tests against the default dictionary in the class
    
    def test_normalize_medical_terms(self, medical_processor):
        """测试医疗术语标准化"""
        text = "患者有高血压病史，并且是T2DM患者。"
        
        # The new method standardizes text directly
        normalized_text = medical_processor.standardize_text(text)
        
        assert "高血压" in normalized_text
        assert "2型糖尿病" in normalized_text
        assert "高血压病" not in normalized_text
    
    def test_process_empty_text(self, medical_processor):
        """测试空文本处理"""
        entities = medical_processor.extract_medical_entities("")
        assert not any(entities.values()) # Check if all entity lists are empty
        
        normalized = medical_processor.standardize_text("")
        assert normalized == ""


class TestEnhancedPDFProcessor:
    """增强PDF处理器测试类"""
    
    @pytest.fixture
    def enhanced_processor(self):
        """创建增强PDF处理器实例"""
        return EnhancedPDFProcessor(pdf_path="/tmp/dummy.pdf")
    
    def test_processor_initialization(self, enhanced_processor):
        """测试增强处理器初始化"""
        assert enhanced_processor is not None
        assert hasattr(enhanced_processor, 'extract_with_layout')
    
    @pytest.mark.asyncio
    async def test_extract_with_layout(self, enhanced_processor):
        """测试带布局的文本提取"""
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp_file:
            tmp_file.write(b"%PDF-1.4\ntest content")
            tmp_file.flush()
            
            try:
                with patch.object(enhanced_processor, '_extract_structured_content') as mock_extract:
                    mock_extract.return_value = {
                        'text': '提取的文本',
                        'tables': [],
                        'images': [],
                        'metadata': {}
                    }
                    
                    result = await enhanced_processor.extract_with_layout(tmp_file.name)
                    
                    assert result is not None
                    assert 'text' in result
                    assert 'tables' in result
                    assert 'images' in result
            finally:
                os.unlink(tmp_file.name)
    
    def test_extract_tables(self, enhanced_processor):
        """测试表格提取"""
        with patch.object(enhanced_processor, '_detect_tables') as mock_detect:
            mock_detect.return_value = [
                {'data': [['列1', '列2'], ['值1', '值2']], 'position': (0, 0, 100, 50)}
            ]
            
            tables = enhanced_processor.extract_tables("dummy_path")
            
            assert len(tables) == 1
            assert tables[0]['data'][0] == ['列1', '列2']
            assert tables[0]['data'][1] == ['值1', '值2']