"""文本处理器测试

使用conftest.py中的模拟组件进行测试
"""

import pytest
from unittest.mock import Mock, patch

from app.processors.cleaners import TextCleaner
from app.processors.quality_filter import TextQualityFilter
from app.processors.medical_terminology import MedicalTerminologyStandardizer


class TestTextCleaner:
    """文本清理器测试类"""
    
    @pytest.fixture
    def text_cleaner(self):
        """创建文本清理器实例"""
        return TextCleaner()
    
    def test_cleaner_initialization(self, text_cleaner):
        """测试清理器初始化"""
        assert text_cleaner is not None
        assert hasattr(text_cleaner, 'clean_comprehensive')
    
    def test_clean_comprehensive(self, text_cleaner):
        """测试综合清理功能"""
        # 测试各种需要清理的文本
        test_cases = [
            # 多余空白
            ("这是  多余  空白", "这是 多余 空白"),
            # 特殊字符
            ("这是\t制表符\n换行符", "这是 制表符 换行符"),
            # 重复标点
            ("这是重复标点！！！", "这是重复标点！"),
            # 混合情况
            ("这是\t混合情况  ！！！\n\n", "这是 混合情况 ！")
        ]
        
        for input_text, expected_output in test_cases:
            result = text_cleaner.clean_comprehensive(input_text)
            assert result == expected_output
    
    def test_remove_extra_whitespace(self, text_cleaner):
        """测试移除多余空白功能"""
        input_text = "这是  多余  空白"
        expected_output = "这是 多余 空白"
        result = text_cleaner.remove_extra_whitespace(input_text)
        assert result == expected_output
    
    def test_normalize_punctuation(self, text_cleaner):
        """测试标点规范化功能"""
        input_text = "这是重复标点！！！，，，。。。"
        expected_output = "这是重复标点！，。"
        result = text_cleaner.normalize_punctuation(input_text)
        assert result == expected_output


class TestTextQualityFilter:
    """文本质量过滤器测试类"""
    
    @pytest.fixture
    def quality_filter(self):
        """创建质量过滤器实例"""
        return TextQualityFilter()
    
    def test_filter_initialization(self, quality_filter):
        """测试过滤器初始化"""
        assert quality_filter is not None
        assert hasattr(quality_filter, 'filter_text_chunks')
    
    def test_filter_text_chunks(self, quality_filter):
        """测试文本块过滤功能"""
        chunks = [
            "这是高质量文本，包含足够的信息。",
            "短文本",
            "这个文本包含很多重复重复重复重复重复重复重复重复重复重复重复重复重复重复重复重复重复重复重复重复",
            "这是另一个高质量文本，内容丰富且有意义。"
        ]
        
        metadata = [
            {"source": "file1.txt", "chunk_index": 0},
            {"source": "file1.txt", "chunk_index": 1},
            {"source": "file1.txt", "chunk_index": 2},
            {"source": "file1.txt", "chunk_index": 3}
        ]
        
        filtered_chunks, filtered_metadata = quality_filter.filter_text_chunks(chunks, metadata)
        
        # 验证结果
        assert len(filtered_chunks) < len(chunks)  # 应该过滤掉一些块
        assert len(filtered_chunks) == len(filtered_metadata)  # 块和元数据数量应该一致
        assert "短文本" not in filtered_chunks  # 应该过滤掉短文本
        assert "这个文本包含很多重复重复重复" not in "".join(filtered_chunks)  # 应该过滤掉重复文本
    
    def test_is_low_quality(self, quality_filter):
        """测试低质量判断功能"""
        # 测试各种低质量文本
        test_cases = [
            # 短文本
            ("短文本", True),
            # 重复文本
            ("重复重复重复重复重复重复重复重复重复重复", True),
            # 高质量文本
            ("这是一段高质量的医学文本，包含足够的信息和有意义的内容。", False)
        ]
        
        for input_text, expected_result in test_cases:
            result = quality_filter.is_low_quality(input_text)
            assert result == expected_result


class TestMedicalTerminologyStandardizer:
    """医学术语标准化器测试类"""
    
    @pytest.fixture
    def terminology_standardizer(self):
        """创建术语标准化器实例"""
        return MedicalTerminologyStandardizer()
    
    def test_standardizer_initialization(self, terminology_standardizer):
        """测试标准化器初始化"""
        assert terminology_standardizer is not None
        assert hasattr(terminology_standardizer, 'standardize_text')
        assert hasattr(terminology_standardizer, 'load_terminology_map')
    
    def test_standardize_text(self, terminology_standardizer):
        """测试文本标准化功能"""
        # 模拟术语映射
        with patch.object(terminology_standardizer, 'terminology_map', {
            "高血压": "高血压病",
            "糖尿病": "糖尿病",
            "心脏病": "心脏疾病"
        }):
            input_text = "患者有高血压和心脏病史。"
            expected_output = "患者有高血压病和心脏疾病史。"
            result = terminology_standardizer.standardize_text(input_text)
            assert result == expected_output
    
    def test_load_terminology_map(self, terminology_standardizer):
        """测试加载术语映射功能"""
        # 模拟文件读取
        mock_content = """
        高血压|高血压病
        心脏病|心脏疾病
        糖尿病|糖尿病
        """
        
        with patch('builtins.open', mock_open(read_data=mock_content)):
            terminology_map = terminology_standardizer.load_terminology_map("mock_path")
            
            # 验证结果
            assert terminology_map is not None
            assert len(terminology_map) == 3
            assert terminology_map["高血压"] == "高血压病"
            assert terminology_map["心脏病"] == "心脏疾病"
            assert terminology_map["糖尿病"] == "糖尿病"


# 模拟open函数
def mock_open(read_data=""):
    """创建模拟的open函数"""
    mock = Mock()
    mock.return_value.__enter__.return_value.read.return_value = read_data
    return mock