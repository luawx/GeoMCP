# Workspace / Data Region

## 目标

Workspace 是 Path Sandbox 之上的一层“科研区域”抽象，让 Agent 可以决定输入和输出位置，但只能在管理员预先授权的区域内操作。

固定关系：

```text
Agent
  ↓ workspace + relative path
WorkspaceManager
  ↓
PathPolicy
  ↓
global read_roots / write_roots
  ↓
Scientific Service
```

Workspace **不能扩大** `paths.yaml` 的权限。它只能把全局允许范围进一步缩小。

## 配置文件

`config/workspaces.yaml`：

```yaml
workspaces:
  geomcp:
    description: Default GeoMCP research workspace
    read_root: /cluster/datapool2/xuxy
    write_root: /cluster/datapool2/xuxy/GeoMCP/outputs
```

每个 Workspace 当前采用一个 `read_root` 和一个 `write_root`。如果一个研究项目需要多个独立数据区，建议定义多个 Workspace，而不是让 Agent 自由组合任意根目录。

## 新增科研区域

例如希望 Agent：

- 从 `/cluster/datapool2/xuxy/DAS/2021Guangzhou/**` 读取；
- 只向 `/cluster/datapool2/xuxy/DAS/2021Guangzhou/processed/**` 写入。

先在 `config/paths.yaml` 授权全局写边界：

```yaml
read_roots:
  - /cluster/datapool2/xuxy

write_roots:
  - /cluster/datapool2/xuxy/GeoMCP/runtime
  - /cluster/datapool2/xuxy/GeoMCP/outputs
  - /cluster/datapool2/xuxy/GeoMCP/knowledge
  - /cluster/datapool2/xuxy/DAS/2021Guangzhou/processed
```

再在 `config/workspaces.yaml` 定义研究区域：

```yaml
workspaces:
  geomcp:
    description: Default GeoMCP research workspace
    read_root: /cluster/datapool2/xuxy
    write_root: /cluster/datapool2/xuxy/GeoMCP/outputs

  guangzhou_das:
    description: Guangzhou DAS project
    read_root: /cluster/datapool2/xuxy/DAS/2021Guangzhou
    write_root: /cluster/datapool2/xuxy/DAS/2021Guangzhou/processed
```

如果 `guangzhou_das.write_root` 没有位于任一全局 `write_roots` 内，`geomcp config validate` 会直接失败。

## Agent 使用方式

先查询：

```text
workspace.list
```

然后使用 Workspace 名和相对路径：

```text
workspace = "guangzhou_das"
path = "raw/event001.h5"
output_path = "processed/event001/filter.npy"
```

注意：`output_path` 是相对于 Workspace 的 `write_root`。如果 write root 本身已经是 `.../processed`，更推荐：

```text
output_path = "event001/filter.npy"
```

最终解析为：

```text
read:
/cluster/datapool2/xuxy/DAS/2021Guangzhou/raw/event001.h5

write:
/cluster/datapool2/xuxy/DAS/2021Guangzhou/processed/event001/filter.npy
```

## 安全规则

当提供 `workspace` 时：

1. `path` 和 `output_path` 必须是相对路径；
2. 绝对路径会被拒绝；
3. `../` 逃逸会被拒绝；
4. 符号链接越过 Workspace root 会被拒绝；
5. Workspace root 自身必须位于全局 PathPolicy 授权范围；
6. 原始数据是否可写仍由 `paths.write_roots` 决定；
7. 不提供删除能力。

不传 `workspace` 时，现有绝对路径接口保持兼容，仍直接经过 PathPolicy。

## CLI

```bash
geomcp workspace list --json

geomcp das inspect raw/event001.h5 \
  --workspace guangzhou_das --json

geomcp das bandpass raw/event001.h5 1 20 \
  --workspace guangzhou_das \
  --output-path event001/filter.npy \
  --channel-start 100 --channel-stop 120 \
  --sample-stop 5000 --json
```

## Python API

```python
from geomcp.api import das, workspace

regions = workspace.list_workspaces()

result = das.bandpass(
    "raw/event001.h5",
    workspace="guangzhou_das",
    freqmin=1,
    freqmax=20,
    output_path="event001/filter.npy",
)
```

## MCP

MCP 新增：

```text
workspace.list
```

当前 DAS 工具均支持可选 `workspace` 参数。MCP 不允许 Agent 传 `config_dir`，Workspace 配置只能由服务器管理员修改。

## 后续 Job / GPU 工具

HypoDD、NLLoc、MatchLocate、DAS Advanced 等长任务应在 Service 层先把 Workspace 相对路径解析成已经验证的路径，再提交给 JobManager。

推荐：

```text
Agent
  ↓ workspace + relative input/output
Service
  ↓ WorkspaceManager + PathPolicy
validated paths
  ↓
JobManager
  ↓
CPU/GPU Executor
```

Agent 不应通过 Job 参数指定任意远程工作目录、SSH host、port、username 或 executable。
