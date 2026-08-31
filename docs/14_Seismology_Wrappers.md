# Step 14 — Catalog / HypoDD / NLLoc / MatchLocate

## 目标

将现有地震学程序以 Wrapper 方式接入 GeoMCP，不修改第三方软件内部源码。

## Catalog

```text
catalog.inspect
catalog.stats
catalog.filter
catalog.compare
catalog.export
```

## HypoDD

```text
hypodd.prepare
hypodd.validate
hypodd.run
hypodd.status
hypodd.result
```

## NLLoc

```text
nlloc.prepare
nlloc.validate
nlloc.run
nlloc.result
```

## MatchLocate

```text
matchlocate.prepare
matchlocate.validate
matchlocate.run
matchlocate.result
```

## 原则

程序调用采用固定 Wrapper，不允许任意 shell。

长任务顺序：

```text
prepare
↓
validate
↓
run
↓
status
↓
result
```

输出统一进入：

```text
outputs/location/
outputs/catalogs/
outputs/experiments/
```

## 验收

每个程序至少包含 prepare、validate failure、run、result parsing 测试。

Agent 不可修改 executable path，也不可拼接任意 shell 参数。
