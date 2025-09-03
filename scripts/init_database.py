#!/usr/bin/env python3
"""
MySQL数据库初始化脚本
用于创建数据库、表结构和初始数据
"""

import os
import sys
import pymysql
import json
from pathlib import Path
from datetime import datetime

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.core.config import get_settings

def create_database():
    """创建数据库（如果不存在）"""
    settings = get_settings()
    
    # 不包含数据库名的连接配置
    temp_config = {
        'host': settings.mysql_host,
        'port': settings.mysql_port,
        'user': settings.mysql_user,
        'password': settings.mysql_password,
        'charset': 'utf8mb4'
    }
    
    try:
        print(f"🔗 连接到MySQL服务器 {settings.mysql_host}:{settings.mysql_port}...")
        with pymysql.connect(**temp_config) as conn:
            with conn.cursor() as cursor:
                # 创建数据库
                cursor.execute(f"CREATE DATABASE IF NOT EXISTS {settings.mysql_database} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
                print(f"✅ 数据库 '{settings.mysql_database}' 创建成功或已存在")
                
                # 显示数据库信息
                cursor.execute(f"SHOW CREATE DATABASE {settings.mysql_database}")
                result = cursor.fetchone()
                print(f"📊 数据库信息: {result[1]}")
                
    except Exception as e:
        print(f"❌ 创建数据库失败: {e}")
        raise

def create_tables():
    """创建数据表结构"""
    settings = get_settings()
    
    # 完整的连接配置
    mysql_config = {
        'host': settings.mysql_host,
        'port': settings.mysql_port,
        'user': settings.mysql_user,
        'password': settings.mysql_password,
        'database': settings.mysql_database,
        'charset': 'utf8mb4',
        'autocommit': True
    }
    
    try:
        print(f"🔗 连接到数据库 '{settings.mysql_database}'...")
        with pymysql.connect(**mysql_config) as conn:
            with conn.cursor() as cursor:
                
                print("📄 创建文档表 (documents)...")
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS documents (
                        id VARCHAR(255) PRIMARY KEY COMMENT '文档唯一标识',
                        title VARCHAR(500) NOT NULL COMMENT '文档标题',
                        content LONGTEXT NOT NULL COMMENT '文档内容',
                        file_path VARCHAR(1000) COMMENT '文件路径',
                        file_size BIGINT COMMENT '文件大小(字节)',
                        file_type VARCHAR(200) COMMENT '文件类型',
                        metadata JSON COMMENT '元数据',
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
                        status VARCHAR(50) DEFAULT 'uploading' COMMENT '文档状态',
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
                        vectorized BOOLEAN DEFAULT FALSE COMMENT '是否已向量化',
                        vectorization_status VARCHAR(50) DEFAULT 'pending' COMMENT '向量化状态',
                        metadata_generation_status VARCHAR(50) DEFAULT 'pending' COMMENT '元数据生成状态',
                        processed BOOLEAN DEFAULT FALSE COMMENT '是否已处理',
                        metadata_generation_completed_at TIMESTAMP NULL COMMENT '元数据生成完成时间',
                        INDEX idx_created_at (created_at),
                        INDEX idx_file_type (file_type),
                        INDEX idx_vectorized (vectorized),
                        INDEX idx_vectorization_status (vectorization_status),
                        INDEX idx_status (status),
                        INDEX idx_metadata_generation_status (metadata_generation_status)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='文档表'
                """)
                
                print("💬 创建会话表 (sessions)...")
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS sessions (
                        id VARCHAR(255) PRIMARY KEY COMMENT '会话唯一标识',
                        user_id VARCHAR(255) COMMENT '用户ID',
                        title VARCHAR(500) COMMENT '会话标题',
                        metadata JSON COMMENT '会话元数据',
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
                        is_active BOOLEAN DEFAULT TRUE COMMENT '是否活跃',
                        INDEX idx_user_id (user_id),
                        INDEX idx_created_at (created_at),
                        INDEX idx_is_active (is_active)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='会话表'
                """)
                
                print("💭 创建聊天记录表 (chat_history)...")
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS chat_history (
                        id BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '记录ID',
                        session_id VARCHAR(255) NOT NULL COMMENT '会话ID',
                        question TEXT NOT NULL COMMENT '用户问题',
                        answer LONGTEXT NOT NULL COMMENT 'AI回答',
                        sources JSON COMMENT '参考来源',
                        metadata JSON COMMENT '元数据',
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
                        INDEX idx_session_id (session_id),
                        INDEX idx_created_at (created_at),
                        FOREIGN KEY (session_id) REFERENCES sessions (id) ON DELETE CASCADE
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='聊天记录表'
                """)
                
                print("🔍 创建搜索历史表 (search_history)...")
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS search_history (
                        id BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '记录ID',
                        session_id VARCHAR(255) COMMENT '会话ID',
                        query TEXT NOT NULL COMMENT '搜索查询',
                        results JSON COMMENT '搜索结果',
                        result_count INT DEFAULT 0 COMMENT '结果数量',
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
                        INDEX idx_session_id (session_id),
                        INDEX idx_created_at (created_at),
                        FOREIGN KEY (session_id) REFERENCES sessions (id) ON DELETE SET NULL
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='搜索历史表'
                """)
                
                print("✅ 所有数据表创建完成")
                
    except Exception as e:
        print(f"❌ 创建数据表失败: {e}")
        raise

def show_table_info():
    """显示表结构信息"""
    settings = get_settings()
    
    mysql_config = {
        'host': settings.mysql_host,
        'port': settings.mysql_port,
        'user': settings.mysql_user,
        'password': settings.mysql_password,
        'database': settings.mysql_database,
        'charset': 'utf8mb4'
    }
    
    try:
        with pymysql.connect(**mysql_config) as conn:
            with conn.cursor() as cursor:
                print("\n📊 数据库表信息:")
                print("=" * 60)
                
                # 获取所有表
                cursor.execute("SHOW TABLES")
                tables = cursor.fetchall()
                
                for table in tables:
                    table_name = table[0]
                    print(f"\n📋 表名: {table_name}")
                    
                    # 获取表结构
                    cursor.execute(f"DESCRIBE {table_name}")
                    columns = cursor.fetchall()
                    
                    print("  字段信息:")
                    for col in columns:
                        field, type_, null, key, default, extra = col
                        key_info = f" [{key}]" if key else ""
                        print(f"    - {field}: {type_}{key_info}")
                    
                    # 获取表注释
                    cursor.execute(f"SHOW CREATE TABLE {table_name}")
                    create_sql = cursor.fetchone()[1]
                    if "COMMENT=" in create_sql:
                        comment = create_sql.split("COMMENT=")[-1].strip().strip("'")
                        print(f"  说明: {comment}")
                
    except Exception as e:
        print(f"❌ 获取表信息失败: {e}")

def test_connection():
    """测试数据库连接"""
    settings = get_settings()
    
    mysql_config = {
        'host': settings.mysql_host,
        'port': settings.mysql_port,
        'user': settings.mysql_user,
        'password': settings.mysql_password,
        'database': settings.mysql_database,
        'charset': 'utf8mb4'
    }
    
    try:
        print("🔍 测试数据库连接...")
        with pymysql.connect(**mysql_config) as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT VERSION()")
                version = cursor.fetchone()[0]
                print(f"✅ 数据库连接成功")
                print(f"📊 MySQL版本: {version}")
                
                cursor.execute("SELECT DATABASE()")
                db_name = cursor.fetchone()[0]
                print(f"📊 当前数据库: {db_name}")
                
                cursor.execute("SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = %s", (db_name,))
                table_count = cursor.fetchone()[0]
                print(f"📊 数据表数量: {table_count}")
                
                return True
                
    except Exception as e:
        print(f"❌ 数据库连接失败: {e}")
        return False

def insert_sample_data():
    """插入示例数据（可选）"""
    settings = get_settings()
    
    mysql_config = {
        'host': settings.mysql_host,
        'port': settings.mysql_port,
        'user': settings.mysql_user,
        'password': settings.mysql_password,
        'database': settings.mysql_database,
        'charset': 'utf8mb4',
        'autocommit': True
    }
    
    try:
        print("📝 插入示例数据...")
        with pymysql.connect(**mysql_config) as conn:
            with conn.cursor() as cursor:
                
                # 检查是否已有数据
                cursor.execute("SELECT COUNT(*) FROM sessions")
                session_count = cursor.fetchone()[0]
                
                if session_count == 0:
                    # 插入示例会话
                    sample_session_id = "sample_session_001"
                    cursor.execute("""
                        INSERT INTO sessions (id, user_id, title, metadata, is_active)
                        VALUES (%s, %s, %s, %s, %s)
                    """, (
                        sample_session_id,
                        "demo_user",
                        "示例会话",
                        json.dumps({"type": "demo", "created_by": "init_script"}),
                        True
                    ))
                    
                    print(f"  ✅ 插入示例会话: {sample_session_id}")
                else:
                    print(f"  ℹ️  已存在 {session_count} 个会话，跳过示例数据插入")
                
    except Exception as e:
        print(f"❌ 插入示例数据失败: {e}")

def main():
    """主函数"""
    print("🚀 MySQL数据库初始化工具")
    print("=" * 50)
    
    try:
        # 1. 创建数据库
        create_database()
        
        # 2. 创建表结构
        create_tables()
        
        # 3. 测试连接
        if test_connection():
            print("\n🎉 数据库初始化成功！")
        else:
            print("\n❌ 数据库初始化失败！")
            return False
        
        # 4. 显示表信息
        show_table_info()
        
        # 5. 询问是否插入示例数据
        if input("\n❓ 是否插入示例数据？(y/N): ").lower() == 'y':
            insert_sample_data()
        
        print("\n📝 后续步骤:")
        print("1. 检查数据库配置是否正确")
        print("2. 启动应用服务")
        print("3. 上传文档进行测试")
        print("4. 查看日志确认系统运行正常")
        
        return True
        
    except Exception as e:
        print(f"\n💥 初始化失败: {e}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)