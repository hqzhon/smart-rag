"""
搜索服务
"""

from typing import List, Dict, Any, Optional
from datetime import datetime

from app.models.query_models import SearchResult, QueryAnalysis
from app.retrieval.query_transformer import QueryTransformer
from app.retrieval.fusion_retriever import AdvancedFusionRetriever, create_advanced_fusion_retriever
from app.retrieval.small_to_big_switcher import SmallToBigSwitcher
from app.storage.vector_store import VectorStore
from app.storage.database import get_db_manager_async
from app.embeddings.embeddings import QianwenEmbeddings
from app.utils.logger import setup_logger
from app.core.config import get_settings

logger = setup_logger(__name__)


class SearchService:
    """搜索服务类，处理搜索相关的业务逻辑（异步）"""
    
    def __init__(self):
        """初始化搜索服务"""
        self.query_transformer = QueryTransformer()
        self.db_manager = None
        self.vector_store = None
        self.embeddings = None
        self.retriever = None
        self.documents_content = None
        self.small_to_big_switcher = None
        self.settings = get_settings()
        
        logger.info("搜索服务基础初始化完成")
    
    async def async_init(self):
        """异步初始化重量级组件"""
        logger.info("开始异步初始化搜索服务重量级组件...")
        
        # 异步初始化各个组件
        self.db_manager = await self._get_db_manager()
        self.vector_store = await self._get_vector_store()
        self.embeddings = await self._get_embeddings()
        
        # 预加载文档内容 - 必须在创建检索器之前
        self.documents_content = await self._get_documents_content()
        
        # 初始化检索器 - 使用最新的优化逻辑
        self.retriever = await create_advanced_fusion_retriever(
            vector_store=self.vector_store,
            documents=self.documents_content,
            config_name='balanced',
            enable_all_optimizations=True
        )
        
        self.small_to_big_switcher = SmallToBigSwitcher(self.db_manager)
        await self.small_to_big_switcher.async_init()
        logger.info("小-大切换器初始化完成")
        
        logger.info("搜索服务异步初始化完成")
    
    async def _get_db_manager(self):
        """异步获取数据库管理器"""
        from app.storage.database import get_db_manager_async
        return await get_db_manager_async()
    
    async def _get_vector_store(self):
        """异步获取向量存储"""
        from app.storage.vector_store import VectorStore
        vector_store = VectorStore()
        await vector_store.async_init()
        return vector_store
    
    async def _get_embeddings(self):
        """异步获取嵌入模型"""
        from app.embeddings.embeddings import QianwenEmbeddings
        return QianwenEmbeddings()
    
    async def _get_documents_content(self):
        """异步获取文档内容 - 从向量数据库获取以包含 keywords 和 summary"""
        try:
            # 从向量数据库获取所有文档，这样可以获得包含 keywords 和 summary 的 metadata
            collection_data = self.vector_store.collection.get()
            
            documents = []
            ids = collection_data.get('ids', [])
            metadatas = collection_data.get('metadatas', [])
            documents_data = collection_data.get('documents', [])
            
            for i in range(len(ids)):
                doc = {
                    'id': ids[i],
                    'content': documents_data[i] if i < len(documents_data) else '',
                    'metadata': metadatas[i] if i < len(metadatas) else {}
                }
                documents.append(doc)
            
            logger.info(f"从向量数据库获取到 {len(documents)} 个文档")
            return documents
            
        except Exception as e:
            logger.error(f"从向量数据库获取文档内容时出错: {str(e)}")
            # 如果向量数据库获取失败，回退到数据库
            if self.db_manager:
                logger.info("回退到从 MySQL 数据库获取文档内容")
                return await self.db_manager.get_all_documents_content_async()
            return []
    
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
            
            # 小-大检索切换逻辑
            if self.small_to_big_switcher is not None:
                
                logger.info("执行小-大检索切换")
                switching_result = await self.small_to_big_switcher.switch_to_parent_chunks(
                    retrieved_docs, 
                    preserve_small_chunks=True  # 保留无法找到大块的小块
                )
                
                # 使用切换后的文档
                retrieved_docs = switching_result.switched_documents
                
                # 记录切换统计信息
                stats = self.small_to_big_switcher.get_switching_stats(switching_result)
                logger.info(
                    f"小-大切换统计: 总处理 {stats['total_processed']} 个, "
                    f"成功切换 {stats['parent_chunks_found']} 个, "
                    f"成功率 {stats['switch_success_rate']:.2%}, "
                    f"耗时 {stats['processing_time']:.3f}s"
                )
            
            results = []
            for doc in retrieved_docs:
                metadata = doc.get('metadata', {})
                score = metadata.get('score', 0.0)
                
                if score >= threshold:
                    # 检查是否为切换后的文档
                    chunk_type = "parent_chunk" if metadata.get('switched_to_parent') else "text"
                    
                    results.append(SearchResult(
                        content=doc.get('page_content', doc.get('content', '')),
                        score=score,
                        source=metadata.get('source', 'unknown'),
                        page=metadata.get('page_number', 0),
                        chunk_type=chunk_type,
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
            db = await get_db_manager_async()
            return db.get_search_history(session_id=user_id, limit=limit)
        except Exception as e:
            logger.error(f"获取搜索历史失败: {str(e)}")
            return []
