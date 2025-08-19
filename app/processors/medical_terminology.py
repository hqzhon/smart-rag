"""
Medical Terminology Standardization Module
医学术语标准化模块
"""

import re
import json
from typing import Dict, List, Set, Optional, Tuple
from pathlib import Path
from app.utils.logger import setup_logger

logger = setup_logger(__name__)


class MedicalTerminologyStandardizer:
    """Medical terminology standardization and normalization"""
    
    def __init__(self, custom_dict_path: Optional[str] = None):
        """Initialize terminology standardizer
        
        Args:
            custom_dict_path: Path to custom terminology dictionary
        """
        self.standard_terms = self._init_standard_terms()
        self.abbreviations = self._init_abbreviations()
        self.synonyms = self._init_synonyms()
        self.drug_names = self._init_drug_names()
        self.disease_names = self._init_disease_names()
        self.procedure_names = self._init_procedure_names()
        
        # Load custom dictionary if provided
        if custom_dict_path and Path(custom_dict_path).exists():
            self._load_custom_dictionary(custom_dict_path)
    
    def _init_standard_terms(self) -> Dict[str, str]:
        """Initialize standard medical terms mapping
        
        Returns:
            Dictionary of standard term mappings
        """
        return {
            # Cardiovascular terms
            "心肌梗塞": "心肌梗死",
            "心肌梗死症": "心肌梗死",
            "急性心梗": "急性心肌梗死",
            "急性MI": "急性心肌梗死",
            "冠状动脉疾病": "冠心病",
            "冠状动脉粥样硬化性心脏病": "冠心病",
            "冠状动脉硬化": "冠心病",
            "心房纤颤": "心房颤动",
            "房性纤颤": "心房颤动",
            "心室纤颤": "心室颤动",
            "室性纤颤": "心室颤动",
            "充血性心力衰竭": "心力衰竭",
            "心功能不全": "心力衰竭",
            "左心衰": "左心衰竭",
            "右心衰": "右心衰竭",
            
            # Hypertension
            "高血压病": "高血压",
            "原发性高血压": "高血压",
            "继发性高血压": "继发性高血压",
            "恶性高血压": "恶性高血压",
            "高血压危象": "高血压急症",
            
            # Diabetes
            "糖尿病": "糖尿病",
            "1型糖尿病": "1型糖尿病",
            "2型糖尿病": "2型糖尿病",
            "胰岛素依赖型糖尿病": "1型糖尿病",
            "非胰岛素依赖型糖尿病": "2型糖尿病",
            "妊娠糖尿病": "妊娠期糖尿病",
            "糖尿病酮症酸中毒": "糖尿病酮症酸中毒",
            
            # Respiratory
            "慢性阻塞性肺病": "慢性阻塞性肺疾病",
            "慢阻肺": "慢性阻塞性肺疾病",
            "支气管哮喘": "哮喘",
            "急性呼吸窘迫综合征": "急性呼吸窘迫综合征",
            "呼吸衰竭": "呼吸衰竭",
            
            # Renal
            "慢性肾脏疾病": "慢性肾脏病",
            "慢性肾功能不全": "慢性肾脏病",
            "急性肾损伤": "急性肾损伤",
            "急性肾衰竭": "急性肾损伤",
            "终末期肾病": "终末期肾脏病",
            
            # Neurological
            "脑血管意外": "脑卒中",
            "中风": "脑卒中",
            "脑梗塞": "脑梗死",
            "脑梗死": "脑梗死",
            "脑出血": "脑出血",
            "蛛网膜下腔出血": "蛛网膜下腔出血",
            "短暂性脑缺血发作": "短暂性脑缺血发作",
            
            # Cancer
            "恶性肿瘤": "恶性肿瘤",
            "癌症": "恶性肿瘤",
            "肺癌": "肺癌",
            "乳腺癌": "乳腺癌",
            "胃癌": "胃癌",
            "肝癌": "肝癌",
            "结直肠癌": "结直肠癌",
            
            # Infectious diseases
            "新型冠状病毒肺炎": "COVID-19",
            "新冠肺炎": "COVID-19",
            "获得性免疫缺陷综合征": "艾滋病",
            "艾滋病": "艾滋病",
            "肺结核": "肺结核",
            "结核病": "结核病",
        }
    
    def _init_abbreviations(self) -> Dict[str, str]:
        """Initialize medical abbreviations mapping
        
        Returns:
            Dictionary of abbreviation mappings
        """
        return {
            # English abbreviations
            "MI": "心肌梗死",
            "AMI": "急性心肌梗死",
            "STEMI": "ST段抬高型心肌梗死",
            "NSTEMI": "非ST段抬高型心肌梗死",
            "CAD": "冠心病",
            "CHD": "冠心病",
            "IHD": "缺血性心脏病",
            "HF": "心力衰竭",
            "CHF": "充血性心力衰竭",
            "AF": "心房颤动",
            "VF": "心室颤动",
            "VT": "室性心动过速",
            "SVT": "室上性心动过速",
            "HTN": "高血压",
            "DM": "糖尿病",
            "T1DM": "1型糖尿病",
            "T2DM": "2型糖尿病",
            "COPD": "慢性阻塞性肺疾病",
            "ARDS": "急性呼吸窘迫综合征",
            "CKD": "慢性肾脏病",
            "AKI": "急性肾损伤",
            "ESRD": "终末期肾脏病",
            "CVA": "脑血管意外",
            "TIA": "短暂性脑缺血发作",
            "ICH": "脑出血",
            "SAH": "蛛网膜下腔出血",
            "PE": "肺栓塞",
            "DVT": "深静脉血栓",
            "UTI": "尿路感染",
            "COPD": "慢性阻塞性肺疾病",
            
            # Procedures
            "PCI": "经皮冠状动脉介入治疗",
            "PTCA": "经皮冠状动脉腔内成形术",
            "CABG": "冠状动脉旁路移植术",
            "IABP": "主动脉内球囊反搏",
            "ECMO": "体外膜肺氧合",
            "CPR": "心肺复苏",
            "ACLS": "高级心脏生命支持",
            "BLS": "基础生命支持",
            
            # Diagnostics
            "ECG": "心电图",
            "EKG": "心电图",
            "ECHO": "超声心动图",
            "TTE": "经胸超声心动图",
            "TEE": "经食管超声心动图",
            "CT": "计算机断层扫描",
            "MRI": "磁共振成像",
            "PET": "正电子发射断层扫描",
            "SPECT": "单光子发射计算机断层扫描",
            "DSA": "数字减影血管造影",
            "CAG": "冠状动脉造影",
            "IVUS": "血管内超声",
            "OCT": "光学相干断层扫描",
            "FFR": "血流储备分数",
            
            # Laboratory
            "CBC": "全血细胞计数",
            "BUN": "血尿素氮",
            "Cr": "肌酐",
            "eGFR": "估算肾小球滤过率",
            "ALT": "丙氨酸氨基转移酶",
            "AST": "天冬氨酸氨基转移酶",
            "CK": "肌酸激酶",
            "CK-MB": "肌酸激酶同工酶",
            "cTnI": "心肌肌钙蛋白I",
            "cTnT": "心肌肌钙蛋白T",
            "BNP": "脑钠肽",
            "NT-proBNP": "N末端脑钠肽前体",
            "CRP": "C反应蛋白",
            "ESR": "红细胞沉降率",
            "PCT": "降钙素原",
            "HbA1c": "糖化血红蛋白",
            "LDL": "低密度脂蛋白",
            "HDL": "高密度脂蛋白",
            "TC": "总胆固醇",
            "TG": "甘油三酯",
            
            # Units
            "ICU": "重症监护室",
            "CCU": "冠心病监护室",
            "CICU": "心脏重症监护室",
            "NICU": "新生儿重症监护室",
            "PICU": "儿科重症监护室",
            "ER": "急诊科",
            "ED": "急诊科",
            "OR": "手术室",
            "PACU": "麻醉后恢复室",
            
            # Chinese abbreviations
            "心梗": "心肌梗死",
            "急性心梗": "急性心肌梗死",
            "冠脉": "冠状动脉",
            "房颤": "心房颤动",
            "室颤": "心室颤动",
            "心衰": "心力衰竭",
            "高血压": "高血压",
            "糖尿病": "糖尿病",
            "慢阻肺": "慢性阻塞性肺疾病",
            "慢性肾病": "慢性肾脏病",
            "脑梗": "脑梗死",
            "脑出血": "脑出血",
        }
    
    def _init_synonyms(self) -> Dict[str, List[str]]:
        """Initialize medical term synonyms
        
        Returns:
            Dictionary mapping standard terms to their synonyms
        """
        return {
            "心肌梗死": ["心肌梗塞", "心梗", "MI", "AMI"],
            "冠心病": ["冠状动脉疾病", "CAD", "CHD", "冠状动脉粥样硬化性心脏病"],
            "心房颤动": ["房颤", "AF", "心房纤颤"],
            "心力衰竭": ["心衰", "HF", "CHF", "心功能不全"],
            "高血压": ["HTN", "高血压病"],
            "糖尿病": ["DM", "diabetes"],
            "慢性阻塞性肺疾病": ["COPD", "慢阻肺", "慢性阻塞性肺病"],
            "慢性肾脏病": ["CKD", "慢性肾病", "慢性肾功能不全"],
            "脑卒中": ["中风", "CVA", "脑血管意外"],
            "脑梗死": ["脑梗塞", "脑梗", "缺血性脑卒中"],
        }
    
    def _init_drug_names(self) -> Dict[str, str]:
        """Initialize drug name standardization
        
        Returns:
            Dictionary of drug name mappings
        """
        return {
            # Cardiovascular drugs
            "阿司匹林": "阿司匹林",
            "氯吡格雷": "氯吡格雷",
            "替格瑞洛": "替格瑞洛",
            "阿托伐他汀": "阿托伐他汀",
            "瑞舒伐他汀": "瑞舒伐他汀",
            "美托洛尔": "美托洛尔",
            "比索洛尔": "比索洛尔",
            "卡维地洛": "卡维地洛",
            "依那普利": "依那普利",
            "贝那普利": "贝那普利",
            "缬沙坦": "缬沙坦",
            "氨氯地平": "氨氯地平",
            "硝苯地平": "硝苯地平",
            "螺内酯": "螺内酯",
            "呋塞米": "呋塞米",
            "氢氯噻嗪": "氢氯噻嗪",
            "华法林": "华法林",
            "达比加群": "达比加群",
            "利伐沙班": "利伐沙班",
            "阿哌沙班": "阿哌沙班",
            
            # Diabetes drugs
            "二甲双胍": "二甲双胍",
            "格列齐特": "格列齐特",
            "格列美脲": "格列美脲",
            "瑞格列奈": "瑞格列奈",
            "阿卡波糖": "阿卡波糖",
            "西格列汀": "西格列汀",
            "利拉鲁肽": "利拉鲁肽",
            "胰岛素": "胰岛素",
            
            # Antibiotics
            "青霉素": "青霉素",
            "阿莫西林": "阿莫西林",
            "头孢曲松": "头孢曲松",
            "左氧氟沙星": "左氧氟沙星",
            "阿奇霉素": "阿奇霉素",
            "万古霉素": "万古霉素",
        }
    
    def _init_disease_names(self) -> Dict[str, str]:
        """Initialize disease name standardization
        
        Returns:
            Dictionary of disease name mappings
        """
        return {
            # Already covered in standard_terms, but can be extended
            "肺炎": "肺炎",
            "支气管炎": "支气管炎",
            "胃炎": "胃炎",
            "肝炎": "肝炎",
            "肾炎": "肾炎",
            "关节炎": "关节炎",
            "骨折": "骨折",
            "贫血": "贫血",
            "白血病": "白血病",
            "淋巴瘤": "淋巴瘤",
        }
    
    def _init_procedure_names(self) -> Dict[str, str]:
        """Initialize procedure name standardization
        
        Returns:
            Dictionary of procedure name mappings
        """
        return {
            "经皮冠状动脉介入治疗": "经皮冠状动脉介入治疗",
            "冠状动脉旁路移植术": "冠状动脉旁路移植术",
            "心脏起搏器植入术": "心脏起搏器植入术",
            "心脏除颤器植入术": "心脏除颤器植入术",
            "心脏瓣膜置换术": "心脏瓣膜置换术",
            "心脏瓣膜修复术": "心脏瓣膜修复术",
            "主动脉内球囊反搏": "主动脉内球囊反搏",
            "体外膜肺氧合": "体外膜肺氧合",
            "血液透析": "血液透析",
            "腹膜透析": "腹膜透析",
            "肾移植": "肾移植",
            "肝移植": "肝移植",
            "心脏移植": "心脏移植",
        }
    
    def _load_custom_dictionary(self, dict_path: str):
        """Load custom terminology dictionary
        
        Args:
            dict_path: Path to custom dictionary JSON file
        """
        try:
            with open(dict_path, 'r', encoding='utf-8') as f:
                custom_dict = json.load(f)
            
            # Merge custom dictionary with existing ones
            if 'standard_terms' in custom_dict:
                self.standard_terms.update(custom_dict['standard_terms'])
            if 'abbreviations' in custom_dict:
                self.abbreviations.update(custom_dict['abbreviations'])
            if 'synonyms' in custom_dict:
                for term, syns in custom_dict['synonyms'].items():
                    if term in self.synonyms:
                        self.synonyms[term].extend(syns)
                    else:
                        self.synonyms[term] = syns
            if 'drug_names' in custom_dict:
                self.drug_names.update(custom_dict['drug_names'])
            if 'disease_names' in custom_dict:
                self.disease_names.update(custom_dict['disease_names'])
            if 'procedure_names' in custom_dict:
                self.procedure_names.update(custom_dict['procedure_names'])
            
            logger.info(f"Loaded custom terminology dictionary from {dict_path}")
            
        except Exception as e:
            logger.error(f"Failed to load custom dictionary from {dict_path}: {e}")
    
    def standardize_text(self, text: str) -> str:
        """Standardize medical terminology in text
        
        Args:
            text: Input text
            
        Returns:
            Text with standardized terminology
        """
        if not text or not text.strip():
            return ""
        
        standardized_text = text
        
        # Apply all standardization mappings
        all_mappings = {}
        all_mappings.update(self.standard_terms)
        all_mappings.update(self.abbreviations)
        all_mappings.update(self.drug_names)
        all_mappings.update(self.disease_names)
        all_mappings.update(self.procedure_names)
        
        # Sort by length (longest first) to avoid partial replacements
        sorted_terms = sorted(all_mappings.items(), key=lambda x: len(x[0]), reverse=True)
        
        for original, standard in sorted_terms:
            # Use word boundaries for exact matching
            pattern = r'\b' + re.escape(original) + r'\b'
            standardized_text = re.sub(pattern, standard, standardized_text, flags=re.IGNORECASE)
        
        return standardized_text
    
    def extract_medical_entities(self, text: str) -> Dict[str, List[str]]:
        """Extract medical entities from text
        
        Args:
            text: Input text
            
        Returns:
            Dictionary with categorized medical entities
        """
        if not text or not text.strip():
            return {}
        
        entities = {
            "diseases": [],
            "drugs": [],
            "procedures": [],
            "abbreviations": [],
            "symptoms": []
        }
        
        # Extract diseases
        for disease in self.disease_names.values():
            if disease in text:
                entities["diseases"].append(disease)
        
        # Extract drugs
        for drug in self.drug_names.values():
            if drug in text:
                entities["drugs"].append(drug)
        
        # Extract procedures
        for procedure in self.procedure_names.values():
            if procedure in text:
                entities["procedures"].append(procedure)
        
        # Extract abbreviations
        for abbrev in self.abbreviations.keys():
            if re.search(r'\b' + re.escape(abbrev) + r'\b', text):
                entities["abbreviations"].append(abbrev)
        
        # Remove duplicates
        for category in entities:
            entities[category] = list(set(entities[category]))
        
        return entities
    
    def get_term_variations(self, standard_term: str) -> List[str]:
        """Get all variations of a standard term
        
        Args:
            standard_term: Standard medical term
            
        Returns:
            List of term variations
        """
        variations = [standard_term]
        
        # Check synonyms
        if standard_term in self.synonyms:
            variations.extend(self.synonyms[standard_term])
        
        # Check reverse mappings
        for mapping_dict in [self.standard_terms, self.abbreviations, 
                           self.drug_names, self.disease_names, self.procedure_names]:
            for original, standard in mapping_dict.items():
                if standard == standard_term:
                    variations.append(original)
        
        return list(set(variations))
    
    def validate_terminology(self, text: str) -> Dict[str, List[str]]:
        """Validate terminology usage in text
        
        Args:
            text: Input text
            
        Returns:
            Dictionary with validation results
        """
        validation_results = {
            "non_standard_terms": [],
            "missing_standardization": [],
            "suggestions": []
        }
        
        # Find terms that could be standardized
        for original, standard in self.standard_terms.items():
            if original in text and standard not in text:
                validation_results["non_standard_terms"].append(original)
                validation_results["suggestions"].append(f"Replace '{original}' with '{standard}'")
        
        # Find abbreviations that could be expanded
        for abbrev, full_term in self.abbreviations.items():
            if re.search(r'\b' + re.escape(abbrev) + r'\b', text):
                if full_term not in text:
                    validation_results["missing_standardization"].append(abbrev)
                    validation_results["suggestions"].append(f"Consider expanding '{abbrev}' to '{full_term}'")
        
        return validation_results


# Global terminology standardizer instance
terminology_standardizer = MedicalTerminologyStandardizer()


# Convenience functions
def standardize_medical_text(text: str) -> str:
    """Standardize medical terminology in text"""
    return terminology_standardizer.standardize_text(text)


def extract_medical_entities(text: str) -> Dict[str, List[str]]:
    """Extract medical entities from text"""
    return terminology_standardizer.extract_medical_entities(text)


def get_term_variations(standard_term: str) -> List[str]:
    """Get all variations of a standard term"""
    return terminology_standardizer.get_term_variations(standard_term)


def validate_medical_terminology(text: str) -> Dict[str, List[str]]:
    """Validate terminology usage in text"""
    return terminology_standardizer.validate_terminology(text)