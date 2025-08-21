"""
应用配置管理
"""

import os
from typing import List, Optional
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """应用配置类"""
    
    # 基础配置
    app_name: str = Field(env="APP_NAME", description="应用名称")
    app_version: str = Field(env="APP_VERSION", description="应用版本")
    debug: bool = Field(env="DEBUG", description="调试模式")
    log_level: str = Field(env="LOG_LEVEL", description="日志级别")
    environment: str = Field(env="ENVIRONMENT", description="运行环境")
    
    # API配置
    api_host: str = Field(env="API_HOST", description="API主机")
    api_port: int = Field(env="API_PORT", description="API端口")
    host: str = Field(env="HOST", description="主机地址")
    port: int = Field(env="PORT", description="端口号")
    
    # Deepseek配置
    deepseek_api_key: Optional[str] = Field(env="DEEPSEEK_API_KEY", description="Deepseek API密钥")
    deepseek_base_url: str = Field(env="DEEPSEEK_BASE_URL", description="Deepseek API基础URL")
    deepseek_model: str = Field(env="DEEPSEEK_MODEL", description="Deepseek模型名称")
    
    # 千问API配置
    qianwen_api_key: str = Field(env="QIANWEN_API_KEY", description="千问API密钥")
    qianwen_base_url: str = Field(env="QIANWEN_BASE_URL", default="https://dashscope.aliyuncs.com", description="千问API基础URL")
    qianwen_embedding_model: str = Field(env="QIANWEN_EMBEDDING_MODEL", default="text-embedding-v4", description="千问Embedding模型")
    qianwen_rerank_model: str = Field(env="QIANWEN_RERANK_MODEL", default="gte-rerank-v2", description="千问Rerank模型")
    
    # 数据库配置
    database_url: str = Field(env="DATABASE_URL", description="数据库URL")
    mysql_host: str = Field(env="MYSQL_HOST", description="MySQL主机")
    mysql_port: int = Field(env="MYSQL_PORT", description="MySQL端口")
    mysql_user: str = Field(env="MYSQL_USER", description="MySQL用户名")
    mysql_password: str = Field(env="MYSQL_PASSWORD", description="MySQL密码")
    mysql_database: str = Field(env="MYSQL_DATABASE", description="MySQL数据库名")
    
    # Redis配置
    redis_url: str = Field(env="REDIS_URL", description="Redis连接URL")
    
    # 向量数据库配置
    chroma_persist_directory: str = Field(env="CHROMA_PERSIST_DIRECTORY", description="ChromaDB持久化目录")
    chroma_db_dir: str = Field(env="CHROMA_DB_DIR", description="ChromaDB目录")
    chroma_collection_name: str = Field(env="CHROMA_COLLECTION_NAME", description="ChromaDB集合名称")
    
    # 文件上传配置
    max_file_size: int = Field(env="MAX_FILE_SIZE", description="最大文件大小(字节)")
    allowed_extensions: str = Field(env="ALLOWED_EXTENSIONS", description="允许的文件扩展名")
    upload_dir: str = Field(env="UPLOAD_DIR", description="上传目录")
    processed_dir: str = Field(env="PROCESSED_DIR", description="处理后文件目录")
    upload_directory: str = Field(env="UPLOAD_DIRECTORY", description="上传目录别名")
    processed_directory: str = Field(env="PROCESSED_DIRECTORY", description="处理后文件目录别名")
    
    # JWT和安全配置
    secret_key: str = Field(env="SECRET_KEY", description="应用密钥")
    jwt_secret_key: str = Field(env="JWT_SECRET_KEY", description="JWT密钥")
    jwt_algorithm: str = Field(env="JWT_ALGORITHM", description="JWT算法")
    jwt_expire_minutes: int = Field(env="JWT_EXPIRE_MINUTES", description="JWT过期时间(分钟)")
    access_token_expire_minutes: int = Field(env="ACCESS_TOKEN_EXPIRE_MINUTES", description="访问令牌过期时间(分钟)")
    
    # 检索和生成配置
    retrieval_top_k: int = Field(env="RETRIEVAL_TOP_K", description="检索Top-K数量")
    rerank_top_k: int = Field(env="RERANK_TOP_K", description="重排序Top-K数量")
    chunk_size: int = Field(env="CHUNK_SIZE", description="文本分块大小")
    chunk_overlap: int = Field(env="CHUNK_OVERLAP", description="文本分块重叠")
    max_tokens: int = Field(env="MAX_TOKENS", description="最大生成令牌数")
    temperature: float = Field(env="TEMPERATURE", description="生成温度")
    
    # 智能分块配置
    enable_semantic_chunking: bool = Field(env="ENABLE_SEMANTIC_CHUNKING", default=True, description="启用语义分块")
    semantic_threshold: float = Field(env="SEMANTIC_THRESHOLD", default=0.75, description="语义相似度阈值")
    max_semantic_chunk_size: int = Field(env="MAX_SEMANTIC_CHUNK_SIZE", default=2000, description="语义分块最大大小")
    min_chunk_size: int = Field(env="MIN_CHUNK_SIZE", default=100, description="最小分块大小")
    chunking_batch_size: int = Field(env="CHUNKING_BATCH_SIZE", default=10, description="分块批处理大小")
    embedding_cache_enabled: bool = Field(env="EMBEDDING_CACHE_ENABLED", default=True, description="启用嵌入缓存")
    embedding_cache_ttl: int = Field(env="EMBEDDING_CACHE_TTL", default=3600, description="嵌入缓存TTL(秒)")
    chunking_separators: str = Field(env="CHUNKING_SEPARATORS", default="\n##SECTION_START_,\n\n,。\n,.\n\n", description="分块分隔符(逗号分隔)")
    
    # 模型配置
    embedding_model: str = Field(env="EMBEDDING_MODEL", description="嵌入模型名称")
    llm_model: str = Field(env="LLM_MODEL", description="LLM模型名称")
    reranker_model: str = Field(env="RERANKER_MODEL", description="重排序模型名称")
    embedding_device: str = Field(env="EMBEDDING_DEVICE", description="嵌入模型设备")
    
    # 性能配置
    max_concurrent_requests: int = Field(env="MAX_CONCURRENT_REQUESTS", description="最大并发请求数")
    request_timeout: int = Field(env="REQUEST_TIMEOUT", description="请求超时时间(秒)")
    cache_ttl: int = Field(env="CACHE_TTL", description="缓存生存时间(秒)")
    
    # 日志配置
    log_directory: str = Field(env="LOG_DIRECTORY", description="日志目录")
    
    # OpenAI配置（可选）
    openai_api_key: Optional[str] = Field(env="OPENAI_API_KEY", default=None, description="OpenAI API密钥")
    openai_model: Optional[str] = Field(env="OPENAI_MODEL", default=None, description="OpenAI模型")
    openai_base_url: Optional[str] = Field(env="OPENAI_BASE_URL", default=None, description="OpenAI API基础URL")
    openai_embedding_model: Optional[str] = Field(env="OPENAI_EMBEDDING_MODEL", default=None, description="OpenAI嵌入模型")
    
    @property
    def allowed_extensions_list(self) -> List[str]:
        """将允许的文件扩展名字符串转换为列表"""
        return [ext.strip() for ext in self.allowed_extensions.split(',') if ext.strip()]
    
    @property
    def chunking_separators_list(self) -> List[str]:
        """将分块分隔符字符串转换为列表"""
        return [sep.strip() for sep in self.chunking_separators.split(',') if sep.strip()]
    
    class Config:
        env_file = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), ".env")
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "ignore"  # 忽略额外字段


# 全局配置实例
_settings = None


def get_settings() -> Settings:
    """获取配置实例（单例模式）"""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


def reload_settings():
    """重新加载配置"""
    global _settings
    _settings = None
    return get_settings()


# 导出配置实例
settings = get_settings()