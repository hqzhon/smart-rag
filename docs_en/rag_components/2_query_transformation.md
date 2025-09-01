# RAG Component Deep Dive 2: Query Transformation and Optimization

## 1. Overview

"Garbage in, garbage out." This famous saying applies equally to RAG systems. The original queries entered by users are often colloquial, ambiguous, and may even contain typos. Using such queries directly for retrieval often yields poor results. Query Transformation is a critical link in the RAG chain that acts as a bridge. It uses the intelligence of a Large Language Model (LLM) to analyze, restructure, and expand the original query, aiming to generate a set of "super queries" that are better suited for retrieval and can more effectively "squeeze out" information from the knowledge base.

The core query transformation component in this system is `QueryTransformer`.

## 2. `QueryTransformer`: Bridging User Language and Machine Language

The main responsibility of `QueryTransformer` is to close the "language gap" between user queries and the documents in the knowledge base. It includes two core functions: query expansion and query rewriting.

### 2.1. Query Expansion

**Goal**: To improve the **recall** of the retrieval process. That is, to find as many potentially relevant documents as possible, preferring to retrieve a few irrelevant ones rather than miss a single relevant one.

**Implementation Details**:

1.  **Generate Variants with an LLM**: Upon receiving a user query, `QueryTransformer` calls an LLM (e.g., a smaller, faster model, or an efficient one like GPT-3.5).
2.  **Well-designed Prompt**: It uses a prompt similar to the following to instruct the LLM:

    ```
    You are a professional retrieval assistant. Based on the following user question, generate 3 different but semantically equivalent queries. These queries should ask the question from different angles to allow for a more comprehensive search in the vector database.

    User question: "What are the common treatments for hypertension?"
    ```

3.  **Generate Multiple Sub-queries**: The LLM returns a set of queries, for example:
    - `"How to effectively treat high blood pressure?"`
    - `"What are the common pharmacological and non-pharmacological therapies for hypertension?"`
    - `"What are the recommended lifestyle changes and medical interventions for patients with hypertension?"`

4.  **Parallel Retrieval**: The subsequent `AdvancedFusionRetriever` receives these sub-queries and can search them in the vector database in parallel. This means a single user query actually triggers multiple backend retrievals, significantly increasing the probability of finding relevant information.

**Advantages**:
- **Overcomes Phrasing Differences**: Users may not know the professional terminology used in the knowledge base. Query expansion can generate variants that include these terms.
- **Uncovers Hidden Intent**: The LLM can understand the user's deeper intent and generate queries that reflect it.

### 2.2. Query Rewriting

**Goal**: To improve the **precision** of the retrieval process. That is, to increase the proportion of truly relevant documents among the retrieved results.

**Implementation Details**:

1.  **Optimize Query Structure**: Unlike query expansion, which generates multiple new queries, query rewriting aims to optimize the quality of a single query. It removes colloquialisms, adds context, and corrects grammatical errors to make it more like a "standard query."
2.  **Context-aware**: Query rewriting is especially important in multi-turn conversations. For example:
    - **User's first question**: `"What is hypertension?"`
    - **User's second question**: `"So how is it treated?"`

    Searching directly for `"So how is it treated?"` would yield chaotic results. When `QueryTransformer` receives the second question, it combines it with the previous conversation history and rewrites it as: `"What are the treatments for hypertension?"`. This new query, which contains the full context, is an effective input for retrieval.

3.  **LLM's Logical Reasoning**: This process is also completed by an LLM, which is instructed to understand the context of the conversation and generate a standalone, complete query statement.

### 2.3. Code Example (Pseudocode)

```python
class QueryTransformer:
    def __init__(self, llm_client):
        self.llm_client = llm_client

    def expand_query(self, query):
        prompt = f"Please generate 3 different query variations for the following question: {query}"
        # response is a list containing multiple queries
        expanded_queries = self.llm_client.generate(prompt)
        return expanded_queries

    def rewrite_query(self, query, chat_history):
        if not chat_history:
            return query

        context = "\n".join([f"Q: {turn['q']}\nA: {turn['a']}" for turn in chat_history])
        prompt = f"Based on the following conversation history, rewrite the last question into a standalone, complete query.\n\nHistory:\n{context}\n\nLast question: {query}"
        rewritten_query = self.llm_client.generate(prompt)
        return rewritten_query
```

## 3. Conclusion

`QueryTransformer` is a small but crucial component in the RAG system. By intelligently leveraging an LLM, it optimizes the input before retrieval begins, effectively providing higher-quality "ammunition" for the subsequent heavyweight operations of retrieval and reranking. This optimization step, achieved at a relatively low computational cost, significantly enhances the efficiency and effectiveness of the entire RAG chain and is a key practice in implementing high-performance RAG systems.