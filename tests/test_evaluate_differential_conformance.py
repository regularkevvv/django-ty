from __future__ import annotations

import unittest

from scripts.evaluate_differential_conformance import (
    ConformanceError,
    normalize_ty_checker_version,
)


class NormalizeTyCheckerVersionTest(unittest.TestCase):
    commit = "abcdef1234567890abcdef1234567890abcdef12"

    def normalize(self, reported: str) -> str:
        return normalize_ty_checker_version(reported, "1.2.3", self.commit)

    def test_accepts_release_without_embedded_commit(self) -> None:
        self.assertEqual(self.normalize("ty 1.2.3"), "ty 1.2.3")

    def test_accepts_release_with_matching_embedded_commit(self) -> None:
        self.assertEqual(
            self.normalize("ty 1.2.3 (abcdef123 2030-01-02)"),
            "ty 1.2.3",
        )

    def test_accepts_source_build_metadata(self) -> None:
        self.assertEqual(
            self.normalize("ty 1.2.3+4 (abcdef123 2030-01-02)"),
            "ty 1.2.3",
        )

    def test_rejects_wrong_version(self) -> None:
        with self.assertRaisesRegex(ConformanceError, "expected ty 1.2.3"):
            self.normalize("ty 1.2.2")

    def test_rejects_wrong_embedded_commit(self) -> None:
        with self.assertRaisesRegex(ConformanceError, "expected abcdef123"):
            self.normalize("ty 1.2.3 (deadbeef0 2030-01-02)")


if __name__ == "__main__":
    unittest.main()
