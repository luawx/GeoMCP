# Step 10 — DAS Basic

## 目标

用第一批 DAS 工具验证 GeoMCP 从 Scientific Core 到 MCP 的完整链路。

## 第一批工具

```text
das.inspect
das.metadata
das.list_datasets
das.read_window
das.read_channels
das.demean
das.detrend
das.bandpass
das.rms
das.plot
```

v0.1 最低完成：

```text
das.inspect
das.read_window
das.bandpass
das.rms
das.plot
```

## 工具开发标准

每个工具依次实现：

```text
Scientific Core
↓
Service
↓
Python API
↓
CLI
↓
MCP
↓
Skill
↓
Tests
```

## DAS Skill 规则

任何处理前必须先 inspect，确认：

- sampling rate
- channels
- samples
- start time
- 数据结构

禁止：

- 根据文件名猜参数
- 无必要读取完整大型 DAS
- 滤波超过 Nyquist

## Executor

基础 DAS 默认运行在 1012 CPU。

## 验收

同一文件通过 Python API、CLI、MCP 的 inspect 结果必须来自同一核心实现。
