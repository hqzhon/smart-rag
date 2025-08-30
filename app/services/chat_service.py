"""
聊天服务
"""

import uuid
import asyncio
from typing import Dict, Any, Optional, AsyncGenerator
from datetime import datetime

from app.models.query_models import QueryRequest, QueryResponse, ChatMessage
from app.models.session_models import Session, SessionStatus
from app.core.session_manager import SessionManager
from app.workflow.deepseek_client import get_deepseek_client
from app.workflow.qianwen_client import get_qianwen_client
from app.utils.logger import setup_logger

logger = setup_logger(__name__)


class ChatService:
    """聊天服务类，处理对话相关的业务逻辑"""
    
    def __init__(self):
        """初始化聊天服务"""
        self.session_manager = SessionManager()
        self.db = None
        self.documents_content = None
        logger.info("聊天服务基础初始化完成")
    
    async def async_init(self):
        """异步初始化重量级组件"""
        logger.info("开始异步初始化聊天服务重量级组件...")
        self.db = await self._get_db_manager()
        self.documents_content = await self._get_documents_content()
        logger.info("聊天服务异步初始化完成")
    
    async def _get_db_manager(self):
        """异步获取数据库管理器"""
        from app.storage.database import get_db_manager_async
        return await get_db_manager_async()
    
    async def _get_documents_content(self):
        """异步获取文档内容"""
        if self.db:
            return await self.db.get_all_documents_content_async()
        return []
    
    async def create_session(self, user_id: str = None) -> str:
        """创建聊天会话，自动关联所有可用文档
        
        Args:
            user_id: 用户ID
            
        Returns:
            会话ID
        """
        try:
            session_id = str(uuid.uuid4())
            
            # 自动获取所有可用文档
            from app.storage.database import get_db_manager
            db = get_db_manager()
            documents = db.get_all_documents_content()
            
            # 创建会话，即使没有文档也允许创建
            success = await self.session_manager.create_session(session_id, documents or [])
            if not success:
                raise Exception("创建会话失败")
            
            # 保存会话到数据库
            session_data = {
                'id': session_id,
                'user_id': user_id,
                'title': f'会话 {session_id[:8]}',
                'metadata': {
                    'document_count': len(documents) if documents else 0,
                    'created_by': 'chat_service',
                    'auto_created': True
                }
            }
            db.save_session(session_data)
            
            if documents:
                logger.info(f"聊天会话创建成功，关联了 {len(documents)} 个文档: {session_id}")
            else:
                logger.info(f"聊天会话创建成功，当前无可用文档，用户可以直接开始对话: {session_id}")
            
            return session_id
            
        except Exception as e:
            logger.error(f"创建聊天会话失败: {str(e)}")
            raise
    
    async def process_query(self, request: QueryRequest) -> QueryResponse:
        """处理用户查询
        
        Args:
            request: 查询请求
            
        Returns:
            查询响应
        """
        try:
            start_time = datetime.now()
            
            # 获取会话的工作流
            workflow = self.session_manager.get_workflow(request.session_id)
            
            # 如果内存中没有会话，尝试从数据库重新加载
            if not workflow:
                from app.storage.database import get_db_manager
                db = get_db_manager()
                session_data = db.get_session(request.session_id)
                
                if not session_data:
                    raise Exception(f"会话不存在: {request.session_id}")
                
                # 重新创建内存中的会话
                documents = db.get_all_documents_content()
                success = await self.session_manager.create_session(request.session_id, documents or [])
                if not success:
                    raise Exception(f"无法重新创建会话: {request.session_id}")
                
                workflow = self.session_manager.get_workflow(request.session_id)
                if not workflow:
                    raise Exception(f"重新创建会话失败: {request.session_id}")
                
                logger.info(f"从数据库重新加载会话: {request.session_id}")
            
            # 处理查询
            result = await workflow.process_query(request.query, request.session_id)
            
            # 计算处理时间
            processing_time = (datetime.now() - start_time).total_seconds()
            
            # 构建响应
            response = QueryResponse(
                query=request.query,
                response=result["response"],
                documents=result["documents"],
                sources=result.get("sources", [])[:3] if result.get("sources") else [],  # 添加前3个来源
                session_id=request.session_id,
                processing_time=processing_time,
                metadata=result.get("metadata", {})
            )
            
            # 保存聊天记录到数据库
            try:
                from app.storage.database import get_db_manager
                db = get_db_manager()
                
                chat_data = {
                    'session_id': request.session_id,
                    'question': request.query,
                    'answer': result["response"],
                    'sources': result.get("sources", [])[:3] if result.get("sources") else [],
                    'metadata': {
                        'processing_time': processing_time,
                        'document_count': len(result["documents"]),
                        'timestamp': datetime.now().isoformat(),
                        **result.get("metadata", {})
                    }
                }
                
                db.save_chat_history(chat_data)
                logger.info(f"聊天记录已保存: {request.session_id}")
                
            except Exception as save_error:
                logger.error(f"保存聊天记录失败: {str(save_error)}")
                # 不影响主流程，继续返回响应
            
            logger.info(f"查询处理完成: {request.query[:50]}...")
            return response
            
        except Exception as e:
            logger.error(f"查询处理失败: {str(e)}")
            
            # 返回错误响应
            return QueryResponse(
                query=request.query,
                response=f"抱歉，处理您的查询时出现错误: {str(e)}",
                documents=[],
                sources=[],
                session_id=request.session_id or "unknown",
                processing_time=0.0
            )
    
    async def stream_query(self, request: QueryRequest) -> AsyncGenerator[Dict[str, Any], None]:
        """流式处理查询
        
        Args:
            request: 查询请求
            
        Yields:
            流式响应数据
        """
        try:
            # 获取会话的工作流
            workflow = self.session_manager.get_workflow(request.session_id)
            if not workflow:
                yield {
                    "type": "error",
                    "message": f"会话不存在或未初始化: {request.session_id}"
                }
                return
            
            # 流式处理查询
            async for chunk in workflow.stream_process_query(request.query, request.session_id):
                yield chunk
                
        except Exception as e:
            logger.error(f"流式查询处理失败: {str(e)}")
            yield {
                "type": "error",
                "message": f"处理查询时出现错误: {str(e)}"
            }
    
    async def get_session_info(self, session_id: str) -> Optional[Dict[str, Any]]:
        """获取会话信息
        
        Args:
            session_id: 会话ID
            
        Returns:
            会话信息或None
        """
        try:
            # 首先从数据库获取会话信息
            from app.storage.database import get_db_manager
            db = get_db_manager()
            session_data = db.get_session(session_id)
            
            if not session_data:
                return None
            
            # 检查内存中的会话是否存在（用于确定状态）
            workflow = self.session_manager.get_workflow(session_id)
            status = "active" if workflow else "inactive"
            
            # 获取会话统计信息
            session_count = self.session_manager.get_session_count()
            
            return {
                "session_id": session_id,
                "status": status,
                "title": session_data.get("title", f"会话 {session_id[:8]}"),
                "total_sessions": session_count,
                "created_at": session_data.get("created_at").isoformat() if session_data.get("created_at") else datetime.now().isoformat(),
                "metadata": session_data.get("metadata", {})
            }
            
        except Exception as e:
            logger.error(f"获取会话信息失败: {str(e)}")
            return None
    
    async def close_session(self, session_id: str) -> bool:
        """关闭会话
        
        Args:
            session_id: 会话ID
            
        Returns:
            关闭是否成功
        """
        try:
            # TODO: 实现会话关闭逻辑
            logger.info(f"会话关闭: {session_id}")
            return True
            
        except Exception as e:
            logger.error(f"关闭会话失败: {str(e)}")
            return False
    
    async def add_message(self, session_id: str, message: str, message_type: str = "user") -> ChatMessage:
        """添加消息到会话
        
        Args:
            session_id: 会话ID
            message: 消息内容
            message_type: 消息类型
            
        Returns:
            聊天消息对象
        """
        try:
            chat_message = ChatMessage(
                id=str(uuid.uuid4()),
                session_id=session_id,
                message_type=message_type,
                content=message,
                timestamp=datetime.now()
            )
            
            # 保存聊天记录到数据库
            from app.storage.database import get_db_manager
            db = get_db_manager()
            
            chat_data = {
                'session_id': session_id,
                'question': message if message_type == "user" else "",
                'answer': message if message_type == "assistant" else "",
                'sources': [],
                'metadata': {
                    'message_type': message_type,
                    'timestamp': datetime.now().isoformat()
                }
            }
            
            if message_type in ["user", "assistant"]:
                db.save_chat_history(chat_data)
            
            logger.info(f"消息添加成功: {session_id}")
            return chat_message
            
        except Exception as e:
            logger.error(f"添加消息失败: {str(e)}")
            raise
    
    async def get_chat_history(self, session_id: str, limit: int = 50) -> list:
        """获取聊天历史
        
        Args:
            session_id: 会话ID
            limit: 限制数量
            
        Returns:
            聊天消息列表
        """
        try:
            # 从数据库获取聊天历史
            from app.storage.database import get_db_manager
            db = get_db_manager()
            return db.get_chat_history(session_id, limit)
            
        except Exception as e:
            logger.error(f"获取聊天历史失败: {str(e)}")
            return []
    

    
    async def delete_session(self, session_id: str) -> bool:
        """删除会话
        
        Args:
            session_id: 会话ID
            
        Returns:
            删除是否成功
        """
        try:
            # 从数据库删除会话
            from app.storage.database import get_db_manager
            db = get_db_manager()
            
            # 软删除：将is_active设为0
            success = db.delete_session(session_id)
            
            if success:
                # 从内存中清理会话
                self.session_manager.remove_session(session_id)
                logger.info(f"会话删除成功: {session_id}")
                return True
            else:
                logger.warning(f"会话删除失败，会话可能不存在: {session_id}")
                return False
                
        except Exception as e:
            logger.error(f"删除会话失败: {str(e)}")
            return False
    
    async def update_session(self, session_id: str, title: str = None, metadata: dict = None) -> bool:
        """更新会话信息
        
        Args:
            session_id: 会话ID
            title: 新标题
            metadata: 新元数据
            
        Returns:
            更新是否成功
        """
        try:
            # 更新数据库中的会话信息
            from app.storage.database import get_db_manager
            db = get_db_manager()
            
            update_data = {}
            if title is not None:
                update_data['title'] = title
            if metadata is not None:
                update_data['metadata'] = metadata
                
            if not update_data:
                logger.warning(f"没有提供更新数据: {session_id}")
                return False
                
            success = db.update_session(session_id, update_data)
            
            if success:
                logger.info(f"会话更新成功: {session_id}")
                return True
            else:
                logger.warning(f"会话更新失败，会话可能不存在: {session_id}")
                return False
                
        except Exception as e:
            logger.error(f"更新会话失败: {str(e)}")
            return False
    
    async def get_sessions(self, page: int = 1, page_size: int = 10) -> dict:
        """获取会话列表
        
        Args:
            page: 页码
            page_size: 每页数量
            
        Returns:
            包含会话列表和分页信息的字典
        """
        try:
            # 从数据库获取会话列表
            from app.storage.database import get_db_manager
            db = get_db_manager()
            
            result = db.get_sessions(page=page, page_size=page_size)
            sessions = result.get('sessions', [])
            
            # 转换为前端需要的格式
            formatted_sessions = []
            for session in sessions:
                formatted_session = {
                    'id': session.get('session_id', ''),
                    'title': session.get('title', '新对话'),
                    'updated_at': session.get('updated_at', ''),
                    'created_at': session.get('created_at', ''),
                    'message_count': session.get('message_count', 0)
                }
                formatted_sessions.append(formatted_session)
            
            logger.info(f"获取会话列表成功，共 {len(formatted_sessions)} 个会话，总计 {result.get('total', 0)} 个")
            return {
                'sessions': formatted_sessions,
                'total': result.get('total', 0),
                'page': result.get('page', page),
                'page_size': result.get('page_size', page_size)
            }
            
        except Exception as e:
            logger.error(f"获取会话列表失败: {str(e)}")
            return {'sessions': [], 'total': 0, 'page': page, 'page_size': page_size}
    
    async def cleanup_expired_sessions(self):
        """清理过期会话"""
        try:
            self.session_manager.cleanup_expired_sessions()
            logger.info("过期会话清理完成")
            
        except Exception as e:
            logger.error(f"清理过期会话失败: {str(e)}")