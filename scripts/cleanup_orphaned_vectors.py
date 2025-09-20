#!/usr/bin/env python3
"""
向量数据库垃圾数据清理脚本
清理向量数据库中documents表中不存在的document_id对应的数据
"""

import asyncio
import logging
import sys
import os
from typing import Set, List, Dict, Any, Optional
from datetime import datetime

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.storage.database import DatabaseManager
from app.storage.vector_store import get_vector_store_async
from app.utils.logger import setup_logger

logger = setup_logger(__name__)


class OrphanedVectorCleaner:
    """孤立向量数据清理器"""
    
    def __init__(self):
        self.db_manager = DatabaseManager()
        self.vector_store = None
        
    async def initialize(self):
        """初始化数据库连接"""
        try:
            await self.db_manager.async_init()
            self.vector_store = await get_vector_store_async()
            logger.info("数据库连接初始化完成")
        except Exception as e:
            logger.error(f"初始化失败: {str(e)}")
            raise
    
    def get_valid_document_ids(self) -> Set[str]:
        """从MySQL documents表获取所有有效的文档ID"""
        try:
            # 获取所有文档
            documents = self.db_manager.get_all_documents_content(limit=50000)
            document_ids = {doc['id'] for doc in documents}
            logger.info(f"从documents表获取到 {len(document_ids)} 个有效文档ID")
            return document_ids
        except Exception as e:
            logger.error(f"获取documents表文档ID失败: {str(e)}")
            return set()
    
    def get_vector_document_ids(self) -> Set[str]:
        """从向量数据库获取所有文档ID"""
        try:
            if not self.vector_store or not self.vector_store.collection:
                logger.error("向量存储未初始化")
                return set()
            
            # 获取所有向量数据的元数据
            result = self.vector_store.collection.get(include=['metadatas'])
            
            if not result or not result.get('metadatas'):
                logger.info("向量数据库中没有数据")
                return set()
            
            # 提取document_id
            document_ids = set()
            for metadata in result['metadatas']:
                if metadata and 'document_id' in metadata:
                    document_ids.add(metadata['document_id'])
            
            logger.info(f"从向量数据库获取到 {len(document_ids)} 个文档ID")
            return document_ids
            
        except Exception as e:
            logger.error(f"获取向量数据库文档ID失败: {str(e)}")
            return set()
    
    def get_orphaned_chunk_ids(self, valid_doc_ids: Set[str]) -> List[str]:
        """获取孤立的chunk ID列表"""
        try:
            if not self.vector_store or not self.vector_store.collection:
                logger.error("向量存储未初始化")
                return []
            
            # 获取所有向量数据
            result = self.vector_store.collection.get(include=['metadatas'])
            
            if not result or not result.get('ids') or not result.get('metadatas'):
                logger.info("向量数据库中没有数据")
                return []
            
            orphaned_ids = []
            total_chunks = len(result['ids'])
            
            for i, (chunk_id, metadata) in enumerate(zip(result['ids'], result['metadatas'])):
                if metadata and 'document_id' in metadata:
                    document_id = metadata['document_id']
                    if document_id not in valid_doc_ids:
                        orphaned_ids.append(chunk_id)
                else:
                    # 没有document_id元数据的chunk也视为孤立数据
                    orphaned_ids.append(chunk_id)
            
            logger.info(f"发现 {len(orphaned_ids)} 个孤立chunks，总chunks数: {total_chunks}")
            return orphaned_ids
            
        except Exception as e:
            logger.error(f"获取孤立chunks失败: {str(e)}")
            return []
    
    def delete_orphaned_chunks(self, chunk_ids: List[str], dry_run: bool = True) -> bool:
        """删除孤立的chunks"""
        if not chunk_ids:
            logger.info("没有需要删除的孤立chunks")
            return True
        
        if dry_run:
            logger.info(f"[试运行] 将删除 {len(chunk_ids)} 个孤立chunks")
            # 显示前10个要删除的chunk ID作为示例
            sample_ids = chunk_ids[:10]
            logger.info(f"[试运行] 示例chunk IDs: {sample_ids}")
            if len(chunk_ids) > 10:
                logger.info(f"[试运行] ... 还有 {len(chunk_ids) - 10} 个")
            return True
            
        try:
            if not self.vector_store or not self.vector_store.collection:
                logger.error("向量存储未初始化")
                return False
            
            # 分批删除，避免一次删除太多数据
            batch_size = 100
            total_deleted = 0
            
            logger.info(f"开始删除 {len(chunk_ids)} 个孤立chunks...")
            
            for i in range(0, len(chunk_ids), batch_size):
                batch = chunk_ids[i:i + batch_size]
                try:
                    self.vector_store.collection.delete(ids=batch)
                    total_deleted += len(batch)
                    logger.info(f"已删除 {len(batch)} 个chunks，总计: {total_deleted}/{len(chunk_ids)}")
                except Exception as e:
                    logger.error(f"删除batch失败: {str(e)}")
                    continue
            
            logger.info(f"清理完成，共删除 {total_deleted} 个孤立chunks")
            return True
            
        except Exception as e:
            logger.error(f"删除孤立chunks失败: {str(e)}")
            return False
    
    def get_orphaned_document_stats(self, valid_doc_ids: Set[str]) -> Dict[str, Any]:
        """获取孤立文档的统计信息"""
        try:
            if not self.vector_store or not self.vector_store.collection:
                return {"error": "向量存储未初始化"}
            
            result = self.vector_store.collection.get(include=['metadatas'])
            
            if not result or not result.get('metadatas'):
                return {"total_chunks": 0, "orphaned_chunks": 0, "orphaned_documents": set()}
            
            total_chunks = len(result['metadatas'])
            orphaned_chunks = 0
            orphaned_documents = set()
            document_chunk_count = {}
            
            for metadata in result['metadatas']:
                if metadata and 'document_id' in metadata:
                    document_id = metadata['document_id']
                    document_chunk_count[document_id] = document_chunk_count.get(document_id, 0) + 1
                    
                    if document_id not in valid_doc_ids:
                        orphaned_chunks += 1
                        orphaned_documents.add(document_id)
                else:
                    orphaned_chunks += 1
            
            return {
                "total_chunks": total_chunks,
                "orphaned_chunks": orphaned_chunks,
                "orphaned_documents": list(orphaned_documents),
                "orphaned_document_count": len(orphaned_documents),
                "document_chunk_count": document_chunk_count
            }
            
        except Exception as e:
            logger.error(f"获取统计信息失败: {str(e)}")
            return {"error": str(e)}
    
    async def cleanup(self, dry_run: bool = True) -> Dict[str, Any]:
        """执行清理操作"""
        start_time = datetime.now()
        
        try:
            # 获取有效的文档ID
            valid_doc_ids = self.get_valid_document_ids()
            if not valid_doc_ids:
                logger.error("无法获取有效的文档ID，停止清理")
                return {"success": False, "error": "无法获取有效的文档ID"}
            
            # 获取统计信息
            stats = self.get_orphaned_document_stats(valid_doc_ids)
            logger.info(f"统计信息: {stats}")
            
            # 获取孤立的chunk ID
            orphaned_chunk_ids = self.get_orphaned_chunk_ids(valid_doc_ids)
            
            if not orphaned_chunk_ids:
                logger.info("没有发现孤立的向量数据")
                return {
                    "success": True,
                    "orphaned_chunks_deleted": 0,
                    "stats": stats,
                    "execution_time": (datetime.now() - start_time).total_seconds()
                }
            
            # 删除孤立的chunks
            success = self.delete_orphaned_chunks(orphaned_chunk_ids, dry_run)
            
            end_time = datetime.now()
            execution_time = (end_time - start_time).total_seconds()
            
            result = {
                "success": success,
                "orphaned_chunks_found": len(orphaned_chunk_ids),
                "orphaned_chunks_deleted": len(orphaned_chunk_ids) if success and not dry_run else 0,
                "dry_run": dry_run,
                "stats": stats,
                "execution_time": execution_time
            }
            
            if dry_run:
                logger.info(f"[试运行完成] 发现 {len(orphaned_chunk_ids)} 个孤立chunks，执行时间: {execution_time:.2f}秒")
            else:
                logger.info(f"[清理完成] 删除 {len(orphaned_chunk_ids)} 个孤立chunks，执行时间: {execution_time:.2f}秒")
            
            return result
            
        except Exception as e:
            logger.error(f"清理过程中发生错误: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "execution_time": (datetime.now() - start_time).total_seconds()
            }


async def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='向量数据库垃圾数据清理工具')
    parser.add_argument('--dry-run', action='store_true', default=True,
                       help='试运行模式，不实际删除数据（默认）')
    parser.add_argument('--force', action='store_true', default=False,
                       help='强制执行删除操作')
    parser.add_argument('--log-level', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
                       default='INFO', help='日志级别')
    parser.add_argument('--stats-only', action='store_true', default=False,
                       help='仅显示统计信息，不执行清理')
    
    args = parser.parse_args()
    
    # 设置日志级别
    logging.getLogger().setLevel(getattr(logging, args.log_level))
    
    # 确定运行模式
    dry_run = not args.force
    
    if args.stats_only:
        logger.info("=== 仅显示统计信息模式 ===")
    elif dry_run:
        logger.info("=== 试运行模式 ===")
        logger.info("使用 --force 参数来实际执行删除操作")
    else:
        logger.warning("=== 强制执行模式 ===")
        logger.warning("将实际删除孤立的向量数据！")
        
        # 二次确认
        try:
            confirm = input("确认要删除孤立的向量数据吗？(输入 'YES' 确认): ")
            if confirm != 'YES':
                logger.info("操作已取消")
                return
        except KeyboardInterrupt:
            logger.info("\n操作已取消")
            return
    
    cleaner = OrphanedVectorCleaner()
    
    try:
        await cleaner.initialize()
        
        if args.stats_only:
            # 仅显示统计信息
            valid_doc_ids = cleaner.get_valid_document_ids()
            stats = cleaner.get_orphaned_document_stats(valid_doc_ids)
            
            print("\n=== 向量数据库统计信息 ===")
            print(f"总chunks数: {stats.get('total_chunks', 0)}")
            print(f"孤立chunks数: {stats.get('orphaned_chunks', 0)}")
            print(f"孤立文档数: {stats.get('orphaned_document_count', 0)}")
            
            if stats.get('orphaned_documents'):
                print(f"孤立文档ID列表: {stats['orphaned_documents'][:10]}")
                if len(stats['orphaned_documents']) > 10:
                    print(f"... 还有 {len(stats['orphaned_documents']) - 10} 个")
        else:
            # 执行清理
            result = await cleaner.cleanup(dry_run=dry_run)
            
            print("\n=== 清理结果 ===")
            print(f"执行成功: {result.get('success', False)}")
            print(f"发现孤立chunks: {result.get('orphaned_chunks_found', 0)}")
            print(f"删除chunks: {result.get('orphaned_chunks_deleted', 0)}")
            print(f"执行时间: {result.get('execution_time', 0):.2f}秒")
            
            if result.get('error'):
                print(f"错误信息: {result['error']}")
        
    except Exception as e:
        logger.error(f"程序执行失败: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())