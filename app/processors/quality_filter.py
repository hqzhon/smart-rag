"""
文本块质量过滤器
用于在嵌入前过滤低质量文本块
"""

import re
import math
from typing import List, Dict, Any, Tuple
from collections import Counter
import logging

logger = logging.getLogger(__name__)


class TextQualityFilter:
    """文本质量过滤器"""
    
    def __init__(self, 
                 min_length: int = 50,
                 max_length: int = 8000,
                 min_word_count: int = 10,
                 max_repetition_ratio: float = 0.7,
                 min_entropy: float = 2.0,
                 min_medical_relevance: float = 0.1):
        """初始化质量过滤器
        
        Args:
            min_length: 最小字符长度
            max_length: 最大字符长度
            min_word_count: 最小词数
            max_repetition_ratio: 最大重复率
            min_entropy: 最小信息熵
            min_medical_relevance: 最小医学相关性分数
        """
        self.min_length = min_length
        self.max_length = max_length
        self.min_word_count = min_word_count
        self.max_repetition_ratio = max_repetition_ratio
        self.min_entropy = min_entropy
        self.min_medical_relevance = min_medical_relevance
        
        # Medical keywords for relevance scoring
        self.medical_keywords = {
            'disease': ['疾病', '病症', '症状', '综合征', '病理', '诊断', '治疗', '药物', '手术'],
            'anatomy': ['心脏', '肺部', '肝脏', '肾脏', '大脑', '血管', '神经', '肌肉', '骨骼'],
            'medical_terms': ['患者', '病人', '医生', '护士', '医院', '临床', '检查', '化验', '影像'],
            'procedures': ['手术', '检查', '治疗', '护理', '康复', '预防', '筛查', '监测'],
            'medications': ['药物', '药品', '剂量', '副作用', '禁忌', '适应症', '处方']
        }
        
        # Compile medical keyword patterns
        self.medical_patterns = []
        for category, keywords in self.medical_keywords.items():
            pattern = '|'.join(keywords)
            self.medical_patterns.append(re.compile(pattern))
    
    def filter_text_chunks(self, text_chunks: List[str], 
                          metadata_list: List[Dict[str, Any]] = None) -> Tuple[List[str], List[Dict[str, Any]]]:
        """过滤文本块列表
        
        Args:
            text_chunks: 文本块列表
            metadata_list: 对应的元数据列表
            
        Returns:
            过滤后的文本块和元数据列表
        """
        if metadata_list is None:
            metadata_list = [{}] * len(text_chunks)
        
        filtered_chunks = []
        filtered_metadata = []
        
        for i, (chunk, metadata) in enumerate(zip(text_chunks, metadata_list)):
            quality_score, quality_info = self.assess_text_quality(chunk)
            
            # Add quality information to metadata
            enhanced_metadata = metadata.copy()
            enhanced_metadata.update({
                'quality_score': quality_score,
                'quality_info': quality_info,
                'chunk_index': i
            })
            
            # Filter based on quality criteria
            if self._passes_quality_filter(quality_info):
                filtered_chunks.append(chunk)
                filtered_metadata.append(enhanced_metadata)
            else:
                logger.debug(f"Filtered out chunk {i}: {quality_info}")
        
        logger.info(f"Filtered {len(text_chunks)} chunks to {len(filtered_chunks)} high-quality chunks")
        return filtered_chunks, filtered_metadata
    
    def assess_text_quality(self, text: str) -> Tuple[float, Dict[str, Any]]:
        """评估文本质量
        
        Args:
            text: 输入文本
            
        Returns:
            质量分数和详细信息
        """
        quality_info = {}
        
        # Basic length checks
        length = len(text)
        word_count = len(text.split())
        
        quality_info['length'] = length
        quality_info['word_count'] = word_count
        quality_info['length_score'] = self._score_length(length)
        quality_info['word_count_score'] = self._score_word_count(word_count)
        
        # Repetition analysis
        repetition_ratio = self._calculate_repetition_ratio(text)
        quality_info['repetition_ratio'] = repetition_ratio
        quality_info['repetition_score'] = self._score_repetition(repetition_ratio)
        
        # Information entropy
        entropy = self._calculate_entropy(text)
        quality_info['entropy'] = entropy
        quality_info['entropy_score'] = self._score_entropy(entropy)
        
        # Medical relevance
        medical_relevance = self._calculate_medical_relevance(text)
        quality_info['medical_relevance'] = medical_relevance
        quality_info['medical_relevance_score'] = self._score_medical_relevance(medical_relevance)
        
        # Language quality
        language_score = self._assess_language_quality(text)
        quality_info['language_score'] = language_score
        
        # Structure quality
        structure_score = self._assess_structure_quality(text)
        quality_info['structure_score'] = structure_score
        
        # Calculate overall quality score
        scores = [
            quality_info['length_score'],
            quality_info['word_count_score'],
            quality_info['repetition_score'],
            quality_info['entropy_score'],
            quality_info['medical_relevance_score'],
            language_score,
            structure_score
        ]
        
        overall_score = sum(scores) / len(scores)
        quality_info['overall_score'] = overall_score
        
        return overall_score, quality_info
    
    def _passes_quality_filter(self, quality_info: Dict[str, Any]) -> bool:
        """检查文本是否通过质量过滤
        
        Args:
            quality_info: 质量信息字典
            
        Returns:
            是否通过过滤
        """
        # Hard filters
        if quality_info['length'] < self.min_length or quality_info['length'] > self.max_length:
            return False
        
        if quality_info['word_count'] < self.min_word_count:
            return False
        
        if quality_info['repetition_ratio'] > self.max_repetition_ratio:
            return False
        
        if quality_info['entropy'] < self.min_entropy:
            return False
        
        if quality_info['medical_relevance'] < self.min_medical_relevance:
            return False
        
        # Soft filter based on overall score
        if quality_info['overall_score'] < 0.5:
            return False
        
        return True
    
    def _score_length(self, length: int) -> float:
        """评分文本长度"""
        if length < self.min_length:
            return 0.0
        elif length > self.max_length:
            return max(0.0, 1.0 - (length - self.max_length) / self.max_length)
        else:
            # Optimal range: 200-2000 characters
            if 200 <= length <= 2000:
                return 1.0
            elif length < 200:
                return length / 200
            else:
                return max(0.5, 1.0 - (length - 2000) / 6000)
    
    def _score_word_count(self, word_count: int) -> float:
        """评分词数"""
        if word_count < self.min_word_count:
            return 0.0
        elif word_count < 50:
            return word_count / 50
        elif word_count <= 500:
            return 1.0
        else:
            return max(0.5, 1.0 - (word_count - 500) / 1000)
    
    def _calculate_repetition_ratio(self, text: str) -> float:
        """计算重复率"""
        words = text.split()
        if len(words) < 2:
            return 0.0
        
        word_counts = Counter(words)
        total_words = len(words)
        repeated_words = sum(count - 1 for count in word_counts.values() if count > 1)
        
        return repeated_words / total_words if total_words > 0 else 0.0
    
    def _score_repetition(self, repetition_ratio: float) -> float:
        """评分重复率"""
        if repetition_ratio > self.max_repetition_ratio:
            return 0.0
        else:
            return 1.0 - repetition_ratio / self.max_repetition_ratio
    
    def _calculate_entropy(self, text: str) -> float:
        """计算信息熵"""
        if not text:
            return 0.0
        
        # Character-level entropy
        char_counts = Counter(text.lower())
        total_chars = len(text)
        
        entropy = 0.0
        for count in char_counts.values():
            probability = count / total_chars
            entropy -= probability * math.log2(probability)
        
        return entropy
    
    def _score_entropy(self, entropy: float) -> float:
        """评分信息熵"""
        if entropy < self.min_entropy:
            return 0.0
        elif entropy < 4.0:
            return entropy / 4.0
        else:
            return 1.0
    
    def _calculate_medical_relevance(self, text: str) -> float:
        """计算医学相关性"""
        text_lower = text.lower()
        total_matches = 0
        
        for pattern in self.medical_patterns:
            matches = len(pattern.findall(text_lower))
            total_matches += matches
        
        # Normalize by text length
        words = text.split()
        if len(words) == 0:
            return 0.0
        
        relevance_score = min(1.0, total_matches / len(words) * 10)
        return relevance_score
    
    def _score_medical_relevance(self, relevance: float) -> float:
        """评分医学相关性"""
        if relevance < self.min_medical_relevance:
            return 0.0
        else:
            return min(1.0, relevance / 0.5)  # Scale to 0-1
    
    def _assess_language_quality(self, text: str) -> float:
        """评估语言质量"""
        score = 1.0
        
        # Check for excessive punctuation
        punct_ratio = len(re.findall(r'[^\w\s]', text)) / len(text) if text else 0
        if punct_ratio > 0.3:
            score -= 0.3
        
        # Check for excessive whitespace
        whitespace_ratio = len(re.findall(r'\s', text)) / len(text) if text else 0
        if whitespace_ratio > 0.5:
            score -= 0.2
        
        # Check for mixed languages (basic heuristic)
        chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', text))
        english_chars = len(re.findall(r'[a-zA-Z]', text))
        total_chars = chinese_chars + english_chars
        
        if total_chars > 0:
            # Penalize heavily mixed content
            chinese_ratio = chinese_chars / total_chars
            if 0.1 < chinese_ratio < 0.9:
                score -= 0.1
        
        return max(0.0, score)
    
    def _assess_structure_quality(self, text: str) -> float:
        """评估结构质量"""
        score = 1.0
        
        # Check for proper sentence structure
        sentences = re.split(r'[.!?。！？]', text)
        if len(sentences) > 1:
            avg_sentence_length = sum(len(s.strip()) for s in sentences) / len(sentences)
            if avg_sentence_length < 10:  # Too short sentences
                score -= 0.2
            elif avg_sentence_length > 200:  # Too long sentences
                score -= 0.2
        
        # Check for paragraph structure
        paragraphs = text.split('\n\n')
        if len(paragraphs) > 1:
            avg_paragraph_length = sum(len(p.strip()) for p in paragraphs) / len(paragraphs)
            if avg_paragraph_length < 50:  # Too short paragraphs
                score -= 0.1
        
        # Check for excessive line breaks
        line_breaks = text.count('\n')
        if line_breaks > len(text) / 50:  # Too many line breaks
            score -= 0.2
        
        return max(0.0, score)


class ChunkMetadataEnhancer:
    """文本块元数据增强器"""
    
    def __init__(self):
        """初始化元数据增强器"""
        self.quality_filter = TextQualityFilter()
    
    def enhance_chunk_metadata(self, chunk: str, base_metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """增强单个文本块的元数据
        
        Args:
            chunk: 文本块
            base_metadata: 基础元数据
            
        Returns:
            增强后的元数据
        """
        if base_metadata is None:
            base_metadata = {}
        
        enhanced = base_metadata.copy()
        
        # Add quality assessment
        quality_score, quality_info = self.quality_filter.assess_text_quality(chunk)
        enhanced.update({
            'quality_score': quality_score,
            'quality_details': quality_info
        })
        
        # Add content analysis
        content_analysis = self._analyze_content(chunk)
        enhanced.update(content_analysis)
        
        # Add structural information
        structure_info = self._analyze_structure(chunk)
        enhanced.update(structure_info)
        
        return enhanced
    
    def _analyze_content(self, text: str) -> Dict[str, Any]:
        """分析文本内容"""
        analysis = {}
        
        # Basic statistics
        analysis['char_count'] = len(text)
        analysis['word_count'] = len(text.split())
        analysis['sentence_count'] = len(re.split(r'[.!?。！？]', text))
        analysis['paragraph_count'] = len(text.split('\n\n'))
        
        # Language detection
        chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', text))
        english_chars = len(re.findall(r'[a-zA-Z]', text))
        total_chars = chinese_chars + english_chars
        
        if total_chars > 0:
            analysis['chinese_ratio'] = chinese_chars / total_chars
            analysis['english_ratio'] = english_chars / total_chars
            analysis['primary_language'] = 'chinese' if chinese_chars > english_chars else 'english'
        else:
            analysis['chinese_ratio'] = 0.0
            analysis['english_ratio'] = 0.0
            analysis['primary_language'] = 'unknown'
        
        # Content type detection
        analysis['content_type'] = self._detect_content_type(text)
        
        return analysis
    
    def _analyze_structure(self, text: str) -> Dict[str, Any]:
        """分析文本结构"""
        structure = {}
        
        # Check for structured elements
        structure['has_headers'] = bool(re.search(r'<HEADER>.*?</HEADER>', text))
        structure['has_tables'] = bool(re.search(r'<TABLE>.*?</TABLE>', text))
        structure['has_lists'] = bool(re.search(r'<LIST>.*?</LIST>', text))
        structure['has_sections'] = bool(re.search(r'<SECTION>.*?</SECTION>', text))
        
        # Count structured elements
        structure['header_count'] = len(re.findall(r'<HEADER>.*?</HEADER>', text))
        structure['table_count'] = len(re.findall(r'<TABLE>.*?</TABLE>', text))
        structure['list_count'] = len(re.findall(r'<LIST>.*?</LIST>', text))
        structure['section_count'] = len(re.findall(r'<SECTION>.*?</SECTION>', text))
        
        # Structure complexity score
        structure_elements = (structure['header_count'] + structure['table_count'] + 
                            structure['list_count'] + structure['section_count'])
        structure['structure_complexity'] = min(1.0, structure_elements / 5.0)
        
        return structure
    
    def _detect_content_type(self, text: str) -> str:
        """检测内容类型"""
        text_lower = text.lower()
        
        # Medical report patterns
        if any(keyword in text_lower for keyword in ['诊断', '症状', '治疗', '病史', '检查结果']):
            return 'medical_report'
        
        # Research paper patterns
        if any(keyword in text_lower for keyword in ['摘要', '方法', '结果', '结论', '参考文献']):
            return 'research_paper'
        
        # Clinical guideline patterns
        if any(keyword in text_lower for keyword in ['指南', '建议', '推荐', '标准', '规范']):
            return 'clinical_guideline'
        
        # Table content
        if re.search(r'<TABLE>.*?</TABLE>', text):
            return 'table_content'
        
        # List content
        if re.search(r'<LIST>.*?</LIST>', text):
            return 'list_content'
        
        return 'general_text'