# Step 10 — DAS Basic

状态：已实现 v0.1 最低工具集，底层采用 DASPy。

GeoMCP 可选依赖：

```bash
python -m pip install -e ".[das]"
```

PyPI 包名是 `daspy-toolbox`，Python import 为 `daspy`。

当前工具：

```text
das.inspect
das.read_window
das.bandpass
das.rms
das.plot
```

完整链路：

```text
DASPy-backed Scientific Core
  -> DASService + PathPolicy
  -> Python API
  -> CLI
  -> MCP
  -> Skill
```

安全约束：

- 所有输入路径先经过 read root 校验
- 输出只能进入 write roots
- 大窗口按 `geomcp.das.max_points` 拒绝，默认 200000 points
- bandpass 必须满足 `0 < freqmin < freqmax < Nyquist`
- 原始 DAS 文件只读
- 处理前内部读取 metadata；Agent 侧也要求先调用 `das.inspect`

示例：

```bash
geomcp das inspect /cluster/datapool2/xuxy/data/example.h5 --json
geomcp das rms /cluster/datapool2/xuxy/data/example.h5 --channel-start 100 --channel-stop 120 --sample-start 0 --sample-stop 5000 --json
geomcp das bandpass /cluster/datapool2/xuxy/data/example.h5 1 20 --channel-start 100 --channel-stop 120 --sample-stop 5000 --json
geomcp das plot /cluster/datapool2/xuxy/data/example.h5 --channel-start 100 --channel-stop 120 --sample-stop 5000 --json
```

Step 13 再加入连续数据、FK、beamforming、去噪等高级 DAS 能力。
