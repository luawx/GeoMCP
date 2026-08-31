# Step 09 — GPU Worker

## 目标

在 1015 建立唯一受控的 GPU 任务执行入口。

## Worker Registry

只允许执行白名单任务，例如：

```text
rag.embedding
rag.rerank
das.fk
das.beamforming
das.ml_detect
```

未知任务立即拒绝。

## 启动方式

第一版：

```bash
python -m geomcp.worker.runner JOB_ID
```

Worker 从共享 runtime 中读取任务，并再次验证：

- task_type
- 输入路径
- 输出路径
- 参数 schema

CUDA、Conda、模型位置由 1015 本地配置管理。

## 验收

注册一个 `gpu.healthcheck` 测试任务，并验证：

- 1012 可触发
- 1015 执行
- 未注册任务拒绝
- shell 文本不会被执行
- Job 状态正确回写
