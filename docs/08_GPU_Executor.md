# Step 08 — Remote GPU Executor

## 目标

由 1012 安全地把 GPU 任务转发到 1015。

## 架构

```text
GeoMCP @ 1012
↓
RemoteGPUExecutor
↓
固定 SSH endpoint
↓
1015
↓
GPU Worker
```

## 安全原则

Agent 不得传入：

```text
host
port
username
command
CUDA_VISIBLE_DEVICES
```

这些全部来自服务器端配置。

远程入口固定为类似：

```bash
python -m geomcp.worker.runner JOB_ID
```

不得拼接任意用户 shell。

## 共享文件系统

1012 和 1015 均直接访问：

```text
/cluster/datapool2/xuxy
```

因此只传 Job ID 和少量参数，不复制大型 DAS 数据。

## 验收

完成：

```text
1012 创建 Job
→ 1015 执行
→ 共享目录写结果
→ 1012 获取结果
```

并确认 Agent 无法改变 SSH endpoint 或远程命令。
