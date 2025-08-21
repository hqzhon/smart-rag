"""
文档处理器
"""

from typing import List, Dict, Any, Optional
import os
import json
import uuid
from redis import Redis
from rq import Queue
from .pdf_processor import PDFProcessor
from .enhanced_pdf_processor import EnhancedPDFProcessor
from .cleaners import TextCleaner
from .medical_terminology import MedicalTerminologyStandardizer
from .quality_filter import TextQualityFilter, ChunkMetadataEnhancer
from app.utils.logger import setup_logger
from app.metadata.tasks import generate_metadata_for_chunk
from datetime import datetime

logger = setup_logger(__name__)


class DocumentProcessor:
    """处理文档集合的类"""
    
    def __init__(self, input_dir: str, output_dir: str, vector_store=None, use_enhanced_parser: bool = True, 
                 enable_cleaning: bool = True, enable_terminology_standardization: bool = True,
                 enable_quality_filtering: bool = True, enable_async_metadata: bool = True,
                 redis_host: str = 'localhost', redis_port: int = 6379):
        """初始化文档处理器
        
        Args:
            input_dir: 输入目录，包含PDF文件
            output_dir: 输出目录，存储处理结果
            vector_store: VectorStore实例，用于存储文档块
            use_enhanced_parser: 是否使用增强的PDF解析器
            enable_cleaning: 是否启用文本清洗
            enable_terminology_standardization: 是否启用术语标准化
            enable_quality_filtering: 是否启用质量过滤
            enable_async_metadata: 是否启用异步元数据处理
            redis_host: Redis服务器地址
            redis_port: Redis服务器端口
        """
        self.input_dir = input_dir
        self.output_dir = output_dir
        self.vector_store = vector_store  # 确保能访问到VectorStore实例
        self.use_enhanced_parser = use_enhanced_parser
        self.enable_cleaning = enable_cleaning
        self.enable_terminology_standardization = enable_terminology_standardization
        self.enable_quality_filtering = enable_quality_filtering
        self.enable_async_metadata = enable_async_metadata
        
        os.makedirs(output_dir, exist_ok=True)
        
        # Initialize processors
        if enable_cleaning:
            self.text_cleaner = TextCleaner()
        if enable_terminology_standardization:
            self.terminology_standardizer = MedicalTerminologyStandardizer()
        if enable_quality_filtering:
            self.quality_filter = TextQualityFilter()
            self.metadata_enhancer = ChunkMetadataEnhancer()
            
        # Initialize RQ queue for async metadata processing
        if self.enable_async_metadata:
            try:
                redis_conn = Redis(host=redis_host, port=redis_port, decode_responses=True)
                self.metadata_queue = Queue('metadata_queue', connection=redis_conn)
                logger.info(f"RQ队列已初始化，连接到Redis {redis_host}:{redis_port}")
            except Exception as e:
                logger.error(f"初始化RQ队列失败: {e}")
                logger.warning("将禁用异步元数据处理")
                self.enable_async_metadata = False
        
    def process_single_document(self, file_path: str) -> Dict[str, Any]:
        """处理单个文档（支持PDF和TXT文件）
        
        Args:
            file_path: 文件路径
            
        Returns:
            处理结果字典，包含原始文本、清洗后文本、结构化信息等
        """
        try:
            # Step 1: 根据文件类型进行解析
            file_extension = os.path.splitext(file_path)[1].lower()
            structured_elements = []  # 初始化structured_elements变量
            
            if file_extension == '.txt':
                # 处理TXT文件
                with open(file_path, 'r', encoding='utf-8') as f:
                    raw_text = f.read()
                structured_text = raw_text
                metadata = {"file_type": "txt", "file_name": os.path.basename(file_path)}
                
            elif file_extension == '.pdf':
                # 处理PDF文件
                if self.use_enhanced_parser:
                    processor = EnhancedPDFProcessor(file_path)
                    result = processor.process()
                    
                    # Extract structured elements
                    structured_elements = result.get("structured_elements", [])
                    raw_text = result.get("text", "")
                    metadata = result.get("metadata", {})
                    
                    # Add structure markers
                    structured_text = self._add_structure_markers(structured_elements)
                    
                else:
                    # Fallback to original processor
                    processor = PDFProcessor(file_path)
                    result = processor.process()
                    raw_text = result.get("text", "")
                    structured_text = raw_text
                    metadata = {}
            else:
                raise ValueError(f"Unsupported file type: {file_extension}")
            
            # Step 2: Multi-stage text cleaning
            cleaned_text = raw_text
            if self.enable_cleaning:
                cleaned_text = self.text_cleaner.clean_comprehensive(raw_text)
                
                # Extract structured content if available
                if structured_elements:
                    # Convert structured elements to text for analysis
                    structured_text_for_analysis = "\n".join([
                        element.get("content", "") for element in structured_elements 
                        if element.get("content")
                    ])
                    if structured_text_for_analysis:
                        structured_content = self.text_cleaner.extract_structured_content(structured_text_for_analysis)
                        metadata.update(structured_content)
            
            # Step 3: Medical terminology standardization
            standardized_text = cleaned_text
            if self.enable_terminology_standardization:
                standardized_text = self.terminology_standardizer.standardize_text(cleaned_text)
                
                # Extract medical entities
                entities = self.terminology_standardizer.extract_medical_entities(standardized_text)
                metadata["medical_entities"] = entities
            
            # Step 4: Enhanced metadata
            enhanced_metadata = self._enhance_metadata(metadata, file_path)
            
            # Generate document ID for all processing paths
            document_id = str(uuid.uuid4())
            enhanced_metadata["document_id"] = document_id
            
            # Step 5: Quality filtering and metadata enhancement (if enabled)
            if self.enable_quality_filtering:
                # Split text into chunks for quality assessment
                text_chunks = self._split_into_chunks(standardized_text)
                
                # Filter chunks by quality
                filtered_chunks, chunk_metadata = self.quality_filter.filter_text_chunks(
                    text_chunks, 
                    [{"source": file_path, "chunk_index": i} for i in range(len(text_chunks))]
                )
                
                # Enhance metadata for each chunk
                enhanced_chunk_metadata = []
                for chunk, base_meta in zip(filtered_chunks, chunk_metadata):
                    enhanced_meta = self.metadata_enhancer.enhance_chunk_metadata(chunk, base_meta)
                    # Generate unique chunk ID for async processing
                    chunk_id = str(uuid.uuid4())
                    enhanced_meta["chunk_id"] = chunk_id
                    enhanced_chunk_metadata.append(enhanced_meta)
                
                # Update final result with filtered chunks
                enhanced_metadata["filtered_chunks"] = filtered_chunks
                enhanced_metadata["chunk_metadata"] = enhanced_chunk_metadata
                enhanced_metadata["quality_stats"] = {
                    "original_chunks": len(text_chunks),
                    "filtered_chunks": len(filtered_chunks),
                    "filter_ratio": len(filtered_chunks) / len(text_chunks) if text_chunks else 0
                }
                
                # Submit async metadata generation tasks with "store first, update later" strategy
                if self.enable_async_metadata:
                    
                    logger.info(f"准备为 {len(filtered_chunks)} 个文本块创建异步元数据生成任务...")
                    
                    # Implement "store first, update later" strategy
                    if self.vector_store:
                        for chunk_text, chunk_meta in zip(filtered_chunks, enhanced_chunk_metadata):
                            chunk_id = chunk_meta.get("chunk_id")
                            if chunk_id:
                                try:
                                    # Prepare initial document data (store first)
                                    initial_metadata = {
                                        "document_id": document_id,
                                        "chunk_index": chunk_meta.get("chunk_index", 0),
                                        "total_chunks": len(filtered_chunks),
                                        "created_at": datetime.now().isoformat(),
                                        "status": "processing",
                                        "has_metadata": False  # Mark that metadata is not yet generated
                                    }
                                    
                                    # Store to ChromaDB immediately (store first)
                                    self.vector_store.add_documents(
                                        texts=[chunk_text],
                                        metadatas=[initial_metadata],
                                        ids=[chunk_id]
                                    )
                                    logger.debug(f"已存储块 {chunk_id} 到ChromaDB")
                                    
                                    # Then submit async metadata generation task (update later)
                                    job = self.metadata_queue.enqueue(
                                        generate_metadata_for_chunk,
                                        chunk_id,
                                        chunk_text,
                                        document_id,
                                        job_timeout='10m',
                                        result_ttl=86400,
                                        failure_ttl=604800
                                    )
                                    logger.debug(f"任务已推送到队列: chunk_id={chunk_id}, job_id={job.id}")
                                except Exception as e:
                                    logger.error(f"存储块 {chunk_id} 到ChromaDB或推送任务失败: {e}")
                        
                        logger.info("所有文本块已存储到ChromaDB，元数据生成任务已成功推送到队列")
                    else:
                        logger.warning("VectorStore未初始化，跳过ChromaDB存储，仅推送异步任务")
                        # Fallback to original logic
                        for chunk_text, chunk_meta in zip(filtered_chunks, enhanced_chunk_metadata):
                            chunk_id = chunk_meta.get("chunk_id")
                            if chunk_id:
                                try:
                                    job = self.metadata_queue.enqueue(
                                        generate_metadata_for_chunk,
                                        chunk_id,
                                        chunk_text,
                                        document_id,
                                        job_timeout='10m',
                                        result_ttl=86400,
                                        failure_ttl=604800
                                    )
                                    logger.debug(f"任务已推送到队列: chunk_id={chunk_id}, job_id={job.id}")
                                except Exception as e:
                                    logger.error(f"推送任务到队列失败 chunk_id={chunk_id}: {e}")
                        
                        logger.info("所有元数据生成任务已成功推送到队列")
                else:
                    logger.info("异步元数据处理已禁用，跳过任务推送")
            else:
                # If quality filtering is disabled, create empty chunk metadata list
                enhanced_chunk_metadata = []
            
            # Prepare final result
            final_result = {
                "file_path": file_path,
                "document_id": document_id,
                "chunk_ids": [chunk_meta.get("chunk_id") for chunk_meta in enhanced_chunk_metadata if chunk_meta.get("chunk_id")],
                "raw_text": raw_text,
                "cleaned_text": cleaned_text,
                "standardized_text": standardized_text,
                "structured_text": structured_text,
                "metadata": enhanced_metadata,
                "processing_stats": {
                    "raw_length": len(raw_text),
                    "cleaned_length": len(cleaned_text),
                    "standardized_length": len(standardized_text),
                    "structure_elements": len(structured_elements) if 'structured_elements' in locals() else 0,
                    "total_chunks": len(enhanced_chunk_metadata)
                }
            }
            
            # Save processing results
            self._save_processing_results(final_result, file_path)
            
            logger.info(f"Successfully processed document: {os.path.basename(file_path)}")
            return final_result
            
        except Exception as e:
            import traceback
            logger.error(f"Error processing document {file_path}: {str(e)}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            raise
        
    def _add_structure_markers(self, structured_elements: List[Dict[str, Any]]) -> str:
        """为结构化元素添加标记
        
        Args:
            structured_elements: 结构化元素列表
            
        Returns:
            带有结构标记的文本
        """
        marked_text = []
        
        for element in structured_elements:
            element_type = element.get("type", "text")
            content = element.get("content", "")
            
            # Debug: Check if content is a list
            if isinstance(content, list):
                logger.warning(f"Found list content in element type {element_type}: {content}")
                text = " ".join(str(item) for item in content if item).strip()
            else:
                text = str(content).strip()
            
            if not text:
                continue
                
            # Add structure markers based on element type
            if element_type == "title":
                marked_text.append(f"<TITLE>{text}</TITLE>")
            elif element_type == "header":
                marked_text.append(f"<HEADER>{text}</HEADER>")
            elif element_type == "section":
                marked_text.append(f"<SECTION>{text}</SECTION>")
            elif element_type == "table":
                marked_text.append(f"<TABLE>{text}</TABLE>")
            elif element_type == "list":
                marked_text.append(f"<LIST>{text}</LIST>")
            elif element_type == "figure_caption":
                marked_text.append(f"<FIGURE_CAPTION>{text}</FIGURE_CAPTION>")
            elif element_type == "footer":
                marked_text.append(f"<FOOTER>{text}</FOOTER>")
            else:
                marked_text.append(text)
        
        return "\n\n".join(marked_text)
    
    def _enhance_metadata(self, metadata: Dict[str, Any], file_path: str) -> Dict[str, Any]:
        """增强文档元数据
        
        Args:
            metadata: 原始元数据
            file_path: 文件路径
            
        Returns:
            增强后的元数据
        """
        enhanced = metadata.copy()
        
        # Add file information
        enhanced.update({
            "file_name": os.path.basename(file_path),
            "file_size": os.path.getsize(file_path),
            "processing_timestamp": __import__('datetime').datetime.now().isoformat(),
            "processor_version": "2.0.0"
        })
        
        # Add document type classification
        file_name = os.path.basename(file_path).lower()
        if any(keyword in file_name for keyword in ["report", "报告"]):
            enhanced["document_type"] = "medical_report"
        elif any(keyword in file_name for keyword in ["guideline", "指南"]):
            enhanced["document_type"] = "clinical_guideline"
        elif any(keyword in file_name for keyword in ["paper", "论文"]):
            enhanced["document_type"] = "research_paper"
        else:
            enhanced["document_type"] = "general_medical"
        
        return enhanced
    
    def _save_processing_results(self, result: Dict[str, Any], file_path: str):
        """保存处理结果到文件
        
        Args:
            result: 处理结果
            file_path: 原始文件路径
        """
        filename = os.path.basename(file_path)
        base_name = os.path.splitext(filename)[0]
        
        # Save unified JSON output for validation tests
        unified_output = {
            "text": result["standardized_text"],  # Use the final processed text
            "metadata": result["metadata"],
            "enhanced_metadata": {
                "quality_statistics": result["metadata"].get("quality_stats", {}),
                "processing_stats": result["processing_stats"]
            },
            "raw_text": result["raw_text"],
            "cleaned_text": result["cleaned_text"],
            "structured_text": result["structured_text"]
        }
        
        # Save main JSON file (expected by validation tests)
        main_output_path = os.path.join(self.output_dir, f"{filename}.json")
        with open(main_output_path, 'w', encoding='utf-8') as f:
            json.dump(unified_output, f, ensure_ascii=False, indent=2)
        
        # Save different versions of text (for backward compatibility)
        text_outputs = {
            "raw": result["raw_text"],
            "cleaned": result["cleaned_text"],
            "standardized": result["standardized_text"],
            "structured": result["structured_text"]
        }
        
        for version, text in text_outputs.items():
            if text:  # Only save non-empty text
                output_path = os.path.join(self.output_dir, f"{base_name}_{version}.txt")
                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write(text)
        
        # Save metadata as JSON (for backward compatibility)
        metadata_path = os.path.join(self.output_dir, f"{base_name}_metadata.json")
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(result["metadata"], f, ensure_ascii=False, indent=2)
        
        # Save processing stats (for backward compatibility)
        stats_path = os.path.join(self.output_dir, f"{base_name}_stats.json")
        with open(stats_path, 'w', encoding='utf-8') as f:
            json.dump(result["processing_stats"], f, ensure_ascii=False, indent=2)
    
    def _split_into_chunks(self, text: str, chunk_size: int = 1000, overlap: int = 200) -> List[str]:
        """将文本分割成块
        
        Args:
            text: 输入文本
            chunk_size: 块大小（字符数）
            overlap: 重叠大小（字符数）
            
        Returns:
            文本块列表
        """
        if not text:
            return []
        
        chunks = []
        start = 0
        
        while start < len(text):
            end = start + chunk_size
            
            # If this is not the last chunk, try to find a good break point
            if end < len(text):
                # Look for sentence endings within the last 100 characters
                search_start = max(start + chunk_size - 100, start)
                sentence_endings = []
                
                for i in range(search_start, min(end + 50, len(text))):
                    if text[i] in '.!?。！？':
                        sentence_endings.append(i + 1)
                
                # Use the last sentence ending if found
                if sentence_endings:
                    end = sentence_endings[-1]
            
            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)
            
            # Move start position with overlap
            start = max(start + chunk_size - overlap, end)
            
            # Prevent infinite loop
            if start >= len(text):
                break
        
        return chunks
    
    def process_all_documents(self) -> List[Dict[str, Any]]:
        """处理目录中的所有PDF文档
            处理结果列表
        """
        results = []
        
        if not os.path.exists(self.input_dir):
            logger.warning(f"输入目录不存在: {self.input_dir}")
            return results
        
        # 遍历目录中的所有PDF文件
        pdf_files = [f for f in os.listdir(self.input_dir) if f.lower().endswith('.pdf')]
        
        if not pdf_files:
            logger.info(f"在目录 {self.input_dir} 中未找到PDF文件")
            return results
        
        logger.info(f"找到 {len(pdf_files)} 个PDF文件，开始处理...")
        
        for filename in pdf_files:
            file_path = os.path.join(self.input_dir, filename)
            try:
                result = self.process_single_document(file_path)
                results.append(result)
            except Exception as e:
                logger.error(f"跳过文件 {filename}: {str(e)}")
                continue
        
        logger.info(f"文档处理完成，成功处理 {len(results)} 个文件")
        return results