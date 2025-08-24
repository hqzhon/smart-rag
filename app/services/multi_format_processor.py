"""多格式文档处理器

使用unstructured库处理多种文档格式，包括PDF、DOCX、PPTX、XLSX、TXT、MD等。
"""

import os
import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from pathlib import Path
import asyncio
from concurrent.futures import ThreadPoolExecutor

from unstructured.partition.auto import partition
from unstructured.partition.pdf import partition_pdf
from unstructured.partition.docx import partition_docx
from unstructured.partition.pptx import partition_pptx
from unstructured.partition.xlsx import partition_xlsx
from unstructured.partition.text import partition_text
from unstructured.partition.md import partition_md
from unstructured.documents.elements import Element

from app.core.config import settings
from app.models.document_models import Document, DocumentChunk


logger = logging.getLogger(__name__)


class ProcessingError(Exception):
    """文档处理异常"""
    pass


class MultiFormatProcessor:
    """多格式文档处理器"""
    
    def __init__(self):
        self.supported_formats = settings.supported_formats_list
        self.max_workers = settings.max_workers
        self.processing_timeout = settings.processing_timeout
        self.chunk_size = settings.chunk_size
        self.chunk_overlap = settings.chunk_overlap
        
        # Initialize thread pool for async processing
        self.executor = ThreadPoolExecutor(max_workers=self.max_workers)
        
        logger.info(f"MultiFormatProcessor initialized with formats: {self.supported_formats}")
    
    def get_supported_formats(self) -> List[str]:
        """获取支持的文档格式列表"""
        return self.supported_formats.copy()
    
    def get_format_info(self, file_format: str) -> Dict[str, Any]:
        """获取指定格式的详细信息"""
        format_info = {
            "pdf": {
                "name": "PDF Document",
                "extensions": [".pdf"],
                "description": "Portable Document Format",
                "supports_pages": True,
                "supports_tables": True,
                "supports_images": True
            },
            "docx": {
                "name": "Word Document",
                "extensions": [".docx"],
                "description": "Microsoft Word Document",
                "supports_pages": True,
                "supports_tables": True,
                "supports_images": True
            },
            "pptx": {
                "name": "PowerPoint Presentation",
                "extensions": [".pptx"],
                "description": "Microsoft PowerPoint Presentation",
                "supports_pages": True,
                "supports_tables": True,
                "supports_images": True
            },
            "xlsx": {
                "name": "Excel Spreadsheet",
                "extensions": [".xlsx"],
                "description": "Microsoft Excel Spreadsheet",
                "supports_pages": False,
                "supports_tables": True,
                "supports_images": False
            },
            "txt": {
                "name": "Text File",
                "extensions": [".txt"],
                "description": "Plain Text File",
                "supports_pages": False,
                "supports_tables": False,
                "supports_images": False
            },
            "md": {
                "name": "Markdown File",
                "extensions": [".md", ".markdown"],
                "description": "Markdown Document",
                "supports_pages": False,
                "supports_tables": True,
                "supports_images": False
            }
        }
        
        return format_info.get(file_format.lower(), {})
    
    def is_supported_format(self, file_path: str) -> bool:
        """检查文件格式是否支持"""
        file_extension = Path(file_path).suffix.lower()
        
        logger.info(f"Checking file format for: {file_path}")
        logger.info(f"File extension: {file_extension}")
        logger.info(f"Supported formats: {self.supported_formats}")
        
        for format_name in self.supported_formats:
            format_info = self.get_format_info(format_name)
            extensions = format_info.get("extensions", [])
            logger.info(f"Format {format_name}: extensions = {extensions}")
            if file_extension in extensions:
                logger.info(f"Match found! {file_extension} in {extensions}")
                return True
        
        logger.warning(f"No match found for extension: {file_extension}")
        return False
    
    def detect_file_format(self, file_path: str) -> str:
        """检测文件格式"""
        file_extension = Path(file_path).suffix.lower()
        
        format_mapping = {
            ".pdf": "pdf",
            ".docx": "docx",
            ".pptx": "pptx",
            ".xlsx": "xlsx",
            ".txt": "txt",
            ".md": "md",
            ".markdown": "md"
        }
        
        return format_mapping.get(file_extension, "unknown")
    
    async def process_document(self, file_path: str, document: Document) -> Tuple[List[DocumentChunk], Dict[str, Any]]:
        """异步处理文档"""
        try:
            logger.info(f"Starting document processing: {file_path}")
            
            # Run processing in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                self.executor,
                self._process_document_sync,
                file_path,
                document
            )
            
            logger.info(f"Document processing completed: {file_path}")
            return result
            
        except Exception as e:
            logger.error(f"Error processing document {file_path}: {str(e)}")
            raise ProcessingError(f"Failed to process document: {str(e)}")
    
    def _process_document_sync(self, file_path: str, document: Document) -> Tuple[List[DocumentChunk], Dict[str, Any]]:
        """同步处理文档（在线程池中运行）"""
        file_format = self.detect_file_format(file_path)
        
        if file_format == "unknown" or not self.is_supported_format(file_path):
            raise ProcessingError(f"Unsupported file format: {file_format}")
        
        # Process based on file format
        if file_format == "pdf":
            elements = self._process_pdf(file_path)
        elif file_format == "docx":
            elements = self._process_docx(file_path)
        elif file_format == "pptx":
            elements = self._process_pptx(file_path)
        elif file_format == "xlsx":
            elements = self._process_xlsx(file_path)
        elif file_format == "txt":
            elements = self._process_txt(file_path)
        elif file_format == "md":
            elements = self._process_md(file_path)
        else:
            raise ProcessingError(f"Processing not implemented for format: {file_format}")
        
        # Extract metadata
        metadata = self._extract_metadata(elements, file_format)
        
        # Create text chunks
        chunks = self._create_text_chunks(elements, document.id or "")
        
        return chunks, metadata
    
    def _process_pdf(self, file_path: str) -> List[Element]:
        """处理PDF文档"""
        try:
            elements = partition_pdf(
                filename=file_path,
                strategy="hi_res",  # Use high-resolution strategy for better accuracy
                infer_table_structure=True,
                extract_images_in_pdf=False,  # Set to True if you want to extract images
                include_page_breaks=True
            )
            return elements
        except Exception as e:
            logger.error(f"Error processing PDF {file_path}: {str(e)}")
            raise ProcessingError(f"Failed to process PDF: {str(e)}")
    
    def _process_docx(self, file_path: str) -> List[Element]:
        """处理DOCX文档"""
        try:
            elements = partition_docx(
                filename=file_path,
                infer_table_structure=True,
                include_page_breaks=True
            )
            return elements
        except Exception as e:
            logger.error(f"Error processing DOCX {file_path}: {str(e)}")
            raise ProcessingError(f"Failed to process DOCX: {str(e)}")
    
    def _process_pptx(self, file_path: str) -> List[Element]:
        """处理PPTX文档"""
        try:
            elements = partition_pptx(
                filename=file_path,
                infer_table_structure=True
            )
            return elements
        except Exception as e:
            logger.error(f"Error processing PPTX {file_path}: {str(e)}")
            raise ProcessingError(f"Failed to process PPTX: {str(e)}")
    
    def _process_xlsx(self, file_path: str) -> List[Element]:
        """处理XLSX文档"""
        try:
            elements = partition_xlsx(
                filename=file_path,
                infer_table_structure=True
            )
            return elements
        except Exception as e:
            logger.error(f"Error processing XLSX {file_path}: {str(e)}")
            raise ProcessingError(f"Failed to process XLSX: {str(e)}")
    
    def _process_txt(self, file_path: str) -> List[Element]:
        """处理TXT文档"""
        try:
            elements = partition_text(filename=file_path)
            return elements
        except Exception as e:
            logger.error(f"Error processing TXT {file_path}: {str(e)}")
            raise ProcessingError(f"Failed to process TXT: {str(e)}")
    
    def _process_md(self, file_path: str) -> List[Element]:
        """处理Markdown文档"""
        try:
            elements = partition_md(filename=file_path)
            return elements
        except Exception as e:
            logger.error(f"Error processing MD {file_path}: {str(e)}")
            raise ProcessingError(f"Failed to process MD: {str(e)}")
    
    def _extract_metadata(self, elements: List[Element], file_format: str) -> Dict[str, Any]:
        """从元素中提取元数据"""
        metadata = {
            "file_format": file_format,
            "processing_timestamp": datetime.now().isoformat(),
            "total_elements": len(elements),
            "element_types": [],
            "total_pages": 0,
            "total_sheets": 0,
            "total_slides": 0,
            "page_range": None
        }
        
        # Count element types
        element_type_counts = {}
        page_numbers = set()
        
        for element in elements:
            element_type = type(element).__name__
            element_type_counts[element_type] = element_type_counts.get(element_type, 0) + 1
            
            # Extract page information if available
            if hasattr(element, 'metadata') and element.metadata:
                # Convert metadata to dict if it's not already
                metadata_dict = element.metadata if isinstance(element.metadata, dict) else element.metadata.__dict__
                if 'page_number' in metadata_dict:
                    page_numbers.add(metadata_dict['page_number'])
                elif 'sheet_name' in metadata_dict:
                    metadata["total_sheets"] += 1
                elif 'slide_number' in metadata_dict:
                    page_numbers.add(metadata_dict['slide_number'])
        
        metadata["element_types"] = list(element_type_counts.keys())
        metadata["element_type_counts"] = element_type_counts
        
        if page_numbers:
            metadata["total_pages"] = len(page_numbers)
            metadata["page_range"] = f"{min(page_numbers)}-{max(page_numbers)}"
        
        # Format-specific metadata
        if file_format == "xlsx":
            sheet_names = set()
            for element in elements:
                if hasattr(element, 'metadata') and element.metadata:
                    metadata_dict = element.metadata if isinstance(element.metadata, dict) else element.metadata.__dict__
                    sheet_names.add(metadata_dict.get('sheet_name', 'Sheet1'))
            metadata["total_sheets"] = len(sheet_names)
        elif file_format == "pptx":
            metadata["total_slides"] = len(page_numbers) if page_numbers else 0
        
        return metadata
    
    def _create_text_chunks(self, elements: List[Element], document_id: str) -> List[DocumentChunk]:
        """从元素创建文本块"""
        chunks = []
        chunk_index = 0
        
        for element in elements:
            if not element.text or not element.text.strip():
                continue
            
            # Extract metadata from element
            element_metadata = {}
            if hasattr(element, 'metadata') and element.metadata:
                element_metadata = dict(element.metadata)
            
            # Determine chunk type based on element type
            element_type = type(element).__name__.lower()
            chunk_type = "text"
            if "table" in element_type:
                chunk_type = "table"
            elif "title" in element_type or "header" in element_type:
                chunk_type = "title"
            elif "list" in element_type:
                chunk_type = "list"
            
            # Extract page number
            page_number = None
            if 'page_number' in element_metadata:
                page_number = element_metadata['page_number']
            elif 'slide_number' in element_metadata:
                page_number = element_metadata['slide_number']
            
            # Create chunk
            chunk = DocumentChunk(
                document_id=document_id,
                chunk_index=chunk_index,
                content=element.text.strip(),
                chunk_type=chunk_type,
                page_number=page_number,
                metadata=element_metadata
            )
            
            chunks.append(chunk)
            chunk_index += 1
        
        logger.info(f"Created {len(chunks)} text chunks for document {document_id}")
        return chunks
    
    def get_mime_types_for_extension(self, file_extension: str) -> List[str]:
        """获取文件扩展名对应的MIME类型列表"""
        mime_type_mapping = {
            ".pdf": ["application/pdf"],
            ".docx": ["application/vnd.openxmlformats-officedocument.wordprocessingml.document"],
            ".pptx": ["application/vnd.openxmlformats-officedocument.presentationml.presentation"],
            ".xlsx": ["application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"],
            ".txt": ["text/plain"],
            ".md": ["text/markdown", "text/plain"],
            ".markdown": ["text/markdown", "text/plain"]
        }
        
        return mime_type_mapping.get(file_extension.lower(), [])
    
    async def process_document_async(self, file_path: str) -> Dict[str, Any]:
        """异步处理文档（为了兼容DocumentService的调用）"""
        try:
            logger.info(f"Starting async document processing: {file_path}")
            
            # Run processing in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                self.executor,
                self._process_document_for_service,
                file_path
            )
            
            logger.info(f"Async document processing completed: {file_path}")
            return result
            
        except Exception as e:
            logger.error(f"Error in async document processing {file_path}: {str(e)}")
            raise ProcessingError(f"Failed to process document: {str(e)}")
    
    def _process_document_for_service(self, file_path: str) -> Dict[str, Any]:
        """为DocumentService提供的同步处理方法"""
        file_format = self.detect_file_format(file_path)
        
        if file_format == "unknown" or not self.is_supported_format(file_path):
            raise ProcessingError(f"Unsupported file format: {file_format}")
        
        # Process based on file format
        if file_format == "pdf":
            elements = self._process_pdf(file_path)
        elif file_format == "docx":
            elements = self._process_docx(file_path)
        elif file_format == "pptx":
            elements = self._process_pptx(file_path)
        elif file_format == "xlsx":
            elements = self._process_xlsx(file_path)
        elif file_format == "txt":
            elements = self._process_txt(file_path)
        elif file_format == "md":
            elements = self._process_md(file_path)
        else:
            raise ProcessingError(f"Processing not implemented for format: {file_format}")
        
        # Extract text content
        text_content = "\n".join([element.text for element in elements if hasattr(element, 'text') and element.text])
        
        # Extract metadata
        metadata = self._extract_metadata(elements, file_format)
        
        # Return result in the format expected by DocumentService
        return {
            "text": text_content,
            "standardized_text": text_content,
            "cleaned_text": text_content,
            "raw_text": text_content,
            "metadata": metadata,
            "elements": elements,
            "format": file_format
        }
    
    def __del__(self):
        """清理资源"""
        if hasattr(self, 'executor'):
            self.executor.shutdown(wait=True)