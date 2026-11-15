"""Relation annotations follow Django's object/key behavior."""

from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path


class RelationRuntimeTests(unittest.TestCase):
    def test_real_django_and_sqlite_contracts(self):
        script = (
            Path(__file__).resolve().parents[1] / "scripts/check_relation_runtime.py"
        )
        result = subprocess.run(
            [sys.executable, str(script)], check=True, capture_output=True, text=True
        )
        report = json.loads(result.stdout)
        self.assertTrue(report["passed"])
        self.assertEqual(len(report["cases"]), 31)
        self.assertTrue(all(report["cases"].values()))
