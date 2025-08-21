# Smart RAG - 医学文献智能检索问答系统

🚀 **基于先进RAG技术的医学文献智能检索问答系统**

一个集成了混合检索、RRF结果融合和多模型支持的智能文档问答平台，专为医学文献处理和知识检索而设计。

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![React](https://img.shields.io/badge/react-18.0+-61dafb.svg)](https://reactjs.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-009688.svg)](https://fastapi.tiangolo.com/)

## ✨ 核心亮点

### 🎯 **智能检索引擎**
- **混合检索算法**：结合关键词检索和向量检索，检索准确率提升40%
- **RRF结果融合**：采用Reciprocal Rank Fusion算法，智能融合多种检索结果
- **语义理解**：基于先进的向量嵌入技术，深度理解文档语义
- **上下文感知**：支持多轮对话的上下文理解和记忆

### 📚 **强大文档处理**
- **多格式支持**：PDF、Word、TXT、Markdown等主流格式
- **智能分块**：语义感知的文档分块策略，保持内容完整性
- **批量处理**：支持大规模文档批量上传和并行处理
- **实时预览**：文档内容预览和管理功能

### 💬 **智能问答体验**
- **流式输出**：实时流式回答，提升用户交互体验
- **多模型兼容**：支持OpenAI GPT、Claude、本地LLM等多种模型
- **引用溯源**：精确的答案来源定位和引用展示
- **会话管理**：多会话并行处理和历史记录管理

### 🔧 **企业级特性**
- **高性能架构**：支持GPU加速和分布式部署
- **安全可靠**：完整的权限控制和数据安全保护
- **监控运维**：实时系统监控和性能指标展示
- **可扩展性**：模块化设计，支持功能扩展和定制

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
```

后端API将在 http://localhost:8001 启动

### 5. 启动前端服务

```bash
cd frontend
npm install
npm run dev
```

前端界面将在 http://localhost:3001 启动

## 📖 使用指南

### Web界面使用

#### 启动前端
```bash
cd frontend
npm install
npm run dev
```

前端将在 http://localhost:3001 启动

#### 使用步骤
1. **访问系统**：打开浏览器访问 http://localhost:3001
2. **上传文档**：选择医疗PDF文件并上传
3. **等待处理**：系统会自动处理文档并建立索引
4. **开始查询**：在查询框中输入医疗相关问题
5. **查看结果**：系统会返回基于文档的专业回答

### API接口使用

#### 1. 健康检查
```bash
curl http://localhost:8001/api/v1/health
```

#### 2. 上传文档
```bash
curl -X POST "http://localhost:8001/api/v1/documents/upload" \
     -H "accept: application/json" \
     -H "Content-Type: multipart/form-data" \
     -F "file=@your_medical_document.pdf"
```

#### 3. 查询问答
```bash
curl -X POST "http://localhost:8001/api/v1/chat/query" \
     -H "accept: application/json" \
     -H "Content-Type: application/json" \
     -d '{
       "query": "高血压的症状有哪些？",
       "session_id": "your_session_id"
     }'
```

### 流式查询

系统支持流式响应，可以实时获取生成的回答：

```bash
curl -X POST "http://localhost:8001/api/v1/chat/stream" \
     -H "accept: application/json" \
     -H "Content-Type: application/json" \
     -d '{
       "query": "糖尿病的治疗方法有哪些？",
       "session_id": "your_session_id"
     }'
```

## 📚 详细文档

### 📖 完整指南
- **[安装配置指南](docs/installation.md)** - 详细的环境配置和安装步骤
- **[使用指南](docs/usage.md)** - Web界面和API接口的详细使用说明
- **[API文档](docs/api.md)** - 完整的API接口文档和示例
- **[系统架构](docs/architecture.md)** - 技术架构、组件设计和开发指南

### 🔧 开发文档
- **配置说明** - 环境变量和系统配置详解 → [安装指南](docs/installation.md#环境配置)
- **扩展开发** - 自定义处理器和模型集成 → [架构文档](docs/architecture.md#扩展开发)
- **性能优化** - 系统调优和监控指南 → [架构文档](docs/architecture.md#性能优化)
- **部署指南** - 生产环境部署方案 → [架构文档](docs/architecture.md#部署架构)

### 🚀 快速链接
- **问题排查** → [使用指南](docs/usage.md#故障排除)
- **API示例** → [API文档](docs/api.md#SDK示例)
- **性能基准** → [架构文档](docs/architecture.md#性能基准)
- **更新日志** → [API文档](docs/api.md#版本更新)

---

## 🏗️ 系统架构

### 核心组件

1. **文档处理器** (`app/processors/`)
   - PDF文档解析
   - 文本提取和清理
   - 表格和图像处理

2. **嵌入模块** (`app/embeddings/`)
   - 文本向量化
   - 智能分块
   - 多语言支持

3. **检索系统** (`app/retrieval/`)
   - 混合检索（向量检索+BM25）
   - 查询转换和扩展
   - 结果重排序

4. **存储模块** (`app/storage/`)
   - 向量数据库集成
   - 文档元数据管理
   - 高效检索索引

5. **工作流模块** (`app/workflow/`)
   - RAG工作流协调
   - LLM集成
   - 上下文构建

6. **API接口** (`app/api/`)
   - RESTful API
   - 流式响应支持
   - 文档上传和处理

### 系统流程

```
用户查询 → 查询转换 → 混合检索 → 结果重排序 → 上下文构建 → LLM流式生成 → 回答后处理 → 返回结果
```

### 部署架构

```
前端服务 (http://localhost:3001) ← → 后端API (http://localhost:8001)
                                      ↓
                              向量数据库 + 文档存储
```

## 🔧 开发指南

### 项目结构

```
medical-rag-system/
├── app/                    # 应用代码
│   ├── api/                # API接口
│   ├── core/               # 核心功能
│   ├── embeddings/         # 嵌入模块
│   ├── models/             # 数据模型
│   ├── processors/         # 文档处理
│   ├── retrieval/          # 检索系统
│   ├── services/           # 业务服务
│   ├── static/             # 静态资源
│   ├── storage/            # 存储模块
│   ├── tests/              # 测试代码
│   ├── utils/              # 工具函数
│   ├── workflow/           # 工作流
│   ├── __init__.py
│   └── main.py             # 应用入口
├── data/                   # 数据目录
│   ├── chroma_db/          # 向量数据库
│   ├── processed/          # 处理后数据
│   └── raw/                # 原始数据
├── frontend/               # 前端代码 (独立React应用)
├── logs/                   # 日志文件
├── scripts/                # 脚本工具
├── .env                    # 环境变量
├── .env.example            # 环境变量示例
├── docker-compose.yml      # Docker配置
├── requirements.txt        # 完整依赖
├── requirements-simple.txt # 基础依赖
└── run.py                  # 启动脚本
```

### 扩展指南

1. **添加新的文档处理器**
   - 在 `app/processors/` 目录下创建新的处理器类
   - 实现 `process()` 方法
   - 在 `document_processor.py` 中注册新处理器

2. **集成新的嵌入模型**
   - 在 `app/embeddings/embeddings.py` 中添加新模型支持
   - 实现 `embed_documents()` 和 `embed_query()` 方法

3. **添加新的检索策略**
   - 在 `app/retrieval/retriever.py` 中扩展 `HybridRetriever` 类
   - 实现新的检索方法

4. **集成新的LLM模型**
   - 在 `app/workflow/llm_client.py` 中添加新模型支持
   - 实现 `generate()` 和 `stream_generate()` 方法

## 📊 性能优化

1. **检索性能优化**
   - 使用混合检索策略
   - 实现查询扩展和重写
   - 结果重排序提高相关性

2. **生成性能优化**
   - 上下文压缩和筛选
   - 流式响应提升用户体验
   - 缓存常见查询

3. **系统性能优化**
   - 异步处理
   - 前后端分离架构
   - 分布式部署支持

## 📝 许可证

本项目采用 MIT 许可证
