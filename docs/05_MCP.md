# Step 05 — MCP

## 目标

建立 Codex / AI Agent 的标准调用入口。

## 固定调用链

```text
Codex
↓
MCP Tool
↓
Service
↓
Scientific Core
```

MCP 层不实现科研算法。

## 第一批工具

```text
system.status
filesystem.inspect
```

后续再注册 Job、DAS、RAG、Memory 和定位工具。

## 工具注册

使用显式 Registry，每个工具定义：

```text
name
description
input schema
output schema
handler
```

MCP 输入不能包含：

- 任意 shell command
- 任意 SSH command
- 任意 executable path

## Skills

建立 `skills/geomcp/`，写入总体安全规则：

- 不直接 SSH 1015
- 不下载完整大型 DAS
- 长任务使用 Job
- 不删除服务器文件
- 不访问 allowed root 外目录

## 验收

Codex 能发现并调用基础 MCP 工具，非法路径由服务器端权限系统拒绝。
