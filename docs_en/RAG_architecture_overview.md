# RAG System Architecture Overview

## 1. Introduction

This intelligent Q&A system is an advanced implementation based on the Retrieval-Augmented Generation (RAG) architecture. It aims to overcome the knowledge limitations and "hallucination" problems of Large Language Models (LLMs) by integrating with external knowledge bases, thereby providing accurate, reliable, and traceable answers in professional domains such as medicine.

This document aims to provide a high-level overview of this system's RAG architecture and serve as a guide, linking to detailed technical analyses of each core component.

## 2. Overall Architecture

The system's workflow can be divided into two main phases:

1.  **Offline Phase: Data Ingestion**: The process of parsing, chunking, and vectorizing raw documents (like PDFs) and storing them in the knowledge base.
2.  **Online Phase: Query Processing**: The complete, real-time chain of retrieving, reranking, and generating answers when a user asks a question.

![RAG Architecture Diagram](https://example.com/rag_architecture.png)  <!-- You can replace this with a real architecture diagram URL -->

## 3. Core Component Deep Dive

The following are the core components that make up our advanced RAG chain. Each component is meticulously designed and optimized for maximum performance. Click the links to navigate to the in-depth analysis documents for each component.

### 3.1. [Intelligent Document Processing](./rag_components/1_document_processing.md)

- **Overview**: This phase is the foundation of a high-quality knowledge base. It is responsible for transforming raw, unstructured PDF documents into clean, structured, and metadata-rich information chunks.
- **Core Components**:
    - `EnhancedPDFProcessor`: Not only extracts text but also parses tables, images, and understands the document's layout.
    - `MedicalTextSplitter`: A dual-mode dispatcher that prioritizes intelligent semantic chunking with `HybridTextSplitter` and retains stable traditional "recursive" chunking as a fallback.
- **[>> Read the detailed implementation of Document Processing...](./rag_components/1_document_processing.md)**

### 3.2. [Query Transformation and Optimization](./rag_components/2_query_transformation.md)

- **Overview**: To bridge the gap between users' colloquial queries and the professional terminology in the knowledge base, the system intelligently optimizes queries before retrieval.
- **Core Component**:
    - `QueryTransformer`: Uses an LLM to rewrite and expand the original query, generating a set of "super queries" better suited for retrieval to maximize recall.
- **[>> Read the detailed implementation of Query Transformation...](./rag_components/2_query_transformation.md)**

### 3.3. [4-Path Recall and Fusion Retrieval](./rag_components/3_retrieval.md)

- **Overview**: This is the core engine of the RAG system. It employs a 4-path recall strategy based on "multi-dimensional content representation," searching four different "profiles" of a document (vector, full text, summary, keywords) in parallel to achieve unparalleled recall and precision.
- **Core Components**:
    - `AdvancedFusionRetriever`: A highly configurable fusion retriever.
    - **4-Path Recall**: Simultaneously executes four retrieval paths: `VECTOR` (semantic), `CONTENT` (full-text keyword), `SUMMARY` (summary keyword), and `KEYWORDS` (keyword list).
    - **Result Fusion**: Uses the Reciprocal Rank Fusion (RRF) algorithm to intelligently merge the results from all four recall paths.
- **[>> Read the detailed implementation of 4-Path Recall and Fusion Retrieval...](./rag_components/3_retrieval.md)**

### 3.4. [AI-Enhanced Reranking](./rag_components/4_reranking.md)

- **Overview**: After the initial retrieval, a more powerful "judge" model performs a second-pass "close reading" of the candidate documents to ensure that only the most relevant, highest-quality information is passed to the final generation stage.
- **Core Components**:
    - `EnhancedReranker`: Calls an external large model API (e.g., Qwen) to perform deep relevance scoring and sorting, achieving selection of the best from the best.
    - **Smart Caching**: Caches reranking results to significantly improve the efficiency and response time for repeated queries.
- **[>> Read the detailed implementation of Reranking...](./rag_components/4_reranking.md)**

### 3.5. [Context Construction and Answer Generation](./rag_components/5_response_generation.md)

- **Overview**: The final mile of the RAG chain. The system constructs a context from the filtered, high-quality information and guides an LLM via a carefully designed prompt to generate a professional, safe, and credible answer.
- **Core Components**:
    - `EnhancedRAGWorkflow`: Orchestrates the entire generation process.
    - **Prompt Engineering**: A professional prompt template for the medical domain, including role-setting, core instructions, and safety constraints.
    - **Streaming and Source Tracing**: Implements a typewriter effect for the response and clearly displays the source literature on the frontend.
- **[>> Read the detailed implementation of Answer Generation...](./rag_components/5_response_generation.md)**

## 4. Conclusion

This RAG system is a precision-engineered system composed of multiple highly optimized, collaborative components. Through meticulous refinement at every stage—document processing, query optimization, fusion retrieval, AI reranking, and answer generation—we have built an intelligent Q&A system that excels in professional domains and delivers highly accurate and trustworthy answers. We hope this series of documents helps you fully understand its internal workings.
