from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import tomllib

from scripts.runtime_config import checker_options

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "django_ty_runtime", ROOT / "python/django_ty/runtime.py"
)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class RuntimeConfigTest(unittest.TestCase):
    def test_both_backends_select_exactly_one_plugin_and_the_same_stubs(self):
        for backend, artifact, manifest in [
            ("wasm", "django_ty.wasm", "ty-plugin.json"),
            ("monty", "monty.py", "ty-plugin-monty.json"),
        ]:
            with (
                self.subTest(backend=backend),
                tempfile.TemporaryDirectory() as directory,
            ):
                # Quotes, spaces and backslashes must survive TOML encoding.
                package = Path(directory).resolve() / 'package "quoted" with \\ spaces'
                parsed = tomllib.loads(
                    "\n".join(module.config_overrides(backend, package))
                )
                plugins = parsed["plugins"]
                self.assertTrue(plugins["enabled"])
                self.assertFalse(plugins["auto-discover"])
                self.assertEqual(len(plugins["plugin"]), 1)
                entry = plugins["plugin"][0]
                self.assertEqual(entry["runtime"], backend)
                self.assertEqual(entry["path"], str(package / artifact))
                self.assertEqual(entry["manifest-path"], str(package / manifest))
                self.assertEqual(entry["stub-overlay-path"], str(package / "stubs"))

    def test_settings_configuration_belongs_to_the_explicit_entry(self):
        parsed = tomllib.loads(
            "\n".join(
                module.config_overrides("monty", settings_module="project.settings")
            )
        )
        self.assertEqual(
            parsed["plugins"]["plugin"][0]["config"],
            {"django-settings-module": "project.settings"},
        )

    def test_candidate_interpreter_resolves_its_own_installed_package(self):
        with patch(
            "scripts.runtime_config.subprocess.check_output",
            return_value=json.dumps(["--config", "plugins.enabled=true"]),
        ) as run:
            options = checker_options(Path("/candidate"), "monty")
        self.assertEqual(options, ["--config", "plugins.enabled=true"])
        self.assertEqual(run.call_args.args[0][0], "/candidate/bin/python")
        self.assertEqual(run.call_args.args[0][-2], "monty")

    def test_invalid_runtime_is_rejected_before_launching_a_process(self):
        with patch.dict("os.environ", {"DJANGO_TY_RUNTIME": "typo"}):
            with self.assertRaisesRegex(ValueError, "wasm or monty"):
                checker_options(Path("/candidate"))
        with self.assertRaisesRegex(ValueError, "wasm or monty"):
            module.config_overrides("typo")
