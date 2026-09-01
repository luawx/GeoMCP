# Step 01 — Project Core

## 目标

建立 GeoMCP 的最小可运行项目骨架，为后续所有模块提供统一的包结构、配置、异常和基础模型。

## 主要任务

建立：

```text
src/geomcp/
├── api/
├── cli/
├── mcp/
├── services/
├── scientific/
├── jobs/
├── executors/
├── worker/
├── rag/
└── memory/
```

同时建立：

```text
config/
runtime/
outputs/
knowledge/
tests/
docs/
```

实现统一配置加载器，集中读取：

- geomcp.yaml
- paths.yaml
- permissions.yaml
- executors.yaml
- rag.yaml\n- workspaces.yaml

定义统一异常，例如：

```text
GeoMCPError
ConfigurationError
PermissionDenied
InvalidPathError
JobError
ExecutorError
WorkerError
ScientificToolError
```

建立版本信息和最小测试框架。

## 本步不做

暂不实现 MCP、Job、GPU、DAS、RAG 和地震学算法。

## 验收

```bash
python -c "import geomcp; print(geomcp.__version__)"
pytest -q
```

必须能够正常导入包、加载配置，并完成基础测试。
