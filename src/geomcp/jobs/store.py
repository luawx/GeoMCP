from __future__ import annotations
import json, sqlite3, threading, uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from geomcp.exceptions import JobError
from .models import ALLOWED_TRANSITIONS, JobRecord

_MIRROR_LOCK = threading.RLock()

def _now() -> str:
    return datetime.now(timezone.utc).isoformat()

def _dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, default=str)

def _loads(value: str | None, default: Any) -> Any:
    if value in (None, ""):
        return default
    return json.loads(value)

class JobStore:
    def __init__(self, runtime_dir: str | Path):
        self.runtime_dir = Path(runtime_dir).expanduser().resolve(strict=False)
        self.jobs_dir = self.runtime_dir / "jobs"
        self.db_path = self.runtime_dir / "jobs.db"
        self.runtime_dir.mkdir(parents=True, exist_ok=True)
        self.jobs_dir.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self):
        conn = sqlite3.connect(self.db_path, timeout=30)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self._connect() as conn:
            conn.execute("""CREATE TABLE IF NOT EXISTS jobs (
                job_id TEXT PRIMARY KEY, tool TEXT NOT NULL, task_type TEXT NOT NULL, executor TEXT NOT NULL,
                status TEXT NOT NULL, input_json TEXT NOT NULL, parameters_json TEXT NOT NULL,
                created_at TEXT, started_at TEXT, finished_at TEXT, progress REAL NOT NULL,
                output_json TEXT, error TEXT, executor_meta_json TEXT NOT NULL
            )""")

    @staticmethod
    def _validate_job_id(job_id: str) -> None:
        if not isinstance(job_id, str) or len(job_id) != 32 or any(c not in "0123456789abcdef" for c in job_id):
            raise JobError("Invalid job id")

    def _row_to_record(self, row) -> JobRecord:
        return JobRecord(
            row["job_id"], row["tool"], row["task_type"], row["executor"], row["status"],
            _loads(row["input_json"], {}), _loads(row["parameters_json"], {}),
            row["created_at"], row["started_at"], row["finished_at"], float(row["progress"]),
            _loads(row["output_json"], None), row["error"], _loads(row["executor_meta_json"], {}),
        )

    def _mirror(self, record: JobRecord):
        tmp = self.jobs_dir / f"{record.job_id}.json.tmp"
        dest = self.jobs_dir / f"{record.job_id}.json"
        with _MIRROR_LOCK:
            tmp.write_text(json.dumps(record.to_dict(), ensure_ascii=False, indent=2, default=str), encoding="utf-8")
            tmp.replace(dest)

    def create(self, *, tool: str, task_type: str, executor: str, input: dict[str, Any] | None=None, parameters: dict[str, Any] | None=None) -> JobRecord:
        job_id = uuid.uuid4().hex
        record = JobRecord(job_id, tool, task_type, executor, "queued", input or {}, parameters or {}, created_at=_now())
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO jobs VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    record.job_id, record.tool, record.task_type, record.executor, record.status,
                    _dumps(record.input), _dumps(record.parameters), record.created_at, None, None,
                    record.progress, None, None, _dumps({}),
                ),
            )
        self._mirror(record)
        self.append_log(job_id, "queued")
        return record

    def get(self, job_id: str) -> JobRecord:
        self._validate_job_id(job_id)
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM jobs WHERE job_id=?", (job_id,)).fetchone()
        if row is None:
            raise JobError(f"Job not found: {job_id}")
        return self._row_to_record(row)

    def list(self, *, limit: int=100, status: str | None=None) -> list[JobRecord]:
        limit = max(1, min(int(limit), 1000))
        with self._connect() as conn:
            if status:
                rows = conn.execute(
                    "SELECT * FROM jobs WHERE status=? ORDER BY created_at DESC LIMIT ?",
                    (status, limit),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM jobs ORDER BY created_at DESC LIMIT ?",
                    (limit,),
                ).fetchall()
        return [self._row_to_record(r) for r in rows]

    def claim_running(self, job_id: str, *, executor: str, max_running: int) -> bool:
        self._validate_job_id(job_id)
        max_running = max(1, int(max_running))
        with self._connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute("SELECT * FROM jobs WHERE job_id=?", (job_id,)).fetchone()
            if row is None:
                raise JobError(f"Job not found: {job_id}")
            current = self._row_to_record(row)
            if current.status == "cancelled":
                conn.commit()
                return False
            if current.status != "queued":
                raise JobError(f"Cannot claim job in state: {current.status}")
            active = conn.execute(
                "SELECT COUNT(*) FROM jobs WHERE executor=? AND status='running'",
                (executor,),
            ).fetchone()[0]
            if int(active) >= max_running:
                conn.commit()
                return False
            started = current.started_at or _now()
            cursor = conn.execute(
                "UPDATE jobs SET status='running', started_at=?, progress=? WHERE job_id=? AND status='queued'",
                (started, max(current.progress, 0.01), job_id),
            )
            if cursor.rowcount != 1:
                conn.rollback()
                return False
            conn.commit()
        updated = self.get(job_id)
        self._mirror(updated)
        self.append_log(job_id, "running")
        return True

    def transition(self, job_id: str, new_status: str, *, output: Any=None, error: str | None=None, progress: float | None=None) -> JobRecord:
        self._validate_job_id(job_id)
        with self._connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute("SELECT * FROM jobs WHERE job_id=?", (job_id,)).fetchone()
            if row is None:
                raise JobError(f"Job not found: {job_id}")
            current = self._row_to_record(row)
            if new_status not in ALLOWED_TRANSITIONS.get(current.status, frozenset()):
                raise JobError(f"Illegal job transition: {current.status} -> {new_status}")

            started = current.started_at
            finished = current.finished_at
            value = current.progress if progress is None else float(progress)
            if new_status == "running":
                started = started or _now()
                value = max(value, 0.01)
            if new_status in {"completed", "failed", "cancelled"}:
                finished = _now()
                if new_status == "completed":
                    value = 1.0

            output_json = _dumps(output) if output is not None else (
                _dumps(current.output) if current.output is not None else None
            )
            next_error = error if error is not None else current.error
            cursor = conn.execute(
                """UPDATE jobs
                   SET status=?, started_at=?, finished_at=?, progress=?, output_json=?, error=?
                   WHERE job_id=? AND status=?""",
                (
                    new_status, started, finished, value, output_json, next_error,
                    job_id, current.status,
                ),
            )
            if cursor.rowcount != 1:
                conn.rollback()
                raise JobError(f"Concurrent job transition rejected for {job_id}")
            conn.commit()

        updated = self.get(job_id)
        self._mirror(updated)
        self.append_log(job_id, new_status + (f": {error}" if error else ""))
        return updated

    def set_executor_meta(self, job_id: str, **values: Any) -> JobRecord:
        self._validate_job_id(job_id)
        with self._connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute("SELECT executor_meta_json FROM jobs WHERE job_id=?", (job_id,)).fetchone()
            if row is None:
                raise JobError(f"Job not found: {job_id}")
            meta = _loads(row["executor_meta_json"], {})
            meta.update(values)
            conn.execute("UPDATE jobs SET executor_meta_json=? WHERE job_id=?", (_dumps(meta), job_id))
            conn.commit()
        updated = self.get(job_id)
        self._mirror(updated)
        return updated

    def update_progress(self, job_id: str, progress: float) -> JobRecord:
        self._validate_job_id(job_id)
        value = min(1.0, max(0.0, float(progress)))
        with self._connect() as conn:
            conn.execute(
                "UPDATE jobs SET progress=? WHERE job_id=? AND status='running'",
                (value, job_id),
            )
        updated = self.get(job_id)
        self._mirror(updated)
        return updated

    def append_log(self, job_id: str, message: str):
        self._validate_job_id(job_id)
        path = self.jobs_dir / f"{job_id}.log"
        with _MIRROR_LOCK, path.open("a", encoding="utf-8") as f:
            f.write(f"{_now()} {message}\n")

    def logs(self, job_id: str) -> str:
        self.get(job_id)
        path = self.jobs_dir / f"{job_id}.log"
        return path.read_text(encoding="utf-8") if path.exists() else ""
