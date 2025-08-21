"""
向量存储接口
"""

import os
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv
from app.utils.logger import setup_logger

# 加载环境变量
load_dotenv()

logger = setup_logger(__name__)


class VectorStore:
    """向量存储接口（异步）"""
    
    def __init__(self, embedding_model=None):
        """初始化向量存储
        
        Args:
            embedding_model: 异步嵌入模型实例
        """
        if embedding_model is None:
            from app.embeddings.embeddings import get_embeddings
            embedding_model = get_embeddings()

        self.embedding_model = embedding_model
        self.persist_directory = os.getenv("CHROMA_DB_DIR", "./data/chroma_db")
        self.collection_name = os.getenv("CHROMA_COLLECTION_NAME", "medical_documents")
        
        os.makedirs(self.persist_directory, exist_ok=True)
        
        # 初始化向量存储
        self.db = None
        self._initialize_db()
        
        logger.info(f"向量存储初始化完成，目录: {self.persist_directory}")
    
    def _initialize_db(self):
        """初始化数据库连接"""
        try:
            import chromadb
            from chromadb.config import Settings
            
            self.client = chromadb.PersistentClient(
                path=self.persist_directory,
                settings=Settings(anonymized_telemetry=False)
            )
            
            try:
                self.collection = self.client.get_collection(name=self.collection_name)
                logger.info(f"加载现有集合: {self.collection_name}")
            except Exception:
                self.collection = self.client.create_collection(
                    name=self.collection_name,
                    metadata={"hnsw:space": "cosine"}
                )
                logger.info(f"创建新集合: {self.collection_name}")
                
        except ImportError:
            logger.warning("ChromaDB未安装，使用模拟向量存储")
            self.client = None
            self.collection = MockCollection()
    
    async def add_documents(self, documents: List[Dict[str, Any]]) -> None:
        """异步添加文档到向量存储
        
        Args:
            documents: 文档列表，每个文档包含content和metadata
        """
        if not documents:
            logger.warning("没有文档需要添加")
            return
        
        try:
            texts = [doc["content"] for doc in documents]
            metadatas = [doc["metadata"] for doc in documents]
            
            logger.info(f"开始异步生成 {len(texts)} 个文档的嵌入向量...")
            embeddings = await self.embedding_model.embed_documents(texts)
            
            ids = [f"{meta.get('document_id', f'unknown_{i}')}_chunk_{meta.get('chunk_index', i)}" for i, meta in enumerate(metadatas)]
            
            self.collection.add(
                embeddings=embeddings,
                documents=texts,
                metadatas=metadatas,
                ids=ids
            )
            
            logger.info(f"成功添加 {len(documents)} 个文档到向量存储")
            
        except Exception as e:
            logger.error(f"添加文档到向量存储时出错: {str(e)}")
            raise
    
    async def similarity_search(self, query: str, k: int = 5, filter_dict: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """异步相似度搜索
        
        Args:
            query: 查询文本
            k: 返回结果数量
            filter_dict: 过滤条件
            
        Returns:
            搜索结果列表
        """
        try:
            query_embedding = await self.embedding_model.embed_query(query)
            
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=k,
                where=filter_dict
            )
            
            documents = []
            if results and results['documents'] and results['documents'][0]:
                for i, doc_content in enumerate(results['documents'][0]):
                    distance = results['distances'][0][i] if results['distances'] and results['distances'][0] else 0.0
                    documents.append({
                        'content': doc_content,
                        'metadata': results['metadatas'][0][i] if results['metadatas'] and results['metadatas'][0] else {},
                        'score': 1 - distance
                    })
            
            logger.info(f"相似度搜索完成，返回 {len(documents)} 个结果")
            return documents
            
        except Exception as e:
            logger.error(f"相似度搜索时出错: {str(e)}")
            return []
    
    async def delete_document(self, document_id: str) -> bool:
        """异步删除文档的向量数据
        
        Args:
            document_id: 文档ID
            
        Returns:
            删除是否成功
        """
        try:
            all_data = self.collection.get(where={"document_id": document_id})
            ids_to_delete = all_data.get('ids', [])
            
            if ids_to_delete:
                self.collection.delete(ids=ids_to_delete)
                logger.info(f"成功删除文档 {document_id} 的 {len(ids_to_delete)} 条向量记录")
            else:
                logger.warning(f"未找到文档 {document_id} 的向量记录")
            return True
                
        except Exception as e:
            logger.error(f"删除文档向量数据时出错: {str(e)}")
            return False
    
    async def update_document(self, ids: List[str], metadatas: List[Dict[str, Any]]) -> bool:
        """更新文档元数据
        
        Args:
            ids: 要更新的文档ID列表
            metadatas: 新的元数据列表，与ids一一对应
            
        Returns:
            更新是否成功
        """
        try:
            if len(ids) != len(metadatas):
                logger.error("IDs和metadatas列表长度不匹配")
                return False
                
            self.collection.update(
                ids=ids,
                metadatas=metadatas
            )
            
            logger.info(f"成功更新 {len(ids)} 个文档的元数据")
            return True
            
        except Exception as e:
            logger.error(f"更新文档元数据时出错: {str(e)}")
            return False
    
    def get_retriever(self, search_type: str = "similarity", **kwargs: Any) -> "VectorStoreRetriever":
        """获取检索器"""
        return VectorStoreRetriever(self, search_type, **kwargs)


class VectorStoreRetriever:
    """向量存储检索器（异步）"""
    
    def __init__(self, vector_store: VectorStore, search_type: str = "similarity", **kwargs: Any):
        self.vector_store = vector_store
        self.search_type = search_type
        self.k = kwargs.get("k", 5)
        self.filter_dict = kwargs.get("filter", None)
    
    async def get_relevant_documents(self, query: str) -> List[Dict[str, Any]]:
        """异步获取相关文档"""
        results = await self.vector_store.similarity_search(
            query=query,
            k=self.k,
            filter_dict=self.filter_dict
        )
        
        return [{'page_content': r['content'], 'metadata': r['metadata']} for r in results]


class MockCollection:
    """模拟集合，用于开发测试"""
    
    def __init__(self) -> None:
        self.documents: List[str] = []
        self.embeddings: List[List[float]] = []
        self.metadatas: List[Dict[str, Any]] = []
        self.ids: List[str] = []
    
    def add(self, embeddings: List[List[float]], documents: List[str], metadatas: List[Dict[str, Any]], ids: List[str]) -> None:
        self.embeddings.extend(embeddings)
        self.documents.extend(documents)
        self.metadatas.extend(metadatas)
        self.ids.extend(ids)
    
    def query(self, query_embeddings: List[List[float]], n_results: int = 5, where: Optional[Dict[str, Any]] = None) -> Dict[str, List[Any]]:
        if not self.documents:
            return {'documents': [[]], 'metadatas': [[]], 'distances': [[]]}
        
        n = min(n_results, len(self.documents))
        return {
            'documents': [self.documents[:n]],
            'metadatas': [self.metadatas[:n]],
            'distances': [[0.1 * i for i in range(n)]]
        }
    
    def get(self, where: Optional[Dict[str, Any]] = None) -> Dict[str, List[Any]]:
        # 模拟 where 子句过滤
        if where and 'document_id' in where:
            doc_id_to_find = where['document_id']
            indices = [i for i, meta in enumerate(self.metadatas) if meta.get('document_id') == doc_id_to_find]
            return {
                'ids': [self.ids[i] for i in indices],
                'documents': [self.documents[i] for i in indices],
                'metadatas': [self.metadatas[i] for i in indices],
            }
        return {
            'ids': self.ids,
            'documents': self.documents,
            'metadatas': self.metadatas,
        }
    
    def delete(self, ids: List[str]) -> None:
        indices_to_remove = {i for i, doc_id in enumerate(self.ids) if doc_id in ids}
        self.ids = [v for i, v in enumerate(self.ids) if i not in indices_to_remove]
        self.documents = [v for i, v in enumerate(self.documents) if i not in indices_to_remove]
        self.metadatas = [v for i, v in enumerate(self.metadatas) if i not in indices_to_remove]
        self.embeddings = [v for i, v in enumerate(self.embeddings) if i not in indices_to_remove]
    
    def update(self, ids: List[str], metadatas: List[Dict[str, Any]]) -> None:
        """更新文档元数据"""
        for update_id, new_metadata in zip(ids, metadatas):
            for i, existing_id in enumerate(self.ids):
                if existing_id == update_id:
                    # 更新现有元数据
                    self.metadatas[i].update(new_metadata)
                    break