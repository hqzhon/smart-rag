"""
文档处理器
"""

from typing import List, Dict, Any
import os
from .pdf_processor import PDFProcessor
from app.utils.logger import setup_logger

logger = setup_logger(__name__)


class DocumentProcessor:
    """处理文档集合的类"""
    
    def __init__(self, input_dir: str, output_dir: str):
        """初始化文档处理器
        
        Args:
            input_dir: 输入目录，包含PDF文件
            output_dir: 输出目录，存储处理结果
        """
        self.input_dir = input_dir
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        
    def process_single_document(self, file_path: str) -> Dict[str, Any]:
        """处理单个PDF文档
        
        Args:
            file_path: PDF文件路径
            
        Returns:
            处理结果字典
        """
        try:
            processor = PDFProcessor(file_path)
            result = processor.process()
            
            # 保存处理结果
            filename = os.path.basename(file_path)
            output_path = os.path.join(self.output_dir, f"{os.path.splitext(filename)[0]}.txt")
            
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(result["text"])
            
            logger.info(f"成功处理文档: {filename}")
            return result
            
        except Exception as e:
            logger.error(f"处理文档 {file_path} 时出错: {str(e)}")
            raise
        
    def process_all_documents(self) -> List[Dict[str, Any]]:
        """处理目录中的所有PDF文档
        
        Returns:
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