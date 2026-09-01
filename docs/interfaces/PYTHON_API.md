# Step 03 — Python API

## 目标

先建立程序化入口，后续 CLI 与 MCP 复用相同 Service，而不是重复实现逻辑。

## 固定调用链

```text
Python API
↓
Service
↓
Scientific Core
```

## 开发任务

建立：

```text
src/geomcp/api/
├── __init__.py
├── system.py
├── filesystem.py
└── jobs.py
```

当前 `jobs.py` 仅保留 Step 06 的公共 API 位置，不提前暴露任何 Job 操作。Job Manager 完成后再在该模块加入稳定接口。

后续再扩展：

```text
das.py
knowledge.py
memory.py
hypodd.py
nlloc.py
matchlocate.py
```

API 统一返回结构化结果：

```text
success
data
error_code
error_message
metadata
```

不得暴露：

```text
run_shell()
ssh_exec()
delete()
```

## 验收

Python 中能够直接调用 system / filesystem 基础能力，并且所有路径仍经过 Permission / Path Sandbox。
