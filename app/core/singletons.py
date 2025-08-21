"""单例模式管理器

提供单例模式的实现和管理功能，确保资源的单一实例，避免重复初始化。
"""

import asyncio
from typing import Optional, Dict, Any, Callable, TypeVar, Type, Coroutine
from functools import wraps
import threading

T = TypeVar('T')


class SingletonMeta(type):
    """单例元类
    
    使用元类实现单例模式，确保每个类只有一个实例。
    支持异步初始化。
    """
    _instances: Dict[type, Any] = {}
    _lock = threading.Lock()
    
    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            with cls._lock:
                if cls not in cls._instances:
                    instance = super().__call__(*args, **kwargs)
                    cls._instances[cls] = instance
        return cls._instances[cls]


class AsyncSingletonMeta(type):
    """异步单例元类
    
    支持异步初始化的单例模式。
    """
    _instances: Dict[type, Any] = {}
    _lock = asyncio.Lock()
    
    async def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            async with cls._lock:
                if cls not in cls._instances:
                    instance = super().__call__(*args, **kwargs)
                    if hasattr(instance, 'initialize') and asyncio.iscoroutinefunction(instance.initialize):
                        await instance.initialize()
                    cls._instances[cls] = instance
        return cls._instances[cls]


class SingletonManager:
    """单例管理器
    
    提供统一的单例实例管理功能，支持同步和异步初始化。
    """
    _instances: Dict[str, Any] = {}
    _async_lock = asyncio.Lock()
    _sync_lock = threading.Lock()
    
    @classmethod
    async def get_async_instance(cls, key: str, factory_func: Callable, *args, **kwargs) -> Any:
        """获取或创建异步单例实例
        
        Args:
            key: 实例唯一标识
            factory_func: 工厂函数
            *args: 工厂函数参数
            **kwargs: 工厂函数关键字参数
            
        Returns:
            单例实例
        """
        if key not in cls._instances:
            async with cls._async_lock:
                if key not in cls._instances:
                    if asyncio.iscoroutinefunction(factory_func):
                        instance = await factory_func(*args, **kwargs)
                    else:
                        instance = factory_func(*args, **kwargs)
                    cls._instances[key] = instance
        return cls._instances[key]
    
    @classmethod
    def get_sync_instance(cls, key: str, factory_func: Callable, *args, **kwargs) -> Any:
        """获取或创建同步单例实例
        
        Args:
            key: 实例唯一标识
            factory_func: 工厂函数
            *args: 工厂函数参数
            **kwargs: 工厂函数关键字参数
            
        Returns:
            单例实例
        """
        if key not in cls._instances:
            with cls._sync_lock:
                if key not in cls._instances:
                    instance = factory_func(*args, **kwargs)
                    cls._instances[key] = instance
        return cls._instances[key]
    
    @classmethod
    def has_instance(cls, key: str) -> bool:
        """检查是否存在指定的实例
        
        Args:
            key: 实例唯一标识
            
        Returns:
            是否存在实例
        """
        return key in cls._instances
    
    @classmethod
    def remove_instance(cls, key: str) -> bool:
        """移除指定的实例
        
        Args:
            key: 实例唯一标识
            
        Returns:
            是否成功移除
        """
        if key in cls._instances:
            del cls._instances[key]
            return True
        return False
    
    @classmethod
    async def cleanup_all(cls):
        """清理所有实例
        
        调用每个实例的cleanup方法（如果存在），然后清空实例字典。
        """
        cleanup_tasks = []
        
        for instance in cls._instances.values():
            if hasattr(instance, 'cleanup'):
                if asyncio.iscoroutinefunction(instance.cleanup):
                    cleanup_tasks.append(instance.cleanup())
                else:
                    try:
                        instance.cleanup()
                    except Exception as e:
                        print(f"Error during sync cleanup: {e}")
        
        if cleanup_tasks:
            try:
                await asyncio.gather(*cleanup_tasks, return_exceptions=True)
            except Exception as e:
                print(f"Error during async cleanup: {e}")
        
        cls._instances.clear()
    
    @classmethod
    def get_all_instances(cls) -> Dict[str, Any]:
        """获取所有实例
        
        Returns:
            所有实例的字典
        """
        return cls._instances.copy()


def singleton(cls: Type[T]) -> Callable[..., T]:
    """单例装饰器
    
    使用装饰器实现单例模式，支持同步初始化。
    
    Args:
        cls: 要应用单例模式的类
        
    Returns:
        单例实例获取函数
    """
    instances = {}
    lock = threading.Lock()
    
    @wraps(cls)
    def get_instance(*args, **kwargs) -> T:
        if cls not in instances:
            with lock:
                if cls not in instances:
                    instance = cls(*args, **kwargs)
                    instances[cls] = instance
        return instances[cls]
    
    return get_instance


def async_singleton(cls: Type[T]) -> Callable[..., Coroutine[Any, Any, T]]:
    """异步单例装饰器
    
    使用装饰器实现异步单例模式，支持异步初始化。
    
    Args:
        cls: 要应用单例模式的类
        
    Returns:
        异步单例实例获取函数
    """
    instances = {}
    lock = asyncio.Lock()
    
    @wraps(cls)
    async def get_instance(*args, **kwargs) -> T:
        if cls not in instances:
            async with lock:
                if cls not in instances:
                    instance = cls(*args, **kwargs)
                    if hasattr(instance, 'initialize') and asyncio.iscoroutinefunction(instance.initialize):
                        await instance.initialize()
                    instances[cls] = instance
        return instances[cls]
    
    return get_instance


class SingletonRegistry:
    """单例注册表
    
    提供单例实例的注册和管理功能。
    """
    
    def __init__(self):
        self._registry: Dict[str, Any] = {}
        self._lock = threading.Lock()
    
    def register(self, name: str, instance: Any) -> None:
        """注册单例实例
        
        Args:
            name: 实例名称
            instance: 实例对象
        """
        with self._lock:
            self._registry[name] = instance
    
    def get(self, name: str) -> Optional[Any]:
        """获取单例实例
        
        Args:
            name: 实例名称
            
        Returns:
            实例对象或None
        """
        return self._registry.get(name)
    
    def unregister(self, name: str) -> bool:
        """注销单例实例
        
        Args:
            name: 实例名称
            
        Returns:
            是否成功注销
        """
        with self._lock:
            if name in self._registry:
                del self._registry[name]
                return True
            return False
    
    def list_all(self) -> Dict[str, Any]:
        """列出所有注册的实例
        
        Returns:
            所有实例的字典
        """
        return self._registry.copy()
    
    def clear(self) -> None:
        """清空注册表"""
        with self._lock:
            self._registry.clear()


# 全局单例注册表实例
global_registry = SingletonRegistry()