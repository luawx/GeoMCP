# GeoMCP 基础使用指南（Step 01–05）

当前基础版本实现 Project Core、Permission / Path Sandbox、Python API、CLI 和 MCP。
Job Manager、CPU/GPU Executor、DAS、RAG、Research Memory 尚未进入本版本。

## 1. 安装

开发环境：

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[test,mcp]"
pytest -q
```

只需要 CLI / Python API：

```bash
python -m pip install -e .
```

需要 MCP：

```bash
python -m pip install -e ".[mcp]"
```

## 2. 配置目录

默认读取仓库中的 `config/`。也可以显式指定：

```bash
export GEOMCP_HOME=/cluster/datapool2/xuxy/GeoMCP
export GEOMCP_CONFIG_DIR=/cluster/datapool2/xuxy/GeoMCP/config
```

`config/paths.yaml` 默认：

```yaml
read_roots:
  - /cluster/datapool2/xuxy
write_roots:
  - /cluster/datapool2/xuxy/GeoMCP/runtime
  - /cluster/datapool2/xuxy/GeoMCP/outputs
  - /cluster/datapool2/xuxy/GeoMCP/knowledge
```

含义：`/cluster/datapool2/xuxy/**` 可以读取，但只有 GeoMCP 的 runtime / outputs / knowledge 可以写入。
原始科研数据默认只读。

## 3. Python API

```python
from geomcp.api.system import status
from geomcp.api.filesystem import inspect

print(status().to_dict())
print(inspect("/cluster/datapool2/xuxy/example.dat").to_dict())
```

统一返回字段：

```text
success
data
error_code
error_message
metadata
```

## 4. CLI

```bash
geomcp system status
geomcp system status --json
geomcp config show
geomcp config validate
geomcp filesystem inspect /cluster/datapool2/xuxy
```

指定另一套配置：

```bash
geomcp --config-dir /path/to/config system status --json
```

非法路径会返回非 0 exit code：

```bash
geomcp filesystem inspect /etc/passwd --json
```

## 5. MCP

启动 stdio MCP Server：

```bash
geomcp-mcp
```

或者：

```bash
python -m geomcp.mcp.server
```

目前暴露：

```text
system.status
filesystem.inspect
```

MCP 不提供 `delete`、任意 shell、任意 SSH 或任意 executable path。

## 6. 当前架构

```text
Python API ─┐
CLI ────────┼──> Service / Permission ──> Server filesystem
MCP ────────┘
```

后续 Step 06 开始增加 Job Manager。GPU 节点不会直接暴露给 Agent。
