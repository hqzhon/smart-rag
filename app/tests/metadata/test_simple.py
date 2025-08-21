"""简单测试验证"""
import pytest
from app.tests.metadata.test_config import set_test_env_vars, clear_test_env_vars


def test_basic():
    """基本测试"""
    assert True


def test_config_setup():
    """测试配置设置"""
    set_test_env_vars()
    import os
    assert os.getenv('APP_NAME') == 'Smart RAG Test'
    clear_test_env_vars()