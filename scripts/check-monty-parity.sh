#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
WORK_DIR="$(mktemp -d "${TMPDIR:-/tmp}/django-ty-monty-parity.XXXXXX")"
export CARGO_TARGET_DIR="$WORK_DIR/target"
export CARGO_INCREMENTAL=0
export CARGO_BUILD_JOBS="${CARGO_BUILD_JOBS:-2}"
cleanup() {
  parity_status=$?
  if [ -n "${DJANGO_TY_PARITY_EVIDENCE_DIR:-}" ]; then
    mkdir -p "$DJANGO_TY_PARITY_EVIDENCE_DIR"
    for report in oracle.jsonl responses.jsonl cpython.jsonl; do
      if [ -f "$WORK_DIR/$report" ]; then
        cp "$WORK_DIR/$report" "$DJANGO_TY_PARITY_EVIDENCE_DIR/$report"
      fi
    done
  fi
  cargo clean --manifest-path "$ROOT/Cargo.toml" || true
  rm -rf "$WORK_DIR"
  exit "$parity_status"
}
trap cleanup EXIT
uv venv --python 3.13 "$WORK_DIR/env"
uv pip install --python "$WORK_DIR/env/bin/python" 'ty-extended==0.90.0' 'pydantic-monty==1.5.0'
DJANGO_TY_ORACLE_PATH="$WORK_DIR/oracle.jsonl" cargo test --locked --test plugin
"$WORK_DIR/env/bin/python" "$ROOT/scripts/check_monty_parity.py" \
  "$WORK_DIR/oracle.jsonl" "$WORK_DIR/cpython.jsonl" --runtime cpython
"$WORK_DIR/env/bin/python" "$ROOT/scripts/check_monty_parity.py" \
  "$WORK_DIR/oracle.jsonl" "$WORK_DIR/responses.jsonl" --runtime monty --reference "$WORK_DIR/cpython.jsonl"
DJANGO_TY_MONTY_RESPONSES="$WORK_DIR/responses.jsonl" \
  cargo test --locked --test monty_parity -- --ignored
