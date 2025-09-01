# 安装配置指南

本文档提供医疗文献RAG系统的详细安装和配置说明。

## 环境要求

### 系统要求
- **操作系统**: Linux, macOS, Windows
- **Python版本**: 3.9+
- **Node.js版本**: 16+
- **内存**: 16GB+ 推荐
- **存储空间**: 100GB+ 可用空间
- **GPU**: 可选，用于加速嵌入计算

### 硬件建议
- **CPU**: 8核心以上
- **内存**: 32GB 推荐用于大规模文档处理
- **存储**: SSD 推荐，提升I/O性能
- **GPU**: NVIDIA GPU with CUDA支持（可选）

## 安装步骤

### 1. 克隆项目

```bash
git clone https://github.com/hqzhon/smart-rag
cd smart-rag
```

### 2. 创建虚拟环境

```bash
# 使用conda
conda create -n smart-rag python=3.12
conda activate smart-rag

# 或使用venv
python -m venv venv
source venv/bin/activate  # Linux/macOS
# 或
venv\Scripts\activate     # Windows
```

### 3. 安装Python依赖

```bash
# 安装完整依赖
pip install -r requirements.txt

# 或安装基础依赖
pip install -r requirements-simple.txt
```

### 4. 安装前端依赖

```bash
cd frontend
npm install
cd ..
```

## 环境配置

### 1. 环境变量配置

复制环境变量模板：
```bash
cp .env.example .env
```

编辑 `.env` 文件，配置以下参数：

```bash
# 应用基础配置
APP_NAME="Medical RAG System"
APP_VERSION="2.0.0"
DEBUG=false
LOG_LEVEL="INFO"
ENVIRONMENT="development"

# API配置
API_HOST="0.0.0.0"
API_PORT=8001
HOST=0.0.0.0
PORT=8001

# MySQL数据库配置
DATABASE_URL="mysql+pymysql://toolkit:your_password@localhost:3306/medical_rag"
MYSQL_HOST="localhost"
MYSQL_PORT=3306
MYSQL_USER="toolkit"
MYSQL_PASSWORD="your_password"
MYSQL_DATABASE="medical_rag"

# Redis配置
REDIS_URL=redis://localhost:6379/0

# Deepseek配置
DEEPSEEK_API_KEY=sk-your-deepseek-api-key-here
DEEPSEEK_MODEL=deepseek-chat
DEEPSEEK_BASE_URL=https://api.deepseek.com/v1

# 千问API配置
QIANWEN_API_KEY=your-qianwen-api-key-here
QIANWEN_BASE_URL=https://dashscope.aliyuncs.com
QIANWEN_EMBEDDING_MODEL=text-embedding-v4
QIANWEN_RERANK_MODEL=gte-rerank-v2

# 备用OpenAI配置（可选）
# OPENAI_API_KEY="your-openai-api-key"
# OPENAI_MODEL="gpt-3.5-turbo"
# OPENAI_BASE_URL="https://api.openai.com/v1"
# OPENAI_EMBEDDING_MODEL="text-embedding-ada-002"

# 嵌入模型配置
EMBEDDING_MODEL="text-embedding-v4"
LLM_MODEL="deepseek-chat"
RERANKER_MODEL="gte-rerank-v2"
EMBEDDING_DEVICE="cpu"

# 向量数据库配置
CHROMA_PERSIST_DIRECTORY=./data/chroma_db
CHROMA_DB_DIR=./data/chroma_db
CHROMA_COLLECTION_NAME=medical_documents

# 文档处理配置
MAX_FILE_SIZE=52428800  # 50MB in bytes
ALLOWED_EXTENSIONS=".pdf,.txt,.docx,.md"
UPLOAD_DIR="./data/uploads"
PROCESSED_DIR="./data/processed"
UPLOAD_DIRECTORY="./data/uploads"
PROCESSED_DIRECTORY="./data/processed"

# 检索和生成配置
RETRIEVAL_TOP_K=10
RERRANK_TOP_K=5
CHUNK_SIZE=500
CHUNK_OVERLAP=100
MAX_TOKENS=1000
TEMPERATURE=0.7
ENABLE_SEMANTIC_CHUNKING=true

# 日志配置
LOG_DIRECTORY="./logs"

# 安全配置
SECRET_KEY="your-secret-key-here"
JWT_SECRET_KEY="your-jwt-secret-key-here"
JWT_ALGORITHM="HS256"
JWT_EXPIRE_MINUTES=1440
ACCESS_TOKEN_EXPIRE_MINUTES=30

# 性能配置
MAX_CONCURRENT_REQUESTS=10
REQUEST_TIMEOUT=60
CACHE_TTL=3600

```

**重要说明**：
- `DEEPSEEK_API_KEY` 和 `QIANWEN_API_KEY` 需要分别从 [Deepseek](https://platform.deepseek.com/) 和 [阿里云灵积](https://dashscope.aliyuncs.com/) 获取
- `MYSQL_PASSWORD` 请设置为安全的密码
- `SECRET_KEY` 和 `JWT_SECRET_KEY` 请生成随机字符串
- 文件大小限制默认为50MB（52428800字节）
```

### 2. 前端环境配置

编辑 `frontend/.env` 文件：

```bash
# API配置
VITE_API_BASE_URL=http://localhost:8001
VITE_API_TIMEOUT=30000

# 上传配置
VITE_MAX_FILE_SIZE=104857600  # 100MB
VITE_ALLOWED_FILE_TYPES=.pdf,.doc,.docx,.txt

# 界面配置
VITE_APP_TITLE="医疗文献RAG系统"
VITE_ENABLE_DEBUG=true
```

## 数据库初始化

### 1. 创建数据目录

```bash
mkdir -p data/chroma_db
mkdir -p data/processed
mkdir -p data/raw
mkdir -p logs
```

### 2. MySQL 数据库配置

#### 安装 MySQL

```bash
# macOS
brew install mysql

# Ubuntu/Debian
sudo apt-get install mysql-server

# CentOS/RHEL
sudo yum install mysql-server
```

#### 启动 MySQL 服务

```bash
# macOS
brew services start mysql

# Linux
sudo systemctl start mysql
sudo systemctl enable mysql
```

#### 安全配置（推荐）

```bash
sudo mysql_secure_installation
```
按提示设置 root 密码，移除匿名用户，禁用远程 root 登录等。

#### 创建数据库和用户

```sql
# 登录 MySQL
mysql -u root -p

# 创建数据库
CREATE DATABASE medical_rag CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

# 创建用户
CREATE USER 'toolkit'@'localhost' IDENTIFIED BY 'your_password';

# 授权
GRANT ALL PRIVILEGES ON medical_rag.* TO 'toolkit'@'localhost';
FLUSH PRIVILEGES;

# 验证创建结果
SHOW DATABASES;
SELECT User, Host FROM mysql.user WHERE User = 'toolkit';

# 退出
EXIT;
```

#### 数据库初始化

项目提供了自动化的数据库初始化脚本，可以一键创建所有必要的表结构。

**方法一：使用初始化脚本（推荐）**

1. **确保环境变量已配置**
   ```bash
   # 检查 .env 文件中的数据库配置
   cat .env | grep MYSQL
   ```
   
   确保以下配置正确：
   ```env
   MYSQL_HOST=localhost
   MYSQL_PORT=3306
   MYSQL_USER=toolkit
   MYSQL_PASSWORD=your_password
   MYSQL_DATABASE=medical_rag
   DATABASE_URL=mysql+pymysql://toolkit:your_password@localhost:3306/medical_rag
   ```

2. **运行初始化脚本**
   ```bash
   # 进入项目目录
   cd /path/to/smart-rag
   
   # 运行数据库初始化脚本
   python scripts/init_database.py
   ```
   
   脚本将自动：
   - 创建数据库（如果不存在）
   - 创建所有必要的数据表
   - 设置正确的字符集和索引
   - 验证数据库连接
   - 显示表结构信息
   - 可选插入示例数据

3. **验证初始化结果**
   ```bash
   # 登录数据库查看表结构
   mysql -u toolkit -p medical_rag
   
   # 查看所有表
   SHOW TABLES;
   
   # 查看表结构（以 documents 表为例）
   DESCRIBE documents;
   ```

**方法二：手动创建表结构**

如果需要手动创建表结构，可以执行以下 SQL：

```sql
-- 使用数据库
USE medical_rag;

-- 文档表
CREATE TABLE IF NOT EXISTS documents (
    id VARCHAR(255) PRIMARY KEY COMMENT '文档唯一标识',
    title VARCHAR(500) NOT NULL COMMENT '文档标题',
    content LONGTEXT NOT NULL COMMENT '文档内容',
    file_path VARCHAR(1000) COMMENT '文件路径',
    file_size BIGINT COMMENT '文件大小(字节)',
    file_type VARCHAR(50) COMMENT '文件类型',
    vectorized BOOLEAN DEFAULT FALSE COMMENT '是否已向量化',
    vectorization_status ENUM('pending', 'processing', 'completed', 'failed') DEFAULT 'pending' COMMENT '向量化状态',
    vectorization_time TIMESTAMP NULL COMMENT '向量化时间',
    metadata JSON COMMENT '元数据',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    INDEX idx_created_at (created_at),
    INDEX idx_file_type (file_type),
    INDEX idx_vectorized (vectorized),
    INDEX idx_vectorization_status (vectorization_status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='文档表';

-- 会话表
CREATE TABLE IF NOT EXISTS sessions (
    id VARCHAR(255) PRIMARY KEY COMMENT '会话唯一标识',
    user_id VARCHAR(255) COMMENT '用户ID',
    title VARCHAR(500) COMMENT '会话标题',
    metadata JSON COMMENT '会话元数据',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    is_active BOOLEAN DEFAULT TRUE COMMENT '是否活跃',
    INDEX idx_user_id (user_id),
    INDEX idx_created_at (created_at),
    INDEX idx_is_active (is_active)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='会话表';

-- 聊天记录表
CREATE TABLE IF NOT EXISTS chat_history (
    id BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '记录ID',
    session_id VARCHAR(255) NOT NULL COMMENT '会话ID',
    question TEXT NOT NULL COMMENT '用户问题',
    answer LONGTEXT NOT NULL COMMENT 'AI回答',
    sources JSON COMMENT '参考来源',
    metadata JSON COMMENT '元数据',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    INDEX idx_session_id (session_id),
    INDEX idx_created_at (created_at),
    FOREIGN KEY (session_id) REFERENCES sessions (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='聊天记录表';

-- 搜索历史表
CREATE TABLE IF NOT EXISTS search_history (
    id BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '记录ID',
    session_id VARCHAR(255) COMMENT '会话ID',
    query TEXT NOT NULL COMMENT '搜索查询',
    results JSON COMMENT '搜索结果',
    result_count INT DEFAULT 0 COMMENT '结果数量',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    INDEX idx_session_id (session_id),
    INDEX idx_created_at (created_at),
    FOREIGN KEY (session_id) REFERENCES sessions (id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='搜索历史表';
```

**数据库表结构说明**

| 表名 | 说明 | 主要字段 |
|------|------|----------|
| `documents` | 文档存储表 | id, title, content, file_path, vectorized, vectorization_status |
| `sessions` | 会话管理表 | id, user_id, title, metadata, is_active |
| `chat_history` | 聊天记录表 | id, session_id, question, answer, sources |
| `search_history` | 搜索历史表 | id, session_id, query, results, result_count |

**故障排除**

常见问题及解决方案：

1. **连接被拒绝**
   ```bash
   # 检查 MySQL 服务状态
   brew services list | grep mysql  # macOS
   systemctl status mysql          # Linux
   
   # 重启 MySQL 服务
   brew services restart mysql     # macOS
   sudo systemctl restart mysql    # Linux
   ```

2. **权限不足**
   ```sql
   # 重新授权
   GRANT ALL PRIVILEGES ON medical_rag.* TO 'toolkit'@'localhost';
   FLUSH PRIVILEGES;
   ```

3. **字符集问题**
   ```sql
   # 检查数据库字符集
   SELECT DEFAULT_CHARACTER_SET_NAME, DEFAULT_COLLATION_NAME 
   FROM information_schema.SCHEMATA 
   WHERE SCHEMA_NAME = 'medical_rag';
   
   # 修改字符集（如果需要）
   ALTER DATABASE medical_rag CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
   ```

4. **初始化脚本失败**
   ```bash
   # 检查 Python 依赖
   pip install pymysql
   
   # 检查环境变量
   python -c "from app.core.config import get_settings; print(get_settings().mysql_host)"
   
   # 手动测试连接
   python -c "import pymysql; pymysql.connect(host='localhost', user='toolkit', password='your_password', database='medical_rag')"
   ```

### 3. 初始化向量数据库

系统首次启动时会自动初始化Chroma向量数据库。如需手动初始化：

```bash
python -c "from app.storage.vector_store import VectorStore; VectorStore().initialize()"
```

## 可选组件配置

### 1. Redis任务队列（可选）

如果需要使用异步任务处理，安装并配置Redis：

```bash
# 安装Redis
# Ubuntu/Debian
sudo apt-get install redis-server

# macOS
brew install redis

# 启动Redis
redis-server

# 启动Celery Worker
celery -A app.celery_app worker --loglevel=info --pool=threads --concurrency=2 --queues=metadata
```

### 2. GPU加速（可选）

如果有NVIDIA GPU，可以安装CUDA支持：

```bash
# 安装PyTorch with CUDA
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118

# 安装其他GPU加速库
pip install sentence-transformers[gpu]
```

### 3. 本地LLM模型（可选）

如果要使用本地LLM模型，安装Ollama：

```bash
# 安装Ollama
curl -fsSL https://ollama.ai/install.sh | sh

# 下载模型
ollama pull llama2
ollama pull qwen:7b

# 配置环境变量
LLM_PROVIDER="ollama"
OLLAMA_BASE_URL="http://localhost:11434"
LLM_MODEL="llama2"
```

## 验证安装

### 1. 启动后端服务

```bash
python run.py
```

访问 http://localhost:8001/docs 查看API文档

### 2. 启动前端服务

```bash
cd frontend
npm run dev
```

访问 http://localhost:3001 查看Web界面

### 3. 健康检查

```bash
curl http://localhost:8001/api/v1/health
```

预期返回：
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "timestamp": "2024-01-01T00:00:00Z"
}
```

## 常见问题

### 1. 依赖安装失败

**问题**: pip安装依赖时出错
**解决**: 
```bash
# 升级pip
pip install --upgrade pip

# 使用国内镜像
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple/
```

### 2. 端口占用

**问题**: 端口8001或3001被占用
**解决**: 修改 `.env` 文件中的端口配置

### 3. 内存不足

**问题**: 处理大文档时内存不足
**解决**: 
- 减小 `MAX_CHUNK_SIZE` 参数
- 增加系统内存
- 使用分批处理

### 4. GPU不可用

**问题**: CUDA相关错误
**解决**: 
- 检查CUDA安装
- 降级到CPU版本
- 设置 `CUDA_VISIBLE_DEVICES=""`

## 性能优化建议

1. **使用SSD存储**提升I/O性能
2. **启用GPU加速**提升嵌入计算速度
3. **配置Redis缓存**减少重复计算
4. **调整chunk参数**平衡精度和性能
5. **使用本地模型**减少API调用延迟

## 下一步

安装完成后，请参考以下文档：
- [使用指南](usage.md) - 学习如何使用系统
- [API文档](api.md) - 了解API接口
- [架构指南](architecture.md) - 深入了解系统架构