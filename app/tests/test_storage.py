"""存储模块测试

使用conftest.py中的模拟组件进行测试
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
import os
import tempfile

from app.storage.database import DatabaseManager
from app.storage.vector_store import VectorStore


class TestDatabaseManager:
    """数据库管理器测试类"""
    
    @pytest.fixture
    def db_manager(self):
        """创建数据库管理器实例"""
        # 使用conftest.py中的mock_db_manager
        manager = Mock()
        
        # 设置常用方法的返回值
        manager.save_document.return_value = "doc_123"
        manager.get_document.return_value = {
            "id": "doc_123",
            "title": "测试文档",
            "content": "文档内容",
            "file_path": "/path/to/doc.pdf",
            "file_size": 1000,
            "file_type": "application/pdf",
            "metadata": {"key": "value"},
            "created_at": "2023-01-01 00:00:00"
        }
        manager.save_chunks.return_value = ["chunk_1", "chunk_2"]
        manager.get_chunks.return_value = [
            {"id": "chunk_1", "content": "块1内容", "metadata": {"source": "doc1.pdf"}},
            {"id": "chunk_2", "content": "块2内容", "metadata": {"source": "doc1.pdf"}}
        ]
        manager.save_chat_history.return_value = "chat_123"
        manager.get_chat_history.return_value = {
            "id": "chat_123",
            "session_id": "session_123",
            "messages": [
                {"role": "user", "content": "你好"},
                {"role": "assistant", "content": "您好，有什么可以帮助您的？"}
            ],
            "created_at": "2023-01-01 00:00:00"
        }
        
        return manager
    
    def test_save_document(self, db_manager):
        """测试保存文档功能"""
        # 准备测试数据
        doc_data = {
            "id": "doc_123",
            "title": "测试文档",
            "content": "文档内容",
            "file_path": "/path/to/doc.pdf",
            "file_size": 1000,
            "file_type": "application/pdf",
            "metadata": {"key": "value"}
        }
        
        # 执行保存
        result = db_manager.save_document(doc_data)
        
        # 验证结果
        assert result == "doc_123"
        
        # 验证调用
        db_manager.save_document.assert_called_once_with(doc_data)
    
    def test_get_document(self, db_manager):
        """测试获取文档功能"""
        # 执行获取
        result = db_manager.get_document("doc_123")
        
        # 验证结果
        assert result is not None
        assert result["id"] == "doc_123"
        assert result["title"] == "测试文档"
        
        # 验证调用
        db_manager.get_document.assert_called_once_with("doc_123")
    
    def test_get_document_not_found(self, db_manager):
        """测试获取不存在的文档"""
        # 设置模拟返回None
        db_manager.get_document.return_value = None
        
        # 执行获取
        result = db_manager.get_document("not_exist")
        
        # 验证结果
        assert result is None
    
    def test_save_chunks(self, db_manager):
        """测试保存文本块功能"""
        # 准备测试数据
        chunks = [
            {"content": "块1内容", "metadata": {"source": "doc1.pdf"}},
            {"content": "块2内容", "metadata": {"source": "doc1.pdf"}}
        ]
        
        # 执行保存
        result = db_manager.save_chunks(chunks, document_id="doc_123")
        
        # 验证结果
        assert len(result) == 2
        
        # 验证调用
        db_manager.save_chunks.assert_called_once_with(chunks, document_id="doc_123")
    
    def test_get_chunks(self, db_manager):
        """测试获取文本块功能"""
        # 执行获取
        result = db_manager.get_chunks(document_id="doc_123")
        
        # 验证结果
        assert len(result) == 2
        assert result[0]["id"] == "chunk_1"
        assert result[0]["content"] == "块1内容"
        
        # 验证调用
        db_manager.get_chunks.assert_called_once_with(document_id="doc_123")
    
    def test_save_chat_history(self, db_manager):
        """测试保存聊天历史功能"""
        # 准备测试数据
        chat_data = {
            "session_id": "session_123",
            "messages": [
                {"role": "user", "content": "你好"},
                {"role": "assistant", "content": "您好，有什么可以帮助您的？"}
            ]
        }
        
        # 执行保存
        result = db_manager.save_chat_history(chat_data)
        
        # 验证结果
        assert result is not None
        
        # 验证调用
        db_manager.save_chat_history.assert_called_once_with(chat_data)
    
    def test_get_chat_history(self, db_manager):
        """测试获取聊天历史功能"""
        # 执行获取
        result = db_manager.get_chat_history(session_id="session_123")
        
        # 验证结果
        assert result is not None
        assert result["session_id"] == "session_123"
        assert len(result["messages"]) == 2
        
        # 验证调用
        db_manager.get_chat_history.assert_called_once_with(session_id="session_123")


class TestVectorStore:
    """向量存储测试类"""
    
    @pytest.fixture
    async def vector_store(self):
        """创建向量存储实例"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # 模拟嵌入模型
            mock_embeddings = Mock()
            mock_embeddings.embed_query.return_value = [0.1, 0.2, 0.3]
            mock_embeddings.embed_documents.return_value = [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]]
            
            # 模拟Chroma客户端
            with patch('app.storage.vector_store.chromadb') as mock_chromadb:
                mock_client = Mock()
                mock_collection = Mock()
                mock_client.get_or_create_collection.return_value = mock_collection
                mock_chromadb.PersistentClient.return_value = mock_client
                
                # 创建向量存储
                store = VectorStore(embedding_model=mock_embeddings)
                store.chroma_client = mock_client
                store.collection = mock_collection
                
                # 返回存储和模拟对象
                yield store, mock_client, mock_collection, mock_embeddings
    
    @pytest.mark.asyncio
    async def test_add_documents(self, vector_store):
        """测试添加文档功能"""
        store, mock_client, mock_collection, mock_embeddings = vector_store
        
        # 设置模拟返回值
        mock_collection.add.return_value = {"ids": ["id1", "id2"]}
        
        # 准备测试数据
        documents = [
            {"content": "文档1内容", "metadata": {"source": "doc1.pdf"}},
            {"content": "文档2内容", "metadata": {"source": "doc2.pdf"}}
        ]
        
        # 执行添加
        result = await store.add_documents(documents)
        
        # 验证结果
        assert len(result) == 2
        
        # 验证调用
        mock_embeddings.embed_documents.assert_called_once()
        mock_collection.add.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_search(self, vector_store):
        """测试搜索功能"""
        store, mock_client, mock_collection, mock_embeddings = vector_store
        
        # 设置模拟返回值
        mock_collection.query.return_value = {
            "ids": ["id1", "id2"],
            "documents": ["文档1内容", "文档2内容"],
            "metadatas": [{"source": "doc1.pdf"}, {"source": "doc2.pdf"}],
            "distances": [0.1, 0.2]
        }
        
        # 执行搜索
        result = await store.search("测试查询", top_k=2)
        
        # 验证结果
        assert len(result) == 2
        assert result[0]["id"] == "id1"
        assert result[0]["content"] == "文档1内容"
        assert result[0]["metadata"]["source"] == "doc1.pdf"
        assert result[0]["score"] == 0.9  # 1 - 0.1
        
        # 验证调用
        mock_embeddings.embed_query.assert_called_once_with("测试查询")
        mock_collection.query.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_update_document(self, vector_store):
        """测试更新文档功能"""
        store, mock_client, mock_collection, mock_embeddings = vector_store
        
        # 设置模拟返回值
        mock_collection.get.return_value = {
            "ids": ["doc_123"],
            "documents": ["旧内容"],
            "metadatas": [{"source": "doc1.pdf"}]
        }
        
        # 执行更新
        result = await store.update_document("doc_123", "新内容", {"source": "doc1.pdf", "updated": True})
        
        # 验证结果
        assert result is True
        
        # 验证调用
        mock_collection.get.assert_called_once_with(ids=["doc_123"])
        mock_embeddings.embed_documents.assert_called_once_with(["新内容"])
        mock_collection.update.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_delete_document(self, vector_store):
        """测试删除文档功能"""
        store, mock_client, mock_collection, mock_embeddings = vector_store
        
        # 执行删除
        result = await store.delete_document("doc_123")
        
        # 验证结果
        assert result is True
        
        # 验证调用
        mock_collection.delete.assert_called_once_with(ids=["doc_123"])
    
    @pytest.mark.asyncio
    async def test_get_collection_stats(self, vector_store):
        """测试获取集合统计信息功能"""
        store, mock_client, mock_collection, mock_embeddings = vector_store
        
        # 设置模拟返回值
        mock_collection.count.return_value = 10
        
        # 执行获取统计信息
        result = await store.get_collection_stats()
        
        # 验证结果
        assert result is not None
        assert result["document_count"] == 10
        
        # 验证调用
        mock_collection.count.assert_called_once()