"""Resolve backend configuration from the candidate's installed package."""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path


def checker_options(
    environment: Path, runtime: str | None = None, settings_module: str | None = None
) -> list[str]:
    selected = runtime or os.environ.get("DJANGO_TY_RUNTIME", "wasm")
    if selected not in {"wasm", "monty"}:
        raise ValueError("DJANGO_TY_RUNTIME must be wasm or monty")
    return json.loads(
        subprocess.check_output(
            [
                str(environment / "bin/python"),
                "-c",
                "import json, sys; from django_ty.runtime import checker_options; "
                "print(json.dumps(checker_options(sys.argv[1], sys.argv[2] or None)))",
                selected,
                settings_module or "",
            ],
            text=True,
        )
    )
