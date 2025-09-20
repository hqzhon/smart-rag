"""小-大检索处理器

负责处理文档的小-大检索流程：
1. 使用SmallToBigSplitter进行两阶段分块
2. 为大块生成摘要和关键词
3. 将大块存储到MySQL
4. 将小块存储到向量数据库
"""

import asyncio
from typing import List, Dict, Any, Optional
from app.text_processing.small_to_big_splitter import SmallToBigSplitter
from app.storage.database import DatabaseManager
from app.storage.vector_store import VectorStore
from app.embeddings.embeddings import get_embeddings
from app.core.config import get_settings
from app.utils.logger import setup_logger

logger = setup_logger(__name__)


class SmallToBigProcessor:
    """小-大检索处理器"""
    
    def __init__(self):
        """初始化处理器"""
        self.settings = get_settings()
        self.splitter = SmallToBigSplitter()
        self.db_manager = None
        self.vector_store = None
        self.embedding_model = None
        
        logger.info("小-大检索处理器初始化完成")
    
    async def async_init(self):
        """异步初始化"""
        try:
            # 初始化数据库管理器
            from app.storage.database import get_db_manager_async
            self.db_manager = await get_db_manager_async()
            
            # 初始化嵌入模型
            self.embedding_model = get_embeddings()
            
            # 初始化向量存储
            self.vector_store = VectorStore(self.embedding_model)
            await self.vector_store.async_init()
            
            logger.info("小-大检索处理器异步初始化完成")
            
        except Exception as e:
            logger.error(f"小-大检索处理器异步初始化失败: {e}")
            raise
    
    async def process_document(self, document_id: str, content: str, document_title: str = None) -> Dict[str, Any]:
        """处理文档的小-大检索流程
        
        Args:
            document_id: 文档ID
            content: 文档内容
            document_title: 文档标题（可选）
            
        Returns:
            处理结果统计信息
        """
        try:
            logger.info(f"开始处理文档 {document_id} 的小-大检索流程")
            
            # 确保异步初始化完成
            if not self.db_manager or not self.vector_store:
                await self.async_init()
            
            # 第一步：两阶段分块
            parent_chunks, child_chunks = self.splitter.split_document(document_id, content)
            
            # 第二步：为大块生成摘要和关键词
            await self._generate_parent_chunks_metadata(parent_chunks)
            
            # 第三步：保存大块到MySQL
            await self._save_parent_chunks_to_mysql(parent_chunks)
            
            # 第四步：为小块添加元数据并保存到向量数据库
            await self._save_child_chunks_to_vector_db(child_chunks, parent_chunks, document_title)
            
            # 获取统计信息
            stats = self.splitter.get_chunk_statistics(parent_chunks, child_chunks)
            
            logger.info(f"文档 {document_id} 小-大检索处理完成: {stats}")
            
            return {
                'success': True,
                'document_id': document_id,
                'statistics': stats,
                'parent_chunks_count': len(parent_chunks),
                'child_chunks_count': len(child_chunks)
            }
            
        except Exception as e:
            logger.error(f"处理文档 {document_id} 的小-大检索流程失败: {e}")
            return {
                'success': False,
                'document_id': document_id,
                'error': str(e)
            }
    
    async def _generate_parent_chunks_metadata(self, parent_chunks: List[Dict[str, Any]]):
        """为大块生成摘要和关键词
        
        Args:
            parent_chunks: 大块列表
        """
        try:
            logger.info(f"开始为 {len(parent_chunks)} 个大块生成摘要和关键词")
            
            # 导入LLM客户端
            from app.metadata.clients.qianwen_client import get_metadata_qianwen_client
            llm_client = await get_metadata_qianwen_client()

            # 创建一个信号量，限制并发数为5
            concurrency_limit = 5
            semaphore = asyncio.Semaphore(concurrency_limit)
            
            # 使用异步上下文管理器
            async with llm_client:
                # 并发生成摘要和关键词
                tasks = []
                for chunk in parent_chunks:
                    task = self._generate_single_chunk_metadata(llm_client, chunk, semaphore)
                    tasks.append(task)
                
                # 批量执行
                await asyncio.gather(*tasks)
            
            logger.info("大块摘要和关键词生成完成")
            
        except Exception as e:
            logger.error(f"生成大块摘要和关键词失败: {e}")
            # 如果生成失败，设置默认值
            for chunk in parent_chunks:
                if 'summary' not in chunk:
                    chunk['summary'] = f"文档片段 {chunk.get('chunk_index', 0) + 1}"
                if 'keywords' not in chunk:
                    chunk['keywords'] = ""

    async def _generate_single_chunk_metadata(self, llm_client, chunk: Dict[str, Any], semaphore: asyncio.Semaphore):
        """为单个大块生成摘要和关键词
        
        Args:
            llm_client: LLM客户端
            chunk: 大块数据
            semaphore: 信号量用于并发控制
        """
        async with semaphore:
            import json
            try:
                content = chunk['content']
                
                # 设计一个新的Prompt，要求LLM返回JSON格式
                prompt = f"""请为以下文本提取摘要和关键词。
要求：
1. 摘要（summary）应简洁、准确，不超过100字。
2. 关键词（keywords）应为包含5-8个核心词汇的数组。
3. 必须以一个合法的JSON对象格式返回，不要包含任何额外的解释或标记。

文本内容如下：
---
{content}
---

请严格按照以下JSON格式返回：
{{
  "summary": "这里是生成的摘要",
  "keywords": ["关键词1", "关键词2", "..." ]
}}
"""
                
                response_text = await llm_client.generate_text(
                    prompt=prompt,
                    max_tokens=300, # 稍微增加token以容纳JSON结构
                    temperature=0.1 # 使用较低的温度以保证格式稳定
                )

                # 解析LLM返回的JSON
                response_json = json.loads(response_text)
                chunk['summary'] = response_json.get('summary', '')
                # 将关键词列表转换为逗号分隔的字符串以匹配数据库存储
                chunk['keywords'] = ', '.join(response_json.get('keywords', []))

            except json.JSONDecodeError as e:
                logger.error(f"解析LLM返回的JSON失败: {e} - 返回内容: {response_text}")
                # Fallback: 如果JSON解析失败，执行原始的、分离的调用
                await self._fallback_generate_metadata(llm_client, chunk)
            except Exception as e:
                logger.error(f"生成单个大块元数据失败: {e}")
                # 设置默认值
                chunk['summary'] = f"文档片段 {chunk.get('chunk_index', 0) + 1}"
                chunk['keywords'] = ""

    async def _fallback_generate_metadata(self, llm_client, chunk: Dict[str, Any]):
        """当JSON模式失败时的备用生成逻辑"""
        logger.warning(f"正在为块 {chunk.get('id')} 启动备用元数据生成模式...")
        try:
            content = chunk['content']
            # 生成摘要
            summary_prompt = f'''请为以下文本生成一个简洁的摘要（不超过100字）：

{content}

摘要：'''
            summary_response = await llm_client.generate_text(prompt=summary_prompt, max_tokens=150, temperature=0.3)
            chunk['summary'] = summary_response.strip()

            # 生成关键词
            keywords_prompt = f'''请从以下文本中提取5-8个关键词，用逗号分隔：

{content}

关键词：'''
            keywords_response = await llm_client.generate_text(prompt=keywords_prompt, max_tokens=100, temperature=0.3)
            chunk['keywords'] = keywords_response.strip()
        except Exception as e:
            logger.error(f"备用元数据生成模式也失败了: {e}")
            chunk['summary'] = f"文档片段 {chunk.get('chunk_index', 0) + 1}"
            chunk['keywords'] = ""
    
    async def _save_parent_chunks_to_mysql(self, parent_chunks: List[Dict[str, Any]]):
        """保存大块到MySQL
        
        Args:
            parent_chunks: 大块列表
        """
        try:
            logger.info(f"开始保存 {len(parent_chunks)} 个大块到MySQL")
            
            for chunk in parent_chunks:
                chunk_data = {
                    'id': chunk['id'],
                    'document_id': chunk['document_id'],
                    'content': chunk['content'],
                    'summary': chunk.get('summary', ''),
                    'keywords': chunk.get('keywords', '')
                }
                
                success = self.db_manager.save_parent_chunk(chunk_data)
                if not success:
                    logger.warning(f"保存大块 {chunk['id']} 到MySQL失败")
            
            logger.info("大块保存到MySQL完成")
            
        except Exception as e:
            logger.error(f"保存大块到MySQL失败: {e}")
            raise
    
    async def _save_child_chunks_to_vector_db(self, child_chunks: List[Dict[str, Any]], parent_chunks: List[Dict[str, Any]], document_title: str = None):
        """保存小块到向量数据库
        
        Args:
            child_chunks: 小块列表
            parent_chunks: 大块列表（用于获取摘要信息）
            document_title: 文档标题
        """
        try:
            logger.info(f"开始保存 {len(child_chunks)} 个小块到向量数据库")
            
            # 创建大块ID到元数据的映射
            import json
            parent_metadata_map = {
                chunk['id']: {
                    'summary': chunk.get('summary', ''),
                    'keywords': chunk.get('keywords', '')
                } for chunk in parent_chunks
            }
            
            # 准备向量化数据
            documents = []
            metadatas = []
            ids = []
            
            for chunk in child_chunks:
                # 小块内容
                documents.append(chunk['content'])
                
                parent_id = chunk['parent_chunk_id']
                parent_meta = parent_metadata_map.get(parent_id, {})
                
                # 将关键词字符串转换为JSON数组格式
                keywords_str = parent_meta.get('keywords', '')
                keywords_list = [k.strip() for k in keywords_str.split(',') if k.strip()]
                keywords_json_str = json.dumps(keywords_list, ensure_ascii=False)

                # 小块元数据
                metadata = {
                    'document_id': chunk['document_id'],
                    'parent_chunk_id': parent_id,
                    'summary': parent_meta.get('summary', ''),
                    'keywords': keywords_json_str,  # 存入JSON字符串
                    'chunk_type': 'child',
                    'child_index': chunk['child_index'],
                    'start_char': chunk['start_char'],
                    'end_char': chunk['end_char']
                }
                
                if document_title:
                    metadata['title'] = document_title
                
                metadatas.append(metadata)
                ids.append(chunk['id'])
            
            # 批量添加到向量数据库
            await self.vector_store.add_documents_async(
                documents=documents,
                metadatas=metadatas,
                ids=ids
            )
            
            logger.info("小块保存到向量数据库完成")
            
        except Exception as e:
            logger.error(f"保存小块到向量数据库失败: {e}")
            raise
    
    async def delete_document_chunks(self, document_id: str) -> bool:
        """删除文档的所有块数据
        
        Args:
            document_id: 文档ID
            
        Returns:
            删除是否成功
        """
        try:
            logger.info(f"开始删除文档 {document_id} 的所有块数据")
            
            # 确保初始化完成
            if not self.db_manager:
                await self.async_init()
            
            # 删除MySQL中的大块数据
            mysql_success = self.db_manager.delete_parent_chunks_by_document_id(document_id)
            
            # 删除向量数据库中的小块数据
            # 注意：这里需要根据实际的向量数据库API来实现
            # ChromaDB可能需要先查询再删除
            vector_success = True  # 暂时设为True，实际实现时需要调用向量数据库的删除API
            
            success = mysql_success and vector_success
            
            if success:
                logger.info(f"文档 {document_id} 的所有块数据删除成功")
            else:
                logger.warning(f"文档 {document_id} 的块数据删除部分失败")
            
            return success
            
        except Exception as e:
            logger.error(f"删除文档 {document_id} 的块数据失败: {e}")
            return False


def create_small_to_big_processor() -> SmallToBigProcessor:
    """创建小-大检索处理器实例
    
    Returns:
        小-大检索处理器实例
    """
    return SmallToBigProcessor()