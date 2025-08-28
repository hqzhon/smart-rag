"""千问API客户端 - 用于元数据摘要生成"""

import asyncio
import aiohttp
import json
from typing import Dict, Any, Optional, List
import logging
from datetime import datetime

from app.core.config import get_settings
from app.utils.logger import setup_logger

logger = setup_logger(__name__)

class QianwenClient:
    """千问API客户端 - 专用于元数据摘要生成"""
    
    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None):
        """初始化千问客户端
        
        Args:
            api_key: API密钥，如果不提供则从配置中获取
            base_url: API基础URL，如果不提供则从配置中获取
        """
        self.settings = get_settings()
        self.api_key = api_key or self.settings.qianwen_api_key
        self.base_url = base_url or self.settings.qianwen_base_url
        
        # 默认模型配置
        self.default_model = "qwen2.5-1.5b-instruct"
        self.max_tokens = 2048
        self.temperature = 0.3
        
        if not self.api_key:
            raise ValueError("QIANWEN_API_KEY未设置")
        
        if not self.base_url:
            raise ValueError("QIANWEN_BASE_URL未设置")
        
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        
        # 连接池配置
        self.connector = None
        self.session = None
        
        # 请求统计
        self.request_count = 0
        self.error_count = 0
        self.total_tokens = 0
        
        logger.info(f"千问客户端初始化完成 - 模型: {self.default_model}")
    
    async def __aenter__(self):
        """异步上下文管理器入口"""
        # 每次都重新创建connector和session，避免事件循环冲突
        if self.connector:
            try:
                await self.connector.close()
            except:
                pass
        
        self.connector = aiohttp.TCPConnector(
            limit=20,
            limit_per_host=5,
            ttl_dns_cache=300,
            use_dns_cache=True,
            keepalive_timeout=30
        )
        
        if self.session and not self.session.closed:
            try:
                await self.session.close()
            except:
                pass
        
        self.session = aiohttp.ClientSession(
            connector=self.connector,
            headers=self.headers,
            timeout=aiohttp.ClientTimeout(total=60)  # 文本生成可能需要更长时间
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        if hasattr(self, 'session') and self.session:
            await self.session.close()
        if self.connector:
            await self.connector.close()
    
    async def generate_text(
        self,
        prompt: str,
        model: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        system_prompt: Optional[str] = None
    ) -> str:
        """生成文本
        
        Args:
            prompt: 用户提示词
            model: 模型名称，默认使用qwen2.5-1.5b-instruct
            max_tokens: 最大token数
            temperature: 温度参数，控制随机性
            system_prompt: 系统提示词
            
        Returns:
            生成的文本内容
        """
        try:
            model_name = model or self.default_model
            max_tokens_val = max_tokens or self.max_tokens
            temperature_val = temperature or self.temperature
            
            # 构建消息列表
            messages = []
            if system_prompt:
                messages.append({
                    "role": "system",
                    "content": system_prompt
                })
            
            messages.append({
                "role": "user",
                "content": prompt
            })
            
            # 构建请求payload
            payload = {
                "model": model_name,
                "messages": messages,
                "max_tokens": max_tokens_val,
                "temperature": temperature_val,
                "stream": False
            }
            
            # 使用千问OpenAI兼容模式的URL
            url = f"{self.base_url}/compatible-mode/v1/chat/completions"
            
            if not hasattr(self, 'session') or not self.session or self.session.closed:
                await self.__aenter__()
            
            self.request_count += 1
            start_time = datetime.now()
            
            async with self.session.post(url, json=payload) as response:
                if response.status != 200:
                    error_text = await response.text()
                    self.error_count += 1
                    logger.error(f"千问文本生成API错误: {response.status} - {error_text}")
                    raise Exception(f"文本生成API调用失败: {response.status} - {error_text}")
                
                result = await response.json()
                
                # 解析响应
                if 'choices' not in result or not result['choices']:
                    raise Exception("API响应格式错误：缺少choices字段")
                
                choice = result['choices'][0]
                if 'message' not in choice or 'content' not in choice['message']:
                    raise Exception("API响应格式错误：缺少message.content字段")
                
                generated_text = choice['message']['content'].strip()
                
                # 统计token使用量
                if 'usage' in result:
                    usage = result['usage']
                    self.total_tokens += usage.get('total_tokens', 0)
                
                # 记录请求时间
                duration = (datetime.now() - start_time).total_seconds()
                
                logger.debug(f"文本生成完成 - 耗时: {duration:.2f}s, 长度: {len(generated_text)}")
                return generated_text
                
        except Exception as e:
            self.error_count += 1
            logger.error(f"文本生成失败: {str(e)}")
            raise
    
    async def generate_summary(
        self,
        text: str,
        max_length: int = 200,
        language: str = "中文"
    ) -> str:
        """生成文本摘要
        
        Args:
            text: 待摘要的文本
            max_length: 摘要最大长度
            language: 摘要语言
            
        Returns:
            生成的摘要
        """
        system_prompt = f"""你是一个专业的文本摘要生成助手。请根据以下要求生成摘要：
1. 摘要语言：{language}
2. 摘要长度：不超过{max_length}字
3. 保持原文的核心信息和关键观点
4. 使用简洁、准确的语言
5. 如果是医学文本，请保留重要的医学术语
6. 直接输出摘要内容，不要添加额外的说明"""
        
        prompt = f"请为以下文本生成摘要：\n\n{text}"
        
        return await self.generate_text(
            prompt=prompt,
            system_prompt=system_prompt,
            max_tokens=max_length + 100,  # 留一些余量
            temperature=0.3
        )
    
    async def batch_generate_summaries(
        self,
        texts: List[str],
        max_length: int = 200,
        language: str = "中文",
        batch_delay: float = 0.5
    ) -> List[str]:
        """批量生成摘要
        
        Args:
            texts: 待摘要的文本列表
            max_length: 摘要最大长度
            language: 摘要语言
            batch_delay: 批次间延迟（秒）
            
        Returns:
            摘要列表
        """
        summaries = []
        
        for i, text in enumerate(texts):
            try:
                summary = await self.generate_summary(text, max_length, language)
                summaries.append(summary)
                
                # 避免请求过于频繁
                if i < len(texts) - 1:
                    await asyncio.sleep(batch_delay)
                    
            except Exception as e:
                logger.error(f"批量摘要生成失败 (索引 {i}): {str(e)}")
                summaries.append("")  # 失败时添加空摘要
        
        logger.info(f"批量摘要生成完成: {len([s for s in summaries if s])}/{len(texts)}")
        return summaries
    
    async def health_check(self) -> bool:
        """健康检查"""
        try:
            # 使用简单的文本生成测试API可用性
            test_prompt = "请说'健康检查通过'"
            result = await self.generate_text(
                prompt=test_prompt,
                max_tokens=10,
                temperature=0
            )
            
            if result and "健康检查" in result:
                logger.info("千问API健康检查通过")
                return True
            else:
                logger.warning(f"千问API健康检查异常响应: {result}")
                return False
                
        except Exception as e:
            logger.error(f"千问API健康检查失败: {str(e)}")
            return False
    
    def get_stats(self) -> Dict[str, Any]:
        """获取客户端统计信息"""
        return {
            "total_requests": self.request_count,
            "request_count": self.request_count,
            "error_count": self.error_count,
            "success_rate": (self.request_count - self.error_count) / max(self.request_count, 1),
            "total_tokens": self.total_tokens,
            "model": self.default_model
        }
    
    def reset_stats(self):
        """重置统计信息"""
        self.request_count = 0
        self.error_count = 0
        self.total_tokens = 0
        logger.info("客户端统计信息已重置")
    
    async def close(self):
        """Close the HTTP session"""
        if hasattr(self, 'session') and self.session and not self.session.closed:
            await self.session.close()
        if self.connector:
            await self.connector.close()


# 全局客户端实例管理
_metadata_qianwen_clients = {}

async def get_metadata_qianwen_client() -> QianwenClient:
    """获取元数据专用的千问客户端实例"""
    import threading
    
    thread_id = threading.get_ident()
    
    # 检查现有客户端是否有效
    if thread_id in _metadata_qianwen_clients:
        client = _metadata_qianwen_clients[thread_id]
        # 检查会话是否仍然有效，以及是否在同一个事件循环中
        try:
            current_loop = asyncio.get_running_loop()
            if (hasattr(client, 'session') and client.session and 
                not client.session.closed and 
                hasattr(client, '_loop') and client._loop == current_loop):
                return client
        except RuntimeError:
            # 没有运行中的事件循环
            pass
        
        # 会话已关闭或事件循环不匹配，清理并重新创建
        try:
            await client.__aexit__(None, None, None)
        except:
            pass
        del _metadata_qianwen_clients[thread_id]
    
    # 创建新的客户端实例
    client = QianwenClient()
    # 记录当前事件循环
    try:
        client._loop = asyncio.get_running_loop()
    except RuntimeError:
        client._loop = None
    
    _metadata_qianwen_clients[thread_id] = client
    return client

async def cleanup_metadata_qianwen_client():
    """清理元数据千问客户端"""
    import threading
    
    thread_id = threading.get_ident()
    if thread_id in _metadata_qianwen_clients:
        client = _metadata_qianwen_clients[thread_id]
        try:
            await client.__aexit__(None, None, None)
        except:
            pass
        del _metadata_qianwen_clients[thread_id]