#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CARGO_TARGET_DIR="${CARGO_TARGET_DIR:-"$ROOT/target"}"
DIST_DIR="${DIST_DIR:-"$ROOT/dist"}"
export CARGO_TARGET_DIR

if [ "${DJANGO_TY_RUNTIME:-wasm}" = "monty" ]; then
  python3 "$ROOT/scripts/build-monty-wheel.py" --out-dir "$DIST_DIR"
  exit 0
fi
if [ "${DJANGO_TY_RUNTIME:-wasm}" != "wasm" ]; then
  echo "DJANGO_TY_RUNTIME must be wasm or monty" >&2
  exit 2
fi

cargo build \
  --manifest-path "$ROOT/Cargo.toml" \
  --release \
  --target wasm32-unknown-unknown \
  --locked

cp \
  "$CARGO_TARGET_DIR/wasm32-unknown-unknown/release/django_ty.wasm" \
  "$ROOT/python/django_ty/django_ty.wasm"

cargo run \
  --manifest-path "$ROOT/Cargo.toml" \
  --release \
  --bin django_ty_package_manifest \
  --locked \
  > "$ROOT/python/django_ty/ty-plugin.json"

python3 "$ROOT/scripts/build-monty.py" --from-wasm

rm -rf "$DIST_DIR"
uv build --no-sources --out-dir "$DIST_DIR" "$ROOT"
