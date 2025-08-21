"""质量评估器"""

import asyncio
from typing import List, Dict, Optional, Any, Tuple
import logging
import re
from datetime import datetime
import math
from collections import Counter
import jieba
from textstat import flesch_reading_ease, flesch_kincaid_grade

from ..models.metadata_models import (
    SummaryQuality, KeywordQuality, QualityLevel,
    SummaryMethod, KeywordMethod, MedicalCategory
)
from app.utils.logger import setup_logger

logger = setup_logger(__name__)

class QualityEvaluator:
    """质量评估器
    
    功能：
    - 摘要质量评估
    - 关键词质量评估
    - 多维度评分
    - 医学文档特化评估
    """
    
    def __init__(
        self,
        min_summary_length: int = 20,
        max_summary_length: int = 500,
        min_keyword_count: int = 3,
        max_keyword_count: int = 15,
        medical_term_bonus: float = 0.1,
        enable_readability_check: bool = True
    ):
        """初始化质量评估器
        
        Args:
            min_summary_length: 最小摘要长度
            max_summary_length: 最大摘要长度
            min_keyword_count: 最小关键词数量
            max_keyword_count: 最大关键词数量
            medical_term_bonus: 医学术语加分
            enable_readability_check: 是否启用可读性检查
        """
        self.min_summary_length = min_summary_length
        self.max_summary_length = max_summary_length
        self.min_keyword_count = min_keyword_count
        self.max_keyword_count = max_keyword_count
        self.medical_term_bonus = medical_term_bonus
        self.enable_readability_check = enable_readability_check
        
        # 医学术语词典（简化版）
        self.medical_terms = self._load_medical_terms()
        
        # 停用词
        self.stop_words = self._load_stop_words()
        
        # 统计信息
        self.total_summary_evaluations = 0
        self.total_keyword_evaluations = 0
        self.average_summary_score = 0.0
        self.average_keyword_score = 0.0
        
        logger.info("质量评估器初始化完成")
    
    def _load_medical_terms(self) -> set:
        """加载医学术语"""
        return {
            # 基础医学术语
            "症状", "诊断", "治疗", "药物", "手术", "检查", "化验", "病理",
            "临床", "病史", "体征", "疾病", "综合征", "并发症", "预后", "康复",
            
            # 解剖学术语
            "心脏", "肺部", "肝脏", "肾脏", "大脑", "血管", "神经", "肌肉",
            "骨骼", "关节", "皮肤", "眼部", "耳鼻喉", "消化道", "呼吸道",
            
            # 常见疾病
            "高血压", "糖尿病", "冠心病", "脑梗塞", "肺炎", "肝炎", "肾炎",
            "胃炎", "肠炎", "关节炎", "骨折", "肿瘤", "癌症", "白血病",
            
            # 检查项目
            "血常规", "尿常规", "肝功能", "肾功能", "心电图", "胸片", "CT",
            "MRI", "B超", "内镜", "病理检查", "基因检测", "免疫检查",
            
            # 药物分类
            "抗生素", "激素", "降压药", "降糖药", "止痛药", "抗炎药",
            "抗凝药", "利尿剂", "镇静剂", "维生素", "中药", "西药"
        }
    
    def _load_stop_words(self) -> set:
        """加载停用词"""
        return {
            "的", "了", "在", "是", "我", "有", "和", "就", "不", "人",
            "都", "一", "一个", "上", "也", "很", "到", "说", "要", "去",
            "你", "会", "着", "没有", "看", "好", "自己", "这", "那", "里",
            "患者", "病人", "例", "岁", "男性", "女性", "主诉", "现病史"
        }
    
    def _calculate_text_similarity(self, text1: str, text2: str) -> float:
        """计算文本相似度（简化版Jaccard相似度）
        
        Args:
            text1: 文本1
            text2: 文本2
            
        Returns:
            相似度分数 (0-1)
        """
        try:
            # 分词
            words1 = set(jieba.cut(text1.lower()))
            words2 = set(jieba.cut(text2.lower()))
            
            # 去除停用词
            words1 = words1 - self.stop_words
            words2 = words2 - self.stop_words
            
            # 计算Jaccard相似度
            intersection = len(words1 & words2)
            union = len(words1 | words2)
            
            if union == 0:
                return 0.0
            
            return intersection / union
            
        except Exception as e:
            logger.warning(f"文本相似度计算失败: {str(e)}")
            return 0.0
    
    def _calculate_compression_ratio(self, original_text: str, summary: str) -> float:
        """计算压缩比
        
        Args:
            original_text: 原始文本
            summary: 摘要文本
            
        Returns:
            压缩比 (0-1)
        """
        original_length = len(original_text)
        summary_length = len(summary)
        
        if original_length == 0:
            return 0.0
        
        return summary_length / original_length
    
    def _calculate_information_density(self, text: str) -> float:
        """计算信息密度
        
        Args:
            text: 文本
            
        Returns:
            信息密度分数 (0-1)
        """
        try:
            # 分词
            words = list(jieba.cut(text))
            
            if not words:
                return 0.0
            
            # 去除停用词
            content_words = [w for w in words if w not in self.stop_words and len(w) > 1]
            
            # 计算词汇多样性
            unique_words = len(set(content_words))
            total_words = len(content_words)
            
            if total_words == 0:
                return 0.0
            
            # 词汇多样性比率
            diversity_ratio = unique_words / total_words
            
            # 医学术语密度
            medical_word_count = sum(1 for word in content_words if word in self.medical_terms)
            medical_density = medical_word_count / total_words if total_words > 0 else 0
            
            # 综合信息密度
            info_density = (diversity_ratio * 0.7) + (medical_density * 0.3)
            
            return min(info_density, 1.0)
            
        except Exception as e:
            logger.warning(f"信息密度计算失败: {str(e)}")
            return 0.0
    
    def _calculate_readability_score(self, text: str) -> float:
        """计算可读性分数
        
        Args:
            text: 文本
            
        Returns:
            可读性分数 (0-1)
        """
        if not self.enable_readability_check:
            return 0.8  # 默认分数
        
        try:
            # 对于中文文本，使用简化的可读性评估
            sentences = re.split(r'[。！？；]', text)
            sentences = [s.strip() for s in sentences if s.strip()]
            
            if not sentences:
                return 0.0
            
            # 平均句长
            avg_sentence_length = sum(len(s) for s in sentences) / len(sentences)
            
            # 理想句长范围：15-30字符
            if 15 <= avg_sentence_length <= 30:
                length_score = 1.0
            elif avg_sentence_length < 15:
                length_score = avg_sentence_length / 15
            else:
                length_score = max(0.3, 30 / avg_sentence_length)
            
            # 句子数量合理性
            sentence_count = len(sentences)
            if 2 <= sentence_count <= 8:
                count_score = 1.0
            elif sentence_count < 2:
                count_score = sentence_count / 2
            else:
                count_score = max(0.3, 8 / sentence_count)
            
            # 综合可读性分数
            readability = (length_score * 0.6) + (count_score * 0.4)
            
            return min(readability, 1.0)
            
        except Exception as e:
            logger.warning(f"可读性计算失败: {str(e)}")
            return 0.5
    
    def _calculate_medical_relevance(self, text: str) -> float:
        """计算医学相关性
        
        Args:
            text: 文本
            
        Returns:
            医学相关性分数 (0-1)
        """
        try:
            words = list(jieba.cut(text.lower()))
            content_words = [w for w in words if len(w) > 1]
            
            if not content_words:
                return 0.0
            
            # 医学术语计数
            medical_word_count = sum(1 for word in content_words if word in self.medical_terms)
            
            # 医学相关性比率
            medical_ratio = medical_word_count / len(content_words)
            
            # 归一化到0-1范围
            return min(medical_ratio * 3, 1.0)  # 乘以3是因为医学术语密度通常较低
            
        except Exception as e:
            logger.warning(f"医学相关性计算失败: {str(e)}")
            return 0.0
    
    def _determine_quality_level(self, score: float) -> QualityLevel:
        """确定质量等级
        
        Args:
            score: 质量分数 (0-1)
            
        Returns:
            质量等级
        """
        if score >= 0.8:
            return QualityLevel.EXCELLENT
        elif score >= 0.6:
            return QualityLevel.GOOD
        elif score >= 0.4:
            return QualityLevel.FAIR
        else:
            return QualityLevel.POOR
    
    async def evaluate_summary_quality(
        self,
        original_text: str,
        summary: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> SummaryQuality:
        """评估摘要质量
        
        Args:
            original_text: 原始文本
            summary: 摘要文本
            metadata: 额外元数据
            
        Returns:
            摘要质量评估结果
        """
        start_time = datetime.now()
        self.total_summary_evaluations += 1
        
        try:
            # 输入验证
            if not original_text or not summary:
                return SummaryQuality(
                    overall_score=0.0,
                    quality_level=QualityLevel.POOR,
                    length_score=0.0,
                    coherence_score=0.0,
                    coverage_score=0.0,
                    readability_score=0.0,
                    medical_relevance_score=0.0,
                    compression_ratio=0.0,
                    evaluation_time=(datetime.now() - start_time).total_seconds(),
                    metadata=metadata or {"error": "输入文本为空"}
                )
            
            # 1. 长度评分
            summary_length = len(summary)
            if self.min_summary_length <= summary_length <= self.max_summary_length:
                length_score = 1.0
            elif summary_length < self.min_summary_length:
                length_score = summary_length / self.min_summary_length
            else:
                length_score = max(0.3, self.max_summary_length / summary_length)
            
            # 2. 连贯性评分（基于句子结构）
            coherence_score = self._calculate_readability_score(summary)
            
            # 3. 覆盖度评分（基于文本相似度）
            coverage_score = self._calculate_text_similarity(original_text, summary)
            
            # 4. 可读性评分
            readability_score = self._calculate_readability_score(summary)
            
            # 5. 医学相关性评分
            medical_relevance_score = self._calculate_medical_relevance(summary)
            
            # 6. 压缩比
            compression_ratio = self._calculate_compression_ratio(original_text, summary)
            
            # 7. 信息密度加分
            info_density = self._calculate_information_density(summary)
            
            # 综合评分
            base_score = (
                length_score * 0.15 +
                coherence_score * 0.20 +
                coverage_score * 0.25 +
                readability_score * 0.15 +
                medical_relevance_score * 0.15 +
                info_density * 0.10
            )
            
            # 医学术语加分
            medical_bonus = 0.0
            if medical_relevance_score > 0.3:
                medical_bonus = self.medical_term_bonus
            
            # 最终分数
            overall_score = min(base_score + medical_bonus, 1.0)
            
            # 质量等级
            quality_level = self._determine_quality_level(overall_score)
            
            # 更新统计
            self.average_summary_score = (
                (self.average_summary_score * (self.total_summary_evaluations - 1) + overall_score) /
                self.total_summary_evaluations
            )
            
            # 创建质量评估结果
            quality_result = SummaryQuality(
                overall_score=overall_score,
                quality_level=quality_level,
                length_score=length_score,
                coherence_score=coherence_score,
                coverage_score=coverage_score,
                readability_score=readability_score,
                medical_relevance_score=medical_relevance_score,
                compression_ratio=compression_ratio,
                evaluation_time=(datetime.now() - start_time).total_seconds(),
                metadata={
                    **(metadata or {}),
                    "summary_length": summary_length,
                    "original_length": len(original_text),
                    "info_density": info_density,
                    "medical_bonus": medical_bonus
                }
            )
            
            logger.debug(f"摘要质量评估完成 - 分数: {overall_score:.3f}, 等级: {quality_level.value}")
            return quality_result
            
        except Exception as e:
            logger.error(f"摘要质量评估失败: {str(e)}")
            return SummaryQuality(
                overall_score=0.0,
                quality_level=QualityLevel.POOR,
                length_score=0.0,
                coherence_score=0.0,
                coverage_score=0.0,
                readability_score=0.0,
                medical_relevance_score=0.0,
                compression_ratio=0.0,
                evaluation_time=(datetime.now() - start_time).total_seconds(),
                metadata={"error": str(e)}
            )
    
    async def evaluate_keyword_quality(
        self,
        original_text: str,
        keywords: List[str],
        keyword_scores: Optional[List[float]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> KeywordQuality:
        """评估关键词质量
        
        Args:
            original_text: 原始文本
            keywords: 关键词列表
            keyword_scores: 关键词分数列表
            metadata: 额外元数据
            
        Returns:
            关键词质量评估结果
        """
        start_time = datetime.now()
        self.total_keyword_evaluations += 1
        
        try:
            # 输入验证
            if not original_text or not keywords:
                return KeywordQuality(
                    overall_score=0.0,
                    quality_level=QualityLevel.POOR,
                    relevance_score=0.0,
                    diversity_score=0.0,
                    coverage_score=0.0,
                    medical_specificity_score=0.0,
                    keyword_count=0,
                    average_keyword_score=0.0,
                    evaluation_time=(datetime.now() - start_time).total_seconds(),
                    metadata=metadata or {"error": "输入为空"}
                )
            
            keyword_count = len(keywords)
            keyword_scores = keyword_scores or [1.0] * keyword_count
            
            # 1. 数量评分
            if self.min_keyword_count <= keyword_count <= self.max_keyword_count:
                count_score = 1.0
            elif keyword_count < self.min_keyword_count:
                count_score = keyword_count / self.min_keyword_count
            else:
                count_score = max(0.3, self.max_keyword_count / keyword_count)
            
            # 2. 相关性评分（关键词在原文中的出现频率）
            original_words = set(jieba.cut(original_text.lower()))
            relevant_keywords = [kw for kw in keywords if kw.lower() in original_words]
            relevance_score = len(relevant_keywords) / keyword_count if keyword_count > 0 else 0.0
            
            # 3. 多样性评分（关键词的唯一性和长度分布）
            unique_keywords = set(keywords)
            uniqueness_ratio = len(unique_keywords) / keyword_count if keyword_count > 0 else 0.0
            
            # 长度多样性
            keyword_lengths = [len(kw) for kw in keywords]
            if keyword_lengths:
                length_variance = sum((l - sum(keyword_lengths) / len(keyword_lengths)) ** 2 for l in keyword_lengths) / len(keyword_lengths)
                length_diversity = min(length_variance / 10, 1.0)  # 归一化
            else:
                length_diversity = 0.0
            
            diversity_score = (uniqueness_ratio * 0.7) + (length_diversity * 0.3)
            
            # 4. 覆盖度评分（关键词覆盖原文的程度）
            keyword_text = " ".join(keywords)
            coverage_score = self._calculate_text_similarity(original_text, keyword_text)
            
            # 5. 医学专业性评分
            medical_keywords = [kw for kw in keywords if kw in self.medical_terms]
            medical_specificity_score = len(medical_keywords) / keyword_count if keyword_count > 0 else 0.0
            
            # 6. 平均关键词分数
            average_keyword_score = sum(keyword_scores) / len(keyword_scores) if keyword_scores else 0.0
            
            # 综合评分
            base_score = (
                count_score * 0.15 +
                relevance_score * 0.25 +
                diversity_score * 0.20 +
                coverage_score * 0.20 +
                medical_specificity_score * 0.10 +
                average_keyword_score * 0.10
            )
            
            # 医学术语加分
            medical_bonus = 0.0
            if medical_specificity_score > 0.3:
                medical_bonus = self.medical_term_bonus
            
            # 最终分数
            overall_score = min(base_score + medical_bonus, 1.0)
            
            # 质量等级
            quality_level = self._determine_quality_level(overall_score)
            
            # 更新统计
            self.average_keyword_score = (
                (self.average_keyword_score * (self.total_keyword_evaluations - 1) + overall_score) /
                self.total_keyword_evaluations
            )
            
            # 创建质量评估结果
            quality_result = KeywordQuality(
                overall_score=overall_score,
                quality_level=quality_level,
                relevance_score=relevance_score,
                diversity_score=diversity_score,
                coverage_score=coverage_score,
                medical_specificity_score=medical_specificity_score,
                keyword_count=keyword_count,
                average_keyword_score=average_keyword_score,
                evaluation_time=(datetime.now() - start_time).total_seconds(),
                metadata={
                    **(metadata or {}),
                    "unique_keyword_count": len(unique_keywords),
                    "medical_keyword_count": len(medical_keywords),
                    "relevant_keyword_count": len(relevant_keywords),
                    "count_score": count_score,
                    "medical_bonus": medical_bonus
                }
            )
            
            logger.debug(f"关键词质量评估完成 - 分数: {overall_score:.3f}, 等级: {quality_level.value}")
            return quality_result
            
        except Exception as e:
            logger.error(f"关键词质量评估失败: {str(e)}")
            return KeywordQuality(
                overall_score=0.0,
                quality_level=QualityLevel.POOR,
                relevance_score=0.0,
                diversity_score=0.0,
                coverage_score=0.0,
                medical_specificity_score=0.0,
                keyword_count=len(keywords) if keywords else 0,
                average_keyword_score=0.0,
                evaluation_time=(datetime.now() - start_time).total_seconds(),
                metadata={"error": str(e)}
            )
    
    async def batch_evaluate_quality(
        self,
        evaluations: List[Dict[str, Any]],
        batch_size: int = 10
    ) -> List[Tuple[Optional[SummaryQuality], Optional[KeywordQuality]]]:
        """批量质量评估
        
        Args:
            evaluations: 评估任务列表
            batch_size: 批处理大小
            
        Returns:
            质量评估结果列表
        """
        results = []
        
        for i in range(0, len(evaluations), batch_size):
            batch = evaluations[i:i + batch_size]
            batch_tasks = []
            
            for eval_data in batch:
                tasks = []
                
                # 摘要质量评估
                if "summary" in eval_data:
                    tasks.append(
                        self.evaluate_summary_quality(
                            original_text=eval_data["original_text"],
                            summary=eval_data["summary"],
                            metadata=eval_data.get("metadata")
                        )
                    )
                else:
                    tasks.append(asyncio.create_task(asyncio.sleep(0, result=None)))
                
                # 关键词质量评估
                if "keywords" in eval_data:
                    tasks.append(
                        self.evaluate_keyword_quality(
                            original_text=eval_data["original_text"],
                            keywords=eval_data["keywords"],
                            keyword_scores=eval_data.get("keyword_scores"),
                            metadata=eval_data.get("metadata")
                        )
                    )
                else:
                    tasks.append(asyncio.create_task(asyncio.sleep(0, result=None)))
                
                batch_tasks.extend(tasks)
            
            # 执行批次任务
            batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
            
            # 处理结果
            for j in range(0, len(batch_results), 2):
                summary_quality = batch_results[j] if not isinstance(batch_results[j], Exception) else None
                keyword_quality = batch_results[j + 1] if not isinstance(batch_results[j + 1], Exception) else None
                results.append((summary_quality, keyword_quality))
            
            # 批次间延迟
            if i + batch_size < len(evaluations):
                await asyncio.sleep(0.1)
        
        logger.info(f"批量质量评估完成: {len(results)} 个评估")
        return results
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            "total_summary_evaluations": self.total_summary_evaluations,
            "total_keyword_evaluations": self.total_keyword_evaluations,
            "average_summary_score": self.average_summary_score,
            "average_keyword_score": self.average_keyword_score,
            "min_summary_length": self.min_summary_length,
            "max_summary_length": self.max_summary_length,
            "min_keyword_count": self.min_keyword_count,
            "max_keyword_count": self.max_keyword_count,
            "medical_term_bonus": self.medical_term_bonus,
            "enable_readability_check": self.enable_readability_check,
            "medical_terms_count": len(self.medical_terms)
        }
    
    def reset_stats(self):
        """重置统计信息"""
        self.total_summary_evaluations = 0
        self.total_keyword_evaluations = 0
        self.average_summary_score = 0.0
        self.average_keyword_score = 0.0
        logger.info("质量评估器统计信息已重置")
    
    async def health_check(self) -> bool:
        """健康检查"""
        try:
            # 测试摘要质量评估
            test_text = "这是一个测试文本，用于检查质量评估功能。患者出现发热症状，需要进行血常规检查。"
            test_summary = "患者发热，需要血常规检查。"
            
            summary_quality = await self.evaluate_summary_quality(test_text, test_summary)
            
            # 测试关键词质量评估
            test_keywords = ["患者", "发热", "血常规", "检查"]
            keyword_quality = await self.evaluate_keyword_quality(test_text, test_keywords)
            
            if (
                isinstance(summary_quality, SummaryQuality) and
                isinstance(keyword_quality, KeywordQuality) and
                summary_quality.overall_score >= 0 and
                keyword_quality.overall_score >= 0
            ):
                logger.info("质量评估器健康检查通过")
                return True
            else:
                logger.warning("质量评估器健康检查失败")
                return False
                
        except Exception as e:
            logger.error(f"质量评估器健康检查异常: {str(e)}")
            return False