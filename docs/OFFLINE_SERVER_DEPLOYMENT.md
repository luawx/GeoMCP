# 无外网服务器部署 GeoMCP

目标：服务器本身不能访问 GitHub/PyPI，也可以在 `/cluster/datapool2/xuxy/GeoMCP` 运行 GeoMCP；本地 Codex 通过已有 SSH 连接启动远程 stdio MCP Server。

当前 Step 01–05 不需要服务器主动访问外网。

## 1. 联网机器准备离线包

最好使用与服务器相同的 Linux 架构和 Python 小版本准备依赖，例如服务器是 Linux x86_64 + Python 3.11，就在相同环境制作 wheelhouse。

```bash
git clone https://github.com/luawx/GeoMCP.git
cd GeoMCP

python3 -m venv .build-venv
source .build-venv/bin/activate
python -m pip install -U pip build

# 构建 GeoMCP 自身 wheel
python -m build --wheel

# 下载所有运行时依赖；--only-binary=:all: 可提前发现缺少可离线安装 wheel 的依赖
mkdir -p wheelhouse
python -m pip download \
  --only-binary=:all: \
  --dest wheelhouse \
  "PyYAML>=6.0,<7" \
  "mcp>=2,<3"

cp dist/geomcp-*.whl wheelhouse/
```

把下面内容一起打包：

```bash
cd ..
tar -czf geomcp-offline.tar.gz \
  GeoMCP/wheelhouse \
  GeoMCP/config \
  GeoMCP/skills \
  GeoMCP/docs
```

然后通过允许的文件传输方式把 `geomcp-offline.tar.gz` 传到服务器。服务器不需要连接 GitHub 或 PyPI。

## 2. 在无外网服务器安装

进入服务器后：

```bash
cd /cluster/datapool2/xuxy
mkdir -p GeoMCP
cd GeoMCP

tar -xzf /path/to/geomcp-offline.tar.gz --strip-components=1

python3 -m venv .venv
source .venv/bin/activate

python -m pip install \
  --no-index \
  --find-links ./wheelhouse \
  ./wheelhouse/geomcp-*.whl
```

`--no-index` 会强制 pip 不访问 PyPI。

## 3. 建立允许写入的目录

```bash
mkdir -p \
  /cluster/datapool2/xuxy/GeoMCP/outputs \
  /cluster/datapool2/xuxy/GeoMCP/runtime \
  /cluster/datapool2/xuxy/GeoMCP/knowledge
```

不要把原始科研数据目录加入 `write_roots`。

## 4. 配置 GeoMCP

当前默认 `config/paths.yaml`：

```yaml
read_roots:
  - /cluster/datapool2/xuxy
write_roots:
  - /cluster/datapool2/xuxy/GeoMCP/outputs
  - /cluster/datapool2/xuxy/GeoMCP/runtime
  - /cluster/datapool2/xuxy/GeoMCP/knowledge
```

权限配置必须保持：

```yaml
capabilities:
  inspect: true
  write: true
  delete: false
  recursive_delete: false
  arbitrary_shell: false
  arbitrary_ssh: false
```

设置配置目录：

```bash
export GEOMCP_CONFIG_DIR=/cluster/datapool2/xuxy/GeoMCP/config
```

如需长期生效，可以把这一行加入该账号自己的 shell 启动配置；也可以只在启动 GeoMCP 时传入环境变量。

## 5. 服务器端验证

```bash
source /cluster/datapool2/xuxy/GeoMCP/.venv/bin/activate
export GEOMCP_CONFIG_DIR=/cluster/datapool2/xuxy/GeoMCP/config

geomcp config validate
geomcp system status
geomcp filesystem inspect /cluster/datapool2/xuxy
```

安全边界也应验证一次：

```bash
geomcp filesystem inspect /etc/passwd
```

该命令必须失败并返回 `PERMISSION_DENIED`。

验证 MCP SDK 和服务器对象可加载：

```bash
python -c "from geomcp.mcp.server import create_server; create_server(); print('MCP OK')"
```

## 6. 本地 Codex 连接无外网服务器

推荐让 MCP Server 运行在服务器 1012 控制节点上，本地 Codex 通过 SSH 的 stdin/stdout 与它通信。服务器仍然不需要访问外网。

如果本地已有：

```bash
ssh asgroup
```

可以在本地注册：

```bash
codex mcp add geomcp -- \
  ssh asgroup \
  env GEOMCP_CONFIG_DIR=/cluster/datapool2/xuxy/GeoMCP/config \
  /cluster/datapool2/xuxy/GeoMCP/.venv/bin/geomcp-mcp
```

然后检查：

```bash
codex mcp get geomcp
codex mcp list
```

调用链为：

```text
本地 Codex
   ↓ stdio
本地 ssh asgroup
   ↓ SSH
1012: geomcp-mcp
   ↓
GeoMCP Service / Path Sandbox
```

这里的 SSH 只用于“启动受控 MCP Server 并传输 stdio”，GeoMCP 自身没有向 Agent 暴露任意 SSH 工具。

## 7. 1015 GPU 节点说明

当前只完成 Step 01–05，因此还没有 GPU Executor / Worker，不应该让 Agent 绕过 GeoMCP 直接操作 1015。

后续 Step 08–09 完成后，设计调用链才会变为：

```text
Codex
  ↓
MCP @ 1012
  ↓
Job Manager / GPU Executor
  ↓
受控 Worker Registry @ 1015
```

## 8. 更新离线服务器

服务器不能 `git pull` 时，在联网机器重新构建新的 GeoMCP wheel 和 wheelhouse，再传入服务器。升级仍使用：

```bash
python -m pip install \
  --no-index \
  --find-links ./wheelhouse \
  --upgrade \
  ./wheelhouse/geomcp-*.whl
```

配置目录建议与 Python 包分离保留，升级前先备份 `config/*.yaml`，再检查新版本配置项。
