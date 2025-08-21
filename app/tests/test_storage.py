"""存储模块测试"""

import pytest
import tempfile
import os
import json
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from pathlib import Path

from app.storage.vector_store import VectorStore
from app.storage.database import DatabaseManager as DocumentStore
from unittest.mock import Mock as CacheManager
from unittest.mock import Mock as FileManager
from app.models.document_models import Document


class TestVectorStore:
    """向量存储测试类"""
    
    @pytest.fixture
    def vector_store(self):
        """创建向量存储实例"""
        with patch('app.storage.vector_store.ChromaDB') as mock_chroma:
            mock_chroma.return_value = Mock()
            return VectorStore()
    
    @pytest.fixture
    def sample_vectors(self):
        """创建示例向量数据"""
        return [
            {
                'id': 'doc1_chunk1',
                'vector': [0.1, 0.2, 0.3, 0.4, 0.5],
                'metadata': {'document_id': 'doc1', 'chunk_index': 0},
                'text': '这是第一个文档块的内容'
            },
            {
                'id': 'doc1_chunk2', 
                'vector': [0.2, 0.3, 0.4, 0.5, 0.6],
                'metadata': {'document_id': 'doc1', 'chunk_index': 1},
                'text': '这是第二个文档块的内容'
            }
        ]
    
    def test_vector_store_initialization(self, vector_store):
        """测试向量存储初始化"""
        assert vector_store is not None
        assert hasattr(vector_store, 'add_vectors')
        assert hasattr(vector_store, 'search_similar')
    
    @pytest.mark.asyncio
    async def test_add_vectors_success(self, vector_store, sample_vectors):
        """测试添加向量成功"""
        with patch.object(vector_store, '_client') as mock_client:
            mock_client.add.return_value = True
            
            result = await vector_store.add_vectors(sample_vectors)
            
            assert result is True
            mock_client.add.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_add_vectors_failure(self, vector_store, sample_vectors):
        """测试添加向量失败"""
        with patch.object(vector_store, '_client') as mock_client:
            mock_client.add.side_effect = Exception("添加失败")
            
            with pytest.raises(Exception, match="添加失败"):
                await vector_store.add_vectors(sample_vectors)
    
    @pytest.mark.asyncio
    async def test_search_similar_vectors(self, vector_store):
        """测试相似向量搜索"""
        query_vector = [0.15, 0.25, 0.35, 0.45, 0.55]
        
        with patch.object(vector_store, '_client') as mock_client:
            mock_client.query.return_value = {
                'ids': [['doc1_chunk1', 'doc1_chunk2']],
                'distances': [[0.1, 0.2]],
                'metadatas': [[
                    {'document_id': 'doc1', 'chunk_index': 0},
                    {'document_id': 'doc1', 'chunk_index': 1}
                ]],
                'documents': [['文档块1内容', '文档块2内容']]
            }
            
            results = await vector_store.search_similar(query_vector, top_k=2)
            
            assert len(results) == 2
            assert results[0]['id'] == 'doc1_chunk1'
            assert results[0]['distance'] == 0.1
            assert results[1]['id'] == 'doc1_chunk2'
            assert results[1]['distance'] == 0.2
    
    @pytest.mark.asyncio
    async def test_delete_vectors(self, vector_store):
        """测试删除向量"""
        document_id = "doc1"
        
        with patch.object(vector_store, '_client') as mock_client:
            mock_client.delete.return_value = True
            
            result = await vector_store.delete_vectors(document_id)
            
            assert result is True
            mock_client.delete.assert_called_once()
    
    def test_get_collection_stats(self, vector_store):
        """测试获取集合统计信息"""
        with patch.object(vector_store, '_client') as mock_client:
            mock_client.count.return_value = 100
            
            stats = vector_store.get_collection_stats()
            
            assert stats['total_vectors'] == 100
            assert 'collection_name' in stats


class TestDocumentStore:
    """文档存储测试类"""
    
    @pytest.fixture
    def document_store(self):
        """创建文档存储实例"""
        with patch('app.storage.document_store.DatabaseManager') as mock_db:
            mock_db.return_value = Mock()
            return DocumentStore()
    
    @pytest.fixture
    def sample_document(self):
        """创建示例文档"""
        return Document(
            id="test-doc-1",
            title="测试文档",
            content="这是一个测试文档的内容",
            file_path="/tmp/test.pdf",
            file_type="pdf",
            file_size=1024,
            metadata={"author": "测试作者"}
        )
    
    def test_document_store_initialization(self, document_store):
        """测试文档存储初始化"""
        assert document_store is not None
        assert hasattr(document_store, 'save_document')
        assert hasattr(document_store, 'get_document')
        assert hasattr(document_store, 'delete_document')
    
    @pytest.mark.asyncio
    async def test_save_document_success(self, document_store, sample_document):
        """测试保存文档成功"""
        with patch.object(document_store, '_db') as mock_db:
            mock_db.insert.return_value = sample_document.id
            
            result = await document_store.save_document(sample_document)
            
            assert result == sample_document.id
            mock_db.insert.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_document_exists(self, document_store, sample_document):
        """测试获取存在的文档"""
        with patch.object(document_store, '_db') as mock_db:
            mock_db.select.return_value = {
                'id': sample_document.id,
                'title': sample_document.title,
                'content': sample_document.content,
                'file_path': sample_document.file_path,
                'file_type': sample_document.file_type,
                'file_size': sample_document.file_size,
                'metadata': json.dumps(sample_document.metadata)
            }
            
            result = await document_store.get_document(sample_document.id)
            
            assert result is not None
            assert result.id == sample_document.id
            assert result.title == sample_document.title
    
    @pytest.mark.asyncio
    async def test_get_document_not_exists(self, document_store):
        """测试获取不存在的文档"""
        with patch.object(document_store, '_db') as mock_db:
            mock_db.select.return_value = None
            
            result = await document_store.get_document("nonexistent-id")
            
            assert result is None
    
    @pytest.mark.asyncio
    async def test_delete_document_success(self, document_store):
        """测试删除文档成功"""
        document_id = "test-doc-1"
        
        with patch.object(document_store, '_db') as mock_db:
            mock_db.delete.return_value = True
            
            result = await document_store.delete_document(document_id)
            
            assert result is True
            mock_db.delete.assert_called_once_with(document_id)
    
    @pytest.mark.asyncio
    async def test_list_documents(self, document_store):
        """测试列出文档"""
        with patch.object(document_store, '_db') as mock_db:
            mock_db.select_all.return_value = [
                {
                    'id': 'doc1',
                    'title': '文档1',
                    'content': '内容1',
                    'file_path': '/tmp/doc1.pdf',
                    'file_type': 'pdf',
                    'file_size': 1024,
                    'metadata': '{}'
                },
                {
                    'id': 'doc2',
                    'title': '文档2', 
                    'content': '内容2',
                    'file_path': '/tmp/doc2.pdf',
                    'file_type': 'pdf',
                    'file_size': 2048,
                    'metadata': '{}'
                }
            ]
            
            results = await document_store.list_documents(limit=10, offset=0)
            
            assert len(results) == 2
            assert results[0].id == 'doc1'
            assert results[1].id == 'doc2'


class TestDatabaseManager:
    """数据库管理器测试类"""
    
    @pytest.fixture
    def db_manager(self):
        """创建数据库管理器实例"""
        with patch('app.storage.database.mysql.connector.connect') as mock_connect:
            mock_connect.return_value = Mock()
            from app.storage.database import DatabaseManager
            return DatabaseManager()
    
    @pytest.fixture
    def sample_document_data(self):
        """创建示例文档数据"""
        return {
            'id': 'test-doc-1',
            'title': '测试文档',
            'content': '这是测试内容',
            'file_path': '/tmp/test.pdf',
            'file_type': 'pdf',
            'file_size': 1024,
            'metadata': '{"author": "测试作者"}',
            'vectorized': False,
            'created_at': '2024-01-01 00:00:00',
            'updated_at': '2024-01-01 00:00:00'
        }
    
    def test_database_manager_initialization(self, db_manager):
        """测试数据库管理器初始化"""
        assert db_manager is not None
        assert hasattr(db_manager, 'save_document')
        assert hasattr(db_manager, 'get_document')
        assert hasattr(db_manager, 'delete_document')
        assert hasattr(db_manager, 'create_session')
        assert hasattr(db_manager, 'save_chat_history')
    
    @pytest.mark.asyncio
    async def test_save_document_new(self, db_manager, sample_document_data):
        """测试保存新文档"""
        with patch.object(db_manager, '_execute_query') as mock_execute:
            mock_execute.return_value = None
            
            await db_manager.save_document(
                sample_document_data['id'],
                sample_document_data['title'],
                sample_document_data['content'],
                sample_document_data['file_path'],
                sample_document_data['file_type'],
                sample_document_data['file_size'],
                sample_document_data['metadata']
            )
            
            mock_execute.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_document_exists(self, db_manager, sample_document_data):
        """测试获取存在的文档"""
        with patch.object(db_manager, '_fetch_one') as mock_fetch:
            mock_fetch.return_value = sample_document_data
            
            result = await db_manager.get_document(sample_document_data['id'])
            
            assert result is not None
            assert result['id'] == sample_document_data['id']
            assert result['title'] == sample_document_data['title']
    
    @pytest.mark.asyncio
    async def test_get_document_not_exists(self, db_manager):
        """测试获取不存在的文档"""
        with patch.object(db_manager, '_fetch_one') as mock_fetch:
            mock_fetch.return_value = None
            
            result = await db_manager.get_document('nonexistent-id')
            
            assert result is None
    
    @pytest.mark.asyncio
    async def test_list_documents_with_pagination(self, db_manager):
        """测试分页列出文档"""
        mock_documents = [
            {'id': 'doc1', 'title': '文档1'},
            {'id': 'doc2', 'title': '文档2'}
        ]
        
        with patch.object(db_manager, '_fetch_all') as mock_fetch:
            mock_fetch.return_value = mock_documents
            
            results = await db_manager.list_documents(limit=10, offset=0)
            
            assert len(results) == 2
            assert results[0]['id'] == 'doc1'
            assert results[1]['id'] == 'doc2'
    
    @pytest.mark.asyncio
    async def test_delete_document_success(self, db_manager):
        """测试删除文档成功"""
        document_id = 'test-doc-1'
        
        with patch.object(db_manager, '_execute_query') as mock_execute:
            mock_execute.return_value = None
            
            await db_manager.delete_document(document_id)
            
            mock_execute.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_update_document_vectorized_status(self, db_manager):
        """测试更新文档向量化状态"""
        document_id = 'test-doc-1'
        
        with patch.object(db_manager, '_execute_query') as mock_execute:
            mock_execute.return_value = None
            
            await db_manager.update_document_vectorized_status(document_id, True)
            
            mock_execute.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_documents_by_vectorized_status(self, db_manager):
        """测试根据向量化状态获取文档"""
        mock_documents = [
            {'id': 'doc1', 'vectorized': False},
            {'id': 'doc2', 'vectorized': False}
        ]
        
        with patch.object(db_manager, '_fetch_all') as mock_fetch:
            mock_fetch.return_value = mock_documents
            
            results = await db_manager.get_documents_by_vectorized_status(False)
            
            assert len(results) == 2
            assert all(not doc['vectorized'] for doc in results)
    
    @pytest.mark.asyncio
    async def test_create_session(self, db_manager):
        """测试创建会话"""
        session_id = 'test-session-1'
        user_id = 'test-user-1'
        
        with patch.object(db_manager, '_execute_query') as mock_execute:
            mock_execute.return_value = None
            
            await db_manager.create_session(session_id, user_id)
            
            mock_execute.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_session_exists(self, db_manager):
        """测试获取存在的会话"""
        session_data = {
            'id': 'test-session-1',
            'user_id': 'test-user-1',
            'created_at': '2024-01-01 00:00:00'
        }
        
        with patch.object(db_manager, '_fetch_one') as mock_fetch:
            mock_fetch.return_value = session_data
            
            result = await db_manager.get_session(session_data['id'])
            
            assert result is not None
            assert result['id'] == session_data['id']
            assert result['user_id'] == session_data['user_id']
    
    @pytest.mark.asyncio
    async def test_save_chat_history(self, db_manager):
        """测试保存聊天记录"""
        session_id = 'test-session-1'
        user_message = '用户问题'
        assistant_message = '助手回答'
        
        with patch.object(db_manager, '_execute_query') as mock_execute:
            mock_execute.return_value = None
            
            await db_manager.save_chat_history(
                session_id, user_message, assistant_message
            )
            
            mock_execute.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_chat_history(self, db_manager):
        """测试获取聊天记录"""
        session_id = 'test-session-1'
        mock_history = [
            {
                'session_id': session_id,
                'user_message': '问题1',
                'assistant_message': '回答1',
                'created_at': '2024-01-01 00:00:00'
            },
            {
                'session_id': session_id,
                'user_message': '问题2',
                'assistant_message': '回答2',
                'created_at': '2024-01-01 00:01:00'
            }
        ]
        
        with patch.object(db_manager, '_fetch_all') as mock_fetch:
            mock_fetch.return_value = mock_history
            
            results = await db_manager.get_chat_history(session_id, limit=10)
            
            assert len(results) == 2
            assert results[0]['user_message'] == '问题1'
            assert results[1]['user_message'] == '问题2'
    
    @pytest.mark.asyncio
    async def test_save_search_history(self, db_manager):
        """测试保存搜索记录"""
        session_id = 'test-session-1'
        query = '测试查询'
        results = ['结果1', '结果2']
        
        with patch.object(db_manager, '_execute_query') as mock_execute:
            mock_execute.return_value = None
            
            await db_manager.save_search_history(session_id, query, results)
            
            mock_execute.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_health_check_success(self, db_manager):
        """测试数据库健康检查成功"""
        with patch.object(db_manager, '_fetch_one') as mock_fetch:
            mock_fetch.return_value = {'result': 1}
            
            result = await db_manager.health_check()
            
            assert result is True
    
    @pytest.mark.asyncio
    async def test_health_check_failure(self, db_manager):
        """测试数据库健康检查失败"""
        with patch.object(db_manager, '_fetch_one') as mock_fetch:
            mock_fetch.side_effect = Exception('Database connection failed')
            
            result = await db_manager.health_check()
            
            assert result is False
    
    @pytest.mark.asyncio
    async def test_get_all_documents_content(self, db_manager):
        """测试获取所有文档内容"""
        mock_documents = [
            {'id': 'doc1', 'content': '内容1'},
            {'id': 'doc2', 'content': '内容2'}
        ]
        
        with patch.object(db_manager, '_fetch_all') as mock_fetch:
            mock_fetch.return_value = mock_documents
            
            results = await db_manager.get_all_documents_content()
            
            assert len(results) == 2
            assert results[0]['content'] == '内容1'
            assert results[1]['content'] == '内容2'


class TestCacheManager:
    """缓存管理器测试类"""
    
    @pytest.fixture
    def cache_manager(self):
        """创建缓存管理器实例"""
        with patch('app.storage.cache_manager.Redis') as mock_redis:
            mock_redis.return_value = Mock()
            return CacheManager()
    
    def test_cache_manager_initialization(self, cache_manager):
        """测试缓存管理器初始化"""
        assert cache_manager is not None
        assert hasattr(cache_manager, 'get')
        assert hasattr(cache_manager, 'set')
        assert hasattr(cache_manager, 'delete')
    
    @pytest.mark.asyncio
    async def test_cache_set_and_get(self, cache_manager):
        """测试缓存设置和获取"""
        key = "test_key"
        value = {"data": "test_value", "number": 123}
        
        with patch.object(cache_manager, '_redis') as mock_redis:
            mock_redis.set.return_value = True
            mock_redis.get.return_value = json.dumps(value)
            
            # 设置缓存
            set_result = await cache_manager.set(key, value, ttl=3600)
            assert set_result is True
            
            # 获取缓存
            get_result = await cache_manager.get(key)
            assert get_result == value
    
    @pytest.mark.asyncio
    async def test_cache_get_nonexistent(self, cache_manager):
        """测试获取不存在的缓存"""
        with patch.object(cache_manager, '_redis') as mock_redis:
            mock_redis.get.return_value = None
            
            result = await cache_manager.get("nonexistent_key")
            assert result is None
    
    @pytest.mark.asyncio
    async def test_cache_delete(self, cache_manager):
        """测试删除缓存"""
        key = "test_key"
        
        with patch.object(cache_manager, '_redis') as mock_redis:
            mock_redis.delete.return_value = 1
            
            result = await cache_manager.delete(key)
            assert result is True
    
    @pytest.mark.asyncio
    async def test_cache_exists(self, cache_manager):
        """测试检查缓存是否存在"""
        key = "test_key"
        
        with patch.object(cache_manager, '_redis') as mock_redis:
            mock_redis.exists.return_value = 1
            
            result = await cache_manager.exists(key)
            assert result is True
    
    @pytest.mark.asyncio
    async def test_cache_clear_pattern(self, cache_manager):
        """测试按模式清理缓存"""
        pattern = "test_*"
        
        with patch.object(cache_manager, '_redis') as mock_redis:
            mock_redis.keys.return_value = ["test_key1", "test_key2"]
            mock_redis.delete.return_value = 2
            
            result = await cache_manager.clear_pattern(pattern)
            assert result == 2


class TestFileManager:
    """文件管理器测试类"""
    
    @pytest.fixture
    def file_manager(self):
        """创建文件管理器实例"""
        return FileManager(base_path="/tmp/test_storage")
    
    @pytest.fixture
    def temp_file(self):
        """创建临时文件"""
        with tempfile.NamedTemporaryFile(delete=False, suffix='.txt') as tmp:
            tmp.write(b"test file content")
            tmp.flush()
            yield tmp.name
        os.unlink(tmp.name)
    
    def test_file_manager_initialization(self, file_manager):
        """测试文件管理器初始化"""
        assert file_manager is not None
        assert hasattr(file_manager, 'save_file')
        assert hasattr(file_manager, 'get_file')
        assert hasattr(file_manager, 'delete_file')
    
    @pytest.mark.asyncio
    async def test_save_file_success(self, file_manager, temp_file):
        """测试保存文件成功"""
        file_id = "test_file_1"
        
        with patch('shutil.copy2') as mock_copy:
            mock_copy.return_value = None
            with patch('os.makedirs') as mock_makedirs:
                mock_makedirs.return_value = None
                
                result = await file_manager.save_file(temp_file, file_id)
                
                assert result is not None
                assert file_id in result
    
    @pytest.mark.asyncio
    async def test_get_file_exists(self, file_manager):
        """测试获取存在的文件"""
        file_id = "test_file_1"
        
        with patch('os.path.exists') as mock_exists:
            mock_exists.return_value = True
            with patch('builtins.open', create=True) as mock_open:
                mock_open.return_value.__enter__.return_value.read.return_value = b"file content"
                
                result = await file_manager.get_file(file_id)
                
                assert result == b"file content"
    
    @pytest.mark.asyncio
    async def test_get_file_not_exists(self, file_manager):
        """测试获取不存在的文件"""
        file_id = "nonexistent_file"
        
        with patch('os.path.exists') as mock_exists:
            mock_exists.return_value = False
            
            result = await file_manager.get_file(file_id)
            
            assert result is None
    
    @pytest.mark.asyncio
    async def test_delete_file_success(self, file_manager):
        """测试删除文件成功"""
        file_id = "test_file_1"
        
        with patch('os.path.exists') as mock_exists:
            mock_exists.return_value = True
            with patch('os.remove') as mock_remove:
                mock_remove.return_value = None
                
                result = await file_manager.delete_file(file_id)
                
                assert result is True
    
    @pytest.mark.asyncio
    async def test_delete_file_not_exists(self, file_manager):
        """测试删除不存在的文件"""
        file_id = "nonexistent_file"
        
        with patch('os.path.exists') as mock_exists:
            mock_exists.return_value = False
            
            result = await file_manager.delete_file(file_id)
            
            assert result is False
    
    def test_get_file_info(self, file_manager):
        """测试获取文件信息"""
        file_id = "test_file_1"
        
        with patch('os.path.exists') as mock_exists:
            mock_exists.return_value = True
            with patch('os.path.getsize') as mock_size:
                mock_size.return_value = 1024
                with patch('os.path.getmtime') as mock_mtime:
                    mock_mtime.return_value = 1640995200.0  # 2022-01-01 00:00:00
                    
                    info = file_manager.get_file_info(file_id)
                    
                    assert info['size'] == 1024
                    assert info['modified_time'] == 1640995200.0
                    assert info['exists'] is True
    
    def test_list_files(self, file_manager):
        """测试列出文件"""
        with patch('os.listdir') as mock_listdir:
            mock_listdir.return_value = ['file1.txt', 'file2.pdf', 'subdir']
            with patch('os.path.isfile') as mock_isfile:
                mock_isfile.side_effect = lambda x: x.endswith(('.txt', '.pdf'))
                
                files = file_manager.list_files()
                
                assert 'file1.txt' in files
                assert 'file2.pdf' in files
                assert 'subdir' not in files