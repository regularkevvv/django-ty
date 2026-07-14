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
MAP_PATH = ROOT / "compatibility" / "django-stubs-6.0.6.toml"
TEMPLATES_SETTING_IMPORT = "from django_stubs_ext.settings import TemplatesSetting\n"
TEMPLATES_SETTING_CLASS = """@type_check_only
class TemplatesSetting(TypedDict):
    BACKEND: str
    NAME: NotRequired[str]
    DIRS: NotRequired[list[str | _Path]]
    APP_DIRS: NotRequired[bool]
    OPTIONS: NotRequired[dict[str, Any]]
"""


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
    for source in sorted(path for path in source_root.rglob("*") if path.is_file() and include(path)):
        destination = destination_root / source.relative_to(source_root)
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
        copied += 1
    return copied


def inline_templates_setting(path: Path) -> None:
    source = path.read_text(encoding="utf-8")
    if TEMPLATES_SETTING_IMPORT not in source:
        raise ValueError(f"{path} no longer imports TemplatesSetting as expected")
    source = source.replace(
        "from collections.abc import Collection, Mapping, Sequence\n",
        "from collections.abc import Collection, Mapping, Sequence\nfrom pathlib import Path as _Path\n",
        1,
    )
    source = source.replace(TEMPLATES_SETTING_IMPORT, TEMPLATES_SETTING_CLASS, 1)
    path.write_text(source, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--upstream-root", required=True, help="reviewed django-stubs source checkout")
    args = parser.parse_args()

    baseline = load_baseline()
    upstream_root = Path(args.upstream_root).resolve()
    with (upstream_root / "pyproject.toml").open("rb") as file:
        version = tomllib.load(file)["project"]["version"]
    if version != baseline["version"]:
        raise SystemExit(f"source version {version} does not match pinned {baseline['version']}")
    commit = git_commit(upstream_root)
    if commit != baseline["commit"]:
        raise SystemExit(f"source commit {commit} does not match pinned {baseline['commit']}")

    stub_source = upstream_root / str(baseline["upstream_stub_root"])
    stub_destination = ROOT / str(baseline["vendored_stub_root"])
    stub_count = copy_files(stub_source, stub_destination, lambda path: path.suffix == ".pyi" or path.name == "py.typed")
    inline_templates_setting(stub_destination / "conf" / "global_settings.pyi")
    shutil.rmtree(ROOT / "python" / "django_ty" / "stubs" / "django_stubs_ext", ignore_errors=True)
    print(f"vendored {stub_count} Django static files with the required settings type inlined")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
