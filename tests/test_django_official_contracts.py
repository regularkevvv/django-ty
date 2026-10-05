from __future__ import annotations
import unittest
from scripts.django_official_contracts import (
    load_contracts,
    reviewed_difference,
    documentation_url,
)


class OfficialContractTest(unittest.TestCase):
    def setUp(self):
        self.contracts = load_contracts()
        self.runtime = {
            "django": "5.0.14",
            "cases": {"fresh-request-get": {"passed": True}},
        }

    def test_mypy_cannot_define_an_unreviewed_contract(self):
        with self.assertRaisesRegex(ValueError, "unreviewed"):
            reviewed_difference(
                "http.querydict-mutability",
                "unknown",
                "pass",
                "5.0.14",
                self.runtime,
                self.contracts,
            )

    def test_changed_expectation_requires_review(self):
        with self.assertRaisesRegex(ValueError, "unreviewed"):
            reviewed_difference(
                "http.querydict-mutability",
                "fresh-get-write",
                "fail",
                "5.0.14",
                self.runtime,
                self.contracts,
            )

    def test_missing_and_wrong_version_runtime_proofs_fail(self):
        for runtime in [
            {"django": "5.0.14", "cases": {}},
            {"django": "6.1.1", "cases": {"fresh-request-get": {"passed": True}}},
        ]:
            with self.subTest(runtime=runtime), self.assertRaisesRegex(
                ValueError, "runtime proof"
            ):
                reviewed_difference(
                    "http.querydict-mutability",
                    "fresh-get-write",
                    "pass",
                    "5.0.14",
                    runtime,
                    self.contracts,
                )

    def test_official_reference_matches_the_installed_django_line(self):
        result = reviewed_difference(
            "http.querydict-mutability",
            "fresh-get-write",
            "pass",
            "5.0.14",
            self.runtime,
            self.contracts,
        )
        self.assertIn("/en/5.0/", result["documentation"])
        self.assertIn("/blob/5.0.14/", result["django_source"])
        self.assertEqual(result["classification"], "deliberate-policy-or-limit")

    def test_external_or_escaping_documentation_routes_fail(self):
        for route in ["https://example.com", "../other", "/other"]:
            with self.subTest(route=route), self.assertRaisesRegex(
                ValueError, "invalid"
            ):
                documentation_url("6.1.1", "apps.model-registry", self.contracts, route)


class CheckedEvidenceTest(unittest.TestCase):
    def check_changed_result(self, change):
        import copy
        from scripts.evaluate_django_stubs_coverage import (
            load_map,
            load_result,
            check_result,
        )

        config = load_map()
        result = copy.deepcopy(load_result())
        change(result)
        return check_result(
            result, config["baseline"], config["conformance"], config["feature"]
        )

    def test_current_evidence_passes(self):
        self.assertEqual(self.check_changed_result(lambda result: None), [])

    def test_stale_proof_script_cannot_reuse_green_results(self):
        errors = self.check_changed_result(
            lambda result: result["corpus"].update(runtime_proof_sha256="stale")
        )
        self.assertTrue(any("stale" in error for error in errors))

    def test_missing_runtime_proof_cannot_reuse_green_results(self):
        errors = self.check_changed_result(
            lambda result: result["django_runtime"]["cases"].clear()
        )
        self.assertTrue(any("runtime evidence" in error for error in errors))

    def test_contract_score_cannot_hide_a_failed_feature(self):
        errors = self.check_changed_result(
            lambda result: result["features"][0].update(contract_matched=0)
        )
        self.assertTrue(any("score totals" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
