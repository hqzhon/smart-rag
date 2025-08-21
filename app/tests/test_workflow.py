"""工作流模块测试"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from typing import Dict, Any, List

from app.workflow.enhanced_rag_workflow import EnhancedRAGWorkflow
from app.workflow.rag_graph import RAGWorkflow
from app.workflow.llm_client import LLMClient
from app.workflow.deepseek_client import DeepseekClient
from app.workflow.qianwen_client import QianwenClient


class TestEnhancedRAGWorkflow:
    """增强RAG工作流测试类"""
    
    @pytest.fixture
    def mock_components(self):
        """模拟组件"""
        retriever = Mock()
        reranker = Mock()
        query_transformer = Mock()
        deepseek_client = Mock()
        qianwen_client = Mock()
        db_manager = Mock()
        
        # 设置默认返回值
        retriever.adaptive_retrieve = AsyncMock(return_value=[
            {"content": "高血压是一种常见的心血管疾病", "metadata": {"source": "医学百科"}}
        ])
        retriever.multi_query_retrieve = AsyncMock(return_value=[
            {"content": "高血压的症状包括头痛、头晕", "metadata": {"source": "医学指南"}}
        ])
        reranker.rerank = AsyncMock(return_value=[
            {"content": "高血压是一种常见的心血管疾病", "metadata": {"source": "医学百科"}, "score": 0.9}
        ])
        query_transformer.expand_query = Mock(return_value=["高血压症状", "高血压治疗", "高血压预防"])
        query_transformer.rewrite_query = Mock(return_value="什么是高血压疾病？")
        deepseek_client.generate_response = AsyncMock(return_value="高血压是一种常见的心血管疾病，需要及时治疗。")
        qianwen_client.rerank_documents = AsyncMock(return_value=[(0, 0.9)])
        db_manager.save_chat_history = AsyncMock(return_value=None)
        
        return retriever, reranker, query_transformer, deepseek_client, qianwen_client, db_manager
    
    @pytest.fixture
    def enhanced_workflow(self, mock_components):
        """创建增强RAG工作流实例"""
        from app.workflow.enhanced_rag_workflow import EnhancedRAGWorkflow
        retriever, reranker, query_transformer, deepseek_client, qianwen_client, db_manager = mock_components
        
        workflow = EnhancedRAGWorkflow()
        # 注入模拟组件
        workflow.retriever = retriever
        workflow.reranker = reranker
        workflow.query_transformer = query_transformer
        workflow.deepseek_client = deepseek_client
        workflow.qianwen_client = qianwen_client
        workflow.db_manager = db_manager
        
        return workflow
    
    def test_init(self):
        """测试初始化"""
        from app.workflow.enhanced_rag_workflow import EnhancedRAGWorkflow
        workflow = EnhancedRAGWorkflow()
        assert workflow is not None
        assert hasattr(workflow, 'retriever')
        assert hasattr(workflow, 'reranker')
        assert hasattr(workflow, 'query_transformer')
    
    @pytest.mark.asyncio
    async def test_process_query_empty(self, enhanced_workflow):
        """测试空查询处理"""
        result = await enhanced_workflow.process_query("")
        assert result is not None
        assert "query" in result
        assert "response" in result
        assert "documents" in result
        assert "请输入有效的查询" in result["response"]
    
    @pytest.mark.asyncio
    async def test_process_query_valid(self, enhanced_workflow, mock_components):
        """测试有效查询处理"""
        retriever, reranker, query_transformer, deepseek_client, qianwen_client, db_manager = mock_components
        
        result = await enhanced_workflow.process_query("什么是高血压？")
        
        assert result is not None
        assert "query" in result
        assert "response" in result
        assert "documents" in result
        
        # 验证组件调用
        query_transformer.expand_query.assert_called_once()
        query_transformer.rewrite_query.assert_called_once()
        retriever.adaptive_retrieve.assert_called_once()
        qianwen_client.rerank_documents.assert_called_once()
        deepseek_client.generate_response.assert_called_once()
        db_manager.save_chat_history.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_process_query_multi_query_mode(self, enhanced_workflow, mock_components):
        """测试多查询模式处理"""
        retriever, reranker, query_transformer, deepseek_client, qianwen_client, db_manager = mock_components
        
        # 设置多查询扩展返回多个查询
        query_transformer.expand_query.return_value = ["查询1", "查询2", "查询3"]
        
        result = await enhanced_workflow.process_query("什么是高血压？", use_multi_query=True)
        
        assert result is not None
        assert "query" in result
        assert "response" in result
        assert "documents" in result
        
        # 验证使用了多查询检索
        retriever.multi_query_retrieve.assert_called_once()
        query_transformer.expand_query.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_process_query_no_documents(self, enhanced_workflow, mock_components):
        """测试无文档检索结果"""
        retriever, reranker, query_transformer, deepseek_client, qianwen_client, db_manager = mock_components
        
        # 设置检索返回空结果
        retriever.adaptive_retrieve.return_value = []
        
        result = await enhanced_workflow.process_query("什么是高血压？")
        
        assert result is not None
        assert "抱歉，我没有找到相关的医疗信息" in result["response"]
        assert result["documents"] == []
    
    @pytest.mark.asyncio
    async def test_process_query_error_handling(self, enhanced_workflow, mock_components):
        """测试查询处理错误处理"""
        retriever, reranker, query_transformer, deepseek_client, qianwen_client, db_manager = mock_components
        
        # 设置检索器抛出异常
        retriever.adaptive_retrieve.side_effect = Exception("检索失败")
        
        result = await enhanced_workflow.process_query("什么是高血压？")
        
        assert result is not None
        assert "处理查询时出现错误" in result["response"]
        assert result["documents"] == []
    
    @pytest.mark.asyncio
    async def test_stream_process_query(self, enhanced_workflow, mock_components):
        """测试流式查询处理"""
        retriever, reranker, query_transformer, deepseek_client, qianwen_client, db_manager = mock_components
        
        # 模拟流式生成
        async def mock_stream_generate(prompt, context):
            yield "流式"
            yield "回答"
            yield "内容"
        
        deepseek_client.generate_stream_response = mock_stream_generate
        
        # 收集流式结果
        results = []
        async for chunk in enhanced_workflow.stream_process_query("什么是高血压？"):
            results.append(chunk)
        
        assert len(results) > 0
        # 验证包含开始、内容和结束事件
        event_types = [r.get("type") for r in results if isinstance(r, dict)]
        assert "start" in event_types or "thinking" in event_types
        assert "end" in event_types or "complete" in event_types
    
    @pytest.mark.asyncio
    async def test_query_expansion(self, enhanced_workflow, mock_components):
        """测试查询扩展功能"""
        retriever, reranker, query_transformer, deepseek_client, qianwen_client, db_manager = mock_components
        
        # 设置查询扩展返回多个相关查询
        query_transformer.expand_query.return_value = [
            "高血压症状", "高血压治疗", "高血压预防", "高血压饮食"
        ]
        
        result = await enhanced_workflow.process_query("高血压")
        
        # 验证查询扩展被调用
        query_transformer.expand_query.assert_called_once_with("高血压")
        assert result is not None
    
    @pytest.mark.asyncio
    async def test_query_rewriting(self, enhanced_workflow, mock_components):
        """测试查询重写功能"""
        retriever, reranker, query_transformer, deepseek_client, qianwen_client, db_manager = mock_components
        
        # 设置查询重写
        query_transformer.rewrite_query.return_value = "什么是高血压疾病及其症状？"
        
        result = await enhanced_workflow.process_query("高血压是什么")
        
        # 验证查询重写被调用
        query_transformer.rewrite_query.assert_called_once_with("高血压是什么")
        assert result is not None
    
    @pytest.mark.asyncio
    async def test_document_reranking(self, enhanced_workflow, mock_components):
        """测试文档重排序功能"""
        retriever, reranker, query_transformer, deepseek_client, qianwen_client, db_manager = mock_components
        
        # 设置检索返回多个文档
        retriever.adaptive_retrieve.return_value = [
            {"content": "文档1", "metadata": {"source": "来源1"}},
            {"content": "文档2", "metadata": {"source": "来源2"}},
            {"content": "文档3", "metadata": {"source": "来源3"}}
        ]
        
        # 设置重排序结果
        qianwen_client.rerank_documents.return_value = [(2, 0.9), (0, 0.8), (1, 0.7)]
        
        result = await enhanced_workflow.process_query("什么是高血压？")
        
        # 验证重排序被调用
        qianwen_client.rerank_documents.assert_called_once()
        assert result is not None
    
    @pytest.mark.asyncio
    async def test_context_building(self, enhanced_workflow, mock_components):
        """测试上下文构建功能"""
        retriever, reranker, query_transformer, deepseek_client, qianwen_client, db_manager = mock_components
        
        # 设置检索返回的文档
        retriever.adaptive_retrieve.return_value = [
            {"content": "高血压是一种常见疾病", "metadata": {"source": "医学百科", "title": "高血压概述"}},
            {"content": "高血压的症状包括头痛", "metadata": {"source": "医学指南", "title": "高血压症状"}}
        ]
        
        result = await enhanced_workflow.process_query("什么是高血压？")
        
        # 验证Deepseek客户端被调用时传入了正确的上下文
        deepseek_client.generate_response.assert_called_once()
        call_args = deepseek_client.generate_response.call_args
        assert len(call_args) >= 2  # prompt和context参数
        context = call_args[0][1]  # 第二个参数是context
        assert "高血压是一种常见疾病" in context
        assert "高血压的症状包括头痛" in context
    
    @pytest.mark.asyncio
    async def test_reference_extraction(self, enhanced_workflow, mock_components):
        """测试参考文档提取功能"""
        retriever, reranker, query_transformer, deepseek_client, qianwen_client, db_manager = mock_components
        
        # 设置检索返回的文档
        retriever.adaptive_retrieve.return_value = [
            {"content": "高血压相关内容", "metadata": {"source": "医学百科", "title": "高血压", "url": "http://example.com/1"}},
            {"content": "治疗方法", "metadata": {"source": "医学指南", "title": "治疗", "url": "http://example.com/2"}}
        ]
        
        result = await enhanced_workflow.process_query("什么是高血压？")
        
        # 验证返回结果包含参考文档
        assert "documents" in result
        assert len(result["documents"]) > 0
        
        # 验证文档包含必要的元数据
        for doc in result["documents"]:
            assert "content" in doc
            assert "metadata" in doc
            assert "source" in doc["metadata"]
    
    @pytest.mark.asyncio
    async def test_chat_history_saving(self, enhanced_workflow, mock_components):
        """测试聊天历史保存功能"""
        retriever, reranker, query_transformer, deepseek_client, qianwen_client, db_manager = mock_components
        
        session_id = "test-session-123"
        result = await enhanced_workflow.process_query("什么是高血压？", session_id=session_id)
        
        # 验证聊天历史被保存
        db_manager.save_chat_history.assert_called_once()
        call_args = db_manager.save_chat_history.call_args[1]  # 关键字参数
        assert call_args["session_id"] == session_id
        assert call_args["user_message"] == "什么是高血压？"
        assert "assistant_message" in call_args
    
    @pytest.mark.asyncio
    async def test_adaptive_retrieval_fallback(self, enhanced_workflow, mock_components):
        """测试自适应检索回退机制"""
        retriever, reranker, query_transformer, deepseek_client, qianwen_client, db_manager = mock_components
        
        # 设置自适应检索失败，回退到多查询检索
        retriever.adaptive_retrieve.side_effect = Exception("自适应检索失败")
        retriever.multi_query_retrieve.return_value = [
            {"content": "回退检索结果", "metadata": {"source": "备用来源"}}
        ]
        
        result = await enhanced_workflow.process_query("什么是高血压？")
        
        # 验证回退到多查询检索
        retriever.multi_query_retrieve.assert_called_once()
        assert result is not None
        assert len(result["documents"]) > 0


class TestRAGWorkflow:
    """RAG工作流测试类"""
    
    @pytest.fixture
    def mock_components(self):
        """创建模拟组件"""
        retriever = Mock()
        reranker = Mock()
        query_transformer = Mock()
        llm_client = Mock()
        
        retriever.retrieve = AsyncMock(return_value=[
            {"content": "测试内容", "score": 0.9}
        ])
        retriever.adaptive_retrieve = AsyncMock(return_value=[
            {"page_content": "测试内容", "score": 0.9, "metadata": {"source": "test.pdf"}}
        ])
        retriever.multi_query_retrieve = Mock(return_value=[
            {"page_content": "多查询内容", "score": 0.85, "metadata": {"source": "test2.pdf"}}
        ])
        reranker.rerank = AsyncMock(return_value=[
            {"page_content": "测试内容", "score": 0.95, "metadata": {"source": "test.pdf"}}
        ])
        query_transformer.expand_query = Mock(return_value=["扩展查询1", "扩展查询2"])
        query_transformer.rewrite_query = Mock(return_value="重写查询")
        llm_client.generate = AsyncMock(return_value="生成的回答")
        
        return retriever, reranker, query_transformer, llm_client
    
    @pytest.fixture
    def rag_workflow(self, mock_components):
        """创建RAG工作流实例"""
        retriever, reranker, query_transformer, llm_client = mock_components
        return RAGWorkflow(retriever, reranker, query_transformer, llm_client)
    
    def test_init(self, rag_workflow):
        """测试初始化"""
        assert rag_workflow is not None
        assert hasattr(rag_workflow, 'retriever')
        assert hasattr(rag_workflow, 'reranker')
        assert hasattr(rag_workflow, 'query_transformer')
        assert hasattr(rag_workflow, 'llm_client')
    
    @pytest.mark.asyncio
    async def test_process_query(self, rag_workflow, mock_components):
        """测试查询处理"""
        retriever, reranker, query_transformer, llm_client = mock_components
        
        result = await rag_workflow.process_query("测试查询")
        
        assert result is not None
        assert "query" in result
        assert "response" in result
        assert "documents" in result
        
        # 验证组件调用
        retriever.adaptive_retrieve.assert_called_once()
        reranker.rerank.assert_called_once()
        query_transformer.expand_query.assert_called_once()
        query_transformer.rewrite_query.assert_called_once()
        llm_client.generate.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_process_query_multi_query_retrieval(self, rag_workflow, mock_components):
        """测试多查询检索处理"""
        retriever, reranker, query_transformer, llm_client = mock_components
        
        # 设置多查询扩展
        query_transformer.expand_query.return_value = ["查询1", "查询2", "查询3"]
        
        result = await rag_workflow.process_query("测试查询")
        
        assert result is not None
        assert "query" in result
        assert "response" in result
        assert "documents" in result
        
        # 验证使用了多查询检索
        retriever.multi_query_retrieve.assert_called_once()
        query_transformer.expand_query.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_process_query_no_documents(self, rag_workflow, mock_components):
        """测试无文档检索结果"""
        retriever, reranker, query_transformer, llm_client = mock_components
        
        # 设置检索返回空结果
        retriever.adaptive_retrieve.return_value = []
        
        result = await rag_workflow.process_query("测试查询")
        
        assert result is not None
        assert "抱歉，我没有找到相关的医疗信息" in result["response"]
        assert result["documents"] == []
    
    @pytest.mark.asyncio
    async def test_process_query_error_handling(self, rag_workflow, mock_components):
        """测试查询处理错误处理"""
        retriever, reranker, query_transformer, llm_client = mock_components
        
        # 设置检索器抛出异常
        retriever.adaptive_retrieve.side_effect = Exception("检索失败")
        
        result = await rag_workflow.process_query("测试查询")
        
        assert result is not None
        assert "处理查询时出现错误" in result["response"]
        assert result["documents"] == []
    
    @pytest.mark.asyncio
    async def test_stream_process_query(self, rag_workflow, mock_components):
        """测试流式查询处理"""
        retriever, reranker, query_transformer, llm_client = mock_components
        
        # 模拟流式生成
        async def mock_stream_generate(prompt, **kwargs):
            yield "流式"
            yield "回答"
            yield "内容"
        
        llm_client.stream_generate = mock_stream_generate
        
        # 收集流式结果
        results = []
        async for chunk in rag_workflow.stream_process_query("测试查询"):
            results.append(chunk)
        
        assert len(results) > 0
        # 验证包含开始、内容和结束事件
        event_types = [r.get("type") for r in results if isinstance(r, dict)]
        assert "start" in event_types or "thinking" in event_types
        assert "end" in event_types or "complete" in event_types


class TestLLMClient:
    """LLM客户端测试类"""
    
    @pytest.fixture
    def llm_client(self):
        """创建LLM客户端实例"""
        from app.workflow.llm_client import LLMClient
        return LLMClient(model_name="gpt-4o")
    
    def test_init_with_model(self):
        """测试指定模型初始化"""
        from app.workflow.llm_client import LLMClient
        client = LLMClient(model_name="gpt-3.5-turbo")
        assert client.model_name == "gpt-3.5-turbo"
    
    def test_init_default_model(self):
        """测试默认模型初始化"""
        from app.workflow.llm_client import LLMClient
        with patch.dict('os.environ', {'LLM_MODEL': 'test-model'}):
            client = LLMClient()
            assert client.model_name == "test-model"
    
    @pytest.mark.asyncio
    async def test_generate_mock_response(self, llm_client):
        """测试模拟生成回答"""
        # 由于没有真实API密钥，应该使用模拟客户端
        response = await llm_client.generate("什么是高血压？")
        assert isinstance(response, str)
        assert len(response) > 0
    
    @pytest.mark.asyncio
    async def test_generate_with_parameters(self, llm_client):
        """测试带参数的生成"""
        response = await llm_client.generate(
            "什么是糖尿病？",
            temperature=0.5,
            max_tokens=500
        )
        assert isinstance(response, str)
        assert len(response) > 0
    
    @pytest.mark.asyncio
    async def test_generate_error_handling(self, llm_client):
        """测试生成错误处理"""
        # 模拟客户端错误
        with patch.object(llm_client, '_generate_mock', side_effect=Exception("API错误")):
            response = await llm_client.generate("测试查询")
            assert "抱歉，生成回答时出现错误" in response
    
    @pytest.mark.asyncio
    async def test_stream_generate(self, llm_client):
        """测试流式生成"""
        chunks = []
        async for chunk in llm_client.stream_generate("什么是心脏病？"):
            chunks.append(chunk)
        
        assert len(chunks) > 0
        # 验证所有块都是字符串
        for chunk in chunks:
            assert isinstance(chunk, str)


class TestDeepseekClient:
    """Deepseek客户端测试类"""
    
    @pytest.fixture
    def mock_settings(self):
        """模拟设置"""
        settings = Mock()
        settings.deepseek_api_key = "test-api-key"
        settings.deepseek_base_url = "https://api.deepseek.com"
        settings.deepseek_model = "deepseek-chat"
        return settings
    
    @pytest.fixture
    def deepseek_client(self, mock_settings):
        """创建Deepseek客户端实例"""
        from app.workflow.deepseek_client import DeepseekClient
        with patch('app.workflow.deepseek_client.get_settings', return_value=mock_settings):
            return DeepseekClient()
    
    def test_init_success(self, deepseek_client):
        """测试成功初始化"""
        assert deepseek_client.api_key == "test-api-key"
        assert deepseek_client.base_url == "https://api.deepseek.com"
        assert deepseek_client.model == "deepseek-chat"
    
    def test_init_missing_api_key(self):
        """测试缺少API密钥"""
        from app.workflow.deepseek_client import DeepseekClient
        mock_settings = Mock()
        mock_settings.deepseek_api_key = None
        mock_settings.deepseek_base_url = "https://api.deepseek.com"
        mock_settings.deepseek_model = "deepseek-chat"
        
        with patch('app.workflow.deepseek_client.get_settings', return_value=mock_settings):
            with pytest.raises(ValueError, match="DEEPSEEK_API_KEY未设置"):
                DeepseekClient()
    
    @pytest.mark.asyncio
    async def test_generate_response_success(self, deepseek_client):
        """测试成功生成回答"""
        mock_response = {
            "choices": [{
                "message": {
                    "content": "这是Deepseek的回答"
                }
            }]
        }
        
        with patch.object(deepseek_client, 'chat_completion', return_value=mock_response):
            response = await deepseek_client.generate_response("测试提示", "测试上下文")
            assert response == "这是Deepseek的回答"
    
    @pytest.mark.asyncio
    async def test_generate_response_error(self, deepseek_client):
        """测试生成回答错误处理"""
        with patch.object(deepseek_client, 'chat_completion', side_effect=Exception("API错误")):
            with pytest.raises(Exception, match="API错误"):
                await deepseek_client.generate_response("测试提示", "测试上下文")
    
    @pytest.mark.asyncio
    async def test_stream_response(self, deepseek_client):
        """测试流式回答生成"""
        async def mock_stream():
            yield {"choices": [{"delta": {"content": "流式"}}]}
            yield {"choices": [{"delta": {"content": "回答"}}]}
            yield {"choices": [{"delta": {}}]}  # 结束标记
        
        with patch.object(deepseek_client, 'stream_chat_completion', return_value=mock_stream()):
            chunks = []
            async for chunk in deepseek_client.generate_stream_response("测试提示", "测试上下文"):
                chunks.append(chunk)
            
            assert len(chunks) == 2
            assert chunks[0] == "流式"
            assert chunks[1] == "回答"


class TestQianwenClient:
    """千问客户端测试类"""
    
    @pytest.fixture
    def mock_settings(self):
        """模拟设置"""
        settings = Mock()
        settings.qianwen_api_key = "test-api-key"
        settings.qianwen_base_url = "https://dashscope.aliyuncs.com"
        settings.qianwen_embedding_model = "text-embedding-v3"
        settings.qianwen_rerank_model = "gte-rerank"
        return settings
    
    @pytest.fixture
    def qianwen_client(self, mock_settings):
        """创建千问客户端实例"""
        from app.workflow.qianwen_client import QianwenClient
        with patch('app.workflow.qianwen_client.get_settings', return_value=mock_settings):
            return QianwenClient()
    
    def test_init_success(self, qianwen_client):
        """测试成功初始化"""
        assert qianwen_client.api_key == "test-api-key"
        assert qianwen_client.base_url == "https://dashscope.aliyuncs.com"
        assert qianwen_client.embedding_model == "text-embedding-v3"
        assert qianwen_client.rerank_model == "gte-rerank"
    
    def test_init_missing_api_key(self):
        """测试缺少API密钥"""
        from app.workflow.qianwen_client import QianwenClient
        mock_settings = Mock()
        mock_settings.qianwen_api_key = None
        mock_settings.qianwen_base_url = "https://dashscope.aliyuncs.com"
        
        with patch('app.workflow.qianwen_client.get_settings', return_value=mock_settings):
            with pytest.raises(ValueError, match="QIANWEN_API_KEY未设置"):
                QianwenClient()
    
    @pytest.mark.asyncio
    async def test_get_embeddings_success(self, qianwen_client):
        """测试成功获取嵌入"""
        mock_response = {
            "data": [
                {"embedding": [0.1, 0.2, 0.3]},
                {"embedding": [0.4, 0.5, 0.6]}
            ]
        }
        
        with patch('aiohttp.ClientSession.post') as mock_post:
            mock_post.return_value.__aenter__.return_value.status = 200
            mock_post.return_value.__aenter__.return_value.json.return_value = mock_response
            
            async with qianwen_client:
                embeddings = await qianwen_client.get_embeddings(["文本1", "文本2"])
                
            assert len(embeddings) == 2
            assert embeddings[0] == [0.1, 0.2, 0.3]
            assert embeddings[1] == [0.4, 0.5, 0.6]
    
    @pytest.mark.asyncio
    async def test_get_embeddings_empty_input(self, qianwen_client):
        """测试空输入获取嵌入"""
        async with qianwen_client:
            embeddings = await qianwen_client.get_embeddings([])
            assert embeddings == []
    
    @pytest.mark.asyncio
    async def test_rerank_documents_success(self, qianwen_client):
        """测试成功重排序文档"""
        mock_response = {
            "results": [
                {"index": 1, "relevance_score": 0.9},
                {"index": 0, "relevance_score": 0.7}
            ]
        }
        
        with patch('aiohttp.ClientSession.post') as mock_post:
            mock_post.return_value.__aenter__.return_value.status = 200
            mock_post.return_value.__aenter__.return_value.json.return_value = mock_response
            
            async with qianwen_client:
                results = await qianwen_client.rerank_documents(
                    "查询", ["文档1", "文档2"], top_k=2
                )
                
            assert len(results) == 2
            assert results[0] == (1, 0.9)
            assert results[1] == (0, 0.7)
    
    @pytest.mark.asyncio
    async def test_batch_embeddings(self, qianwen_client):
        """测试批量获取嵌入"""
        texts = [f"文本{i}" for i in range(25)]  # 超过批量大小
        
        mock_response = {
            "data": [{"embedding": [0.1, 0.2]} for _ in range(10)]
        }
        
        with patch.object(qianwen_client, 'get_embeddings', return_value=[[0.1, 0.2]] * 10) as mock_get:
            async with qianwen_client:
                embeddings = await qianwen_client.batch_embeddings(texts, batch_size=10)
                
            # 应该调用3次（25个文本，每批10个）
            assert mock_get.call_count == 3
            assert len(embeddings) == 25
    
    @pytest.mark.asyncio
    async def test_health_check_success(self, qianwen_client):
        """测试健康检查成功"""
        with patch.object(qianwen_client, 'get_single_embedding', return_value=[0.1, 0.2]):
            async with qianwen_client:
                is_healthy = await qianwen_client.health_check()
                assert is_healthy is True
    
    @pytest.mark.asyncio
    async def test_health_check_failure(self, qianwen_client):
        """测试健康检查失败"""
        with patch.object(qianwen_client, 'get_single_embedding', side_effect=Exception("API错误")):
            async with qianwen_client:
                is_healthy = await qianwen_client.health_check()
                assert is_healthy is False


class TestLLMClient:
    """LLM客户端测试类"""
    
    @pytest.fixture
    def llm_client(self):
        """创建LLM客户端实例"""
        return LLMClient()
    
    def test_init(self, llm_client):
        """测试初始化"""
        assert llm_client is not None
        assert hasattr(llm_client, 'client')
    
    @pytest.mark.asyncio
    async def test_generate_empty_prompt(self, llm_client):
        """测试空提示生成"""
        with pytest.raises(ValueError, match="提示不能为空"):
            await llm_client.generate("")
    
    @pytest.mark.asyncio
    async def test_generate_valid_prompt(self, llm_client):
        """测试有效提示生成"""
        with patch.object(llm_client.client, 'chat') as mock_chat:
            mock_chat.completions.create = AsyncMock(return_value=Mock(
                choices=[Mock(message=Mock(content="生成的回答"))]
            ))
            
            result = await llm_client.generate("测试提示")
            
            assert result is not None
            assert isinstance(result, str)
    
    @pytest.mark.asyncio
    async def test_stream_generate(self, llm_client):
        """测试流式生成"""
        with patch.object(llm_client.client, 'chat') as mock_chat:
            # 模拟流式响应
            async def mock_stream():
                yield Mock(choices=[Mock(delta=Mock(content="流式"))])
                yield Mock(choices=[Mock(delta=Mock(content="回答"))])
            
            mock_chat.completions.create = AsyncMock(return_value=mock_stream())
            
            result = []
            async for chunk in llm_client.stream_generate("测试提示"):
                result.append(chunk)
            
            assert len(result) > 0


class TestDeepseekClient:
    """Deepseek客户端测试类"""
    
    @pytest.fixture
    def deepseek_client(self):
        """创建Deepseek客户端实例"""
        with patch('app.workflow.deepseek_client.OpenAI') as mock_openai:
            mock_openai.return_value = Mock()
            return DeepseekClient(api_key="test-key")
    
    def test_init(self, deepseek_client):
        """测试初始化"""
        assert deepseek_client is not None
        assert hasattr(deepseek_client, 'client')
    
    @pytest.mark.asyncio
    async def test_generate(self, deepseek_client):
        """测试生成"""
        with patch.object(deepseek_client.client.chat.completions, 'create') as mock_create:
            mock_create.return_value = Mock(
                choices=[Mock(message=Mock(content="Deepseek生成的回答"))]
            )
            
            result = await deepseek_client.generate("测试提示")
            
            assert result is not None
            assert isinstance(result, str)
            assert "Deepseek生成的回答" in result


class TestQianwenClient:
    """千问客户端测试类"""
    
    @pytest.fixture
    def qianwen_client(self):
        """创建千问客户端实例"""
        with patch('app.workflow.qianwen_client.dashscope') as mock_dashscope:
            mock_dashscope.Generation = Mock()
            return QianwenClient(api_key="test-key")
    
    def test_init(self, qianwen_client):
        """测试初始化"""
        assert qianwen_client is not None
        assert hasattr(qianwen_client, 'api_key')
    
    @pytest.mark.asyncio
    async def test_generate(self, qianwen_client):
        """测试生成"""
        with patch('app.workflow.qianwen_client.dashscope.Generation.call') as mock_call:
            mock_call.return_value = {
                'status_code': 200,
                'output': {
                    'text': '千问生成的回答'
                }
            }
            
            result = await qianwen_client.generate("测试提示")
            
            assert result is not None
            assert isinstance(result, str)
            assert "千问生成的回答" in result
    
    @pytest.mark.asyncio
    async def test_generate_error(self, qianwen_client):
        """测试生成错误处理"""
        with patch('app.workflow.qianwen_client.dashscope.Generation.call') as mock_call:
            mock_call.return_value = {
                'status_code': 400,
                'message': '请求错误'
            }
            
            with pytest.raises(Exception, match="千问API调用失败"):
                await qianwen_client.generate("测试提示")