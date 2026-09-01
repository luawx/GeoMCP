# GeoMCP 使用指南（Step 01–05）

本文对应当前已完成的 Step 01–05，只介绍现阶段已经存在的能力。

## 1. 配置目录

GeoMCP 读取 5 个配置文件：

```text
config/
├── geomcp.yaml
├── paths.yaml
├── permissions.yaml
├── executors.yaml
└── rag.yaml
```

推荐在服务器设置：

```bash
export GEOMCP_CONFIG_DIR=/cluster/datapool2/xuxy/GeoMCP/config
```

如果使用 wheel 安装，这个环境变量必须指向部署包中保留的 `config/` 目录。

## 2. 当前路径权限

默认允许读取：

```text
/cluster/datapool2/xuxy/**
```

默认允许写入的根目录：

```text
/cluster/datapool2/xuxy/GeoMCP/outputs/**
/cluster/datapool2/xuxy/GeoMCP/runtime/**
/cluster/datapool2/xuxy/GeoMCP/knowledge/**
```

Step 01–05 尚未暴露通用写文件 API。写目录现在先作为后续 Job/RAG/Memory 的安全边界保留。

以下能力固定关闭：

```text
delete
recursive_delete
arbitrary_shell
arbitrary_ssh
```

`config validate` 会在这些危险能力被人为改为 `true` 时直接失败。

## 3. CLI

验证配置：

```bash
geomcp config validate
```

查看当前状态：

```bash
geomcp system status
```

查看配置：

```bash
geomcp config show
```

检查允许范围内的文件或目录：

```bash
geomcp filesystem inspect /cluster/datapool2/xuxy
```

脚本调用可以增加：

```bash
geomcp --json system status
```

越界访问会返回非 0 exit code，例如：

```bash
geomcp filesystem inspect /etc/passwd
```

## 4. Python API

```python
from geomcp.api import inspect_path, system_status

print(system_status().to_dict())
print(inspect_path("/cluster/datapool2/xuxy").to_dict())
```

统一结果结构：

```text
success
data
error_code
error_message
metadata
```

## 5. MCP

启动 stdio MCP Server：

```bash
geomcp-mcp
```

当前只注册两个工具：

```text
system.status
filesystem.inspect
```

MCP 层只调用 Python API / Service，不单独实现文件系统逻辑，因此 CLI、Python API 与 MCP 使用同一套 Path Sandbox。

## 6. 当前阶段限制

Step 06 之前没有 Job Manager；Step 08–09 之前没有 1015 GPU 调度。因此当前不要把长任务或 GPU 任务直接塞进基础 MCP 工具，也不要给 MCP 增加任意 SSH/Shell 参数。

无外网服务器的完整安装与 Codex 连接方法见 [OFFLINE_SERVER_DEPLOYMENT.md](OFFLINE_SERVER_DEPLOYMENT.md)。
