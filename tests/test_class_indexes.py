"""Class-scoped indexes preserve hook semantics without copying every model."""

from __future__ import annotations

import importlib.util
import json
import unittest
from pathlib import Path


class ClassIndexesTest(unittest.TestCase):
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
        cls.namespace = {}
        exec(compile(source, "django_ty_monty_test.py", "exec"), cls.namespace)

    def response(self, request):
        return json.loads(self.namespace["__ty_handle__"](json.dumps(request)))

    def test_manifest_is_constructed_only_for_the_handshake(self):
        self.assertIsNone(self.namespace["_MANIFEST"])
        package = Path(__file__).resolve().parents[1] / "python/django_ty"
        manifest = json.loads((package / "ty-plugin.json").read_text())
        self.assertEqual(
            self.response({"kind": "manifest"}), {"kind": "manifest", **manifest}
        )
        self.assertIsNone(self.namespace["_MANIFEST"])

    @staticmethod
    def model(name, fields=(), base="django.db.models.Model"):
        return {
            "qualified-name": name,
            "bases": [{"expression": base, "mode": "annotation"}],
            "fields": list(fields),
        }

    @staticmethod
    def relation(name, value, *, keyword=False, annotation=None):
        argument = {"kind": "keyword" if keyword else "positional", "value": value}
        if keyword:
            argument["name"] = "to"
        if annotation is not None:
            argument["type-expr"] = {"expression": annotation, "mode": "annotation"}
        return {
            "name": name,
            "assigned-value": {
                "kind": "call",
                "callee": {"qualified-name": "django.db.models.ForeignKey"},
                "arguments": [argument],
            },
        }

    def compare_classes(self, request):
        response = self.response(request)
        self.assertEqual(response["kind"], "project-index", response)
        records = []
        for model in request["classes"]:
            with self.subTest(model=model["qualified-name"]):
                call = {
                    "kind": "analyze-class",
                    "context": request["context"],
                    "class": model,
                    "project-index": response["plugin-index"],
                }
                expected = self.response(call)
                call["project-index"] = response["class-indexes"][
                    model["qualified-name"]
                ]
                self.assertEqual(self.response(call), expected)
                records.append((call, expected))
        original = json.dumps(response, sort_keys=True)
        # Changing item order and batch boundaries must preserve the complete
        # individual response, including relation targets and descriptor types.
        for width, ordered in [
            (1, records),
            (7, list(reversed(records))),
            (128, records[::2] + records[1::2]),
        ]:
            for offset in range(0, len(ordered), width):
                chunk = ordered[offset : offset + width]
                actual = self.response(
                    {"kind": "analyze-classes", "requests": [call for call, _ in chunk]}
                )
                self.assertEqual(
                    actual,
                    {
                        "kind": "class-batch",
                        "responses": [expected for _, expected in chunk],
                    },
                )
        self.assertEqual(json.dumps(response, sort_keys=True), original)
        return response

    def test_relation_resolution_settings_ambiguity_and_inheritance(self):
        values = [
            {"kind": "str", "value": "self"},
            {"kind": "str", "value": "accounts.User"},
            {"kind": "str", "value": "AUTH_USER_MODEL"},
            {"kind": "symbol-ref", "qualified-name": "settings.AUTH_USER_MODEL"},
            {
                "kind": "enum-ref",
                "qualified-name": "django.conf.settings.AUTH_USER_MODEL",
            },
            {"kind": "class-ref", "qualified-name": "two.accounts.models.User"},
            {"kind": "str", "value": "missing.Unknown"},
            {"kind": "unknown"},
        ]
        fields = [
            self.relation(f"relation_{i}", value, keyword=i % 2 == 0)
            for i, value in enumerate(values)
        ]
        fields.append(
            self.relation(
                "typed", {"kind": "unknown"}, annotation="two.accounts.models.User"
            )
        )
        request = {
            "kind": "build-project-index",
            "context": {
                "config": {},
                "python-version": "3.13",
                "platform": "linux",
                "root": "/project",
            },
            "classes": [
                self.model("one.accounts.models.User"),
                self.model("two.accounts.models.User"),
                self.model("books.models.Book", fields),
                self.model("books.models.Child", base="books.models.Book"),
                self.model("books.Plain", base="builtins.object"),
            ],
            "settings": [
                {
                    "module": "settings",
                    "values": [
                        {
                            "name": "AUTH_USER_MODEL",
                            "value": {"kind": "str", "value": "accounts.User"},
                        },
                        {
                            "name": "DEFAULT_AUTO_FIELD",
                            "value": {
                                "kind": "str",
                                "value": "django.db.models.BigAutoField",
                            },
                        },
                        {
                            "name": "UNRELATED",
                            "value": {"kind": "str", "value": "unrelated setting"},
                        },
                    ],
                }
            ],
        }
        response = self.compare_classes(request)
        scoped = response["class-indexes"]["books.models.Book"]
        self.assertNotIn("UNRELATED", scoped["settings"])
        self.assertIn("one.accounts.models.User", scoped["class_models"])
        self.assertIn("two.accounts.models.User", scoped["class_models"])

    def test_unqualified_relation_resolves_inside_the_same_models_package(self):
        target = self.model("project.books.models.authors.Author")
        unrelated = self.model("other.models.authors.Author")
        book = self.model(
            "project.books.models.books.Book",
            [
                self.relation("author", {"kind": "str", "value": "Author"}),
            ],
        )
        request = {
            "kind": "build-project-index",
            "context": {"config": {}},
            "classes": [book, target, unrelated],
            "settings": [],
        }
        response = self.compare_classes(request)
        self.assertEqual(response.get("diagnostics", []), [])
        model = response["plugin-index"]["models"][book["qualified-name"]]
        self.assertEqual(model["fields"]["author"], target["qualified-name"])
        scoped = response["class-indexes"][book["qualified-name"]]["class_models"]
        self.assertIn(target["qualified-name"], scoped)
        self.assertNotIn(unrelated["qualified-name"], scoped)

        request["classes"] = [book, unrelated]
        missing = self.response(request)
        self.assertTrue(
            any(
                "Unknown Django relation target" in d["message"]
                for d in missing.get("diagnostics", [])
            )
        )

    def test_class_index_storage_grows_linearly_with_related_models(self):
        sizes = []
        for count in [100, 200, 400]:
            models = [
                self.model(
                    f"app.models.Item{i:04}",
                    []
                    if i == 0
                    else [
                        self.relation(
                            "parent", {"kind": "str", "value": f"Item{i - 1:04}"}
                        )
                    ],
                )
                for i in range(count)
            ]
            response = self.compare_classes(
                {
                    "kind": "build-project-index",
                    "context": {"config": {}},
                    "classes": models,
                    "settings": [],
                }
            )
            scopes = response["class-indexes"]
            self.assertEqual(len(scopes), count)
            self.assertTrue(
                all(len(scope["class_models"]) <= 2 for scope in scopes.values())
            )
            sizes.append(len(json.dumps(scopes)))
        self.assertLess(sizes[1], sizes[0] * 2.1)
        self.assertLess(sizes[2], sizes[1] * 2.1)


if __name__ == "__main__":
    unittest.main()
