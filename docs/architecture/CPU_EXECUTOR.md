# Step 07 — Local CPU Executor

状态：已实现。

```text
Job Manager
  -> LocalCPUExecutor
  -> python -m geomcp.worker.local_runner JOB_ID
  -> registered task
```

LocalCPUExecutor 不接受任意函数路径和任意 shell。Job ID 由 GeoMCP 生成，runner 再从 Job Store 读取 task type 和参数。

支持：

- `max_workers`：runner 通过 Job Store 原子 claim 控制并发
- `timeout`：与任务自身超时取更严格值
- `memory_soft_limit_mb`：Linux 下对子任务设置地址空间软限制
- 运行中 cancel：终止受控 worker/task 进程

当前注册 CPU 诊断任务：`cpu.healthcheck`；`cpu.delay` 仅用于超时/取消测试，不通过 MCP 暴露通用提交接口。
