"""小-大检索切换逻辑处理器

实现从小块检索结果切换到大块内容的逻辑，用于LLM生成阶段。
"""

from typing import List, Dict, Any, Optional, Set
from dataclasses import dataclass
import asyncio
from app.storage.database import DatabaseManager
from app.utils.logger import setup_logger

logger = setup_logger(__name__)


@dataclass
class SwitchingResult:
    """切换结果"""
    switched_documents: List[Dict[str, Any]]
    parent_chunks_found: int
    parent_chunks_missing: int
    small_chunks_kept: int
    processing_time: float
    error_details: Optional[List[str]] = None


class SmallToBigSwitcher:
    """小-大检索切换逻辑处理器
    
    负责将检索到的小块结果切换为对应的大块内容：
    1. 提取小块的parent_chunk_id
    2. 批量查询MySQL获取大块内容
    3. 替换小块内容为大块内容
    4. 保持原有的相关性评分和元数据
    """
    
    def __init__(self, db_manager: Optional[DatabaseManager] = None):
        self.db_manager = db_manager
        self.logger = logger
    
    async def async_init(self):
        """异步初始化数据库管理器"""
        if self.db_manager is None:
            from app.storage.database import get_db_manager_async
            self.db_manager = await get_db_manager_async()
            self.logger.info("小-大切换器异步初始化完成")
    
    async def switch_to_parent_chunks(self, 
                                     small_chunk_documents: List[Dict[str, Any]], 
                                     preserve_small_chunks: bool = False) -> SwitchingResult:
        """将小块文档切换为大块内容
        
        Args:
            small_chunk_documents: 小块文档列表
            preserve_small_chunks: 是否保留无法找到大块的小块
            
        Returns:
            切换结果
        """
        import time
        start_time = time.time()
        
        if not small_chunk_documents:
            return SwitchingResult(
                switched_documents=[],
                parent_chunks_found=0,
                parent_chunks_missing=0,
                small_chunks_kept=0,
                processing_time=0.0
            )
        
        # 确保数据库管理器已初始化
        if self.db_manager is None:
            await self.async_init()
        
        # 提取所有parent_chunk_id
        parent_chunk_ids = self._extract_parent_chunk_ids(small_chunk_documents)
        
        if not parent_chunk_ids:
            # 没有parent_chunk_id，可能是传统模式，直接返回原文档
            self.logger.warning("未找到任何parent_chunk_id，可能是传统检索模式")
            return SwitchingResult(
                switched_documents=small_chunk_documents if preserve_small_chunks else [],
                parent_chunks_found=0,
                parent_chunks_missing=0,
                small_chunks_kept=len(small_chunk_documents) if preserve_small_chunks else 0,
                processing_time=time.time() - start_time
            )
        
        # 批量查询大块内容
        parent_chunks_map = await self._batch_get_parent_chunks(parent_chunk_ids)
        
        # 执行切换
        switched_documents = []
        parent_chunks_found = 0
        parent_chunks_missing = 0
        small_chunks_kept = 0
        error_details = []
        
        for small_doc in small_chunk_documents:
            try:
                parent_chunk_id = self._extract_parent_chunk_id(small_doc)
                
                if parent_chunk_id and parent_chunk_id in parent_chunks_map:
                    # 找到对应的大块，执行切换
                    parent_chunk = parent_chunks_map[parent_chunk_id]
                    switched_doc = self._create_switched_document(small_doc, parent_chunk)
                    switched_documents.append(switched_doc)
                    parent_chunks_found += 1
                    
                    self.logger.debug(f"成功切换到大块: {parent_chunk_id}")
                    
                elif preserve_small_chunks:
                    # 保留小块
                    switched_documents.append(small_doc)
                    small_chunks_kept += 1
                    
                    if parent_chunk_id:
                        parent_chunks_missing += 1
                        self.logger.warning(f"未找到大块 {parent_chunk_id}，保留小块")
                    else:
                        self.logger.debug("小块无parent_chunk_id，保留原内容")
                        
                else:
                    # 不保留小块，跳过
                    if parent_chunk_id:
                        parent_chunks_missing += 1
                        error_details.append(f"未找到大块: {parent_chunk_id}")
                    
            except Exception as e:
                error_msg = f"处理文档时出错: {str(e)}"
                error_details.append(error_msg)
                self.logger.error(error_msg)
                
                if preserve_small_chunks:
                    switched_documents.append(small_doc)
                    small_chunks_kept += 1
        
        processing_time = time.time() - start_time
        
        self.logger.info(
            f"小-大切换完成: 找到大块 {parent_chunks_found} 个, "
            f"缺失大块 {parent_chunks_missing} 个, "
            f"保留小块 {small_chunks_kept} 个, "
            f"耗时 {processing_time:.3f}s"
        )
        
        return SwitchingResult(
            switched_documents=switched_documents,
            parent_chunks_found=parent_chunks_found,
            parent_chunks_missing=parent_chunks_missing,
            small_chunks_kept=small_chunks_kept,
            processing_time=processing_time,
            error_details=error_details if error_details else None
        )
    
    def _extract_parent_chunk_ids(self, documents: List[Dict[str, Any]]) -> Set[str]:
        """提取所有文档的parent_chunk_id
        
        Args:
            documents: 文档列表
            
        Returns:
            parent_chunk_id集合
        """
        parent_chunk_ids = set()
        
        for doc in documents:
            parent_chunk_id = self._extract_parent_chunk_id(doc)
            if parent_chunk_id:
                parent_chunk_ids.add(parent_chunk_id)
        
        return parent_chunk_ids
    
    def _extract_parent_chunk_id(self, document: Dict[str, Any]) -> Optional[str]:
        """从文档中提取parent_chunk_id
        
        Args:
            document: 文档对象
            
        Returns:
            parent_chunk_id，如果不存在则返回None
        """
        # 尝试从不同位置获取parent_chunk_id
        metadata = document.get('metadata', {})
        
        # 优先从metadata中获取
        parent_chunk_id = metadata.get('parent_chunk_id')
        if parent_chunk_id:
            return str(parent_chunk_id)
        
        # 尝试从文档顶层获取
        parent_chunk_id = document.get('parent_chunk_id')
        if parent_chunk_id:
            return str(parent_chunk_id)
        
        return None
    
    async def _batch_get_parent_chunks(self, parent_chunk_ids: Set[str]) -> Dict[str, Dict[str, Any]]:
        """批量获取大块内容
        
        Args:
            parent_chunk_ids: parent_chunk_id集合
            
        Returns:
            parent_chunk_id -> 大块数据的映射
        """
        if not parent_chunk_ids:
            return {}
        
        try:
            parent_chunks = await self.db_manager.batch_get_parent_chunks(list(parent_chunk_ids))
            
            # 转换为字典格式
            parent_chunks_map = {}
            for chunk in parent_chunks:
                chunk_id = str(chunk.get('id', chunk.get('chunk_id', '')))
                parent_chunks_map[chunk_id] = chunk
            
            self.logger.info(
                f"批量查询大块: 请求 {len(parent_chunk_ids)} 个, "
                f"找到 {len(parent_chunks_map)} 个"
            )
            
            return parent_chunks_map
            
        except Exception as e:
            self.logger.error(f"批量查询大块失败: {str(e)}")
            return {}
    
    def _create_switched_document(self, 
                                 small_doc: Dict[str, Any], 
                                 parent_chunk: Dict[str, Any]) -> Dict[str, Any]:
        """创建切换后的文档
        
        Args:
            small_doc: 原始小块文档
            parent_chunk: 对应的大块数据
            
        Returns:
            切换后的文档
        """
        # 复制小块文档的结构
        switched_doc = small_doc.copy()
        
        # 替换内容为大块内容
        switched_doc['content'] = parent_chunk.get('content', '')
        switched_doc['page_content'] = parent_chunk.get('content', '')  # 兼容不同字段名
        
        # 更新元数据
        metadata = switched_doc.get('metadata', {}).copy()
        metadata.update({
            'switched_to_parent': True,
            'parent_chunk_id': parent_chunk.get('id', parent_chunk.get('chunk_id')),
            'parent_summary': parent_chunk.get('summary', ''),
            'parent_keywords': parent_chunk.get('keywords', []),
            'original_small_chunk_id': small_doc.get('id', ''),
            'switch_timestamp': self._get_current_timestamp()
        })
        
        # 如果大块有自己的元数据，也合并进来
        parent_metadata = parent_chunk.get('metadata', {})
        if isinstance(parent_metadata, dict):
            metadata.update(parent_metadata)
        
        switched_doc['metadata'] = metadata
        
        # 保持原有的评分信息
        # 这些字段通常来自检索器，需要保留用于后续排序
        score_fields = ['similarity_score', 'bm25_score', 'quality_score', 'retrieval_path']
        for field in score_fields:
            if field in small_doc:
                switched_doc[field] = small_doc[field]
        
        return switched_doc
    
    def _get_current_timestamp(self) -> str:
        """获取当前时间戳"""
        from datetime import datetime
        return datetime.now().isoformat()
    
    def get_switching_stats(self, result: SwitchingResult) -> Dict[str, Any]:
        """获取切换统计信息
        
        Args:
            result: 切换结果
            
        Returns:
            切换统计信息
        """
        total_processed = result.parent_chunks_found + result.parent_chunks_missing + result.small_chunks_kept
        
        stats = {
            'total_processed': total_processed,
            'parent_chunks_found': result.parent_chunks_found,
            'parent_chunks_missing': result.parent_chunks_missing,
            'small_chunks_kept': result.small_chunks_kept,
            'switch_success_rate': result.parent_chunks_found / max(total_processed, 1),
            'processing_time': result.processing_time,
            'has_errors': bool(result.error_details),
            'error_count': len(result.error_details) if result.error_details else 0
        }
        
        return stats