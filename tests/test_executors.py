from geomcp.jobs import JobStore
from geomcp.executors.gpu import RemoteGPUExecutor

def test_gpu_command_uses_only_fixed_endpoint_and_job_id(config_factory, monkeypatch):
    config_dir, _, runtime, _ = config_factory(gpu_enabled=True)
    store = JobStore(runtime)
    job = store.create(
        tool="gpu.healthcheck",
        task_type="gpu.healthcheck",
        executor="gpu",
        input={"command": "unexpected user text"},
        parameters={"host": "untrusted.example"},
    )
    captured = {}

    class P:
        pid = 123

    def fake_popen(cmd, **kwargs):
        captured["cmd"] = cmd
        return P()

    monkeypatch.setattr("subprocess.Popen", fake_popen)
    monkeypatch.setattr("geomcp.executors.gpu.watch_dispatch", lambda *args, **kwargs: None)
    RemoteGPUExecutor(config_dir=config_dir).submit(job.job_id)
    cmd = captured["cmd"]
    assert cmd[:4] == ["ssh", "-p", "1015", "researcher@gpu.internal"]
    joined = " ".join(cmd)
    assert "unexpected user text" not in joined
    assert "untrusted.example" not in joined
    assert cmd[-5:] == [
        "-m",
        "geomcp.worker.runner",
        job.job_id,
        "--config-dir",
        "/cluster/datapool2/xuxy/GeoMCP/config",
    ]
