from __future__ import annotations
import threading
import time
from typing import Any
from geomcp.exceptions import JobError
from geomcp.jobs import JobStore

def watch_dispatch(store: JobStore, job_id: str, process: Any, *, timeout: float, label: str) -> None:
    timeout = max(0.5, float(timeout))

    def _watch() -> None:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            try:
                current = store.get(job_id)
            except JobError:
                return
            if current.status != "queued":
                return
            poll = getattr(process, "poll", None)
            code = poll() if callable(poll) else None
            if code is not None:
                try:
                    store.transition(
                        job_id,
                        "failed",
                        error=f"{label} exited before worker claimed job (exit code {code})",
                    )
                except JobError:
                    pass
                return
            time.sleep(0.1)

        try:
            current = store.get(job_id)
        except JobError:
            return
        if current.status != "queued":
            return
        terminate = getattr(process, "terminate", None)
        if callable(terminate):
            try:
                terminate()
            except OSError:
                pass
        try:
            store.transition(job_id, "failed", error=f"{label} dispatch timeout after {timeout:.1f}s")
        except JobError:
            pass

    threading.Thread(target=_watch, name=f"geomcp-dispatch-{job_id[:8]}", daemon=True).start()
