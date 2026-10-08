from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path

from scripts.benchmark_runtimes import measure


@unittest.skipUnless(
    hasattr(os, "wait4"), "child resource accounting needs macOS or Linux"
)
class BenchmarkRuntimesTest(unittest.TestCase):
    def test_large_output_does_not_block_and_failures_are_recorded(self):
        with tempfile.TemporaryDirectory() as directory:
            result = measure(
                [sys.executable, "-c", 'import sys; print("x" * 200000); sys.exit(7)'],
                Path(directory),
                10,
            )
        self.assertEqual(result["output"], "x" * 200000)
        self.assertEqual(result["exit_code"], 7)
        self.assertFalse(result["timed_out"])
        self.assertGreater(result["peak_rss_bytes"], 0)

    def test_timeout_kills_and_reaps_only_the_owned_process_group(self):
        with tempfile.TemporaryDirectory() as directory:
            result = measure(
                [sys.executable, "-c", "import time; time.sleep(30)"],
                Path(directory),
                0.1,
            )
        self.assertTrue(result["timed_out"])
        self.assertEqual(result["exit_code"], -9)
