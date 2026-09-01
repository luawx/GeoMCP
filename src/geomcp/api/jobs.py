"""Reserved Python API namespace for Step 06 Job Manager."""

from .result import APIResult


def status(*_: object, **__: object) -> APIResult:
    return APIResult(
        success=False,
        error_code="NOT_IMPLEMENTED",
        error_message="Job Manager is scheduled for Step 06.",
    )
