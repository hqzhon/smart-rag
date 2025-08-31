"""
重排序器
"""

from typing import List, Dict, Any
from app.workflow.qianwen_client import get_qianwen_client
from app.utils.logger import setup_logger

logger = setup_logger(__name__)


class QianwenReranker:
    """千问重排序器（异步）"""
    
    async def rerank_documents(
        self, 
        query: str, 
        documents: List[Dict[str, Any]], 
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """异步重排序文档
        
        Args:
            query: 查询文本
            documents: 待排序的文档列表
            top_k: 返回的文档数量
            
        Returns:
            重排序后的文档列表
        """
        if not documents:
            return []
            
        try:
            # 兼容不同的文档结构，优先使用page_content，如果没有则使用content
            # 确保所有文档文本都是有效的非空字符串
            doc_texts = []
            valid_doc_indices = []
            
            for i, doc in enumerate(documents):
                text = doc.get('page_content') or doc.get('content', '')
                # 确保文本是字符串且非空
                if isinstance(text, str) and text.strip():
                    doc_texts.append(text.strip())
                    valid_doc_indices.append(i)
                else:
                    logger.warning(f"Document at index {i} has invalid or empty content, skipping")
            
            if not doc_texts:
                logger.warning("No valid documents found for reranking")
                return documents[:top_k]
            
            client = await get_qianwen_client()
            async with client as c:
                rerank_results = await c.rerank_documents(
                    query=query,
                    documents=doc_texts,
                    top_k=top_k
                )
            
            reranked_docs = []
            for idx, score in rerank_results:
                if idx < len(valid_doc_indices):
                    # 使用valid_doc_indices映射回原始文档索引
                    original_idx = valid_doc_indices[idx]
                    doc = documents[original_idx].copy()
                    doc['rerank_score'] = score
                    reranked_docs.append(doc)
            
            logger.debug(f"千问重排序完成，返回{len(reranked_docs)}个文档")
            return reranked_docs
            
        except Exception as e:
            logger.warning(f"千问重排序失败，使用原始排序: {str(e)}")
            return documents[:top_k]