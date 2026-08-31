# GeoMCP

GeoMCP 是一个面向地球物理科研服务器的统一工具与知识服务平台。

目标是把服务器上的 DAS 数据处理、波形与地震目录处理、HypoDD、NLLoc、MatchLocate、RAG、Research Memory 以及 CPU/GPU 计算能力，统一封装为可由以下入口调用的科研基础设施：

```text
Codex / AI Agent
人工 CLI
Python 脚本
```

## 核心架构

```text
Codex / CLI / Python
        ↓
      GeoMCP
        ↓
Scientific Core + Job Manager + Permission
        ↓
  CPU @ 1012 / GPU @ 1015
```

默认设计：

- 1012：Control Plane、MCP Server、Job Manager、Vector DB、CPU 任务
- 1015：GPU Compute Plane、Embedding、Reranker、GPU DAS
- MCP、CLI、Python API 共用同一套 Service / Scientific Core
- 原始科研数据默认只读
- Agent 不提供任意 Shell、任意 SSH、删除工具
- 长任务统一进入 Job Manager
- GPU 任务只能执行 Worker Registry 中注册的任务

## 开发状态

项目目前处于基础架构开发阶段。

详细开发顺序与每一步验收标准见：

[docs/README.md](docs/README.md)

## 推荐项目目录

```text
/cluster/datapool2/xuxy/GeoMCP
```

GeoMCP 的目标不是单纯为 Codex 编写服务器工具，而是建立一套人工和 AI Agent 都可以安全使用的地球物理科研基础设施。
