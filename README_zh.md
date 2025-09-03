# Smart RAG - 医学文献智能检索问答系统

[![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![React](https://img.shields.io/badge/react-18.0+-61dafb.svg)](https://reactjs.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-009688.svg)](https://fastapi.tiangolo.com/)

[中文版](README_zh.md) | [English Version](README.md)

🚀 **基于先进RAG技术的医学文献智能检索问答系统**

一个集成了混合检索、RRF结果融合和多模型支持的智能文档问答平台，专为医学文献处理和知识检索而设计。

## ✨ 核心亮点

- **🚀 先进RAG架构**: 采用业界领先的检索增强生成（RAG）技术，确保答案的准确性、相关性和可追溯性。
- **🧠 智能文档处理**:
  - **多模态解析**: 不仅提取文本，还能理解PDF中的表格、图片等复杂结构。
  - **双模智能分块**: 优先使用`HybridTextSplitter`进行语义分块，并保留稳定的“递归”分块作为后备，保证上下文的完整性。
- **🎯 四路混合检索**:
  - **多维度召回**: 并行执行`VECTOR`（向量语义）、`CONTENT`（全文关键词）、`SUMMARY`（摘要关键词）和`KEYWORDS`（关键词列表）四路检索，召回率和精确率最大化。
  - **RRF融合**: 采用倒数排名融合（RRF）算法，智能合并多路结果。
- **🔍 AI增强与优化**:
  - **查询转换**: 利用LLM对用户问题进行重写和扩展，更好地匹配知识库。
  - **AI重排序**: 在检索后，通过更强大的AI模型进行二次“精读”和重排序，确保最终答案基于最相关的精华内容生成。
- **💬 企业级问答体验**:
  - **流式输出**: 答案实时响应，提升用户交互体验。
  - **精准溯源**: 所有答案都提供清晰的文献来源，方便核实。
  - **高可扩展性**: 异步化、模块化的设计，易于集成新模型、新功能。

## 🚀 快速开始

### 1. 环境要求

- Python 3.9+
- Node.js 16+
- 16GB+ 内存推荐
- 100GB+ 可用存储空间

### 2. 安装依赖

```bash
# 安装基础依赖
pip install -r requirements.txt
```

### 3. 配置环境变量

复制并编辑环境变量文件：
```bash
cp .env.example .env
# 编辑 .env 文件，配置必要的参数
```

### 4. 启动后端服务

```bash
python run.py
python start_celery_worker.py  // 队列
```

后端API将在 http://localhost:8001 启动

### 5. 启动前端服务

```bash
cd frontend
npm install
npm run dev
```

前端界面将在 http://localhost:3001 启动

## 📚 详细文档

### RAG架构深度解析

为了帮助您深入理解本系统的内部工作原理，我们提供了一系列详细的组件解析文档：

- **[RAG系统架构概览](docs/RAG_architecture_overview.md)** - **建议首先阅读**，高层次地了解系统全貌。
  - **[组件详解一：智能文档处理](docs/rag_components/1_document_processing.md)**
  - **[组件详解二：查询转换与优化](docs/rag_components/2_query_transformation.md)**
  - **[组件详解三：四路召回与融合检索](docs/rag_components/3_retrieval.md)**
  - **[组件详解四：AI增强重排序](docs/rag_components/4_reranking.md)**
  - **[组件详解五：上下文构建与答案生成](docs/rag_components/5_response_generation.md)**

### 其他文档

- **[安装与配置指南](docs/installation.md)** - 详细的环境配置和安装步骤。
- **[API接口文档](docs/api.md)** - 完整的API接口文档和使用示例。
- **[系统架构](docs/architecture.md)** - 原始的技术架构、组件设计和开发指南。


---

## 🏗️ 项目结构

```
smart-rag/
├── app/                    # 应用后端代码 (FastAPI)
│   ├── api/                # API接口路由
│   ├── core/               # 核心功能 (配置, Session管理等)
│   ├── embeddings/         # 嵌入与文本分块模块
│   ├── metadata/           # 摘要、关键词等元数据生成模块
│   ├── models/             # Pydantic数据模型
│   ├── processors/         # 文档解析与处理
│   ├── retrieval/          # 核心检索模块 (四路召回, 融合, 重排)
│   ├── services/           # 业务服务层
│   ├── storage/            # 数据库与向量存储
│   ├── tests/              # 测试代码
│   ├── utils/              # 工具函数
│   └── workflow/           # RAG工作流与LLM客户端
├── data/                   # 数据目录 (向量数据库, 上传文件等)
├── docs/                   # 项目文档
│   ├── rag_components/     # RAG核心组件深度解析文档
│   ├── RAG_architecture_overview.md
│   ├── ...
│   └── ...
├── frontend/               # 前端代码 (React)
├── logs/                   # 日志文件
├── scripts/                # 实用脚本
├── .env.example            # 环境变量示例
├── docker-compose.yml      # Docker配置
├── requirements.txt        # Python依赖
└── run.py                  # 后端启动脚本
```

## 📝 许可证

本项目采用 Apache License 2.0 许可证，并附加商业使用限制条款。详情请见 [LICENSE](LICENSE) 文件。

### 商业使用限制

- ✅ **后台服务器商用**: 允许作为后台服务器直接商用
- ❌ **SaaS服务限制**: 未经商业授权不允许提供SaaS服务
- ⚠️ **版权信息保留**: 任何商业服务均需保留版权信息（除非获得单独商业授权）

商业授权咨询请联系：**hqzhon@gmail.com**

## 📧 联系方式

如有问题、建议或商业授权需求：
- 邮箱：**hqzhon@gmail.com**
- 电报：**@hqzhon**
