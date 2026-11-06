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


## Workspace / Data Region

新增：

```python
from geomcp.api import workspace, das

regions = workspace.list_workspaces()

result = das.bandpass(
    "raw/event001.h5",
    workspace="guangzhou_das",
    freqmin=1,
    freqmax=20,
    output_path="event001/filter.npy",
)
```

当 `workspace` 不为空时，DAS 输入/输出路径必须是相对路径，并由 Service 层的 WorkspaceManager + PathPolicy 双重校验。Python API 仍保留原有绝对路径模式以兼容人工脚本。


## Picking offline workflow

Picking now shares the Python/CLI/MCP service, workspace/path checks and Job Manager.
Install optional readers with `pip install -e ".[picking]"`. Administrators must
explicitly register picking.yaml, versioned presets, fixed model environments and
hard resource limits. Missing configuration disables picking without blocking base
services. Models/weights are never downloaded automatically.

Discover picking.backends/presets, inspect waveform/geometry inputs, prepare a frozen
configuration, validate it, then submit picking.run. Follow job.status/job.cancel
and retrieve picking.result artifact references. Input/config changes require a new
prepare. Preview default is 20, maximum 100; interface responses are capped at 64 KiB.
STA/LTA emits unknown triggers, which are not P/S observations for location.
Implementation and synthetic fixtures do not establish scientific acceptance: real
data precision/recall, false alarms, throughput and memory benchmarks remain needed.

```python
from geomcp.api import picking

available = picking.backends(config_dir="config")
prepared = picking.prepare("inputs/waveforms.json", "inputs/geometry.json",
    "station-stalta-demo", preset_version="1", workspace="research", config_dir="config")
if prepared.success:
    checked = picking.validate(prepared.data["prepared_ref"], workspace="research", config_dir="config")
    if checked.success:
        submitted = picking.run(prepared.data["prepared_ref"], workspace="research", config_dir="config")
```

All calls return ApiResult; check success/error fields before reading data.
Other functions: presets(backend_id=None), inspect(waveform_manifest_ref,
geometry_ref=None, workspace=None, preview_limit=20), result(job_id, preview_limit=20),
import_picks(input_ref, geometry_ref, format="external_csv", mapping=None,
output_path=None, workspace=None). All accept server-side config_dir.
