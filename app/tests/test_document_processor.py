"""文档处理器测试

使用conftest.py中的模拟组件进行测试
"""

import pytest
import os
import tempfile
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from pathlib import Path

from app.processors.document_processor import DocumentProcessor


class TestDocumentProcessor:
    """文档处理器测试类"""
    
    @pytest.fixture
    def document_processor(self, tmp_dirs, mock_vector_store, mock_db_manager):
        """创建文档处理器实例"""
        input_dir, output_dir = tmp_dirs
        processor = DocumentProcessor(
            input_dir=input_dir,
            output_dir=output_dir,
            vector_store=mock_vector_store
        )
        # 注入模拟的db_manager
        processor.db_manager = mock_db_manager
        # 禁用异步元数据处理，避免测试依赖Redis
        processor.enable_async_metadata = False
        return processor
    
    def test_processor_initialization(self, document_processor):
        """测试处理器初始化"""
        assert document_processor is not None
        assert document_processor.input_dir is not None
        assert document_processor.output_dir is not None
        assert document_processor.vector_store is not None
        assert hasattr(document_processor, 'process_single_document')
    
    @pytest.mark.asyncio
    async def test_process_single_document_pdf(self, document_processor, tmp_dirs):
        """测试处理单个PDF文档"""
        input_dir, _ = tmp_dirs
        
        # 创建测试PDF文件
        test_pdf_path = os.path.join(input_dir, "test.pdf")
        with open(test_pdf_path, "wb") as f:
            f.write(b"%PDF-1.4\ntest content")
        
        # 模拟PDF处理器
        with patch('app.processors.document_processor.PDFProcessor') as mock_pdf_processor:
            mock_instance = Mock()
            mock_instance.process.return_value = {
                "filename": "test.pdf",
                "title": "测试文档",
                "text": "这是测试PDF内容",
                "tables": [],
                "references": []
            }
            mock_pdf_processor.return_value = mock_instance
            
            # 模拟文本清理器
            with patch.object(document_processor.text_cleaner, 'clean_comprehensive') as mock_clean:
                mock_clean.return_value = "清理后的测试内容"
                
                # 模拟术语标准化
                with patch.object(document_processor.terminology_standardizer, 'standardize_text') as mock_standardize:
                    mock_standardize.return_value = "标准化后的测试内容"
                    
                    # 模拟质量过滤
                    with patch.object(document_processor, '_split_into_chunks') as mock_split:
                        mock_split.return_value = ["测试块1", "测试块2"]
                        
                        with patch.object(document_processor.quality_filter, 'filter_text_chunks') as mock_filter:
                            mock_filter.return_value = (["测试块1"], [{"source": test_pdf_path, "chunk_index": 0}])
                            
                            # 执行处理
                            import uuid
                            test_document_id = str(uuid.uuid4())
                            result = await document_processor.process_single_document(test_pdf_path, test_document_id)
                            
                            # 验证结果
                            assert result is not None
                            assert "document_id" in result
                            assert "raw_text" in result
                            assert "cleaned_text" in result
                            assert "standardized_text" in result
                            assert result["cleaned_text"] == "清理后的测试内容"
                            assert result["standardized_text"] == "标准化后的测试内容"
    
    @pytest.mark.asyncio
    async def test_process_single_document_txt(self, document_processor, tmp_dirs):
        """测试处理单个TXT文档"""
        input_dir, _ = tmp_dirs
        
        # 创建测试TXT文件
        test_txt_path = os.path.join(input_dir, "test.txt")
        with open(test_txt_path, "w", encoding="utf-8") as f:
            f.write("这是测试TXT内容")
        
        # 模拟文本清理器
        with patch.object(document_processor.text_cleaner, 'clean_comprehensive') as mock_clean:
            mock_clean.return_value = "清理后的TXT内容"
            
            # 模拟术语标准化
            with patch.object(document_processor.terminology_standardizer, 'standardize_text') as mock_standardize:
                mock_standardize.return_value = "标准化后的TXT内容"
                
                # 模拟质量过滤
                with patch.object(document_processor, '_split_into_chunks') as mock_split:
                    mock_split.return_value = ["TXT测试块1"]
                    
                    with patch.object(document_processor.quality_filter, 'filter_text_chunks') as mock_filter:
                        mock_filter.return_value = (["TXT测试块1"], [{"source": test_txt_path, "chunk_index": 0}])
                        
                        # 执行处理
                        import uuid
                        test_document_id = str(uuid.uuid4())
                        result = await document_processor.process_single_document(test_txt_path, test_document_id)
                        
                        # 验证结果
                        assert result is not None
                        assert "document_id" in result
                        assert "raw_text" in result
                        assert "cleaned_text" in result
                        assert "standardized_text" in result
                        assert result["cleaned_text"] == "清理后的TXT内容"
                        assert result["standardized_text"] == "标准化后的TXT内容"
    
    @pytest.mark.asyncio
    async def test_process_single_document_unsupported_type(self, document_processor, tmp_dirs):
        """测试处理不支持的文件类型"""
        input_dir, _ = tmp_dirs
        
        # 创建测试不支持类型文件
        test_unsupported_path = os.path.join(input_dir, "test.exe")
        with open(test_unsupported_path, "wb") as f:
            f.write(b"binary content")
        
        # 执行处理，应该抛出异常
        import uuid
        test_document_id = str(uuid.uuid4())
        with pytest.raises(ValueError, match="Unsupported file type"):
            await document_processor.process_single_document(test_unsupported_path, test_document_id)
    
    def test_split_into_chunks(self, document_processor):
        """测试文本分块功能"""
        text = "这是第一句话。这是第二句话。这是第三句话。"
        chunks = document_processor._split_into_chunks(text)
        
        assert len(chunks) > 0
        assert isinstance(chunks[0], str)