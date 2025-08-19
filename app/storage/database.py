"""
完整的MySQL数据库存储管理
"""
import pymysql
from typing import List, Dict, Optional, Any
import json
import logging
from app.core.config import get_settings

logger = logging.getLogger(__name__)

class DatabaseManager:
    """MySQL数据库管理器"""
    
    def __init__(self):
        """初始化MySQL数据库管理器"""
        self.settings = get_settings()
        self.connection_config = {
            'host': self.settings.mysql_host,
            'port': self.settings.mysql_port,
            'user': self.settings.mysql_user,
            'password': self.settings.mysql_password,
            'database': self.settings.mysql_database,
            'charset': 'utf8mb4',
            'autocommit': True
        }
        
        self._init_database()
        logger.info(f"MySQL数据库初始化完成: {self.settings.mysql_host}:{self.settings.mysql_port}")
    
    def _get_connection(self):
        """获取数据库连接"""
        return pymysql.connect(**self.connection_config)
    
    def _init_database(self):
        """初始化数据库表"""
        # 首先创建数据库（如果不存在）
        temp_config = self.connection_config.copy()
        temp_config.pop('database')
        
        try:
            with pymysql.connect(**temp_config) as conn:
                with conn.cursor() as cursor:
                    cursor.execute(f"CREATE DATABASE IF NOT EXISTS {self.settings.mysql_database} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
                    logger.info(f"数据库 {self.settings.mysql_database} 创建成功或已存在")
        except Exception as e:
            logger.error(f"创建数据库失败: {e}")
            raise
        
        # 创建表结构
        with self._get_connection() as conn:
            with conn.cursor() as cursor:
                # 文档表
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS documents (
                        id VARCHAR(255) PRIMARY KEY,
                        title VARCHAR(500) NOT NULL,
                        content LONGTEXT NOT NULL,
                        file_path VARCHAR(1000),
                        file_size BIGINT,
                        file_type VARCHAR(50),
                        vectorized BOOLEAN DEFAULT FALSE,
                        vectorization_status ENUM('pending', 'processing', 'completed', 'failed') DEFAULT 'pending',
                        vectorization_time TIMESTAMP NULL,
                        metadata JSON,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                        INDEX idx_created_at (created_at),
                        INDEX idx_file_type (file_type),
                        INDEX idx_vectorized (vectorized),
                        INDEX idx_vectorization_status (vectorization_status)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                """)
                
                # 会话表
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS sessions (
                        id VARCHAR(255) PRIMARY KEY,
                        user_id VARCHAR(255),
                        title VARCHAR(500),
                        metadata JSON,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                        is_active BOOLEAN DEFAULT TRUE,
                        INDEX idx_user_id (user_id),
                        INDEX idx_created_at (created_at),
                        INDEX idx_is_active (is_active)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                """)
                
                # 聊天记录表
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS chat_history (
                        id BIGINT AUTO_INCREMENT PRIMARY KEY,
                        session_id VARCHAR(255) NOT NULL,
                        question TEXT NOT NULL,
                        answer LONGTEXT NOT NULL,
                        sources JSON,
                        metadata JSON,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        INDEX idx_session_id (session_id),
                        INDEX idx_created_at (created_at),
                        FOREIGN KEY (session_id) REFERENCES sessions (id) ON DELETE CASCADE
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                """)
                
                # 搜索历史表
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS search_history (
                        id BIGINT AUTO_INCREMENT PRIMARY KEY,
                        session_id VARCHAR(255),
                        query TEXT NOT NULL,
                        results JSON,
                        result_count INT DEFAULT 0,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        INDEX idx_session_id (session_id),
                        INDEX idx_created_at (created_at),
                        FOREIGN KEY (session_id) REFERENCES sessions (id) ON DELETE SET NULL
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                """)
                
                logger.info("MySQL数据库表结构初始化完成")
    
    def save_document(self, doc_data: Dict[str, Any]) -> str:
        """保存文档信息"""
        with self._get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO documents 
                    (id, title, content, file_path, file_size, file_type, metadata)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                    title = VALUES(title),
                    content = VALUES(content),
                    file_path = VALUES(file_path),
                    file_size = VALUES(file_size),
                    file_type = VALUES(file_type),
                    metadata = VALUES(metadata),
                    updated_at = CURRENT_TIMESTAMP
                """, (
                    doc_data['id'],
                    doc_data['title'],
                    doc_data['content'],
                    doc_data.get('file_path'),
                    doc_data.get('file_size'),
                    doc_data.get('file_type'),
                    json.dumps(doc_data.get('metadata', {}), ensure_ascii=False)
                ))
                conn.commit()  # 确保事务立即提交
                
                logger.info(f"文档保存成功: {doc_data['id']}")
                return doc_data['id']
    
    def get_document(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """获取文档信息"""
        with self._get_connection() as conn:
            with conn.cursor(pymysql.cursors.DictCursor) as cursor:
                cursor.execute("SELECT * FROM documents WHERE id = %s", (doc_id,))
                row = cursor.fetchone()
                
                if row:
                    if row['metadata']:
                        row['metadata'] = json.loads(row['metadata']) if isinstance(row['metadata'], str) else row['metadata']
                    return row
                return None
    
    def list_documents(self, limit: int = 100) -> List[Dict[str, Any]]:
        """获取文档列表"""
        with self._get_connection() as conn:
            with conn.cursor(pymysql.cursors.DictCursor) as cursor:
                cursor.execute("""
                    SELECT id, title, file_type, file_size, created_at 
                    FROM documents 
                    ORDER BY created_at DESC 
                    LIMIT %s
                """, (limit,))
                
                return list(cursor.fetchall())
    
    def get_all_documents_content(self, limit: int = 1000) -> List[Dict[str, Any]]:
        """获取所有文档的完整内容，用于RAG工作流"""
        with self._get_connection() as conn:
            with conn.cursor(pymysql.cursors.DictCursor) as cursor:
                cursor.execute("""
                    SELECT id, title, content, file_path, file_type, metadata, created_at
                    FROM documents 
                    WHERE content IS NOT NULL AND content != ''
                    ORDER BY created_at DESC 
                    LIMIT %s
                """, (limit,))
                
                results = list(cursor.fetchall())
                
                # 解析metadata字段
                for doc in results:
                    if doc['metadata']:
                        doc['metadata'] = json.loads(doc['metadata']) if isinstance(doc['metadata'], str) else doc['metadata']
                
                return results
    
    def delete_document(self, doc_id: str) -> bool:
        """删除文档"""
        with self._get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("DELETE FROM documents WHERE id = %s", (doc_id,))
                
                deleted = cursor.rowcount > 0
                if deleted:
                    logger.info(f"文档删除成功: {doc_id}")
                return deleted
    
    def get_documents_by_status(self, vectorization_status: str = None, vectorized: bool = None, limit: int = 100) -> List[Dict[str, Any]]:
        """根据向量化状态获取文档列表"""
        with self._get_connection() as conn:
            with conn.cursor(pymysql.cursors.DictCursor) as cursor:
                conditions = []
                params = []
                
                if vectorization_status is not None:
                    conditions.append("vectorization_status = %s")
                    params.append(vectorization_status)
                
                if vectorized is not None:
                    conditions.append("vectorized = %s")
                    params.append(vectorized)
                
                where_clause = " WHERE " + " AND ".join(conditions) if conditions else ""
                
                query = f"""
                    SELECT id, title, file_path, file_type, file_size, vectorized, 
                           vectorization_status, vectorization_time, metadata, created_at
                    FROM documents{where_clause}
                    ORDER BY created_at DESC 
                    LIMIT %s
                """
                params.append(limit)
                
                cursor.execute(query, params)
                results = list(cursor.fetchall())
                
                # 解析metadata字段
                for doc in results:
                    if doc['metadata']:
                        doc['metadata'] = json.loads(doc['metadata']) if isinstance(doc['metadata'], str) else doc['metadata']
                
                return results
    
    def update_document(self, doc_id: str, update_data: Dict[str, Any]) -> bool:
        """更新文档信息"""
        with self._get_connection() as conn:
            with conn.cursor() as cursor:
                # 构建更新字段
                set_clauses = []
                params = []
                
                for key, value in update_data.items():
                    if key == 'metadata':
                        set_clauses.append(f"{key} = %s")
                        params.append(json.dumps(value, ensure_ascii=False))
                    else:
                        set_clauses.append(f"{key} = %s")
                        params.append(value)
                
                if not set_clauses:
                    return False
                
                set_clauses.append("updated_at = CURRENT_TIMESTAMP")
                params.append(doc_id)
                
                query = f"UPDATE documents SET {', '.join(set_clauses)} WHERE id = %s"
                cursor.execute(query, params)
                conn.commit()  # 确保事务立即提交
                
                updated = cursor.rowcount > 0
                if updated:
                    logger.info(f"文档更新成功: {doc_id}")
                return updated
    
    def save_session(self, session_data: Dict[str, Any]) -> str:
        """保存会话信息"""
        with self._get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO sessions 
                    (id, user_id, title, metadata)
                    VALUES (%s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                    user_id = VALUES(user_id),
                    title = VALUES(title),
                    metadata = VALUES(metadata),
                    updated_at = CURRENT_TIMESTAMP
                """, (
                    session_data['id'],
                    session_data.get('user_id'),
                    session_data.get('title'),
                    json.dumps(session_data.get('metadata', {}), ensure_ascii=False)
                ))
                conn.commit()  # 确保事务立即提交
                
                return session_data['id']
    
    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """获取会话信息"""
        with self._get_connection() as conn:
            with conn.cursor(pymysql.cursors.DictCursor) as cursor:
                cursor.execute("SELECT * FROM sessions WHERE id = %s", (session_id,))
                row = cursor.fetchone()
                
                if row:
                    if row['metadata']:
                        row['metadata'] = json.loads(row['metadata']) if isinstance(row['metadata'], str) else row['metadata']
                    return row
                return None
    
    def save_chat_history(self, chat_data: Dict[str, Any]) -> int:
        """保存聊天记录"""
        with self._get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO chat_history 
                    (session_id, question, answer, sources, metadata)
                    VALUES (%s, %s, %s, %s, %s)
                """, (
                    chat_data['session_id'],
                    chat_data['question'],
                    chat_data['answer'],
                    json.dumps(chat_data.get('sources', []), ensure_ascii=False),
                    json.dumps(chat_data.get('metadata', {}), ensure_ascii=False)
                ))
                conn.commit()  # 确保事务立即提交
                
                return cursor.lastrowid
    
    def get_chat_history(self, session_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """获取聊天历史"""
        with self._get_connection() as conn:
            with conn.cursor(pymysql.cursors.DictCursor) as cursor:
                cursor.execute("""
                    SELECT * FROM chat_history 
                    WHERE session_id = %s 
                    ORDER BY created_at ASC 
                    LIMIT %s
                """, (session_id, limit))
                
                history = []
                for row in cursor.fetchall():
                    if row['sources']:
                        row['sources'] = json.loads(row['sources']) if isinstance(row['sources'], str) else row['sources']
                    if row['metadata']:
                        row['metadata'] = json.loads(row['metadata']) if isinstance(row['metadata'], str) else row['metadata']
                    history.append(row)
                
                return history
    
    def save_search_history(self, search_data: Dict[str, Any]) -> int:
        """保存搜索历史"""
        with self._get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO search_history 
                    (session_id, query, results, result_count)
                    VALUES (%s, %s, %s, %s)
                """, (
                    search_data.get('session_id'),
                    search_data['query'],
                    json.dumps(search_data.get('results', []), ensure_ascii=False),
                    search_data.get('result_count', 0)
                ))
                
                return cursor.lastrowid
    
    def get_search_history(self, session_id: str = None, limit: int = 20) -> List[Dict[str, Any]]:
        """获取搜索历史"""
        with self._get_connection() as conn:
            with conn.cursor(pymysql.cursors.DictCursor) as cursor:
                if session_id:
                    cursor.execute("""
                        SELECT * FROM search_history 
                        WHERE session_id = %s 
                        ORDER BY created_at DESC 
                        LIMIT %s
                    """, (session_id, limit))
                else:
                    cursor.execute("""
                        SELECT * FROM search_history 
                        ORDER BY created_at DESC 
                        LIMIT %s
                    """, (limit,))
                
                history = []
                for row in cursor.fetchall():
                    if row['results']:
                        row['results'] = json.loads(row['results']) if isinstance(row['results'], str) else row['results']
                    history.append(row)
                
                return history
    
    def health_check(self) -> bool:
        """健康检查"""
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("SELECT 1")
                    return True
        except Exception as e:
            logger.error(f"MySQL健康检查失败: {e}")
            return False


# 全局数据库实例
db_manager = DatabaseManager()

def get_db_manager() -> DatabaseManager:
    """获取数据库管理器实例"""
    return db_manager