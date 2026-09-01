# GeoMCP

GeoMCP 是一个面向地球物理科研服务器的统一工具与知识服务平台。

目标是把服务器上的 DAS 数据处理、波形与地震目录处理、HypoDD、NLLoc、MatchLocate、RAG、Research Memory 以及 CPU/GPU 计算能力，统一封装为可由以下入口调用的科研基础设施：

```text
Codex / AI Agent
人工 CLI
Python 脚本
```

## 当前状态

基础层 Step 01–05 已实现：

```text
Python API ─┐
CLI ────────┼──> Services + Permission / Path Sandbox
MCP ────────┘
```

当前 MCP 工具：

```text
system.status
filesystem.inspect
```

Job Manager、CPU/GPU Executor、DAS、RAG、Research Memory 和地震学 wrapper 将按 docs 中的后续步骤继续开发。

## 快速开始

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[test,mcp]"
pytest -q
geomcp system status --json
```

详细使用方法见 [docs/USAGE.md](docs/USAGE.md)。
不能连接公网的服务器部署见 [docs/OFFLINE_SERVER_DEPLOYMENT.md](docs/OFFLINE_SERVER_DEPLOYMENT.md)。

## 核心安全边界

- `/cluster/datapool2/xuxy/**` 默认可读
- 仅 `GeoMCP/runtime`、`GeoMCP/outputs`、`GeoMCP/knowledge` 默认可写
- 原始科研数据默认只读
- 不提供删除、任意 Shell、任意 SSH
- MCP、CLI、Python API 共用同一 Permission / Path Sandbox
- 1012 负责控制；后续由 Job Manager 向 1015 GPU Worker 调度，Agent 不直接操作 1015

开发计划见 [docs/README.md](docs/README.md)。
