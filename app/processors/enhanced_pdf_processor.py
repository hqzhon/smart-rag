"""
Enhanced PDF Document Processor with Layout-Aware Parsing
使用unstructured库实现布局感知的PDF文档处理器
"""

import os
import re
from typing import List, Dict, Any, Optional
from app.utils.logger import setup_logger

logger = setup_logger(__name__)

try:
    from unstructured.partition.pdf import partition_pdf
    from unstructured.documents.elements import Element
    UNSTRUCTURED_AVAILABLE = True
except ImportError:
    logger.warning("unstructured library not available, falling back to basic PDF processing")
    UNSTRUCTURED_AVAILABLE = False
    # Fallback imports
    import pypdf
    import pdfplumber


class EnhancedPDFProcessor:
    """Enhanced PDF processor with layout-aware parsing capabilities"""
    
    def __init__(self, pdf_path: str):
        """Initialize enhanced PDF processor
        
        Args:
            pdf_path: Path to PDF file
        """
        self.pdf_path = pdf_path
        self.filename = os.path.basename(pdf_path)
        self.use_unstructured = UNSTRUCTURED_AVAILABLE
        
    def extract_structured_elements(self) -> List[Dict[str, Any]]:
        """Extract structured elements using unstructured library
        
        Returns:
            List of structured elements with type, content, and metadata
        """
        if not self.use_unstructured:
            logger.warning("Falling back to basic PDF processing")
            return self._fallback_extraction()
            
        try:
            logger.info(f"Processing PDF with unstructured: {self.filename}")
            
            # Use unstructured to partition PDF with layout awareness
            # Use fast strategy for better performance
            elements = partition_pdf(
                self.pdf_path,
                strategy="fast",  # Fast strategy for better performance
                infer_table_structure=True,  # Better table handling
                languages=["chi_sim", "eng"],  # Support Chinese and English
                include_page_breaks=True,  # Preserve page structure
                extract_images_in_pdf=False,  # Skip images for now
                chunking_strategy="by_title"  # Group content by titles
            )
            
            processed_elements = []
            current_page = 1
            
            for element in elements:
                element_type = element.__class__.__name__
                content = element.text.strip() if element.text else ""
                
                if not content:
                    continue
                    
                # Extract metadata
                metadata = element.metadata.to_dict() if hasattr(element, 'metadata') else {}
                page_number = metadata.get('page_number', current_page)
                
                # Classify element type for better processing
                classified_type = self._classify_element_type(element_type, content)
                
                processed_element = {
                    "type": classified_type,
                    "original_type": element_type,
                    "content": content,
                    "page_number": page_number,
                    "metadata": metadata,
                    "length": len(content),
                    "is_structured": True
                }
                
                processed_elements.append(processed_element)
                
                # Update current page for elements without page info
                if page_number > current_page:
                    current_page = page_number
                    
            logger.info(f"Extracted {len(processed_elements)} structured elements")
            return processed_elements
            
        except Exception as e:
            logger.error(f"Unstructured processing failed: {str(e)}")
            logger.info("Falling back to basic PDF processing")
            return self._fallback_extraction()
    
    def _classify_element_type(self, original_type: str, content: str) -> str:
        """Classify element type based on content analysis
        
        Args:
            original_type: Original type from unstructured
            content: Element content
            
        Returns:
            Classified element type
        """
        content_lower = content.lower().strip()
        
        # Medical document specific classifications
        if original_type == "Title":
            if any(keyword in content_lower for keyword in ["指南", "共识", "标准", "规范", "建议"]):
                return "document_title"
            elif any(keyword in content_lower for keyword in ["摘要", "abstract", "背景", "目的"]):
                return "section_title"
            else:
                return "title"
                
        elif original_type == "NarrativeText":
            if len(content) > 500:
                return "main_content"
            elif any(keyword in content_lower for keyword in ["作者", "author", "通信", "corresponding"]):
                return "author_info"
            elif any(keyword in content_lower for keyword in ["关键词", "keywords", "key words"]):
                return "keywords"
            else:
                return "narrative_text"
                
        elif original_type == "ListItem":
            if re.match(r'^\d+[\.\)]\s+', content):
                return "numbered_list"
            elif re.match(r'^[•·\-\*]\s+', content):
                return "bullet_list"
            else:
                return "list_item"
                
        elif original_type == "Table":
            return "table"
            
        elif original_type == "Header":
            return "header"
            
        elif original_type == "Footer":
            return "footer"
            
        else:
            return original_type.lower()
    
    def _fallback_extraction(self) -> List[Dict[str, Any]]:
        """Fallback extraction using basic PDF processing
        
        Returns:
            List of basic elements
        """
        try:
            elements = []
            
            # Extract text using pypdf
            with open(self.pdf_path, 'rb') as file:
                reader = pypdf.PdfReader(file)
                
                for page_num, page in enumerate(reader.pages, 1):
                    page_text = page.extract_text()
                    if page_text and page_text.strip():
                        elements.append({
                            "type": "narrative_text",
                            "original_type": "Text",
                            "content": page_text.strip(),
                            "page_number": page_num,
                            "metadata": {"page_number": page_num},
                            "length": len(page_text.strip()),
                            "is_structured": False
                        })
            
            # Extract tables using pdfplumber
            try:
                with pdfplumber.open(self.pdf_path) as pdf:
                    for page_num, page in enumerate(pdf.pages, 1):
                        tables = page.extract_tables()
                        for table_idx, table in enumerate(tables):
                            if table and len(table) > 0:
                                table_text = self._format_table_text(table, page_num, table_idx)
                                elements.append({
                                    "type": "table",
                                    "original_type": "Table",
                                    "content": table_text,
                                    "page_number": page_num,
                                    "metadata": {
                                        "page_number": page_num,
                                        "table_index": table_idx,
                                        "raw_table": table
                                    },
                                    "length": len(table_text),
                                    "is_structured": False
                                })
            except Exception as e:
                logger.warning(f"Table extraction failed: {str(e)}")
            
            logger.info(f"Fallback extraction completed: {len(elements)} elements")
            return elements
            
        except Exception as e:
            logger.error(f"Fallback extraction failed: {str(e)}")
            return []
    
    def _format_table_text(self, table: List[List[str]], page_num: int, table_idx: int) -> str:
        """Format table data as text
        
        Args:
            table: Raw table data
            page_num: Page number
            table_idx: Table index on page
            
        Returns:
            Formatted table text
        """
        table_text = f"表格内容(第{page_num}页，第{table_idx+1}个表格):\n"
        for row in table:
            if row:
                table_text += " | ".join([str(cell) if cell else "" for cell in row]) + "\n"
        return table_text
    
    def extract_document_metadata(self, elements: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Extract document-level metadata from elements
        
        Args:
            elements: List of document elements
            
        Returns:
            Document metadata
        """
        metadata = {
            "filename": self.filename,
            "total_elements": len(elements),
            "total_pages": max([el.get("page_number", 1) for el in elements]) if elements else 1,
            "element_types": {},
            "total_length": sum([el.get("length", 0) for el in elements]),
            "has_tables": any(el.get("type") == "table" for el in elements),
            "has_structured_content": any(el.get("is_structured", False) for el in elements)
        }
        
        # Count element types
        for element in elements:
            element_type = element.get("type", "unknown")
            metadata["element_types"][element_type] = metadata["element_types"].get(element_type, 0) + 1
        
        # Extract title from first title element
        title_elements = [el for el in elements if el.get("type") in ["document_title", "title"]]
        if title_elements:
            metadata["title"] = title_elements[0]["content"][:100]  # First 100 chars
        else:
            metadata["title"] = os.path.splitext(self.filename)[0]
        
        return metadata
    
    def process(self) -> Dict[str, Any]:
        """Process PDF document and extract structured content
        
        Returns:
            Dictionary containing structured elements and metadata
        """
        logger.info(f"Starting enhanced PDF processing: {self.filename}")
        
        try:
            # Extract structured elements
            elements = self.extract_structured_elements()
            
            # Extract document metadata
            metadata = self.extract_document_metadata(elements)
            
            # Combine all text content from elements
            text_content = "\n\n".join([element.get("content", "") for element in elements if element.get("content")])
            
            result = {
                "filename": self.filename,
                "text": text_content,  # Add text field for compatibility
                "metadata": metadata,
                "structured_elements": elements,  # Rename for clarity
                "processing_method": "unstructured" if self.use_unstructured else "fallback"
            }
            
            logger.info(f"Enhanced PDF processing completed: {self.filename}")
            logger.info(f"Extracted {len(elements)} elements using {result['processing_method']} method")
            logger.info(f"Combined text length: {len(text_content)} characters")
            
            return result
            
        except Exception as e:
            logger.error(f"Enhanced PDF processing failed: {str(e)}")
            raise