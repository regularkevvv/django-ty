from __future__ import annotations

import unittest

from scripts.probe_django_versions import aggregate, check_declared_flags


class DeclaredCompatibilityTest(unittest.TestCase):
    def test_probe_cannot_claim_support_above_install_bound(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "disagrees"):
            check_declared_flags([{"django": "6.1.1", "declared": True}], ">=5.0,<6.1")

    def test_bound_widening_requires_the_probe_declaration_to_change(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "disagrees"):
            check_declared_flags([{"django": "6.1.1", "declared": False}], ">=5.0,<6.2")


class MatrixEvidenceTest(unittest.TestCase):
    def test_matrix_cannot_combine_different_corpus_revisions(self) -> None:
        results = [{"corpus": {"sha256": "old"}}, {"corpus": {"sha256": "new"}}]
        with self.assertRaisesRegex(RuntimeError, "different corpus"):
            aggregate({}, [{}, {}], results, {}, "")

    def test_matrix_cannot_omit_a_pair(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "completed result"):
            aggregate({}, [{}, {}], [{}], {}, "")

    def test_matrix_cannot_change_semantic_authority(self) -> None:
        results = [
            {"corpus": {}, "authority": "Django"},
            {"corpus": {}, "authority": "mypy"},
        ]
        with self.assertRaisesRegex(RuntimeError, "different semantic authorities"):
            aggregate({}, [{}, {}], results, {}, "")


class ReferenceSupportTest(unittest.TestCase):
    def test_unsupported_pairs_fail_before_installing(self):
        from copy import deepcopy
        from scripts.probe_django_versions import (
            ROOT,
            load_toml,
            check_reference_support,
        )

        support = load_toml(ROOT / "compatibility/reference-support.toml")
        matrix = load_toml(ROOT / "compatibility/django-versions.toml")["matrix"][
            "probe"
        ]
        check_reference_support(matrix, support)
        for change in (
            {"python": ["3.15"]},
            {"mypy": "3.0.0"},
            {"mypy": "1.0.0"},
            {"django_stubs_commit": "unreviewed"},
            {"django_stubs": "99.0.0"},
            {"django": "4.0.0"},
        ):
            broken = deepcopy(matrix)
            broken[0].update(change)
            with self.subTest(change=change), self.assertRaises(RuntimeError):
                check_reference_support(broken, support)
        broken = deepcopy(matrix)
        broken[0]["django"] = "5.2.17"
        broken[0]["python"] = ["3.14"]
        with self.assertRaisesRegex(RuntimeError, "comparator Python"):
            check_reference_support(broken, support)


if __name__ == "__main__":
    unittest.main()
