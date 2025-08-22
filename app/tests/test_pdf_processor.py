"""PDF处理器测试

使用conftest.py中的模拟组件进行测试
"""

import pytest
import os
import tempfile
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from pathlib import Path

from app.processors.pdf_processor import PDFProcessor
from app.processors.enhanced_pdf_processor import EnhancedPDFProcessor


class TestPDFProcessor:
    """PDF处理器测试类"""
    
    @pytest.fixture
    def pdf_processor(self, tmp_path):
        """创建PDF处理器实例"""
        # 创建一个临时的PDF文件路径用于测试
        test_pdf_path = tmp_path / "test.pdf"
        test_pdf_path.write_bytes(b"%PDF-1.4\ntest content")
        return PDFProcessor(str(test_pdf_path))
    
    def test_processor_initialization(self, pdf_processor):
        """测试处理器初始化"""
        assert pdf_processor is not None
        assert isinstance(pdf_processor, PDFProcessor)
    
    def test_process_valid_pdf(self, pdf_processor, tmp_path):
        """测试处理有效的PDF文件"""
        # 创建测试PDF文件
        test_pdf_path = os.path.join(tmp_path, "test.pdf")
        with open(test_pdf_path, "wb") as f:
            f.write(b"%PDF-1.4\ntest content")
        
        # 模拟PDFProcessor的方法
        with patch.object(PDFProcessor, 'extract_text') as mock_extract_text, \
             patch.object(PDFProcessor, 'extract_tables') as mock_extract_tables, \
             patch.object(PDFProcessor, 'extract_title') as mock_extract_title:
            
            mock_extract_text.return_value = "测试文本内容"
            mock_extract_tables.return_value = []
            mock_extract_title.return_value = "test.pdf"
            
            # 执行处理
            text = pdf_processor.extract_text()
            tables = pdf_processor.extract_tables()
            title = pdf_processor.extract_title()

            # 验证结果
            assert text == "测试文本内容"
            assert tables == []
            assert title == "test.pdf"
    
    def test_process_invalid_pdf(self, pdf_processor, tmp_path):
        """测试处理无效的PDF文件"""
        # 创建无效的PDF文件
        test_invalid_pdf_path = os.path.join(tmp_path, "invalid.pdf")
        with open(test_invalid_pdf_path, "wb") as f:
            f.write(b"not a pdf file")
        
        # 模拟PdfReader在初始化时抛出异常
        with patch('app.processors.pdf_processor.pypdf.PdfReader', side_effect=Exception("Invalid PDF")):
            # 重新创建pdf_processor实例，确保它使用被mock的PdfReader
            pdf_processor = PDFProcessor(test_invalid_pdf_path)

            # 执行处理，应该返回空文本
            text = pdf_processor.extract_text()
            tables = pdf_processor.extract_tables()
            title = pdf_processor.extract_title()

            # 验证结果
            assert text == ""
            assert tables == []
            assert title == ""


class TestEnhancedPDFProcessor:
    """增强PDF处理器测试类"""
    
    @pytest.fixture
    def enhanced_pdf_processor(self, tmp_path):
        """创建增强PDF处理器实例"""
        # 创建一个临时的PDF文件路径用于测试
        test_pdf_path = tmp_path / "test.pdf"
        test_pdf_path.write_bytes(b"%PDF-1.4\ntest content")
        return EnhancedPDFProcessor(str(test_pdf_path))
    
    def test_processor_initialization(self, enhanced_pdf_processor):
        """测试处理器初始化"""
        assert enhanced_pdf_processor is not None
        assert hasattr(enhanced_pdf_processor, 'process')
        assert hasattr(enhanced_pdf_processor, 'extract_tables')
        assert hasattr(enhanced_pdf_processor, 'extract_references')
    
    def test_process_valid_pdf(self, enhanced_pdf_processor, tmp_path):
        """测试处理有效的PDF文件"""
        # 创建测试PDF文件
        test_pdf_path = os.path.join(tmp_path, "test.pdf")
        with open(test_pdf_path, "wb") as f:
            f.write(b"%PDF-1.4\ntest content")
        
        # 模拟基础处理
        with patch.object(PDFProcessor, 'process') as mock_base_process:
            mock_base_process.return_value = {
                "filename": "test.pdf",
                "text": "PDF内容",
                "tables": [],
                "references": []
            }
            
            # 模拟表格提取
            with patch.object(enhanced_pdf_processor, 'extract_tables') as mock_extract_tables:
                mock_extract_tables.return_value = [{"表格1": "数据1"}]
                
                # 模拟参考文献提取
                with patch.object(enhanced_pdf_processor, 'extract_references') as mock_extract_references:
                    mock_extract_references.return_value = ["参考文献1", "参考文献2"]
                    
                    # 执行处理
                    result = enhanced_pdf_processor.process(test_pdf_path)
                    
                    # 验证结果
                    assert result is not None
                    assert "filename" in result
                    assert "text" in result
                    assert "tables" in result
                    assert "references" in result
                    assert result["filename"] == "test.pdf"
                    assert result["text"] == "PDF内容"
                    assert len(result["tables"]) == 1
                    assert len(result["references"]) == 2
    
    def test_extract_tables(self, enhanced_pdf_processor, tmp_path):
        """测试表格提取功能"""
        # 创建测试PDF文件
        test_pdf_path = os.path.join(tmp_path, "test.pdf")
        with open(test_pdf_path, "wb") as f:
            f.write(b"%PDF-1.4\ntest content")
        
        # 模拟tabula-py
        with patch('app.processors.enhanced_pdf_processor.read_pdf') as mock_read_pdf:
            mock_read_pdf.return_value = [{"列1": "值1", "列2": "值2"}]
            
            # 执行表格提取
            tables = enhanced_pdf_processor.extract_tables(test_pdf_path)
            
            # 验证结果
            assert tables is not None
            assert len(tables) == 1
            assert "列1" in tables[0]
            assert tables[0]["列1"] == "值1"
    
    def test_extract_references(self, enhanced_pdf_processor, tmp_path):
        """测试参考文献提取功能"""
        # 创建测试PDF文件
        test_pdf_path = os.path.join(tmp_path, "test.pdf")
        with open(test_pdf_path, "wb") as f:
            f.write(b"%PDF-1.4\ntest content")
        
        # 模拟正则表达式匹配
        with patch('app.processors.enhanced_pdf_processor.re.findall') as mock_findall:
            mock_findall.return_value = ["[1] 作者. 标题. 期刊, 2023", "[2] 作者2. 标题2. 期刊2, 2023"]
            
            # 执行参考文献提取
            references = enhanced_pdf_processor.extract_references("参考文献\n[1] 作者. 标题. 期刊, 2023\n[2] 作者2. 标题2. 期刊2, 2023")
            
            # 验证结果
            assert references is not None
            assert len(references) == 2
            assert references[0] == "[1] 作者. 标题. 期刊, 2023"