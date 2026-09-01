from pathlib import Path
import pytest

@pytest.fixture
def config_factory(tmp_path):
    def make(*, gpu_enabled=False):
        root = tmp_path / "research"
        runtime = root / "GeoMCP" / "runtime"
        outputs = root / "GeoMCP" / "outputs"
        knowledge = root / "GeoMCP" / "knowledge"
        for p in (root, runtime, outputs, knowledge):
            p.mkdir(parents=True, exist_ok=True)

        config = tmp_path / ("config_gpu" if gpu_enabled else "config")
        config.mkdir(exist_ok=True)
        allowed = (
            "[system.status, filesystem.inspect, filesystem.read, filesystem.write, "
            "job.list, job.status, job.result, job.logs, job.cancel, job.submit_healthcheck, "
            "das.inspect, das.read, das.process, das.plot]"
        )
        (config / "geomcp.yaml").write_text(
            f"name: GeoMCP\ncontrol_node: '1012'\ngpu_node: '1015'\n"
            f"runtime_dir: {runtime}\noutputs_dir: {outputs}\ndas:\n  max_points: 1000\n",
            encoding="utf-8",
        )
        (config / "paths.yaml").write_text(
            f"read_roots:\n  - {root}\nwrite_roots:\n  - {runtime}\n  - {outputs}\n  - {knowledge}\n",
            encoding="utf-8",
        )
        (config / "permissions.yaml").write_text(
            f"default_policy: deny\nallowed_capabilities: {allowed}\n"
            "denied_capabilities: [delete, recursive_delete, arbitrary_shell, arbitrary_ssh]\n",
            encoding="utf-8",
        )
        (config / "executors.yaml").write_text(
            "default_executor: cpu\n"
            "cpu:\n  node: '1012'\n  dispatch_timeout: 1\n"
            "gpu:\n  node: '1015'\n  enabled: %s\n  host: gpu.internal\n  port: 1015\n"
            "  username: researcher\n  python: /opt/geomcp/bin/python\n"
            "  config_dir: /cluster/datapool2/xuxy/GeoMCP/config\n"
            "  ssh_executable: ssh\n  dispatch_timeout: 1\n"
            % ("true" if gpu_enabled else "false"),
            encoding="utf-8",
        )
        (config / "rag.yaml").write_text("enabled: false\n", encoding="utf-8")
        return config, root, runtime, outputs
    return make
