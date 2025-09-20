#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
为parent_chunks表添加性能优化索引的脚本

该脚本会为parent_chunks表添加以下索引：
1. idx_created_at - 基于创建时间的索引，用于时间排序查询
2. idx_document_created - 复合索引(document_id, created_at)，用于按文档ID和时间的组合查询

使用方法：
    python scripts/add_parent_chunks_indexes.py
"""

import sys
import os
import logging
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.storage.database import get_db_manager
from app.core.config import get_settings

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def add_parent_chunks_indexes():
    """
    为parent_chunks表添加性能优化索引
    """
    try:
        logger.info("开始为parent_chunks表添加索引...")
        
        # 获取数据库管理器
        db_manager = get_db_manager()
        
        with db_manager._get_connection() as conn:
            with conn.cursor() as cursor:
                # 检查表是否存在
                cursor.execute("""
                    SELECT COUNT(*) 
                    FROM information_schema.tables 
                    WHERE table_schema = DATABASE() 
                    AND table_name = 'parent_chunks'
                """)
                
                if cursor.fetchone()[0] == 0:
                    logger.error("parent_chunks表不存在，请先运行数据库初始化脚本")
                    return False
                
                # 检查并添加idx_created_at索引
                logger.info("检查idx_created_at索引...")
                cursor.execute("""
                    SELECT COUNT(*) 
                    FROM information_schema.statistics 
                    WHERE table_schema = DATABASE() 
                    AND table_name = 'parent_chunks' 
                    AND index_name = 'idx_created_at'
                """)
                
                if cursor.fetchone()[0] == 0:
                    logger.info("添加idx_created_at索引...")
                    cursor.execute("""
                        ALTER TABLE parent_chunks 
                        ADD INDEX idx_created_at (created_at)
                    """)
                    logger.info("idx_created_at索引添加成功")
                else:
                    logger.info("idx_created_at索引已存在，跳过")
                
                # 检查并添加idx_document_created复合索引
                logger.info("检查idx_document_created索引...")
                cursor.execute("""
                    SELECT COUNT(*) 
                    FROM information_schema.statistics 
                    WHERE table_schema = DATABASE() 
                    AND table_name = 'parent_chunks' 
                    AND index_name = 'idx_document_created'
                """)
                
                if cursor.fetchone()[0] == 0:
                    logger.info("添加idx_document_created复合索引...")
                    cursor.execute("""
                        ALTER TABLE parent_chunks 
                        ADD INDEX idx_document_created (document_id, created_at)
                    """)
                    logger.info("idx_document_created索引添加成功")
                else:
                    logger.info("idx_document_created索引已存在，跳过")
                
                # 显示当前所有索引
                logger.info("当前parent_chunks表的索引：")
                cursor.execute("""
                    SHOW INDEX FROM parent_chunks
                """)
                
                indexes = cursor.fetchall()
                for index in indexes:
                    logger.info(f"  - {index[2]} ({index[4]}): {index[10]}")
                
                logger.info("索引添加完成！")
                return True
                
    except Exception as e:
        logger.error(f"添加索引失败: {e}")
        return False

def main():
    """
    主函数
    """
    try:
        # 检查配置
        settings = get_settings()
        logger.info(f"连接数据库: {settings.mysql_host}:{settings.mysql_port}/{settings.mysql_database}")
        
        # 添加索引
        success = add_parent_chunks_indexes()
        
        if success:
            logger.info("✅ 索引添加成功！")
            print("\n🎉 parent_chunks表索引优化完成！")
            print("\n新增索引：")
            print("  1. idx_created_at - 基于创建时间的索引")
            print("  2. idx_document_created - 复合索引(document_id, created_at)")
            print("\n这些索引将显著提升以下查询的性能：")
            print("  - 按文档ID获取大块信息")
            print("  - 按时间排序的查询")
            print("  - 文档ID和时间的组合查询")
        else:
            logger.error("❌ 索引添加失败！")
            sys.exit(1)
            
    except Exception as e:
        logger.error(f"脚本执行失败: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()