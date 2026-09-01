# 无外网服务器部署与 MCP 配置（v0.1）

适用于服务器不能访问公网，但本地开发机可以通过 SSH 访问服务器的场景。推荐目录：

```text
/cluster/datapool2/xuxy/GeoMCP
```

原则：联网 Linux 环境准备完整 wheelhouse，服务器只做 `--no-index` 离线安装。

## 1. 联网机器准备 wheelhouse

使用尽量与服务器相同的 Linux / Python 版本：

```bash
git clone https://github.com/luawx/GeoMCP.git
cd GeoMCP
git checkout main
python -m venv .packenv
source .packenv/bin/activate
python -m pip install --upgrade pip wheel setuptools
```

仅 MCP：

```bash
python -m pip wheel --wheel-dir wheelhouse ".[mcp]"
```

MCP + DASPy（推荐 v0.1 科研节点）：

```bash
python -m pip wheel --wheel-dir wheelhouse ".[mcp,das]"
```

这会把 `daspy-toolbox` 及 NumPy/SciPy/Matplotlib/HDF5/SEG-Y/TDMS 等依赖一起准备到 wheelhouse。不要直接拿 Windows 平台相关 wheel 到 Linux 服务器使用。

## 2. 传到服务器并离线安装

```bash
scp -r GeoMCP asgroup:/cluster/datapool2/xuxy/
ssh asgroup
cd /cluster/datapool2/xuxy/GeoMCP
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --no-index --find-links ./wheelhouse ".[mcp,das]"
```

`--no-index` 保证安装过程不访问 PyPI。

## 3. 基础配置

```bash
export GEOMCP_HOME=/cluster/datapool2/xuxy/GeoMCP
export GEOMCP_CONFIG_DIR=/cluster/datapool2/xuxy/GeoMCP/config
```

默认：

```yaml
read_roots:
  - /cluster/datapool2/xuxy
write_roots:
  - /cluster/datapool2/xuxy/GeoMCP/runtime
  - /cluster/datapool2/xuxy/GeoMCP/outputs
  - /cluster/datapool2/xuxy/GeoMCP/knowledge
```

不要把 `/`、整个 `/cluster` 或其他用户目录加入 write roots。

### Workspace / Data Region

`workspaces.yaml` 是可选配置；旧部署没有该文件仍可运行，但不会有命名 Workspace。推荐新部署配置：

```yaml
workspaces:
  geomcp:
    description: Default GeoMCP research workspace
    read_root: /cluster/datapool2/xuxy
    write_root: /cluster/datapool2/xuxy/GeoMCP/outputs
```

如果要让 Agent 写入项目自己的目录，例如：

```text
/cluster/datapool2/xuxy/DAS/2021Guangzhou/processed
```

必须先把它加入 `paths.yaml -> write_roots`，再增加：

```yaml
workspaces:
  guangzhou_das:
    read_root: /cluster/datapool2/xuxy/DAS/2021Guangzhou
    write_root: /cluster/datapool2/xuxy/DAS/2021Guangzhou/processed
```

Workspace 不能扩大全局路径权限。

验证：

```bash
.venv/bin/geomcp config validate
.venv/bin/geomcp system status --json
.venv/bin/geomcp filesystem inspect /cluster/datapool2/xuxy --json
.venv/bin/geomcp filesystem inspect /etc/passwd --json
```

最后一条必须失败。

## 4. 1012 -> 1015 GPU 配置

GPU Executor 默认 `enabled: false`。确认服务器 SSH 结构后，只由管理员修改 `config/executors.yaml`：

```yaml
gpu:
  enabled: true
  host: <fixed-host>
  port: <fixed-port>
  username: <fixed-user>
  python: <1015-geomcp-python>
  config_dir: /cluster/datapool2/xuxy/GeoMCP/config
```

Agent 没有这些字段的工具参数。GeoMCP 只会构造固定入口：

```text
python -m geomcp.worker.runner JOB_ID
```

1012 和 1015 必须都能访问共享 GeoMCP runtime 和科研数据目录。

## 5. MCP

服务器：

```bash
/cluster/datapool2/xuxy/GeoMCP/scripts/run_mcp.sh
```

本地 Codex：

```powershell
codex mcp add geomcp -- ssh asgroup /cluster/datapool2/xuxy/GeoMCP/scripts/run_mcp.sh
codex mcp get geomcp
```

Codex 只是通过 SSH 启动固定 MCP stdio 入口；GeoMCP 本身不暴露任意 shell/SSH 工具。`config_dir` 只由管理员在 MCP 启动时设置，不作为 MCP Tool 参数暴露给 Agent。

## 6. v0.1 验收

```bash
.venv/bin/python -c "import geomcp; print(geomcp.__version__)"
.venv/bin/python -c "import daspy; print(daspy.__file__)"
.venv/bin/geomcp config validate
.venv/bin/geomcp system status --json
pytest -q
```

然后从 MCP 客户端确认至少发现 system/filesystem/workspace/job/das 工具，并确认越权路径、`../`、符号链接逃逸、任意 shell/SSH 均不可用。
