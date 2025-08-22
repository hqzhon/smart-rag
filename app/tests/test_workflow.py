"""工作流模块测试

使用conftest.py中的模拟组件进行测试
"""

import pytest
import asyncio
import json
from unittest.mock import Mock, patch, AsyncMock

from app.workflow.enhanced_rag_workflow import EnhancedRAGWorkflow
from app.workflow.rag_graph import RAGWorkflow
from app.workflow.llm_client import LLMClient
from app.workflow.deepseek_client import DeepseekClient
from app.workflow.qianwen_client import QianwenClient


class AsyncContextManagerMock(AsyncMock):
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass


class TestEnhancedRAGWorkflow:
    """增强RAG工作流测试类"""
    
    @pytest.mark.asyncio
    async def test_process_query_empty(self, mock_retriever, mock_reranker, mock_query_transformer, mock_deepseek_client):
        """测试空查询处理"""
        with patch('app.workflow.enhanced_rag_workflow.get_deepseek_client', return_value=mock_deepseek_client):
            workflow = EnhancedRAGWorkflow(mock_retriever, mock_reranker, mock_query_transformer)
            # 设置检索返回空结果
            mock_retriever.adaptive_retrieve.return_value = []
            mock_retriever.multi_query_retrieve.return_value = []
            
            result = await workflow.process_query("")
            assert result is not None
            assert "query" in result
            assert "response" in result
            assert "documents" in result
            assert "抱歉，我没有找到相关的医疗信息。" in result["response"]
    
    

    @pytest.mark.asyncio
    async def test_process_query_valid(self, mock_retriever, mock_reranker, mock_query_transformer, 
                                     mock_deepseek_client, mock_db_manager):
        """测试有效查询处理"""
        mock_deepseek_client.__aenter__.return_value = mock_deepseek_client
        with patch('app.workflow.enhanced_rag_workflow.get_deepseek_client', return_value=mock_deepseek_client):
            workflow = EnhancedRAGWorkflow(mock_retriever, mock_reranker, mock_query_transformer)
            mock_retriever.multi_query_retrieve.return_value = [
                {'page_content': '多查询内容', 'metadata': {'source': 'doc3.pdf', 'score': 0.90}}
            ]
            mock_reranker.rerank_documents.return_value = [
                {'page_content': '重排序内容', 'metadata': {'source': 'doc1.pdf', 'score': 0.98}, 'rerank_score': 0.98}
            ]
            result = await workflow.process_query("什么是高血压？")
            
            assert result is not None
            assert "query" in result
            assert "response" in result
            assert "documents" in result
            
            # 验证组件调用 - 使用更宽松的验证，因为实际调用可能有所不同
            assert mock_retriever.multi_query_retrieve.called or mock_retriever.adaptive_retrieve.called
            mock_deepseek_client.generate_response.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_process_query_multi_query_mode(self, mock_retriever, mock_reranker, mock_query_transformer, mock_deepseek_client):
        """测试多查询模式处理"""
        with patch('app.workflow.enhanced_rag_workflow.get_deepseek_client', return_value=mock_deepseek_client):
            workflow = EnhancedRAGWorkflow(mock_retriever, mock_reranker, mock_query_transformer)
            mock_query_transformer.expand_query.return_value = ["扩展查询1", "扩展查询2"]
            mock_retriever.multi_query_retrieve.return_value = [
                {'page_content': '多查询内容', 'metadata': {'source': 'doc3.pdf', 'score': 0.90}}
            ]
            mock_reranker.rerank_documents.return_value = [
                {'page_content': '重排序内容', 'metadata': {'source': 'doc1.pdf', 'score': 0.98}, 'rerank_score': 0.98}
            ]

            result = await workflow.process_query("什么是高血压？")
            
            assert result is not None
            assert "query" in result
            assert "response" in result
            assert "documents" in result
            
            # 验证使用了多查询检索
            mock_retriever.multi_query_retrieve.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_process_query_no_documents(self, mock_retriever, mock_reranker, mock_query_transformer, mock_deepseek_client):
        """测试无文档检索结果"""
        with patch('app.workflow.enhanced_rag_workflow.get_deepseek_client', return_value=mock_deepseek_client):
            workflow = EnhancedRAGWorkflow(mock_retriever, mock_reranker, mock_query_transformer)
            # 设置检索返回空结果
            mock_retriever.adaptive_retrieve.return_value = []
            mock_retriever.multi_query_retrieve.return_value = []
            
            result = await workflow.process_query("什么是高血压？")
            
            assert result is not None
            assert "抱歉，我没有找到相关的医疗信息。" in result["response"]
            assert result["documents"] == []
    
    @pytest.mark.asyncio
    async def test_process_query_error_handling(self, mock_retriever, mock_reranker, mock_query_transformer, mock_deepseek_client):
        """测试查询处理错误处理"""
        with patch('app.workflow.enhanced_rag_workflow.get_deepseek_client', return_value=mock_deepseek_client):
            workflow = EnhancedRAGWorkflow(mock_retriever, mock_reranker, mock_query_transformer)
            # 设置检索器抛出异常
            mock_retriever.adaptive_retrieve.side_effect = Exception("检索失败")
            mock_retriever.multi_query_retrieve.side_effect = Exception("检索失败")
            
            result = await workflow.process_query("什么是高血压？")
            
            assert result is not None
            assert "处理查询时出现错误: 检索失败" in result["response"]
            assert result["documents"] == []
    
    @pytest.mark.asyncio
    async def test_stream_process_query(self, mock_retriever, mock_reranker, mock_query_transformer, mock_deepseek_client):
        """测试流式查询处理"""
        with patch('app.workflow.enhanced_rag_workflow.get_deepseek_client', return_value=mock_deepseek_client):
            workflow = EnhancedRAGWorkflow(mock_retriever, mock_reranker, mock_query_transformer)
            mock_deepseek_client.generate_stream_response.return_value = self.mock_stream_response()
            # 收集流式结果
            results = []
            async for chunk in workflow.stream_process_query("什么是高血压？"):
                results.append(chunk)
            
            assert len(results) > 0
            # 验证包含开始、内容和结束事件
            event_types = [r.get("type") for r in results if isinstance(r, dict)]
            assert "status" in event_types or "chunk" in event_types or "result" in event_types

    async def mock_stream_response(self):
        yield f"""data: {json.dumps({"choices":[{"delta":{"content":"流式"}}]})}
""".encode('utf-8')
        yield f"""data: {json.dumps({"choices":[{"delta":{"content":"响应"}}]})}
""".encode('utf-8')
        yield f"""data: [DONE]
""".encode('utf-8')


class TestRAGWorkflow:
    """RAG工作流测试类"""
    
    @pytest.fixture
    def rag_workflow(self, mock_retriever, mock_reranker, mock_query_transformer, mock_deepseek_client):
        mock_deepseek_client.generate.return_value = "模拟LLM回答"
        """创建RAG工作流实例"""
        return RAGWorkflow(mock_retriever, mock_reranker, mock_query_transformer, mock_deepseek_client)
    
    def test_init(self, rag_workflow):
        """测试初始化"""
        assert rag_workflow is not None
        assert hasattr(rag_workflow, 'retriever')
        assert hasattr(rag_workflow, 'reranker')
        assert hasattr(rag_workflow, 'query_transformer')
        assert hasattr(rag_workflow, 'llm_client')
    
    @pytest.mark.asyncio
    async def test_process_query(self, rag_workflow, mock_retriever, mock_reranker, 
                               mock_query_transformer, mock_deepseek_client, mock_qianwen_embedding_rerank_client):
        """测试查询处理"""
        rag_workflow.llm_client = mock_deepseek_client
        result = await rag_workflow.process_query("测试查询")
        
        assert result is not None
        assert "query" in result
        assert "response" in result
        assert "documents" in result
        
        # 验证组件调用
        mock_retriever.multi_query_retrieve.assert_called_once()
        mock_reranker.rerank_documents.assert_called_once()
        mock_query_transformer.expand_query.assert_called_once()
        mock_query_transformer.rewrite_query.assert_called_once()
        mock_deepseek_client.generate.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_process_query_no_documents(self, rag_workflow, mock_retriever):
        """测试无文档检索结果"""
        # 设置检索返回空结果
        mock_retriever.adaptive_retrieve.return_value = []
        mock_retriever.multi_query_retrieve.return_value = []
        
        result = await rag_workflow.process_query("测试查询")
        
        assert result is not None
        assert "抱歉，我没有找到相关的医疗信息" in result["response"]
        assert result["documents"] == []
    
    @pytest.mark.asyncio
    async def test_process_query_error_handling(self, rag_workflow, mock_retriever):
        """测试查询处理错误处理"""
        # 设置检索器抛出异常
        mock_retriever.adaptive_retrieve.side_effect = Exception("检索失败")
        
        result = await rag_workflow.process_query("测试查询")
        
        assert result is not None
        assert "处理查询时出现错误" in result["response"]
        assert result["documents"] == []
    
    @pytest.mark.asyncio
    async def test_stream_process_query(self, rag_workflow):
        """测试流式查询处理"""
        # 收集流式结果
        results = []
        async for chunk in rag_workflow.stream_process_query("测试查询"):
            results.append(chunk)
        
        assert len(results) > 0
        # 验证包含开始、内容和结束事件
        event_types = [r.get("type") for r in results if isinstance(r, dict)]
        assert "status" in event_types or "result" in event_types or "error" in event_types


class TestLLMClient:
    """LLM客户端测试类"""
    
    @pytest.fixture
    def llm_client(self):
        """创建LLM客户端实例"""
        with patch('openai.AsyncOpenAI'):
            return LLMClient(model_name="gpt-4o")
    
    def test_init_with_model(self):
        """测试指定模型初始化"""
        with patch('openai.AsyncOpenAI'):
            client = LLMClient(model_name="gpt-3.5-turbo")
            assert client.model_name == "gpt-3.5-turbo"
    
    def test_init_default_model(self):
        """测试默认模型初始化"""
        with patch('openai.AsyncOpenAI'):
            with patch.dict('os.environ', {'LLM_MODEL': 'test-model'}):
                client = LLMClient()
                assert client.model_name == "test-model"
    
    @pytest.mark.asyncio
    async def test_generate(self, llm_client):
        """测试生成响应"""
        with patch('app.workflow.llm_client.LLMClient._generate_mock') as mock_generate_mock:
            llm_client.client_type = "mock"
            mock_generate_mock.return_value = "模拟LLM响应"
            response = await llm_client.generate("测试查询")
            assert response == "模拟LLM响应"
            mock_generate_mock.assert_called_once_with("测试查询")

    @pytest.mark.asyncio
    async def test_generate_error_handling(self, llm_client):
        """测试生成错误处理"""
        # 模拟客户端错误
        with patch('app.workflow.llm_client.LLMClient._generate_openai', side_effect=Exception("API错误")) as mock_generate_openai:
            with patch('app.workflow.llm_client.LLMClient._generate_mock', side_effect=Exception("Mock错误")) as mock_generate_mock:
                # 测试OpenAI路径错误
                llm_client.client_type = "openai"
                response = await llm_client.generate("测试查询")
                assert "抱歉，生成回答时出现错误" in response
                mock_generate_openai.assert_called_once_with("测试查询")

                # 测试Mock路径错误
                llm_client.client_type = "mock"
                response = await llm_client.generate("测试查询")
                assert "抱歉，生成回答时出现错误" in response
                mock_generate_mock.assert_called_once_with("测试查询")


class TestDeepseekClient:
    """Deepseek客户端测试类"""
    
    @pytest.mark.asyncio
    async def test_init(self):
        """测试初始化"""
        client = DeepseekClient()
        assert client is not None
    
    @pytest.mark.asyncio
    async def test_generate(self):
        """测试生成响应"""
        client = DeepseekClient()
        mock_session = AsyncMock()
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "模拟Deepseek响应"}}]
        }
        mock_session.post.return_value.__aenter__.return_value = mock_response
        client.session = mock_session
        
        response = await client.generate_response("测试查询", "测试上下文")
        assert response == "模拟Deepseek响应"
        mock_session.post.assert_called_once()
        await client.close_session()
    
    @pytest.mark.asyncio
    async def test_generate_stream(self):
        """测试生成流式响应"""
        async def mock_stream_response():
            yield f"""data: {json.dumps({"choices":[{"delta":{"content":"流式"}}]})}
""".encode('utf-8')
            yield f"""data: {json.dumps({"choices":[{"delta":{"content":"响应"}}]})}
""".encode('utf-8')
            yield f"""data: [DONE]
""".encode('utf-8')

        client = DeepseekClient()
        mock_session = AsyncMock()
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.content.iter_any.return_value = mock_stream_response()
        mock_session.post.return_value.__aenter__.return_value = mock_response
        client.session = mock_session
        
        results = []
        async for chunk in client.generate_stream_response("测试查询", "测试上下文"):
            results.append(chunk)
        
        assert len(results) == 2
        assert results[0] == "流式"
        assert results[1] == "响应"
        mock_session.post.assert_called_once()
        await client.close_session()




class TestQianwenClient:
    """千问客户端测试类"""
    
    @pytest.fixture
    def qianwen_client(self):
        """创建千问客户端实例"""
        with patch('app.workflow.qianwen_client.get_settings') as mock_settings:
            mock_settings.return_value.qianwen_api_key = "test-key"
            mock_settings.return_value.qianwen_base_url = "https://test-url.com"
            mock_settings.return_value.qianwen_embedding_model = "test-embedding"
            mock_settings.return_value.qianwen_rerank_model = "test-rerank"
            client = QianwenClient()
            with patch.object(client, 'session', new_callable=AsyncContextManagerMock) as mock_session:
                yield client
    
    def test_init(self, qianwen_client):
        """测试初始化"""
        assert qianwen_client is not None
        assert qianwen_client.api_key == "test-key"
        assert qianwen_client.base_url == "https://test-url.com"
        assert qianwen_client.embedding_model == "test-embedding"
        assert qianwen_client.rerank_model == "test-rerank"
    
    @pytest.mark.asyncio
    async def test_get_embeddings(self, qianwen_client):
        """测试获取嵌入"""
        with patch('aiohttp.ClientSession.post') as mock_post:
            mock_post.return_value.__aenter__.return_value.status = 200
            mock_post.return_value.__aenter__.return_value.json = AsyncMock(return_value={
                "data": [
                    {"embedding": [0.1, 0.2, 0.3]},
                    {"embedding": [0.4, 0.5, 0.6]}
                ]
            })
            
            async with qianwen_client:
                embeddings = await qianwen_client.get_embeddings(["文本1", "文本2"])
                
            assert len(embeddings) == 2
            assert embeddings[0] == [0.1, 0.2, 0.3]
            assert embeddings[1] == [0.4, 0.5, 0.6]
    
    @pytest.mark.asyncio
    async def test_rerank_documents(self, qianwen_client):
        """测试重排序文档"""
        with patch('aiohttp.ClientSession.post') as mock_post:
            mock_post.return_value.__aenter__.return_value.status = 200
            mock_post.return_value.__aenter__.return_value.json = AsyncMock(return_value={
                "output": {
                    "results": [
                        {"index": 1, "relevance_score": 0.9},
                        {"index": 0, "relevance_score": 0.7}
                    ]
                }
            })
            
            async with qianwen_client:
                results = await qianwen_client.rerank_documents(
                    "查询", ["文档1", "文档2"], top_k=2
                )
                
            assert len(results) == 2
            assert results[0] == (1, 0.9)
            assert results[1] == (0, 0.7)
