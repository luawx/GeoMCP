"""Path normalization helpers used by all entry points."""

from __future__ import annotations

from pathlib import Path

from geomcp.exceptions import InvalidPathError


def resolve_path(path: str | Path, *, must_exist: bool = True) -> Path:
    if path is None or str(path).strip() == "":
        raise InvalidPathError("Path must not be empty")
    candidate = Path(path).expanduser()
    try:
        return candidate.resolve(strict=must_exist)
    except (OSError, RuntimeError) as exc:
        raise InvalidPathError(f"Unable to resolve path {candidate}: {exc}") from exc


def is_within(path: Path, root: Path) -> bool:
    return path == root or root in path.parents
