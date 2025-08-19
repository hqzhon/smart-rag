#!/usr/bin/env python3
"""
MySQL数据库迁移脚本
将SQLite数据迁移到MySQL
"""

import os
import sys
import sqlite3
import pymysql
import json
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.core.config import get_settings

def migrate_sqlite_to_mysql():
    """将SQLite数据迁移到MySQL"""
    settings = get_settings()
    
    # SQLite数据库路径
    sqlite_db_path = "./data/medical_rag.db"
    
    if not os.path.exists(sqlite_db_path):
        print("❌ SQLite数据库文件不存在，跳过迁移")
        return
    
    print("🔄 开始从SQLite迁移数据到MySQL...")
    
    # MySQL连接配置
    mysql_config = {
        'host': settings.mysql_host,
        'port': settings.mysql_port,
        'user': settings.mysql_user,
        'password': settings.mysql_password,
        'database': settings.mysql_database,
        'charset': 'utf8mb4'
    }
    
    try:
        # 连接SQLite
        sqlite_conn = sqlite3.connect(sqlite_db_path)
        sqlite_conn.row_factory = sqlite3.Row
        
        # 连接MySQL
        mysql_conn = pymysql.connect(**mysql_config)
        
        print("✅ 数据库连接成功")
        
        # 迁移文档表
        migrate_documents(sqlite_conn, mysql_conn)
        
        # 迁移会话表
        migrate_sessions(sqlite_conn, mysql_conn)
        
        # 迁移聊天记录表
        migrate_chat_history(sqlite_conn, mysql_conn)
        
        # 迁移搜索历史表
        migrate_search_history(sqlite_conn, mysql_conn)
        
        print("✅ 数据迁移完成")
        
    except Exception as e:
        print(f"❌ 迁移失败: {e}")
        raise
    finally:
        if 'sqlite_conn' in locals():
            sqlite_conn.close()
        if 'mysql_conn' in locals():
            mysql_conn.close()

def migrate_documents(sqlite_conn, mysql_conn):
    """迁移文档表"""
    print("📄 迁移文档表...")
    
    sqlite_cursor = sqlite_conn.cursor()
    mysql_cursor = mysql_conn.cursor()
    
    # 获取SQLite数据
    sqlite_cursor.execute("SELECT * FROM documents")
    rows = sqlite_cursor.fetchall()
    
    if not rows:
        print("  - 文档表为空，跳过")
        return
    
    # 插入MySQL
    for row in rows:
        mysql_cursor.execute("""
            INSERT INTO documents 
            (id, title, content, file_path, file_size, file_type, metadata, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
            title = VALUES(title),
            content = VALUES(content),
            updated_at = VALUES(updated_at)
        """, (
            row['id'], row['title'], row['content'], 
            row['file_path'], row['file_size'], row['file_type'],
            row['metadata'], row['created_at'], row['updated_at']
        ))
    
    mysql_conn.commit()
    print(f"  - 迁移了 {len(rows)} 条文档记录")

def migrate_sessions(sqlite_conn, mysql_conn):
    """迁移会话表"""
    print("💬 迁移会话表...")
    
    sqlite_cursor = sqlite_conn.cursor()
    mysql_cursor = mysql_conn.cursor()
    
    # 获取SQLite数据
    sqlite_cursor.execute("SELECT * FROM sessions")
    rows = sqlite_cursor.fetchall()
    
    if not rows:
        print("  - 会话表为空，跳过")
        return
    
    # 插入MySQL
    for row in rows:
        mysql_cursor.execute("""
            INSERT INTO sessions 
            (id, user_id, title, metadata, created_at, updated_at, is_active)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
            title = VALUES(title),
            metadata = VALUES(metadata),
            updated_at = VALUES(updated_at)
        """, (
            row['id'], row['user_id'], row['title'],
            row['metadata'], row['created_at'], row['updated_at'],
            bool(row['is_active'])
        ))
    
    mysql_conn.commit()
    print(f"  - 迁移了 {len(rows)} 条会话记录")

def migrate_chat_history(sqlite_conn, mysql_conn):
    """迁移聊天记录表"""
    print("💭 迁移聊天记录表...")
    
    sqlite_cursor = sqlite_conn.cursor()
    mysql_cursor = mysql_conn.cursor()
    
    # 获取SQLite数据
    sqlite_cursor.execute("SELECT * FROM chat_history")
    rows = sqlite_cursor.fetchall()
    
    if not rows:
        print("  - 聊天记录表为空，跳过")
        return
    
    # 插入MySQL
    for row in rows:
        mysql_cursor.execute("""
            INSERT INTO chat_history 
            (session_id, question, answer, sources, metadata, created_at)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (
            row['session_id'], row['question'], row['answer'],
            row['sources'], row['metadata'], row['created_at']
        ))
    
    mysql_conn.commit()
    print(f"  - 迁移了 {len(rows)} 条聊天记录")

def migrate_search_history(sqlite_conn, mysql_conn):
    """迁移搜索历史表"""
    print("🔍 迁移搜索历史表...")
    
    sqlite_cursor = sqlite_conn.cursor()
    mysql_cursor = mysql_conn.cursor()
    
    # 获取SQLite数据
    sqlite_cursor.execute("SELECT * FROM search_history")
    rows = sqlite_cursor.fetchall()
    
    if not rows:
        print("  - 搜索历史表为空，跳过")
        return
    
    # 插入MySQL
    for row in rows:
        mysql_cursor.execute("""
            INSERT INTO search_history 
            (session_id, query, results, result_count, created_at)
            VALUES (%s, %s, %s, %s, %s)
        """, (
            row['session_id'], row['query'], row['results'],
            row['result_count'], row['created_at']
        ))
    
    mysql_conn.commit()
    print(f"  - 迁移了 {len(rows)} 条搜索记录")

if __name__ == "__main__":
    print("🚀 MySQL数据库迁移工具")
    print("=" * 50)
    
    try:
        migrate_sqlite_to_mysql()
        print("\n🎉 迁移成功完成！")
        print("\n📝 后续步骤：")
        print("1. 验证MySQL数据完整性")
        print("2. 备份SQLite数据库文件")
        print("3. 更新应用配置使用MySQL")
        print("4. 重启应用服务")
        
    except Exception as e:
        print(f"\n💥 迁移失败: {e}")
        sys.exit(1)