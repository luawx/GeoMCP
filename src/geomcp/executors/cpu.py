from __future__ import annotations
import subprocess, sys
from pathlib import Path
from geomcp.config import load_config, runtime_dir
from geomcp.jobs import JobStore
from geomcp.exceptions import ExecutorError

class LocalCPUExecutor:
    def __init__(self, *, config_dir: str | Path | None=None):
        self.config_dir = str(Path(config_dir).resolve()) if config_dir is not None else None
        self.config = load_config(config_dir); self.store = JobStore(runtime_dir(self.config))
    def submit(self, job_id: str) -> None:
        job = self.store.get(job_id)
        if job.executor != "cpu": raise ExecutorError("LocalCPUExecutor only accepts cpu jobs")
        cmd=[sys.executable, "-m", "geomcp.worker.local_runner", job_id]
        if self.config_dir: cmd += ["--config-dir", self.config_dir]
        try:
            proc=subprocess.Popen(cmd, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
        except OSError as exc:
            self.store.transition(job_id, "failed", error=f"Unable to start CPU worker: {exc}"); raise ExecutorError(str(exc)) from exc
        self.store.set_executor_meta(job_id, launcher_pid=proc.pid, command="geomcp.worker.local_runner")
    def cancel(self, job_id: str) -> None:
        from geomcp.worker.runtime import cancel_local_job
        cancel_local_job(job_id, config_dir=self.config_dir)
