"""
嵌入向量模型接口
"""

from typing import List, Optional
from app.core.config import settings
from app.workflow.qianwen_client import get_qianwen_client
from app.utils.logger import setup_logger

logger = setup_logger(__name__)


class QianwenEmbeddings:
    """千问嵌入向量模型（异步）"""
    
    def __init__(self, model: Optional[str] = None):
        """初始化千问嵌入向量模型
        
        Args:
            model: 模型名称
        """
        self.model = model or settings.qianwen_embedding_model
        logger.info(f"千问嵌入向量模型初始化完成: {self.model}")
    
    async def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """异步嵌入文档列表
        
        Args:
            texts: 文档文本列表
            
        Returns:
            嵌入向量列表
        """
        if not texts:
            return []
        
        try:
            logger.debug(f"开始异步嵌入 {len(texts)} 个文档")
            client = await get_qianwen_client()
            async with client as c:
                embeddings = await c.batch_embeddings(texts, model=self.model)
            logger.debug(f"文档嵌入成功，获得 {len(embeddings)} 个向量")
            return embeddings
        except Exception as e:
            logger.error(f"文档嵌入失败: {str(e)}")
            raise
    
    async def embed_query(self, text: str) -> List[float]:
        """异步嵌入单个查询
        
        Args:
            text: 查询文本
            
        Returns:
            嵌入向量
        """
        try:
            logger.debug(f"开始异步嵌入查询: {text[:50]}...")
            client = await get_qianwen_client()
            async with client as c:
                embedding = await c.get_single_embedding(text, model=self.model)
            logger.debug("查询嵌入成功")
            return embedding
        except Exception as e:
            logger.error(f"查询嵌入失败: {str(e)}")
            raise

# 全局单例
_qianwen_embeddings: Optional[QianwenEmbeddings] = None

def get_embeddings() -> QianwenEmbeddings:
    """获取千问嵌入向量模型实例（单例）"""
    global _qianwen_embeddings
    if _qianwen_embeddings is None:
        _qianwen_embeddings = QianwenEmbeddings()
    return _qianwen_embeddings