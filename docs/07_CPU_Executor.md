# Step 07 — Local CPU Executor

## 目标

让 1012 能以统一方式执行 CPU 科研任务。

## 架构

```text
Job Manager
↓
Scheduler
↓
LocalCPUExecutor
↓
1012
```

## 开发任务

定义 Executor 抽象：

```text
submit(job)
status(job)
cancel(job)
result(job)
```

LocalCPUExecutor 只执行注册任务，不允许任意函数路径。

可以配置：

```text
max_workers
timeout
memory_soft_limit
```

第一阶段不引入 Celery、Redis、Kafka。

## 验收

测试一个 CPU Job，确认：

- 状态完整
- 可取消
- 超时可失败
- 输出进入 runtime 或 outputs
- Python / CLI / MCP 最终走同一个 Executor
