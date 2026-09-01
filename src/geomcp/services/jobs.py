from __future__ import annotations
from pathlib import Path
from geomcp.config import load_config, runtime_dir
from geomcp.exceptions import JobError
from geomcp.jobs import JobStore
from geomcp.jobs.manager import JobManager
from geomcp.services.permissions import PathPolicy

class JobService:
    def __init__(self, *, config_dir: str | Path | None=None):
        self.config_dir = config_dir
        self.config = load_config(config_dir)
        self.policy = PathPolicy.from_config(self.config)
        self.store = JobStore(runtime_dir(self.config))

    def list(self, *, limit: int=100, status: str | None=None):
        self.policy.assert_capability_allowed("job.list")
        return [j.to_dict() for j in self.store.list(limit=limit, status=status)]

    def status(self, job_id: str):
        self.policy.assert_capability_allowed("job.status")
        return self.store.get(job_id).to_dict()

    def result(self, job_id: str):
        self.policy.assert_capability_allowed("job.result")
        job = self.store.get(job_id)
        return {"job_id": job.job_id, "status": job.status, "output": job.output, "error": job.error}

    def logs(self, job_id: str):
        self.policy.assert_capability_allowed("job.logs")
        return {"job_id": job_id, "logs": self.store.logs(job_id)}

    def cancel(self, job_id: str):
        self.policy.assert_capability_allowed("job.cancel")
        return JobManager(config_dir=self.config_dir).cancel(job_id).to_dict()

    def submit_healthcheck(self, *, executor: str="cpu"):
        self.policy.assert_capability_allowed("job.submit_healthcheck")
        if executor not in {"cpu", "gpu"}:
            raise JobError("Healthcheck executor must be 'cpu' or 'gpu'")
        task_type = f"{executor}.healthcheck"
        return JobManager(config_dir=self.config_dir).submit(
            task_type=task_type,
            executor=executor,
            tool="job.submit_healthcheck",
        ).to_dict()
