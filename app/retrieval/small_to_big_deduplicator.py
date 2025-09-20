"""小-大检索去重择优处理器

实现RRF融合前的去重择优预处理步骤，确保每个大块只有一个最优小块代表。
"""

from typing import List, Dict, Any, Set, Tuple
from dataclasses import dataclass
from app.utils.logger import setup_logger

logger = setup_logger(__name__)


@dataclass
class DeduplicationResult:
    """去重结果"""
    deduplicated_documents: List[Dict[str, Any]]
    removed_count: int
    parent_chunk_stats: Dict[str, int]  # parent_chunk_id -> 小块数量
    processing_time: float


class SmallToBigDeduplicator:
    """小-大检索去重择优处理器
    
    在RRF融合前对四路召回结果进行去重择优处理：
    1. 遍历每路召回的小块列表
    2. 对于每个parent_chunk_id，只保留排名最靠前的小块
    3. 确保公平融合，避免同一大块的多个小块影响RRF结果
    """
    
    def __init__(self):
        self.logger = logger
    
    def deduplicate_path_results(self, 
                                path_results: Dict[str, List[Dict[str, Any]]]) -> Dict[str, List[Dict[str, Any]]]:
        """对四路召回结果进行去重择优处理
        
        Args:
            path_results: 四路召回结果，格式为 {path_name: [documents]}
            
        Returns:
            去重后的四路召回结果
        """
        import time
        start_time = time.time()
        
        deduplicated_results = {}
        total_removed = 0
        
        for path_name, documents in path_results.items():
            deduplicated_docs, removed_count = self._deduplicate_single_path(
                documents, path_name
            )
            deduplicated_results[path_name] = deduplicated_docs
            total_removed += removed_count
        
        processing_time = time.time() - start_time
        
        self.logger.info(
            f"去重择优完成: 总移除 {total_removed} 个重复小块, "
            f"耗时 {processing_time:.3f}s"
        )
        
        return deduplicated_results
    
    def _deduplicate_single_path(self, 
                                documents: List[Dict[str, Any]], 
                                path_name: str) -> Tuple[List[Dict[str, Any]], int]:
        """对单路召回结果进行去重择优
        
        Args:
            documents: 单路召回的文档列表（按相关性排序）
            path_name: 路径名称（用于日志）
            
        Returns:
            (去重后的文档列表, 移除的文档数量)
        """
        if not documents:
            return [], 0
        
        seen_parent_chunks: Set[str] = set()
        deduplicated_docs = []
        removed_count = 0
        
        for i, doc in enumerate(documents):
            parent_chunk_id = self._extract_parent_chunk_id(doc)
            
            if parent_chunk_id is None:
                # 如果没有parent_chunk_id，保留该文档（可能是传统模式）
                deduplicated_docs.append(doc)
                continue
            
            if parent_chunk_id not in seen_parent_chunks:
                # 第一次遇到该parent_chunk_id，保留该小块
                seen_parent_chunks.add(parent_chunk_id)
                deduplicated_docs.append(doc)
                
                self.logger.debug(
                    f"{path_name}路径: 保留 parent_chunk_id={parent_chunk_id} "
                    f"的小块 (排名第{i+1})"
                )
            else:
                # 已经有该parent_chunk_id的代表，跳过当前小块
                removed_count += 1
                
                self.logger.debug(
                    f"{path_name}路径: 跳过 parent_chunk_id={parent_chunk_id} "
                    f"的重复小块 (排名第{i+1})"
                )
        
        self.logger.info(
            f"{path_name}路径去重: 保留 {len(deduplicated_docs)} 个小块, "
            f"移除 {removed_count} 个重复小块"
        )
        
        return deduplicated_docs, removed_count
    
    def _extract_parent_chunk_id(self, document: Dict[str, Any]) -> str:
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
        
        # 如果都没有，返回None（可能是传统模式的文档）
        return None
    
    def get_deduplication_stats(self, 
                               original_results: Dict[str, List[Dict[str, Any]]], 
                               deduplicated_results: Dict[str, List[Dict[str, Any]]]) -> Dict[str, Any]:
        """获取去重统计信息
        
        Args:
            original_results: 原始四路召回结果
            deduplicated_results: 去重后的四路召回结果
            
        Returns:
            去重统计信息
        """
        stats = {
            'path_stats': {},
            'total_original': 0,
            'total_deduplicated': 0,
            'total_removed': 0,
            'deduplication_rate': 0.0
        }
        
        for path_name in original_results.keys():
            original_count = len(original_results.get(path_name, []))
            deduplicated_count = len(deduplicated_results.get(path_name, []))
            removed_count = original_count - deduplicated_count
            
            stats['path_stats'][path_name] = {
                'original_count': original_count,
                'deduplicated_count': deduplicated_count,
                'removed_count': removed_count,
                'deduplication_rate': removed_count / max(original_count, 1)
            }
            
            stats['total_original'] += original_count
            stats['total_deduplicated'] += deduplicated_count
            stats['total_removed'] += removed_count
        
        if stats['total_original'] > 0:
            stats['deduplication_rate'] = stats['total_removed'] / stats['total_original']
        
        return stats
    
    def analyze_parent_chunk_distribution(self, 
                                        path_results: Dict[str, List[Dict[str, Any]]]) -> Dict[str, Any]:
        """分析大块分布情况
        
        Args:
            path_results: 四路召回结果
            
        Returns:
            大块分布分析结果
        """
        parent_chunk_distribution = {}
        
        for path_name, documents in path_results.items():
            path_distribution = {}
            
            for doc in documents:
                parent_chunk_id = self._extract_parent_chunk_id(doc)
                if parent_chunk_id:
                    path_distribution[parent_chunk_id] = path_distribution.get(parent_chunk_id, 0) + 1
            
            parent_chunk_distribution[path_name] = path_distribution
        
        # 统计跨路径的大块重复情况
        all_parent_chunks = set()
        for path_dist in parent_chunk_distribution.values():
            all_parent_chunks.update(path_dist.keys())
        
        cross_path_stats = {}
        for parent_chunk_id in all_parent_chunks:
            paths_with_chunk = []
            total_small_chunks = 0
            
            for path_name, path_dist in parent_chunk_distribution.items():
                if parent_chunk_id in path_dist:
                    paths_with_chunk.append(path_name)
                    total_small_chunks += path_dist[parent_chunk_id]
            
            cross_path_stats[parent_chunk_id] = {
                'paths': paths_with_chunk,
                'path_count': len(paths_with_chunk),
                'total_small_chunks': total_small_chunks
            }
        
        return {
            'path_distribution': parent_chunk_distribution,
            'cross_path_stats': cross_path_stats,
            'unique_parent_chunks': len(all_parent_chunks),
            'multi_path_chunks': len([k for k, v in cross_path_stats.items() if v['path_count'] > 1])
        }