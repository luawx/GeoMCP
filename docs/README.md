# GeoMCP 开发计划

本目录保存 GeoMCP 的分步开发计划。

开发顺序：

1. Project Core
2. Permission / Path Sandbox
3. Python API
4. CLI
5. MCP
6. Job Manager
7. CPU Executor
8. GPU Executor
9. GPU Worker
10. DAS Basic
11. RAG
12. Research Memory
13. DAS Advanced
14. Catalog / HypoDD / NLLoc / MatchLocate
15. 集成验收与发布

核心架构边界：

- 1012 = Control Plane
- 1015 = GPU Compute Plane
- MCP、CLI、Python API 共享同一套 Service / Scientific Core
- 所有路径必须经过 Permission / Path Sandbox
- 原始科研数据默认只读
- Agent 不暴露 delete、任意 Shell、任意 SSH
- 长任务统一进入 Job Manager
- GPU 任务只能通过固定 Worker Registry 执行
- Reference Knowledge 与 Research Memory 分离

按编号依次开发，不建议跳过基础设施阶段直接堆积科研算法。
