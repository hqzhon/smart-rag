# Smart RAG - Intelligent Medical Literature Retrieval and Q&A System

[![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![React](https://img.shields.io/badge/react-18.0+-61dafb.svg)](https://reactjs.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-009688.svg)](https://fastapi.tiangolo.com/)

[中文版](README_zh.md) | [English Version](README.md)

🚀 **An intelligent medical literature Q&A system based on advanced RAG technology**

An intelligent document Q&A platform that integrates hybrid retrieval, RRF result fusion, and multi-model support, specifically designed for medical literature processing and knowledge retrieval.

## ✨ Core Features

- **🚀 Advanced RAG Architecture**: Adopts industry-leading Retrieval-Augmented Generation (RAG) technology to ensure the accuracy, relevance, and traceability of answers.
- **🧠 Intelligent Document Processing**:
  - **Multi-modal Parsing**: Not only extracts text but also understands complex structures like tables and images in PDFs.
  - **Dual-mode Smart Chunking**: Prioritizes semantic chunking using `HybridTextSplitter` and maintains stable "recursive" chunking as a fallback to ensure context integrity.
- **🎯 Small-to-Big Retrieval & 4-Path Hybrid Retrieval**:
  - **Small-to-Big Architecture**: Revolutionary retrieval strategy that uses small chunks for precise matching and parent chunks for complete context, optimizing both cost and quality.
  - **Multi-dimensional Recall**: Simultaneously performs four retrieval paths—`VECTOR` (semantic), `CONTENT` (full-text keyword), `SUMMARY` (summary keyword), and `KEYWORDS` (keyword list)—to maximize recall and precision.
  - **RRF Fusion**: Uses the Reciprocal Rank Fusion (RRF) algorithm to intelligently merge results from multiple paths.
  - **Smart Switching**: Automatically switches from small chunks (for retrieval) to parent chunks (for generation) to ensure optimal context.
- **🔍 AI Enhancement & Optimization**:
  - **Query Transformation**: Utilizes LLMs to rewrite and expand user queries for better matching with the knowledge base.
  - **AI Reranking**: After retrieval, a more powerful AI model performs a second-pass "close reading" and reranking to ensure the final answer is based on the most relevant, high-quality content.
- **💬 Enterprise-grade Q&A Experience**:
  - **Streaming Output**: Real-time streaming of answers to enhance user interaction.
  - **Precise Source Tracing**: All answers provide clear literature sources for easy verification.
  - **High Scalability**: Asynchronous and modular design makes it easy to integrate new models and features.

## 🚀 Quick Start

### 1. Prerequisites

- Python 3.9+
- Node.js 16+
- 16GB+ RAM recommended
- 100GB+ available storage space

### 2. Install Dependencies

```bash
# Install base dependencies
pip install -r requirements.txt
```

### 3. Configure Environment Variables

Copy and edit the environment variables file:
```bash
cp .env.example .env
# Edit the .env file to configure necessary parameters
```

### 4. Start the Backend Service

```bash
python run.py
python start_celery_worker.py  // For the queue
```

The backend API will start at http://localhost:8001

### 5. Start the Frontend Service

```bash
cd frontend
npm install
npm run dev
```

The frontend interface will start at http://localhost:3001

## 📚 Detailed Documentation

### In-depth RAG Architecture Analysis

To help you understand the internal workings of our system, we provide a series of detailed component analysis documents:

- **[RAG System Architecture Overview](docs_en/RAG_architecture_overview.md)** - **Recommended to read first** for a high-level overview of the system.
  - **[Component Deep Dive 1: Intelligent Document Processing](docs_en/rag_components/1_document_processing.md)**
  - **[Component Deep Dive 2: Query Transformation and Optimization](docs_en/rag_components/2_query_transformation.md)**
  - **[Component Deep Dive 3: 4-Path Recall and Fusion Retrieval](docs_en/rag_components/3_retrieval.md)**
  - **[Component Deep Dive 4: AI-Enhanced Reranking](docs_en/rag_components/4_reranking.md)**
  - **[Component Deep Dive 5: Context Construction and Answer Generation](docs_en/rag_components/5_response_generation.md)**

### Other Documents

- **[Usage Guide](docs_en/usage.md)** - Detailed instructions on how to use the web interface and API.
- **[Installation and Configuration Guide](docs_en/installation.md)** - Detailed environment setup and installation steps.
- **[API Reference](docs_en/api.md)** - Complete API documentation and usage examples.
- **[System Architecture](docs_en/architecture.md)** - The original technical architecture, component design, and development guide.


---

## 🏗️ Project Structure

```
smart-rag/
├── app/                    # Application backend code (FastAPI)
│   ├── api/                # API routes
│   ├── core/               # Core functionalities (Config, Session Mgmt, etc.)
│   ├── embeddings/         # Embeddings and text chunking module
│   ├── metadata/           # Metadata generation module (summaries, keywords)
│   ├── models/             # Pydantic data models
│   ├── processors/         # Document parsing and processing
│   ├── retrieval/          # Core retrieval module (4-path recall, fusion, reranking)
│   ├── services/           # Business logic services
│   ├── storage/            # Database and vector store
│   ├── tests/              # Test code
│   ├── utils/              # Utility functions
│   └── workflow/           # RAG workflow and LLM clients
├── data/                   # Data directory (vector DB, uploads, etc.)
├── docs/                   # Project documentation (Chinese)
├── docs_en/                # Project documentation (English)
│   ├── rag_components/     # RAG core component deep dives
│   ├── RAG_architecture_overview.md
│   ├── ...
│   └── ...
├── frontend/               # Frontend code (React)
├── logs/                   # Log files
├── scripts/                # Utility scripts
├── .env.example            # Environment variable example
├── docker-compose.yml      # Docker configuration
├── requirements.txt        # Python dependencies
└── run.py                  # Backend startup script
```

## 📝 License

This project is licensed under the Apache License 2.0 with additional commercial use restrictions. See the [LICENSE](LICENSE) file for details.

### Commercial Use Restrictions

- ✅ **Backend Server Commercial Use**: Permitted for direct commercial purposes
- ❌ **SaaS Service Restriction**: Not permitted without separate commercial license
- ⚠️ **Copyright Attribution**: Required for all commercial services (unless separately licensed)

For commercial licensing inquiries, please contact: **hqzhon@gmail.com**

## 📧 Contact

For questions, suggestions, or commercial licensing:
- Email: **hqzhon@gmail.com**
- Telegram: **@hqzhon**
