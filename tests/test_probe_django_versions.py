from __future__ import annotations

import unittest

from scripts.probe_django_versions import check_declared_flags


class DeclaredCompatibilityTest(unittest.TestCase):
    def test_probe_cannot_claim_support_above_install_bound(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "disagrees"):
            check_declared_flags([{"django": "6.1.1", "declared": True}], ">=5.0,<6.1")

    def test_bound_widening_requires_the_probe_declaration_to_change(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "disagrees"):
            check_declared_flags([{"django": "6.1.1", "declared": False}], ">=5.0,<6.2")


if __name__ == "__main__":
    unittest.main()
