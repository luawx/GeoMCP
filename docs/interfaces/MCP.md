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

## 当前基础工具

```text
system.status
filesystem.inspect
workspace.list
```

Job 与 DAS 工具也由同一 Registry 暴露。

## Workspace / Data Region

Agent 需要指定项目级输入/输出区域时，应先调用：

```text
workspace.list
```

然后在 DAS 等支持 Workspace 的工具中传：

```text
workspace="guangzhou_das"
path="raw/event001.h5"
output_path="event001/filter.npy"
```

有 `workspace` 时，路径必须是相对路径。绝对路径、`../` 逃逸和符号链接越界由服务器端 WorkspaceManager + PathPolicy 拒绝。

Workspace 配置只由服务器管理员维护，MCP 不允许 Agent 修改 Workspace root。

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
- `config_dir`
- 任意 host / port / username

## Skills

`skills/geomcp/` 负责告诉 Agent 正确调用顺序：

- 不直接 SSH 1015
- 不下载完整大型 DAS
- 长任务使用 Job
- 不删除服务器文件
- 不访问 allowed root 外目录
- 使用 Workspace 时只传相对路径
- 不自行构造或猜测 Workspace 名

## 验收

测试必须覆盖：

1. Registry 只包含预期安全工具。
2. MCP Server 从 Registry 自动注册。
3. Client 能发现并调用 `workspace.list` 与 `filesystem.inspect`。
4. 非法路径仍由 Permission / Path Sandbox 拒绝。
5. Workspace 绝对路径和路径逃逸被拒绝。

这样后续新增工具只修改 Registry 和对应 API/Service，不需要同步修改 Server 工具列表。
