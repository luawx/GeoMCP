# Step 13 — DAS Advanced

## 目标

在基础 DAS 稳定后加入高计算量分析任务。

## 高级工具

```text
das.decimate
das.stack
das.cross_correlation
das.fk
das.beamforming
das.detect
das.ml_detect
das.event_extract
```

## Executor

CPU：

```text
decimate
stack
部分 cross_correlation
event_extract
```

GPU：

```text
fk
beamforming
ml_detect
大规模 cross_correlation
```

由工具定义 preferred executor，不让 Agent 自由指定节点。

## 长任务

FK、Beamforming、ML Detection 等必须进入 Job Manager。

MCP 返回：

```text
job_id
status
```

而不是长时间阻塞。

## 可追溯性

Job 保存：

- 输入路径
- 时间窗口
- channel selection
- 参数
- 软件版本
- executor
- node
- output path

## 验收

至少完成一个 GPU 高级工具的完整链路：

```text
MCP → Job → GPU Executor → 1015 Worker → Result
```
