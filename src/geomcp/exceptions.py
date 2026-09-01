"""GeoMCP exception hierarchy."""


class GeoMCPError(Exception):
    """Base class for expected GeoMCP errors."""


class ConfigurationError(GeoMCPError):
    pass


class PermissionDenied(GeoMCPError):
    pass


class InvalidPathError(GeoMCPError):
    pass


class JobError(GeoMCPError):
    pass


class ExecutorError(GeoMCPError):
    pass


class WorkerError(GeoMCPError):
    pass


class ScientificToolError(GeoMCPError):
    pass
