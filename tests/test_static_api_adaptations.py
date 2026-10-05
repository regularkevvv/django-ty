from __future__ import annotations

import unittest

from scripts.normalize_static_api import normalize_stub


class StaticApiAdaptationsTest(unittest.TestCase):
    def test_fresh_request_constructor_preserves_mutable_querydicts(self) -> None:
        source = 'class HttpRequest:\n    def __init__(self) -> None: ...\n\n_Z = TypeVar("_Z")\n'
        adapted = normalize_stub("http/request.pyi", source)
        self.assertIn("def __init__(self) -> None", adapted)
        self.assertNotIn("def __new__", adapted)
        self.assertIn("class _MutableHttpRequest(HttpRequest)", adapted)
        self.assertIn("GET: QueryDict", adapted)
        self.assertIn("POST: QueryDict", adapted)
        self.assertEqual(normalize_stub("http/request.pyi", adapted), adapted)

    def test_python_310_backports_preserve_type_information(self) -> None:
        cases = {
            "db/models/query.pyi": "from typing import Any, Self, Never\n",
            "db/models/enums.pyi": "import enum\nimport sys\nfrom enum import EnumType, IntEnum, StrEnum\nfrom enum import property as enum_property\n",
            "db/migrations/operations/base.pyi": "from enum import StrEnum\n",
            "utils/csp.pyi": "from enum import StrEnum as _StrEnum\n",
        }
        for path, source in cases.items():
            with self.subTest(path=path):
                adapted = normalize_stub(path, source)
                self.assertEqual(normalize_stub(path, adapted), adapted)
                if path.endswith("query.pyi"):
                    self.assertIn("from typing_extensions import Self, Never", adapted)
                    self.assertIn("from typing import Any", adapted)
                else:
                    self.assertIn("version_info >= (3, 11)", adapted)
                    self.assertIn("(str,", adapted)


if __name__ == "__main__":
    unittest.main()
