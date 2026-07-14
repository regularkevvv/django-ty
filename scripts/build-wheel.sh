#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CARGO_TARGET_DIR="${CARGO_TARGET_DIR:-"$ROOT/target"}"
DIST_DIR="${DIST_DIR:-"$ROOT/dist"}"
export CARGO_TARGET_DIR

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

rm -rf "$DIST_DIR"
uv build --no-sources --wheel --out-dir "$DIST_DIR" "$ROOT"
