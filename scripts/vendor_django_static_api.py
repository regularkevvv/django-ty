#!/usr/bin/env python3
"""Vendor the reviewed Django static API from a pinned source checkout."""

from __future__ import annotations

import argparse
import shutil
import subprocess
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:
    import tomli as tomllib


ROOT = Path(__file__).resolve().parents[1]
MAP_PATH = ROOT / "compatibility" / "django-stubs-6.1.1.toml"
from normalize_static_api import normalize_stub


def load_baseline() -> dict[str, object]:
    with MAP_PATH.open("rb") as file:
        return tomllib.load(file)["baseline"]


def git_commit(repository_root: Path) -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repository_root,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def copy_files(source_root: Path, destination_root: Path, include) -> int:
    shutil.rmtree(destination_root, ignore_errors=True)
    destination_root.mkdir(parents=True)
    copied = 0
    for source in sorted(
        path for path in source_root.rglob("*") if path.is_file() and include(path)
    ):
        destination = destination_root / source.relative_to(source_root)
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
        copied += 1
    return copied


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--upstream-root", required=True, help="reviewed django-stubs source checkout"
    )
    args = parser.parse_args()

    baseline = load_baseline()
    upstream_root = Path(args.upstream_root).resolve()
    with (upstream_root / "pyproject.toml").open("rb") as file:
        version = tomllib.load(file)["project"]["version"]
    if version != baseline["version"]:
        raise SystemExit(
            f"source version {version} does not match pinned {baseline['version']}"
        )
    commit = git_commit(upstream_root)
    if commit != baseline["commit"]:
        raise SystemExit(
            f"source commit {commit} does not match pinned {baseline['commit']}"
        )

    stub_source = upstream_root / str(baseline["upstream_stub_root"])
    stub_destination = ROOT / str(baseline["vendored_stub_root"])
    stub_count = copy_files(
        stub_source,
        stub_destination,
        lambda path: path.suffix == ".pyi" or path.name == "py.typed",
    )
    for path in stub_destination.rglob("*.pyi"):
        source = path.read_text(encoding="utf-8")
        path.write_text(
            normalize_stub(path.relative_to(stub_destination).as_posix(), source),
            encoding="utf-8",
        )
    shutil.rmtree(
        ROOT / "python" / "django_ty" / "stubs" / "django_stubs_ext", ignore_errors=True
    )
    print(
        f"vendored {stub_count} Django static files with the required settings type inlined"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
