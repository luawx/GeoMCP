# Step 04 — CLI

## 目标

建立人工操作入口，使 GeoMCP 不依赖 Codex 也能正常工作。

统一命令：

```text
geomcp
```

## 第一批命令

```bash
geomcp system status
geomcp config show
geomcp config validate
geomcp filesystem inspect PATH
```

后续逐步加入 DAS、Job、RAG、Memory 和定位程序。

## 开发原则

CLI 必须复用 Service / Python API，不能自己实现一套科研算法。

CLI 与 MCP 使用同一 Permission / Path Sandbox。

推荐支持：

```bash
--json
```

便于脚本调用。

## 错误处理

错误至少包含：

- 明确错误码
- 简短说明
- 非 0 exit code

## 验收

```bash
geomcp --help
geomcp system status
geomcp config validate
```

均可正常执行。


## Workspace / Data Region

查看管理员配置的科研区域：

```bash
geomcp workspace list --json
```

DAS 命令支持：

```bash
geomcp das inspect raw/event001.h5 --workspace guangzhou_das --json

geomcp das plot raw/event001.h5 \
  --workspace guangzhou_das \
  --output-path event001/preview.png --json
```

传 `--workspace` 后，`path` 和 `--output-path` 都按 Workspace root 解析，并禁止绝对路径与路径逃逸。


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

```bash
geomcp picking backends --json
geomcp picking presets --backend-id stalta --json
geomcp picking inspect inputs/waveforms.json --geometry-ref inputs/geometry.json --workspace research --json
geomcp picking prepare --request '{"workspace":"research","waveform_manifest_ref":"inputs/waveforms.json","geometry_ref":"inputs/geometry.json","preset_id":"station-stalta-demo","preset_version":"1"}' --json
geomcp picking validate PREPARED_REF --workspace research --json
geomcp picking run PREPARED_REF --workspace research --json
geomcp picking result JOB_ID --preview-limit 20 --json
geomcp picking import --request '{"workspace":"research","input_ref":"inputs/picks.csv","geometry_ref":"inputs/geometry.json","format":"external_csv","mapping":{"missing_phase":"unknown"}}' --json
```

Use returned prepared_ref/job_id values. --request takes an inline JSON object.
Human --config-dir is a startup option before the group, never a request field.
