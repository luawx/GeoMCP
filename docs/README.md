# GeoMCP 开发计划

本目录保存 GeoMCP 的分步开发计划。每一步独立成文档，建议严格按编号推进。

## 当前实现状态

- [x] Step 01 — Project Core
- [x] Step 02 — Permission / Path Sandbox
- [x] Step 03 — Python API
- [x] Step 04 — CLI
- [x] Step 05 — MCP
- [ ] Step 06 — Job Manager
- [ ] Step 07 — CPU Executor
- [ ] Step 08 — GPU Executor
- [ ] Step 09 — GPU Worker
- [ ] Step 10 — DAS Basic
- [ ] Step 11 — RAG
- [ ] Step 12 — Research Memory
- [ ] Step 13 — DAS Advanced
- [ ] Step 14 — Catalog / HypoDD / NLLoc / MatchLocate
- [ ] Step 15 — 集成验收与发布

## 使用文档

- [基础使用指南](USAGE.md)
- [无外网服务器部署与 MCP 配置](OFFLINE_SERVER_DEPLOYMENT.md)

## 开发顺序

1. [Project Core](01_Project_Core.md)
2. [Permission / Path Sandbox](02_Permission_Path_Sandbox.md)
3. [Python API](03_Python_API.md)
4. [CLI](04_CLI.md)
5. [MCP](05_MCP.md)
6. [Job Manager](06_Job_Manager.md)
7. [CPU Executor](07_CPU_Executor.md)
8. [GPU Executor](08_GPU_Executor.md)
9. [GPU Worker](09_GPU_Worker.md)
10. [DAS Basic](10_DAS_Basic.md)
11. [RAG](11_RAG.md)
12. [Research Memory](12_Research_Memory.md)
13. [DAS Advanced](13_DAS_Advanced.md)
14. [Catalog / HypoDD / NLLoc / MatchLocate](14_Seismology_Wrappers.md)
15. [集成验收与发布](15_Integration_Release.md)

## 版本对应

```text
v0.1 = Step 01–10
v0.2 = Step 11
v0.3 = Step 12–13
v0.4 = Step 14
Release Gate = Step 15
```

## 总体原则

```text
Codex负责思考
Skills负责指导
MCP负责Agent接口
CLI负责人工接口
Python API负责程序接口
Scientific Core负责算法
Job Manager负责任务生命周期
Executor负责计算节点选择
Worker负责真正执行
1012负责控制
1015负责GPU计算
RAG负责外部知识
Research Memory负责内部经验
Permission负责安全边界
```

不要先开发大量科研算法，再补权限、接口和任务系统。
