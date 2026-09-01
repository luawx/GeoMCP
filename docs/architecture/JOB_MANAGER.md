# Step 06 — Job Manager

状态：已实现。

Job 生命周期：`queued -> running -> completed|failed|cancelled`。非法状态转换会被拒绝。

持久化：

```text
runtime/jobs.db
runtime/jobs/<job_id>.json
runtime/jobs/<job_id>.log
```

每个 Job 记录 `job_id/tool/task_type/executor/status/input/parameters/created_at/started_at/finished_at/progress/output/error`，并附带受控 executor metadata。

人工接口：

```bash
geomcp job list
geomcp job status JOB_ID
geomcp job result JOB_ID
geomcp job logs JOB_ID
geomcp job cancel JOB_ID
```

MCP：`job.list`、`job.status`、`job.result`、`job.cancel`。

`cancel` 只改变/终止任务，不删除输入数据、输出数据或 Job 记录。
