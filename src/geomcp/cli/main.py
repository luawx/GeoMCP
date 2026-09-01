"""Human CLI for GeoMCP."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Sequence

import yaml

from geomcp.api import filesystem as filesystem_api
from geomcp.api import system as system_api
from geomcp.models import ApiResult


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="geomcp", description="GeoMCP research service CLI")
    parser.add_argument("--config-dir", type=Path, default=None, help="Override configuration directory")
    sub = parser.add_subparsers(dest="group", required=True)

    system = sub.add_parser("system", help="System operations")
    system_sub = system.add_subparsers(dest="command", required=True)
    system_sub.add_parser("status", help="Show GeoMCP status")

    config = sub.add_parser("config", help="Configuration operations")
    config_sub = config.add_subparsers(dest="command", required=True)
    config_sub.add_parser("show", help="Show merged configuration")
    config_sub.add_parser("validate", help="Validate configuration")

    filesystem = sub.add_parser("filesystem", help="Safe filesystem operations")
    fs_sub = filesystem.add_subparsers(dest="command", required=True)
    inspect_parser = fs_sub.add_parser("inspect", help="Inspect an allowed path")
    inspect_parser.add_argument("path")
    return parser


def _render(result: ApiResult, *, as_json: bool) -> None:
    payload = result.to_dict()
    if as_json:
        print(json.dumps(payload, ensure_ascii=False, indent=2, default=str))
    else:
        print(yaml.safe_dump(payload, allow_unicode=True, sort_keys=False).rstrip())


def main(argv: Sequence[str] | None = None) -> int:
    raw = list(sys.argv[1:] if argv is None else argv)
    as_json = "--json" in raw
    raw = [item for item in raw if item != "--json"]
    args = _parser().parse_args(raw)

    if args.group == "system" and args.command == "status":
        result = system_api.status(args.config_dir)
    elif args.group == "config" and args.command == "show":
        result = system_api.config_snapshot(args.config_dir)
    elif args.group == "config" and args.command == "validate":
        result = system_api.validate(args.config_dir)
    elif args.group == "filesystem" and args.command == "inspect":
        result = filesystem_api.inspect(args.path, config_dir=args.config_dir)
    else:  # pragma: no cover
        _parser().error("Unsupported command")
        return 2

    _render(result, as_json=as_json)
    return 0 if result.success else 2


if __name__ == "__main__":
    raise SystemExit(main())
