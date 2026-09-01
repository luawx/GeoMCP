# GeoMCP 新增工具开发指南

本文说明如何在 GeoMCP 中开发新的科学工具，并让同一项能力安全地被 Python API、人工 CLI 和 MCP/AI Agent 使用。当前 DAS Basic 是最完整的参考实现。

适用对象包括：

- DAS 新算法：FK、beamforming、去噪、事件检测等；
- 地震学程序封装：HypoDD、NLLoc、MatchLocate、catalog 工具；
- RAG / Research Memory；
- 其他需要 CPU 或 GPU 的科研工具。

---

## 1. 先理解 GeoMCP 的标准调用链

同步、耗时较短的工具优先采用：

```text
CLI / Python API / MCP
        ↓
      API
        ↓
   Service Layer
        ↓
 Scientific Core
        ↓
    科学计算库
```

需要长时间运行、CPU/GPU 调度或外部科学程序的工具采用：

```text
CLI / Python API / MCP
        ↓
      API
        ↓
   Service Layer
        ↓
    JobManager
        ↓
 CPU Executor / GPU Executor
        ↓
   Worker Registry
        ↓
  已注册的科学任务
```

### 各层职责

| 层 | 主要职责 | 不应该做的事 |
|---|---|---|
| Scientific Core | 科学算法、参数合法性、第三方库调用 | 不决定服务器权限，不直接暴露给 Agent |
| Service | capability 检查、Workspace/读写路径检查、默认输出目录、业务边界 | 不绕过 PathPolicy |
| API | 把异常转换成统一 `ApiResult` | 不复制科学算法 |
| CLI | 人工命令行入口 | 不直接调用 Scientific Core |
| MCP | Agent 工具定义、JSON Schema、上下文压缩 | 不暴露 config_dir / SSH / 任意 command |
| JobManager | 创建 Job、选择固定 Executor、持久化状态 | 不接受未注册 task type |
| Worker Registry | 白名单任务、严格 validator、timeout | 不执行任意 shell |

核心原则：**同一个能力只实现一次科学逻辑，CLI / Python / MCP 共用 Service 与安全策略。**

---

## 2. 开发前先判断工具属于哪一类

### A. 同步轻量工具

满足大多数条件时直接走 Scientific Core：

- 执行时间通常较短；
- 内存占用可控；
- 不需要跨节点；
- 不需要后台状态跟踪；
- 输入输出可以限制在安全大小。

例如当前：

- `das.inspect`
- `das.read_window`
- `das.rms`
- `das.bandpass`
- `das.plot`

### B. Job 工具

满足任意一项时优先使用 JobManager：

- 可能运行几十秒到数小时；
- 需要 GPU；
- 需要 1012 → 1015 调度；
- 需要进度、取消、结果查询；
- 调用外部科学程序；
- 生成多个中间文件；
- 失败后需要保留可审计状态。

HypoDD、NLLoc、MatchLocate、较重的 DAS 算法通常应设计为 Job。

### C. 外部可执行程序封装

外部程序不能设计成：

```text
tool(command="任意字符串")
```

正确方式是：

```text
结构化参数
   ↓
Service 验证
   ↓
生成固定格式配置文件
   ↓
JobManager
   ↓
Worker Registry 中已注册 handler
   ↓
调用服务器配置中固定的 executable
```

Agent 不得传：

- 任意 shell；
- 任意 SSH host / port / username；
- 任意 executable；
- 任意工作目录；
- 任意删除命令。

---

## 3. 新工具开始开发前必须先写清楚 8 件事

建议先做一个最小设计表：

| 项目 | 示例 |
|---|---|
| 工具命名空间 | `nlloc.*` |
| 是否同步 | 否，使用 Job |
| 输入 | catalog、pick 文件、速度模型 |
| 输出 | 定位目录、日志、统计 |
| 读权限 | 只允许 read roots |
| 写权限 | 只允许 outputs/runtime/knowledge |
| Executor | CPU 或 GPU，固定 |
| MCP 返回 | 摘要 + 输出文件路径，不返回巨大数组 |

另外必须确定：

1. 最大输入规模；
2. timeout；
3. 第三方依赖是否 optional dependency；
4. 失败时使用哪个 GeoMCP 异常；
5. 是否需要新增 capability；
6. MCP 是否需要 compact/preview；
7. 是否会修改原始科研数据；
8. 是否需要新增 Worker task。

---

## 4. 推荐文件结构

假设新增工具命名为 `example`：

```text
src/geomcp/
├── scientific/
│   └── example.py
├── services/
│   └── example.py
├── api/
│   └── example.py
├── cli/
│   └── main.py
├── mcp/
│   └── registry.py
└── worker/
    └── registry.py        # 仅 Job 工具需要

tests/
├── test_example.py
├── test_mcp_registry.py
└── ...                    # 必要时补 API/CLI/Job 测试

config/
├── permissions.yaml
├── paths.yaml
├── workspaces.yaml        # 可选；Agent 命名科研区域
├── geomcp.yaml            # 工具运行限制
└── executors.yaml         # 仅 Executor 相关配置
```

不要为 CLI 和 MCP 各写一份算法实现。

---

## 5. Step 1：实现 Scientific Core

参考：`src/geomcp/scientific/das.py`。

Scientific Core 应负责：

- 调第三方库；
- 数值计算；
- 科学参数合法性；
- 将底层异常转换成可理解的 `ScientificToolError`；
- 避免无界数据加载。

推荐模式：

```python
from geomcp.exceptions import ScientificToolError

def _dependency():
    try:
        import some_package
    except ImportError as exc:
        raise ScientificToolError(
            'Example support is not installed. Install the corresponding extra.'
        ) from exc
    return some_package

def run(path, *, parameter: float):
    if parameter <= 0:
        raise ScientificToolError("parameter must be > 0")

    lib = _dependency()
    result = lib.run(str(path), parameter=parameter)
    return {"value": result}
```

### 要求

- 大型可选依赖使用延迟 import，不要让基础 GeoMCP 因缺包无法启动。
- 对大数组设置硬限制。
- 对采样率、频率、窗口等做科学合法性检查。
- 不在这里决定 `/cluster/...` 是否允许访问；路径权限交给 Service。
- 不接受任意 shell 字符串。

---

## 6. Step 2：实现 Service Layer

参考：`src/geomcp/services/das.py`。

Service 是整个安全边界的核心。

如果工具允许 Agent 指定项目级输入/输出区域，应复用 `WorkspaceManager`，不要自己拼路径。规则是：

```text
workspace + relative path
↓
WorkspaceManager
↓
PathPolicy
↓
Scientific Core / JobManager
```

Workspace 只能缩小全局 `read_roots/write_roots`，不能扩大它。

典型结构：

```python
from pathlib import Path

from geomcp.config import load_config
from geomcp.scientific import example as core
from geomcp.services.permissions import PathPolicy

class ExampleService:
    def __init__(self, *, config_dir: str | Path | None = None):
        self.config = load_config(config_dir)
        self.policy = PathPolicy.from_config(self.config)

    def run(self, path, *, parameter: float):
        self.policy.assert_capability_allowed("example.run")
        input_path = self.policy.validate_read(path)
        return core.run(input_path, parameter=parameter)
```

如果产生文件：

1. 默认输出到 GeoMCP `outputs/`；
2. 使用 Workspace 时，输入/输出必须经过 `WorkspaceManager.resolve_read/resolve_write()`；
3. 用户指定绝对输出路径时仍必须 `validate_write()`；
4. 不覆盖 read-only 原始数据；
5. 不提供 delete。

### capability

在 `config/permissions.yaml` 中显式加入：

```yaml
allowed_capabilities:
  - example.run
```

当前策略是 `default_policy: deny`，所以忘记添加 capability 时应该失败，而不是自动放行。

---

## 7. Step 3：增加 Python API

参考：`src/geomcp/api/das.py`。

对外 API 统一返回：

```python
ApiResult(
    success=True/False,
    data=...,
    error_code=...,
    error_message=...,
    metadata=...
)
```

推荐结构：

```python
from geomcp.exceptions import GeoMCPError
from geomcp.models import fail, ok
from geomcp.services.example import ExampleService

def run(path, *, parameter, config_dir=None):
    try:
        data = ExampleService(config_dir=config_dir).run(
            path, parameter=parameter
        )
        return ok(data)
    except (GeoMCPError, OSError, ValueError, TypeError) as exc:
        return fail(type(exc).__name__.upper(), str(exc))
```

同时更新 `src/geomcp/api/__init__.py`。

Python API 可以接收 `config_dir`，因为这是服务器端/人工编程接口；**MCP 工具参数不能接收 config_dir**。

---

## 8. Step 4：增加 CLI

参考：`src/geomcp/cli/main.py`。

需要完成两处：

1. parser 中增加命令；
2. dispatch 中调用 API。

例如：

```text
geomcp example run INPUT --parameter 1.0 --json
```

CLI 应调用：

```text
cli → api → service → scientific
```

不要写成：

```text
cli → scientific
```

这样才能保证人工接口和 Agent 接口使用完全相同的安全规则。

---

## 9. Step 5：增加 MCP Tool

参考：`src/geomcp/mcp/registry.py`。

MCP Tool 必须有：

- 固定名称，例如 `example.run`；
- 清晰 description；
- 显式 JSON Schema；
- 必填参数；
- handler；
- 统一 output schema。

示意：

```python
def example_run(path: str, parameter: float):
    return example_api.run(
        path,
        parameter=parameter,
        config_dir=fixed_config,
    ).to_dict()

reg(
    "example.run",
    "Run the registered example operation.",
    example_run,
    {
        "path": {"type": "string"},
        "parameter": {"type": "number"},
    },
    ["path", "parameter"],
)
```

### Workspace 参数

对于需要项目级输入/输出的工具，可以加入可选：

```json
{
  "workspace": "guangzhou_das",
  "path": "raw/event001.h5",
  "output_path": "event001/result.dat"
}
```

有 `workspace` 时路径必须是相对路径；无 `workspace` 时可保留旧的绝对路径 API 以兼容人工脚本。

### MCP 的特殊限制

MCP registry 在 server 启动时固定 `config_dir`。不要把以下参数加入 tool schema：

- `config_dir`
- `host`
- `port`
- `username`
- `command`
- `ssh_command`
- 任意 task type

### 大结果必须压缩

当前 `das.read_window` 会在 MCP 层把完整二维数组转换成：

- metadata；
- shape；
- point_count；
- preview；
- preview_shape；
- truncated。

新工具如果可能返回大型数组、长日志或大量 catalog，也要做类似 compact，而不是把完整内容塞进 Agent context。

---

## 10. Step 6：如果是长任务，注册 Worker Task

参考：`src/geomcp/worker/registry.py`。

所有 Job task 必须在 `TaskRegistry` 白名单中。

示意：

```python
def _validate_example(input_data, parameters):
    unknown = set(parameters) - {"parameter"}
    if unknown:
        raise WorkerError(f"Unknown parameters: {sorted(unknown)}")

    value = float(parameters["parameter"])
    if not 0 < value <= 100:
        raise WorkerError("parameter out of range")

def _run_example(input_data, parameters):
    ...
    return {"output_path": "...", "summary": {...}}

r.register(
    TaskDefinition(
        "example.run",
        "cpu",
        _run_example,
        timeout=600.0,
        validator=_validate_example,
    )
)
```

### validator 必须严格

必须拒绝：

- 未知字段；
- 超范围值；
- 不允许的路径；
- 与 task 不匹配的 executor；
- 用户提供的可执行命令。

`JobManager.submit()` 会先通过 `build_task_registry().get(task_type)` 获取已注册任务，并强制任务要求的 executor 与实际 executor 一致。

---

## 11. Step 7：Service 通过 JobManager 提交长任务

典型模式：

```python
return JobManager(config_dir=self.config_dir).submit(
    task_type="example.run",
    executor="cpu",
    tool="example.run",
    input={"path": str(input_path)},
    parameters={"parameter": parameter},
).to_dict()
```

Job 状态由 GeoMCP 持久化为：

```text
queued
running
completed
failed
cancelled
```

不要自己再实现第二套 Job 状态机。

GPU 工具同理，只是任务定义为 `executor="gpu"`。GPU host / port / username 必须来自服务器端 `config/executors.yaml`。

---

## 12. Step 8：处理第三方依赖

如果工具需要新 Python 包，在 `pyproject.toml` 中增加 optional dependency。

例如：

```toml
[project.optional-dependencies]
example = ["some-package>=1,<2"]
```

开发/测试环境再决定是否加入 `all` 或 CI。

原则：

- 基础 CLI 不应被重型科研依赖拖死；
- 第三方包缺失时返回明确错误；
- 版本范围不要完全不锁定；
- 外部二进制程序不要由 Agent 动态下载或指定路径。

---

## 13. Step 9：测试

新工具至少应覆盖以下测试层。

### Scientific Core

测试：

- 正常参数；
- 边界参数；
- 非法科学参数；
- 大输入限制；
- 第三方库异常。

### Permission / Service

测试：

- read root 内可以读取；
- read root 外拒绝；
- write root 内可以写；
- 原始科研数据目录不能写；
- capability 未授权时拒绝。

### API

测试：

- success 结构；
- error_code / error_message；
- 不把异常直接抛给普通调用方。

### CLI

至少测试：

```text
geomcp <tool> ...
geomcp <tool> ... --json
```

并检查 exit code。

### MCP

检查：

- tool 已注册；
- input schema；
- required 参数；
- 没有 `config_dir/host/port/command`；
- 大结果已经 compact。

### Job / Worker

如果使用 Job：

- task 未注册时拒绝；
- executor 不匹配时拒绝；
- validator 拒绝未知参数；
- completed / failed / cancelled 状态正确；
- CPU/GPU healthcheck 仍可通过。

完整测试：

```bash
python -m pip install -e ".[test,mcp,das]"
pytest -q
```

加入新 optional dependency 后，把对应 extra 加到开发安装命令或 CI。

---

## 14. Step 10：更新文档与 Skill

新增一类 Agent 可直接使用的工具后，至少更新：

1. `docs/scientific/` 下对应领域文档；
2. `docs/getting-started/USAGE.md` 中的用户命令；
3. `docs/development/ROADMAP.md` 中的实现状态；
4. `skills/geomcp/SKILL.md` 中的正确调用顺序和限制；
5. 根 `README.md` 中的 MCP Tool 清单（如果是公开 MCP 工具）。

Skill 只负责教 Agent 如何正确使用工具，不负责实现权限。真正的权限必须在 Service / PathPolicy / Registry 中强制执行。

---

## 15. 外部地震学程序的推荐封装方式

对于 HypoDD / NLLoc / MatchLocate，推荐每个工具拆成三部分：

```text
输入检查
  ↓
准备工作目录和配置文件
  ↓
注册 Job 执行
  ↓
解析结果
  ↓
返回 summary + output paths
```

例如 MCP 不应返回整个定位输出文件，而应返回：

```json
{
  "job_id": "...",
  "status": "completed",
  "summary": {
    "event_count": 758,
    "failed_count": 0
  },
  "outputs": {
    "catalog": "...",
    "log": "..."
  }
}
```

详细文件由后续工具读取，Agent 上下文只保留必要摘要。

---

## 16. PR 前检查清单

提交 PR 前逐项确认：

- [ ] Scientific Core 与 Service 已分层；
- [ ] 所有输入路径经过 `validate_read()`，或 WorkspaceManager 后再进入 PathPolicy；
- [ ] 所有输出路径经过 `validate_write()`，或 WorkspaceManager 后再进入 PathPolicy；
- [ ] Workspace 不能扩大全局 read/write roots；
- [ ] 新 capability 已显式加入权限配置；
- [ ] 没有 delete / arbitrary shell / arbitrary SSH；
- [ ] MCP 没有暴露服务器配置参数；
- [ ] Job task 已加入 Worker Registry 白名单；
- [ ] validator 拒绝未知字段；
- [ ] GPU endpoint 仍完全由服务器配置固定；
- [ ] 大数组 / 大日志不会直接进入 MCP context；
- [ ] CLI / Python / MCP 复用同一 Service；
- [ ] 单元测试覆盖成功与拒绝路径；
- [ ] `pytest -q` 通过；
- [ ] 使用文档、领域文档、Skill 已更新。

---

## 17. 最小开发顺序

以后开发一个新的工具，建议固定按下面顺序：

```text
1. 定义输入/输出和安全边界
2. scientific/<tool>.py
3. services/<tool>.py
4. permissions.yaml
5. api/<tool>.py
6. CLI
7. MCP Registry
8. 若为长任务：Worker Registry + JobManager
9. tests
10. docs + skill
11. pytest -q
12. PR
```

不要从 MCP handler 直接开始写科学逻辑。先把 Scientific Core 和 Service 做正确，后面的 CLI / Python / MCP 都只是同一能力的不同入口。
