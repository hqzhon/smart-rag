# RAG组件详解之一：智能文档处理（修订版）

## 1. 概述

文档处理是RAG系统的入口和基石。处理质量直接决定了知识库的质量，进而影响整个系统的最终表现。本系统的文档处理流程包含两个核心组件：`EnhancedPDFProcessor`（增强PDF处理器）和`MedicalTextSplitter`（医疗文本分块器），旨在从原始PDF文档中提取最丰富、最干净、最易于检索的信息。

## 2. `EnhancedPDFProcessor`：超越文本提取

`EnhancedPDFProcessor`的目标是将一个PDF文档彻底“解构”，提取其所有有价值的信息，而不仅仅是纯文本。

- **核心依赖**：基于强大的`unstructured`库，它能够解析复杂的文档格式，识别文本、表格、图片等多种元素。
- **实现细节**：通过先进的版面分析，它能智能地重组内容，并为每个内容块注入来源、页码等关键元数据，为后续的答案溯源提供支持。

## 3. `MedicalTextSplitter`：双模递归的文本切分策略

在文本提取之后，如何将长文本切分成大小适中、语义连贯的“块”（Chunks）是至关重要的一步。本系统采用`MedicalTextSplitter`作为总的切分“调度器”，它内置了两种核心策略：**语义分块**和**传统递归分块**，以兼顾智能与稳定。

### 3.1. 双模调度：智能与传统的结合

`MedicalTextSplitter`并非单一的算法，而是一个可配置的调度器。它通过`enable_semantic`配置项，来决定使用哪种分块模式：

- **语义模式（Semantic Mode）**：当`enable_semantic`为`True`（默认）时，系统会启用`HybridTextSplitter`，进行高质量的语义分块。这是首选的高级策略。
- **传统模式（Traditional Mode）**：当`enable_semantic`为`False`，或`HybridTextSplitter`因故（如模型加载失败）无法初始化时，系统会自动降级，采用稳定可靠的传统递归分块策略作为后备（Fallback）。

### 3.2. 策略一：`HybridTextSplitter`（混合语义分块）

这是系统的首选智能分块策略，其核心思想是**结合结构和语义来寻找最佳断点**。

- **原理**：它首先会使用一组常规的分隔符（如换行符）进行初步的文本分割。然后，它会使用句子嵌入模型（Sentence Embedding Model）来计算这些初步分割后相邻句子之间的语义相似度。当相似度出现一个明显的“低谷”时，意味着此处可能是一个新的话题，因此是一个理想的切分点。
- **优势**：通过这种方式切分出的文本块，语义更加完整和内聚，极大地提升了后续向量检索的准确性。

### 3.3. 策略二：传统递归分块

这是系统的后备（Fallback）策略，其核心是**基于一组预设的分隔符进行循环（递归）切分**，确保了即使在没有AI模型的情况下，切分任务也能稳定完成。

#### 实现细节：“循环分割”的艺术

该策略的精髓在于`_split_text_with_separators`这个递归函数。其工作流程如下：

1.  **分隔符优先级列表**：系统预定义了一个有序的分隔符列表，优先级从高到低，例如：`["\n##SECTION_START_", "\n\n", "。\n", ".\n", " ", ...]`。这个顺序至关重要，因为它代表了从最强的结构边界（章节）到最弱的边界（空格）的尝试顺序。

2.  **递归下降（Recursive Descent）**：
    - **第一轮尝试**：函数首先尝试使用列表中优先级最高的分隔符（`\n##SECTION_START_`）来切分整个文本。
    - **检查子块大小**：切分后，它会检查每一个产生的子块（sub-split）。
    - **进入下一轮循环**：如果某个子块的长度仍然**超过**预设的`chunk_size`，函数会**带着这个过长的子块**，调用**自身**，但这一次传入的是**优先级次一级**的分隔符列表（即从`\n\n`开始）。
    - **递归终止**：这个“切分 -> 检查 -> 再切分”的循环会一直持续下去，直到所有子块的长度都小于`chunk_size`，或者所有分隔符都已用尽。

#### 代码示例（伪代码）

```python
class MedicalTextSplitter:
    def _split_text_with_separators(self, text, separators):
        # 如果没有分隔符了，或文本已经够小，则返回
        if not text or not separators:
            return [text]

        # 取出当前最高优先级的分割符
        separator = separators[0]
        remaining_separators = separators[1:]

        # 用最高优先级的分割符进行切分
        splits = text.split(separator)

        results = []
        for sub_split in splits:
            # 检查切分后的子块是否仍然过长
            if len(sub_split) > self.chunk_size:
                # 如果过长，则对这个子块进行下一轮“循环”
                # 注意：传入的是剩余的、优先级更低的分隔符
                deeper_splits = self._split_text_with_separators(sub_split, remaining_separators)
                results.extend(deeper_splits)
            else:
                # 如果子块大小合适，则接受它
                results.append(sub_split)
        return results
```

## 4. 总结

`MedicalTextSplitter`通过其**双模调度**的设计，完美地平衡了智能化与鲁棒性。它优先使用先进的`HybridTextSplitter`进行高质量的语义分块，同时保留了稳定可靠的**传统递归分块**作为后备。特别是其递归分块策略中精巧的“循环分割”逻辑，确保了无论文本结构多么复杂，最终都能被切分成符合要求的大小，为构建高质量的知识库提供了坚实的保障。