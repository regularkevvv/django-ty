#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORK_DIR="$(mktemp -d "${TMPDIR:-/tmp}/django-ty-monty-parity.XXXXXX")"
trap 'rm -rf "$WORK_DIR"' EXIT
uv venv --python 3.13 "$WORK_DIR/env"
uv pip install --python "$WORK_DIR/env/bin/python" 'ty-extended==0.84.4' 'pydantic-monty==1.0.0'
cargo run --locked --bin django_ty_package_manifest > "$WORK_DIR/manifest.json"
DJANGO_TY_ORACLE_PATH="$WORK_DIR/oracle.jsonl" cargo test --locked --test plugin
for runtime in cpython monty; do
  "$WORK_DIR/env/bin/python" "$ROOT/scripts/check_monty_parity.py" \
    "$WORK_DIR/oracle.jsonl" "$WORK_DIR/responses.jsonl" --runtime "$runtime" --manifest "$WORK_DIR/manifest.json"
  DJANGO_TY_MONTY_RESPONSES="$WORK_DIR/responses.jsonl" \
    cargo test --locked --test monty_parity -- --ignored
done
