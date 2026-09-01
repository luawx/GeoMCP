# Step 08 — Remote GPU Executor

状态：代码已实现；默认禁用，部署时需要管理员配置固定 SSH endpoint。

```text
1012 GeoMCP
  -> RemoteGPUExecutor
  -> fixed SSH endpoint
  -> python -m geomcp.worker.runner JOB_ID
  -> 1015 GPU Worker
```

Agent/MCP 参数中不存在 `host`、`port`、`username`、远程 command 或 `CUDA_VISIBLE_DEVICES`。这些只从 `config/executors.yaml` 读取。

`gpu.enabled: true` 时必须配置：`host`、`port`、`username`、`python`、`config_dir`。远程命令固定为 GeoMCP worker runner，只传系统生成的 Job ID。

1012/1015 通过共享 `/cluster/datapool2/xuxy` 读写 Job 和结果，不复制大型 DAS 数据。
