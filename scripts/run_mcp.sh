#!/usr/bin/env bash
set -euo pipefail

ROOT="${GEOMCP_HOME:-/cluster/datapool2/xuxy/GeoMCP}"
export GEOMCP_HOME="$ROOT"
export GEOMCP_CONFIG_DIR="${GEOMCP_CONFIG_DIR:-$ROOT/config}"

cd "$ROOT"
exec "$ROOT/.venv/bin/geomcp-mcp"
