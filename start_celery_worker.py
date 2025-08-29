#!/usr/bin/env python3
"""
Celery Worker启动脚本 - MVP版本
简化的Worker启动脚本，用于处理元数据生成任务
"""

import os
import sys
import logging
from celery import Celery
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 设置环境变量
os.environ.setdefault('CELERY_CONFIG_MODULE', 'app.celery_app')

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

def main():
    """启动Celery Worker"""
    try:
        # 导入Celery应用
        from app.celery_app import celery_app
        
        logger.info("Starting Celery Worker for metadata processing...")
        logger.info(f"Redis URL: {os.getenv('REDIS_URL', 'redis://localhost:6379/0')}")
        debug = os.getenv("DEBUG", "true").lower() == "true"
        
        # 启动Worker
        # 参数说明:
        # --loglevel=info: 设置日志级别
        # --concurrency=2: 设置并发数为2（MVP版本保持简单）
        # --queues=metadata: 只处理metadata队列的任务
        celery_app.worker_main([
            'worker',
            '--loglevel=' + ('debug' if debug else 'info'),
            '--concurrency=2',
            '--queues=metadata',
            '--pool=prefork'
        ])
        
    except KeyboardInterrupt:
        logger.info("Worker停止中...")
    except Exception as e:
        logger.error(f"Worker启动失败: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()