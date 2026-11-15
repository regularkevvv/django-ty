"""Call handlers produce the same answers with shared module initialization."""

from __future__ import annotations

import importlib.util
import json
import unittest
from pathlib import Path


class StatelessCallsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        sdk = importlib.util.find_spec("ty_extended.plugin_sdk")
        assert sdk is not None and sdk.origin is not None
        source = Path(sdk.origin).read_text()
        source += (
            "\n"
            + (
                Path(__file__).resolve().parents[1] / "python/django_ty/monty.py"
            ).read_text()
        )
        cls.code = compile(source, "django_ty_stateless_test.py", "exec")

    def namespace(self):
        namespace = {}
        exec(self.code, namespace)
        return namespace

    @staticmethod
    def model(name, custom_key=False):
        fields = [
            {
                "name": "name",
                "assigned-value": {
                    "kind": "call",
                    "callee": {"qualified-name": "django.db.models.CharField"},
                    "arguments": [],
                },
            }
        ]
        if custom_key:
            fields.append(
                {
                    "name": "slug",
                    "assigned-value": {
                        "kind": "call",
                        "callee": {"qualified-name": "django.db.models.CharField"},
                        "arguments": [
                            {
                                "kind": "keyword",
                                "name": "primary_key",
                                "value": {"kind": "bool", "value": True},
                            }
                        ],
                    },
                }
            )
        return {
            "qualified-name": name,
            "bases": [
                {"expression": "django.db.models.base.Model", "mode": "annotation"}
            ],
            "fields": fields,
        }

    def test_shared_initialization_matches_fresh_handlers(self):
        previous = None
        for custom_key in [False, True]:
            index = self.namespace()["build_django_index"](
                {
                    "context": {"config": {}},
                    "classes": [
                        self.model("one.Book", custom_key),
                        self.model("two.Book"),
                    ],
                }
            )["plugin-index"]
            before = json.dumps(index, sort_keys=True)
            requests = []
            for _ in range(10):
                for name in ["one.Book", "two.Book"]:
                    for kind in ["adjust-call-return", "adjust-call-state"]:
                        requests.append(
                            {
                                "kind": kind,
                                "context": {
                                    "config": {},
                                    "speculative": kind == "adjust-call-return",
                                },
                                "callee": {
                                    "expression": "django.db.models.query._BaseQuerySet.get",
                                    "mode": "expression",
                                },
                                "receiver": {
                                    "type-expr": {
                                        "expression": "django.db.models.manager.BaseManager["
                                        + name
                                        + "]",
                                        "mode": "annotation",
                                    },
                                    "nominal-class": "django.db.models.manager.BaseManager",
                                    "generic-arguments": [
                                        {"expression": name, "mode": "annotation"}
                                    ],
                                },
                                "arguments": [],
                                "default-return-type": {
                                    "expression": "object",
                                    "mode": "annotation",
                                },
                                "project-index": index,
                            }
                        )
            shared = self.namespace()
            answers = []
            for request in requests:
                encoded = json.dumps(request)
                expected = json.loads(self.namespace()["__ty_handle__"](encoded))
                actual = json.loads(shared["__ty_handle__"](encoded))
                self.assertEqual(actual, expected)
                answers.append(actual)
            self.assertTrue(any(r["kind"] == "call-return-patch" for r in answers))
            self.assertTrue(any(r["kind"] == "call-state-patch" for r in answers))
            if previous is not None:
                self.assertNotEqual(answers, previous)
            previous = answers
            self.assertEqual(json.dumps(index, sort_keys=True), before)


if __name__ == "__main__":
    unittest.main()
