"""
完整的MySQL数据库存储管理
"""
import pymysql
from typing import List, Dict, Optional, Any
import json
import logging
from app.core.config import get_settings
from app.core.singletons import SingletonMeta

logger = logging.getLogger(__name__)

class DatabaseManager(metaclass=SingletonMeta):
    """MySQL数据库管理器 - 单例模式"""
    
    def __init__(self):
        """初始化MySQL数据库管理器"""
        if hasattr(self, '_initialized'):
            return
            
        self.settings = get_settings()
        self.connection_config = {
            'host': self.settings.mysql_host,
            'port': self.settings.mysql_port,
            'user': self.settings.mysql_user,
            'password': self.settings.mysql_password,
            'database': self.settings.mysql_database,
            'charset': 'utf8mb4',
            'autocommit': True,
            'connect_timeout': 10,  # 连接超时10秒
            'read_timeout': 30,     # 读取超时30秒
            'write_timeout': 30     # 写入超时30秒
        }
        
        self._initialized = True
        logger.info(f"MySQL数据库管理器基础初始化完成: {self.settings.mysql_host}:{self.settings.mysql_port}")
    
    async def async_init(self):
        """异步初始化数据库连接和表结构"""
        logger.info("开始异步初始化数据库连接和表结构...")
        await self._init_database_async()
        logger.info("数据库异步初始化完成")
    
    async def _init_database_async(self):
        """异步初始化数据库表"""
        import asyncio
        
        def _sync_init():
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
            self._create_tables()
        
        # 在线程池中执行同步数据库操作
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, _sync_init)
    
    def _create_tables(self):
        """创建数据库表结构"""
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
                        file_type VARCHAR(200),
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
                        user_message LONGTEXT,
                        assistant_message LONGTEXT,
                        question LONGTEXT,
                        answer LONGTEXT,
                        sources JSON,
                        metadata JSON,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        INDEX idx_session_id (session_id),
                        INDEX idx_created_at (created_at),
                        FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                """)
                
                # 添加新字段（如果不存在）
                try:
                    cursor.execute("ALTER TABLE chat_history ADD COLUMN question LONGTEXT")
                    logger.info("添加question字段成功")
                except pymysql.Error as e:
                    if "Duplicate column name" not in str(e):
                        logger.warning(f"添加question字段失败: {e}")
                
                try:
                    cursor.execute("ALTER TABLE chat_history ADD COLUMN answer LONGTEXT")
                    logger.info("添加answer字段成功")
                except pymysql.Error as e:
                    if "Duplicate column name" not in str(e):
                        logger.warning(f"添加answer字段失败: {e}")
                
                try:
                    cursor.execute("ALTER TABLE chat_history ADD COLUMN sources JSON")
                    logger.info("添加sources字段成功")
                except pymysql.Error as e:
                    if "Duplicate column name" not in str(e):
                        logger.warning(f"添加sources字段失败: {e}")
                
                logger.info("数据库表结构创建完成")
    
    def _get_connection(self):
        """获取数据库连接"""
        return pymysql.connect(**self.connection_config)
    

    
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
    
    def list_documents(self, limit: int = 100, offset: int = 0) -> Dict[str, Any]:
        """获取文档列表（支持分页）
        
        Args:
            limit: 每页数量
            offset: 偏移量
            
        Returns:
            包含文档列表和总数的字典
        """
        with self._get_connection() as conn:
            with conn.cursor(pymysql.cursors.DictCursor) as cursor:
                # 获取总数
                cursor.execute("SELECT COUNT(*) as total FROM documents")
                total = cursor.fetchone()['total']
                
                # 获取分页数据
                cursor.execute("""
                    SELECT id, title, file_type, file_size, created_at 
                    FROM documents 
                    ORDER BY created_at DESC 
                    LIMIT %s OFFSET %s
                """, (limit, offset))
                
                documents = list(cursor.fetchall())
                
                return {
                    'documents': documents,
                    'total': total,
                    'page': (offset // limit) + 1,
                    'page_size': limit,
                    'total_pages': (total + limit - 1) // limit
                }
    
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
    
    async def get_all_documents_content_async(self, limit: int = 1000) -> List[Dict[str, Any]]:
        """异步获取所有文档的完整内容，用于RAG工作流"""
        import asyncio
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.get_all_documents_content, limit)
    
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
    
    def delete_session(self, session_id: str) -> bool:
        """删除会话（软删除）"""
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        UPDATE sessions 
                        SET is_active = 0, updated_at = CURRENT_TIMESTAMP
                        WHERE id = %s AND is_active = 1
                    """, (session_id,))
                    conn.commit()
                    
                    # 检查是否有行被更新
                    return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"删除会话失败: {e}")
            return False
    
    def update_session(self, session_id: str, update_data: Dict[str, Any], update_timestamp: bool = True) -> bool:
        """更新会话信息
        
        Args:
            session_id: 会话ID
            update_data: 要更新的数据字典，可包含title、metadata等字段
            update_timestamp: 是否更新updated_at时间戳，默认为True
            
        Returns:
            更新是否成功
        """
        try:
            if not update_data:
                return False
                
            # 构建更新字段
            set_clauses = []
            values = []
            
            for key, value in update_data.items():
                if key in ['title', 'metadata']:
                    set_clauses.append(f"{key} = %s")
                    if key == 'metadata':
                        values.append(json.dumps(value, ensure_ascii=False))
                    else:
                        values.append(value)
            
            if not set_clauses:
                return False
                
            # 根据参数决定是否更新时间戳
            if update_timestamp:
                set_clauses.append("updated_at = CURRENT_TIMESTAMP")
            else:
                # 不更新时间戳时，明确保持原有时间戳以覆盖MySQL的ON UPDATE CURRENT_TIMESTAMP
                set_clauses.append("updated_at = updated_at")
            values.append(session_id)
            
            with self._get_connection() as conn:
                with conn.cursor() as cursor:
                    query = f"""
                        UPDATE sessions 
                        SET {', '.join(set_clauses)}
                        WHERE id = %s AND is_active = 1
                    """
                    cursor.execute(query, values)
                    conn.commit()
                    
                    # 检查是否有行被更新
                    return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"更新会话失败: {e}")
            return False
    
    def get_sessions(self, page: int = 1, page_size: int = 10, include_empty: bool = False) -> Dict[str, Any]:
        """获取会话列表
        
        Args:
            page: 页码
            page_size: 每页数量
            include_empty: 是否包含空会话（新建但未发送消息的会话）
            
        Returns:
            包含会话列表和总数的字典
        """
        try:
            offset = (page - 1) * page_size
            
            with self._get_connection() as conn:
                with conn.cursor(pymysql.cursors.DictCursor) as cursor:
                    # 根据include_empty参数决定过滤条件
                    if include_empty:
                        # 包含所有会话，不过滤空会话
                        cursor.execute("""
                            SELECT COUNT(*) as total
                            FROM sessions s
                            WHERE s.is_active = 1
                        """)
                        total_count = cursor.fetchone()['total']
                        
                        cursor.execute("""
                            SELECT 
                                s.id as session_id,
                                s.title,
                                s.created_at,
                                s.updated_at,
                                s.metadata,
                                COALESCE(COUNT(ch.id), 0) as message_count,
                                CASE WHEN COUNT(ch.id) > 0 THEN 'active' ELSE 'empty' END as status
                            FROM sessions s
                            LEFT JOIN chat_history ch ON s.id = ch.session_id
                            WHERE s.is_active = 1
                            GROUP BY s.id, s.title, s.created_at, s.updated_at, s.metadata
                            ORDER BY s.updated_at DESC
                            LIMIT %s OFFSET %s
                        """, (page_size, offset))
                    else:
                        # 只获取有消息的会话（原有逻辑）
                        cursor.execute("""
                            SELECT COUNT(*) as total
                            FROM (
                                SELECT s.id
                                FROM sessions s
                                LEFT JOIN chat_history ch ON s.id = ch.session_id
                                WHERE s.is_active = 1
                                GROUP BY s.id
                                HAVING COUNT(ch.id) > 0
                            ) as filtered_sessions
                        """)
                        total_count = cursor.fetchone()['total']
                        
                        cursor.execute("""
                            SELECT 
                                s.id as session_id,
                                s.title,
                                s.created_at,
                                s.updated_at,
                                s.metadata,
                                COUNT(ch.id) as message_count,
                                'active' as status
                            FROM sessions s
                            LEFT JOIN chat_history ch ON s.id = ch.session_id
                            WHERE s.is_active = 1
                            GROUP BY s.id, s.title, s.created_at, s.updated_at, s.metadata
                            HAVING COUNT(ch.id) > 0
                            ORDER BY s.updated_at DESC
                            LIMIT %s OFFSET %s
                        """, (page_size, offset))
                    
                    sessions = []
                    for row in cursor.fetchall():
                        if row['metadata']:
                            row['metadata'] = json.loads(row['metadata']) if isinstance(row['metadata'], str) else row['metadata']
                        sessions.append(row)
                    
                    return {
                        'sessions': sessions,
                        'total': total_count,
                        'page': page,
                        'page_size': page_size
                    }
                    
        except Exception as e:
            logger.error(f"获取会话列表失败: {e}")
            return {'sessions': [], 'total': 0, 'page': page, 'page_size': page_size}
    
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


# 全局数据库管理器实例
db_manager = DatabaseManager()

def get_db_manager() -> DatabaseManager:
    """获取数据库管理器实例（同步版本，已废弃）"""
    return db_manager

async def get_db_manager_async() -> DatabaseManager:
    """异步获取数据库管理器实例"""
    await db_manager.async_init()
    return db_manager