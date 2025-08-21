#!/usr/bin/env python3
"""
医疗RAG系统启动脚本
"""

import os
import sys
import uvicorn
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

def main():
    """主函数"""
    # 设置环境变量
    os.environ.setdefault("PYTHONPATH", os.getcwd())
    
    # 获取配置
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", 8001))
    debug = os.getenv("DEBUG", "true").lower() == "true"
    
    print(f"启动医疗RAG系统...")
    print(f"服务地址: http://{host}:{port}")
    print(f"调试模式: {debug}")
    print(f"API文档: http://{host}:{port}/docs")
    
    # 启动服务
    uvicorn.run(
        "app.main:app",
        host=host,
        port=port,
        reload=debug,
        log_level="info" if not debug else "debug"
    )

if __name__ == "__main__":
    main()