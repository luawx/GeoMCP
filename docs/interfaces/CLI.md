# Step 04 — CLI

## 目标

建立人工操作入口，使 GeoMCP 不依赖 Codex 也能正常工作。

统一命令：

```text
geomcp
```

## 第一批命令

```bash
geomcp system status
geomcp config show
geomcp config validate
geomcp filesystem inspect PATH
```

后续逐步加入 DAS、Job、RAG、Memory 和定位程序。

## 开发原则

CLI 必须复用 Service / Python API，不能自己实现一套科研算法。

CLI 与 MCP 使用同一 Permission / Path Sandbox。

推荐支持：

```bash
--json
```

便于脚本调用。

## 错误处理

错误至少包含：

- 明确错误码
- 简短说明
- 非 0 exit code

## 验收

```bash
geomcp --help
geomcp system status
geomcp config validate
```

均可正常执行。
