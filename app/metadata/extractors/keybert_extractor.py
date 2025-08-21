"""KeyBERT关键词提取器 - 增强版"""

import asyncio
from typing import List, Dict, Set, Tuple, Optional, Any
import logging
import re
from datetime import datetime
import jieba
import jieba.posseg as pseg
from collections import Counter

try:
    from keybert import KeyBERT
    from sentence_transformers import SentenceTransformer
except ImportError:
    KeyBERT = None
    SentenceTransformer = None

from ..models.metadata_models import KeywordInfo, KeywordMethod, MedicalCategory
from app.utils.logger import setup_logger

logger = setup_logger(__name__)

class KeyBERTExtractor:
    """KeyBERT关键词提取器
    
    支持：
    - KeyBERT模型提取
    - 医学词典增强
    - 中文分词优化
    - 关键词后处理
    - 降级策略
    """
    
    def __init__(
        self,
        model_name: str = "paraphrase-multilingual-MiniLM-L12-v2",
        top_k: int = 10,
        min_keyword_length: int = 2,
        max_keyword_length: int = 20,
        use_medical_dict: bool = True,
        medical_dict_weight: float = 1.5
    ):
        """初始化KeyBERT提取器
        
        Args:
            model_name: 句子嵌入模型名称
            top_k: 提取关键词数量
            min_keyword_length: 最小关键词长度
            max_keyword_length: 最大关键词长度
            use_medical_dict: 是否使用医学词典
            medical_dict_weight: 医学词典权重
        """
        self.model_name = model_name
        self.top_k = top_k
        self.min_keyword_length = min_keyword_length
        self.max_keyword_length = max_keyword_length
        self.use_medical_dict = use_medical_dict
        self.medical_dict_weight = medical_dict_weight
        
        # 模型初始化
        self.keybert_model = None
        self.sentence_model = None
        self.model_available = False
        
        # 医学词典
        self.medical_terms = self._load_medical_dictionary()
        
        # 停用词
        self.stop_words = self._load_stop_words()
        
        # 统计信息
        self.total_processed = 0
        self.success_count = 0
        self.error_count = 0
        
        # 模型初始化标志
        self._models_initialized = False
        
        logger.info(f"KeyBERT提取器初始化完成 - 模型: {model_name}, top_k: {top_k}")
    
    async def _initialize_models(self):
        """异步初始化模型"""
        try:
            if KeyBERT is None or SentenceTransformer is None:
                logger.warning("KeyBERT或SentenceTransformer未安装，将使用降级策略")
                self.model_available = False
                return
            
            # 在后台线程中加载模型
            loop = asyncio.get_event_loop()
            
            def load_models():
                try:
                    sentence_model = SentenceTransformer(self.model_name)
                    keybert_model = KeyBERT(model=sentence_model)
                    return keybert_model, sentence_model
                except Exception as e:
                    logger.error(f"模型加载失败: {str(e)}")
                    return None, None
            
            self.keybert_model, self.sentence_model = await loop.run_in_executor(
                None, load_models
            )
            
            if self.keybert_model is not None:
                self.model_available = True
                logger.info("KeyBERT模型加载成功")
            else:
                self.model_available = False
                logger.warning("KeyBERT模型加载失败，将使用降级策略")
                
        except Exception as e:
            logger.error(f"模型初始化异常: {str(e)}")
            self.model_available = False
    
    def _load_medical_dictionary(self) -> Set[str]:
        """加载医学词典"""
        # 基础医学术语词典
        medical_terms = {
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
            "抗凝药", "利尿剂", "镇静剂", "维生素", "中药", "西药",
            
            # 医疗操作
            "穿刺", "活检", "造影", "介入", "微创", "腹腔镜", "内镜",
            "放疗", "化疗", "免疫治疗", "靶向治疗", "康复训练"
        }
        
        logger.info(f"医学词典加载完成，包含{len(medical_terms)}个术语")
        return medical_terms
    
    def _load_stop_words(self) -> Set[str]:
        """加载停用词"""
        stop_words = {
            # 常见停用词
            "的", "了", "在", "是", "我", "有", "和", "就", "不", "人",
            "都", "一", "一个", "上", "也", "很", "到", "说", "要", "去",
            "你", "会", "着", "没有", "看", "好", "自己", "这", "那", "里",
            "就是", "还是", "把", "比", "或", "又", "可", "对", "及", "与",
            
            # 医学文档常见停用词
            "患者", "病人", "例", "岁", "男性", "女性", "主诉", "现病史",
            "既往史", "家族史", "个人史", "体格检查", "辅助检查", "诊断",
            "治疗", "医嘱", "出院", "入院", "住院", "门诊", "急诊",
            
            # 数字和单位
            "mg", "ml", "cm", "mm", "kg", "g", "次", "天", "小时",
            "分钟", "秒", "年", "月", "日", "周", "度", "℃"
        }
        
        return stop_words
    
    def _preprocess_text(self, text: str) -> str:
        """文本预处理"""
        # 去除特殊字符，保留中文、英文、数字
        text = re.sub(r'[^\u4e00-\u9fa5a-zA-Z0-9\s]', ' ', text)
        
        # 去除多余空格
        text = re.sub(r'\s+', ' ', text).strip()
        
        return text
    
    def _extract_with_jieba(self, text: str) -> List[Tuple[str, float]]:
        """使用jieba进行关键词提取（降级策略）"""
        try:
            # 分词和词性标注
            words = pseg.cut(text)
            
            # 过滤词性和长度
            valid_words = []
            for word, flag in words:
                if (
                    len(word) >= self.min_keyword_length and
                    len(word) <= self.max_keyword_length and
                    word not in self.stop_words and
                    flag in ['n', 'nr', 'ns', 'nt', 'nz', 'v', 'vn', 'a', 'ad']  # 名词、动词、形容词
                ):
                    valid_words.append(word)
            
            # 统计词频
            word_freq = Counter(valid_words)
            
            # 医学词典加权
            if self.use_medical_dict:
                for word in word_freq:
                    if word in self.medical_terms:
                        word_freq[word] *= self.medical_dict_weight
            
            # 获取top_k关键词
            top_words = word_freq.most_common(self.top_k)
            
            # 归一化分数
            if top_words:
                max_score = top_words[0][1]
                normalized_keywords = [
                    (word, score / max_score) for word, score in top_words
                ]
            else:
                normalized_keywords = []
            
            return normalized_keywords
            
        except Exception as e:
            logger.error(f"jieba关键词提取失败: {str(e)}")
            return []
    
    def _extract_with_keybert(self, text: str) -> List[Tuple[str, float]]:
        """使用KeyBERT进行关键词提取"""
        try:
            if not self.model_available or self.keybert_model is None:
                return []
            
            # KeyBERT提取
            keywords = self.keybert_model.extract_keywords(
                text,
                keyphrase_ngram_range=(1, 3),
                stop_words='english',  # KeyBERT内置英文停用词
                use_maxsum=True,
                nr_candidates=20,
                diversity=0.5
            )
            
            # 过滤和后处理
            filtered_keywords = []
            for keyword, score in keywords:
                # 长度过滤
                if (
                    len(keyword) >= self.min_keyword_length and
                    len(keyword) <= self.max_keyword_length and
                    keyword not in self.stop_words
                ):
                    # 医学词典加权
                    if self.use_medical_dict and keyword in self.medical_terms:
                        score *= self.medical_dict_weight
                    
                    filtered_keywords.append((keyword, score))
            
            # 按分数排序并取top_k
            filtered_keywords.sort(key=lambda x: x[1], reverse=True)
            return filtered_keywords[:self.top_k]
            
        except Exception as e:
            logger.error(f"KeyBERT关键词提取失败: {str(e)}")
            return []
    
    def _classify_medical_category(self, keywords: List[str]) -> MedicalCategory:
        """分类医学类别"""
        # 定义类别关键词
        category_keywords = {
            MedicalCategory.DISEASE: {
                "诊断", "疾病", "综合征", "病", "症", "炎", "癌", "瘤", "梗塞", "出血"
            },
            MedicalCategory.TREATMENT: {
                "治疗", "手术", "药物", "用药", "服用", "注射", "输液", "放疗", "化疗"
            },
            MedicalCategory.EXAMINATION: {
                "检查", "化验", "CT", "MRI", "B超", "心电图", "胸片", "血常规", "尿常规"
            },
            MedicalCategory.SYMPTOM: {
                "症状", "疼痛", "发热", "咳嗽", "呼吸困难", "头痛", "恶心", "呕吐", "腹痛"
            },
            MedicalCategory.DRUG: {
                "药物", "药品", "用药", "服药", "注射", "输液", "胶囊", "片剂", "针剂"
            },
            MedicalCategory.ANATOMY: {
                "器官", "组织", "细胞", "血管", "神经", "肌肉", "骨骼", "关节", "皮肤"
            }
        }
        
        # 统计各类别匹配度
        category_scores = {category: 0 for category in MedicalCategory}
        
        for keyword in keywords:
            for category, terms in category_keywords.items():
                if any(term in keyword for term in terms):
                    category_scores[category] += 1
        
        # 返回得分最高的类别
        if max(category_scores.values()) > 0:
            return max(category_scores, key=category_scores.get)
        else:
            return MedicalCategory.GENERAL
    
    async def extract_keywords(
        self,
        text: str,
        chunk_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> KeywordInfo:
        """提取关键词
        
        Args:
            text: 待提取的文本
            chunk_id: 文档块ID
            metadata: 额外的元数据
            
        Returns:
            关键词信息对象
        """
        start_time = datetime.now()
        self.total_processed += 1
        
        # 确保模型已初始化
        if not self._models_initialized:
            await self._initialize_models()
            self._models_initialized = True
        
        try:
            # 输入验证
            if not text or not text.strip():
                raise ValueError("输入文本不能为空")
            
            # 文本预处理
            processed_text = self._preprocess_text(text)
            
            if len(processed_text) < 10:
                logger.warning(f"文本过短 (长度: {len(processed_text)})，跳过关键词提取")
                return KeywordInfo(
                    chunk_id=chunk_id or f"chunk_{self.total_processed}",
                    keywords=[],
                    keyword_scores=[],
                    method=KeywordMethod.FALLBACK,
                    medical_category=MedicalCategory.GENERAL,
                    processing_time=(datetime.now() - start_time).total_seconds(),
                    metadata=metadata or {}
                )
            
            # 尝试KeyBERT提取
            keywords_with_scores = []
            method = KeywordMethod.KEYBERT
            
            if self.model_available:
                keywords_with_scores = self._extract_with_keybert(processed_text)
            
            # 如果KeyBERT失败，使用jieba降级
            if not keywords_with_scores:
                keywords_with_scores = self._extract_with_jieba(processed_text)
                method = KeywordMethod.JIEBA_FALLBACK if keywords_with_scores else KeywordMethod.FALLBACK
            
            # 分离关键词和分数
            keywords = [kw for kw, _ in keywords_with_scores]
            scores = [score for _, score in keywords_with_scores]
            
            # 医学类别分类
            medical_category = self._classify_medical_category(keywords)
            
            # 创建关键词信息对象
            keyword_info = KeywordInfo(
                chunk_id=chunk_id or f"chunk_{self.total_processed}",
                keywords=keywords,
                keyword_scores=scores,
                method=method,
                medical_category=medical_category,
                processing_time=(datetime.now() - start_time).total_seconds(),
                metadata=metadata or {}
            )
            
            self.success_count += 1
            logger.debug(f"关键词提取成功 - 块ID: {chunk_id}, 提取数量: {len(keywords)}, 方法: {method.value}")
            return keyword_info
            
        except Exception as e:
            self.error_count += 1
            logger.error(f"关键词提取失败: {str(e)}")
            
            # 返回空的关键词信息
            return KeywordInfo(
                chunk_id=chunk_id or f"chunk_{self.total_processed}",
                keywords=[],
                keyword_scores=[],
                method=KeywordMethod.FALLBACK,
                medical_category=MedicalCategory.GENERAL,
                processing_time=(datetime.now() - start_time).total_seconds(),
                metadata={
                    "error": str(e),
                    "fallback_reason": "关键词提取异常"
                }
            )
    
    async def batch_extract_keywords(
        self,
        texts: List[str],
        chunk_ids: Optional[List[str]] = None,
        metadata_list: Optional[List[Dict[str, Any]]] = None,
        batch_size: int = 10
    ) -> List[KeywordInfo]:
        """批量提取关键词
        
        Args:
            texts: 文本列表
            chunk_ids: 块ID列表
            metadata_list: 元数据列表
            batch_size: 批处理大小
            
        Returns:
            关键词信息列表
        """
        if not texts:
            return []
        
        # 参数对齐
        chunk_ids = chunk_ids or [None] * len(texts)
        metadata_list = metadata_list or [None] * len(texts)
        
        keyword_infos = []
        
        # 分批处理
        for i in range(0, len(texts), batch_size):
            batch_texts = texts[i:i + batch_size]
            batch_chunk_ids = chunk_ids[i:i + batch_size]
            batch_metadata = metadata_list[i:i + batch_size]
            
            # 并发处理当前批次
            batch_tasks = [
                self.extract_keywords(
                    text=text,
                    chunk_id=chunk_id,
                    metadata=metadata
                )
                for text, chunk_id, metadata in zip(
                    batch_texts, batch_chunk_ids, batch_metadata
                )
            ]
            
            batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
            
            # 处理异常结果
            for j, result in enumerate(batch_results):
                if isinstance(result, Exception):
                    logger.error(f"批次关键词提取异常 (索引 {i + j}): {str(result)}")
                    # 创建错误关键词信息
                    error_info = KeywordInfo(
                        chunk_id=batch_chunk_ids[j] or f"chunk_{i + j}",
                        keywords=[],
                        keyword_scores=[],
                        method=KeywordMethod.FALLBACK,
                        medical_category=MedicalCategory.GENERAL,
                        processing_time=0.0,
                        metadata={"error": str(result)}
                    )
                    keyword_infos.append(error_info)
                else:
                    keyword_infos.append(result)
            
            # 批次间延迟
            if i + batch_size < len(texts):
                await asyncio.sleep(0.2)
        
        success_count = len([ki for ki in keyword_infos if ki.method != KeywordMethod.FALLBACK])
        logger.info(f"批量关键词提取完成: {success_count}/{len(texts)} 成功")
        
        return keyword_infos
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            "total_processed": self.total_processed,
            "success_count": self.success_count,
            "error_count": self.error_count,
            "success_rate": self.success_count / max(self.total_processed, 1),
            "model_available": self.model_available,
            "model_name": self.model_name,
            "top_k": self.top_k,
            "medical_terms_count": len(self.medical_terms),
            "use_medical_dict": self.use_medical_dict
        }
    
    def reset_stats(self):
        """重置统计信息"""
        self.total_processed = 0
        self.success_count = 0
        self.error_count = 0
        logger.info("关键词提取器统计信息已重置")
    
    async def health_check(self) -> bool:
        """健康检查"""
        try:
            # 测试文本
            test_text = "这是一个测试文本，用于检查关键词提取功能是否正常工作。"
            result = await self.extract_keywords(test_text)
            
            if result and isinstance(result, KeywordInfo):
                logger.info("关键词提取器健康检查通过")
                return True
            else:
                logger.warning("关键词提取器健康检查失败")
                return False
                
        except Exception as e:
            logger.error(f"关键词提取器健康检查异常: {str(e)}")
            return False