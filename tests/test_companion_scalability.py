from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path

from scripts.check_companion_scalability import check, diagnostics_match


@unittest.skipUnless(os.name == "posix", "requires POSIX process groups and RSS")
class ResourceGuardTest(unittest.TestCase):
    def measure(self, source: str, timeout: float, max_mib: int = 512):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            project = root / "project"
            output = root / "output"
            project.mkdir()
            output.mkdir()
            (project / "source.py").write_text("value: int = 1\n")
            result = check(
                [sys.executable, "-c", source],
                project,
                output,
                timeout=timeout,
                max_mib=max_mib,
            )
            text = Path(result["stdout"]).read_text()
        self.assertTrue(result["source_preserved"])
        return result, text

    def test_large_output_is_drained_and_failure_is_recorded(self):
        result, text = self.measure('import sys; print("x" * 200000); sys.exit(7)', 10)
        self.assertEqual(result["exit"], 7)
        self.assertEqual(text, "x" * 200000 + "\n")
        self.assertIsNone(result["stopped"])

    def test_timeout_kills_only_the_owned_process_group(self):
        result, _ = self.measure("import time; time.sleep(30)", 0.1)
        self.assertEqual(result["stopped"], "timeout")
        self.assertEqual(result["exit"], -9)

    def test_memory_budget_includes_descendants(self):
        source = "import subprocess, sys, time; subprocess.Popen([sys.executable, '-c', 'import time; data=bytearray(120*1024*1024); time.sleep(30)']); time.sleep(30)"
        result, _ = self.measure(source, 10, 64)
        self.assertEqual(result["stopped"], "memory-limit")
        self.assertGreater(result["peak_process_tree_rss_kib"], 64 * 1024)
        self.assertEqual(result["exit"], -9)


class SemanticGuardTest(unittest.TestCase):
    def errors(self):
        return [
            {
                "check_name": "invalid-assignment",
                "description": "str is not int",
                "location": {"path": "checks.py", "positions": {"begin": {"line": 4}}},
            },
            {
                "check_name": "plugin-configuration",
                "description": "Unknown Django lookup missing_name: django-ty.unknown-lookup",
                "location": {"path": "checks.py", "positions": {"begin": {"line": 5}}},
            },
        ]

    def test_both_ordinary_and_django_errors_are_required(self):
        errors = self.errors()
        self.assertTrue(diagnostics_match(errors, True, 3))
        self.assertFalse(diagnostics_match(errors[:1], True, 3))
        self.assertTrue(diagnostics_match([], False, 3))

    def test_plugin_failure_cannot_stand_in_for_django_validation(self):
        errors = self.errors()
        errors[1]["description"] = "plugin crashed before checking models"
        self.assertFalse(diagnostics_match(errors, True, 3))

    def test_unrelated_source_error_cannot_satisfy_the_control(self):
        errors = self.errors()
        errors[1]["location"]["path"] = "models.py"
        self.assertFalse(diagnostics_match(errors, True, 3))
        errors = self.errors()
        errors[1]["location"]["positions"]["begin"]["line"] = 6
        self.assertFalse(diagnostics_match(errors, True, 3))

    def test_extra_diagnostics_are_not_ignored(self):
        errors = self.errors()
        self.assertFalse(diagnostics_match(errors + errors[:1], True, 3))
