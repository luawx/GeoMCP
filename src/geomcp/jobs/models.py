from __future__ import annotations
from dataclasses import asdict, dataclass, field
from typing import Any

JOB_STATES = ("queued", "running", "completed", "failed", "cancelled")
TERMINAL_STATES = frozenset({"completed", "failed", "cancelled"})
ALLOWED_TRANSITIONS = {
    "queued": frozenset({"running", "failed", "cancelled"}),
    "running": frozenset({"completed", "failed", "cancelled"}),
    "completed": frozenset(), "failed": frozenset(), "cancelled": frozenset(),
}

@dataclass(slots=True)
class JobRecord:
    job_id: str
    tool: str
    task_type: str
    executor: str
    status: str
    input: dict[str, Any] = field(default_factory=dict)
    parameters: dict[str, Any] = field(default_factory=dict)
    created_at: str | None = None
    started_at: str | None = None
    finished_at: str | None = None
    progress: float = 0.0
    output: Any = None
    error: str | None = None
    executor_meta: dict[str, Any] = field(default_factory=dict)
    def to_dict(self) -> dict[str, Any]: return asdict(self)
