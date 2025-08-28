from celery import Celery
import os
import logging
from logging.handlers import RotatingFileHandler

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('celery')

# Add file handler for Celery logs
file_handler = RotatingFileHandler(
    'logs/celery.log',
    maxBytes=10*1024*1024,  # 10MB
    backupCount=5
)
file_handler.setLevel(logging.INFO)
formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

# Create Celery app with minimal configuration
app = Celery('smart_rag')

# Basic configuration
app.conf.update(
    broker_url=f"redis://{os.getenv('REDIS_HOST', 'localhost')}:{os.getenv('REDIS_PORT', 6379)}/0",
    result_backend=f"redis://{os.getenv('REDIS_HOST', 'localhost')}:{os.getenv('REDIS_PORT', 6379)}/0",
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minutes
    task_soft_time_limit=25 * 60,  # 25 minutes
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    worker_disable_rate_limits=True,
    # Use threads instead of processes to avoid macOS fork issues
    worker_pool='threads',
    worker_concurrency=2,
)

# Import tasks to register them
try:
    from app.metadata import celery_tasks
except ImportError as e:
    print(f"Warning: Could not import celery_tasks: {e}")

# Auto-discover tasks from celery_tasks module
app.autodiscover_tasks(['app.metadata.celery_tasks'])

# Export the app instance
celery_app = app

if __name__ == '__main__':
    app.start()