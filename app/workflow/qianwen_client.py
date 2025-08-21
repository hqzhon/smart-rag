"""
千问API客户端 - 用于embedding和rerank
"""
import asyncio
import aiohttp
import json
from typing import List, Dict, Any, Optional, Tuple
import logging
import numpy as np

from app.core.config import get_settings
from app.utils.logger import setup_logger

logger = setup_logger(__name__)

class QianwenClient:
    """千问API客户端"""
    
    def __init__(self):
        """初始化千问客户端"""
        self.settings = get_settings()
        self.api_key = self.settings.qianwen_api_key
        self.base_url = self.settings.qianwen_base_url
        self.embedding_model = self.settings.qianwen_embedding_model
        self.rerank_model = self.settings.qianwen_rerank_model
        
        if not self.api_key:
            raise ValueError("QIANWEN_API_KEY未设置")
        
        if not self.base_url:
            raise ValueError("QIANWEN_BASE_URL未设置")
        
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        
        # 连接池配置 - 延迟初始化
        self.connector = None
        self.session = None
        
        logger.info(f"千问客户端初始化完成")
        logger.info(f"Embedding模型: {self.embedding_model}")
        logger.info(f"Rerank模型: {self.rerank_model}")
    
    async def __aenter__(self):
        """异步上下文管理器入口"""
        if self.connector is None:
            self.connector = aiohttp.TCPConnector(
                limit=150,  # 增加总连接数限制
                limit_per_host=30,  # 增加每个主机的连接数限制
                ttl_dns_cache=600,  # 增加DNS缓存时间
                use_dns_cache=True,
                enable_cleanup_closed=True,  # 启用清理已关闭的连接
                keepalive_timeout=60,  # 保持连接时间
            )
        
        self.session = aiohttp.ClientSession(
            connector=self.connector,
            headers=self.headers,
            timeout=aiohttp.ClientTimeout(
                total=90,  # 增加总超时时间
                connect=20,  # 连接超时
                sock_read=45  # 读取超时
            )
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        if hasattr(self, 'session') and self.session:
            await self.session.close()
        if self.connector:
            await self.connector.close()
    
    async def get_embeddings(
        self,
        texts: List[str],
        model: Optional[str] = None,
        dimensions: Optional[int] = None,
        encoding_format: str = "float"
    ) -> List[List[float]]:
        """获取文本embeddings"""
        try:
            if not texts:
                return []
            
            model_name = model or self.embedding_model
            if not model_name:
                raise ValueError("未指定embedding模型")
            
            # 按照千问OpenAI兼容模式的格式构建请求
            payload = {
                "model": model_name,
                "input": texts,
                "encoding_format": encoding_format
            }
            
            # 添加维度参数（仅text-embedding-v3和v4支持）
            if dimensions is not None:
                payload["dimensions"] = dimensions
            
            # 使用千问OpenAI兼容模式的URL
            url = f"{self.base_url}/compatible-mode/v1/embeddings"
            
            if not hasattr(self, 'session') or not self.session or self.session.closed:
                await self.__aenter__()
            
            async with self.session.post(url, json=payload) as response:
                if response.status != 200:
                    error_text = await response.text()
                    logger.error(f"千问embedding API错误: {response.status} - {error_text}")
                    raise Exception(f"Embedding API调用失败: {response.status}")
                
                result = await response.json()
                
                if 'data' not in result:
                    raise Exception("API响应格式错误：缺少data字段")
                
                embeddings = []
                for item in result['data']:
                    if 'embedding' in item:
                        embeddings.append(item['embedding'])
                    else:
                        raise Exception("API响应格式错误：缺少embedding字段")
                
                logger.debug(f"获取到{len(embeddings)}个embeddings")
                return embeddings
                
        except Exception as e:
            logger.error(f"获取embeddings失败: {str(e)}")
            raise
    
    async def get_single_embedding(
        self, 
        text: str, 
        model: Optional[str] = None,
        dimensions: Optional[int] = None,
        encoding_format: str = "float"
    ) -> List[float]:
        """获取单个文本的embedding"""
        embeddings = await self.get_embeddings([text], model, dimensions, encoding_format)
        return embeddings[0] if embeddings else []
    
    async def rerank_documents(
        self,
        query: str,
        documents: List[str],
        model: Optional[str] = None,
        top_k: Optional[int] = None
    ) -> List[Tuple[int, float]]:
        """对文档进行重排序"""
        try:
            if not documents:
                return []
            
            model_name = model or self.rerank_model
            if not model_name:
                raise ValueError("未指定rerank模型")
            
            # 按照千问API的正确格式构建请求
            payload = {
                "model": model_name,
                "input": {
                    "query": query,
                    "documents": documents
                },
                "parameters": {
                    "return_documents": True
                }
            }
            
            if top_k is not None:
                payload["parameters"]["top_n"] = top_k
            
            # 使用千问rerank的正确URL
            url = f"{self.base_url}/api/v1/services/rerank/text-rerank/text-rerank"
            
            if not hasattr(self, 'session') or not self.session or self.session.closed:
                await self.__aenter__()
            
            async with self.session.post(url, json=payload) as response:
                if response.status != 200:
                    error_text = await response.text()
                    logger.error(f"千问rerank API错误: {response.status} - {error_text}")
                    raise Exception(f"Rerank API调用失败: {response.status}")
                
                result = await response.json()
                
                # 千问rerank API的响应格式
                if 'output' not in result:
                    raise Exception("API响应格式错误：缺少output字段")
                
                output = result['output']
                if 'results' not in output:
                    raise Exception("API响应格式错误：缺少output.results字段")
                
                # 解析重排序结果
                rerank_results = []
                for item in output['results']:
                    if 'index' in item and 'relevance_score' in item:
                        rerank_results.append((item['index'], item['relevance_score']))
                    else:
                        raise Exception("API响应格式错误：缺少index或relevance_score字段")
                
                logger.debug(f"重排序完成，返回{len(rerank_results)}个结果")
                return rerank_results
                
        except Exception as e:
            logger.error(f"文档重排序失败: {str(e)}")
            raise
    
    async def batch_embeddings(
        self,
        texts: List[str],
        batch_size: int = 10,  # 千问API限制批量大小不能超过10
        model: Optional[str] = None,
        dimensions: Optional[int] = None,
        encoding_format: str = "float"
    ) -> List[List[float]]:
        """批量获取embeddings"""
        try:
            if not texts:
                return []
            
            all_embeddings = []
            
            # 分批处理
            for i in range(0, len(texts), batch_size):
                batch_texts = texts[i:i + batch_size]
                batch_embeddings = await self.get_embeddings(batch_texts, model, dimensions, encoding_format)
                all_embeddings.extend(batch_embeddings)
                
                # 避免请求过于频繁
                if i + batch_size < len(texts):
                    await asyncio.sleep(0.1)
            
            logger.info(f"批量处理完成，共获取{len(all_embeddings)}个embeddings")
            return all_embeddings
            
        except Exception as e:
            logger.error(f"批量获取embeddings失败: {str(e)}")
            raise
    
    async def health_check(self) -> bool:
        """健康检查"""
        try:
            url = f"{self.base_url}/v1/models"
            
            if not hasattr(self, 'session') or not self.session or self.session.closed:
                await self.__aenter__()
            
            async with self.session.get(url) as response:
                if response.status == 200:
                    result = await response.json()
                    logger.info("千问API服务健康检查通过")
                    return True
                else:
                    logger.warning(f"千问API服务健康检查失败: {response.status}")
                    return False
                    
        except Exception as e:
            logger.error(f"千问API健康检查异常: {str(e)}")
            return False

# 全局客户端实例字典，按事件循环存储
_qianwen_clients = {}

async def get_qianwen_client() -> QianwenClient:
    """获取千问客户端实例"""
    import threading
    
    # 获取当前线程ID作为键
    thread_id = threading.get_ident()
    
    # 检查现有客户端是否有效
    if thread_id in _qianwen_clients:
        client = _qianwen_clients[thread_id]
        # 检查会话是否仍然有效
        if hasattr(client, 'session') and client.session and not client.session.closed:
            return client
        else:
            # 会话已关闭，清理并重新创建
            try:
                await client.__aexit__(None, None, None)
            except:
                pass
            del _qianwen_clients[thread_id]
    
    # 创建新的客户端实例
    client = QianwenClient()
    _qianwen_clients[thread_id] = client
    return client

async def cleanup_qianwen_client():
    """清理千问客户端"""
    import threading
    
    thread_id = threading.get_ident()
    if thread_id in _qianwen_clients:
        client = _qianwen_clients[thread_id]
        try:
            await client.__aexit__(None, None, None)
        except:
            pass
        del _qianwen_clients[thread_id]
