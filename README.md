# GeoMCP

GeoMCP 是面向地球物理科研服务器的安全工具与知识服务平台，让 Codex / AI Agent、人工 CLI 和 Python 脚本共享同一套权限、任务和科学计算接口。

## 当前状态：v0.1（Step 01–10）

已实现：

```text
Permission / Path Sandbox
Workspace / Data Region I/O
Python API + CLI + MCP
Job Manager (SQLite + JSON mirror)
Local CPU Executor
Fixed-endpoint Remote GPU Executor
GPU Worker Registry
DAS Basic (DASPy)
Picking (STA/LTA + registered PhaseNet / PhaseNet-DAS adapters)
```

当前 MCP 工具：

```text
system.status
filesystem.inspect
workspace.list
job.list
job.status
job.result
job.cancel
job.submit_healthcheck
das.inspect
das.read_window
das.bandpass
das.rms
das.plot
picking.backends
picking.presets
picking.inspect
picking.prepare
picking.validate
picking.run
picking.result
picking.import
```

## v0.1 封板状态

Step 10.1 Hardening 已补齐：CI 全量 DAS 依赖、SQLite 原子 Job 状态转换、dispatch watchdog、MCP 固定配置边界、CPU/GPU healthcheck 闭环、DASPy 真正按 channel/sample 窗口读取，以及 MCP DAS 窗口结果压缩。

在此基础上加入 Workspace / Data Region：Agent 可以选择管理员配置的科研区域并使用相对输入/输出路径，但 Workspace 不能扩大全局 Path Sandbox。

MCP 不接受 `config_dir`、host、port、username、command 或任意 task type。

## 安装

基础 CLI / Python API：

```bash
python -m pip install -e .
```

MCP：

```bash
python -m pip install -e ".[mcp]"
```

DASPy 支持：

```bash
python -m pip install -e ".[das]"
```

开发与拾取模块回归：

```bash
python -m pip install -e ".[test,mcp,das,picking]"
pytest -q
```

## 安全边界

- `/cluster/datapool2/xuxy/**` 默认可读
- 仅 GeoMCP `runtime/outputs/knowledge` 默认可写
- 原始科研数据默认只读
- Agent 可通过 Workspace 使用相对输入/输出路径，但 Workspace 不能扩大全局 Path Sandbox
- 不暴露 delete、任意 Shell、任意 SSH
- GPU endpoint 只能由服务器配置指定，Agent 不能传 host/port/user/command
- Worker 只执行 Registry 白名单任务
- DAS 大窗口和超过 Nyquist 的滤波会被拒绝

1012 作为控制侧；GPU Executor 默认关闭，配置固定 endpoint 后由 1012 把 Job ID 转发给 1015 Worker。

## 文档

- [文档总览](docs/README.md)
- [基础使用指南](docs/getting-started/USAGE.md)
- [Workspace / Data Region](docs/architecture/WORKSPACES.md)
- [新增工具开发指南](docs/development/TOOL_DEVELOPMENT.md)
- [开发路线图](docs/development/ROADMAP.md)
- [离线服务器部署](docs/deployment/OFFLINE_SERVER_DEPLOYMENT.md)


## 离线拾取模块

已接入统一 Python/CLI/MCP、参数预设与覆盖、权限检查、Job 执行、规范 CSV/JSON 输出及外部拾取导入。STA/LTA 输出 unknown 触发，不能直接当作 P/S 到时用于定位。

| 后端 | 当前工程状态 | 验收边界 |
|---|---|---|
| STA/LTA | miniSEED / DAS HDF5 可运行，支持跨块状态 | 合成后台 Job 已验证，真实数据阈值与质量仍需评测 |
| PhaseNet | 固定源码、模型登记和隔离环境适配已实现 | 需登记真实权重、验证环境和原生推理结果 |
| PhaseNet-DAS | 固定源码、时间/空间分块和适配已实现 | 需登记真实权重、验证环境和原生推理结果 |

安装读取依赖：`python -m pip install -e ".[picking]"`。管理员在 `config/picking.yaml` 显式启用执行配置、资源上限及模型；默认关闭，不自动下载权重。先发现 backends/presets，再 inspect、prepare、validate、run，最后通过 result 获取摘要与产物引用；输入或配置改变后重新 prepare。

合成示例（目标目录必须未占用）：

```powershell
.\.venv\Scripts\python.exe scripts/picking_demo.py --output-dir outputs/picking-demo --run
```

示例通过真实后台任务验证台站拾取、DAS 拾取和外部 CSV 导入。预览默认 20 行、最多 100 行，MCP 响应上限 64 KiB。真实数据精度、吞吐及显存基准尚未验收。

详见[拾取开发与实现状态](docs/scientific/PICKING_MODULE_DEVELOPMENT.md)、[源码来源与环境说明](third_party/README.md)和[使用指南](docs/getting-started/USAGE.md)。
