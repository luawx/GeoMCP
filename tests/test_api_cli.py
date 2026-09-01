from geomcp.api import jobs
from geomcp.cli.main import main

def test_job_api_and_cli(config_factory, capsys, monkeypatch):
    config_dir, _, _, _ = config_factory()
    assert jobs.list_jobs(config_dir=config_dir).success
    code = main(["--config-dir", str(config_dir), "job", "list", "--json"])
    assert code == 0
    assert '"success": true' in capsys.readouterr().out

    captured = {}

    class FakeRecord:
        def to_dict(self):
            return {"job_id": "a" * 32, "status": "queued", "task_type": "gpu.healthcheck"}

    def fake_submit(self, **kwargs):
        captured.update(kwargs)
        return FakeRecord()

    monkeypatch.setattr("geomcp.services.jobs.JobManager.submit", fake_submit)
    result = jobs.submit_healthcheck(executor="gpu", config_dir=config_dir)
    assert result.success
    assert captured["task_type"] == "gpu.healthcheck"
    assert captured["executor"] == "gpu"

    code = main([
        "--config-dir",
        str(config_dir),
        "job",
        "healthcheck",
        "--executor",
        "cpu",
        "--json",
    ])
    assert code == 0
