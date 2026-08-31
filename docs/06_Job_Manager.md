# Step 06 — Job Manager

## 目标

为耗时任务建立统一生命周期管理。

## Job 状态

```text
queued
running
completed
failed
cancelled
```

## Job 至少记录

```text
job_id
tool
task_type
executor
status
input
parameters
created_at
started_at
finished_at
progress
output
error
```

## 存储

第一阶段：

```text
SQLite + JSON + 共享目录
```

结构：

```text
runtime/
├── jobs.db
└── jobs/
    └── <job_id>.json
```

## 人工接口

```bash
geomcp job list
geomcp job status JOB_ID
geomcp job result JOB_ID
geomcp job logs JOB_ID
geomcp job cancel JOB_ID
```

cancel 只终止任务，不删除科研数据。

## MCP

提供：

```text
job.list
job.status
job.result
job.cancel
```

## 验收

至少测试 queued → running → completed、failed、cancelled 以及非法状态转换。
