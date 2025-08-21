"""异步元数据处理器"""

import asyncio
from typing import List, Dict, Optional, Any, Callable, Union
import logging
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import json
import uuid
from concurrent.futures import ThreadPoolExecutor
import threading
from collections import defaultdict, deque

from ..models.metadata_models import (
    DocumentSummary, KeywordInfo, MetadataInfo, ProcessingTask,
    SummaryMethod, KeywordMethod, QualityLevel
)
from ..summarizers.lightweight_summarizer import LightweightSummaryGenerator
from ..extractors.keybert_extractor import KeyBERTExtractor
from ..evaluators.quality_evaluator import QualityEvaluator
from app.storage.vector_store import VectorStore
from app.utils.logger import setup_logger

logger = setup_logger(__name__)

class TaskStatus(Enum):
    """任务状态"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class TaskPriority(Enum):
    """任务优先级"""
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    URGENT = 4

@dataclass
class ProcessingTaskInternal:
    """内部处理任务"""
    task_id: str
    chunk_id: str
    text: str
    priority: TaskPriority = TaskPriority.MEDIUM
    status: TaskStatus = TaskStatus.PENDING
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3
    metadata: Dict[str, Any] = field(default_factory=dict)
    result: Optional[MetadataInfo] = None
    
    def __lt__(self, other):
        """优先级比较（用于优先队列）"""
        if self.priority.value != other.priority.value:
            return self.priority.value > other.priority.value  # 高优先级在前
        return self.created_at < other.created_at  # 相同优先级按时间排序

class AsyncMetadataProcessor:
    """异步元数据处理器
    
    功能：
    - 异步任务队列管理
    - 并发处理控制
    - 错误重试机制
    - ChromaDB集成
    - 进度监控
    - 性能统计
    """
    
    def __init__(
        self,
        summarizer: Optional[LightweightSummaryGenerator] = None,
        extractor: Optional[KeyBERTExtractor] = None,
        evaluator: Optional[QualityEvaluator] = None,
        chroma_client: Optional[VectorStore] = None,
        max_workers: int = 4,
        max_queue_size: int = 1000,
        batch_size: int = 10,
        processing_timeout: int = 300,
        enable_quality_check: bool = True
    ):
        """初始化异步元数据处理器
        
        Args:
            summarizer: 摘要生成器
            extractor: 关键词提取器
            evaluator: 质量评估器
            chroma_client: ChromaDB客户端
            max_workers: 最大工作线程数
            max_queue_size: 最大队列大小
            batch_size: 批处理大小
            processing_timeout: 处理超时时间（秒）
            enable_quality_check: 是否启用质量检查
        """
        # 组件初始化
        self.summarizer = summarizer or LightweightSummaryGenerator()
        self.extractor = extractor or KeyBERTExtractor()
        self.evaluator = evaluator or QualityEvaluator()
        self.chroma_client = chroma_client
        
        # 配置参数
        self.max_workers = max_workers
        self.max_queue_size = max_queue_size
        self.batch_size = batch_size
        self.processing_timeout = processing_timeout
        self.enable_quality_check = enable_quality_check
        
        # 任务队列和管理
        self.task_queue = asyncio.PriorityQueue(maxsize=max_queue_size)
        self.active_tasks: Dict[str, ProcessingTaskInternal] = {}
        self.completed_tasks: deque = deque(maxlen=1000)  # 保留最近1000个完成任务
        self.task_lock = asyncio.Lock()
        
        # 工作线程池
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        
        # 控制标志
        self.is_running = False
        self.shutdown_event = asyncio.Event()
        
        # 统计信息
        self.stats = {
            "total_submitted": 0,
            "total_completed": 0,
            "total_failed": 0,
            "total_cancelled": 0,
            "current_queue_size": 0,
            "active_workers": 0,
            "average_processing_time": 0.0,
            "last_activity": None
        }
        
        # 性能监控
        self.processing_times = deque(maxlen=100)
        self.error_counts = defaultdict(int)
        
        # 回调函数
        self.task_callbacks: Dict[str, List[Callable]] = defaultdict(list)
        
        logger.info(f"异步元数据处理器初始化完成 - 最大工作线程: {max_workers}, 队列大小: {max_queue_size}")
    
    async def start(self):
        """启动处理器"""
        if self.is_running:
            logger.warning("处理器已在运行中")
            return
        
        self.is_running = True
        self.shutdown_event.clear()
        
        # 启动工作协程
        self.worker_tasks = [
            asyncio.create_task(self._worker(f"worker-{i}"))
            for i in range(self.max_workers)
        ]
        
        # 启动监控协程
        self.monitor_task = asyncio.create_task(self._monitor())
        
        logger.info("异步元数据处理器已启动")
    
    async def stop(self, timeout: int = 30):
        """停止处理器
        
        Args:
            timeout: 停止超时时间（秒）
        """
        if not self.is_running:
            logger.warning("处理器未在运行")
            return
        
        logger.info("正在停止异步元数据处理器...")
        
        # 设置停止标志
        self.is_running = False
        self.shutdown_event.set()
        
        # 等待所有任务完成或超时
        try:
            await asyncio.wait_for(
                asyncio.gather(
                    *self.worker_tasks,
                    self.monitor_task,
                    return_exceptions=True
                ),
                timeout=timeout
            )
        except asyncio.TimeoutError:
            logger.warning(f"停止处理器超时 ({timeout}秒)，强制取消任务")
            
            # 强制取消任务
            for task in self.worker_tasks + [self.monitor_task]:
                if not task.done():
                    task.cancel()
        
        # 关闭线程池
        self.executor.shutdown(wait=True)
        
        logger.info("异步元数据处理器已停止")
    
    async def submit_task(
        self,
        chunk_id: str,
        text: str,
        priority: TaskPriority = TaskPriority.MEDIUM,
        metadata: Optional[Dict[str, Any]] = None,
        callback: Optional[Callable] = None
    ) -> str:
        """提交处理任务
        
        Args:
            chunk_id: 文档块ID
            text: 待处理文本
            priority: 任务优先级
            metadata: 额外元数据
            callback: 完成回调函数
            
        Returns:
            任务ID
        """
        if not self.is_running:
            raise RuntimeError("处理器未启动")
        
        if self.task_queue.full():
            raise RuntimeError("任务队列已满")
        
        # 创建任务
        task_id = str(uuid.uuid4())
        task = ProcessingTaskInternal(
            task_id=task_id,
            chunk_id=chunk_id,
            text=text,
            priority=priority,
            metadata=metadata or {}
        )
        
        # 注册回调
        if callback:
            self.task_callbacks[task_id].append(callback)
        
        # 添加到队列
        await self.task_queue.put(task)
        
        async with self.task_lock:
            self.active_tasks[task_id] = task
            self.stats["total_submitted"] += 1
            self.stats["current_queue_size"] = self.task_queue.qsize()
        
        logger.debug(f"任务已提交 - ID: {task_id}, 块ID: {chunk_id}, 优先级: {priority.name}")
        return task_id
    
    async def submit_batch_tasks(
        self,
        tasks: List[Dict[str, Any]],
        default_priority: TaskPriority = TaskPriority.MEDIUM
    ) -> List[str]:
        """批量提交任务
        
        Args:
            tasks: 任务列表，每个任务包含chunk_id, text等字段
            default_priority: 默认优先级
            
        Returns:
            任务ID列表
        """
        task_ids = []
        
        for task_data in tasks:
            try:
                task_id = await self.submit_task(
                    chunk_id=task_data["chunk_id"],
                    text=task_data["text"],
                    priority=task_data.get("priority", default_priority),
                    metadata=task_data.get("metadata"),
                    callback=task_data.get("callback")
                )
                task_ids.append(task_id)
            except Exception as e:
                logger.error(f"批量提交任务失败: {str(e)}")
                task_ids.append(None)
        
        logger.info(f"批量提交完成: {len([tid for tid in task_ids if tid])} / {len(tasks)} 成功")
        return task_ids
    
    async def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """获取任务状态
        
        Args:
            task_id: 任务ID
            
        Returns:
            任务状态信息
        """
        async with self.task_lock:
            # 检查活跃任务
            if task_id in self.active_tasks:
                task = self.active_tasks[task_id]
                return {
                    "task_id": task.task_id,
                    "chunk_id": task.chunk_id,
                    "status": task.status.value,
                    "priority": task.priority.name,
                    "created_at": task.created_at.isoformat(),
                    "started_at": task.started_at.isoformat() if task.started_at else None,
                    "completed_at": task.completed_at.isoformat() if task.completed_at else None,
                    "retry_count": task.retry_count,
                    "error_message": task.error_message,
                    "has_result": task.result is not None
                }
            
            # 检查已完成任务
            for task in self.completed_tasks:
                if task.task_id == task_id:
                    return {
                        "task_id": task.task_id,
                        "chunk_id": task.chunk_id,
                        "status": task.status.value,
                        "priority": task.priority.name,
                        "created_at": task.created_at.isoformat(),
                        "started_at": task.started_at.isoformat() if task.started_at else None,
                        "completed_at": task.completed_at.isoformat() if task.completed_at else None,
                        "retry_count": task.retry_count,
                        "error_message": task.error_message,
                        "has_result": task.result is not None
                    }
        
        return None
    
    async def get_task_result(self, task_id: str) -> Optional[MetadataInfo]:
        """获取任务结果
        
        Args:
            task_id: 任务ID
            
        Returns:
            元数据信息
        """
        async with self.task_lock:
            # 检查活跃任务
            if task_id in self.active_tasks:
                task = self.active_tasks[task_id]
                if task.status == TaskStatus.COMPLETED:
                    return task.result
            
            # 检查已完成任务
            for task in self.completed_tasks:
                if task.task_id == task_id and task.status == TaskStatus.COMPLETED:
                    return task.result
        
        return None
    
    async def cancel_task(self, task_id: str) -> bool:
        """取消任务
        
        Args:
            task_id: 任务ID
            
        Returns:
            是否成功取消
        """
        async with self.task_lock:
            if task_id in self.active_tasks:
                task = self.active_tasks[task_id]
                if task.status == TaskStatus.PENDING:
                    task.status = TaskStatus.CANCELLED
                    task.completed_at = datetime.now()
                    self.stats["total_cancelled"] += 1
                    logger.info(f"任务已取消 - ID: {task_id}")
                    return True
                else:
                    logger.warning(f"无法取消正在处理的任务 - ID: {task_id}, 状态: {task.status.value}")
                    return False
        
        logger.warning(f"未找到任务 - ID: {task_id}")
        return False
    
    async def _worker(self, worker_name: str):
        """工作协程
        
        Args:
            worker_name: 工作线程名称
        """
        logger.info(f"工作线程启动: {worker_name}")
        
        while self.is_running:
            try:
                # 获取任务（带超时）
                try:
                    task = await asyncio.wait_for(
                        self.task_queue.get(),
                        timeout=1.0
                    )
                except asyncio.TimeoutError:
                    continue
                
                # 检查任务是否已取消
                if task.status == TaskStatus.CANCELLED:
                    self.task_queue.task_done()
                    continue
                
                # 更新任务状态
                task.status = TaskStatus.PROCESSING
                task.started_at = datetime.now()
                
                async with self.task_lock:
                    self.stats["active_workers"] += 1
                
                try:
                    # 处理任务
                    result = await self._process_task(task, worker_name)
                    
                    # 更新任务结果
                    task.result = result
                    task.status = TaskStatus.COMPLETED
                    task.completed_at = datetime.now()
                    
                    # 更新统计
                    processing_time = (task.completed_at - task.started_at).total_seconds()
                    self.processing_times.append(processing_time)
                    
                    async with self.task_lock:
                        self.stats["total_completed"] += 1
                        self.stats["average_processing_time"] = sum(self.processing_times) / len(self.processing_times)
                        self.stats["last_activity"] = datetime.now().isoformat()
                    
                    # 执行回调
                    await self._execute_callbacks(task.task_id, result, None)
                    
                    logger.debug(f"任务处理完成 - ID: {task.task_id}, 耗时: {processing_time:.2f}秒")
                    
                except Exception as e:
                    # 处理失败
                    task.error_message = str(e)
                    task.retry_count += 1
                    
                    if task.retry_count <= task.max_retries:
                        # 重试
                        task.status = TaskStatus.PENDING
                        task.started_at = None
                        await self.task_queue.put(task)
                        logger.warning(f"任务处理失败，将重试 - ID: {task.task_id}, 重试次数: {task.retry_count}/{task.max_retries}, 错误: {str(e)}")
                    else:
                        # 最终失败
                        task.status = TaskStatus.FAILED
                        task.completed_at = datetime.now()
                        
                        async with self.task_lock:
                            self.stats["total_failed"] += 1
                            self.error_counts[type(e).__name__] += 1
                        
                        # 执行错误回调
                        await self._execute_callbacks(task.task_id, None, e)
                        
                        logger.error(f"任务最终失败 - ID: {task.task_id}, 错误: {str(e)}")
                
                finally:
                    async with self.task_lock:
                        self.stats["active_workers"] -= 1
                        self.stats["current_queue_size"] = self.task_queue.qsize()
                        
                        # 移动到已完成队列
                        if task.status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]:
                            if task.task_id in self.active_tasks:
                                del self.active_tasks[task.task_id]
                            self.completed_tasks.append(task)
                    
                    self.task_queue.task_done()
                    
            except Exception as e:
                logger.error(f"工作线程异常 - {worker_name}: {str(e)}")
                await asyncio.sleep(1)
        
        logger.info(f"工作线程停止: {worker_name}")
    
    async def _process_task(self, task: ProcessingTaskInternal, worker_name: str) -> MetadataInfo:
        """处理单个任务
        
        Args:
            task: 处理任务
            worker_name: 工作线程名称
            
        Returns:
            元数据信息
        """
        start_time = datetime.now()
        
        try:
            # 并发生成摘要和提取关键词
            summary_task = asyncio.create_task(
                self.summarizer.generate_summary(
                    text=task.text,
                    chunk_id=task.chunk_id,
                    metadata=task.metadata
                )
            )
            
            keywords_task = asyncio.create_task(
                self.extractor.extract_keywords(
                    text=task.text,
                    chunk_id=task.chunk_id,
                    metadata=task.metadata
                )
            )
            
            # 等待两个任务完成
            summary_info, keyword_info = await asyncio.gather(
                summary_task, keywords_task
            )
            
            # 质量评估
            summary_quality = None
            keyword_quality = None
            
            if self.enable_quality_check:
                quality_tasks = []
                
                if summary_info and summary_info.content:
                    quality_tasks.append(
                        self.evaluator.evaluate_summary_quality(
                            original_text=task.text,
                            summary=summary_info.content,
                            metadata={}
                        )
                    )
                else:
                    quality_tasks.append(asyncio.create_task(asyncio.sleep(0, result=None)))
                
                if keyword_info and keyword_info.keywords:
                    quality_tasks.append(
                        self.evaluator.evaluate_keyword_quality(
                            original_text=task.text,
                            keywords=keyword_info.keywords,
                            keyword_scores=keyword_info.keyword_scores,
                            metadata=keyword_info.metadata
                        )
                    )
                else:
                    quality_tasks.append(asyncio.create_task(asyncio.sleep(0, result=None)))
                
                summary_quality, keyword_quality = await asyncio.gather(*quality_tasks)
            
            # 创建元数据信息
            processing_time = (datetime.now() - start_time).total_seconds()
            
            metadata_info = MetadataInfo(
                chunk_id=task.chunk_id,
                summary=summary_info,
                keywords=keyword_info,
                summary_quality=summary_quality,
                keyword_quality=keyword_quality,
                processing_time=processing_time,
                processed_at=datetime.now(),
                processor_version="1.0.0",
                metadata={
                    **task.metadata,
                    "worker_name": worker_name,
                    "task_id": task.task_id,
                    "retry_count": task.retry_count
                }
            )
            
            # 注意：不再直接存储到ChromaDB，而是返回元数据供外部更新
            # ChromaDB的更新将由外部调用update_chunk_in_chroma方法完成
            
            return metadata_info
            
        except Exception as e:
            logger.error(f"任务处理异常 - ID: {task.task_id}, 错误: {str(e)}")
            raise
    
    async def update_chunk_in_chroma(self, chunk_id: str, metadata_info: MetadataInfo):
        """更新ChromaDB中的文档块元数据
        
        Args:
            chunk_id: 文档块ID
            metadata_info: 元数据信息
        """
        try:
            # 准备更新的元数据
            # 处理关键词列表
            all_keywords = []
            keyword_method = ""
            medical_category = ""
            if metadata_info.keywords:
                for kw_info in metadata_info.keywords:
                    all_keywords.extend(kw_info.keywords)
                # 使用第一个关键词信息的方法和分类
                if metadata_info.keywords:
                    keyword_method = metadata_info.keywords[0].method.value
                    medical_category = metadata_info.keywords[0].medical_category.value
            
            updated_metadata = {
                "summary": metadata_info.summary.content if metadata_info.summary else "",
                "keywords": ",".join(all_keywords),
                "summary_method": metadata_info.summary.method.value if metadata_info.summary else "",
                "keyword_method": keyword_method,
                "medical_category": medical_category,
                "summary_quality": metadata_info.summary_quality.overall_score if metadata_info.summary_quality else 0.0,
                "keyword_quality": metadata_info.keyword_quality.overall_score if metadata_info.keyword_quality else 0.0,
                "processed_at": metadata_info.created_at.isoformat(),
                "processing_time": metadata_info.processing_time,
                "processor_version": metadata_info.processor_version,
                "metadata_updated": True
            }
            
            # 使用VectorStore的update方法更新ChromaDB中的文档
            await self.chroma_client.update_document(
                document_id=chunk_id,
                metadata=updated_metadata
            )
            
            logger.debug(f"ChromaDB中的文档块元数据已更新 - 块ID: {chunk_id}")
            
        except Exception as e:
            logger.error(f"ChromaDB元数据更新失败 - 块ID: {chunk_id}, 错误: {str(e)}")
            raise
    
    async def _execute_callbacks(self, task_id: str, result: Optional[MetadataInfo], error: Optional[Exception]):
        """执行任务回调
        
        Args:
            task_id: 任务ID
            result: 处理结果
            error: 错误信息
        """
        callbacks = self.task_callbacks.get(task_id, [])
        if not callbacks:
            return
        
        for callback in callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(task_id, result, error)
                else:
                    callback(task_id, result, error)
            except Exception as e:
                logger.error(f"回调执行失败 - 任务ID: {task_id}, 错误: {str(e)}")
        
        # 清理回调
        del self.task_callbacks[task_id]
    
    async def _monitor(self):
        """监控协程"""
        logger.info("监控协程启动")
        
        while self.is_running:
            try:
                await asyncio.sleep(30)  # 每30秒监控一次
                
                # 记录统计信息
                stats = self.get_stats()
                logger.info(
                    f"处理器状态 - 队列: {stats['current_queue_size']}, "
                    f"活跃: {stats['active_workers']}, "
                    f"完成: {stats['total_completed']}, "
                    f"失败: {stats['total_failed']}, "
                    f"平均耗时: {stats['average_processing_time']:.2f}秒"
                )
                
                # 检查长时间运行的任务
                current_time = datetime.now()
                async with self.task_lock:
                    for task in self.active_tasks.values():
                        if (
                            task.status == TaskStatus.PROCESSING and
                            task.started_at and
                            (current_time - task.started_at).total_seconds() > self.processing_timeout
                        ):
                            logger.warning(
                                f"检测到长时间运行任务 - ID: {task.task_id}, "
                                f"运行时间: {(current_time - task.started_at).total_seconds():.1f}秒"
                            )
                
            except Exception as e:
                logger.error(f"监控协程异常: {str(e)}")
        
        logger.info("监控协程停止")
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            **self.stats,
            "is_running": self.is_running,
            "max_workers": self.max_workers,
            "max_queue_size": self.max_queue_size,
            "batch_size": self.batch_size,
            "processing_timeout": self.processing_timeout,
            "enable_quality_check": self.enable_quality_check,
            "error_counts": dict(self.error_counts),
            "recent_processing_times": list(self.processing_times)[-10:],  # 最近10次处理时间
            "active_task_count": len(self.active_tasks),
            "completed_task_count": len(self.completed_tasks)
        }
    
    def reset_stats(self):
        """重置统计信息"""
        self.stats = {
            "total_submitted": 0,
            "total_completed": 0,
            "total_failed": 0,
            "total_cancelled": 0,
            "current_queue_size": self.task_queue.qsize(),
            "active_workers": 0,
            "average_processing_time": 0.0,
            "last_activity": None
        }
        self.processing_times.clear()
        self.error_counts.clear()
        logger.info("处理器统计信息已重置")
    
    async def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        try:
            health_status = {
                "is_running": self.is_running,
                "queue_health": not self.task_queue.full(),
                "worker_health": self.stats["active_workers"] <= self.max_workers,
                "component_health": {}
            }
            
            # 检查组件健康状态
            if self.summarizer:
                health_status["component_health"]["summarizer"] = await self.summarizer.health_check()
            
            if self.extractor:
                health_status["component_health"]["extractor"] = await self.extractor.health_check()
            
            if self.evaluator:
                health_status["component_health"]["evaluator"] = await self.evaluator.health_check()
            
            if self.chroma_client:
                try:
                    health_status["component_health"]["chroma_client"] = await self.chroma_client.health_check()
                except:
                    health_status["component_health"]["chroma_client"] = False
            
            # 整体健康状态
            health_status["overall_healthy"] = (
                health_status["is_running"] and
                health_status["queue_health"] and
                health_status["worker_health"] and
                all(health_status["component_health"].values())
            )
            
            return health_status
            
        except Exception as e:
            logger.error(f"健康检查异常: {str(e)}")
            return {
                "overall_healthy": False,
                "error": str(e)
            }
    
    async def __aenter__(self):
        """异步上下文管理器入口"""
        await self.start()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        await self.stop()