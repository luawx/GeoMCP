# Step 02 — Permission / Path Sandbox

## 目标

在任何科研工具接触服务器数据之前建立统一安全边界。

## 默认范围

允许读取：

```text
/cluster/datapool2/xuxy/**
```

允许写入：

```text
/cluster/datapool2/xuxy/GeoMCP/outputs/**
/cluster/datapool2/xuxy/GeoMCP/runtime/**
/cluster/datapool2/xuxy/GeoMCP/knowledge/**
```

原始科研数据默认只读。

## 开发任务

实现：

```text
src/geomcp/services/paths.py
src/geomcp/services/permissions.py
config/paths.yaml
config/permissions.yaml
```

任何输入路径必须：

```text
输入
↓
normalize
↓
resolve()
↓
检查 allowed root
↓
检查 read/write 权限
↓
执行
```

必须防止：

- ../ 路径逃逸
- 符号链接越界
- 相对路径越界
- 原始数据写入
- allowed root 外访问

禁止能力：

```text
delete
recursive_delete
arbitrary_shell
arbitrary_ssh
```

## 验收

必须覆盖合法路径、/etc、其他用户目录、../、符号链接越界、原始数据写入等测试。

所有安全判断采用 fail closed。
