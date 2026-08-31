# Step 12 — Research Memory

## 目标

建立与 Reference Knowledge 独立的内部研究经验系统。

## 两类知识必须区分

Reference Knowledge：

```text
论文
官方文档
技术报告
书籍
网页
```

Research Memory：

```text
实验结论
参数经验
失败方案
处理经验
历史决策
项目总结
```

## 数据模型

建议包括：

```text
memory_id
project
type
title
content
tags
source_experiment
confidence
created_at
updated_at
```

## 项目隔离

默认不得跨研究项目混合检索。

## 接口

CLI：

```bash
geomcp memory add --project xinjing --type experience "..."
geomcp memory search "MAXSEP"
```

MCP：

```text
memory.search
memory.add
memory.get
memory.list
```

第一版不向 Agent 提供删除。

## 验收

同一关键词分别检索 Reference Knowledge 和 Research Memory 时，来源类型必须清晰可辨，且项目隔离生效。
