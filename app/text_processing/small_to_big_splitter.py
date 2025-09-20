"""小-大检索分块器

实现两阶段分块逻辑：
1. 先将文档切分为大块(Parent Chunks) - 1024字符
2. 再将大块切分为小块(Child Chunks) - 256字符
"""

import uuid
from typing import List, Dict, Any, Tuple
from app.core.config import get_settings
from app.utils.logger import setup_logger
from app.embeddings.text_splitter import MedicalTextSplitter

logger = setup_logger(__name__)


class SmallToBigSplitter:
    """小-大检索分块器"""
    
    def __init__(self):
        """初始化分块器"""
        self.settings = get_settings()
        self.parent_chunk_size = self.settings.parent_chunk_size
        self.child_chunk_size = self.settings.child_chunk_size
        self.parent_chunk_overlap = self.settings.parent_chunk_overlap
        self.child_chunk_overlap = self.settings.child_chunk_overlap
        
        # 初始化医疗文本分块器
        self.parent_splitter = MedicalTextSplitter(
            chunk_size=self.parent_chunk_size,
            chunk_overlap=self.parent_chunk_overlap
        )
        self.child_splitter = MedicalTextSplitter(
            chunk_size=self.child_chunk_size,
            chunk_overlap=self.child_chunk_overlap
        )
        
        logger.info(f"小-大分块器初始化完成 - 大块:{self.parent_chunk_size}, 小块:{self.child_chunk_size}")
    
    def split_document(self, document_id: str, content: str) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """对文档进行两阶段分块
        
        Args:
            document_id: 文档ID
            content: 文档内容
            
        Returns:
            Tuple[parent_chunks, child_chunks]: (大块列表, 小块列表)
        """
        try:
            # 第一阶段：使用 MedicalTextSplitter 切分为大块
            parent_chunk_texts = self.parent_splitter.split_text(content)
            parent_chunks = []
            
            for chunk_index, chunk_content in enumerate(parent_chunk_texts):
                parent_chunk_id = str(uuid.uuid4())
                parent_chunk = {
                    'id': parent_chunk_id,
                    'document_id': document_id,
                    'content': chunk_content,
                    'chunk_index': chunk_index,
                    'start_char': 0,  # 由于使用了 split_text，无法精确计算位置
                    'end_char': len(chunk_content)
                }
                parent_chunks.append(parent_chunk)
            
            logger.info(f"文档 {document_id} 切分为 {len(parent_chunks)} 个大块")
            
            # 第二阶段：将每个大块使用 MedicalTextSplitter 切分为小块
            child_chunks = []
            for parent_chunk in parent_chunks:
                child_chunk_texts = self.child_splitter.split_text(parent_chunk['content'])
                
                for child_index, child_content in enumerate(child_chunk_texts):
                    child_chunk_id = str(uuid.uuid4())
                    child_chunk = {
                        'id': child_chunk_id,
                        'parent_chunk_id': parent_chunk['id'],
                        'document_id': document_id,
                        'content': child_content,
                        'child_index': child_index,
                        'start_char': 0,  # 由于使用了 split_text，无法精确计算位置
                        'end_char': len(child_content)
                    }
                    child_chunks.append(child_chunk)
            
            logger.info(f"文档 {document_id} 总共生成 {len(child_chunks)} 个小块")
            
            return parent_chunks, child_chunks
            
        except Exception as e:
            logger.error(f"文档分块失败: {e}")
            raise
    

    
    def get_chunk_statistics(self, parent_chunks: List[Dict[str, Any]], child_chunks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """获取分块统计信息
        
        Args:
            parent_chunks: 大块列表
            child_chunks: 小块列表
            
        Returns:
            统计信息
        """
        if not parent_chunks:
            return {
                'parent_chunks_count': 0,
                'child_chunks_count': 0,
                'avg_parent_chunk_size': 0,
                'avg_child_chunk_size': 0,
                'avg_children_per_parent': 0
            }
        
        # 计算平均大小
        avg_parent_size = sum(len(chunk['content']) for chunk in parent_chunks) / len(parent_chunks)
        avg_child_size = sum(len(chunk['content']) for chunk in child_chunks) / len(child_chunks) if child_chunks else 0
        
        # 计算每个大块的平均小块数量
        avg_children_per_parent = len(child_chunks) / len(parent_chunks) if parent_chunks else 0
        
        return {
            'parent_chunks_count': len(parent_chunks),
            'child_chunks_count': len(child_chunks),
            'avg_parent_chunk_size': round(avg_parent_size, 2),
            'avg_child_chunk_size': round(avg_child_size, 2),
            'avg_children_per_parent': round(avg_children_per_parent, 2)
        }


def create_small_to_big_splitter() -> SmallToBigSplitter:
    """创建小-大分块器实例
    
    Returns:
        小-大分块器实例
    """
    return SmallToBigSplitter()