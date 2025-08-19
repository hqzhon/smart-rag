"""
混合检索器
"""

from typing import List, Dict, Any, Optional
from app.utils.logger import setup_logger
from app.storage.vector_store import VectorStore
import asyncio

logger = setup_logger(__name__)


class HybridRetriever:
    """混合检索器，结合向量检索和BM25，支持自适应检索策略（异步）"""
    
    def __init__(self, vector_store: VectorStore, documents: List[Dict[str, Any]], vector_weight: float = 0.6):
        """初始化混合检索器
        
        Args:
            vector_store: 向量存储实例
            documents: 文档列表，用于BM25检索器
            vector_weight: 向量检索权重
        """
        self.vector_store = vector_store
        self.documents = documents
        self.vector_weight = vector_weight
        
        self.vector_retriever = vector_store.get_retriever(search_type="similarity", k=5)
        self.bm25_retriever = SimpleBM25Retriever(documents)
        
        logger.info(f"混合检索器初始化完成，向量权重: {vector_weight}")
    
    def _classify_query(self, query: str) -> str:
        """分类查询类型"""
        factual_keywords = ["什么是", "定义", "症状", "治疗方法", "药物", "剂量", "副作用"]
        conceptual_keywords = ["为什么", "如何", "机制", "原理", "关系", "影响", "比较"]
        
        query_lower = query.lower()
        factual_count = sum(1 for keyword in factual_keywords if keyword in query_lower)
        conceptual_count = sum(1 for keyword in conceptual_keywords if keyword in query_lower)
        
        if factual_count > conceptual_count:
            return "factual"
        elif conceptual_count > factual_count:
            return "conceptual"
        else:
            return "mixed"
    
    async def adaptive_retrieve(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """异步自适应检索相关文档"""
        try:
            query_type = self._classify_query(query)
            
            vector_results = await self.vector_retriever.get_relevant_documents(query)
            bm25_results = self.bm25_retriever.get_relevant_documents(query, top_k)
            
            vector_weight, bm25_weight = (0.3, 0.7) if query_type == "factual" else \
                                        (0.8, 0.2) if query_type == "conceptual" else \
                                        (self.vector_weight, 1.0 - self.vector_weight)
            
            combined_results = self._combine_results(vector_results, bm25_results, vector_weight, bm25_weight, top_k)
            
            logger.info(f"自适应检索完成，查询类型: {query_type}, 返回 {len(combined_results)} 个结果")
            return combined_results
            
        except Exception as e:
            logger.error(f"自适应检索时出错: {str(e)}")
            return []
    
    def _combine_results(self, vector_results: List[Dict[str, Any]], bm25_results: List[Dict[str, Any]], 
                        vector_weight: float, bm25_weight: float, top_k: int) -> List[Dict[str, Any]]:
        """融合检索结果"""
        doc_scores: Dict[int, Dict[str, Any]] = {}
        
        def get_doc_id(doc: Dict[str, Any]) -> int:
            return hash(doc['page_content'][:100])

        for i, doc in enumerate(vector_results[:top_k]):
            doc_id = get_doc_id(doc)
            score = vector_weight * (1.0 / (i + 1))
            doc_scores[doc_id] = {'document': doc, 'score': score}
        
        for i, doc in enumerate(bm25_results[:top_k]):
            doc_id = get_doc_id(doc)
            score = bm25_weight * (1.0 / (i + 1))
            if doc_id in doc_scores:
                doc_scores[doc_id]['score'] += score
            else:
                doc_scores[doc_id] = {'document': doc, 'score': score}
        
        sorted_results = sorted(doc_scores.values(), key=lambda x: x['score'], reverse=True)
        return [item['document'] for item in sorted_results[:top_k]]
    
    async def retrieve(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """异步检索相关文档"""
        return await self.adaptive_retrieve(query, top_k)
    
    async def multi_query_retrieve(self, queries: List[str], top_k: int = 5) -> List[Dict[str, Any]]:
        """异步多查询检索并融合结果"""
        doc_scores: Dict[int, Dict[str, Any]] = {}
        
        tasks = [self.adaptive_retrieve(query, top_k * 2) for query in queries]
        results_list = await asyncio.gather(*tasks)

        for results in results_list:
            for i, doc in enumerate(results):
                doc_id = hash(doc['page_content'][:100])
                score = 1.0 / (i + 1)
                if doc_id in doc_scores:
                    doc_scores[doc_id]['score'] += score
                else:
                    doc_scores[doc_id] = {'document': doc, 'score': score}
        
        sorted_results = sorted(doc_scores.values(), key=lambda x: x['score'], reverse=True)
        return [item['document'] for item in sorted_results[:top_k]]


class SimpleBM25Retriever:
    """简化的BM25检索器"""
    
    def __init__(self, documents: List[Dict[str, Any]]):
        self.documents = documents
        self.doc_contents = [doc.get('content', '') for doc in documents]
        
    def get_relevant_documents(self, query: str, k: int = 5) -> List[Dict[str, Any]]:
        """获取相关文档"""
        try:
            scores = []
            query_terms = query.lower().split()
            
            for i, content in enumerate(self.doc_contents):
                content_lower = content.lower()
                score = sum(content_lower.count(term) for term in query_terms if term in content_lower)
                if score > 0:
                    scores.append((i, score))
            
            scores.sort(key=lambda x: x[1], reverse=True)
            
            results = []
            for i, score in scores[:k]:
                original_doc = self.documents[i]
                results.append({
                    'page_content': self.doc_contents[i],
                    'metadata': original_doc.get('metadata', {})
                })
            return results
            
        except Exception as e:
            logger.error(f"BM25检索时出错: {str(e)}")
            return []