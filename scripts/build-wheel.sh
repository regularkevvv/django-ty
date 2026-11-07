#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DIST_DIR="${DIST_DIR:-"$ROOT/dist"}"

python3 "$ROOT/scripts/build-monty.py" --check

rm -rf "$DIST_DIR"
uv build --no-sources --out-dir "$DIST_DIR" "$ROOT"
