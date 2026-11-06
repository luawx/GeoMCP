# GeoMCP 开发路线图

## 当前实现状态

- [x] Step 01 — Project Core
- [x] Step 02 — Permission / Path Sandbox
- [x] Step 03 — Python API
- [x] Step 04 — CLI
- [x] Step 05 — MCP
- [x] Step 06 — Job Manager
- [x] Step 07 — CPU Executor
- [x] Step 08 — GPU Executor
- [x] Step 09 — GPU Worker
- [x] Step 10 — DAS Basic
- [x] Step 10.1 — v0.1 Hardening / Release Gate
- [x] Workspace / Data Region — Agent-controlled safe I/O regions
- [ ] Step 11 — RAG
- [ ] Step 12 — Research Memory
- [ ] Step 13 — DAS Advanced
- [ ] Step 14 — Catalog / HypoDD / NLLoc / MatchLocate
- [ ] Step 15 — 集成验收与发布

当前达到 `v0.1` 目标：Step 01–10。

## 使用与开发文档

- [基础使用指南](../getting-started/USAGE.md)
- [新增工具开发指南](TOOL_DEVELOPMENT.md)
- [无外网服务器部署与 MCP 配置](../deployment/OFFLINE_SERVER_DEPLOYMENT.md)

## 开发顺序

1. [Project Core](../architecture/PROJECT_CORE.md)
2. [Permission / Path Sandbox](../architecture/PERMISSION_PATH_SANDBOX.md)
3. [Python API](../interfaces/PYTHON_API.md)
4. [CLI](../interfaces/CLI.md)
5. [MCP](../interfaces/MCP.md)
6. [Job Manager](../architecture/JOB_MANAGER.md)
7. [CPU Executor](../architecture/CPU_EXECUTOR.md)
8. [GPU Executor](../architecture/GPU_EXECUTOR.md)
9. [GPU Worker](../architecture/GPU_WORKER.md)
10. [DAS Basic](../scientific/DAS_BASIC.md)
10.1. [v0.1 Hardening](V0_1_HARDENING.md)
11. [RAG](../scientific/RAG.md)
12. [Research Memory](../scientific/RESEARCH_MEMORY.md)
13. [DAS Advanced](../scientific/DAS_ADVANCED.md)
14. [Catalog / HypoDD / NLLoc / MatchLocate](../scientific/SEISMOLOGY_WRAPPERS.md)
15. [集成验收与发布](INTEGRATION_RELEASE.md)

## 版本对应

```text
v0.1 = Step 01–10
v0.2 = Step 11
v0.3 = Step 12–13
v0.4 = Step 14
Release Gate = Step 15
```


## 定位流程支线：拾取模块（2026-11-06）

本支线不更改既有版本编号，不将后续关联、定位或科学质量验收标记为完成。

- [x] 三类官方源码固定版本、来源校验和及许可证整理。
- [x] 参数预设/覆盖、输入契约、统一产物、Python/CLI/MCP 与 Job 集成。
- [x] STA/LTA 台站和 DAS 合成任务、跨块状态及外部 CSV 导入。
- [x] PhaseNet/PhaseNet-DAS 固定程序适配、模型登记与环境模板。
- [x] 回归测试、权限/篡改检查和原生输出保留测试。
- [ ] 深度学习真实权重与隔离环境登记、原生推理对照。
- [ ] 人工标注/独立噪声评价、科学门槛、资源及 CPU/GPU 基准。

当前验收记录与限制见[拾取模块开发文档](../scientific/PICKING_MODULE_DEVELOPMENT.md#0-当前实现与验证边界)；运行步骤见[使用指南](../getting-started/USAGE.md)。
