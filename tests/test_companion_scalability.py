from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path

from scripts.check_companion_scalability import check


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
