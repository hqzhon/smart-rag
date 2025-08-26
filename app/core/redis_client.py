#!/usr/bin/env python3
"""
Redis客户端配置和连接管理
"""

import redis
import json
import logging
from typing import Optional, Dict, Any
from app.core.config import get_settings

logger = logging.getLogger(__name__)

class RedisClient:
    """Redis客户端封装类"""
    
    def __init__(self):
        self.settings = get_settings()
        self._client: Optional[redis.Redis] = None
        self._pubsub: Optional[redis.client.PubSub] = None
        
    def _get_client(self) -> redis.Redis:
        """获取Redis客户端连接"""
        if self._client is None:
            try:
                # 从配置中解析Redis URL
                redis_url = self.settings.redis_url
                self._client = redis.from_url(
                    redis_url,
                    decode_responses=True,
                    encoding='utf-8',
                    socket_connect_timeout=5,
                    socket_timeout=5
                )
                # 测试连接
                self._client.ping()
                logger.info(f"Redis连接成功: {redis_url}")
            except Exception as e:
                logger.error(f"Redis连接失败: {e}")
                raise
        return self._client
    
    def publish(self, channel: str, message: Dict[str, Any]) -> bool:
        """发布消息到Redis频道"""
        try:
            client = self._get_client()
            message_str = json.dumps(message, ensure_ascii=False)
            result = client.publish(channel, message_str)
            logger.debug(f"Published to {channel}: {message_str}")
            return result > 0
        except Exception as e:
            logger.error(f"发布消息失败 - 频道: {channel}, 错误: {e}")
            return False
    
    def subscribe(self, channel: str) -> Optional[redis.client.PubSub]:
        """订阅Redis频道"""
        try:
            client = self._get_client()
            pubsub = client.pubsub()
            pubsub.subscribe(channel)
            logger.debug(f"Subscribed to channel: {channel}")
            return pubsub
        except Exception as e:
            logger.error(f"订阅频道失败 - 频道: {channel}, 错误: {e}")
            return None
    
    def get_message(self, pubsub: redis.client.PubSub, timeout: float = 1.0) -> Optional[Dict[str, Any]]:
        """从订阅中获取消息"""
        try:
            message = pubsub.get_message(timeout=timeout)
            if message and message['type'] == 'message':
                data = json.loads(message['data'])
                return data
            return None
        except Exception as e:
            logger.error(f"获取消息失败: {e}")
            return None
    
    def close(self):
        """关闭Redis连接"""
        try:
            if self._pubsub:
                self._pubsub.close()
                self._pubsub = None
            if self._client:
                self._client.close()
                self._client = None
            logger.info("Redis连接已关闭")
        except Exception as e:
            logger.error(f"关闭Redis连接失败: {e}")
    
    def is_connected(self) -> bool:
        """检查Redis连接状态"""
        try:
            if self._client is None:
                return False
            self._client.ping()
            return True
        except Exception:
            return False

# 全局Redis客户端实例
_redis_client: Optional[RedisClient] = None

def get_redis_client() -> RedisClient:
    """获取Redis客户端实例（单例模式）"""
    global _redis_client
    if _redis_client is None:
        _redis_client = RedisClient()
    return _redis_client

def close_redis_client():
    """关闭Redis客户端"""
    global _redis_client
    if _redis_client is not None:
        _redis_client.close()
        _redis_client = None

# 导出便捷访问的实例
redis_client = get_redis_client()