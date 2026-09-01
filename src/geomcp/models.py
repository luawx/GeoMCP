"""Shared structured result models."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(slots=True)
class ApiResult:
    success: bool
    data: Any = None
    error_code: str | None = None
    error_message: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def ok(data: Any = None, *, metadata: dict[str, Any] | None = None) -> ApiResult:
    return ApiResult(success=True, data=data, metadata=metadata or {})


def fail(
    error_code: str,
    error_message: str,
    *,
    metadata: dict[str, Any] | None = None,
) -> ApiResult:
    return ApiResult(
        success=False,
        error_code=error_code,
        error_message=error_message,
        metadata=metadata or {},
    )
