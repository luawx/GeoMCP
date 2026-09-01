# Step 15 — 集成验收与发布

## 目标

确认 GeoMCP 已经从工具集合变成稳定、可追溯、安全的科研基础设施。

## 架构验收

确认：

```text
MCP
CLI
Python API
```

均调用同一 Service / Scientific Core。

## 安全验收

必须验证：

1. /etc 等越界目录拒绝
2. 其他用户目录拒绝
3. 原始科研数据写入拒绝
4. 无 delete 工具
5. 无 arbitrary shell
6. 无 arbitrary SSH
7. 1015 只能执行 Worker Registry 任务
8. Agent 无法修改 SSH endpoint
9. Agent 无法修改 allowed root
10. 输出只进入允许目录

## Job 验收

覆盖：

```text
queued
running
completed
failed
cancelled
```

以及 CPU Job、GPU Job、cancel、timeout、Worker failure、1015 unavailable。

## 端到端科研验收

执行：

```text
knowledge.search
↓
memory.search
↓
das.inspect
↓
das.read_window
↓
das.bandpass
↓
das.fk / detect
↓
catalog.inspect
↓
必要时定位程序
↓
研究结果
```

## 版本建议

```text
v0.1.0 基础设施 + 基础 DAS
v0.2.0 RAG
v0.3.0 Memory + Advanced DAS
v0.4.0 Seismology Wrappers
```

v0.4 稳定后再考虑 Persistent GPU Worker、Slurm、MultiGPU、Web UI、多用户权限等扩展。
