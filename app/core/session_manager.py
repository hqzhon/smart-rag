"""
会话管理器
"""

import time
from typing import Dict, Any, List, Optional
from app.utils.logger import setup_logger
from app.core.singletons import SingletonMeta

logger = setup_logger(__name__)


class SessionManager(metaclass=SingletonMeta):
    """会话管理器，解决并发安全问题"""
    
    def __init__(self):
        if hasattr(self, '_initialized'):
            return
            
        self.sessions = {}
        self.last_cleanup = time.time()
        self.cleanup_interval = 300  # 5分钟清理一次
        self._initialized = True
    
    async def create_session(self, session_id: str, documents: List[Dict[str, Any]]) -> bool:
        """创建新会话，使用已存在的向量数据库
        
        Args:
            session_id: 会话ID
            documents: 处理后的文档列表（用于检查是否有可用文档）
            
        Returns:
            创建是否成功
        """
        try:
            # 延迟导入避免循环依赖
            from app.embeddings.embeddings import get_embeddings
            from app.storage.vector_store import VectorStore
            from app.retrieval.fusion_retriever import AdvancedFusionRetriever, create_advanced_fusion_retriever
            from app.retrieval.enhanced_reranker import EnhancedReranker, create_enhanced_reranker
            from app.retrieval.query_transformer import QueryTransformer
            from app.workflow.enhanced_rag_workflow import EnhancedRAGWorkflow
            
            # 初始化嵌入模型
            embedding_model = get_embeddings()
            
            # 初始化向量存储（直接使用已存在的向量数据库）
            vector_store = VectorStore(embedding_model)
            
            # 检查是否有已向量化的文档
            vectorized_documents = [doc for doc in documents if doc.get('vectorized', False)]
            
            if vectorized_documents:
                logger.info(f"会话 {session_id} 将使用 {len(vectorized_documents)} 个已向量化的文档")
            else:
                logger.info(f"会话 {session_id} 创建成功，当前无已向量化文档，用户可以直接开始对话")
            
            # 准备文档格式（仅用于检索器初始化，不进行重复向量化）
            formatted_documents = []
            for doc in vectorized_documents:
                formatted_doc = {
                    "content": doc.get("content", ""),
                    "metadata": {
                        "document_id": doc.get("id"),
                        "title": doc.get("title", ""),
                        "file_type": doc.get("file_type", ""),
                        "file_path": doc.get("file_path", ""),
                        "created_at": doc.get("created_at").isoformat() if doc.get("created_at") and hasattr(doc.get("created_at"), 'isoformat') else str(doc.get("created_at")) if doc.get("created_at") else None
                    }
                }
                # 合并原有的metadata，但确保所有值都是基本类型
                if doc.get("metadata") and isinstance(doc["metadata"], dict):
                    for key, value in doc["metadata"].items():
                        # 只添加基本类型的值，避免列表类型
                        if isinstance(value, (str, int, float, bool)) or value is None:
                            formatted_doc["metadata"][key] = value
                        elif isinstance(value, list):
                            # 将列表转换为长度
                            formatted_doc["metadata"][f"{key}_count"] = len(value)
                
                formatted_documents.append(formatted_doc)
            
            # 不再重复向量化，直接使用现有的向量存储
            # vector_store.add_documents(formatted_documents)  # 移除这行
            
            # 初始化查询转换器
            query_transformer = QueryTransformer()
            
            # 初始化检索器 - 使用最新的优化逻辑
            retriever = await create_advanced_fusion_retriever(
                vector_store=vector_store,
                documents=formatted_documents,
                config_name='balanced',
                enable_all_optimizations=True
            )
            
            # 初始化重排序器 - 使用增强版本
            reranker = create_enhanced_reranker(
                strategy='qianwen_api',
                enable_cache=True
            )
            
            # 初始化增强版RAG工作流
            rag_workflow = EnhancedRAGWorkflow(retriever, reranker, query_transformer)
            
            # 存储会话信息
            self.sessions[session_id] = {
                "workflow": rag_workflow,
                "documents": formatted_documents,
                "created_at": time.time()
            }
            
            logger.info(f"会话 {session_id} 创建成功，使用现有向量数据库")
            return True
            
        except Exception as e:
            logger.error(f"创建会话 {session_id} 时出错: {str(e)}")
            return False
    
    def get_workflow(self, session_id: str):
        """获取会话的工作流实例
        
        Args:
            session_id: 会话ID
            
        Returns:
            RAG工作流实例或None
        """
        session = self.sessions.get(session_id)
        return session["workflow"] if session else None
    
    def remove_session(self, session_id: str) -> bool:
        """从内存中移除会话
        
        Args:
            session_id: 会话ID
            
        Returns:
            是否成功移除
        """
        try:
            if session_id in self.sessions:
                del self.sessions[session_id]
                logger.info(f"从内存中移除会话: {session_id}")
                return True
            else:
                logger.warning(f"尝试移除不存在的会话: {session_id}")
                return False
        except Exception as e:
            logger.error(f"移除会话失败: {str(e)}")
            return False
    

    
    def cleanup_expired_sessions(self, max_age: int = 3600):
        """清理过期会话
        
        Args:
            max_age: 最大会话年龄（秒）
        """
        current_time = time.time()
        
        # 检查是否需要清理
        if current_time - self.last_cleanup < self.cleanup_interval:
            return
        
        expired_sessions = []
        for session_id, session_info in self.sessions.items():
            if current_time - session_info["created_at"] > max_age:
                expired_sessions.append(session_id)
        
        # 删除过期会话
        for session_id in expired_sessions:
            del self.sessions[session_id]
            logger.info(f"清理过期会话: {session_id}")
        
        self.last_cleanup = current_time
    
    def get_session_count(self) -> int:
        """获取当前会话数量"""
        return len(self.sessions)