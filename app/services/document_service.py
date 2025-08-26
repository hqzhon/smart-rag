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
        self.text_splitter = MedicalTextSplitter(
            enable_semantic=self.settings.enable_semantic_chunking
        )
        
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
        """处理文档，提取文本、分块并进行向量化
        
        Args:
            document: 文档对象
            
        Returns:
            处理结果
        """
        try:
            logger.info(f"开始处理文档: {document.filename}")
            start_time = datetime.now()
            
            # 更新处理状态
            document.processing_status = "processing"
            document.status = "processing"  # 更新整体状态为processing
            
            # 更新数据库中的状态
            self.db_manager.update_document(document.id, {'status': 'processing'})
            
            # 发布开始处理进度
            self._publish_progress(document.id, "processing", 30, "开始处理文档内容")
            
            # 使用MultiFormatProcessor处理文档
            try:
                result = await self.multi_format_processor.process_document_async(document.file_path)
                # 发布文档解析完成进度
                self._publish_progress(document.id, "parsed", 50, "文档内容解析完成")
            except ProcessingError as e:
                logger.error(f"多格式处理器处理失败: {str(e)}")
                # 回退到原始处理器（仅支持PDF）
                if document.file_path.lower().endswith('.pdf'):
                    logger.info("回退到原始PDF处理器")
                    result = await asyncio.get_event_loop().run_in_executor(
                        None, self.document_processor.process_single_document, document.file_path
                    )
                    # 发布文档解析完成进度
                    self._publish_progress(document.id, "parsed", 50, "文档内容解析完成")
                else:
                    raise e
            
            # 文本分块 - 转换为text_splitter期望的格式
            self._publish_progress(document.id, "chunking", 60, "开始文本分块")
            document_for_splitting = {
                "text": result.get("text", result.get("standardized_text", result.get("cleaned_text", result.get("raw_text", "")))),
                "filename": document.filename,
                "tables": result.get("tables", result.get("metadata", {}).get("tables", [])),
                "references": result.get("references", result.get("metadata", {}).get("references", []))
            }
            chunks = self.text_splitter.split_documents([document_for_splitting])
            self._publish_progress(document.id, "chunked", 70, f"文本分块完成，共{len(chunks)}个块")
            
            # 获取提取的标题
            document_title = result.get('title', document.filename)
            if not document_title or document_title.strip() == '':
                document_title = document.filename
            
            # 计算处理时间
            processing_time = (datetime.now() - start_time).total_seconds()
            
            # 获取文档内容
            content = result.get('text', result.get('standardized_text', result.get('cleaned_text', result.get('raw_text', ''))))
            logger.info(f"准备保存文档内容，长度: {len(content)}")
            
            # 使用数据库事务确保向量化和MySQL更新的原子性
            try:
                # 开始事务：先更新数据库，再进行向量化
                # 构建文档数据，包含多格式处理的元数据
                metadata = result.get('metadata', {})
                doc_data = {
                    'id': document.id,
                    'title': document_title,  # 使用提取的标题
                    'content': content,
                    'file_path': document.file_path,
                    'file_size': document.file_size,
                    'file_type': document.content_type,
                    'file_format': metadata.get('file_format', Path(document.filename).suffix.lower()),
                    'original_filename': document.filename,
                    'total_pages': metadata.get('total_pages', 0),
                    'total_sheets': metadata.get('total_sheets', 0),
                    'total_slides': metadata.get('total_slides', 0),
                    'element_types': metadata.get('element_types', []),
                    'processing_start_time': start_time,
                    'processing_end_time': datetime.now(),
                    'metadata': {
                        'original_filename': document.filename,
                        'chunks_count': len(chunks),
                        'processing_time': processing_time,
                        'tables_count': len(result.get('tables', [])),
                        'references_count': len(result.get('references', [])),
                        'images_count': len(result.get('images', [])),
                        'processing_status': 'completed',
                        'vectorized': False,
                        'vectorization_status': 'processing',
                        'file_format': metadata.get('file_format', Path(document.filename).suffix.lower()),
                        'total_pages': metadata.get('total_pages', 0),
                        'total_sheets': metadata.get('total_sheets', 0),
                        'total_slides': metadata.get('total_slides', 0),
                        'element_types': metadata.get('element_types', [])
                    }
                }
                
                # 更新数据库中的文档信息（包含处理后的内容）
                doc_data['status'] = 'processing'  # 设置状态为processing
                self.db_manager.save_document(doc_data)
                logger.info(f"文档内容已更新到数据库: {document.id}")
                self._publish_progress(document.id, "saved_content", 80, "文档内容已保存到数据库")
                
                # 进行向量化处理
                self._publish_progress(document.id, "vectorizing", 85, "开始向量化处理")
                await self._vectorize_document_chunks(document.id, document, chunks, document_title)
                logger.info(f"文档向量化完成: {document.id}")
                self._publish_progress(document.id, "vectorized", 95, "向量化处理完成")
                
                # 向量化成功后，更新向量化状态
                vectorization_update = {
                    'vectorized': True,
                    'vectorization_status': 'completed',
                    'vectorization_time': datetime.now()
                }
                
                # 更新元数据中的向量化状态
                doc_data['metadata'].update({
                    'vectorized': True,
                    'vectorization_status': 'completed'
                })
                
                self.db_manager.update_document(document.id, {
                    'vectorized': True,
                    'vectorization_status': 'completed',
                    'status': 'chat_ready',  # 向量化完成后设置为chat_ready状态
                    'metadata': doc_data['metadata']
                })
                
                logger.info(f"文档处理和向量化事务完成: {document.id}")
                
            except Exception as transaction_error:
                logger.error(f"文档处理事务失败: {str(transaction_error)}")
                
                # 发布错误进度
                self._publish_progress(document.id, "error", 0, f"处理失败: {str(transaction_error)}")
                
                # 回滚：更新数据库状态为失败
                try:
                    self.db_manager.update_document(document.id, {
                        'vectorized': False,
                        'vectorization_status': 'failed',
                        'status': 'failed',  # 设置整体状态为failed
                        'metadata': {
                            'processing_status': 'failed',
                            'error_message': str(transaction_error),
                            'vectorized': False,
                            'vectorization_status': 'failed'
                        }
                    })
                    logger.info(f"文档状态已回滚为失败: {document.id}")
                except Exception as rollback_error:
                    logger.error(f"状态回滚失败: {str(rollback_error)}")
                
                # 重新抛出异常
                raise transaction_error
            
            # 更新文档状态
            document.processed = True
            document.processing_status = "completed"
            document.status = "chat_ready"  # 设置最终状态为chat_ready
            
            # 发布完成进度
            self._publish_progress(document.id, "chat_ready", 100, f"文档处理完成，耗时{processing_time:.1f}秒")
            
            # 创建处理结果
            processing_result = ProcessingResult(
                document_id=document.id,
                success=True,
                total_chunks=len(chunks),
                processing_time=processing_time,
                extracted_text_length=len(content),
                tables_count=len(result.get("tables", [])),
                references_count=len(result.get("references", [])),
                images_count=len(result.get("images", []))
            )
            
            logger.info(f"文档处理和向量化完成: {document.filename}, 耗时: {processing_time:.2f}秒")
            return processing_result
            
        except Exception as e:
            logger.error(f"文档处理失败: {str(e)}")
            document.processing_status = "failed"
            document.error_message = str(e)
            
            # 更新数据库中的状态为失败
            try:
                self.db_manager.update_document(document.id, {
                    'processed': False,
                    'processing_status': 'failed',
                    'status': 'failed',  # 设置整体状态为failed
                    'metadata': {
                        'processing_status': 'failed',
                        'error_message': str(e),
                        'vectorized': False,
                        'vectorization_status': 'failed'
                    }
                })
            except Exception as db_error:
                logger.error(f"更新文档失败状态时出错: {str(db_error)}")
            
            # 发布处理失败进度
            self._publish_progress(document.id, "failed", 0, f"文档处理失败: {str(e)}")
            
            return ProcessingResult(
                document_id=document.id,
                success=False,
                total_chunks=0,
                processing_time=0,
                extracted_text_length=0,
                error_message=str(e)
            )
    
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
            
            # 2. 删除向量存储中的数据（先删除向量数据，因为这个操作相对安全）
            vector_store = VectorStore()
            vector_deleted = await vector_store.delete_document(document_id)
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
    
    async def _vectorize_document_chunks(self, document_id: str, document: Document, text_chunks: list, document_title: str = None):
        """对文档块进行向量化处理
        
        Args:
            document_id: 文档ID
            document: 文档信息
            text_chunks: 文本块列表
            document_title: 文档标题（可选）
        """
        try:
            from app.storage.vector_store import VectorStore
            from app.embeddings.embeddings import get_embeddings
            
            # 初始化向量存储
            embedding_model = get_embeddings()
            vector_store = VectorStore(embedding_model)
            
            # 使用传入的标题或文档文件名
            title = document_title or document.filename
            
            # 准备向量化数据
            formatted_documents = []
            for i, chunk in enumerate(text_chunks):
                # 处理不同格式的chunk数据
                if isinstance(chunk, dict):
                    # text_splitter返回的字典格式
                    content = chunk.get('content', str(chunk))
                    chunk_metadata = chunk.get('metadata', {})
                elif hasattr(chunk, 'page_content'):
                    # LangChain Document格式
                    content = chunk.page_content
                    chunk_metadata = getattr(chunk, 'metadata', {})
                else:
                    # 字符串格式
                    content = str(chunk)
                    chunk_metadata = {}
                
                formatted_doc = {
                    "content": content,
                    "metadata": {
                        "document_id": document_id,
                        "file_name": document.filename,
                        "file_type": document.content_type,
                        "title": title,  # 添加标题到元数据
                        "source": title,  # 添加源文档名到元数据
                        "chunk_index": i,
                        "chunk_id": f"{document_id}_{i}",
                        "created_at": document.upload_time.isoformat() if document.upload_time else None,
                        # 合并原有的chunk元数据
                        **chunk_metadata
                    }
                }
                formatted_documents.append(formatted_doc)
            
            # 添加到向量存储
            await vector_store.add_documents(formatted_documents)
            
            logger.info(f"文档 {document_id} 的 {len(text_chunks)} 个文本块已成功向量化")
            
        except Exception as e:
            logger.error(f"向量化文档块时出错: {str(e)}")
            raise
    
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