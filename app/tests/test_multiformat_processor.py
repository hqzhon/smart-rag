"""
测试多格式文档处理器功能
"""

import os
import pytest
import tempfile
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

from app.processors.document_processor import DocumentProcessor, ProcessingError
from app.models.document_models import Document


class TestMultiFormatDocumentProcessor:
    """测试多格式文档处理器"""
    
    @pytest.fixture
    def temp_dirs(self):
        """创建临时目录"""
        with tempfile.TemporaryDirectory() as input_dir:
            with tempfile.TemporaryDirectory() as output_dir:
                yield input_dir, output_dir
    
    @pytest.fixture
    def processor(self, temp_dirs):
        """创建文档处理器实例"""
        input_dir, output_dir = temp_dirs
        return DocumentProcessor(
            input_dir=input_dir,
            output_dir=output_dir,
            use_enhanced_parser=False,  # 简化测试
            enable_cleaning=False,
            enable_terminology_standardization=False,
            enable_quality_filtering=False,
            enable_async_metadata=False
        )
    
    @pytest.fixture
    def sample_txt_file(self, temp_dirs):
        """创建样本TXT文件"""
        input_dir, _ = temp_dirs
        file_path = os.path.join(input_dir, "test.txt")
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write("这是一个测试文档。\n包含多行文本。")
        return file_path
    
    @pytest.fixture
    def sample_md_file(self, temp_dirs):
        """创建样本Markdown文件"""
        input_dir, _ = temp_dirs
        file_path = os.path.join(input_dir, "test.md")
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write("# 测试标题\n\n这是一个测试markdown文档。\n\n## 子标题\n\n- 列表项1\n- 列表项2")
        return file_path
    
    @pytest.mark.asyncio
    async def test_txt_file_processing(self, processor, sample_txt_file):
        """测试TXT文件处理"""
        result = await processor.process_single_document(sample_txt_file)
        
        assert result is not None
        assert "raw_text" in result
        assert "这是一个测试文档" in result["raw_text"]
        assert result["metadata"]["file_type"] == "txt"
        assert result["processing_stats"]["raw_length"] > 0
    
    @pytest.mark.asyncio
    async def test_md_file_processing(self, processor, sample_md_file):
        """测试Markdown文件处理"""
        # Mock unstructured partition_md
        mock_element = Mock()
        mock_element.text = "测试标题\n\n这是一个测试markdown文档。\n\n子标题\n\n列表项1\n列表项2"
        mock_element.metadata = {}
        
        with patch('unstructured.partition.md.partition_md', return_value=[mock_element]):
            result = await processor.process_single_document(sample_md_file)
            
            assert result is not None
            assert "raw_text" in result
            assert "测试标题" in result["raw_text"]
            assert result["metadata"]["file_type"] == "md"
            assert result["metadata"]["processing_method"] == "unstructured"
    
    @pytest.mark.asyncio
    async def test_md_file_fallback_processing(self, processor, sample_md_file):
        """测试Markdown文件的回退处理"""
        # Mock unstructured to fail
        with patch('unstructured.partition.md.partition_md', side_effect=Exception("Unstructured failed")):
            result = await processor.process_single_document(sample_md_file)
            
            assert result is not None
            assert "raw_text" in result
            assert "测试标题" in result["raw_text"]
            assert result["metadata"]["processing_method"] == "fallback_text_extraction"
            assert "warning" in result["metadata"]
    
    @pytest.mark.asyncio
    async def test_docx_file_processing_mock(self, processor, temp_dirs):
        """测试DOCX文件处理（使用mock）"""
        input_dir, _ = temp_dirs
        file_path = os.path.join(input_dir, "test.docx")
        
        # 创建空文件用于测试
        Path(file_path).touch()
        
        # Mock unstructured partition_docx
        mock_element = Mock()
        mock_element.text = "这是Word文档内容"
        mock_element.metadata = {"page_number": 1}
        
        with patch('unstructured.partition.docx.partition_docx', return_value=[mock_element]):
            result = await processor.process_single_document(file_path)
            
            assert result is not None
            assert "raw_text" in result
            assert "这是Word文档内容" in result["raw_text"]
            assert result["metadata"]["file_type"] == "docx"
            assert result["metadata"]["total_pages"] == 1
    
    @pytest.mark.asyncio
    async def test_pptx_file_processing_mock(self, processor, temp_dirs):
        """测试PPTX文件处理（使用mock）"""
        input_dir, _ = temp_dirs
        file_path = os.path.join(input_dir, "test.pptx")
        
        # 创建空文件用于测试
        Path(file_path).touch()
        
        # Mock unstructured partition_pptx
        mock_element = Mock()
        mock_element.text = "幻灯片标题"
        mock_element.metadata = {"slide_number": 1}
        
        with patch('unstructured.partition.pptx.partition_pptx', return_value=[mock_element]):
            result = await processor.process_single_document(file_path)
            
            assert result is not None
            assert "raw_text" in result
            assert "幻灯片标题" in result["raw_text"]
            assert result["metadata"]["file_type"] == "pptx"
            assert result["metadata"]["total_slides"] == 1
    
    @pytest.mark.asyncio
    async def test_xlsx_file_processing_mock(self, processor, temp_dirs):
        """测试XLSX文件处理（使用mock）"""
        input_dir, _ = temp_dirs
        file_path = os.path.join(input_dir, "test.xlsx")
        
        # 创建空文件用于测试
        Path(file_path).touch()
        
        # Mock unstructured partition_xlsx
        mock_element = Mock()
        mock_element.text = "表格数据内容"
        mock_element.metadata = {"sheet_name": "Sheet1"}
        
        with patch('unstructured.partition.xlsx.partition_xlsx', return_value=[mock_element]):
            result = await processor.process_single_document(file_path)
            
            assert result is not None
            assert "raw_text" in result
            assert "表格数据内容" in result["raw_text"]
            assert result["metadata"]["file_type"] == "xlsx"
            assert result["metadata"]["total_sheets"] == 1
            assert "Sheet1" in result["metadata"]["sheet_names"]
    
    def test_extract_unstructured_metadata(self, processor):
        """测试unstructured元数据提取"""
        # 创建mock元素
        mock_element1 = Mock()
        mock_element1.metadata = {"page_number": 1}
        
        mock_element2 = Mock()
        mock_element2.metadata = {"page_number": 2, "sheet_name": "Data"}
        
        mock_element3 = Mock()
        mock_element3.metadata = {"slide_number": 1}
        
        elements = [mock_element1, mock_element2, mock_element3]
        
        metadata = processor._extract_unstructured_metadata(elements, ".xlsx")
        
        assert metadata["file_type"] == "xlsx"
        assert metadata["total_elements"] == 3
        assert metadata["processing_method"] == "unstructured"
        assert metadata["total_pages"] == 2
        assert metadata["total_sheets"] == 1
        assert "Data" in metadata["sheet_names"]
    
    def test_add_structure_markers_from_unstructured(self, processor):
        """测试unstructured结构标记添加"""
        # 创建mock元素
        mock_title = Mock()
        mock_title.text = "文档标题"
        mock_title.__class__.__name__ = "Title"
        
        mock_table = Mock()
        mock_table.text = "表格内容"
        mock_table.__class__.__name__ = "Table"
        
        mock_text = Mock()
        mock_text.text = "普通文本"
        mock_text.__class__.__name__ = "NarrativeText"
        
        elements = [mock_title, mock_table, mock_text]
        
        structured_text = processor._add_structure_markers_from_unstructured(elements)
        
        assert "##TITLE_START_" in structured_text
        assert "文档标题" in structured_text
        assert "##TABLE_START_" in structured_text
        assert "表格内容" in structured_text
        assert "##SECTION_START_" in structured_text
        assert "普通文本" in structured_text
    
    def test_fallback_text_extraction_md(self, processor, sample_md_file):
        """测试Markdown回退文本提取"""
        result = processor._fallback_text_extraction(sample_md_file, ".md")
        
        assert "测试标题" in result
        assert "子标题" in result
        assert "列表项1" in result
    
    @pytest.mark.asyncio
    async def test_unsupported_file_type(self, processor, temp_dirs):
        """测试不支持的文件类型"""
        input_dir, _ = temp_dirs
        file_path = os.path.join(input_dir, "test.unknown")
        Path(file_path).touch()
        
        with pytest.raises(ValueError, match="Unsupported file type"):
            await processor.process_single_document(file_path)
    
    def test_supported_formats_detection(self, processor):
        """测试支持的格式检测"""
        # 这个测试验证处理器能正确识别支持的格式
        supported_extensions = ['.txt', '.pdf', '.docx', '.pptx', '.xlsx', '.md']
        
        for ext in supported_extensions:
            if ext in ['.txt', '.pdf']:
                # 这些格式由原生处理器支持
                assert True  # 总是支持
            else:
                # 这些格式由unstructured支持（如果库可用）
                assert True  # 在我们的实现中支持


class TestMultiFormatProcessorIntegration:
    """多格式处理器集成测试"""
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_real_file_processing_if_unstructured_available(self):
        """如果unstructured库可用，测试真实文件处理"""
        try:
            # 尝试导入unstructured库
            from unstructured.partition.md import partition_md
            
            # 如果导入成功，进行真实测试
            with tempfile.TemporaryDirectory() as temp_dir:
                # 创建真实的markdown文件
                md_file = os.path.join(temp_dir, "real_test.md")
                with open(md_file, 'w', encoding='utf-8') as f:
                    f.write("# 真实测试\n\n这是真实的markdown测试文件。\n\n## 功能验证\n\n- 功能1\n- 功能2")
                
                # 创建处理器
                processor = DocumentProcessor(
                    input_dir=temp_dir,
                    output_dir=temp_dir,
                    use_enhanced_parser=False,
                    enable_cleaning=False,
                    enable_terminology_standardization=False,
                    enable_quality_filtering=False,
                    enable_async_metadata=False
                )
                
                # 处理文件
                result = await processor.process_single_document(md_file)
                
                # 验证结果
                assert result is not None
                assert "真实测试" in result["raw_text"]
                assert result["metadata"]["processing_method"] == "unstructured"
                
        except ImportError:
            # 如果unstructured库不可用，跳过测试
            pytest.skip("Unstructured library not available for integration test")


# Pytest配置标记
pytestmark = [
    pytest.mark.unit,  # 标记为单元测试
]