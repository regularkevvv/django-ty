from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from scripts.compatibility_value import conformance_value


class ConformanceValueTest(unittest.TestCase):
    def write_map(self, contents: str) -> Path:
        temporary = tempfile.NamedTemporaryFile("w", suffix=".toml", delete=False)
        self.addCleanup(Path(temporary.name).unlink, missing_ok=True)
        with temporary:
            temporary.write(contents)
        return Path(temporary.name)

    def test_reads_string_value(self) -> None:
        path = self.write_map('[conformance]\nhost_version = "1.2.3"\n')
        self.assertEqual(conformance_value("host_version", path), "1.2.3")

    def test_rejects_missing_value(self) -> None:
        path = self.write_map("[conformance]\n")
        with self.assertRaisesRegex(ValueError, "missing string conformance value"):
            conformance_value("host_version", path)


if __name__ == "__main__":
    unittest.main()
