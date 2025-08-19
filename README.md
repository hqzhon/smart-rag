# 医疗文献RAG系统

基于检索增强生成(RAG)技术的智能医疗文献问答系统，能够处理医疗PDF文档并提供专业的医疗信息查询服务。

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
