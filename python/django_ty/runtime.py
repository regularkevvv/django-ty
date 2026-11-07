"""Configure the packaged Django plugin for the Monty companion."""

from __future__ import annotations

import json
from pathlib import Path


def config_overrides(
    runtime: str = "monty",
    package_dir: Path | None = None,
    settings_module: str | None = None,
) -> list[str]:
    if runtime != "monty":
        raise ValueError("runtime must be monty")
    directory = (package_dir or Path(__file__).parent).resolve()
    entry = {
        "id": "django-ty",
        "runtime": runtime,
        "trusted": True,
        "path": str(directory / "monty.py"),
        "manifest-path": str(directory / "ty-plugin.json"),
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


def checker_options(
    runtime: str = "monty", settings_module: str | None = None
) -> list[str]:
    return [
        part
        for override in config_overrides(runtime, settings_module=settings_module)
        for part in ("--config", override)
    ]
