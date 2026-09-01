"""GeoMCP exception hierarchy."""


class GeoMCPError(Exception):
    """Base exception for GeoMCP."""

    error_code = "GEOMCP_ERROR"


class ConfigurationError(GeoMCPError):
    error_code = "CONFIGURATION_ERROR"


class PermissionDenied(GeoMCPError):
    error_code = "PERMISSION_DENIED"


class InvalidPathError(GeoMCPError):
    error_code = "INVALID_PATH"


class JobError(GeoMCPError):
    error_code = "JOB_ERROR"


class ExecutorError(GeoMCPError):
    error_code = "EXECUTOR_ERROR"


class WorkerError(GeoMCPError):
    error_code = "WORKER_ERROR"


class ScientificToolError(GeoMCPError):
    error_code = "SCIENTIFIC_TOOL_ERROR"
