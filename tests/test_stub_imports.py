from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from scripts.audit_stub_imports import unresolved_imports


class StubImportTest(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)

    def write(self, name, contents):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(contents)

    def test_transitive_reexports_detect_removed_definitions(self):
        self.write("base.pyi", "class Field: ...\n")
        self.write("exports.pyi", "from .base import Field as PublicField\n")
        self.write("consumer.pyi", "from .exports import PublicField\n")
        self.assertEqual(unresolved_imports(self.root), [])
        self.write("base.pyi", "class DifferentField: ...\n")
        self.assertEqual(
            unresolved_imports(self.root),
            [("django.base", "Field"), ("django.exports", "PublicField")],
        )

    def test_missing_local_modules_fail_and_external_imports_are_separate(self):
        self.write(
            "consumer.pyi", "from django.missing import Field\nfrom typing import Any\n"
        )
        self.assertEqual(unresolved_imports(self.root), [("django.missing", "Field")])

    def test_relative_star_exports_and_submodules_resolve(self):
        self.write("pkg/__init__.pyi", "from .base import *\n")
        self.write("pkg/base.pyi", "class Field: ...\n")
        self.write("consumer.pyi", "from django import pkg\nfrom .pkg import Field\n")
        self.assertEqual(unresolved_imports(self.root), [])


if __name__ == "__main__":
    unittest.main()
