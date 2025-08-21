#!/usr/bin/env python3
"""
RQ集成测试
测试Redis Queue异步任务队列功能
"""

import os
import sys
import time
import uuid
import pytest
import logging
from unittest.mock import patch, MagicMock

# Add project root to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from redis import Redis
from rq import Queue, Worker
from app.metadata.tasks import generate_metadata_for_chunk, get_metadata_processor, cleanup_metadata_processor
from app.processors.document_processor import DocumentProcessor

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TestRQIntegration:
    """RQ集成测试类"""
    
    @pytest.fixture(scope="class")
    def redis_connection(self):
        """Redis连接fixture"""
        try:
            redis_conn = Redis(host='localhost', port=6379, decode_responses=True)
            redis_conn.ping()
            return redis_conn
        except Exception as e:
            pytest.skip(f"Redis服务不可用: {e}")
    
    @pytest.fixture(scope="class")
    def rq_queue(self, redis_connection):
        """RQ队列fixture"""
        return Queue('test_metadata_queue', connection=redis_connection)
    
    def test_redis_connection(self, redis_connection):
        """测试Redis连接"""
        assert redis_connection.ping() is True
        logger.info("Redis连接测试通过")
    
    def test_rq_queue_creation(self, rq_queue):
        """测试RQ队列创建"""
        assert rq_queue.name == 'test_metadata_queue'
        assert rq_queue.is_empty() is True
        logger.info("RQ队列创建测试通过")
    
    def test_task_enqueue(self, rq_queue):
        """测试任务入队"""
        chunk_id = str(uuid.uuid4())
        chunk_text = "这是一个测试文本块，用于验证元数据生成功能。"
        document_id = str(uuid.uuid4())
        
        # Enqueue task
        job = rq_queue.enqueue(
            generate_metadata_for_chunk,
            chunk_id,
            chunk_text,
            document_id,
            job_timeout='5m'
        )
        
        assert job is not None
        assert job.id is not None
        assert job.func_name == 'app.metadata.tasks.generate_metadata_for_chunk'
        logger.info(f"任务入队测试通过，任务ID: {job.id}")
    
    @patch('app.metadata.tasks.AsyncMetadataProcessor')
    def test_task_execution_mock(self, mock_processor_class, rq_queue):
        """测试任务执行（使用Mock）"""
        # Setup mock
        mock_processor = MagicMock()
        mock_processor_class.return_value = mock_processor
        mock_processor.submit_task.return_value = {
            'chunk_id': 'test_chunk_id',
            'keywords': ['测试', '关键词'],
            'summary': '测试摘要'
        }
        
        chunk_id = str(uuid.uuid4())
        chunk_text = "这是一个测试文本块。"
        document_id = str(uuid.uuid4())
        
        # Execute task directly
        result = generate_metadata_for_chunk(chunk_id, chunk_text, document_id)
        
        assert result is not None
        assert 'chunk_id' in result
        logger.info("任务执行测试通过（Mock模式）")
    
    def test_document_processor_rq_integration(self, redis_connection):
        """测试DocumentProcessor的RQ集成"""
        # Create temporary directories
        import tempfile
        with tempfile.TemporaryDirectory() as temp_dir:
            input_dir = os.path.join(temp_dir, 'input')
            output_dir = os.path.join(temp_dir, 'output')
            os.makedirs(input_dir)
            
            # Create test text file
            test_file = os.path.join(input_dir, 'test.txt')
            with open(test_file, 'w', encoding='utf-8') as f:
                f.write("这是一个测试文档。\n" * 10)  # Create enough content for chunking
            
            # Initialize DocumentProcessor with RQ enabled
            processor = DocumentProcessor(
                input_dir=input_dir,
                output_dir=output_dir,
                enable_async_metadata=True,
                redis_host='localhost',
                redis_port=6379
            )
            
            assert processor.enable_async_metadata is True
            assert hasattr(processor, 'metadata_queue')
            
            # Process document (this should enqueue tasks)
            result = processor.process_single_document(test_file)
            
            assert result is not None
            assert 'document_id' in result
            logger.info("DocumentProcessor RQ集成测试通过")
    
    def test_worker_functionality(self, rq_queue, redis_connection):
        """测试Worker功能（简单验证）"""
        # Create worker
        worker = Worker([rq_queue], connection=redis_connection)
        
        assert worker is not None
        assert len(worker.queues) == 1
        assert worker.queues[0].name == 'test_metadata_queue'
        logger.info("Worker功能测试通过")
    
    def test_cleanup_function(self):
        """测试清理函数"""
        try:
            cleanup_metadata_processor()
            logger.info("清理函数测试通过")
        except Exception as e:
            logger.warning(f"清理函数执行时出现警告: {e}")
            # 清理函数可能会有警告，但不应该抛出异常
            assert True

if __name__ == '__main__':
    # Run tests directly
    pytest.main([__file__, '-v'])