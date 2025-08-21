"""工具模块测试"""

import pytest
import logging
import os
import tempfile
import shutil
from unittest.mock import patch, Mock
from pathlib import Path

from app.utils.logger import setup_logger, get_logger


class TestLogger:
    """日志工具测试类"""
    
    def setup_method(self):
        """测试前设置"""
        # 清理现有的日志处理器
        logging.getLogger().handlers.clear()
        
    def teardown_method(self):
        """测试后清理"""
        # 清理测试创建的日志文件
        if os.path.exists("logs"):
            shutil.rmtree("logs")
    
    def test_setup_logger_default_level(self):
        """测试默认日志级别设置"""
        logger = setup_logger("test_logger")
        
        assert logger is not None
        assert logger.name == "test_logger"
        assert logger.level == logging.INFO  # 默认级别
        assert len(logger.handlers) == 2  # 控制台和文件处理器
    
    def test_setup_logger_custom_level(self):
        """测试自定义日志级别"""
        logger = setup_logger("test_logger", "DEBUG")
        
        assert logger.level == logging.DEBUG
        
    def test_setup_logger_env_level(self):
        """测试环境变量日志级别"""
        with patch.dict(os.environ, {'LOG_LEVEL': 'WARNING'}):
            logger = setup_logger("test_logger")
            
            assert logger.level == logging.WARNING
    
    def test_setup_logger_handlers(self):
        """测试日志处理器设置"""
        logger = setup_logger("test_logger")
        
        # 检查处理器类型
        handler_types = [type(handler).__name__ for handler in logger.handlers]
        assert "StreamHandler" in handler_types  # 控制台处理器
        assert "FileHandler" in handler_types    # 文件处理器
    
    def test_setup_logger_no_duplicate_handlers(self):
        """测试避免重复添加处理器"""
        logger1 = setup_logger("test_logger")
        logger2 = setup_logger("test_logger")  # 同名logger
        
        assert logger1 is logger2
        assert len(logger1.handlers) == 2  # 不应该重复添加
    
    def test_setup_logger_creates_log_directory(self):
        """测试创建日志目录"""
        # 确保logs目录不存在
        if os.path.exists("logs"):
            shutil.rmtree("logs")
            
        logger = setup_logger("test_logger")
        
        assert os.path.exists("logs")
        assert os.path.isdir("logs")
    
    def test_setup_logger_file_handler_encoding(self):
        """测试文件处理器编码"""
        logger = setup_logger("test_logger")
        
        # 找到文件处理器
        file_handler = None
        for handler in logger.handlers:
            if isinstance(handler, logging.FileHandler):
                file_handler = handler
                break
        
        assert file_handler is not None
        # 检查文件名格式
        assert "app_" in file_handler.baseFilename
        assert ".log" in file_handler.baseFilename
    
    def test_get_logger_alias(self):
        """测试get_logger别名函数"""
        logger1 = setup_logger("test_logger")
        logger2 = get_logger("test_logger")
        
        assert logger1 is logger2
    
    def test_get_logger_with_level(self):
        """测试get_logger带级别参数"""
        logger = get_logger("test_logger", "ERROR")
        
        assert logger.level == logging.ERROR
    
    def test_logger_formatting(self):
        """测试日志格式化"""
        logger = setup_logger("test_logger")
        
        # 检查格式化器
        for handler in logger.handlers:
            formatter = handler.formatter
            assert formatter is not None
            # 检查格式字符串包含必要元素
            format_str = formatter._fmt
            assert "%(asctime)s" in format_str
            assert "%(name)s" in format_str
            assert "%(levelname)s" in format_str
            assert "%(message)s" in format_str
    
    def test_logger_different_names(self):
        """测试不同名称的日志记录器"""
        logger1 = setup_logger("logger1")
        logger2 = setup_logger("logger2")
        
        assert logger1 is not logger2
        assert logger1.name == "logger1"
        assert logger2.name == "logger2"
    
    @patch('os.makedirs')
    def test_setup_logger_makedirs_called(self, mock_makedirs):
        """测试创建目录被调用"""
        with patch('os.path.exists', return_value=False):
            setup_logger("test_logger")
            mock_makedirs.assert_called_once_with("logs")
    
    def test_invalid_log_level(self):
        """测试无效日志级别处理"""
        # Python logging会将无效级别转换为0
        with pytest.raises(AttributeError):
            setup_logger("test_logger", "INVALID_LEVEL")
    
    def test_logger_case_insensitive_level(self):
        """测试日志级别大小写不敏感"""
        logger1 = setup_logger("test_logger1", "debug")
        logger2 = setup_logger("test_logger2", "DEBUG")
        
        assert logger1.level == logging.DEBUG
        assert logger2.level == logging.DEBUG
        assert logger1.level == logger2.level