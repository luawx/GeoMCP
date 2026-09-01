# Step 10.1 — v0.1 Hardening / 封板

状态：完成后作为 Step 01–10 的 v0.1 Release Gate。

## 封板项

- CI 安装 `[test,mcp,das]`，DAS plot 等测试必须真实具备 DAS 依赖。
- Job 状态转换使用 SQLite `BEGIN IMMEDIATE` + 条件更新，跨进程竞争时只有一个终态转换成功。
- CPU/GPU launcher 增加 dispatch watchdog；worker 未 claim、launcher 提前退出或 dispatch 超时会把 queued Job 标记为 failed。
- MCP Tool 不再接收 `config_dir`；权限、路径、GPU endpoint 由服务器启动配置固定。
- 新增 `job.submit_healthcheck`，只允许 `cpu` / `gpu` 两种内置 healthcheck，不接受任意 task、host、command、Shell 或 SSH。
- DASPy 窗口读取使用 `chmin/chmax` 与 `spmin/spmax` 在底层读取阶段裁剪，不再先读整段时间数据后切片。
- MCP `das.read_window` 仅返回 metadata + compact preview；完整数组仍保留在 Python API / CLI 的受限窗口接口。

## v0.1 Release Gate

合并到 `main` 前必须满足：

1. GitHub Actions `pytest` 全绿。
2. MCP Registry 不含 `config_dir`、任意 Shell、任意 SSH 或通用 Job submit。
3. Job race / timeout / dispatch failure / cancel 测试通过。
4. DAS Nyquist / max_points / bounded read / plot 测试通过。
5. 服务器部署后再执行一次 1012 CPU healthcheck 和 1012 -> 1015 GPU healthcheck，作为环境级验收。
