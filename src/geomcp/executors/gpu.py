from __future__ import annotations
import subprocess
from pathlib import Path
from geomcp.config import load_config, runtime_dir
from geomcp.exceptions import ExecutorError
from geomcp.jobs import JobStore
from .dispatch import watch_dispatch

class RemoteGPUExecutor:
    def __init__(self, *, config_dir: str | Path | None=None):
        self.config = load_config(config_dir)
        self.store = JobStore(runtime_dir(self.config))
        self.gpu = self.config.get("executors", {}).get("gpu", {}) or {}
        if not self.gpu.get("enabled"):
            raise ExecutorError("GPU executor is disabled")

    def _ssh_prefix(self) -> list[str]:
        host = str(self.gpu["host"])
        port = int(self.gpu["port"])
        user = str(self.gpu["username"])
        if port < 1 or port > 65535:
            raise ExecutorError("Configured GPU SSH port is invalid")
        return [str(self.gpu.get("ssh_executable", "ssh")), "-p", str(port), f"{user}@{host}"]

    def _remote_cmd(self, job_id: str, *, cancel: bool=False) -> list[str]:
        self.store.get(job_id)
        cmd = [
            str(self.gpu["python"]), "-m", "geomcp.worker.runner", job_id,
            "--config-dir", str(self.gpu["config_dir"]),
        ]
        if cancel:
            cmd.append("--cancel")
        return self._ssh_prefix() + cmd

    def submit(self, job_id: str) -> None:
        job = self.store.get(job_id)
        if job.executor != "gpu":
            raise ExecutorError("RemoteGPUExecutor only accepts gpu jobs")
        try:
            proc = subprocess.Popen(
                self._remote_cmd(job_id),
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
            )
        except OSError as exc:
            self.store.transition(job_id, "failed", error=f"Unable to dispatch GPU job: {exc}")
            raise ExecutorError(str(exc)) from exc
        self.store.set_executor_meta(job_id, ssh_launcher_pid=proc.pid, remote_worker="geomcp.worker.runner")
        watch_dispatch(
            self.store,
            job_id,
            proc,
            timeout=float(self.gpu.get("dispatch_timeout", 30)),
            label="GPU SSH launcher",
        )

    def cancel(self, job_id: str) -> None:
        current = self.store.get(job_id)
        if current.status == "queued":
            self.store.transition(job_id, "cancelled")
            return
        if current.status != "running":
            return
        result = subprocess.run(
            self._remote_cmd(job_id, cancel=True),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=30,
            check=False,
        )
        if result.returncode != 0:
            raise ExecutorError(f"Remote GPU cancellation failed with exit code {result.returncode}")
        current = self.store.get(job_id)
        if current.status in {"queued", "running"}:
            try:
                self.store.transition(job_id, "cancelled")
            except Exception:
                pass
