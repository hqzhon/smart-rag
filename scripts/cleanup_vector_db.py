#!/usr/bin/env python3
"""
向量数据库清理脚本
从MySQL数据库的documents表中获取所有文件，然后查询向量数据库，
删除MySQL中不存在的文件信息，防止数据干扰。
"""

import asyncio
import logging
from typing import Set, List, Dict, Any
import sys
import os

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.storage.database import DatabaseManager
from app.storage.vector_store import get_vector_store_async
from app.utils.logger import setup_logger

logger = setup_logger(__name__)

class VectorDBCleaner:
    """向量数据库清理器"""
    
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
    
    def get_mysql_document_ids(self) -> Set[str]:
        """从MySQL获取所有文档ID"""
        try:
            # 获取所有文档
            documents = self.db_manager.get_all_documents_content(limit=10000)
            document_ids = {doc['id'] for doc in documents}
            logger.info(f"从MySQL获取到 {len(document_ids)} 个文档ID")
            return document_ids
        except Exception as e:
            logger.error(f"获取MySQL文档ID失败: {str(e)}")
            return set()
    
    def get_vector_db_document_ids(self) -> Set[str]:
        """从向量数据库获取所有文档ID"""
        try:
            if not self.vector_store or not self.vector_store.collection:
                logger.warning("向量存储未初始化")
                return set()
            
            # 获取所有向量数据库中的数据
            results = self.vector_store.collection.get()
            
            if not results or not results.get('metadatas'):
                logger.info("向量数据库中没有数据")
                return set()
            
            # 从metadata中提取document_id
            document_ids = set()
            for metadata in results['metadatas']:
                if metadata and 'document_id' in metadata:
                    document_ids.add(metadata['document_id'])
            
            logger.info(f"从向量数据库获取到 {len(document_ids)} 个文档ID")
            return document_ids
            
        except Exception as e:
            logger.error(f"获取向量数据库文档ID失败: {str(e)}")
            return set()
    
    def get_orphaned_chunks(self, mysql_doc_ids: Set[str]) -> List[str]:
        """获取孤立的chunk ID（在向量数据库中但不在MySQL中的chunks）"""
        try:
            if not self.vector_store or not self.vector_store.collection:
                logger.warning("向量存储未初始化")
                return []
            
            # 获取所有向量数据库中的数据
            results = self.vector_store.collection.get()
            
            if not results or not results.get('ids') or not results.get('metadatas'):
                logger.info("向量数据库中没有数据")
                return []
            
            orphaned_chunk_ids = []
            
            # 检查每个chunk
            for i, (chunk_id, metadata) in enumerate(zip(results['ids'], results['metadatas'])):
                if metadata and 'document_id' in metadata:
                    doc_id = metadata['document_id']
                    # 如果文档ID不在MySQL中，则这个chunk是孤立的
                    if doc_id not in mysql_doc_ids:
                        orphaned_chunk_ids.append(chunk_id)
            
            logger.info(f"发现 {len(orphaned_chunk_ids)} 个孤立的chunks")
            return orphaned_chunk_ids
            
        except Exception as e:
            logger.error(f"获取孤立chunks失败: {str(e)}")
            return []
    
    def delete_orphaned_chunks(self, chunk_ids: List[str]) -> bool:
        """删除孤立的chunks"""
        if not chunk_ids:
            logger.info("没有需要删除的孤立chunks")
            return True
            
        try:
            if not self.vector_store or not self.vector_store.collection:
                logger.error("向量存储未初始化")
                return False
            
            # 分批删除，避免一次删除太多数据
            batch_size = 100
            total_deleted = 0
            
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
    
    async def cleanup(self, dry_run: bool = True) -> Dict[str, Any]:
        """执行清理操作
        
        Args:
            dry_run: 是否为试运行模式（不实际删除数据）
            
        Returns:
            清理结果统计
        """
        logger.info(f"开始向量数据库清理 (dry_run={dry_run})")
        
        # 获取MySQL中的文档ID
        mysql_doc_ids = self.get_mysql_document_ids()
        if not mysql_doc_ids:
            logger.warning("MySQL中没有文档，跳过清理")
            return {'status': 'skipped', 'reason': 'no_mysql_documents'}
        
        # 获取向量数据库中的文档ID
        vector_doc_ids = self.get_vector_db_document_ids()
        if not vector_doc_ids:
            logger.info("向量数据库中没有文档，无需清理")
            return {'status': 'completed', 'mysql_docs': len(mysql_doc_ids), 'vector_docs': 0, 'orphaned': 0, 'deleted': 0}
        
        # 找出孤立的文档ID
        orphaned_doc_ids = vector_doc_ids - mysql_doc_ids
        logger.info(f"发现 {len(orphaned_doc_ids)} 个孤立的文档ID: {list(orphaned_doc_ids)[:10]}{'...' if len(orphaned_doc_ids) > 10 else ''}")
        
        # 获取需要删除的chunk ID
        orphaned_chunk_ids = self.get_orphaned_chunks(mysql_doc_ids)
        
        result = {
            'status': 'completed',
            'mysql_docs': len(mysql_doc_ids),
            'vector_docs': len(vector_doc_ids),
            'orphaned_docs': len(orphaned_doc_ids),
            'orphaned_chunks': len(orphaned_chunk_ids),
            'deleted': 0
        }
        
        if not orphaned_chunk_ids:
            logger.info("没有发现孤立的chunks，数据库已经是干净的")
            return result
        
        if dry_run:
            logger.info(f"试运行模式：发现 {len(orphaned_chunk_ids)} 个孤立chunks，但不会实际删除")
            result['status'] = 'dry_run'
        else:
            # 实际删除孤立的chunks
            success = self.delete_orphaned_chunks(orphaned_chunk_ids)
            if success:
                result['deleted'] = len(orphaned_chunk_ids)
                logger.info(f"清理完成，删除了 {len(orphaned_chunk_ids)} 个孤立chunks")
            else:
                result['status'] = 'failed'
                logger.error("清理过程中发生错误")
        
        return result

async def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='向量数据库清理工具')
    parser.add_argument('--dry-run', action='store_true', default=True,
                       help='试运行模式，不实际删除数据（默认）')
    parser.add_argument('--force', action='store_true', default=False,
                       help='强制执行删除操作')
    parser.add_argument('--log-level', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
                       default='INFO', help='日志级别')
    
    args = parser.parse_args()
    
    # 设置日志级别
    logging.getLogger().setLevel(getattr(logging, args.log_level))
    
    # 确定运行模式
    dry_run = not args.force
    
    if dry_run:
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
    
    cleaner = VectorDBCleaner()
    
    try:
        await cleaner.initialize()
        result = await cleaner.cleanup(dry_run=dry_run)
        
        # 打印结果
        print("\n=== 清理结果 ===")
        print(f"状态: {result['status']}")
        print(f"MySQL文档数: {result['mysql_docs']}")
        print(f"向量数据库文档数: {result['vector_docs']}")
        print(f"孤立文档数: {result['orphaned_docs']}")
        print(f"孤立chunks数: {result['orphaned_chunks']}")
        print(f"已删除chunks数: {result['deleted']}")
        
        if result['status'] == 'dry_run' and result['orphaned_chunks'] > 0:
            print("\n使用 --force 参数来实际执行删除操作")
        
    except Exception as e:
        logger.error(f"清理过程中发生错误: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())