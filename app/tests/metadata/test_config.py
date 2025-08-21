"""测试配置"""

import os
from typing import Dict, Any

# 测试配置字典
TEST_CONFIG: Dict[str, Any] = {
    # 基础配置
    "app_name": "Smart RAG Test",
    "app_version": "1.0.0",
    "debug": True,
    "log_level": "DEBUG",
    "environment": "test",
    
    # API配置
    "api_host": "localhost",
    "api_port": 8000,
    "host": "localhost",
    "port": 8000,
    
    # 千问API配置
    "qianwen_api_key": os.getenv("QIANWEN_API_KEY", "test-api-key"),
    "qianwen_base_url": "https://dashscope.aliyuncs.com",
    "qianwen_embedding_model": "text-embedding-v4",
    "qianwen_rerank_model": "gte-rerank-v2",
    
    # 数据库配置
    "database_url": "sqlite:///test.db",
    "mysql_host": "localhost",
    "mysql_port": 3306,
    "mysql_user": "test",
    "mysql_password": "test",
    "mysql_database": "test_db",
    
    # Redis配置
    "redis_url": "redis://localhost:6379/0",
    
    # 向量数据库配置
    "chroma_persist_directory": "/tmp/test_chroma",
    "chroma_db_dir": "/tmp/test_chroma",
    "chroma_collection_name": "test_collection",
    
    # 文件处理配置
    "max_file_size": 10485760,  # 10MB
    "allowed_extensions": ".pdf,.txt,.docx,.md",
    "upload_dir": "/tmp/test_uploads",
    "processed_dir": "/tmp/test_processed",
    "upload_directory": "/tmp/test_uploads",
    "processed_directory": "/tmp/test_processed",
    
    # 安全配置
    "secret_key": "test-secret-key",
    "jwt_secret_key": "test-jwt-secret",
    "jwt_algorithm": "HS256",
    "jwt_expire_minutes": 30,
    "access_token_expire_minutes": 30,
    
    # RAG配置
    "retrieval_top_k": 10,
    "rerank_top_k": 5,
    "chunk_size": 1000,
    "chunk_overlap": 200,
    "max_tokens": 2000,
    "temperature": 0.7,
    
    # 语义分块配置
    "enable_semantic_chunking": True,
    "semantic_threshold": 0.75,
    "max_semantic_chunk_size": 2000,
    "min_chunk_size": 100,
    "chunking_batch_size": 10,
    "embedding_cache_enabled": True,
    "embedding_cache_ttl": 3600,
    "chunking_separators": "\n##SECTION_START_,\n\n,。\n,.\n\n",
    
    # 模型配置
    "embedding_model": "text-embedding-v4",
    "llm_model": "qwen-turbo",
    "reranker_model": "gte-rerank-v2",
    "embedding_device": "cpu",
    
    # 性能配置
    "max_concurrent_requests": 10,
    "request_timeout": 30,
    "cache_ttl": 3600,
    
    # 日志配置
    "log_directory": "/tmp/test_logs",
    
    # Deepseek配置（可选）
    "deepseek_api_key": None,
    "deepseek_base_url": "https://api.deepseek.com",
    "deepseek_model": "deepseek-chat",
    
    # OpenAI配置（可选）
    "openai_api_key": None,
    "openai_model": None,
    "openai_base_url": None,
    "openai_embedding_model": None,
}

def get_test_config() -> Dict[str, Any]:
    """获取测试配置"""
    return TEST_CONFIG.copy()

def set_test_env_vars():
    """设置测试环境变量"""
    for key, value in TEST_CONFIG.items():
        if value is not None:
            os.environ[key.upper()] = str(value)

def clear_test_env_vars():
    """清理测试环境变量"""
    for key in TEST_CONFIG.keys():
        env_key = key.upper()
        if env_key in os.environ:
            del os.environ[env_key]