# Step 09 — GPU Worker

状态：已实现。

1015 唯一入口：

```bash
python -m geomcp.worker.runner JOB_ID
```

Worker Registry 是白名单。当前 GPU 验收任务：`gpu.healthcheck`。

Worker 会再次检查：

- Job ID 格式和 Job 是否存在
- executor 是否为 `gpu`
- task type 是否注册
- task 是否属于 GPU executor
- input / parameters 是否满足该任务 validator
- timeout / worker process 状态

未知任务或多余参数直接失败。Job JSON 中的字符串不会被解释为 shell 命令。

取消使用同一个固定 runner 的 `--cancel` 模式，不暴露任意远程命令。
