"""
RAG工作流图
"""

import asyncio
from typing import Dict, Any, List, Optional
from app.utils.logger import setup_logger

logger = setup_logger(__name__)


class RAGWorkflow:
    """RAG工作流，协调整个检索增强生成过程"""
    
    def __init__(self, retriever, reranker, query_transformer, llm_client=None):
        """初始化RAG工作流
        
        Args:
            retriever: 检索器实例
            reranker: 重排序器实例
            query_transformer: 查询转换器实例
            llm_client: LLM客户端实例
        """
        self.retriever = retriever
        self.reranker = reranker
        self.query_transformer = query_transformer
        self.llm_client = llm_client or MockLLMClient()
        
        logger.info("RAG工作流初始化完成")
    
    async def process_query(self, query: str, session_id: str = None) -> Dict[str, Any]:
        """处理用户查询的完整流程
        
        Args:
            query: 用户查询
            session_id: 会话ID
            
        Returns:
            处理结果字典
        """
        try:
            logger.info(f"开始处理查询: {query}")
            
            # 1. 查询预处理和扩展
            expanded_queries = self.query_transformer.expand_query(query)
            rewritten_query = self.query_transformer.rewrite_query(query)
            
            # 2. 检索相关文档
            if len(expanded_queries) > 1:
                # 多查询检索
                retrieved_docs = await self.retriever.multi_query_retrieve(expanded_queries, top_k=10)
            else:
                # 单查询检索
                retrieved_docs = await self.retriever.adaptive_retrieve(rewritten_query, top_k=10)
            
            if not retrieved_docs:
                return {
                    "query": query,
                    "response": "抱歉，我没有找到相关的医疗信息。请尝试重新表述您的问题。",
                    "documents": [],
                    "session_id": session_id
                }
            
            # 3. 重排序
            reranked_docs = await self.reranker.rerank_documents(query, retrieved_docs, top_k=5)
            
            # 4. 构建上下文
            context = self._build_context(reranked_docs)
            
            # 5. 生成回答
            response = await self._generate_response(query, context)
            
            # 6. 后处理
            final_response = self._post_process_response(response, query)
            
            # 7. 提取参考文档
            reference_docs = [doc['page_content'][:200] + "..." for doc in reranked_docs[:3]]
            
            result = {
                "query": query,
                "response": final_response,
                "documents": reference_docs,
                "session_id": session_id,
                "metadata": {
                    "retrieved_count": len(retrieved_docs),
                    "reranked_count": len(reranked_docs),
                    "expanded_queries": expanded_queries
                }
            }
            
            logger.info(f"查询处理完成: {query}")
            return result
            
        except Exception as e:
            logger.error(f"处理查询时出错: {str(e)}")
            return {
                "query": query,
                "response": f"处理查询时出现错误: {str(e)}",
                "documents": [],
                "session_id": session_id
            }
    
    def _build_context(self, documents: List[Dict[str, Any]]) -> str:
        """构建上下文字符串"""
        context_parts = []
        
        for i, doc in enumerate(documents, 1):
            content = doc['page_content']
            metadata = doc.get('metadata', {})
            source = metadata.get('source', '未知来源')
            
            context_parts.append(f"文档{i} (来源: {source}):\n{content}\n")
        
        return "\n".join(context_parts)
    
    async def _generate_response(self, query: str, context: str) -> str:
        """生成回答"""
        try:
            # 构建提示词
            prompt = self._build_prompt(query, context)
            
            # 调用LLM生成回答
            response = await self.llm_client.generate(prompt)
            
            return response
            
        except Exception as e:
            logger.error(f"生成回答时出错: {str(e)}")
            return "抱歉，生成回答时出现错误。"
    
    def _build_prompt(self, query: str, context: str) -> str:
        """构建提示词"""
        prompt = f"""你是一个专业的医疗AI助手。请基于以下医疗文献内容回答用户的问题。

要求：
1. 回答必须基于提供的文献内容
2. 如果文献中没有相关信息，请明确说明
3. 回答要准确、专业、易懂
4. 避免给出具体的诊断或治疗建议
5. 建议用户咨询专业医生
6. 尽量详细的回答用户问题，使用markdown格式输出

用户问题：{query}

参考文献：
{context}

请基于以上文献内容回答用户问题："""
        
        return prompt
    
    def _post_process_response(self, response: str, query: str) -> str:
        """后处理回答"""
        # 添加免责声明
        disclaimer = "\n\n注意：以上信息仅供参考，不能替代专业医疗建议。如有健康问题，请咨询专业医生。"
        
        if not response.endswith(disclaimer):
            response += disclaimer
        
        return response
    
    async def stream_process_query(self, query: str, session_id: str = None):
        """流式处理查询（用于SSE）"""
        try:
            # 发送状态更新
            yield {"type": "status", "message": "正在分析查询..."}
            
            # 查询预处理
            expanded_queries = self.query_transformer.expand_query(query)
            rewritten_query = self.query_transformer.rewrite_query(query)
            
            yield {"type": "status", "message": "正在检索相关文档..."}
            
            # 检索文档
            if len(expanded_queries) > 1:
                retrieved_docs = self.retriever.multi_query_retrieve(expanded_queries, top_k=10)
            else:
                retrieved_docs = self.retriever.adaptive_retrieve(rewritten_query, top_k=10)
            
            if not retrieved_docs:
                yield {
                    "type": "result",
                    "query": query,
                    "response": "抱歉，我没有找到相关的医疗信息。",
                    "documents": [],
                    "session_id": session_id
                }
                return
            
            yield {"type": "status", "message": "正在重排序文档..."}
            
            # 重排序
            reranked_docs = self.reranker.rerank(query, retrieved_docs, top_k=5)
            
            yield {"type": "status", "message": "正在生成回答..."}
            
            # 生成回答
            context = self._build_context(reranked_docs)
            response = await self._generate_response(query, context)
            final_response = self._post_process_response(response, query)
            
            # 返回最终结果
            reference_docs = [doc['page_content'][:200] + "..." for doc in reranked_docs[:3]]
            
            yield {
                "type": "result",
                "query": query,
                "response": final_response,
                "documents": reference_docs,
                "session_id": session_id
            }
            
        except Exception as e:
            logger.error(f"流式处理查询时出错: {str(e)}")
            yield {
                "type": "error",
                "message": f"处理查询时出现错误: {str(e)}"
            }


class MockLLMClient:
    """模拟LLM客户端，用于开发测试"""
    
    async def generate(self, prompt: str) -> str:
        """生成模拟回答"""
        # 尝试使用Deepseek客户端
        try:
            from app.workflow.deepseek_client import get_deepseek_client
            client = await get_deepseek_client()
            response = await client.generate_response(prompt)
            return response
        except Exception as e:
            logger.warning(f"Deepseek客户端调用失败，使用模拟回答: {str(e)}")
            
        # 模拟异步处理
        await asyncio.sleep(1)
        
        # 基于提示词生成简单回答
        if "高血压" in prompt:
            return """高血压是一种常见的心血管疾病，通常定义为收缩压≥140mmHg和/或舒张压≥90mmHg。

主要症状可能包括：
- 头痛、头晕
- 心悸、胸闷
- 视力模糊
- 颈部僵硬

治疗方法通常包括：
1. 生活方式改变：低盐饮食、规律运动、戒烟限酒
2. 药物治疗：根据医生建议使用降压药物
3. 定期监测血压

预防措施：
- 保持健康体重
- 规律运动
- 健康饮食
- 管理压力"""
        
        elif "糖尿病" in prompt:
            return """糖尿病是一组以高血糖为特征的代谢性疾病。

主要类型：
1. 1型糖尿病：胰岛素绝对缺乏
2. 2型糖尿病：胰岛素相对缺乏或胰岛素抵抗

常见症状：
- 多饮、多尿、多食
- 体重下降
- 疲劳乏力
- 视力模糊

管理方法：
1. 血糖监测
2. 饮食控制
3. 规律运动
4. 药物治疗（必要时）
5. 定期检查并发症"""
        
        else:
            return """根据提供的医疗文献，我为您整理了相关信息。由于医疗问题的复杂性，建议您：

1. 仔细阅读相关医疗文献
2. 关注症状的发展变化
3. 及时就医咨询专业医生
4. 遵循医生的治疗建议
5. 定期复查和随访

每个人的情况不同，具体的诊断和治疗方案需要专业医生根据个人情况制定。"""
