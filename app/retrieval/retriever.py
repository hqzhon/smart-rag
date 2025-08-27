"""
混合检索器
"""

from typing import List, Dict, Any, Optional
import asyncio
import logging
import numpy as np
from rank_bm25 import BM25Okapi
from app.utils.logger import setup_logger
from app.storage.vector_store import VectorStore
from app.retrieval.query_transformer import QueryTransformer
from .bm25_retriever import RankBM25Retriever
from app.embeddings.embeddings import QianwenEmbeddings

logger = setup_logger(__name__)


class HybridRetriever:
    """两阶段混合检索器，先过滤后精排"""
    
    def __init__(self, vector_store: VectorStore, query_transformer: QueryTransformer, embedding_model: QianwenEmbeddings, 
                 fusion_method: str = "weighted", rrf_k: int = 60):
        """初始化两阶段混合检索器
        
        Args:
            vector_store: 向量存储实例
            query_transformer: 查询转换器实例
            embedding_model: 嵌入模型实例
            fusion_method: 融合方法，"rrf" 或 "weighted"
            rrf_k: RRF算法的k参数，默认60
        """
        # Validate fusion method
        if fusion_method not in ["rrf", "weighted"]:
            raise ValueError(f"Invalid fusion method: {fusion_method}. Must be 'rrf' or 'weighted'")
        
        # Validate rrf_k parameter
        if rrf_k <= 0:
            raise ValueError(f"Invalid rrf_k value: {rrf_k}. Must be greater than 0")
        
        self.vector_store = vector_store
        self.query_transformer = query_transformer
        self.embedding_model = embedding_model
        self.fusion_method = fusion_method
        self.rrf_k = rrf_k
        
        logger.info(f"两阶段混合检索器初始化完成，融合方法: {fusion_method}, RRF-k: {rrf_k}")
    
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
    
    async def _extract_keywords_from_query(self, query: str) -> List[str]:
        """从查询中提取关键词"""
        try:
            # 使用查询转换器提取关键词
            keywords = await self.query_transformer.extract_keywords(query)
            logger.debug(f"从查询 '{query}' 中提取到关键词: {keywords}")
            return keywords
        except Exception as e:
            logger.warning(f"关键词提取失败: {e}")
            return []
    
    def _build_chromadb_where_clause(self, keywords: List[str]) -> Optional[Dict[str, Any]]:
        """构建ChromaDB的where子句"""
        if not keywords:
            return None
        
        if len(keywords) == 1:
            return {"keywords": {"$in": [keywords[0]]}}
        else:
            return {"$or": [{"keywords": {"$in": [kw]}} for kw in keywords]}
    

    
    async def retrieve(self, query: str, top_k: int = 5, use_metadata_filter: bool = True) -> List[Dict[str, Any]]:
        """执行两阶段检索
        
        Args:
            query: 用户查询
            top_k: 最终返回结果数量
            use_metadata_filter: 是否启用元数据预过滤
        """
        try:
            # --- 第一阶段：过滤与召回候选集 ---
            candidate_chunks = await self._get_candidate_chunks(query, top_k * 5, use_metadata_filter)
            if not candidate_chunks:
                logger.warning("第一阶段未能召回任何候选文档块。")
                return []
            logger.info(f"第一阶段召回 {len(candidate_chunks)} 个候选文档块。")

            # --- 第二阶段：并行精排与融合 ---
            # 1. BM25精排 - 基于keywords字段建立索引
            bm25_retriever = RankBM25Retriever(candidate_chunks)
            bm25_scores = bm25_retriever.get_scores(query)
            logger.debug(f"BM25检索完成，基于keywords字段计算了 {len(bm25_scores)} 个文档的分数")

            # 2. 向量精排
            candidate_contents = [chunk['content'] for chunk in candidate_chunks]
            query_embedding = await self.embedding_model.embed_query(query)
            chunk_embeddings = await self.embedding_model.embed_documents(candidate_contents)
            vector_scores = self._calculate_cosine_similarity(query_embedding, chunk_embeddings)
            vector_scores_map = {chunk['id']: score for chunk, score in zip(candidate_chunks, vector_scores)}

            # 3. 结果融合
            if self.fusion_method == "rrf":
                fused_results = self._fuse_results_rrf(bm25_scores, vector_scores_map, top_k)
                # RRF返回的是字典列表，提取doc_id
                final_result_ids = [result['doc_id'] for result in fused_results]
            else:
                fused_results = self._fuse_results(bm25_scores, vector_scores_map, top_k)
                # _fuse_results现在也返回字典列表，提取doc_id
                final_result_ids = [result['doc_id'] for result in fused_results]

            logger.info(f"第二阶段精排与融合完成，返回 {len(final_result_ids)} 个结果。")
            return [chunk for chunk in candidate_chunks if chunk['id'] in final_result_ids]

        except Exception as e:
            logger.error(f"两阶段检索过程中发生错误: {e}", exc_info=True)
            return []
    
    async def _get_candidate_chunks(self, query: str, candidate_k: int, use_filter: bool) -> List[Dict[str, Any]]:
        """第一阶段：获取候选文档块"""
        where_filter = None
        if use_filter:
            keywords = await self._extract_keywords_from_query(query)
            if keywords:
                if len(keywords) == 1:
                    where_filter = {"keywords": {"$in": [keywords[0]]}}
                else:
                    where_filter = {"$or": [{"keywords": {"$in": [kw]}} for kw in keywords]}
        
        try:
            # 使用VectorStore的similarity_search方法来获取候选集
            if where_filter:
                # 使用过滤器进行搜索
                results = await self.vector_store.similarity_search(query, candidate_k, where_filter)
            else:
                # 不使用过滤器进行搜索
                results = await self.vector_store.similarity_search(query, candidate_k)
            
            # 将结果格式化为我们需要的字典列表
            formatted_chunks = []
            for doc in results:
                formatted_chunks.append({
                    'id': doc.get('id', str(hash(str(doc)[:100]))),
                    'content': doc.get('content', ''),
                    'metadata': doc.get('metadata', {})
                })
            return formatted_chunks
            
        except Exception as e:
            logger.error(f"获取候选文档块时出错: {str(e)}")
            return []

    def _fuse_results(self, bm25_scores: Dict[str, float], vector_scores: Dict[str, float], top_k: int, w_bm25=0.4, w_vector=0.6) -> List[str]:
        """传统加权融合方法"""
        # 归一化分数 (Min-Max Normalization with small epsilon to avoid zero scores)
        def normalize(scores: Dict[str, float]) -> Dict[str, float]:
            if not scores:
                return {}
            min_score, max_score = min(scores.values()), max(scores.values())
            if max_score == min_score: 
                return {k: 1.0 for k in scores}
            # 添加小的epsilon确保分数不为0
            epsilon = 1e-6
            return {k: ((v - min_score) / (max_score - min_score)) + epsilon for k, v in scores.items()}

        norm_bm25 = normalize(bm25_scores)
        norm_vector = normalize(vector_scores)

        # 加权融合
        fused_scores = {}
        all_ids = set(norm_bm25.keys()) | set(norm_vector.keys())
        for doc_id in all_ids:
            fused_scores[doc_id] = (norm_bm25.get(doc_id, 0) * w_bm25) + (norm_vector.get(doc_id, 0) * w_vector)

        # 排序并返回Top-K结果，格式与RRF方法保持一致
        sorted_results = sorted(fused_scores.items(), key=lambda x: x[1], reverse=True)
        
        results = []
        for doc_id, score in sorted_results[:top_k]:
            results.append({
                "doc_id": doc_id,
                "score": score,
                "content": "",  # 这里暂时为空，在上层方法中会填充
                "metadata": {}
            })
        
        return results
    
    def _fuse_results_rrf(self, bm25_scores: Dict[str, float], vector_scores: Dict[str, float], top_k: int) -> List[str]:
        """使用RRF (Reciprocal Rank Fusion) 融合结果
        
        Args:
            bm25_scores: BM25分数字典
            vector_scores: 向量分数字典
            top_k: 返回结果数量
            
        Returns:
            融合后的文档ID列表
        """
        # 1. 对每个检索器的结果按分数排序，获得排名
        bm25_ranked = sorted(bm25_scores.items(), key=lambda x: x[1], reverse=True)
        vector_ranked = sorted(vector_scores.items(), key=lambda x: x[1], reverse=True)
        
        # 2. 创建排名映射 (文档ID -> 排名)
        bm25_ranks = {doc_id: rank + 1 for rank, (doc_id, _) in enumerate(bm25_ranked)}
        vector_ranks = {doc_id: rank + 1 for rank, (doc_id, _) in enumerate(vector_ranked)}
        
        # 3. 计算RRF分数
        rrf_scores = {}
        all_doc_ids = set(bm25_ranks.keys()) | set(vector_ranks.keys())
        
        for doc_id in all_doc_ids:
            rrf_score = 0.0
            
            # BM25的RRF贡献
            if doc_id in bm25_ranks:
                rrf_score += 1.0 / (self.rrf_k + bm25_ranks[doc_id])
            
            # 向量检索的RRF贡献
            if doc_id in vector_ranks:
                rrf_score += 1.0 / (self.rrf_k + vector_ranks[doc_id])
            
            rrf_scores[doc_id] = rrf_score
        
        # 4. 按RRF分数排序并返回Top-K
        sorted_results = sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)
        
        # 5. 构建返回结果，格式与_fuse_results保持一致
        results = []
        for doc_id, score in sorted_results[:top_k]:
            results.append({
                "doc_id": doc_id,
                "score": score,
                "content": "",  # 这里暂时为空，在上层方法中会填充
                "metadata": {}
            })
        
        logger.debug(f"RRF融合完成，处理了{len(all_doc_ids)}个文档，k={self.rrf_k}")
        return results

    def _calculate_cosine_similarity(self, query_vec: List[float], doc_vecs: List[List[float]]) -> List[float]:
        """计算余弦相似度"""
        query_norm = np.linalg.norm(query_vec)
        doc_norms = np.linalg.norm(doc_vecs, axis=1)
        return np.dot(doc_vecs, query_vec) / (query_norm * doc_norms)
    
    def set_fusion_method(self, method: str) -> None:
        """动态设置融合方法
        
        Args:
            method: 融合方法，"rrf" 或 "weighted"
        """
        if method not in ["rrf", "weighted"]:
            raise ValueError(f"不支持的融合方法: {method}，支持的方法: ['rrf', 'weighted']")
        
        self.fusion_method = method
        logger.info(f"融合方法已更新为: {method}")
    
    def set_rrf_k(self, k: int) -> None:
        """动态设置RRF算法的k参数
        
        Args:
            k: RRF算法的k参数，建议范围[10, 100]
        """
        if k <= 0:
            raise ValueError(f"RRF参数k必须大于0，当前值: {k}")
        
        self.rrf_k = k
        logger.info(f"RRF参数k已更新为: {k}")
    
    def get_fusion_config(self) -> Dict[str, Any]:
        """获取当前融合配置
        
        Returns:
            包含融合方法和参数的配置字典
        """
        return {
            "fusion_method": self.fusion_method,
            "rrf_k": self.rrf_k
        }
    
    async def adaptive_retrieve(self, query: str, top_k: int = 5, use_metadata_filter: bool = True) -> List[Dict[str, Any]]:
        """向后兼容的自适应检索方法"""
        return await self.retrieve(query, top_k, use_metadata_filter)
    
    async def multi_query_retrieve(self, queries: List[str], top_k: int = 5) -> List[Dict[str, Any]]:
        """异步多查询检索并融合结果"""
        doc_scores: Dict[str, Dict[str, Any]] = {}
        
        tasks = [self.retrieve(query, top_k * 2) for query in queries]
        results_list = await asyncio.gather(*tasks)

        for results in results_list:
            for i, doc in enumerate(results):
                doc_id = doc.get('id', str(hash(str(doc)[:100])))
                score = 1.0 / (i + 1)
                if doc_id in doc_scores:
                    doc_scores[doc_id]['score'] += score
                else:
                    doc_scores[doc_id] = {'document': doc, 'score': score}
        
        sorted_results = sorted(doc_scores.values(), key=lambda x: x['score'], reverse=True)
        return [item['document'] for item in sorted_results[:top_k]]