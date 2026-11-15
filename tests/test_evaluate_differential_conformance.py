from __future__ import annotations

import unittest

from scripts.evaluate_differential_conformance import (
    ConformanceError,
    Diagnostic,
    candidate_checker_identity,
    normalize_ty_checker_version,
    require_reachable,
)


class NormalizeTyCheckerVersionTest(unittest.TestCase):
    commit = "abcdef1234567890abcdef1234567890abcdef12"

    def normalize(self, reported: str) -> str:
        return normalize_ty_checker_version(reported, "1.2.3", self.commit)

    def test_accepts_release_without_embedded_commit(self) -> None:
        self.assertEqual(self.normalize("ty-extended 1.2.3"), "ty-extended 1.2.3")

    def test_accepts_primary_command_name(self) -> None:
        self.assertEqual(self.normalize("tyx 1.2.3"), "ty-extended 1.2.3")

    def test_accepts_release_with_matching_embedded_commit(self) -> None:
        self.assertEqual(
            self.normalize("ty-extended 1.2.3 (abcdef123 2030-01-02)"),
            "ty-extended 1.2.3",
        )

    def test_accepts_source_build_metadata(self) -> None:
        self.assertEqual(
            self.normalize("ty-extended 1.2.3+4 (abcdef123 2030-01-02)"),
            "ty-extended 1.2.3",
        )

    def test_rejects_official_or_legacy_checker_name(self) -> None:
        with self.assertRaisesRegex(ConformanceError, "expected ty-extended"):
            self.normalize("ty 1.2.3")

    def test_rejects_wrong_version(self) -> None:
        with self.assertRaisesRegex(ConformanceError, "expected ty-extended 1.2.3"):
            self.normalize("ty-extended 1.2.2")

    def test_rejects_wrong_embedded_commit(self) -> None:
        with self.assertRaisesRegex(ConformanceError, "expected abcdef123"):
            self.normalize("ty-extended 1.2.3 (deadbeef0 2030-01-02)")


class CandidateCheckerIdentityTest(unittest.TestCase):
    baseline = {
        "ty_extended": "0.90.0",
        "ty_extended_commit": NormalizeTyCheckerVersionTest.commit,
    }

    def identity(self, reported, installed, probe=True):
        return candidate_checker_identity(
            reported, installed, self.baseline, probe=probe
        )

    def test_probe_accepts_installed_new_release_without_old_commit_claim(self):
        for name in ("tyx", "ty-extended"):
            with self.subTest(command=name):
                self.assertEqual(
                    self.identity(f"{name} 0.91.0", "0.91.0"),
                    ("ty-extended 0.91.0", None),
                )

    def test_probe_rejects_executable_from_a_different_installation(self):
        with self.assertRaisesRegex(ConformanceError, "expected ty-extended 0.91.0"):
            self.identity("ty-extended 0.90.0", "0.91.0")

    def test_probe_rejects_official_ty(self):
        with self.assertRaises(ConformanceError):
            self.identity("ty 0.91.0", "0.91.0")

    def test_pinned_mode_still_rejects_new_distribution(self):
        with self.assertRaisesRegex(ConformanceError, "expected.*0.90.0"):
            self.identity("ty-extended 0.91.0", "0.91.0", probe=False)

    def test_pinned_mode_retains_baseline_commit(self):
        self.assertEqual(
            self.identity("ty-extended 0.90.0", "0.90.0", probe=False),
            ("ty-extended 0.90.0", self.baseline["ty_extended_commit"]),
        )

    def test_probe_still_validates_embedded_commit_for_baseline_version(self):
        with self.assertRaisesRegex(ConformanceError, "expected abcdef123"):
            self.identity("tyx 0.90.0 (deadbeef0 2030-01-02)", "0.90.0")


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
            ConformanceError,
            Diagnostic,
            Marker,
            require_expected_diagnostic,
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
