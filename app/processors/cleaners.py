"""
Text Cleaning Module for Medical Documents
医疗文档文本清洗模块
"""

import re
from typing import Dict, List, Set, Optional, Tuple
from app.utils.logger import setup_logger

logger = setup_logger(__name__)


class TextCleaner:
    """Text cleaning utilities for medical documents"""
    
    def __init__(self):
        """Initialize text cleaner with predefined patterns"""
        self.noise_patterns = self._init_noise_patterns()
        self.header_footer_patterns = self._init_header_footer_patterns()
        self.medical_abbreviations = self._init_medical_abbreviations()
        
    def _init_noise_patterns(self) -> List[Tuple[str, str]]:
        """Initialize noise removal patterns
        
        Returns:
            List of (pattern, replacement) tuples
        """
        return [
            # PDF conversion artifacts
            (r'书书书+', ''),
            (r'[^\w\s\u4e00-\u9fff\u3000-\u303f\uff00-\uffef.,;:!?()[\]{}""''—–\-+*/=<>@#$%^&|\\~`]+', ''),
            
            # Excessive whitespace and line breaks
            (r'\n\s*\n\s*\n+', '\n\n'),  # Multiple line breaks
            (r'[ \t]+', ' '),  # Multiple spaces/tabs
            (r'^\s+|\s+$', ''),  # Leading/trailing whitespace
            
            # OCR errors and garbled text
            (r'[０-９]+', lambda m: str(int(m.group().replace('０', '0').replace('１', '1').replace('２', '2').replace('３', '3').replace('４', '4').replace('５', '5').replace('６', '6').replace('７', '7').replace('８', '8').replace('９', '9')))),  # Full-width numbers
            (r'[Ａ-Ｚａ-ｚ]+', lambda m: m.group().translate(str.maketrans('ＡＢＣＤＥＦＧＨＩＪＫＬＭＮＯＰＱＲＳＴＵＶＷＸＹＺａｂｃｄｅｆｇｈｉｊｋｌｍｎｏｐｑｒｓｔｕｖｗｘｙｚ', 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz'))),  # Full-width letters
            
            # Repeated punctuation
            (r'[。，；：！？]{2,}', lambda m: m.group()[0]),
            (r'[.,:;!?]{2,}', lambda m: m.group()[0]),
            
            # Page numbers and references
            (r'^\s*第?\s*[0-9]+\s*页?\s*$', ''),  # Page numbers
            (r'^\s*Page\s+\d+\s*$', ''),  # English page numbers
            (r'^\s*-\s*\d+\s*-\s*$', ''),  # Page separators
            
            # DOI and ISSN patterns
            (r'DOI[:：]\s*[^\n]+', ''),
            (r'ISSN[:：]\s*[^\n]+', ''),
            (r'doi[:：]\s*[^\n]+', ''),
            
            # Email addresses (often in headers/footers)
            (r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', ''),
            
            # URLs
            (r'https?://[^\s]+', ''),
            (r'www\.[^\s]+', ''),
            
            # Excessive punctuation marks
            (r'[·•\-=]{3,}', ''),  # Separator lines
            (r'[*]{3,}', ''),  # Asterisk lines
        ]
    
    def _init_header_footer_patterns(self) -> List[str]:
        """Initialize header/footer detection patterns
        
        Returns:
            List of regex patterns for headers/footers
        """
        return [
            r'^·\s*标\s*准\s*与\s*规\s*范\s*·',  # Standards and specifications
            r'^·\s*指南与共识\s*·',  # Guidelines and consensus
            r'^·\s*综\s*述\s*·',  # Review articles
            r'^·\s*论\s*著\s*·',  # Research articles
            r'^临床心血管病杂志',  # Journal name
            r'^中华医学杂志',  # Journal name
            r'^中国医学科学院',  # Institution
            r'^执笔者[:：]',  # Authors
            r'^通信作者[:：]',  # Corresponding author
            r'^作者单位[:：]',  # Author affiliation
            r'^基金项目[:：]',  # Funding
            r'^收稿日期[:：]',  # Received date
            r'^修回日期[:：]',  # Revised date
            r'^接受日期[:：]',  # Accepted date
            r'^\d{4}[-/]\d{1,2}[-/]\d{1,2}',  # Dates
            r'^Vol\.\s*\d+',  # Volume
            r'^No\.\s*\d+',  # Issue number
            r'^\d+年第\d+期',  # Chinese volume/issue
        ]
    
    def _init_medical_abbreviations(self) -> Dict[str, str]:
        """Initialize medical abbreviation mappings
        
        Returns:
            Dictionary of abbreviation mappings
        """
        return {
            # Common medical abbreviations
            'MI': '心肌梗死',
            'AMI': '急性心肌梗死',
            'CAD': '冠心病',
            'CHD': '冠心病',
            'HF': '心力衰竭',
            'AF': '心房颤动',
            'HTN': '高血压',
            'DM': '糖尿病',
            'COPD': '慢性阻塞性肺疾病',
            'CKD': '慢性肾脏病',
            'PCI': '经皮冠状动脉介入治疗',
            'CABG': '冠状动脉旁路移植术',
            'ECG': '心电图',
            'EKG': '心电图',
            'ECHO': '超声心动图',
            'CT': '计算机断层扫描',
            'MRI': '磁共振成像',
            'ICU': '重症监护室',
            'CCU': '冠心病监护室',
            'ER': '急诊科',
            'ED': '急诊科',
            
            # Chinese abbreviations
            '心梗': '心肌梗死',
            '冠脉': '冠状动脉',
            '房颤': '心房颤动',
            '室颤': '心室颤动',
            '心衰': '心力衰竭',
            '高血压': '高血压',
            '糖尿病': '糖尿病',
        }
    
    def clean_basic(self, text: str) -> str:
        """Apply basic text cleaning
        
        Args:
            text: Input text
            
        Returns:
            Cleaned text
        """
        if not text or not text.strip():
            return ""
        
        cleaned_text = text
        
        # Apply noise removal patterns
        for pattern, replacement in self.noise_patterns:
            if callable(replacement):
                cleaned_text = re.sub(pattern, replacement, cleaned_text)
            else:
                cleaned_text = re.sub(pattern, replacement, cleaned_text)
        
        # Normalize whitespace
        cleaned_text = re.sub(r'\s+', ' ', cleaned_text)
        cleaned_text = cleaned_text.strip()
        
        return cleaned_text
    
    def remove_headers_footers(self, text: str, page_number: Optional[int] = None) -> str:
        """Remove headers and footers from text
        
        Args:
            text: Input text
            page_number: Page number for context
            
        Returns:
            Text with headers/footers removed
        """
        if not text or not text.strip():
            return ""
        
        lines = text.split('\n')
        cleaned_lines = []
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Check if line matches header/footer patterns
            is_header_footer = False
            for pattern in self.header_footer_patterns:
                if re.match(pattern, line, re.IGNORECASE):
                    is_header_footer = True
                    logger.debug(f"Removed header/footer: {line[:50]}...")
                    break
            
            if not is_header_footer:
                cleaned_lines.append(line)
        
        return '\n'.join(cleaned_lines)
    
    def normalize_medical_terms(self, text: str, custom_dict: Optional[Dict[str, str]] = None) -> str:
        """Normalize medical terminology
        
        Args:
            text: Input text
            custom_dict: Custom terminology dictionary
            
        Returns:
            Text with normalized terminology
        """
        if not text or not text.strip():
            return ""
        
        # Combine default and custom dictionaries
        term_dict = self.medical_abbreviations.copy()
        if custom_dict:
            term_dict.update(custom_dict)
        
        normalized_text = text
        
        # Apply term normalization
        for abbrev, full_term in term_dict.items():
            # Case-insensitive replacement with word boundaries
            pattern = r'\b' + re.escape(abbrev) + r'\b'
            normalized_text = re.sub(pattern, full_term, normalized_text, flags=re.IGNORECASE)
        
        return normalized_text
    
    def remove_redundant_content(self, text: str) -> str:
        """Remove redundant and repetitive content
        
        Args:
            text: Input text
            
        Returns:
            Text with redundant content removed
        """
        if not text or not text.strip():
            return ""
        
        lines = text.split('\n')
        unique_lines = []
        seen_lines = set()
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Normalize line for comparison (remove extra spaces, punctuation)
            normalized_line = re.sub(r'[^\w\u4e00-\u9fff]', '', line.lower())
            
            # Skip very short lines or lines we've seen before
            if len(normalized_line) < 10 or normalized_line in seen_lines:
                continue
            
            seen_lines.add(normalized_line)
            unique_lines.append(line)
        
        return '\n'.join(unique_lines)
    
    def clean_comprehensive(self, text: str, page_number: Optional[int] = None, 
                          custom_terms: Optional[Dict[str, str]] = None) -> str:
        """Apply comprehensive cleaning pipeline
        
        Args:
            text: Input text
            page_number: Page number for context
            custom_terms: Custom terminology dictionary
            
        Returns:
            Comprehensively cleaned text
        """
        if not text or not text.strip():
            return ""
        
        logger.debug(f"Starting comprehensive cleaning for text of length {len(text)}")
        
        # Step 1: Basic cleaning
        cleaned_text = self.clean_basic(text)
        if not cleaned_text:
            return ""
        
        # Step 2: Remove headers and footers
        cleaned_text = self.remove_headers_footers(cleaned_text, page_number)
        if not cleaned_text:
            return ""
        
        # Step 3: Normalize medical terms
        cleaned_text = self.normalize_medical_terms(cleaned_text, custom_terms)
        
        # Step 4: Remove redundant content
        cleaned_text = self.remove_redundant_content(cleaned_text)
        
        # Step 5: Final cleanup
        cleaned_text = self.clean_basic(cleaned_text)
        
        logger.debug(f"Comprehensive cleaning completed. Output length: {len(cleaned_text)}")
        
        return cleaned_text
    
    def extract_structured_content(self, text: str) -> Dict[str, List[str]]:
        """Extract structured content from text
        
        Args:
            text: Input text
            
        Returns:
            Dictionary with structured content categories
        """
        if not text or not text.strip():
            return {}
        
        structured_content = {
            "titles": [],
            "lists": [],
            "tables": [],
            "references": [],
            "paragraphs": []
        }
        
        lines = text.split('\n')
        current_paragraph = []
        
        for line in lines:
            line = line.strip()
            if not line:
                if current_paragraph:
                    structured_content["paragraphs"].append(' '.join(current_paragraph))
                    current_paragraph = []
                continue
            
            # Detect titles (short lines, often capitalized or with specific patterns)
            if (len(line) < 100 and 
                (line.isupper() or 
                 re.match(r'^[一二三四五六七八九十]+[、．]', line) or
                 re.match(r'^\d+[\.、]\s*[^0-9]', line))):
                structured_content["titles"].append(line)
                if current_paragraph:
                    structured_content["paragraphs"].append(' '.join(current_paragraph))
                    current_paragraph = []
                continue
            
            # Detect lists
            if (re.match(r'^[•·\-\*]\s+', line) or 
                re.match(r'^\d+[\.）\)]\s+', line) or
                re.match(r'^[（\(]\d+[）\)]\s+', line)):
                structured_content["lists"].append(line)
                if current_paragraph:
                    structured_content["paragraphs"].append(' '.join(current_paragraph))
                    current_paragraph = []
                continue
            
            # Detect references
            if (re.match(r'^\[\d+\]', line) or 
                re.match(r'^\d+\.\s+[A-Z]', line) or
                '参考文献' in line):
                structured_content["references"].append(line)
                if current_paragraph:
                    structured_content["paragraphs"].append(' '.join(current_paragraph))
                    current_paragraph = []
                continue
            
            # Regular paragraph content
            current_paragraph.append(line)
        
        # Add final paragraph
        if current_paragraph:
            structured_content["paragraphs"].append(' '.join(current_paragraph))
        
        return structured_content


# Global cleaner instance
text_cleaner = TextCleaner()


# Convenience functions
def clean_basic(text: str) -> str:
    """Apply basic text cleaning"""
    return text_cleaner.clean_basic(text)


def clean_comprehensive(text: str, page_number: Optional[int] = None, 
                       custom_terms: Optional[Dict[str, str]] = None) -> str:
    """Apply comprehensive text cleaning"""
    return text_cleaner.clean_comprehensive(text, page_number, custom_terms)


def normalize_medical_terms(text: str, custom_dict: Optional[Dict[str, str]] = None) -> str:
    """Normalize medical terminology"""
    return text_cleaner.normalize_medical_terms(text, custom_dict)


def remove_headers_footers(text: str, page_number: Optional[int] = None) -> str:
    """Remove headers and footers"""
    return text_cleaner.remove_headers_footers(text, page_number)