from __future__ import annotations
from pathlib import Path
from typing import Any
from geomcp.config import load_config, runtime_dir
from geomcp.exceptions import ExecutorError, JobError
from geomcp.executors import LocalCPUExecutor, RemoteGPUExecutor
from geomcp.worker.registry import build_task_registry
from .store import JobStore

class JobManager:
    def __init__(self, *, config_dir: str | Path | None=None):
        self.config_dir = config_dir
        self.config = load_config(config_dir)
        self.store = JobStore(runtime_dir(self.config))
    def submit(self, *, task_type: str, executor: str | None=None, tool: str | None=None, input: dict[str, Any] | None=None, parameters: dict[str, Any] | None=None):
        task = build_task_registry().get(task_type)
        chosen = executor or task.executor
        if chosen != task.executor: raise JobError(f"Task {task_type} requires executor {task.executor}")
        record = self.store.create(tool=tool or task_type, task_type=task_type, executor=chosen, input=input, parameters=parameters)
        try:
            if chosen == "cpu": LocalCPUExecutor(config_dir=self.config_dir).submit(record.job_id)
            elif chosen == "gpu": RemoteGPUExecutor(config_dir=self.config_dir).submit(record.job_id)
            else: raise JobError(f"Unknown executor: {chosen}")
        except (ExecutorError, JobError):
            current = self.store.get(record.job_id)
            if current.status == "queued": self.store.transition(record.job_id, "failed", error=f"Unable to dispatch executor {chosen}")
            raise
        return self.store.get(record.job_id)
    def cancel(self, job_id: str):
        job = self.store.get(job_id)
        if job.status not in {"queued", "running"}: return job
        if job.executor == "cpu": LocalCPUExecutor(config_dir=self.config_dir).cancel(job_id)
        elif job.executor == "gpu": RemoteGPUExecutor(config_dir=self.config_dir).cancel(job_id)
        else: raise JobError(f"Unknown executor: {job.executor}")
        return self.store.get(job_id)
