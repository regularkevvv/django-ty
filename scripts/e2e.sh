#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORK_DIR="${DJANGO_TY_E2E_DIR:-/tmp/django-ty-wheel-e2e}"
BUILD_DIR="${DJANGO_TY_BUILD_DIR:-/tmp/django-ty-build-cache}"
DJANGO_TY_DIST="$WORK_DIR/django-ty-dist"
TY_EXTENDED_VERSION="$(
  uv run --no-project --python 3.11 \
    python "$ROOT/scripts/compatibility_value.py" ty_extended
)"

rm -rf "$WORK_DIR"
mkdir -p "$DJANGO_TY_DIST" "$BUILD_DIR"

DIST_DIR="$DJANGO_TY_DIST" \
  CARGO_TARGET_DIR="$BUILD_DIR/django-ty-target" \
  bash "$ROOT/scripts/build-wheel.sh"
DJANGO_TY_WHEEL="$(find "$DJANGO_TY_DIST" -maxdepth 1 -name 'django_ty-*.whl' -print -quit)"
if [ -z "$DJANGO_TY_WHEEL" ]; then
  echo "django-ty wheel was not built" >&2
  exit 1
fi

cp -R "$ROOT/e2e/django5_fixture/." "$WORK_DIR/"
rm -f "$WORK_DIR/ty.toml"
rm -rf "$WORK_DIR/.ty"

(
  cd "$WORK_DIR"
  uv init --no-package --no-readme --no-workspace --vcs none
  printf '\n[tool.ty.plugins]\nauto-discover = true\n' >> pyproject.toml
  uv add "$DJANGO_TY_WHEEL"

  package_dir="$(uv run python -c 'import pathlib, django_ty; print(pathlib.Path(django_ty.__file__).parent)')"
  test -f "$package_dir/django_ty.wasm"
  test -f "$package_dir/ty-plugin.json"
  test -f "$package_dir/stubs/django/db/models/query.pyi"
  test ! -e "$package_dir/stubs/django_stubs_ext"
  test ! -e "$package_dir/stubs/mypy_django_plugin"
  test -f "$package_dir/THIRD_PARTY_NOTICES.md"
  test ! -e .ty
  uv run python -c 'import importlib.metadata as metadata, importlib.util, sys; names = {distribution.metadata["Name"].lower() for distribution in metadata.distributions() if distribution.metadata["Name"]}; assert "django-stubs" not in names; assert "django-stubs-ext" not in names; assert importlib.util.find_spec("django_stubs_ext") is None; assert metadata.version("ty-extended") == sys.argv[1]; assert metadata.version("Django").split(".")[:2] in (["5", "0"], ["5", "1"], ["5", "2"], ["6", "0"])' "$TY_EXTENDED_VERSION"

  uv run ty check accounts library commerce auditlog typechecks/positive.py typechecks/static_api.py

  set +e
  negative_output="$(uv run ty check accounts library commerce auditlog caveats typechecks/negative.py 2>&1)"
  negative_status=$?
  set -e

  if [ "$negative_status" -eq 0 ]; then
    echo "negative django-ty wheel check unexpectedly passed" >&2
    exit 1
  fi

  for expected in \
    'django-ty.unknown-relation-target' \
    'django-ty.reverse-relation-conflict' \
    'django-ty.invalid-lookup-value' \
    'django-ty.unknown-lookup' \
    'Expected `str`, found `Literal[123]`' \
    'Object of type `str` is not assignable to `int'
  do
    if ! grep -F "$expected" <<<"$negative_output" >/dev/null; then
      echo "negative django-ty wheel check missed expected output: $expected" >&2
      printf '%s\n' "$negative_output" >&2
      exit 1
    fi
  done
)

echo "django-ty wheel installation e2e passed in $WORK_DIR"
