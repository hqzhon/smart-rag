"""
对话API
"""

from typing import Optional, List
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
import json
import asyncio

from app.utils.logger import setup_logger
from app.storage.database import DatabaseManager
from app.storage.vector_store import VectorStore
from app.retrieval.fusion_retriever import AdvancedFusionRetriever, create_advanced_fusion_retriever
from app.retrieval.enhanced_reranker import EnhancedReranker, create_enhanced_reranker
from app.retrieval.query_transformer import QueryTransformer
from app.workflow.enhanced_rag_workflow import EnhancedRAGWorkflow
from app.models.query_models import QueryRequest, QueryResponse

logger = setup_logger(__name__)

router = APIRouter()


@router.post("/chat/stream")
async def stream_query(request: QueryRequest):
    """处理用户查询 - SSE流式响应"""
    
    if not request.query.strip():
        raise HTTPException(status_code=400, detail="查询内容不能为空")
    
    if not request.session_id:
        raise HTTPException(status_code=400, detail="会话ID不能为空")
    
    async def generate_stream():
        try:
            logger.info(f"开始流式处理查询: {request.query}, 会话ID: {request.session_id}")
            
            # 获取全局RAG工作流实例
            rag_workflow = await get_global_rag_workflow()
            
            if not rag_workflow:
                yield f"data: {json.dumps({'error': 'RAG系统暂时不可用，请稍后重试'})}\n\n"
                return
            
            # 使用RAG工作流处理查询（结构化流式）
            async for data in rag_workflow.stream_process_query(request.query, request.session_id):
                if data:
                    yield f"data: {json.dumps(data)}\n\n"
                    await asyncio.sleep(0.01)  # 小延迟确保流畅性
            
            # 发送结束信号
            yield f"data: {json.dumps({'type': 'end'})}\n\n"
            
        except Exception as e:
            logger.error(f"流式处理查询时出错: {str(e)}")
            yield f"data: {json.dumps({'error': f'处理查询时出错: {str(e)}'})}\n\n"
    
    return StreamingResponse(
        generate_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "*"
        }
    )


@router.post("/chat/query", response_model=QueryResponse)
async def query(request: QueryRequest):
    """处理用户查询"""
    
    if not request.query.strip():
        raise HTTPException(status_code=400, detail="查询内容不能为空")
    
    if not request.session_id:
        raise HTTPException(status_code=400, detail="会话ID不能为空")
    
    try:
        logger.info(f"处理查询: {request.query}, 会话ID: {request.session_id}")
        
        # 获取全局RAG工作流实例
        rag_workflow = await get_global_rag_workflow()
        
        if not rag_workflow:
            raise HTTPException(status_code=503, detail="RAG系统暂时不可用，请稍后重试")
        
        # 使用RAG工作流处理查询
        result = await rag_workflow.process_query(request.query, request.session_id)
        
        return QueryResponse(
            query=result["query"],
            response=result["response"],
            documents=result["documents"],
            session_id=result["session_id"]
        )
        
    except Exception as e:
        logger.error(f"处理查询时出错: {str(e)}")
        raise HTTPException(status_code=500, detail=f"处理查询时出错: {str(e)}")


@router.get("/chat/sessions/{session_id}")
async def get_session(session_id: str):
    """获取会话信息"""
    # 实现会话信息获取
    from app.services.chat_service import ChatService
    
    chat_service = ChatService()
    session_info = await chat_service.get_session_info(session_id)
    
    if not session_info:
        raise HTTPException(status_code=404, detail="会话不存在")
    
    return session_info


@router.get("/chat/history/{session_id}")
async def get_chat_history(session_id: str, limit: int = 50):
    """获取指定会话的聊天历史"""
    try:
        from app.services.chat_service import ChatService
        
        chat_service = ChatService()
        history = await chat_service.get_chat_history(session_id, limit)
        
        logger.info(f"成功获取会话 {session_id} 的聊天历史，共 {len(history)} 条记录")
        return history
        
    except Exception as e:
        logger.error(f"获取聊天历史失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取聊天历史失败: {str(e)}")


@router.get("/chat/sessions")
async def get_sessions(page: int = 1, page_size: int = 10, include_empty: bool = False):
    """获取会话列表
    
    Args:
        page: 页码，默认为1
        page_size: 每页数量，默认为10
        include_empty: 是否包含空会话（新建但未发送消息的会话），默认为False
    
    Returns:
        会话列表和分页信息
    """
    try:
        from app.services.chat_service import ChatService
        
        chat_service = ChatService()
        result = await chat_service.get_sessions(page=page, page_size=page_size, include_empty=include_empty)
        
        return {
            "sessions": result.get('sessions', []),
            "total": result.get('total', 0),
            "page": result.get('page', page),
            "page_size": result.get('page_size', page_size),
            "include_empty": result.get('include_empty', include_empty)
        }
    except Exception as e:
        logger.error(f"获取会话列表失败: {str(e)}")
        raise HTTPException(status_code=500, detail="获取会话列表失败")


@router.post("/chat/sessions")
async def create_session():
    """创建新会话，自动关联所有可用文档"""
    # 实现会话创建
    from app.services.chat_service import ChatService
    from datetime import datetime
    
    chat_service = ChatService()
    session_id = await chat_service.create_session()
    
    return {
        "session_id": session_id, 
        "status": "created",
        "message": "会话创建成功，已自动关联所有可用文档",
        "created_at": datetime.now().isoformat()
    }


# 全局RAG工作流实例
_global_rag_workflow = None


async def get_global_rag_workflow() -> Optional[EnhancedRAGWorkflow]:
    """获取或创建全局RAG工作流实例"""
    global _global_rag_workflow
    
    if _global_rag_workflow is None:
        try:
            # 初始化数据库管理器
            db = DatabaseManager()
            
            # 获取所有文档内容
            raw_documents = db.get_all_documents_content()
            
            if not raw_documents:
                logger.warning("没有找到任何文档，RAG工作流无法初始化")
                return None
            
            # 为文档添加keywords和summary字段以支持MultiFieldBM25Retriever
            documents = []
            for doc in raw_documents:
                # 创建增强的文档副本
                enhanced_doc = doc.copy()
                
                # 从title和content生成keywords（简单的关键词提取）
                title = doc.get('title', '')
                content = doc.get('content', '')
                
                # 生成keywords：取title中的词汇和content的前几个词
                keywords = []
                if title:
                    keywords.extend(title.split()[:5])  # 取title的前5个词
                if content:
                    # 取content的前20个字符作为关键词
                    content_words = content.replace('\n', ' ').split()[:10]
                    keywords.extend(content_words)
                
                # 生成summary：取content的前200个字符
                summary = content[:200] + '...' if len(content) > 200 else content
                
                # 添加到metadata中
                if 'metadata' not in enhanced_doc:
                    enhanced_doc['metadata'] = {}
                
                enhanced_doc['metadata']['keywords'] = keywords
                enhanced_doc['metadata']['summary'] = summary
                
                documents.append(enhanced_doc)
            
            logger.info(f"为 {len(documents)} 个文档添加了keywords和summary字段")
            
            # 初始化向量存储
            vector_store = VectorStore()
            
            # 初始化嵌入模型
            from app.embeddings.embeddings import QianwenEmbeddings
            embedding_model = QianwenEmbeddings()
            
            # 初始化查询转换器
            query_transformer = QueryTransformer()
            
            # 初始化检索器 - 使用最新的优化逻辑
            retriever = await create_advanced_fusion_retriever(
                vector_store=vector_store,
                documents=documents,
                config_name='balanced',
                enable_all_optimizations=True
            )
            
            # 初始化重排序器 - 使用增强版本
            reranker = create_enhanced_reranker(
                strategy='qianwen_api',
                enable_cache=True
            )
            
            # 创建RAG工作流
            _global_rag_workflow = EnhancedRAGWorkflow(
                retriever=retriever,
                reranker=reranker,
                query_transformer=query_transformer
            )
            
            logger.info(f"全局RAG工作流初始化成功，加载了 {len(documents)} 个文档")
            
        except Exception as e:
            logger.error(f"初始化全局RAG工作流失败: {str(e)}")
            return None
    
    return _global_rag_workflow


async def refresh_global_rag_workflow():
    """刷新全局RAG工作流（在文档更新后调用）"""
    global _global_rag_workflow
    _global_rag_workflow = None
    logger.info("全局RAG工作流已重置，下次查询时将重新初始化")


@router.delete("/chat/sessions/{session_id}")
async def delete_session(session_id: str):
    """删除会话"""
    try:
        from app.services.chat_service import ChatService
        
        chat_service = ChatService()
        success = await chat_service.delete_session(session_id)
        
        if success:
            return {"message": "会话删除成功"}
        else:
            raise HTTPException(status_code=404, detail="会话不存在或已被删除")
            
    except Exception as e:
        logger.error(f"删除会话失败: {str(e)}")
        raise HTTPException(status_code=500, detail="删除会话失败")


@router.put("/chat/sessions/{session_id}")
async def update_session(session_id: str, update_data: dict):
    """更新会话信息"""
    try:
        from app.services.chat_service import ChatService
        
        chat_service = ChatService()
        
        # 提取标题和元数据
        title = update_data.get('title')
        metadata = update_data.get('metadata')
        
        if not title and not metadata:
            raise HTTPException(status_code=400, detail="请提供要更新的标题或元数据")
        
        success = await chat_service.update_session(session_id, title=title, metadata=metadata)
        
        if success:
            return {"message": "会话更新成功"}
        else:
            raise HTTPException(status_code=404, detail="会话不存在")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新会话失败: {str(e)}")
        raise HTTPException(status_code=500, detail="更新会话失败")
