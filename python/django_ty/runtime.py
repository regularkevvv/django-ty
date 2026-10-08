"""Select a packaged backend without changing the installed wheel."""

from __future__ import annotations

import json
from pathlib import Path


def config_overrides(
    runtime: str, package_dir: Path | None = None, settings_module: str | None = None
) -> list[str]:
    if runtime not in {"wasm", "monty"}:
        raise ValueError("runtime must be wasm or monty")
    directory = (package_dir or Path(__file__).parent).resolve()
    artifact, manifest = (
        ("django_ty.wasm", "ty-plugin.json")
        if runtime == "wasm"
        else ("monty.py", "ty-plugin-monty.json")
    )
    entry = {
        "id": "django-ty",
        "runtime": runtime,
        "trusted": True,
        "path": str(directory / artifact),
        "manifest-path": str(directory / manifest),
        "stub-overlay-path": str(directory / "stubs"),
    }
    table = ", ".join(f"{key} = {json.dumps(value)}" for key, value in entry.items())
    if settings_module is not None:
        table += (
            ", config = {django-settings-module = " + json.dumps(settings_module) + "}"
        )
    return [
        "plugins.enabled = true",
        "plugins.auto-discover = false",
        f"plugins.plugin = [{{{table}}}]",
    ]


def checker_options(runtime: str, settings_module: str | None = None) -> list[str]:
    return [
        part
        for override in config_overrides(runtime, settings_module=settings_module)
        for part in ("--config", override)
    ]
