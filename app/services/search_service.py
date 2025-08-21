"""
搜索服务
"""

from typing import List, Dict, Any, Optional
from datetime import datetime

from app.models.query_models import SearchResult, QueryAnalysis
from app.retrieval.query_transformer import QueryTransformer
from app.retrieval.retriever import HybridRetriever
from app.storage.vector_store import VectorStore
from app.storage.database import get_db_manager
from app.embeddings.embeddings import QianwenEmbeddings
from app.utils.logger import setup_logger

logger = setup_logger(__name__)


class SearchService:
    """搜索服务类，处理搜索相关的业务逻辑（异步）"""
    
    def __init__(self):
        """初始化搜索服务"""
        self.query_transformer = QueryTransformer()
        
        db_manager = get_db_manager()
        all_docs = db_manager.get_all_documents_content()
        
        vector_store = VectorStore()
        embedding_model = QianwenEmbeddings()
        self.retriever = HybridRetriever(vector_store, self.query_transformer, embedding_model)
        
        logger.info("搜索服务初始化完成")
    
    async def search_documents(self, query: str, session_id: Optional[str] = None, 
                             limit: int = 10, threshold: float = 0.5) -> List[SearchResult]:
        """异步搜索文档
        
        Args:
            query: 搜索查询
            session_id: 会话ID
            limit: 结果限制
            threshold: 相似度阈值
            
        Returns:
            搜索结果列表
        """
        try:
            logger.info(f"执行文档搜索: {query}")
            
            retrieved_docs = await self.retriever.retrieve(query, top_k=limit)
            
            results = []
            for doc in retrieved_docs:
                metadata = doc.get('metadata', {})
                score = metadata.get('score', 0.0)
                
                if score >= threshold:
                    results.append(SearchResult(
                        content=doc.get('page_content', ''),
                        score=score,
                        source=metadata.get('source', 'unknown'),
                        page=metadata.get('page_number', 0),
                        chunk_type="text",
                        metadata=metadata
                    ))
            
            logger.info(f"搜索完成，返回 {len(results)} 个结果")
            return results
            
        except Exception as e:
            logger.error(f"文档搜索失败: {str(e)}")
            return []
    
    async def analyze_query(self, query: str) -> QueryAnalysis:
        """分析查询"""
        try:
            entities = self.query_transformer.extract_medical_entities(query)
            query_type = self._classify_query_type(query)
            language = self._detect_language(query)
            keywords = self._extract_keywords(query)
            
            analysis = QueryAnalysis(
                query_type=query_type,
                entities=entities.get("diseases", []) + entities.get("symptoms", []),
                intent=self._determine_intent(query),
                language=language,
                complexity=self._assess_complexity(query),
                keywords=keywords
            )
            
            logger.info(f"查询分析完成: {query}")
            return analysis
            
        except Exception as e:
            logger.error(f"查询分析失败: {str(e)}")
            return QueryAnalysis(query_type="unknown", entities=[], intent="unknown", language="unknown", complexity="medium", keywords=[])
    
    def _classify_query_type(self, query: str) -> str:
        """分类查询类型"""
        query_lower = query.lower()
        if any(word in query_lower for word in ["什么是", "定义"]): return "definition"
        if any(word in query_lower for word in ["症状", "表现"]): return "symptom"
        if any(word in query_lower for word in ["治疗", "药物"]): return "treatment"
        return "general"
    
    def _detect_language(self, query: str) -> str:
        """检测查询语言"""
        if not query.strip(): return "unknown"
        chinese_chars = sum(1 for char in query if '\u4e00' <= char <= '\u9fff')
        if chinese_chars / len(query.strip()) > 0.5: return "zh"
        return "en"
    
    def _determine_intent(self, query: str) -> str:
        """确定查询意图"""
        if any(word in query.lower() for word in ["？", "?", "什么", "如何"]): return "question"
        return "statement"
    
    def _assess_complexity(self, query: str) -> str:
        """评估查询复杂度"""
        if len(query.split()) < 5: return "simple"
        if len(query.split()) < 15: return "medium"
        return "complex"
    
    def _extract_keywords(self, query: str) -> List[str]:
        """提取关键词"""
        stop_words = {"的", "了", "在", "是", "有", "和", "或", "a", "an", "the"}
        return [word for word in query.split() if word.lower() not in stop_words and len(word) > 1][:10]
    
    async def get_search_suggestions(self, partial_query: str, limit: int = 5) -> List[str]:
        """获取搜索建议"""
        try:
            suggestions = [f"{partial_query}的{cat}" for cat in ["症状", "治疗方法", "诊断标准", "预防措施"]]
            return suggestions[:limit]
        except Exception as e:
            logger.error(f"获取搜索建议失败: {str(e)}")
            return []
    
    async def get_search_history(self, user_id: Optional[str] = None, limit: int = 10) -> List[Dict[str, Any]]:
        """获取搜索历史"""
        try:
            db = get_db_manager()
            return db.get_search_history(session_id=user_id, limit=limit)
        except Exception as e:
            logger.error(f"获取搜索历史失败: {str(e)}")
            return []
