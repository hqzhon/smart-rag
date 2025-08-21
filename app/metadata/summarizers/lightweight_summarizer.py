"""轻量级摘要生成器 - 使用千问API"""

import asyncio
from typing import List, Optional, Dict, Any
import logging
from datetime import datetime

from ..clients.qianwen_client import get_metadata_qianwen_client
from ..models.metadata_models import DocumentSummary, SummaryMethod, QualityLevel
from app.utils.logger import setup_logger

logger = setup_logger(__name__)

class LightweightSummaryGenerator:
    """轻量级摘要生成器
    
    使用千问API生成文档摘要，支持：
    - 块级摘要生成
    - 批量处理
    - 质量控制
    - 错误重试
    """
    
    def __init__(
        self,
        max_summary_length: int = 200,
        language: str = "中文",
        batch_size: int = 5,
        retry_times: int = 3,
        retry_delay: float = 1.0
    ):
        """初始化摘要生成器
        
        Args:
            max_summary_length: 摘要最大长度
            language: 摘要语言
            batch_size: 批处理大小
            retry_times: 重试次数
            retry_delay: 重试延迟（秒）
        """
        self.max_summary_length = max_summary_length
        self.language = language
        self.batch_size = batch_size
        self.retry_times = retry_times
        self.retry_delay = retry_delay
        
        # 统计信息
        self.total_processed = 0
        self.success_count = 0
        self.error_count = 0
        
        logger.info(f"轻量级摘要生成器初始化完成 - 最大长度: {max_summary_length}, 语言: {language}")
    
    def _build_prompt_template(self, text: str, context: Optional[str] = None) -> str:
        """构建提示词模板
        
        Args:
            text: 待摘要的文本
            context: 上下文信息（可选）
            
        Returns:
            构建好的提示词
        """
        base_prompt = f"""请为以下文本生成一个简洁准确的摘要：

文本内容：
{text}

要求：
1. 摘要长度不超过{self.max_summary_length}字
2. 使用{self.language}
3. 保留核心信息和关键观点
4. 如果是医学文本，请保留重要的医学术语
5. 语言简洁明了，逻辑清晰
6. 直接输出摘要内容，不要添加额外说明"""
        
        if context:
            base_prompt += f"\n\n上下文信息：\n{context}"
        
        return base_prompt
    
    async def generate_summary(
        self,
        text: str,
        chunk_id: Optional[str] = None,
        context: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> DocumentSummary:
        """生成单个文档摘要
        
        Args:
            text: 待摘要的文本
            chunk_id: 文档块ID
            context: 上下文信息
            metadata: 额外的元数据
            
        Returns:
            文档摘要对象
        """
        start_time = datetime.now()
        self.total_processed += 1
        
        try:
            # 输入验证
            if not text or not text.strip():
                raise ValueError("输入文本不能为空")
            
            if len(text) < 10:
                logger.warning(f"文本过短 (长度: {len(text)})，直接返回原文")
                return DocumentSummary(
                    chunk_id=chunk_id or f"chunk_{self.total_processed}",
                    original_text=text,
                    summary=text,
                    summary_length=len(text),
                    method=SummaryMethod.QIANWEN_API,
                    processing_time=(datetime.now() - start_time).total_seconds(),
                    metadata=metadata or {}
                )
            
            # 获取千问客户端
            client = await get_metadata_qianwen_client()
            
            # 重试机制
            last_error = None
            for attempt in range(self.retry_times):
                try:
                    # 生成摘要
                    summary_text = await client.generate_summary(
                        text=text,
                        max_length=self.max_summary_length,
                        language=self.language
                    )
                    
                    if not summary_text or not summary_text.strip():
                        raise ValueError("API返回空摘要")
                    
                    # 创建摘要对象
                    summary = DocumentSummary(
                        chunk_id=chunk_id or f"chunk_{self.total_processed}",
                        content=summary_text.strip(),
                        method=SummaryMethod.QIANWEN_API,
                        confidence=0.8,
                        processing_time=(datetime.now() - start_time).total_seconds(),
                        source_length=len(text)
                    )
                    
                    self.success_count += 1
                    logger.debug(f"摘要生成成功 - 块ID: {chunk_id}, 原文长度: {len(text)}, 摘要长度: {len(summary_text)}")
                    return summary
                    
                except Exception as e:
                    last_error = e
                    if attempt < self.retry_times - 1:
                        logger.warning(f"摘要生成失败，第{attempt + 1}次重试: {str(e)}")
                        await asyncio.sleep(self.retry_delay * (attempt + 1))
                    else:
                        logger.error(f"摘要生成最终失败: {str(e)}")
            
            # 所有重试都失败，返回降级摘要
            self.error_count += 1
            fallback_summary = self._create_fallback_summary(text, chunk_id, start_time, last_error)
            return fallback_summary
            
        except Exception as e:
            self.error_count += 1
            logger.error(f"摘要生成异常: {str(e)}")
            return self._create_fallback_summary(text, chunk_id, start_time, e)
    
    def _create_fallback_summary(
        self,
        text: str,
        chunk_id: Optional[str],
        start_time: datetime,
        error: Exception
    ) -> DocumentSummary:
        """创建降级摘要
        
        Args:
            text: 原始文本
            chunk_id: 块ID
            start_time: 开始时间
            error: 错误信息
            
        Returns:
            降级摘要对象
        """
        # 简单的文本截取作为降级策略
        fallback_text = text[:self.max_summary_length] + "..." if len(text) > self.max_summary_length else text
        
        return DocumentSummary(
            chunk_id=chunk_id or f"chunk_{self.total_processed}",
            content=fallback_text,
            method=SummaryMethod.FALLBACK,
            confidence=0.3,
            processing_time=(datetime.now() - start_time).total_seconds(),
            source_length=len(text)
        )
    
    async def batch_generate_summaries(
        self,
        texts: List[str],
        chunk_ids: Optional[List[str]] = None,
        contexts: Optional[List[str]] = None,
        metadata_list: Optional[List[Dict[str, Any]]] = None
    ) -> List[DocumentSummary]:
        """批量生成摘要
        
        Args:
            texts: 文本列表
            chunk_ids: 块ID列表
            contexts: 上下文列表
            metadata_list: 元数据列表
            
        Returns:
            摘要列表
        """
        if not texts:
            return []
        
        # 参数对齐
        chunk_ids = chunk_ids or [None] * len(texts)
        contexts = contexts or [None] * len(texts)
        metadata_list = metadata_list or [None] * len(texts)
        
        summaries = []
        
        # 分批处理
        for i in range(0, len(texts), self.batch_size):
            batch_texts = texts[i:i + self.batch_size]
            batch_chunk_ids = chunk_ids[i:i + self.batch_size]
            batch_contexts = contexts[i:i + self.batch_size]
            batch_metadata = metadata_list[i:i + self.batch_size]
            
            # 并发处理当前批次
            batch_tasks = [
                self.generate_summary(
                    text=text,
                    chunk_id=chunk_id,
                    context=context,
                    metadata=metadata
                )
                for text, chunk_id, context, metadata in zip(
                    batch_texts, batch_chunk_ids, batch_contexts, batch_metadata
                )
            ]
            
            batch_summaries = await asyncio.gather(*batch_tasks, return_exceptions=True)
            
            # 处理异常结果
            for j, result in enumerate(batch_summaries):
                if isinstance(result, Exception):
                    logger.error(f"批次摘要生成异常 (索引 {i + j}): {str(result)}")
                    # 创建错误摘要
                    error_summary = self._create_fallback_summary(
                        batch_texts[j],
                        batch_chunk_ids[j],
                        datetime.now(),
                        result
                    )
                    summaries.append(error_summary)
                else:
                    summaries.append(result)
            
            # 批次间延迟
            if i + self.batch_size < len(texts):
                await asyncio.sleep(0.5)
        
        success_count = len([s for s in summaries if s.method != SummaryMethod.FALLBACK])
        logger.info(f"批量摘要生成完成: {success_count}/{len(texts)} 成功")
        
        return summaries
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            "total_processed": self.total_processed,
            "success_count": self.success_count,
            "error_count": self.error_count,
            "success_rate": self.success_count / max(self.total_processed, 1),
            "max_summary_length": self.max_summary_length,
            "language": self.language,
            "batch_size": self.batch_size
        }
    
    def reset_stats(self):
        """重置统计信息"""
        self.total_processed = 0
        self.success_count = 0
        self.error_count = 0
        logger.info("摘要生成器统计信息已重置")
    
    async def health_check(self) -> bool:
        """健康检查"""
        try:
            client = await get_metadata_qianwen_client()
            return await client.health_check()
        except Exception as e:
            logger.error(f"摘要生成器健康检查失败: {str(e)}")
            return False