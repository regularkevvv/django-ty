from __future__ import annotations

import unittest

from scripts.evaluate_differential_conformance import (
    ConformanceError,
    Diagnostic,
    require_reachable,
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


class ReachabilityTest(unittest.TestCase):
    def test_unreachable_assertions_cannot_be_counted_as_acceptance(self) -> None:
        diagnostic = Diagnostic(
            "cases/extras.py", 36, 1, "unreachable", "Statement is unreachable"
        )
        with self.assertRaisesRegex(ConformanceError, "isolate the assertion"):
            require_reachable("mypy", [diagnostic])


class DiagnosticReasonTest(unittest.TestCase):
    def test_invalid_lookup_requires_the_path_error(self):
        from scripts.evaluate_differential_conformance import (
            Marker,
            Diagnostic,
            require_expected_diagnostic,
            ConformanceError,
        )

        marker = Marker(
            "lookups.field-traversal",
            "unknown-related-field",
            "cases/lookups.py",
            8,
            "fail",
        )
        contracts = {
            "review": {
                "lookups.field-traversal/unknown-related-field": {
                    "candidate_diagnostic": "django-ty.unknown-lookup"
                }
            }
        }
        path_error = Diagnostic(
            marker.path,
            marker.line,
            1,
            "plugin-configuration",
            "django-ty.unknown-lookup",
        )
        value_error = Diagnostic(
            marker.path,
            marker.line,
            1,
            "plugin-configuration",
            "django-ty.invalid-lookup-value",
        )
        require_expected_diagnostic(marker, [path_error], contracts)
        for wrong in ([], [value_error], [path_error, value_error]):
            with self.subTest(wrong=wrong), self.assertRaises(ConformanceError):
                require_expected_diagnostic(marker, wrong, contracts)


if __name__ == "__main__":
    unittest.main()
