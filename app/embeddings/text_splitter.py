"""医疗文本分块器"""

import asyncio
from typing import List, Dict, Any, Optional
from app.utils.logger import setup_logger
from app.core.config import get_settings
from .semantic.hybrid_splitter import HybridTextSplitter, ChunkingConfig
from .semantic.similarity_calculator import SemanticSimilarityCalculator

logger = setup_logger(__name__)
settings = get_settings()


class MedicalTextSplitter:
    """针对医疗文本优化的分块器，支持智能语义分块"""
    
    def __init__(
        self, 
        chunk_size: Optional[int] = None, 
        chunk_overlap: Optional[int] = None,
        enable_semantic: Optional[bool] = None
    ):
        """初始化分块器
        
        Args:
            chunk_size: 块大小，默认从配置读取
            chunk_overlap: 块重叠大小，默认从配置读取
            enable_semantic: 是否启用语义分块，默认从配置读取
        """
        # 从配置获取默认值
        self.chunk_size = chunk_size or settings.chunk_size
        self.chunk_overlap = chunk_overlap or settings.chunk_overlap
        self.enable_semantic = enable_semantic if enable_semantic is not None else settings.enable_semantic_chunking
        
        # 传统分隔符（保持向后兼容）
        self.separators = [
            "\n##SECTION_START_",
            "\n\n", 
            "。\n", 
            ".\n\n",
            ".\n",
            "。\n",
            "、\n", 
            "：\n", ":\n\n",
            "，\n", ",\n\n",
            " ", "\t"
        ]
        
        # 初始化智能分块器
        if self.enable_semantic:
            self._init_semantic_splitter()
        else:
            self.hybrid_splitter = None
        
        logger.info(
            f"医疗文本分块器初始化完成 - 块大小: {self.chunk_size}, 重叠: {self.chunk_overlap}, "
            f"语义分块: {self.enable_semantic}"
        )
    
    def _init_semantic_splitter(self):
        """初始化语义分块器"""
        try:
            # 创建分块配置
            config = ChunkingConfig(
                chunk_size=self.chunk_size,
                chunk_overlap=self.chunk_overlap,
                separators=settings.chunking_separators_list,
                semantic_threshold=settings.semantic_threshold,
                enable_semantic_fallback=True,
                max_semantic_chunk_size=settings.max_semantic_chunk_size,
                min_chunk_size=settings.min_chunk_size,
                batch_size=settings.chunking_batch_size,
                cache_enabled=settings.embedding_cache_enabled,
                cache_ttl=settings.embedding_cache_ttl
            )
            
            # 创建嵌入模型实例
            from .embeddings import QianwenEmbeddings
            embeddings_model = QianwenEmbeddings()
            
            # 创建语义相似度计算器
            similarity_calculator = SemanticSimilarityCalculator(embeddings_model=embeddings_model)
            
            # 创建混合分块器
            self.hybrid_splitter = HybridTextSplitter(
                config=config,
                similarity_calculator=similarity_calculator
            )
            
            logger.info("语义分块器初始化成功")
            
        except Exception as e:
            logger.error(f"语义分块器初始化失败: {e}")
            logger.warning("将使用传统分块方式")
            self.hybrid_splitter = None
            self.enable_semantic = False
    
    def split_text(self, text: str) -> List[str]:
        """分割文本
        
        Args:
            text: 输入文本
            
        Returns:
            分块后的文本列表
        """
        if not text or not text.strip():
            return []
        
        # 使用智能分块器（如果可用）
        if self.enable_semantic and self.hybrid_splitter:
            try:
                # 检查是否已有运行中的事件循环
                try:
                    loop = asyncio.get_running_loop()
                    # 如果有运行中的循环，使用同步方法
                    logger.warning("检测到运行中的事件循环，使用同步分块方法")
                    return self._traditional_split(text)
                except RuntimeError:
                    # 没有运行中的循环，可以安全使用asyncio.run
                    chunks = asyncio.run(self.hybrid_splitter.split_text(text))
                    logger.debug(f"智能分块完成，生成 {len(chunks)} 个块")
                    return chunks
            except Exception as e:
                logger.error(f"智能分块失败，回退到传统分块: {e}")
                # 继续使用传统分块方法
        
        # 传统分块方法（向后兼容）
        return self._traditional_split(text)
    
    def _traditional_split(self, text: str) -> List[str]:
        """传统分块方法
        
        Args:
            text: 输入文本
            
        Returns:
            分块后的文本列表
        """
        if len(text) <= self.chunk_size:
            return [text]
        
        chunks = []
        current_chunk = ""
        
        # 按分隔符递归分割
        splits = self._split_text_with_separators(text, self.separators)
        
        for split in splits:
            if len(current_chunk) + len(split) <= self.chunk_size:
                current_chunk += split
            else:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                    # 处理重叠
                    if self.chunk_overlap > 0 and len(current_chunk) > self.chunk_overlap:
                        overlap_text = current_chunk[-self.chunk_overlap:]
                        current_chunk = overlap_text + split
                    else:
                        current_chunk = split
                else:
                    current_chunk = split
        
        if current_chunk:
            chunks.append(current_chunk.strip())
        
        # 过滤空块
        chunks = [chunk for chunk in chunks if chunk.strip()]
        
        logger.info(f"文本分块完成，原文本长度: {len(text)}, 分块数量: {len(chunks)}")
        return chunks
    
    def _split_text_with_separators(self, text: str, separators: List[str]) -> List[str]:
        """使用分隔符递归分割文本"""
        if not separators:
            return [text]
        
        separator = separators[0]
        remaining_separators = separators[1:]
        
        if separator not in text:
            return self._split_text_with_separators(text, remaining_separators)
        
        splits = text.split(separator)
        result = []
        
        for i, split in enumerate(splits):
            if i > 0:
                result.append(separator)
            
            if len(split) > self.chunk_size:
                result.extend(self._split_text_with_separators(split, remaining_separators))
            else:
                result.append(split)
        
        return result
    
    def split_documents(self, documents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """将文档分块
        
        Args:
            documents: 文档列表
            
        Returns:
            分块后的文档列表
        """
        if not documents:
            return []

        # Debug: 检查传入的documents结构
        logger.debug(f"split_documents received {len(documents)} documents")
        for i, doc in enumerate(documents):
            logger.debug(f"Document {i}: type={type(doc)}, keys={list(doc.keys()) if isinstance(doc, dict) else 'not a dict'}")
            if isinstance(doc, dict) and "text" in doc:
                text_value = doc["text"]
                logger.debug(f"Document {i} text field: type={type(text_value)}, length={len(text_value) if isinstance(text_value, (str, list)) else 'unknown'}")

        # 使用智能分块器（如果可用）
        if self.enable_semantic and self.hybrid_splitter:
            try:
                # 检查是否已有运行中的事件循环
                try:
                    loop = asyncio.get_running_loop()
                    # 如果有运行中的循环，使用同步方法
                    logger.warning("检测到运行中的事件循环，使用同步文档分块方法")
                    return self._traditional_split_documents(documents)
                except RuntimeError:
                    # 没有运行中的循环，可以安全使用asyncio.run
                    # 提取文档文本内容供hybrid_splitter使用
                    # 确保text字段是字符串
                    document_texts = []
                    for doc in documents:
                        if not isinstance(doc, dict):
                            raise ValueError(f"Expected dict, got {type(doc)}: {doc}")
                        text_value = doc["text"]
                        if isinstance(text_value, list):
                            # 如果text是列表，将其转换为字符串
                            text_value = "\n".join(str(item) for item in text_value)
                            logger.warning(f"Converted list text to string for document {doc.get('filename', 'unknown')}")
                        elif not isinstance(text_value, str):
                            text_value = str(text_value)
                            logger.warning(f"Converted {type(text_value)} text to string for document {doc.get('filename', 'unknown')}")
                        document_texts.append(text_value)
                    chunk_lists = asyncio.run(self.hybrid_splitter.split_documents(document_texts))
                    
                    # 将分块结果转换为标准格式
                    chunks = []
                    for doc_idx, (doc, doc_chunks) in enumerate(zip(documents, chunk_lists)):
                        for chunk_idx, chunk_text in enumerate(doc_chunks):
                            chunks.append({
                                "content": chunk_text,
                                "metadata": {
                                    "source": doc["filename"],
                                    "chunk_id": chunk_idx,
                                    "chunk_type": "text",
                                    "language": self._detect_language(chunk_text)
                                }
                            })
                    
                    logger.debug(f"智能文档分块完成，生成 {len(chunks)} 个块")
                    return chunks
            except Exception as e:
                logger.error(f"智能文档分块失败，回退到传统分块: {e}")
                # 继续使用传统分块方法
        
        # 传统文档分块方法
        return self._traditional_split_documents(documents)
    
    def _traditional_split_documents(self, documents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """传统文档分块方法
        
        Args:
            documents: 文档列表
            
        Returns:
            分块后的文档列表
        """
        chunks = []
        
        for doc in documents:
            # 类型检查和错误处理
            if not isinstance(doc, dict):
                logger.error(f"传统分块方法收到非字典类型数据: {type(doc)}, 内容: {doc}")
                raise ValueError(f"Expected dict, got {type(doc)}: {doc}")
            
            # 确保text字段存在且为字符串
            if "text" not in doc:
                logger.error(f"文档缺少text字段: {doc}")
                continue
                
            text_value = doc["text"]
            if isinstance(text_value, list):
                # 如果text是列表，将其转换为字符串
                text_value = "\n".join(str(item) for item in text_value)
                logger.warning(f"传统分块中将列表text转换为字符串，文档: {doc.get('filename', 'unknown')}")
            elif not isinstance(text_value, str):
                text_value = str(text_value)
                logger.warning(f"传统分块中将{type(text_value)}类型text转换为字符串，文档: {doc.get('filename', 'unknown')}")
            
            # 处理主文本
            text_chunks = self._traditional_split(text_value)
            
            for i, chunk in enumerate(text_chunks):
                chunks.append({
                    "content": chunk,
                    "metadata": {
                        "source": doc["filename"],
                        "chunk_id": i,
                        "chunk_type": "text",
                        "language": self._detect_language(chunk)
                    }
                })
            
            # 处理表格 - 支持不同的数据格式
            tables = doc.get("tables", [])
            if tables:
                for i, table in enumerate(tables):
                    if isinstance(table, dict):
                        # 如果是字典格式，尝试提取文本内容
                        table_content = table.get("text_description") or table.get("content") or str(table)
                        chunks.append({
                            "content": table_content,
                            "metadata": {
                                "source": doc["filename"],
                                "chunk_type": "table",
                                "page": table.get("page", table.get("page_number", "unknown")),
                                "table_index": table.get("table_index", i),
                                "language": self._detect_language(table_content)
                            }
                        })
                    elif isinstance(table, str):
                        # 如果是字符串格式，直接使用
                        chunks.append({
                            "content": table,
                            "metadata": {
                                "source": doc["filename"],
                                "chunk_type": "table",
                                "table_index": i,
                                "language": self._detect_language(table)
                            }
                        })
                    else:
                        logger.warning(f"Unexpected table format: {type(table)}, skipping")
            
            # 处理参考文献 - 支持不同的数据格式
            references = doc.get("references", [])
            if references:
                for i, ref in enumerate(references):
                    if isinstance(ref, dict):
                        # 如果是字典格式，尝试提取文本内容
                        ref_content = ref.get("reference_text") or ref.get("content") or str(ref)
                        chunks.append({
                            "content": ref_content,
                            "metadata": {
                                "source": doc["filename"],
                                "chunk_type": "reference",
                                "reference_id": ref.get("reference_id", i),
                                "language": self._detect_language(ref_content)
                            }
                        })
                    elif isinstance(ref, str):
                        # 如果是字符串格式，直接使用
                        chunks.append({
                            "content": ref,
                            "metadata": {
                                "source": doc["filename"],
                                "chunk_type": "reference",
                                "reference_id": i,
                                "language": self._detect_language(ref)
                            }
                        })
                    else:
                        logger.warning(f"Unexpected reference format: {type(ref)}, skipping")
        
        logger.info(f"文档分块完成，总块数: {len(chunks)}")
        return chunks
    
    def _detect_language(self, text: str) -> str:
        """检测文本语言
        
        Args:
            text: 输入文本
            
        Returns:
            语言代码: 'zh', 'en', 或 'mixed'
        """
        if not text:
            return "unknown"
        
        # 简单检测，基于中文字符比例
        chinese_chars = sum(1 for char in text if '\u4e00' <= char <= '\u9fff')
        total_chars = len(text.strip())
        
        if total_chars == 0:
            return "unknown"
        
        chinese_ratio = chinese_chars / total_chars
        
        if chinese_ratio > 0.7:
            return "zh"
        elif chinese_ratio < 0.1:
            return "en"
        else:
            return "mixed"
    
    def get_chunking_stats(self) -> Dict[str, Any]:
        """获取分块统计信息
        
        Returns:
            分块统计信息
        """
        stats = {
            "chunk_size": self.chunk_size,
            "chunk_overlap": self.chunk_overlap,
            "enable_semantic": self.enable_semantic,
            "separators_count": len(self.separators)
        }
        
        # 如果启用了智能分块，获取详细统计
        if self.enable_semantic and self.hybrid_splitter:
            try:
                semantic_stats = self.hybrid_splitter.get_stats()
                stats.update({
                    "semantic_stats": semantic_stats,
                    "cache_enabled": self.hybrid_splitter.config.cache_enabled
                })
            except Exception as e:
                logger.warning(f"获取语义分块统计失败: {e}")
        
        return stats
    
    def reset_stats(self):
        """重置统计信息"""
        if self.enable_semantic and self.hybrid_splitter:
            try:
                self.hybrid_splitter.reset_stats()
                logger.info("语义分块统计信息已重置")
            except Exception as e:
                logger.warning(f"重置语义分块统计失败: {e}")
    
    def update_config(self, **kwargs):
        """动态更新配置
        
        Args:
            **kwargs: 配置参数
        """
        updated = False
        
        if "chunk_size" in kwargs:
            self.chunk_size = kwargs["chunk_size"]
            updated = True
        
        if "chunk_overlap" in kwargs:
            self.chunk_overlap = kwargs["chunk_overlap"]
            updated = True
        
        if "enable_semantic" in kwargs:
            new_enable = kwargs["enable_semantic"]
            if new_enable != self.enable_semantic:
                self.enable_semantic = new_enable
                if new_enable and not self.hybrid_splitter:
                    self._init_semantic_splitter()
                updated = True
        
        if updated:
            logger.info(f"分块器配置已更新: chunk_size={self.chunk_size}, "
                       f"chunk_overlap={self.chunk_overlap}, enable_semantic={self.enable_semantic}")
        
        # 更新智能分块器配置
        if self.enable_semantic and self.hybrid_splitter and updated:
            try:
                # 重新初始化以应用新配置
                self._init_semantic_splitter()
            except Exception as e:
                logger.error(f"更新智能分块器配置失败: {e}")