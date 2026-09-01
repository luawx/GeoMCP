# GeoMCP v0.1 使用指南（Step 01–10）

## 1. 安装

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[mcp,das]"
```

DAS 使用 DASPy；PyPI 包名 `daspy-toolbox`，import 名 `daspy`。

## 2. 配置

```bash
export GEOMCP_HOME=/cluster/datapool2/xuxy/GeoMCP
export GEOMCP_CONFIG_DIR=/cluster/datapool2/xuxy/GeoMCP/config
geomcp config validate
```

默认路径策略：整个 `/cluster/datapool2/xuxy` 可读，仅 GeoMCP 的 runtime / outputs / knowledge 可写。

GPU 默认关闭。部署前由管理员在 `config/executors.yaml` 设置固定 endpoint；MCP 工具本身没有 host/port/user/command 参数。

## 3. 基础接口

```bash
geomcp system status --json
geomcp filesystem inspect /cluster/datapool2/xuxy --json
```

Python：

```python
from geomcp.api.system import status
from geomcp.api.filesystem import inspect
```

## 4. Job Manager

```bash
geomcp job list --json
geomcp job status JOB_ID --json
geomcp job result JOB_ID --json
geomcp job logs JOB_ID
geomcp job cancel JOB_ID --json
geomcp job healthcheck --executor cpu --json
geomcp job healthcheck --executor gpu --json
```

Job 状态：`queued / running / completed / failed / cancelled`。取消不删除任何科研数据。

受控任务由内部 Scientific Service / JobManager 提交，不提供“任意命令提交”工具。对外只增加严格白名单的 CPU/GPU healthcheck，用于验证 Executor/Worker 链路。

## 5. CPU / GPU Executor

CPU Job 在 1012 通过固定模块入口执行：

```text
python -m geomcp.worker.local_runner JOB_ID
```

GPU Job 在固定 SSH endpoint 的 1015 执行：

```text
python -m geomcp.worker.runner JOB_ID
```

Worker 根据 Job ID 从共享 runtime 获取任务，只执行 Registry 白名单。

## 6. DAS Basic

任何处理前先 inspect：

```bash
geomcp das inspect /cluster/datapool2/xuxy/data/example.h5 --json
```

读取小窗口：

Python API / CLI 可以返回完整受限窗口；MCP 的 `das.read_window` 只返回 metadata、shape、point_count 和小型 preview，避免把大数组注入 Agent 上下文。


```bash
geomcp das read-window FILE \
  --channel-start 100 --channel-stop 120 \
  --sample-start 0 --sample-stop 5000 --json
```

RMS：

```bash
geomcp das rms FILE --channel-start 100 --channel-stop 120 --sample-stop 5000 --json
```

Bandpass：

```bash
geomcp das bandpass FILE 1 20 \
  --channel-start 100 --channel-stop 120 --sample-stop 5000 --json
```

Plot：

```bash
geomcp das plot FILE --channel-start 100 --channel-stop 120 --sample-stop 5000 --json
```

Bandpass/plot 默认生成文件到 GeoMCP outputs。用户指定 `--output-path` 时仍必须位于 write roots。

## 7. MCP

```bash
geomcp-mcp
```

暴露：

```text
system.status
filesystem.inspect
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
```

MCP、CLI、Python API 复用同一 Service / Permission / Scientific Core。MCP 的配置目录在服务器启动时固定，工具参数中不暴露 `config_dir`。
