"""
查询转换器
"""

from typing import List, Dict, Any
from app.utils.logger import setup_logger

logger = setup_logger(__name__)


class QueryTransformer:
    """查询转换器，用于查询扩展和改写"""
    
    def __init__(self):
        """初始化查询转换器"""
        # 医疗领域同义词词典
        self.medical_synonyms = {
            "高血压": ["高血压病", "原发性高血压", "继发性高血压"],
            "糖尿病": ["DM", "diabetes", "血糖异常"],
            "心脏病": ["心血管疾病", "冠心病", "心肌梗死"],
            "癌症": ["肿瘤", "恶性肿瘤", "癌", "carcinoma"],
            "感冒": ["上呼吸道感染", "感冒症状", "流感"],
            "发烧": ["发热", "体温升高", "高热"],
            "头痛": ["头疼", "偏头痛", "头部疼痛"],
            "咳嗽": ["咳痰", "干咳", "咳嗽症状"]
        }
        
        # 医疗术语扩展
        self.medical_expansions = {
            "症状": ["临床表现", "体征", "病症"],
            "治疗": ["疗法", "治疗方案", "医治"],
            "药物": ["药品", "medication", "处方药"],
            "诊断": ["确诊", "诊断标准", "鉴别诊断"],
            "预防": ["预防措施", "预防方法", "防护"]
        }
        
        logger.info("查询转换器初始化完成")
    
    def expand_query(self, query: str) -> List[str]:
        """扩展查询，生成多个相关查询
        
        Args:
            query: 原始查询
            
        Returns:
            扩展后的查询列表
        """
        expanded_queries = [query]  # 包含原始查询
        
        try:
            # 同义词扩展
            for term, synonyms in self.medical_synonyms.items():
                if term in query:
                    for synonym in synonyms:
                        expanded_query = query.replace(term, synonym)
                        if expanded_query not in expanded_queries:
                            expanded_queries.append(expanded_query)
            
            # 术语扩展
            for term, expansions in self.medical_expansions.items():
                if term in query:
                    for expansion in expansions:
                        expanded_query = query.replace(term, expansion)
                        if expanded_query not in expanded_queries:
                            expanded_queries.append(expanded_query)
            
            # 生成问题变体
            question_variants = self._generate_question_variants(query)
            expanded_queries.extend(question_variants)
            
            # 去重并限制数量
            unique_queries = list(dict.fromkeys(expanded_queries))[:5]
            
            logger.info(f"查询扩展完成，原查询: {query}, 扩展为 {len(unique_queries)} 个查询")
            return unique_queries
            
        except Exception as e:
            logger.error(f"查询扩展时出错: {str(e)}")
            return [query]
    
    def _generate_question_variants(self, query: str) -> List[str]:
        """生成问题变体"""
        variants = []
        
        # 如果不是问句，尝试转换为问句
        if not any(q in query for q in ["什么", "如何", "为什么", "怎么", "？", "?"]):
            variants.extend([
                f"什么是{query}",
                f"{query}是什么",
                f"如何{query}",
                f"{query}的症状",
                f"{query}的治疗方法"
            ])
        
        # 如果是问句，尝试转换为陈述句
        else:
            if query.startswith("什么是"):
                term = query.replace("什么是", "").replace("？", "").replace("?", "")
                variants.extend([
                    term,
                    f"{term}定义",
                    f"{term}概念"
                ])
            elif "如何" in query:
                term = query.replace("如何", "").replace("？", "").replace("?", "")
                variants.extend([
                    f"{term}方法",
                    f"{term}步骤",
                    f"{term}指南"
                ])
        
        return variants
    
    def rewrite_query(self, query: str, context: str = None) -> str:
        """重写查询，使其更适合检索
        
        Args:
            query: 原始查询
            context: 上下文信息
            
        Returns:
            重写后的查询
        """
        try:
            rewritten = query
            
            # 移除停用词
            stop_words = ["的", "了", "在", "是", "有", "和", "或", "但是", "然而", "因为", "所以"]
            words = rewritten.split()
            filtered_words = [word for word in words if word not in stop_words]
            rewritten = " ".join(filtered_words)
            
            # 标准化医疗术语
            rewritten = self._normalize_medical_terms(rewritten)
            
            # 如果有上下文，结合上下文重写
            if context:
                rewritten = self._context_aware_rewrite(rewritten, context)
            
            logger.info(f"查询重写完成: {query} -> {rewritten}")
            return rewritten
            
        except Exception as e:
            logger.error(f"查询重写时出错: {str(e)}")
            return query
    
    def _normalize_medical_terms(self, query: str) -> str:
        """标准化医疗术语"""
        # 简单的术语标准化
        normalizations = {
            "高血压病": "高血压",
            "糖尿病患者": "糖尿病",
            "心脏疾病": "心脏病",
            "恶性肿瘤": "癌症"
        }
        
        normalized = query
        for old_term, new_term in normalizations.items():
            normalized = normalized.replace(old_term, new_term)
        
        return normalized
    
    def _context_aware_rewrite(self, query: str, context: str) -> str:
        """基于上下文的查询重写"""
        # 简单的上下文感知重写
        if "患者" in context and "患者" not in query:
            query = f"患者 {query}"
        
        if "治疗" in context and "治疗" not in query:
            query = f"{query} 治疗"
        
        return query
    
    def extract_medical_entities(self, query: str) -> Dict[str, List[str]]:
        """提取医疗实体
        
        Args:
            query: 查询文本
            
        Returns:
            提取的实体字典
        """
        entities = {
            "diseases": [],
            "symptoms": [],
            "treatments": [],
            "medications": []
        }
        
        try:
            # 简单的实体识别（基于关键词匹配）
            disease_keywords = ["高血压", "糖尿病", "心脏病", "癌症", "感冒", "肺炎"]
            symptom_keywords = ["发烧", "头痛", "咳嗽", "胸痛", "呼吸困难"]
            treatment_keywords = ["手术", "化疗", "放疗", "药物治疗", "物理治疗"]
            medication_keywords = ["阿司匹林", "青霉素", "胰岛素", "降压药"]
            
            query_lower = query.lower()
            
            for keyword in disease_keywords:
                if keyword in query_lower:
                    entities["diseases"].append(keyword)
            
            for keyword in symptom_keywords:
                if keyword in query_lower:
                    entities["symptoms"].append(keyword)
            
            for keyword in treatment_keywords:
                if keyword in query_lower:
                    entities["treatments"].append(keyword)
            
            for keyword in medication_keywords:
                if keyword in query_lower:
                    entities["medications"].append(keyword)
            
            logger.info(f"实体提取完成: {entities}")
            return entities
            
        except Exception as e:
            logger.error(f"实体提取时出错: {str(e)}")
            return entities