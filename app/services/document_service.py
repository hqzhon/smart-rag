"""
文档服务
"""

import os
import uuid
import asyncio
import time
from typing import List, Dict, Any, Optional
from pathlib import Path
from datetime import datetime
from app.models.document_models import Document, ProcessingResult
from app.processors.document_processor import DocumentProcessor
from app.services.multi_format_processor import MultiFormatProcessor, ProcessingError
from app.embeddings.text_splitter import MedicalTextSplitter
from app.text_processing.small_to_big_processor import SmallToBigProcessor
from app.utils.logger import setup_logger
from app.storage.database import DatabaseManager
from app.core.config import get_settings
from app.core.redis_client import get_redis_client

logger = setup_logger(__name__)


class DocumentService:
    """文档服务类，处理文档相关的业务逻辑"""
    
    def __init__(self):
        """初始化文档服务"""
        self.settings = get_settings()
        self.upload_dir = os.getenv("UPLOAD_DIR", "./data/uploads")
        self.processed_dir = os.getenv("PROCESSED_DIR", "./data/processed")
        self.max_file_size = self._parse_file_size(os.getenv("MAX_FILE_SIZE", "50MB"))
        
        # 确保目录存在
        os.makedirs(self.upload_dir, exist_ok=True)
        os.makedirs(self.processed_dir, exist_ok=True)
        
        # 初始化轻量级组件
        self.document_processor = DocumentProcessor(self.upload_dir, self.processed_dir) 
        self.multi_format_processor = MultiFormatProcessor()
        
        # 初始化小-大检索处理器
        self.small_to_big_processor = None
        
        # 延迟初始化重量级组件
        self.db_manager = None
        
        # 初始化Redis客户端
        self.redis_client = get_redis_client()
        
        logger.info("文档服务基础初始化完成")
    
    async def async_init(self):
        """异步初始化重量级组件"""
        logger.info("开始异步初始化文档服务重量级组件...")
        # 异步初始化数据库管理器
        self.db_manager = DatabaseManager()
        
        # 初始化小-大检索处理器
        if self.small_to_big_processor is None:
            self.small_to_big_processor = SmallToBigProcessor()
            await self.small_to_big_processor.async_init()
        
        logger.info("文档服务异步初始化完成")
    
    def _parse_file_size(self, size_str: str) -> int:
        """解析文件大小字符串"""
        size_str = size_str.upper()
        if size_str.endswith('MB'):
            return int(size_str[:-2]) * 1024 * 1024
        elif size_str.endswith('KB'):
            return int(size_str[:-2]) * 1024
        elif size_str.endswith('GB'):
            return int(size_str[:-2]) * 1024 * 1024 * 1024
        else:
            return int(size_str)
    
    def _publish_progress(self, document_id: str, status: str, progress: int = 0, message: str = ""):
        """发布文档处理进度到Redis
        
        支持的状态值包括:
        - uploading: 文件上传中
        - processing: 文档处理中
        - parsed: 文档解析完成
        - chunking: 文本分块中
        - chunked: 文本分块完成
        - saved_content: 内容已保存
        - vectorizing: 向量化处理中
        - vectorized: 向量化完成
        - completed: 处理完成
        - failed: 处理失败
        - error: 发生错误
        - ready: 文档就绪
        - chat_ready: 可用于聊天
        - generating_metadata: 生成元数据中
        - uploaded: 上传完成
        - connected: SSE连接建立
        - heartbeat: 心跳信号
        - timeout: 超时
        """
        try:
            channel = f"document_progress_{document_id}"
            progress_data = {
                "document_id": document_id,
                "status": status,
                "progress": progress,
                "message": message,
                "timestamp": datetime.now().isoformat()
            }
            self.redis_client.publish(channel, progress_data)
            logger.debug(f"Progress published for {document_id}: {status} ({progress}%)")
        except Exception as e:
            logger.error(f"Failed to publish progress for {document_id}: {e}")
    
    async def upload_document(self, file_content: bytes, filename: str, content_type: str) -> Document:
        """上传文档
        
        Args:
            file_content: 文件内容
            filename: 文件名
            content_type: 文件类型
            
        Returns:
            文档对象
        """
        try:
            # 验证文件
            self._validate_file(file_content, filename, content_type)
            
            # 生成文档ID和文件路径
            document_id = str(uuid.uuid4())
            file_extension = Path(filename).suffix
            safe_filename = f"{document_id}{file_extension}"
            file_path = os.path.join(self.upload_dir, safe_filename)
            
            # 保存文件
            with open(file_path, 'wb') as f:
                f.write(file_content)
            
            # 创建文档对象
            document = Document(
                id=document_id,
                filename=filename,
                file_path=file_path,
                file_size=len(file_content),
                content_type=content_type,
                upload_time=datetime.now(),
                processed=False,
                processing_status="uploaded",
                status="uploading"  # 设置初始状态为uploading
            )
            
            # 发布上传完成进度
            self._publish_progress(document_id, "uploaded", 10, "文件上传完成")
            
            # 立即保存基础文档信息到MySQL数据库
            try:
                doc_data = {
                    'id': document_id,
                    'title': filename,
                    'content': '',  # 上传时内容为空，处理后再更新
                    'file_path': file_path,
                    'file_size': len(file_content),
                    'file_type': content_type,
                    'status': 'uploading',  # 设置初始状态
                    'metadata': {
                        'original_filename': filename,
                        'processing_status': 'uploaded',
                        'vectorized': False,
                        'vectorization_status': 'pending'
                    }
                }
                
                self.db_manager.save_document(doc_data)
                logger.info(f"基础文档信息已保存到数据库: {document_id}")
                
                # 发布数据库保存完成进度
                self._publish_progress(document_id, "saved", 20, "文档信息已保存")
                
            except Exception as db_error:
                # 如果数据库保存失败，删除已保存的文件并抛出异常
                if os.path.exists(file_path):
                    os.remove(file_path)
                logger.error(f"保存基础文档信息到数据库失败: {str(db_error)}")
                raise Exception(f"文档上传失败，数据库保存错误: {str(db_error)}")
            
            logger.info(f"文档上传成功: {filename} -> {document_id}")
            return document
            
        except Exception as e:
            logger.error(f"文档上传失败: {str(e)}")
            raise
    
    def _validate_file(self, file_content: bytes, filename: str, content_type: str):
        """验证文件"""
        # 检查文件大小
        if len(file_content) > self.max_file_size:
            raise ValueError(f"文件大小超过限制: {len(file_content)} > {self.max_file_size}")
        
        # 检查文件类型和扩展名
        file_extension = Path(filename).suffix.lower()
        
        # 使用MultiFormatProcessor验证文件格式
        if not self.multi_format_processor.is_supported_format(filename):
            supported_formats = self.multi_format_processor.get_supported_formats()
            raise ValueError(f"不支持的文件格式: {file_extension}，支持的格式: {supported_formats}")
        
        # 验证MIME类型
        expected_mime_types = self.multi_format_processor.get_mime_types_for_extension(file_extension)
        if expected_mime_types and content_type not in expected_mime_types:
            raise ValueError(f"文件类型不匹配: {content_type}，期望: {expected_mime_types}")
    
    async def process_document(self, document: Document) -> ProcessingResult:
        """处理文档，提取文本、分块并进行向量化（仅使用小-大检索策略）
        
        Args:
            document: 文档对象
            
        Returns:
            处理结果
        """
        start_time = datetime.now()
        logger.info(f"开始处理文档: {document.filename} (ID: {document.id})")

        try:
            # 1. 更新状态并发布进度
            self.db_manager.update_document(document.id, {'status': 'processing'})
            self._publish_progress(document.id, "processing", 30, "开始解析文档内容")

            # 2. 解析文档内容
            try:
                extracted_data = await self.document_processor.process_single_document(document.file_path, document.id) 
            except Exception as e:
                logger.warning(f"EnhancedPDFProcessor失败: {e}, 回退到MultiFormatProcessor...")
                extracted_data = await self.multi_format_processor.process_document_async(document.file_path)
            
            self._publish_progress(document.id, "parsed", 50, "文档内容解析完成")

            content = extracted_data.get('text', '')
            document_title = extracted_data.get('title', document.filename) or document.filename 

            if not content.strip():
                raise ProcessingError("文档内容为空，无法处理。")

            # 3. 执行小-大检索处理流程 (这是唯一的处理路径)
            logger.info(f"文档 {document.id} 将采用 [小-大检索] 模式处理")
            self._publish_progress(document.id, "small_to_big_processing", 65, "开始小-大分块与处理")
            
            s2b_result = await self.small_to_big_processor.process_document(
                document_id=document.id,
                content=content,
                document_title=document_title
            )
            if not s2b_result.get('success'):
                raise Exception(f"小-大检索处理失败: {s2b_result.get('error', '未知错误')}")
            
            total_chunks = s2b_result.get('parent_chunks_count', 0)
            logger.info(f"小-大检索处理成功, 父块数: {total_chunks}")

            # 4. 最终化处理：更新数据库状态和元数据
            processing_time = (datetime.now() - start_time).total_seconds()
            final_metadata = self._build_final_metadata(document, extracted_data, total_chunks, processing_time)

            self.db_manager.update_document(document.id, {
                'title': document_title,
                'content': content, # 保存完整原文
                'vectorized': True,
                'vectorization_status': 'completed',
                'vectorization_time': datetime.now(),
                'status': 'chat_ready',
                'metadata': final_metadata
            })
            
            self._publish_progress(document.id, "chat_ready", 100, f"文档就绪, 耗时{processing_time:.1f}秒")
            logger.info(f"文档 {document.id} 处理完全成功.")

            return ProcessingResult(
                document_id=document.id,
                success=True,
                total_chunks=total_chunks,
                processing_time=processing_time,
                extracted_text_length=len(content),
                tables_count=len(extracted_data.get("tables", [])),
                references_count=len(extracted_data.get("references", [])),
                images_count=len(extracted_data.get("images", []))
            )
        except Exception as e:
            logger.error(f"文档 {document.id} 处理失败: {str(e)}")
            self.db_manager.update_document(document.id, {
                'status': 'error',
                'vectorization_status': 'failed',
                'metadata': {'error': error_message}  
            })
            self._publish_progress(document.id, "error", 100, f"处理失败: {str(e)}")
            raise ProcessingError(f"文档处理失败: {str(e)}")

    def _build_final_metadata(self, document: Document, extracted_data: dict, total_chunks: int, processing_time: float) -> dict:
        """构建最终用于存储的元数据字典"""
        return {
            'original_filename': document.filename,
            'chunks_count': total_chunks,
            'processing_time': processing_time,
            'tables_count': len(extracted_data.get('tables', [])),
            'references_count': len(extracted_data.get('references', [])),
            'images_count': len(extracted_data.get('images', [])),
            'processing_status': 'completed',
            'vectorized': True,
            'vectorization_status': 'completed',
            'file_format': extracted_data.get('metadata', {}).get('file_format', Path(document.filename).suffix.lower()),
            'total_pages': extracted_data.get('metadata', {}).get('total_pages', 0),
        }
    
    async def get_document(self, document_id: str) -> Optional[Document]:
        """获取文档信息
        
        Args:
            document_id: 文档ID
            
        Returns:
            文档对象或None
        """
        try:
            doc_data = self.db_manager.get_document(document_id)
            if doc_data:
                # 将数据库记录转换为Document对象
                return Document(
                    id=doc_data['id'],
                    filename=doc_data['title'],
                    file_path=doc_data.get('file_path', ''),
                    file_size=doc_data.get('file_size', 0),
                    content_type=doc_data.get('file_type', ''),
                    upload_time=doc_data.get('created_at', datetime.now()),
                    processed=True,
                    processing_status="completed"
                )
            return None
        except Exception as e:
            logger.error(f"获取文档信息失败: {str(e)}")
            return None
    
    async def delete_document(self, document_id: str) -> bool:
        """删除文档 - 原子性操作
        
        Args:
            document_id: 文档ID
            
        Returns:
            删除是否成功
        """
        # 用于回滚的状态记录
        rollback_actions = []
        
        try:
            from app.storage.database import get_db_manager_async
            from app.storage.vector_store import VectorStore
            
            db = await get_db_manager_async()
            
            # 1. 获取文档信息
            document = db.get_document(document_id)
            if not document:
                logger.warning(f"文档不存在: {document_id}")
                return False
            
            file_path = document.get('file_path')
            logger.info(f"开始删除文档: {document_id}")
            
            # 小-大检索模式：删除大块和小块数据
            if self.small_to_big_processor:
                vector_deleted = await self.small_to_big_processor.delete_document_chunks(document_id)
            else:
                # 如果处理器未初始化，手动删除
                vector_store = VectorStore()
                vector_deleted = await vector_store.delete_document(document_id)
                # 删除MySQL中的大块数据
                db.delete_parent_chunks_by_document_id(document_id)
            
            if not vector_deleted:
                logger.error(f"删除向量存储数据失败: {document_id}")
                return False
            
            logger.info(f"向量存储数据删除成功: {document_id}")
            rollback_actions.append(('vector', document_id))
            
            # 3. 删除数据库记录（在事务中执行）
            db_deleted = db.delete_document(document_id)
            if not db_deleted:
                logger.error(f"删除数据库记录失败: {document_id}")
                # 回滚向量删除操作（注意：向量数据无法完全恢复，只能记录错误）
                logger.error(f"数据库删除失败，向量数据已被删除但无法恢复: {document_id}")
                return False
            
            logger.info(f"数据库记录删除成功: {document_id}")
            rollback_actions.append(('database', document_id))
            
            # 4. 删除物理文件（最后删除，因为文件删除失败不影响数据一致性）
            if file_path and os.path.exists(file_path):
                try:
                    # 先备份文件路径，以防需要恢复
                    backup_path = f"{file_path}.deleted_{int(time.time())}"
                    os.rename(file_path, backup_path)
                    rollback_actions.append(('file', file_path, backup_path))
                    
                    # 实际删除文件
                    os.remove(backup_path)
                    logger.info(f"物理文件删除成功: {file_path}")
                    
                except Exception as e:
                    logger.warning(f"删除物理文件失败: {e}，但数据库和向量数据已成功删除")
                    # 文件删除失败不影响整体操作成功
            
            logger.info(f"文档删除完全成功: {document_id}")
            return True
            
        except Exception as e:
            logger.error(f"文档删除过程中发生错误: {str(e)}")
            
            # 执行回滚操作
            await self._rollback_delete_operations(rollback_actions, document_id)
            return False
    
    async def _rollback_delete_operations(self, rollback_actions: list, document_id: str):
        """回滚删除操作
        
        Args:
            rollback_actions: 需要回滚的操作列表
            document_id: 文档ID
        """
        logger.warning(f"开始回滚文档删除操作: {document_id}")
        
        for action in reversed(rollback_actions):
            try:
                if action[0] == 'file' and len(action) == 3:
                    # 恢复文件
                    original_path, backup_path = action[1], action[2]
                    if os.path.exists(backup_path):
                        os.rename(backup_path, original_path)
                        logger.info(f"文件回滚成功: {original_path}")
                
                elif action[0] == 'database':
                    # 数据库回滚（注意：这里只能记录，实际恢复需要更复杂的逻辑）
                    logger.error(f"数据库记录已删除，需要手动恢复: {document_id}")
                
                elif action[0] == 'vector':
                    # 向量数据回滚（注意：向量数据删除后很难完全恢复）
                    logger.error(f"向量数据已删除，需要重新生成: {document_id}")
                    
            except Exception as e:
                logger.error(f"回滚操作失败 {action}: {str(e)}")
        
        logger.warning(f"文档删除回滚完成: {document_id}")
    
    async def list_documents(self, limit: int = 10, offset: int = 0) -> Dict[str, Any]:
        """获取文档列表（支持分页）
        
        Args:
            limit: 限制数量
            offset: 偏移量
            
        Returns:
            包含文档列表和分页信息的字典
        """
        try:
            # 调用数据库方法获取分页数据
            result = self.db_manager.list_documents(limit=limit, offset=offset)
            docs_data = result['documents']
            
            documents = []
            for doc_data in docs_data:
                document = Document(
                    id=doc_data['id'],
                    filename=doc_data['title'],
                    file_path=doc_data.get('file_path', ''),
                    file_size=doc_data.get('file_size', 0),
                    content_type=doc_data.get('file_type', ''),
                    upload_time=doc_data.get('created_at', datetime.now()),
                    processed=True,
                    processing_status="completed",
                    status=doc_data.get('status', 'ready')  # 添加status字段
                )
                documents.append(document)
            
            # 返回完整的分页信息
            return {
                'documents': documents,
                'total': result['total'],
                'page': result['page'],
                'page_size': result['page_size'],
                'total_pages': result['total_pages']
            }
        except Exception as e:
            logger.error(f"获取文档列表失败: {str(e)}")
            return {
                'documents': [],
                'total': 0,
                'page': 1,
                'page_size': limit,
                'total_pages': 0
            }
    
    def get_supported_formats(self) -> List[str]:
        """获取支持的文件格式"""
        return self.multi_format_processor.get_supported_formats()
    
    def get_supported_formats_info(self) -> Dict[str, Any]:
        """获取支持的文件格式详细信息"""
        formats = self.multi_format_processor.get_supported_formats()
        
        # 构建格式信息列表
        format_info_list = []
        format_details = {
            'pdf': {
                'extension': '.pdf',
                'mime_type': 'application/pdf',
                'format_name': 'PDF文档',
                'description': 'Portable Document Format',
                'max_size': self.settings.max_file_size,
                'features': ['text_extraction', 'table_detection', 'image_extraction']
            },
            'docx': {
                'extension': '.docx',
                'mime_type': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                'format_name': 'Word文档',
                'description': 'Microsoft Word Document',
                'max_size': self.settings.max_file_size,
                'features': ['text_extraction', 'table_detection', 'style_preservation']
            },
            'pptx': {
                'extension': '.pptx',
                'mime_type': 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
                'format_name': 'PowerPoint演示文稿',
                'description': 'Microsoft PowerPoint Presentation',
                'max_size': self.settings.max_file_size,
                'features': ['text_extraction', 'slide_detection', 'image_extraction']
            },
            'xlsx': {
                'extension': '.xlsx',
                'mime_type': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                'format_name': 'Excel电子表格',
                'description': 'Microsoft Excel Spreadsheet',
                'max_size': self.settings.max_file_size,
                'features': ['table_extraction', 'data_analysis', 'formula_detection']
            },
            'txt': {
                'extension': '.txt',
                'mime_type': 'text/plain',
                'format_name': '纯文本文件',
                'description': 'Plain Text File',
                'max_size': self.settings.max_file_size,
                'features': ['text_extraction', 'encoding_detection']
            },
            'md': {
                'extension': '.md',
                'mime_type': 'text/markdown',
                'format_name': 'Markdown文档',
                'description': 'Markdown Document',
                'max_size': self.settings.max_file_size,
                'features': ['text_extraction', 'structure_preservation', 'link_detection']
            }
        }
        
        for format_name in formats:
            if format_name in format_details:
                format_info_list.append(format_details[format_name])
        
        return {
            'formats': format_info_list,
            'max_file_size': self.settings.max_file_size,
            'processing_timeout': getattr(self.settings, 'processing_timeout', 300)
        }
    
    def get_upload_limits(self) -> Dict[str, Any]:
        """获取上传限制"""
        return {
            "max_file_size": self.max_file_size,
            "max_file_size_mb": self.max_file_size / (1024 * 1024),
            "supported_formats": self.get_supported_formats()
        }
    
    
    
    async def update_vectorization_for_new_documents(self) -> int:
        """为新上传但未向量化的文档进行增量向量化更新
        
        Returns:
            更新的文档数量
        """
        try:
            # 获取未向量化的文档
            unvectorized_docs = self.db_manager.get_documents_by_status(
                vectorized=False, 
                limit=50
            )
            
            if not unvectorized_docs:
                logger.info("没有需要向量化的文档")
                return 0
            
            logger.info(f"发现 {len(unvectorized_docs)} 个未向量化的文档")
            updated_count = 0
            
            for doc in unvectorized_docs:
                try:
                    # 更新状态为处理中
                    self.db_manager.update_document(doc['id'], {
                        "vectorization_status": "processing"
                    })
                    
                    # 读取已处理的文件内容
                    processed_file_path = os.path.join(self.processed_folder, f"{doc['id']}.txt")
                    if not os.path.exists(processed_file_path):
                        logger.warning(f"处理后的文件不存在: {processed_file_path}")
                        continue
                    
                    with open(processed_file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    # 分割文本
                    chunks = self.text_splitter.split_text(content)
                    
                    # 创建Document对象用于向量化
                    document = Document(
                        id=doc['id'],
                        filename=doc.get('title', ''),
                        file_path=doc.get('file_path', ''),
                        file_size=doc.get('file_size', 0),
                        content_type=doc.get('file_type', ''),
                        upload_time=doc.get('created_at', datetime.now()),
                        processed=True,
                        processing_status="completed"
                    )
                    
                    # 向量化
                    await self._vectorize_document_chunks(doc['id'], document, chunks)
                    
                    # 更新文档状态
                    self.db_manager.update_document(doc['id'], {
                        "vectorized": True,
                        "vectorization_status": "completed",
                        "vectorization_time": datetime.now()
                    })
                    
                    updated_count += 1
                    logger.info(f"成功向量化文档 {doc['id']}")
                    
                except Exception as e:
                    logger.error(f"向量化文档 {doc['id']} 失败: {str(e)}")
                    # 更新状态为失败
                    self.db_manager.update_document(doc['id'], {
                        "vectorization_status": "failed"
                    })
            
            logger.info(f"增量向量化完成，共处理 {updated_count} 个文档")
            return updated_count
            
        except Exception as e:
            logger.error(f"增量向量化更新失败: {str(e)}")
            raise
    
    def get_chunking_stats(self) -> Dict[str, Any]:
        """获取分块统计信息
        
        Returns:
            分块统计信息
        """
        try:
            stats = self.text_splitter.get_chunking_stats()
            return {
                "semantic_chunking_enabled": self.settings.enable_semantic_chunking,
                "chunking_stats": stats,
                "current_config": {
                    "chunk_size": self.text_splitter.chunk_size,
                    "chunk_overlap": self.text_splitter.chunk_overlap,
                    "semantic_threshold": getattr(self.settings, 'semantic_threshold', 0.75),
                    "max_semantic_chunk_size": getattr(self.settings, 'max_semantic_chunk_size', 2000),
                    "min_chunk_size": getattr(self.settings, 'min_chunk_size', 100)
                }
            }
        except Exception as e:
            logger.error(f"获取分块统计失败: {str(e)}")
            return {"error": str(e)}
    
    def reset_chunking_stats(self) -> bool:
        """重置分块统计
        
        Returns:
            重置是否成功
        """
        try:
            self.text_splitter.reset_stats()
            logger.info("分块统计已重置")
            return True
        except Exception as e:
            logger.error(f"重置分块统计失败: {str(e)}")
            return False
    
    def update_chunking_config(self, **kwargs) -> bool:
        """更新分块配置
        
        Args:
            **kwargs: 配置参数
            
        Returns:
            更新是否成功
        """
        try:
            self.text_splitter.update_config(**kwargs)
            logger.info(f"分块配置已更新: {kwargs}")
            return True
        except Exception as e:
            logger.error(f"更新分块配置失败: {str(e)}")
            return False