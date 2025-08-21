#!/usr/bin/env python3
"""
RQ集成使用示例
演示如何使用基于Redis Queue的异步元数据处理功能

前置条件:
1. 启动Redis服务器: redis-server
2. 启动RQ Worker: python scripts/start_rq_worker.py
3. 安装依赖: pip install -r requirements.txt
"""

import os
import sys
import time
import logging
from pathlib import Path

# Add project root to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.processors.document_processor import DocumentProcessor
from redis import Redis
from rq import Queue

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def create_sample_documents(input_dir: str):
    """创建示例文档"""
    os.makedirs(input_dir, exist_ok=True)
    
    # Create sample text files
    sample_texts = [
        {
            'filename': 'medical_report_1.txt',
            'content': '''
医学报告 - 患者病历摘要

患者信息：
姓名：张三
年龄：45岁
性别：男

主诉：
患者主诉胸痛3天，伴有呼吸困难和心悸。疼痛性质为压榨性，持续时间约30分钟，休息后可缓解。

既往史：
患者有高血压病史5年，规律服用降压药物。无糖尿病、冠心病等其他慢性疾病史。

体格检查：
血压：150/90 mmHg
心率：85次/分，律齐
呼吸：20次/分
体温：36.8°C

辅助检查：
心电图：ST段轻度压低
胸部X线：心影增大
血常规：白细胞计数正常

诊断：
1. 不稳定性心绞痛
2. 高血压病2级

治疗方案：
1. 抗血小板聚集治疗
2. 调脂治疗
3. 血压控制
4. 生活方式干预
            '''
        },
        {
            'filename': 'research_paper_1.txt',
            'content': '''
人工智能在医疗诊断中的应用研究

摘要：
随着人工智能技术的快速发展，机器学习和深度学习在医疗诊断领域展现出巨大潜力。
本研究综述了AI在影像诊断、病理分析、药物发现等方面的最新进展。

关键词：人工智能，医疗诊断，机器学习，深度学习，影像分析

引言：
医疗诊断是临床医学的核心环节，准确的诊断是有效治疗的前提。传统的医疗诊断主要依赖医生的经验和专业知识，
但随着医疗数据的爆炸式增长和疾病复杂性的增加，单纯依靠人工诊断面临诸多挑战。

人工智能技术，特别是机器学习和深度学习，为医疗诊断带来了新的机遇。这些技术能够从大量医疗数据中
学习模式和规律，辅助医生进行更准确、更快速的诊断。

方法：
本研究采用系统性文献综述的方法，检索了2020-2024年间发表的相关研究论文。
主要关注以下几个方面：
1. 医学影像诊断中的AI应用
2. 病理学诊断的自动化
3. 临床决策支持系统
4. 药物发现和开发

结果：
研究表明，AI在医疗诊断领域取得了显著进展：
- 在放射学诊断中，深度学习模型的准确率已接近或超过专业医生
- 病理图像分析的自动化程度不断提高
- 临床决策支持系统帮助医生提高诊断效率
- AI加速了新药研发过程

结论：
AI技术在医疗诊断中展现出巨大潜力，但仍需要解决数据质量、模型可解释性、
监管合规等挑战。未来的发展方向包括多模态数据融合、个性化医疗、
以及人机协作的智能诊断系统。
            '''
        }
    ]
    
    for sample in sample_texts:
        file_path = os.path.join(input_dir, sample['filename'])
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(sample['content'])
        logger.info(f"创建示例文档: {file_path}")

def check_redis_connection(host='localhost', port=6379):
    """检查Redis连接"""
    try:
        redis_conn = Redis(host=host, port=port, decode_responses=True)
        redis_conn.ping()
        logger.info(f"Redis连接成功: {host}:{port}")
        return True
    except Exception as e:
        logger.error(f"Redis连接失败: {e}")
        return False

def check_queue_status(host='localhost', port=6379):
    """检查队列状态"""
    try:
        redis_conn = Redis(host=host, port=port, decode_responses=True)
        queue = Queue('metadata_queue', connection=redis_conn)
        
        logger.info(f"队列状态:")
        logger.info(f"  - 队列长度: {len(queue)}")
        logger.info(f"  - 失败任务数: {queue.failed_job_registry.count}")
        logger.info(f"  - 已完成任务数: {queue.finished_job_registry.count}")
        
        return queue
    except Exception as e:
        logger.error(f"检查队列状态失败: {e}")
        return None

def main():
    """主函数"""
    logger.info("=== RQ集成使用示例 ===")
    
    # Check Redis connection
    if not check_redis_connection():
        logger.error("请确保Redis服务器正在运行")
        return
    
    # Setup directories
    base_dir = Path(__file__).parent
    input_dir = base_dir / 'sample_input'
    output_dir = base_dir / 'sample_output'
    
    # Create sample documents
    logger.info("创建示例文档...")
    create_sample_documents(str(input_dir))
    
    # Initialize DocumentProcessor with RQ enabled
    logger.info("初始化DocumentProcessor（启用RQ）...")
    processor = DocumentProcessor(
        input_dir=str(input_dir),
        output_dir=str(output_dir),
        enable_async_metadata=True,  # 启用异步元数据处理
        redis_host='localhost',
        redis_port=6379,
        enable_cleaning=True,
        enable_terminology_standardization=True,
        enable_quality_filtering=True
    )
    
    # Check initial queue status
    logger.info("处理前的队列状态:")
    queue = check_queue_status()
    
    # Process documents
    logger.info("开始处理文档...")
    start_time = time.time()
    
    results = processor.process_all_documents()
    
    end_time = time.time()
    processing_time = end_time - start_time
    
    logger.info(f"文档处理完成，耗时: {processing_time:.2f}秒")
    logger.info(f"处理结果: {len(results)} 个文档")
    
    # Check queue status after processing
    logger.info("处理后的队列状态:")
    check_queue_status()
    
    # Display results summary
    for i, result in enumerate(results, 1):
        logger.info(f"文档 {i}:")
        logger.info(f"  - 文件: {result.get('file_path', 'Unknown')}")
        logger.info(f"  - 文档ID: {result.get('document_id', 'N/A')}")
        logger.info(f"  - 文本块数量: {len(result.get('filtered_chunks', []))}")
        
        if 'quality_stats' in result:
            stats = result['quality_stats']
            logger.info(f"  - 质量统计: {stats.get('filtered_chunks', 0)}/{stats.get('original_chunks', 0)} 块通过过滤")
    
    logger.info("\n=== 使用说明 ===")
    logger.info("1. 文档已处理完成，元数据生成任务已推送到RQ队列")
    logger.info("2. 请确保RQ Worker正在运行: python scripts/start_rq_worker.py")
    logger.info("3. 可以使用RQ Dashboard监控任务状态: rq-dashboard")
    logger.info("4. 元数据生成结果将异步处理，不会阻塞主流程")
    
    logger.info("\n示例运行完成！")

if __name__ == '__main__':
    main()