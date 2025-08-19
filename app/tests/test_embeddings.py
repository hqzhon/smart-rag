"""
嵌入服务测试
"""
import pytest
from unittest.mock import Mock, patch
from app.embeddings.embeddings import EmbeddingService
from app.embeddings.text_splitter import TextSplitter

class TestEmbeddingService:
    """嵌入服务测试类"""
    
    @pytest.fixture
    def embedding_service(self):
        """创建嵌入服务实例"""
        return EmbeddingService()
    
    def test_init(self, embedding_service):
        """测试服务初始化"""
        assert embedding_service is not None
        assert hasattr(embedding_service, 'model')
    
    @pytest.mark.asyncio
    async def test_embed_text_empty(self, embedding_service):
        """测试空文本嵌入"""
        with pytest.raises(ValueError, match="文本不能为空"):
            await embedding_service.embed_text("")
    
    @pytest.mark.asyncio
    async def test_embed_text_valid(self, embedding_service):
        """测试有效文本嵌入"""
        text = "这是一个测试文本"
        result = await embedding_service.embed_text(text)
        
        assert result is not None
        assert isinstance(result, list)
        assert len(result) > 0
        assert all(isinstance(x, float) for x in result)

class TestTextSplitter:
    """文本分块器测试类"""
    
    @pytest.fixture
    def text_splitter(self):
        """创建文本分块器实例"""
        return TextSplitter(chunk_size=100, chunk_overlap=20)
    
    def test_init(self, text_splitter):
        """测试初始化"""
        assert text_splitter.chunk_size == 100
        assert text_splitter.chunk_overlap == 20
    
    def test_split_text_empty(self, text_splitter):
        """测试空文本分块"""
        result = text_splitter.split_text("")
        assert result == []
    
    def test_split_text_short(self, text_splitter):
        """测试短文本分块"""
        text = "这是一个短文本"
        result = text_splitter.split_text(text)
        assert len(result) == 1
        assert result[0] == text
    
    def test_split_text_long(self, text_splitter):
        """测试长文本分块"""
        text = "这是一个很长的文本。" * 50  # 创建长文本
        result = text_splitter.split_text(text)
        assert len(result) > 1
        assert all(len(chunk) <= text_splitter.chunk_size + 50 for chunk in result)  # 允许一些误差