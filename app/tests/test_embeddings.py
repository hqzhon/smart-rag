"""嵌入服务测试"""
import pytest
import asyncio
import numpy as np
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from app.embeddings.embeddings import QianwenEmbeddings
from app.embeddings.text_splitter import MedicalTextSplitter
from app.embeddings.semantic.similarity_calculator import SemanticSimilarityCalculator
from app.embeddings.semantic.hybrid_splitter import HybridTextSplitter, ChunkingConfig
from app.embeddings.semantic.cache import EmbeddingCache, GlobalEmbeddingCache
from app.embeddings.semantic.batch_processor import BatchProcessor

class TestQianwenEmbeddings:
    """测试千问嵌入模型"""
    
    @pytest.fixture
    def embeddings(self):
        """创建嵌入模型实例"""
        return QianwenEmbeddings()
    
    def test_init(self, embeddings):
        """测试初始化"""
        assert embeddings is not None
        assert hasattr(embeddings, 'client')
    
    @pytest.mark.asyncio
    async def test_embed_documents_empty(self, embeddings):
        """测试空文档嵌入"""
        result = await embeddings.embed_documents([])
        assert result == []
    
    @pytest.mark.asyncio
    async def test_embed_documents_valid(self, embeddings):
        """测试有效文档嵌入"""
        with patch.object(embeddings, '_embed_text', new_callable=AsyncMock) as mock_embed:
            mock_embed.return_value = [0.1, 0.2, 0.3]
            
            documents = ["测试文档1", "测试文档2"]
            result = await embeddings.embed_documents(documents)
            
            assert len(result) == 2
            assert all(isinstance(emb, list) for emb in result)
            assert mock_embed.call_count == 2
    
    @pytest.mark.asyncio
    async def test_embed_empty_text(self, embeddings):
        """测试空文本嵌入"""
        with patch('app.workflow.qianwen_client.get_qianwen_client') as mock_client:
            mock_client.return_value.__aenter__.return_value.get_single_embedding.return_value = []
            result = await embeddings.embed_query("")
            assert result == []
    
    @pytest.mark.asyncio
    async def test_embed_valid_text(self, embeddings):
        """测试有效文本嵌入"""
        text = "这是一个测试文本"
        mock_embedding = [0.1, 0.2, 0.3, 0.4, 0.5]
        
        with patch('app.workflow.qianwen_client.get_qianwen_client') as mock_client:
            mock_client.return_value.__aenter__.return_value.get_single_embedding.return_value = mock_embedding
            result = await embeddings.embed_query(text)
            
            assert result is not None
            assert isinstance(result, list)
            assert len(result) > 0
            assert all(isinstance(x, float) for x in result)
    
    @pytest.mark.asyncio
    async def test_embed_query(self, embeddings):
        """测试查询嵌入"""
        with patch.object(embeddings, '_embed_text', new_callable=AsyncMock) as mock_embed:
            mock_embed.return_value = [0.1, 0.2, 0.3]
            
            result = await embeddings.embed_query("测试查询")
            
            assert isinstance(result, list)
            assert len(result) == 3
            mock_embed.assert_called_once_with("测试查询")
    
    def test_get_instance_singleton(self):
        """测试单例模式"""
        instance1 = QianwenEmbeddings.get_instance()
        instance2 = QianwenEmbeddings.get_instance()
        assert instance1 is instance2

class TestMedicalTextSplitter:
    """测试医疗文本分块器"""
    
    @pytest.fixture
    def splitter(self):
        """创建分块器实例"""
        return MedicalTextSplitter(chunk_size=100, chunk_overlap=20, enable_semantic=False)
    
    def test_init_default(self):
        """测试默认初始化"""
        splitter = MedicalTextSplitter()
        assert splitter.chunk_size > 0
        assert splitter.chunk_overlap >= 0
        assert isinstance(splitter.enable_semantic, bool)
    
    def test_init_custom(self, splitter):
        """测试自定义参数初始化"""
        assert splitter.chunk_size == 100
        assert splitter.chunk_overlap == 20
        assert splitter.enable_semantic is False
    
    def test_split_text_empty(self, splitter):
        """测试空文本分割"""
        result = splitter.split_text("")
        assert result == []
    
    def test_split_text_short(self, splitter):
        """测试短文本分割"""
        text = "这是一个短文本。"
        result = splitter.split_text(text)
        assert len(result) >= 1
        assert text in result[0]
    
    def test_split_text_long(self, splitter):
        """测试长文本分割"""
        text = "这是一个很长的文本。" * 50  # 创建长文本
        result = splitter.split_text(text)
        assert len(result) > 1
        assert all(len(chunk) <= splitter.chunk_size + splitter.chunk_overlap for chunk in result)
    
    @pytest.mark.asyncio
    async def test_split_text_async_empty(self, splitter):
        """测试异步空文本分割"""
        result = await splitter.split_text_async("")
        assert result == []
    
    @pytest.mark.asyncio
    async def test_split_text_async_valid(self, splitter):
        """测试异步文本分割"""
        text = "这是一个测试文本。" * 10
        result = await splitter.split_text_async(text)
        assert len(result) >= 1
        assert all(isinstance(chunk, str) for chunk in result)


class TestSemanticSimilarityCalculator:
    """测试语义相似度计算器"""
    
    @pytest.fixture
    def mock_embeddings(self):
        """创建模拟嵌入模型"""
        mock = AsyncMock(spec=QianwenEmbeddings)
        mock.embed_query.return_value = [0.1, 0.2, 0.3]
        return mock
    
    @pytest.fixture
    def calculator(self, mock_embeddings):
        """创建相似度计算器实例"""
        return SemanticSimilarityCalculator(mock_embeddings)
    
    def test_init(self, calculator, mock_embeddings):
        """测试初始化"""
        assert calculator.embeddings_model is mock_embeddings
        assert isinstance(calculator.cache, dict)
        assert calculator.cache_size > 0
    
    @pytest.mark.asyncio
    async def test_calculate_similarity(self, calculator, mock_embeddings):
        """测试相似度计算"""
        mock_embeddings.embed_query.side_effect = [
            [1.0, 0.0, 0.0],  # 第一个文本的嵌入
            [0.0, 1.0, 0.0]   # 第二个文本的嵌入
        ]
        
        similarity = await calculator.calculate_similarity("文本1", "文本2")
        
        assert isinstance(similarity, float)
        assert 0.0 <= similarity <= 1.0
        assert mock_embeddings.embed_query.call_count == 2
    
    @pytest.mark.asyncio
    async def test_calculate_similarity_same_text(self, calculator, mock_embeddings):
        """测试相同文本的相似度"""
        mock_embeddings.embed_query.return_value = [1.0, 0.0, 0.0]
        
        similarity = await calculator.calculate_similarity("相同文本", "相同文本")
        
        assert similarity == 1.0  # 相同文本相似度应为1
    
    @pytest.mark.asyncio
    async def test_embedding_cache(self, calculator, mock_embeddings):
        """测试嵌入缓存"""
        mock_embeddings.embed_query.return_value = [0.1, 0.2, 0.3]
        
        # 第一次调用
        await calculator._get_embedding("测试文本")
        # 第二次调用相同文本
        await calculator._get_embedding("测试文本")
        
        # 应该只调用一次嵌入模型（第二次使用缓存）
        assert mock_embeddings.embed_query.call_count == 1
        assert len(calculator.cache) == 1


class TestHybridTextSplitter:
    """测试混合文本分块器"""
    
    @pytest.fixture
    def config(self):
        """创建分块配置"""
        return ChunkingConfig(
            chunk_size=100,
            chunk_overlap=20,
            semantic_threshold=0.75,
            enable_semantic_fallback=True
        )
    
    @pytest.fixture
    def mock_similarity_calculator(self):
        """创建模拟相似度计算器"""
        mock = AsyncMock(spec=SemanticSimilarityCalculator)
        mock.calculate_similarity.return_value = 0.8
        return mock
    
    @pytest.fixture
    def splitter(self, config, mock_similarity_calculator):
        """创建混合分块器实例"""
        return HybridTextSplitter(config, mock_similarity_calculator)
    
    def test_init(self, splitter, config):
        """测试初始化"""
        assert splitter.config == config
        assert splitter.similarity_calculator is not None
        assert splitter.batch_processor is not None
    
    @pytest.mark.asyncio
    async def test_split_text_empty(self, splitter):
        """测试空文本分割"""
        result = await splitter.split_text("")
        assert result == []
    
    @pytest.mark.asyncio
    async def test_split_text_short(self, splitter):
        """测试短文本分割"""
        text = "这是一个短文本。"
        result = await splitter.split_text(text)
        assert len(result) >= 1
        assert text in result[0]
    
    def test_recursive_split(self, splitter):
        """测试递归分割"""
        text = "这是第一段。\n\n这是第二段。\n\n这是第三段。"
        result = splitter._recursive_split(text)
        assert len(result) >= 1
        assert all(isinstance(chunk, str) for chunk in result)
    
    def test_get_stats(self, splitter):
        """测试统计信息获取"""
        stats = splitter.get_stats()
        assert isinstance(stats, dict)
        assert 'total_chunks' in stats
        assert 'semantic_merges' in stats
        assert 'recursive_splits' in stats


class TestEmbeddingCache:
    """测试嵌入缓存"""
    
    @pytest.fixture
    def cache(self):
        """创建缓存实例"""
        return EmbeddingCache(max_size=3, ttl_seconds=None)
    
    def test_init(self, cache):
        """测试初始化"""
        assert cache.max_size == 3
        assert cache.ttl_seconds is None
        assert len(cache.cache) == 0
    
    def test_set_and_get(self, cache):
        """测试设置和获取"""
        embedding = [0.1, 0.2, 0.3]
        cache.set("测试文本", embedding)
        
        result = cache.get("测试文本")
        assert result == embedding
    
    def test_get_nonexistent(self, cache):
        """测试获取不存在的项"""
        result = cache.get("不存在的文本")
        assert result is None
    
    def test_lru_eviction(self, cache):
        """测试LRU淘汰"""
        # 填满缓存
        cache.set("文本1", [0.1])
        cache.set("文本2", [0.2])
        cache.set("文本3", [0.3])
        
        # 添加第四个项，应该淘汰最旧的
        cache.set("文本4", [0.4])
        
        assert cache.get("文本1") is None  # 应该被淘汰
        assert cache.get("文本4") == [0.4]  # 新项应该存在
    
    def test_cache_stats(self, cache):
        """测试缓存统计"""
        cache.set("文本1", [0.1])
        cache.get("文本1")  # 命中
        cache.get("不存在")  # 未命中
        
        stats = cache.get_stats()
        assert stats['hits'] == 1
        assert stats['misses'] == 1
        assert stats['size'] == 1
    
    def test_clear(self, cache):
        """测试清空缓存"""
        cache.set("文本1", [0.1])
        cache.clear()
        
        assert len(cache.cache) == 0
        assert cache.get("文本1") is None


class TestGlobalEmbeddingCache:
    """测试全局嵌入缓存"""
    
    def test_singleton(self):
        """测试单例模式"""
        cache1 = GlobalEmbeddingCache.get_instance()
        cache2 = GlobalEmbeddingCache.get_instance()
        assert cache1 is cache2
    
    def test_resize(self):
        """测试缓存大小调整"""
        cache = GlobalEmbeddingCache.get_instance()
        original_size = cache.max_size
        
        cache.resize(new_max_size=500)
        assert cache.max_size == 500
        
        # 恢复原始大小
        cache.resize(new_max_size=original_size)


class TestBatchProcessor:
    """测试批处理器"""
    
    @pytest.fixture
    def processor(self):
        """创建批处理器实例"""
        return BatchProcessor(batch_size=2, max_workers=2)
    
    def test_init(self, processor):
        """测试初始化"""
        assert processor.batch_size == 2
        assert processor.max_workers == 2
        assert processor.timeout_seconds > 0
    
    @pytest.mark.asyncio
    async def test_process_documents_batch_empty(self, processor):
        """测试空文档批处理"""
        def dummy_processor(doc):
            return f"processed_{doc}"
        
        result = await processor.process_documents_batch([], dummy_processor)
        assert result == []
    
    @pytest.mark.asyncio
    async def test_process_documents_batch_valid(self, processor):
        """测试有效文档批处理"""
        def dummy_processor(doc):
            return f"processed_{doc}"
        
        documents = ["doc1", "doc2", "doc3"]
        result = await processor.process_documents_batch(documents, dummy_processor)
        
        assert len(result) == 3
        assert all("processed_" in item for item in result)
    
    def test_get_stats(self, processor):
        """测试统计信息获取"""
        stats = processor.get_stats()
        assert isinstance(stats, dict)
        assert 'total_processed' in stats
        assert 'total_batches' in stats
        assert 'errors' in stats
    
    def test_cleanup(self, processor):
        """测试清理资源"""
        processor.cleanup()
        # 验证清理后的状态
        assert processor._executor is None or processor._executor._shutdown