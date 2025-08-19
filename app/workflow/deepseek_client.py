"""
Deepseek LLM客户端
"""
import os
import asyncio
import aiohttp
import json
from typing import Dict, Any, Optional, AsyncGenerator
from datetime import datetime
import logging

from app.core.config import get_settings
from app.utils.logger import setup_logger

logger = setup_logger(__name__)

class DeepseekClient:
    """Deepseek API客户端"""
    
    def __init__(self):
        """初始化Deepseek客户端"""
        self.settings = get_settings()
        self.api_key = self.settings.deepseek_api_key
        self.base_url = self.settings.deepseek_base_url
        self.model = self.settings.deepseek_model
        
        if not self.api_key:
            raise ValueError("DEEPSEEK_API_KEY未设置")
        
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        logger.info(f"Deepseek客户端初始化完成，模型: {self.model}")
    
    async def __aenter__(self):
        """异步上下文管理器入口"""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        pass
    
    async def chat_completion(
        self,
        messages: list,
        temperature: float = 0.7,
        max_tokens: int = 1000,
        stream: bool = False
    ) -> Dict[str, Any]:
        """聊天完成API调用"""
        try:
            payload = {
                "model": self.model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
                "stream": stream
            }
            
            url = f"{self.base_url}/chat/completions"
            
            # 每次调用都创建新的会话，避免会话关闭问题
            connector = aiohttp.TCPConnector(
                limit=100,
                limit_per_host=20,
                ttl_dns_cache=300,
                use_dns_cache=True,
            )
            
            async with aiohttp.ClientSession(
                connector=connector,
                headers=self.headers,
                timeout=aiohttp.ClientTimeout(total=60)
            ) as session:
                async with session.post(url, json=payload) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(f"Deepseek API错误: {response.status} - {error_text}")
                        raise Exception(f"API调用失败: {response.status}")
                    
                    result = await response.json()
                    logger.debug(f"Deepseek API响应: {result}")
                    return result
                
        except Exception as e:
            logger.error(f"Deepseek API调用失败: {str(e)}")
            raise
    
    async def stream_chat_completion(
        self,
        messages: list,
        temperature: float = 0.7,
        max_tokens: int = 1000
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """流式聊天完成"""
        try:
            payload = {
                "model": self.model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
                "stream": True
            }
            
            url = f"{self.base_url}/chat/completions"
            
            # 每次调用都创建新的会话
            connector = aiohttp.TCPConnector(
                limit=100,
                limit_per_host=20,
                ttl_dns_cache=300,
                use_dns_cache=True,
            )
            
            async with aiohttp.ClientSession(
                connector=connector,
                headers=self.headers,
                timeout=aiohttp.ClientTimeout(total=60)
            ) as session:
                async with session.post(url, json=payload) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(f"Deepseek流式API错误: {response.status} - {error_text}")
                        raise Exception(f"流式API调用失败: {response.status}")
                    
                    async for line in response.content:
                        line = line.decode('utf-8').strip()
                        if line.startswith('data: '):
                            data = line[6:]  # 移除 'data: ' 前缀
                            if data == '[DONE]':
                                break
                            try:
                                chunk = json.loads(data)
                                yield chunk
                            except json.JSONDecodeError:
                                continue
                            
        except Exception as e:
            logger.error(f"Deepseek流式API调用失败: {str(e)}")
            raise
    
    async def generate_response(
        self,
        prompt: str,
        context: str = "",
        temperature: float = 0.7,
        max_tokens: int = 1000
    ) -> str:
        """生成回答"""
        try:
            messages = []
            
            if context:
                messages.append({
                    "role": "system",
                    "content": f"基于以下医疗文档内容回答问题：\n\n{context}"
                })
            
            messages.append({
                "role": "user",
                "content": prompt
            })
            
            result = await self.chat_completion(
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens
            )
            
            if 'choices' in result and len(result['choices']) > 0:
                return result['choices'][0]['message']['content']
            else:
                raise Exception("API响应格式错误")
                
        except Exception as e:
            logger.error(f"生成回答失败: {str(e)}")
            raise
    
    async def generate_stream_response(
        self,
        prompt: str,
        context: str = "",
        temperature: float = 0.7,
        max_tokens: int = 1000
    ) -> AsyncGenerator[str, None]:
        """流式生成回答"""
        try:
            messages = []
            
            if context:
                messages.append({
                    "role": "system",
                    "content": f"基于以下医疗文档内容回答问题：\n\n{context}"
                })
            
            messages.append({
                "role": "user",
                "content": prompt
            })
            
            async for chunk in self.stream_chat_completion(
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens
            ):
                if 'choices' in chunk and len(chunk['choices']) > 0:
                    delta = chunk['choices'][0].get('delta', {})
                    if 'content' in delta:
                        yield delta['content']
                        
        except Exception as e:
            logger.error(f"流式生成回答失败: {str(e)}")
            raise

# 全局客户端实例
_deepseek_client = None

async def get_deepseek_client() -> DeepseekClient:
    """获取Deepseek客户端实例"""
    global _deepseek_client
    if _deepseek_client is None:
        _deepseek_client = DeepseekClient()
    return _deepseek_client

async def cleanup_deepseek_client():
    """清理Deepseek客户端"""
    global _deepseek_client
    if _deepseek_client is not None:
        _deepseek_client = None