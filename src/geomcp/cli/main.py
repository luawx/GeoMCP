"""GeoMCP CLI implemented with the standard library argparse module."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

from geomcp.api.filesystem import inspect as inspect_path
from geomcp.api.system import status as system_status
from geomcp.config import GeoMCPConfig
from geomcp.exceptions import GeoMCPError


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="geomcp", description="GeoMCP manual interface")
    parser.add_argument("--json", action="store_true", help="emit JSON output")
    parser.add_argument("--config-dir", help="override GEOMCP_CONFIG_DIR")
    sub = parser.add_subparsers(dest="group", required=True)

    system = sub.add_parser("system")
    system_sub = system.add_subparsers(dest="command", required=True)
    system_sub.add_parser("status")

    config = sub.add_parser("config")
    config_sub = config.add_subparsers(dest="command", required=True)
    config_sub.add_parser("show")
    config_sub.add_parser("validate")

    filesystem = sub.add_parser("filesystem")
    fs_sub = filesystem.add_subparsers(dest="command", required=True)
    inspect_cmd = fs_sub.add_parser("inspect")
    inspect_cmd.add_argument("path")
    return parser


def _emit(payload: dict[str, object], as_json: bool) -> None:
    if as_json:
        print(json.dumps(payload, ensure_ascii=False, indent=2, default=str))
        return
    if payload.get("success") is False:
        print(f"ERROR [{payload.get('error_code')}]: {payload.get('error_message')}")
        return
    data = payload.get("data", payload)
    print(json.dumps(data, ensure_ascii=False, indent=2, default=str))


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    config_dir = Path(args.config_dir) if args.config_dir else None

    if args.group == "system" and args.command == "status":
        result = system_status(config_dir).to_dict()
        _emit(result, args.json)
        return 0 if result["success"] else 2

    if args.group == "filesystem" and args.command == "inspect":
        result = inspect_path(args.path, config_dir).to_dict()
        _emit(result, args.json)
        return 0 if result["success"] else 2

    if args.group == "config":
        try:
            config = GeoMCPConfig.load(config_dir)
            if args.command == "validate":
                payload = {"success": True, "data": {"valid": True, "config_dir": str(config.config_dir)}}
            else:
                payload = {"success": True, "data": config.values}
        except GeoMCPError as exc:
            payload = {"success": False, "error_code": exc.error_code, "error_message": str(exc)}
        _emit(payload, args.json)
        return 0 if payload["success"] else 2

    return 2


if __name__ == "__main__":
    raise SystemExit(main())
