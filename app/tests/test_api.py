"""
API接口测试
"""
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

class TestHealthAPI:
    """健康检查API测试"""
    
    def test_health_check(self):
        """测试健康检查接口"""
        response = client.get("/api/v1/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data
        assert "version" in data

class TestDocumentAPI:
    """文档API测试"""
    
    def test_upload_document_no_file(self):
        """测试无文件上传"""
        response = client.post("/api/v1/documents/upload")
        assert response.status_code == 422
    
    def test_upload_document_invalid_file(self):
        """测试无效文件上传"""
        files = {"file": ("test.txt", b"test content", "text/plain")}
        response = client.post("/api/v1/documents/upload", files=files)
        assert response.status_code == 400
        assert "不支持的文件格式" in response.json()["detail"]

class TestChatAPI:
    """聊天API测试"""
    
    def test_ask_question_missing_params(self):
        """测试缺少参数的问答请求"""
        response = client.post("/api/v1/chat/query", json={})
        assert response.status_code == 422
    
    def test_ask_question_empty_question(self):
        """测试空问题"""
        response = client.post("/api/v1/chat/query", json={
            "query": "",
            "session_id": "test"
        })
        assert response.status_code == 400
        assert "查询内容不能为空" in response.json()["detail"]
    
    def test_ask_question_valid(self):
        """测试有效问答请求"""
        response = client.post("/api/v1/chat/query", json={
            "query": "什么是高血压？",
            "session_id": "test_session"
        })
        assert response.status_code == 200
        data = response.json()
        assert "response" in data
        assert "session_id" in data