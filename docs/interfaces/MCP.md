# Step 05 — MCP

## 目标

建立 Codex / AI Agent 的标准调用入口。

## 固定调用链

```text
Codex
↓
MCP Tool Registry
↓
MCP Server Adapter
↓
Python API / Service
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

`src/geomcp/mcp/registry.py` 是工具清单的唯一来源。Server 启动时遍历 Registry 注册工具，不允许在 `server.py` 再维护一份独立工具列表。

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

测试必须覆盖：

1. Registry 只包含预期安全工具。
2. MCP Server 从 Registry 自动注册。
3. 使用 MCP SDK Client 建立连接后能够发现工具并调用 `filesystem.inspect`。
4. 非法路径仍由服务器端 Permission / Path Sandbox 拒绝。

这样后续新增工具只修改 Registry 和对应 API/Service，不需要同步修改 Server 工具列表。
