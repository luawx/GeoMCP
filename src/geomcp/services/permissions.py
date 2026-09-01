"""Capability-level permission checks."""

from __future__ import annotations

from geomcp.config import GeoMCPConfig
from geomcp.exceptions import PermissionDenied


class PermissionService:
    def __init__(self, config: GeoMCPConfig):
        self.capabilities = dict(config.section("permissions").get("capabilities", {}))

    def require(self, capability: str) -> None:
        if self.capabilities.get(capability) is not True:
            raise PermissionDenied(f"Capability is disabled: {capability}")

    def ensure_safe_defaults(self) -> None:
        for capability in ("delete", "recursive_delete", "arbitrary_shell", "arbitrary_ssh"):
            if self.capabilities.get(capability) is True:
                raise PermissionDenied(f"Unsafe capability must not be enabled: {capability}")
