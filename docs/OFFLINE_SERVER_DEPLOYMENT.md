# 无外网服务器部署与 MCP 配置

适用于服务器不能连接公网、但本地开发机可以通过 SSH 访问服务器的场景。
推荐服务器目录：

```text
/cluster/datapool2/xuxy/GeoMCP
```

部署原则是：**联网机器准备完整 wheelhouse，服务器只进行离线安装。**

## 1. 联网机器准备源码

```bash
git clone https://github.com/luawx/GeoMCP.git
cd GeoMCP
git checkout feat/foundation-v0.1   # PR 合并后使用 main
```

建议使用与服务器相同的 Python 大版本、CPU 架构和 Linux 平台准备 wheels。
如果依赖中包含平台相关 wheel，Windows 上下载的 wheel 不能直接拿到 Linux 服务器安装。

## 2. 准备离线 wheelhouse

推荐在一台可联网、且环境尽可能接近服务器的 Linux 机器执行：

```bash
python -m venv .packenv
source .packenv/bin/activate
python -m pip install --upgrade pip wheel setuptools
python -m pip wheel --wheel-dir wheelhouse ".[mcp]"
```

完成后 `wheelhouse/` 应同时包含 GeoMCP、PyYAML、MCP SDK 及其依赖。

如服务器只使用 Python API / CLI，不需要 MCP：

```bash
python -m pip wheel --wheel-dir wheelhouse .
```

## 3. 传到服务器

示例：

```bash
scp -r GeoMCP asgroup:/cluster/datapool2/xuxy/
```

如果源码和 wheelhouse 分开：

```bash
scp -r wheelhouse asgroup:/cluster/datapool2/xuxy/GeoMCP/
```

该过程只需要本地机器能够连接服务器，不要求服务器访问公网。

## 4. 服务器离线安装

SSH 登录：

```bash
ssh asgroup
cd /cluster/datapool2/xuxy/GeoMCP
python3 -m venv .venv
source .venv/bin/activate
```

安装完整 MCP 版本：

```bash
python -m pip install \
  --no-index \
  --find-links ./wheelhouse \
  "geomcp[mcp]"
```

验证整个过程中不会访问 PyPI：`--no-index` 会禁止使用 package index。

如果希望服务器继续直接修改源码，可先从 wheelhouse 安装依赖，再做 editable install：

```bash
python -m pip install --no-index --find-links ./wheelhouse PyYAML "mcp>=2,<3"
python -m pip install --no-index --no-build-isolation -e .
```

## 5. 服务器配置

设置：

```bash
export GEOMCP_HOME=/cluster/datapool2/xuxy/GeoMCP
export GEOMCP_CONFIG_DIR=/cluster/datapool2/xuxy/GeoMCP/config
```

建议写入 GeoMCP 专用启动脚本或服务配置，不必修改全局 shell 环境。

检查 `config/paths.yaml`：

```yaml
read_roots:
  - /cluster/datapool2/xuxy
write_roots:
  - /cluster/datapool2/xuxy/GeoMCP/runtime
  - /cluster/datapool2/xuxy/GeoMCP/outputs
  - /cluster/datapool2/xuxy/GeoMCP/knowledge
```

不要为了方便把 `/`、`/cluster` 或用户 home 全部加入 write_roots。

验证：

```bash
.venv/bin/geomcp config validate
.venv/bin/geomcp system status --json
.venv/bin/geomcp filesystem inspect /cluster/datapool2/xuxy --json
```

安全验证：

```bash
.venv/bin/geomcp filesystem inspect /etc/passwd --json
```

最后一条必须失败。

## 6. 在服务器直接运行 MCP

```bash
cd /cluster/datapool2/xuxy/GeoMCP
GEOMCP_CONFIG_DIR=/cluster/datapool2/xuxy/GeoMCP/config \
  .venv/bin/geomcp-mcp
```

这是 stdio MCP Server；不要在终端手工交互时向它的 stdout 写额外日志。

## 7. 本地 Codex 通过 SSH 使用服务器 MCP

服务器没有公网不影响这种方式：MCP 进程运行在服务器上，而 Codex 在本地通过 SSH 启动远端 stdio 进程。

仓库提供 `scripts/run_mcp.sh`，先在服务器检查：

```bash
chmod +x /cluster/datapool2/xuxy/GeoMCP/scripts/run_mcp.sh
/cluster/datapool2/xuxy/GeoMCP/scripts/run_mcp.sh
```

在本地 Codex CLI 注册：

```powershell
codex mcp add geomcp -- ssh asgroup /cluster/datapool2/xuxy/GeoMCP/scripts/run_mcp.sh
```

检查注册结果：

```powershell
codex mcp get geomcp
codex mcp list
```

如果需要删除后重新注册：

```powershell
codex mcp remove geomcp
```

这条配置的关键点是：Codex 只知道如何通过 SSH 启动 `run_mcp.sh`，并没有得到任意服务器 shell 工具；GeoMCP MCP 本身仍只暴露 Registry 中注册的工具。

核心关系：

```text
Local Codex
    │
    │ stdio over SSH
    ▼
1012: GeoMCP MCP Server
    │
    ├── Permission / Path Sandbox
    ├── Python API / Services
    └── future Job Manager
             │
             └── future dispatch ──> 1015 GPU Worker
```

当前 Step 01–05 **不会主动 SSH 1015**。1015 调度将在后续 Job Manager / GPU Executor / GPU Worker 阶段实现。

## 8. 推荐上线检查

```bash
.venv/bin/python -c "import geomcp; print(geomcp.__version__)"
.venv/bin/geomcp config validate
.venv/bin/geomcp system status --json
pytest -q
```

随后从本地 MCP 客户端确认可以发现：

```text
system.status
filesystem.inspect
```

并确认 `/etc/passwd`、其他用户目录、`../` 逃逸路径和符号链接逃逸均被拒绝。
