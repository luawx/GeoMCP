# GeoMCP

GeoMCP 是面向地球物理科研服务器的安全工具与知识服务平台，让 Codex / AI Agent、人工 CLI 和 Python 脚本共享同一套权限、任务和科学计算接口。

## 当前状态：v0.1（Step 01–10）

已实现：

```text
Permission / Path Sandbox
Python API + CLI + MCP
Job Manager (SQLite + JSON mirror)
Local CPU Executor
Fixed-endpoint Remote GPU Executor
GPU Worker Registry
DAS Basic (DASPy)
```

当前 MCP 工具：

```text
system.status
filesystem.inspect
job.list
job.status
job.result
job.cancel
das.inspect
das.read_window
das.bandpass
das.rms
das.plot
```

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

开发与完整 v0.1：

```bash
python -m pip install -e ".[test,mcp,das]"
pytest -q
```

## 安全边界

- `/cluster/datapool2/xuxy/**` 默认可读
- 仅 GeoMCP `runtime/outputs/knowledge` 默认可写
- 原始科研数据默认只读
- 不暴露 delete、任意 Shell、任意 SSH
- GPU endpoint 只能由服务器配置指定，Agent 不能传 host/port/user/command
- Worker 只执行 Registry 白名单任务
- DAS 大窗口和超过 Nyquist 的滤波会被拒绝

1012 作为控制侧；GPU Executor 默认关闭，配置固定 endpoint 后由 1012 把 Job ID 转发给 1015 Worker。

详细使用见 [docs/USAGE.md](docs/USAGE.md)，离线服务器部署见 [docs/OFFLINE_SERVER_DEPLOYMENT.md](docs/OFFLINE_SERVER_DEPLOYMENT.md)，开发状态见 [docs/README.md](docs/README.md)。
