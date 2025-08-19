#!/usr/bin/env python3
"""
医疗RAG系统测试脚本
"""

import os
import sys
import json
import asyncio
import argparse
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.processors.pdf_processor import PDFProcessor
from app.processors.document_processor import DocumentProcessor
from app.embeddings.embeddings import get_embeddings
from app.embeddings.text_splitter import MedicalTextSplitter
from app.storage.vector_store import VectorStore
from app.retrieval.retriever import HybridRetriever
from app.retrieval.reranker import CrossEncoderReranker
from app.retrieval.query_transformer import QueryTransformer
from app.workflow.rag_graph import RAGWorkflow
from app.workflow.llm_client import LLMClient
from app.utils.logger import setup_logger

logger = setup_logger(__name__)


async def test_document_processing(pdf_path):
    """测试文档处理"""
    logger.info(f"测试文档处理: {pdf_path}")
    
    try:
        # 处理单个PDF
        processor = PDFProcessor(pdf_path)
        result = processor.process()
        
        logger.info(f"文档处理成功: {len(result['text'])} 字符")
        logger.info(f"提取了 {len(result.get('tables', []))} 个表格")
        logger.info(f"提取了 {len(result.get('references', []))} 个参考文献")
        
        return result
    except Exception as e:
        logger.error(f"文档处理失败: {str(e)}")
        return None


async def test_embedding_and_storage(document):
    """测试嵌入和存储"""
    logger.info("测试嵌入和存储")
    
    try:
        # 文本分块
        splitter = MedicalTextSplitter(chunk_size=500, chunk_overlap=100)
        chunks = splitter.split_text(document["text"])
        
        logger.info(f"文本分块成功: {len(chunks)} 个块")
        
        # 创建嵌入模型
        embedding_model = get_embeddings()
        
        # 创建向量存储
        vector_store = VectorStore(embedding_model)
        
        # 准备文档
        documents = []
        for i, chunk in enumerate(chunks):
            documents.append({
                "content": chunk,
                "metadata": {
                    "source": document["filename"],
                    "chunk_id": i
                }
            })
        
        # 添加到向量存储
        vector_store.add_documents(documents)
        
        logger.info("嵌入和存储成功")
        
        return vector_store, documents
    except Exception as e:
        logger.error(f"嵌入和存储失败: {str(e)}")
        return None, None


async def test_retrieval(vector_store, documents, query):
    """测试检索"""
    logger.info(f"测试检索: {query}")
    
    try:
        # 创建检索器
        retriever = HybridRetriever(vector_store, documents)
        
        # 检索
        results = retriever.adaptive_retrieve(query, top_k=5)
        
        logger.info(f"检索成功: {len(results)} 个结果")
        
        # 打印检索结果
        for i, doc in enumerate(results):
            logger.info(f"结果 {i+1}: {doc['page_content'][:100]}...")
        
        return retriever, results
    except Exception as e:
        logger.error(f"检索失败: {str(e)}")
        return None, None


async def test_reranking(retriever, results, query):
    """测试重排序"""
    logger.info(f"测试重排序: {query}")
    
    try:
        # 创建重排序器
        reranker = CrossEncoderReranker()
        
        # 重排序
        reranked_results = reranker.rerank(query, results, top_k=3)
        
        logger.info(f"重排序成功: {len(reranked_results)} 个结果")
        
        # 打印重排序结果
        for i, doc in enumerate(reranked_results):
            logger.info(f"重排序结果 {i+1}: {doc['page_content'][:100]}...")
        
        return reranker, reranked_results
    except Exception as e:
        logger.error(f"重排序失败: {str(e)}")
        return None, None


async def test_query_transformation(query):
    """测试查询转换"""
    logger.info(f"测试查询转换: {query}")
    
    try:
        # 创建查询转换器
        query_transformer = QueryTransformer()
        
        # 扩展查询
        expanded_queries = query_transformer.expand_query(query)
        
        logger.info(f"查询扩展成功: {len(expanded_queries)} 个查询")
        logger.info(f"扩展查询: {expanded_queries}")
        
        # 重写查询
        rewritten_query = query_transformer.rewrite_query(query)
        
        logger.info(f"查询重写成功: {query} -> {rewritten_query}")
        
        return query_transformer
    except Exception as e:
        logger.error(f"查询转换失败: {str(e)}")
        return None


async def test_rag_workflow(retriever, reranker, query_transformer, query):
    """测试RAG工作流"""
    logger.info(f"测试RAG工作流: {query}")
    
    try:
        # 创建LLM客户端
        llm_client = LLMClient()
        
        # 创建RAG工作流
        rag_workflow = RAGWorkflow(retriever, reranker, query_transformer, llm_client)
        
        # 处理查询
        result = await rag_workflow.process_query(query)
        
        logger.info("RAG工作流处理成功")
        logger.info(f"查询: {result['query']}")
        logger.info(f"回答: {result['response'][:200]}...")
        logger.info(f"参考文档数: {len(result['documents'])}")
        
        return result
    except Exception as e:
        logger.error(f"RAG工作流处理失败: {str(e)}")
        return None


async def run_full_test(pdf_path, query):
    """运行完整测试"""
    logger.info("开始运行完整测试")
    
    # 1. 文档处理
    document = await test_document_processing(pdf_path)
    if not document:
        return
    
    # 2. 嵌入和存储
    vector_store, documents = await test_embedding_and_storage(document)
    if not vector_store or not documents:
        return
    
    # 3. 查询转换
    query_transformer = await test_query_transformation(query)
    if not query_transformer:
        return
    
    # 4. 检索
    retriever, results = await test_retrieval(vector_store, documents, query)
    if not retriever or not results:
        return
    
    # 5. 重排序
    reranker, reranked_results = await test_reranking(retriever, results, query)
    if not reranker or not reranked_results:
        return
    
    # 6. RAG工作流
    result = await test_rag_workflow(retriever, reranker, query_transformer, query)
    if not result:
        return
    
    logger.info("完整测试成功完成")
    return result


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="医疗RAG系统测试脚本")
    parser.add_argument("--pdf", type=str, help="PDF文件路径")
    parser.add_argument("--query", type=str, default="高血压的症状有哪些？", help="测试查询")
    args = parser.parse_args()
    
    # 检查PDF文件
    if not args.pdf:
        logger.error("请提供PDF文件路径")
        return
    
    pdf_path = Path(args.pdf)
    if not pdf_path.exists():
        logger.error(f"PDF文件不存在: {pdf_path}")
        return
    
    # 运行测试
    asyncio.run(run_full_test(str(pdf_path), args.query))


if __name__ == "__main__":
    main()