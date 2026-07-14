#!/usr/bin/env bash
set -euo pipefail
export PYTHONDONTWRITEBYTECODE=1

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORK_DIR="${DJANGO_TY_CONFORMANCE_DIR:-/tmp/django-ty-differential-conformance}"
BUILD_DIR="${DJANGO_TY_BUILD_DIR:-/tmp/django-ty-build-cache}"
MODE="${1:---check}"
TY_EXTENDED_VERSION="$(
  uv run --no-project --python 3.11 \
    python "$ROOT/scripts/compatibility_value.py" ty_extended
)"

if [ "$MODE" != "--check" ] && [ "$MODE" != "--write" ]; then
  echo "usage: scripts/differential-conformance.sh [--check|--write]" >&2
  exit 2
fi

rm -rf "$WORK_DIR"
mkdir -p "$WORK_DIR/django-ty-dist" "$BUILD_DIR"

uv venv --python 3.13 "$WORK_DIR/reference"
uv pip install \
  --python "$WORK_DIR/reference/bin/python" \
  --requirement "$ROOT/conformance/reference-requirements.txt"

DIST_DIR="$WORK_DIR/django-ty-dist" \
  CARGO_TARGET_DIR="$BUILD_DIR/django-ty-target" \
  bash "$ROOT/scripts/build-wheel.sh"

uv venv --python 3.13 "$WORK_DIR/candidate"
uv pip install \
  --python "$WORK_DIR/candidate/bin/python" \
  --requirement "$ROOT/conformance/candidate-requirements.txt" \
  "ty-extended==$TY_EXTENDED_VERSION" \
  "$WORK_DIR"/django-ty-dist/*.whl

if ! "$WORK_DIR/candidate/bin/python" -c \
  'import importlib.metadata as metadata, importlib.util; assert importlib.util.find_spec("django_stubs_ext") is None; files = {str(path) for path in metadata.distribution("django-ty").files or ()}; assert not any(path.startswith("django_stubs_ext/") for path in files); assert not any(distribution.metadata.get("Name", "").lower() in {"django-stubs", "django-stubs-ext", "mypy"} for distribution in metadata.distributions())'
then
  echo "candidate must not install or package django-stubs, django-stubs-ext, or mypy" >&2
  exit 1
fi

"$WORK_DIR/candidate/bin/python" "$ROOT/scripts/evaluate_differential_conformance.py" \
  --mypy-bin "$WORK_DIR/reference/bin/mypy" \
  --ty-bin "$WORK_DIR/candidate/bin/ty" \
  --ty-python "$WORK_DIR/candidate" \
  "$MODE"
