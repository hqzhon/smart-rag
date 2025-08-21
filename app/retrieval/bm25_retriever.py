# app/retrieval/bm25_retriever.py
from typing import List, Dict, Any
import jieba
from rank_bm25 import BM25Okapi
from app.utils.logger import setup_logger

logger = setup_logger(__name__)

class RankBM25Retriever:
    """使用rank-bm25库实现的BM25检索器"""

    def __init__(self, documents: List[Dict[str, Any]]):
        """用文档列表初始化BM25索引

        Args:
            documents: 文档块列表，每个字典至少包含'content'和'id'字段
        """
        self.documents = documents
        self.doc_map = {doc['id']: doc for doc in documents}
        
        # 中文分词
        tokenized_corpus = [list(jieba.cut(doc['content'])) for doc in documents]
        
        # 创建BM25索引
        self.bm25 = BM25Okapi(tokenized_corpus)
        logger.info(f"RankBM25Retriever已在 {len(documents)} 个文档上初始化。")

    def get_top_n(self, query: str, n: int = 5) -> List[Dict[str, Any]]:
        """获取最相关的Top-N文档"""
        if not self.documents:
            return []
            
        tokenized_query = list(jieba.cut(query))
        
        # 获取相关文档的索引和分数
        # 注意：get_top_n返回的是原始语料库中的文档，我们需要映射回我们的文档对象
        top_docs = self.bm25.get_top_n(tokenized_query, [doc['content'] for doc in self.documents], n=n)
        
        # 根据返回的文本内容找到原始文档对象
        results = []
        for doc_content in top_docs:
            for doc in self.documents:
                if doc['content'] == doc_content:
                    results.append(doc)
                    break
        return results

    def get_scores(self, query: str) -> Dict[str, float]:
        """获取查询与所有文档的BM25分数"""
        if not self.documents:
            return {}

        tokenized_query = list(jieba.cut(query))
        doc_scores = self.bm25.get_scores(tokenized_query)
        
        # 将分数与文档ID关联
        return {doc['id']: score for doc, score in zip(self.documents, doc_scores)}