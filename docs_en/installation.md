# Installation and Configuration Guide

This document provides detailed installation and configuration instructions for the Medical Literature RAG System.

## Prerequisites

### System Requirements
- **Operating System**: Linux, macOS, Windows
- **Python Version**: 3.9+
- **Node.js Version**: 16+
- **Memory**: 16GB+ recommended
- **Storage**: 100GB+ available space
- **GPU**: Optional, for accelerating embedding calculations

### Hardware Recommendations
- **CPU**: 8 cores or more
- **Memory**: 32GB recommended for large-scale document processing
- **Storage**: SSD recommended for improved I/O performance
- **GPU**: NVIDIA GPU with CUDA support (Optional)

## Installation Steps

### 1. Clone the Project

```bash
git clone https://github.com/hqzhon/smart-rag
cd smart-rag
```

### 2. Create a Virtual Environment

```bash
# Using conda
conda create -n smart-rag python=3.12
conda activate smart-rag

# Or using venv
python -m venv venv
source venv/bin/activate  # Linux/macOS
# Or
venv\Scripts\activate     # Windows
```

### 3. Install Python Dependencies

```bash
# Install full dependencies
pip install -r requirements.txt
```

### 4. Install Frontend Dependencies

```bash
cd frontend
npm install
cd ..
```

## Environment Configuration

### 1. Environment Variables

Copy the environment variable template:
```bash
cp .env.example .env
```

Edit the `.env` file and configure the following parameters:

```bash
# Application Base Config
APP_NAME="Medical RAG System"
APP_VERSION="2.0.0"
DEBUG=false
LOG_LEVEL="INFO"
ENVIRONMENT="development"

# API Config
API_HOST="0.0.0.0"
API_PORT=8001
HOST=0.0.0.0
PORT=8001

# MySQL Database Config
DATABASE_URL="mysql+pymysql://toolkit:your_password@localhost:3306/medical_rag"
MYSQL_HOST="localhost"
MYSQL_PORT=3306
MYSQL_USER="toolkit"
MYSQL_PASSWORD="your_password"
MYSQL_DATABASE="medical_rag"

# Redis Config
REDIS_URL=redis://localhost:6379/0

# Deepseek Config
DEEPSEEK_API_KEY=sk-your-deepseek-api-key-here
DEEPSEEK_MODEL=deepseek-chat
DEEPSEEK_BASE_URL=https://api.deepseek.com/v1

# Qwen API Config
QIANWEN_API_KEY=your-qianwen-api-key-here
QIANWEN_BASE_URL=https://dashscope.aliyuncs.com
QIANWEN_EMBEDDING_MODEL=text-embedding-v4
QIANWEN_RERANK_MODEL=gte-rerank-v2

# Optional OpenAI Config
# OPENAI_API_KEY="your-openai-api-key"
# OPENAI_MODEL="gpt-3.5-turbo"
# OPENAI_BASE_URL="https://api.openai.com/v1"
# OPENAI_EMBEDDING_MODEL="text-embedding-ada-002"

# Embedding Model Config
EMBEDDING_MODEL="text-embedding-v4"
LLM_MODEL="deepseek-chat"
RERANKER_MODEL="gte-rerank-v2"
EMBEDDING_DEVICE="cpu"

# Vector Database Config
CHROMA_PERSIST_DIRECTORY=./data/chroma_db
CHROMA_DB_DIR=./data/chroma_db
CHROMA_COLLECTION_NAME=medical_documents

# Document Processing Config
MAX_FILE_SIZE=52428800  # 50MB in bytes
ALLOWED_EXTENSIONS=".pdf,.txt,.docx,.md"
UPLOAD_DIR="./data/uploads"
PROCESSED_DIR="./data/processed"
UPLOAD_DIRECTORY="./data/uploads"
PROCESSED_DIRECTORY="./data/processed"

# Retrieval and Generation Config
RETRIEVAL_TOP_K=10
RERRANK_TOP_K=5
CHUNK_SIZE=500
CHUNK_OVERLAP=100
MAX_TOKENS=1000
TEMPERATURE=0.7
ENABLE_SEMANTIC_CHUNKING=true

# Logging Config
LOG_DIRECTORY="./logs"

# Security Config
SECRET_KEY="your-secret-key-here"
JWT_SECRET_KEY="your-jwt-secret-key-here"
JWT_ALGORITHM="HS256"
JWT_EXPIRE_MINUTES=1440
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Performance Config
MAX_CONCURRENT_REQUESTS=10
REQUEST_TIMEOUT=60
CACHE_TTL=3600

```

**Important Notes**:
- `DEEPSEEK_API_KEY` and `QIANWEN_API_KEY` need to be obtained from [Deepseek](https://platform.deepseek.com/) and [Alibaba Cloud Dashscope](https://dashscope.aliyuncs.com/) respectively.
- Please set a secure password for `MYSQL_PASSWORD`.
- Please generate random strings for `SECRET_KEY` and `JWT_SECRET_KEY`.
- The default file size limit is 50MB (52428800 bytes).

### 2. Frontend Environment Configuration

Edit the `frontend/.env` file:

```bash
# API Config
VITE_API_BASE_URL=http://localhost:8001
VITE_API_TIMEOUT=30000

# Upload Config
VITE_MAX_FILE_SIZE=104857600  # 100MB
VITE_ALLOWED_FILE_TYPES=.pdf,.doc,.docx,.txt

# UI Config
VITE_APP_TITLE="Medical Literature RAG System"
VITE_ENABLE_DEBUG=true
```

## Database Initialization

### 1. Create Data Directories

```bash
mkdir -p data/chroma_db
mkdir -p data/processed
mkdir -p data/raw
mkdir -p logs
```

### 2. MySQL Database Configuration

#### Install MySQL

```bash
# macOS
brew install mysql

# Ubuntu/Debian
sudo apt-get install mysql-server

# CentOS/RHEL
sudo yum install mysql-server
```

#### Start MySQL Service

```bash
# macOS
brew services start mysql

# Linux
sudo systemctl start mysql
sudo systemctl enable mysql
```

#### Secure Installation (Recommended)

```bash
sudo mysql_secure_installation
```
Follow the prompts to set a root password, remove anonymous users, disable remote root login, etc.

#### Create Database and User

```sql
# Login to MySQL
mysql -u root -p

# Create database
CREATE DATABASE medical_rag CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

# Create user
CREATE USER 'toolkit'@'localhost' IDENTIFIED BY 'your_password';

# Grant privileges
GRANT ALL PRIVILEGES ON medical_rag.* TO 'toolkit'@'localhost';
FLUSH PRIVILEGES;

# Verify creation
SHOW DATABASES;
SELECT User, Host FROM mysql.user WHERE User = 'toolkit';

# Exit
EXIT;
```

#### Database Initialization

The project provides an automated database initialization script to create all necessary table structures with one command.

**Method 1: Using the Initialization Script (Recommended)**

1.  **Ensure Environment Variables are Configured**
    ```bash
    # Check the database configuration in the .env file
    cat .env | grep MYSQL
    ```
    Ensure the following configurations are correct:
    ```env
    MYSQL_HOST=localhost
    MYSQL_PORT=3306
    MYSQL_USER=toolkit
    MYSQL_PASSWORD=your_password
    MYSQL_DATABASE=medical_rag
    DATABASE_URL=mysql+pymysql://toolkit:your_password@localhost:3306/medical_rag
    ```

2.  **Run the Initialization Script**
    ```bash
    # Navigate to the project directory
    cd /path/to/smart-rag
    
    # Run the database initialization script
    python scripts/init_database.py
    ```
    The script will automatically:
    - Create the database (if it doesn't exist)
    - Create all necessary data tables
    - Set the correct character sets and indexes
    - Validate the database connection
    - Display table structure information
    - Optionally insert sample data

3.  **Verify Initialization**
    ```bash
    # Login to the database to check the table structure
    mysql -u toolkit -p medical_rag
    
    # Show all tables
    SHOW TABLES;
    
    # Describe a table (e.g., documents)
    DESCRIBE documents;
    ```

**Method 2: Manual Table Creation**

If you need to create the table structure manually, you can execute the following SQL:

```sql
-- Use the database
USE medical_rag;

-- Documents Table
CREATE TABLE IF NOT EXISTS documents (
    id VARCHAR(255) PRIMARY KEY COMMENT 'Unique document ID',
    title VARCHAR(500) NOT NULL COMMENT 'Document title',
    content LONGTEXT NOT NULL COMMENT 'Document content',
    file_path VARCHAR(1000) COMMENT 'File path',
    file_size BIGINT COMMENT 'File size in bytes',
    file_type VARCHAR(200) COMMENT 'File type',
    metadata JSON COMMENT 'Metadata',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT 'Creation timestamp',
    status VARCHAR(50) DEFAULT 'uploading' COMMENT 'Document status',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT 'Update timestamp',
    vectorized BOOLEAN DEFAULT FALSE COMMENT 'Whether it has been vectorized',
    vectorization_status VARCHAR(50) DEFAULT 'pending' COMMENT 'Vectorization status',
    metadata_generation_status VARCHAR(50) DEFAULT 'pending' COMMENT 'Metadata generation status',
    processed BOOLEAN DEFAULT FALSE COMMENT 'Whether processed',
    metadata_generation_completed_at TIMESTAMP NULL COMMENT 'Metadata generation completion time',
    INDEX idx_created_at (created_at),
    INDEX idx_file_type (file_type),
    INDEX idx_vectorized (vectorized),
    INDEX idx_vectorization_status (vectorization_status),
    INDEX idx_status (status),
    INDEX idx_metadata_generation_status (metadata_generation_status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Documents Table';

-- Sessions Table
CREATE TABLE IF NOT EXISTS sessions (
    id VARCHAR(255) PRIMARY KEY COMMENT 'Unique session ID',
    user_id VARCHAR(255) COMMENT 'User ID',
    title VARCHAR(500) COMMENT 'Session title',
    metadata JSON COMMENT 'Session metadata',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT 'Creation timestamp',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT 'Update timestamp',
    is_active BOOLEAN DEFAULT TRUE COMMENT 'Is active',
    INDEX idx_user_id (user_id),
    INDEX idx_created_at (created_at),
    INDEX idx_is_active (is_active)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Sessions Table';

-- Chat History Table
CREATE TABLE IF NOT EXISTS chat_history (
    id BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT 'Record ID',
    session_id VARCHAR(255) NOT NULL COMMENT 'Session ID',
    question TEXT NOT NULL COMMENT 'User question',
    answer LONGTEXT NOT NULL COMMENT 'AI answer',
    sources JSON COMMENT 'Reference sources',
    metadata JSON COMMENT 'Metadata',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT 'Creation timestamp',
    INDEX idx_session_id (session_id),
    INDEX idx_created_at (created_at),
    FOREIGN KEY (session_id) REFERENCES sessions (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Chat History Table';

-- Search History Table
CREATE TABLE IF NOT EXISTS search_history (
    id BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT 'Record ID',
    session_id VARCHAR(255) COMMENT 'Session ID',
    query TEXT NOT NULL COMMENT 'Search query',
    results JSON COMMENT 'Search results',
    result_count INT DEFAULT 0 COMMENT 'Number of results',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT 'Creation timestamp',
    INDEX idx_session_id (session_id),
    INDEX idx_created_at (created_at),
    FOREIGN KEY (session_id) REFERENCES sessions (id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Search History Table';
```

**Table Structure Overview**

| Table Name       | Description              | Key Fields                                                 |
| ---------------- | ------------------------ | ---------------------------------------------------------- |
| `documents`      | Document storage         | id, title, content, file_path, status, vectorized, vectorization_status, metadata_generation_status, processed |
| `sessions`       | Session management       | id, user_id, title, metadata, is_active                    |
| `chat_history`   | Chat message history     | id, session_id, question, answer, sources                  |
| `search_history` | Search query history     | id, session_id, query, results, result_count               |

**Troubleshooting**

Common issues and solutions:

1.  **Connection Refused**
    ```bash
    # Check MySQL service status
    brew services list | grep mysql  # macOS
    systemctl status mysql          # Linux
    
    # Restart MySQL service
    brew services restart mysql     # macOS
    sudo systemctl restart mysql    # Linux
    ```

2.  **Access Denied**
    ```sql
    # Re-grant privileges
    GRANT ALL PRIVILEGES ON medical_rag.* TO 'toolkit'@'localhost';
    FLUSH PRIVILEGES;
    ```

3.  **Character Set Issues**
    ```sql
    # Check database character set
    SELECT DEFAULT_CHARACTER_SET_NAME, DEFAULT_COLLATION_NAME 
    FROM information_schema.SCHEMATA 
    WHERE SCHEMA_NAME = 'medical_rag';
    
    # Alter character set if needed
    ALTER DATABASE medical_rag CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
    ```

4.  **Initialization Script Fails**
    ```bash
    # Check Python dependencies
    pip install pymysql
    
    # Check environment variables
    python -c "from app.core.config import get_settings; print(get_settings().mysql_host)"
    
    # Test connection manually
    python -c "import pymysql; pymysql.connect(host='localhost', user='toolkit', password='your_password', database='medical_rag')"
    ```

### 3. Initialize Vector Database

The system will automatically initialize the Chroma vector database on the first run. To initialize it manually:

```bash
python -c "from app.storage.vector_store import VectorStore; VectorStore().initialize()"
```

## Optional Component Configuration

### 1. Redis Task Queue (Optional)

If you need asynchronous task processing, install and configure Redis:

```bash
# Install Redis
# Ubuntu/Debian
sudo apt-get install redis-server

# macOS
brew install redis

# Start Redis
redis-server

# Start Celery Worker
celery -A app.celery_app worker --loglevel=info --pool=threads --concurrency=2 --queues=metadata
```

### 2. GPU Acceleration (Optional)

If you have an NVIDIA GPU, you can install CUDA support:

```bash
# Install PyTorch with CUDA
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118

# Install other GPU-accelerated libraries
pip install sentence-transformers[gpu]
```

### 3. Local LLM Models (Optional)

To use local LLM models, install Ollama:

```bash
# Install Ollama
curl -fsSL https://ollama.ai/install.sh | sh

# Download models
ollama pull llama2
ollama pull qwen:7b

# Configure environment variables
LLM_PROVIDER="ollama"
OLLAMA_BASE_URL="http://localhost:11434"
LLM_MODEL="llama2"
```

## Verify Installation

### 1. Start Backend Service

```bash
python run.py
```

Visit http://localhost:8001/docs to see the API documentation.

### 2. Start Frontend Service

```bash
cd frontend
npm run dev
```

Visit http://localhost:3001 to see the web interface.

### 3. Health Check

```bash
curl http://localhost:8001/api/v1/health
```

Expected response:
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "timestamp": "2024-01-01T00:00:00Z"
}
```

## Common Issues

### 1. Dependency Installation Failure

**Issue**: pip fails to install dependencies.
**Solution**:
```bash
# Upgrade pip
pip install --upgrade pip

# Use a different mirror
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple/
```

### 2. Port in Use

**Issue**: Port 8001 or 3001 is already in use.
**Solution**: Modify the port configuration in the `.env` file.

### 3. Out of Memory

**Issue**: Out of memory when processing large documents.
**Solution**:
- Decrease the `MAX_CHUNK_SIZE` parameter.
- Increase system memory.
- Use batch processing.

### 4. GPU Not Available

**Issue**: CUDA-related errors.
**Solution**:
- Check your CUDA installation.
- Fallback to the CPU version.
- Set `CUDA_VISIBLE_DEVICES=""`.

## Performance Tuning Recommendations

1.  **Use SSD storage** to improve I/O performance.
2.  **Enable GPU acceleration** to speed up embedding calculations.
3.  **Configure Redis caching** to reduce redundant computations.
4.  **Adjust chunking parameters** to balance precision and performance.
5.  **Use local models** to reduce API call latency.

## Next Steps

After installation, please refer to the following documents:
- [Usage Guide](usage.md) - Learn how to use the system.
- [API Reference](api.md) - Understand the API endpoints.
- [Architecture Guide](architecture.md) - Dive deeper into the system architecture.
