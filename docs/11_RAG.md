# Step 11 — RAG

## 目标

建立完全运行在服务器端的论文与参考知识检索系统。

## 架构

```text
PDF / Markdown / Notes
↓
Parser
↓
Chunker
↓
Embedding @ 1015
↓
Vector DB @ 1012
↓
Retriever
↓
Reranker @ 1015
↓
Top-K Context
```

推荐：

```text
Embedding: BAAI/bge-m3
Reranker: BAAI/bge-reranker-v2-m3
```

## Metadata

至少保存：

```text
document_id
chunk_id
title
authors
year
source
page
section
project
collection
knowledge_type
created_at
updated_at
```

## 接口

MCP：

```text
knowledge.search
knowledge.get_chunk
knowledge.get_document
knowledge.list_sources
knowledge.add_document
knowledge.add_text
knowledge.reindex
knowledge.update_metadata
knowledge.stats
```

默认不暴露 `knowledge.delete`。

## 检索流程

```text
Vector Search Top 30~50
↓
Reranker
↓
Top 5~10
```

避免大量低相关 Chunk 进入 Agent 上下文。

## 验收

准备测试论文，验证文档添加、Embedding、Vector Search、Rerank、source/page metadata 全链路。
