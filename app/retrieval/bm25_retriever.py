# app/retrieval/bm25_retriever.py
from typing import List, Dict, Any
import jieba
from rank_bm25 import BM25Okapi
from app.utils.logger import setup_logger

logger = setup_logger(__name__)

class RankBM25Retriever:
    """使用rank-bm25库实现的BM25检索器，基于keywords字段建立索引"""

    def __init__(self, documents: List[Dict[str, Any]]):
        """用文档列表初始化BM25索引

        Args:
            documents: 文档块列表，每个字典至少包含'content'、'id'和'metadata'字段
        """
        self.documents = documents
        self.doc_map = {doc['id']: doc for doc in documents}
        
        # 基于keywords字段进行分词，如果没有keywords则使用content
        tokenized_corpus = []
        for doc in documents:
            keywords = doc.get('metadata', {}).get('keywords', [])
            if keywords and isinstance(keywords, list):
                # 如果有keywords，使用keywords列表
                tokenized_corpus.append(keywords)
            elif keywords and isinstance(keywords, str):
                # 如果keywords是字符串，进行分词
                tokenized_corpus.append(list(jieba.cut(keywords)))
            else:
                # 如果没有keywords，回退到使用content进行分词
                tokenized_corpus.append(list(jieba.cut(doc['content'])))
        
        # 创建BM25索引
        self.bm25 = BM25Okapi(tokenized_corpus)
        logger.info(f"RankBM25Retriever已在 {len(documents)} 个文档上初始化，基于keywords字段建立索引。")

    def get_top_n(self, query: str, n: int = 5) -> List[Dict[str, Any]]:
        """获取最相关的Top-N文档"""
        if not self.documents:
            return []
            
        tokenized_query = list(jieba.cut(query))
        
        # 获取所有文档的BM25分数
        doc_scores = self.bm25.get_scores(tokenized_query)
        
        # 将分数与文档配对并排序
        scored_docs = [(doc, score) for doc, score in zip(self.documents, doc_scores)]
        scored_docs.sort(key=lambda x: x[1], reverse=True)
        
        # 返回Top-N文档
        return [doc for doc, score in scored_docs[:n]]

    def get_scores(self, query: str) -> Dict[str, float]:
        """获取查询与所有文档的BM25分数"""
        if not self.documents:
            return {}

        tokenized_query = list(jieba.cut(query))
        doc_scores = self.bm25.get_scores(tokenized_query)
        
        # 将分数与文档ID关联
        return {doc['id']: score for doc, score in zip(self.documents, doc_scores)}