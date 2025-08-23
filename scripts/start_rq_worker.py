#!/usr/bin/env python3
"""
RQ Worker启动脚本
用于启动Redis Queue工作进程来处理元数据生成任务

使用方法:
    python scripts/start_rq_worker.py
    
环境变量:
    REDIS_HOST: Redis服务器地址 (默认: localhost)
    REDIS_PORT: Redis服务器端口 (默认: 6379)
    WORKER_COUNT: 工作进程数量 (默认: 2)
"""

import os
import sys
import logging
import signal
import multiprocessing
from typing import List

# Add project root to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from redis import Redis
from rq import Worker, Queue
from app.metadata.tasks import generate_metadata_for_chunk, cleanup_metadata_processor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('logs/rq_worker.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

# Global worker processes list for cleanup
worker_processes: List[multiprocessing.Process] = []

def signal_handler(signum, frame):
    """Handle shutdown signals gracefully"""
    logger.info(f"接收到信号 {signum}，开始关闭工作进程...")
    
    # Terminate all worker processes
    for process in worker_processes:
        if process.is_alive():
            logger.info(f"终止工作进程 PID: {process.pid}")
            process.terminate()
    
    # Wait for processes to finish
    for process in worker_processes:
        process.join(timeout=10)
        if process.is_alive():
            logger.warning(f"强制杀死工作进程 PID: {process.pid}")
            process.kill()
    
    logger.info("所有工作进程已关闭")
    sys.exit(0)

def start_worker_process(worker_id: int, redis_host: str, redis_port: int):
    """启动单个工作进程"""
    try:
        # Setup Redis connection for RQ compatibility
        redis_conn = Redis(
            host=redis_host, 
            port=redis_port, 
            decode_responses=False,
            encoding='utf-8'
        )
        
        # Create queue
        queue = Queue('metadata_queue', connection=redis_conn)
        
        # Create worker
        worker = Worker([queue], connection=redis_conn, name=f'metadata_worker_{worker_id}')
        
        logger.info(f"工作进程 {worker_id} 已启动，连接到 Redis {redis_host}:{redis_port}")
        
        # Start worker (this will block)
        worker.work(with_scheduler=True)
        
    except KeyboardInterrupt:
        logger.info(f"工作进程 {worker_id} 接收到中断信号")
    except Exception as e:
        logger.error(f"工作进程 {worker_id} 发生错误: {e}")
    finally:
        # Cleanup resources
        try:
            cleanup_metadata_processor()
        except Exception as e:
            logger.error(f"清理资源时发生错误: {e}")
        logger.info(f"工作进程 {worker_id} 已退出")

def main():
    """主函数"""
    # Get configuration from environment variables
    redis_host = os.getenv('REDIS_HOST', 'localhost')
    redis_port = int(os.getenv('REDIS_PORT', '6379'))
    worker_count = int(os.getenv('WORKER_COUNT', '2'))
    
    logger.info(f"启动 RQ Worker 集群")
    logger.info(f"Redis 连接: {redis_host}:{redis_port}")
    logger.info(f"工作进程数量: {worker_count}")
    
    # Setup signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Create log directory
    os.makedirs('logs', exist_ok=True)
    
    # Test Redis connection
    try:
        redis_conn = Redis(
            host=redis_host, 
            port=redis_port, 
            decode_responses=True,
            encoding='utf-8',
            encoding_errors='ignore'
        )
        redis_conn.ping()
        logger.info("Redis 连接测试成功")
    except Exception as e:
        logger.error(f"无法连接到 Redis: {e}")
        sys.exit(1)
    
    # Start worker processes
    for i in range(worker_count):
        process = multiprocessing.Process(
            target=start_worker_process,
            args=(i + 1, redis_host, redis_port),
            name=f'RQWorker-{i + 1}'
        )
        process.start()
        worker_processes.append(process)
        logger.info(f"已启动工作进程 {i + 1}, PID: {process.pid}")
    
    # Wait for all processes to complete
    try:
        for process in worker_processes:
            process.join()
    except KeyboardInterrupt:
        logger.info("接收到中断信号，开始关闭...")
        signal_handler(signal.SIGINT, None)

if __name__ == '__main__':
    main()