# GeoMCP 文档

GeoMCP 文档按“使用、架构、接口、科学工具、开发、部署”分类维护。新增文档不要继续平铺在 `docs/` 根目录。

## 快速入口

| 目标 | 文档 |
|---|---|
| 安装并使用 GeoMCP | [基础使用指南](getting-started/USAGE.md) |
| 开发一个新的科学工具 | [新增工具开发指南](development/TOOL_DEVELOPMENT.md) |
| 查看当前开发进度 | [开发路线图](development/ROADMAP.md) |
| 理解整体架构与安全边界 | [Project Core](architecture/PROJECT_CORE.md) / [Permission & Sandbox](architecture/PERMISSION_PATH_SANDBOX.md) |
| 使用 Python / CLI / MCP | [Python API](interfaces/PYTHON_API.md) / [CLI](interfaces/CLI.md) / [MCP](interfaces/MCP.md) |
| 部署到无外网服务器 | [离线服务器部署](deployment/OFFLINE_SERVER_DEPLOYMENT.md) |

## 目录结构

```text
docs/
├── README.md
├── getting-started/
│   └── USAGE.md
├── architecture/
│   ├── PROJECT_CORE.md
│   ├── PERMISSION_PATH_SANDBOX.md
│   ├── JOB_MANAGER.md
│   ├── CPU_EXECUTOR.md
│   ├── GPU_EXECUTOR.md
│   └── GPU_WORKER.md
├── interfaces/
│   ├── PYTHON_API.md
│   ├── CLI.md
│   └── MCP.md
├── scientific/
│   ├── DAS_BASIC.md
│   ├── DAS_ADVANCED.md
│   ├── RAG.md
│   ├── RESEARCH_MEMORY.md
│   └── SEISMOLOGY_WRAPPERS.md
├── development/
│   ├── ROADMAP.md
│   ├── TOOL_DEVELOPMENT.md
│   ├── V0_1_HARDENING.md
│   └── INTEGRATION_RELEASE.md
└── deployment/
    └── OFFLINE_SERVER_DEPLOYMENT.md
```

## 当前状态

当前达到 `v0.1`：Step 01–10 已完成，Step 10.1 Hardening 已完成。后续计划见 [ROADMAP](development/ROADMAP.md)。

## 文档维护约定

1. 用户操作说明放入 `getting-started/`。
2. 核心组件、权限、任务和 Executor 设计放入 `architecture/`。
3. Python API、CLI、MCP 等对外接口说明放入 `interfaces/`。
4. DAS、RAG、HypoDD、NLLoc、MatchLocate 等领域能力放入 `scientific/`。
5. 开发流程、版本验收和路线图放入 `development/`。
6. 安装、服务器环境和离线部署放入 `deployment/`。
7. 新增工具时必须同步更新 [TOOL_DEVELOPMENT.md](development/TOOL_DEVELOPMENT.md) 中要求的测试、权限和暴露层。
