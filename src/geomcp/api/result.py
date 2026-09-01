"""Stable structured response type for public interfaces."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from geomcp.exceptions import GeoMCPError


@dataclass
class APIResult:
    success: bool
    data: Any = None
    error_code: str | None = None
    error_message: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def success(data: Any, **metadata: Any) -> APIResult:
    return APIResult(success=True, data=data, metadata=metadata)


def failure(exc: Exception) -> APIResult:
    code = exc.error_code if isinstance(exc, GeoMCPError) else "INTERNAL_ERROR"
    return APIResult(success=False, error_code=code, error_message=str(exc))
