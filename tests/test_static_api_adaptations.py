from __future__ import annotations

import unittest

from scripts.normalize_static_api import normalize_stub


class StaticApiAdaptationsTest(unittest.TestCase):
    def test_fresh_request_constructor_preserves_mutable_querydicts(self) -> None:
        source = 'class HttpRequest:\n    def __init__(self) -> None: ...\n\n_Z = TypeVar("_Z")\n'
        adapted = normalize_stub("http/request.pyi", source)
        self.assertIn("def __new__(cls) -> _MutableHttpRequest", adapted)
        self.assertIn("class _MutableHttpRequest(HttpRequest)", adapted)
        self.assertIn("GET: QueryDict", adapted)
        self.assertIn("POST: QueryDict", adapted)
        self.assertEqual(normalize_stub("http/request.pyi", adapted), adapted)


if __name__ == "__main__":
    unittest.main()
