"""
增强版RAG工作流 - 集成Deepseek和千问API (全异步)
"""

import asyncio
import json
from typing import Dict, Any, List, Optional, AsyncGenerator
from datetime import datetime

from app.workflow.deepseek_client import get_deepseek_client
from app.workflow.qianwen_client import get_qianwen_client
from app.retrieval.retriever import HybridRetriever
from app.retrieval.reranker import QianwenReranker
from app.retrieval.query_transformer import QueryTransformer
from app.utils.logger import setup_logger

logger = setup_logger(__name__)


class EnhancedRAGWorkflow:
    """增强版RAG工作流，使用Deepseek和千问API (全异步)"""
    
    def __init__(self, retriever: HybridRetriever, reranker: QianwenReranker, query_transformer: QueryTransformer):
        """初始化增强版RAG工作流
        
        Args:
            retriever: 异步检索器实例
            reranker: 异步重排序器实例  
            query_transformer: 查询转换器实例
        """
        self.retriever = retriever
        self.reranker = reranker
        self.query_transformer = query_transformer
        
        logger.info("增强版RAG工作流初始化完成")
    
    async def process_query(self, query: str, session_id: Optional[str] = None) -> Dict[str, Any]:
        """异步处理用户查询的完整流程"""
        try:
            logger.info(f"开始处理查询: {query}")
            
            expanded_queries = self.query_transformer.expand_query(query)
            rewritten_query = self.query_transformer.rewrite_query(query)
            
            if len(expanded_queries) > 1:
                retrieved_docs = await self.retriever.multi_query_retrieve(expanded_queries, top_k=10)
            else:
                retrieved_docs = await self.retriever.adaptive_retrieve(rewritten_query, top_k=10)
            
            if not retrieved_docs:
                return {
                    "query": query, 
                    "response": "抱歉，我没有找到相关的医疗信息。", 
                    "documents": [], 
                    "sources": [],
                    "session_id": session_id or "",
                    "confidence_score": 0.0,
                    "processing_time": None,
                    "feedback": None,
                    "metadata": {}
                }
            
            reranked_docs = await self.reranker.rerank_documents(query, retrieved_docs, top_k=5)
            
            context = self._build_context(reranked_docs)
            
            response = await self._deepseek_generate_response(query, context)
            
            final_response = self._post_process_response(response)
            
            reference_docs = [doc['page_content'][:200] + "..." for doc in reranked_docs[:3]]
            
            # 构建sources，确保文件名正确显示
            sources = []
            for doc in reranked_docs[:3]:
                metadata = doc.get('metadata', {})
                # 获取文档名称，优先从向量存储的metadata中获取已有的正确信息
                doc_name = None
                
                # 首先尝试从向量存储的metadata中获取正确的文件名信息
                if metadata.get('file_name'):
                    doc_name = metadata['file_name']
                elif metadata.get('source') and metadata['source'] != metadata.get('document_id'):
                    doc_name = metadata['source']
                elif metadata.get('title') and metadata['title'] != metadata.get('document_id'):
                    doc_name = metadata['title']
                elif metadata.get('original_filename'):
                    doc_name = metadata['original_filename']
                elif metadata.get('filename'):
                    doc_name = metadata['filename']
                
                # 如果向量存储metadata中没有找到，尝试从数据库获取
                if not doc_name and metadata.get('document_id'):
                    try:
                        from app.storage.database import get_db_manager
                        db = get_db_manager()
                        doc_info = db.get_document(metadata['document_id'])
                        if doc_info:
                            # 优先使用metadata中的original_filename，然后是title，最后是file_path的文件名
                            doc_metadata = doc_info.get('metadata', {})
                            if isinstance(doc_metadata, str):
                                doc_metadata = json.loads(doc_metadata)
                            
                            doc_name = (doc_metadata.get('original_filename') or 
                                      doc_info.get('title') or 
                                      (doc_info.get('file_path', '').split('/')[-1] if doc_info.get('file_path') else None))
                    except Exception as e:
                        logger.warning(f"Failed to get document info from database: {e}")
                
                # 最终fallback
                if not doc_name:
                    doc_name = '未知文档'
                
                # 更新metadata中的文件名信息
                updated_metadata = metadata.copy()
                updated_metadata['filename'] = doc_name
                updated_metadata['source'] = doc_name
                
                sources.append({
                    "content": doc['page_content'][:200], 
                    "score": doc.get('rerank_score', 0.0), 
                    "metadata": updated_metadata
                })
            
            # 构建符合QueryResponse模型的结果
            result = {
                "query": query,
                "response": final_response,
                "documents": reference_docs,
                "sources": sources,
                "session_id": session_id or "",
                "confidence_score": sum(doc.get('rerank_score', 0.0) for doc in reranked_docs[:3]) / min(3, len(reranked_docs)) if reranked_docs else 0.0,
                "processing_time": None,  # 可以在后续添加时间统计
                "feedback": None,
                "metadata": {
                    "retrieved_count": len(retrieved_docs),
                    "reranked_count": len(reranked_docs),
                    "model_used": "deepseek"
                }
            }
            
            logger.info(f"查询处理完成: {query}")
            return result
            
        except Exception as e:
            logger.error(f"处理查询时出错: {str(e)}", exc_info=True)
            return {
                "query": query, 
                "response": f"处理查询时出现错误: {str(e)}", 
                "documents": [], 
                "sources": [],
                "session_id": session_id or "",
                "confidence_score": 0.0,
                "processing_time": None,
                "feedback": None,
                "metadata": {"error": str(e)}
            }
    
    async def _deepseek_generate_response(self, query: str, context: str) -> str:
        """使用Deepseek生成回答"""
        try:
            client = await get_deepseek_client()
            prompt = self._build_medical_prompt(query, context)
            async with client as c:
                return await c.generate_response(prompt=prompt, temperature=0.7, max_tokens=1000)
        except Exception as e:
            logger.error(f"Deepseek生成回答失败: {str(e)}", exc_info=True)
            return "抱歉，生成回答时出现错误。"
    
    def _build_medical_prompt(self, query: str, context: str) -> str:
        """构建医疗专用提示词"""
        return f"""你是一个专业的医疗AI助手。请基于以下医疗文献内容回答用户的问题。
重要要求：
1. 回答必须严格基于提供的文献内容，不得编造信息。
2. 如果文献中没有相关信息，请明确说明"根据提供的文献，暂无相关信息"。
3. 绝对不要给出具体的诊断结论或治疗方案。
4. 不要标注引用来源。
5. 尽量详细的回答用户问题，使用markdown格式输出。
用户问题：{query}
参考医疗文献：
{context}
请基于以上文献内容专业地回答用户问题："""
    
    def _build_context(self, documents: List[Dict[str, Any]]) -> str:
        """构建上下文字符串"""
        context_parts = [f"{i} (来源: {doc.get('metadata', {}).get('source', '未知')}, 相关度: {doc.get('rerank_score', 0.0):.3f}):\n{doc['page_content']}\n" for i, doc in enumerate(documents, 1)]
        return "\n".join(context_parts)
    
    def _post_process_response(self, response: str) -> str:
        """后处理回答"""
        disclaimer = "\n\n⚠️ 重要提醒：以上信息仅供参考，不能替代专业医疗建议。如有健康问题，请及时咨询专业医生或到医院就诊。"
        return response + disclaimer if disclaimer not in response else response
    
    async def process_query_stream(self, query: str, session_id: Optional[str] = None) -> AsyncGenerator[str, None]:
        """简化的流式处理查询 - 仅返回文本token用于SSE"""
        try:
            logger.info(f"开始流式处理查询: {query}")
            
            # 查询转换和检索
            rewritten_query = self.query_transformer.rewrite_query(query)
            retrieved_docs = await self.retriever.adaptive_retrieve(rewritten_query, top_k=10)
            
            if not retrieved_docs:
                yield "抱歉，我没有找到相关的医疗信息。"
                return
            
            # 重排序
            reranked_docs = await self.reranker.rerank_documents(query, retrieved_docs, top_k=5)
            context = self._build_context(reranked_docs)
            
            # 流式生成回答
            async for chunk in self._stream_deepseek_response(query, context):
                if chunk.strip():  # 只返回非空的文本块
                    yield chunk
            
        except Exception as e:
            logger.error(f"流式处理查询时出错: {str(e)}", exc_info=True)
            yield f"处理查询时出现错误: {str(e)}"

    async def stream_process_query(self, query: str, session_id: Optional[str] = None) -> AsyncGenerator[Dict[str, Any], None]:
        """流式处理查询"""
        full_response = ""  # 收集完整回答用于保存
        reference_docs = []  # 收集引用文档用于保存
        
        try:
            yield {"type": "status", "message": "正在分析查询..."}
            rewritten_query = self.query_transformer.rewrite_query(query)
            
            yield {"type": "status", "message": "正在检索相关医疗文档..."}
            retrieved_docs = await self.retriever.adaptive_retrieve(rewritten_query, top_k=10)
            
            if not retrieved_docs:
                no_result_msg = "抱歉，我没有找到相关的医疗信息。"
                yield {"type": "result", "response": no_result_msg}
                # 保存无结果的聊天记录
                if session_id:
                    await self._save_chat_history(session_id, query, no_result_msg, [])
                return
            
            yield {"type": "status", "message": "正在使用AI重排序文档..."}
            reranked_docs = await self.reranker.rerank_documents(query, retrieved_docs, top_k=5)
            
            yield {"type": "status", "message": "正在生成专业医疗回答..."}
            context = self._build_context(reranked_docs)
            
            # 流式生成回答并收集完整内容
            async for chunk in self._stream_deepseek_response(query, context):
                full_response += chunk
                yield {"type": "chunk", "content": chunk}
            
            # 构建引用文档，使用原始文件名和页码信息
            for doc in reranked_docs[:3]:
                metadata = doc.get('metadata', {})
                # 获取文档名称，优先从向量存储的metadata中获取已有的正确信息
                doc_name = None
                
                # 首先尝试从向量存储的metadata中获取正确的文件名信息
                if metadata.get('file_name'):
                    doc_name = metadata['file_name']
                elif metadata.get('source') and metadata['source'] != metadata.get('document_id'):
                    doc_name = metadata['source']
                elif metadata.get('title') and metadata['title'] != metadata.get('document_id'):
                    doc_name = metadata['title']
                elif metadata.get('original_filename'):
                    doc_name = metadata['original_filename']
                elif metadata.get('filename'):
                    doc_name = metadata['filename']
                
                # 如果向量存储metadata中没有找到，尝试从数据库获取
                if not doc_name and metadata.get('document_id'):
                    try:
                        from app.storage.database import get_db_manager
                        db = get_db_manager()
                        doc_info = db.get_document(metadata['document_id'])
                        if doc_info:
                            # 优先使用metadata中的original_filename，然后是title，最后是file_path的文件名
                            doc_metadata = doc_info.get('metadata', {})
                            if isinstance(doc_metadata, str):
                                doc_metadata = json.loads(doc_metadata)
                            
                            doc_name = (doc_metadata.get('original_filename') or 
                                      doc_info.get('title') or 
                                      (doc_info.get('file_path', '').split('/')[-1] if doc_info.get('file_path') else None))
                    except Exception as e:
                        logger.warning(f"Failed to get document info from database: {e}")
                
                # 最终fallback
                if not doc_name:
                    doc_name = '未知文档'
                
                page_number = metadata.get('page_number')

                # 尝试解析content为JSON
                content = doc['page_content']
                try:
                    import json as json_module
                    content_json = json_module.loads(content)
                    if 'content' in content_json:
                        content = content_json['content']
                except Exception:
                    pass
                
                reference_docs.append({
                    'content': content,  # 移除截断限制，返回完整内容
                    'metadata': {
                        'filename': doc_name,  # 使用原始文件名
                        'page_number': page_number,  # 页码信息
                        'document_id': metadata.get('document_id', ''),
                        'file_type': metadata.get('file_type', ''),
                        'source': doc_name  # 为前端显示提供source字段
                    }
                })
            
            yield {"type": "documents", "documents": reference_docs}
            
            # 保存聊天记录到数据库
            if session_id and full_response:
                try:
                    await self._save_chat_history(session_id, query, full_response, reference_docs)
                    logger.info(f"聊天记录已保存，会话ID: {session_id}")
                except Exception as save_error:
                    logger.error(f"保存聊天记录失败: {str(save_error)}", exc_info=True)
            
            yield {"type": "status", "message": "回答生成完成"}
            
        except Exception as e:
            logger.error(f"流式处理查询时出错: {str(e)}", exc_info=True)
            yield {"type": "error", "message": f"处理查询时出现错误: {str(e)}"}

    async def _stream_deepseek_response(self, query: str, context: str) -> AsyncGenerator[str, None]:
        """流式生成Deepseek回答"""
        try:
            client = await get_deepseek_client()
            prompt = self._build_medical_prompt(query, context)
            async with client as c:
                async for chunk in c.generate_stream_response(prompt=prompt, temperature=0.7, max_tokens=1000):
                    yield chunk
            yield self._post_process_response("") # Add disclaimer at the end
        except Exception as e:
            logger.error(f"流式生成Deepseek回答失败: {str(e)}", exc_info=True)
            yield "抱歉，生成回答时出现错误。"
    
    async def _save_chat_history(self, session_id: str, query: str, response: str, reference_docs: List[Dict[str, Any]]):
        """保存聊天记录到数据库"""
        try:
            from app.storage.database import get_db_manager
            db_manager = get_db_manager()
            
            # 构建引用文档的JSON数据
            sources = []
            for doc in reference_docs:
                sources.append({
                    'filename': doc['metadata'].get('filename', ''),
                    'content': doc['content'][:500],  # 限制内容长度
                    'page_number': doc['metadata'].get('page_number'),
                    'document_id': doc['metadata'].get('document_id', '')
                })
            
            # 保存聊天记录
            chat_data = {
                'session_id': session_id,
                'question': query,
                'answer': response,
                'sources': sources,
                'metadata': {}
            }
            db_manager.save_chat_history(chat_data)
            
        except Exception as e:
            logger.error(f"保存聊天记录时出错: {str(e)}", exc_info=True)
            raise e