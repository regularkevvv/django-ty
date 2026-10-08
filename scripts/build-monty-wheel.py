"""Build a Python-only alternative wheel without changing the WASM default."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import tempfile
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parent.parent
    subprocess.run(
        ["python3", str(root / "scripts/build-monty.py"), "--check"], check=True
    )
    with tempfile.TemporaryDirectory(prefix="django-ty-monty-build-") as temporary:
        stage = Path(temporary) / "django-ty"
        shutil.copytree(
            root,
            stage,
            ignore=shutil.ignore_patterns(
                ".git",
                "target",
                "dist",
                "coverage",
                "__pycache__",
                "*.egg-info",
                "*.wasm",
            ),
        )
        package = stage / "python/django_ty"
        shutil.copyfile(package / "ty-plugin-monty.json", package / "ty-plugin.json")
        config = stage / "pyproject.toml"
        lines = [
            line
            for line in config.read_text().splitlines()
            if "django_ty.wasm" not in line
        ]
        config.write_text("\n".join(lines) + "\n")
        manifest = json.loads((package / "ty-plugin.json").read_text())
        assert manifest["runtime"] == {"kind": "monty", "artifact": "monty.py"}
        subprocess.run(
            [
                "uv",
                "build",
                "--no-sources",
                "--out-dir",
                str(args.out_dir.resolve()),
                str(stage),
            ],
            check=True,
        )


if __name__ == "__main__":
    main()
