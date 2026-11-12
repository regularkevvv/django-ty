"""Compact indexes preserve native reverse members and independent model traits."""

from __future__ import annotations

import importlib.util
import json
import unittest
from pathlib import Path


class PlainIndexCompactionTest(unittest.TestCase):
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
        cls.code = compile(source, "plain_index_compaction_test.py", "exec")

    def namespace(self):
        namespace = {}
        exec(self.code, namespace)
        return namespace

    @staticmethod
    def model(name, relation=None, accessor=None, query=None):
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
        if relation:
            arguments = [
                {"kind": "positional", "value": {"kind": "str", "value": "First"}}
            ]
            for key, value in [
                ("related_name", accessor),
                ("related_query_name", query),
            ]:
                if value is not None:
                    arguments.append(
                        {
                            "kind": "keyword",
                            "name": key,
                            "value": {"kind": "str", "value": value},
                        }
                    )
            fields.append(
                {
                    "name": "parent",
                    "assigned-value": {
                        "kind": "call",
                        "callee": {"qualified-name": "django.db.models." + relation},
                        "arguments": arguments,
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

    def index(
        self,
        namespace,
        relation="ForeignKey",
        accessor=None,
        query=None,
        backwards=False,
    ):
        classes = [
            self.model("app.First"),
            self.model("app.Second", relation, accessor, query),
        ]
        if backwards:
            classes.reverse()
        # Exercise the same JSON boundary as the companion, rather than exposing
        # construction-time aliases as mutable shared state to a reader.
        return json.loads(
            json.dumps(
                namespace["build_django_index"](
                    {"context": {"config": {}}, "classes": classes}
                )["plugin-index"]
            )
        )

    def test_reverse_shadowing_is_independent_of_declaration_order(self):
        for backwards in [False, True]:
            for accessor in [None, "name", "+"]:
                with self.subTest(backwards=backwards, accessor=accessor):
                    index = self.index(
                        self.namespace(), accessor=accessor, backwards=backwards
                    )
                    members = index["native_member_abstentions"]
                    self.assertEqual(
                        members.get("app.First", {}),
                        {} if accessor == "name" else {"name": True},
                    )
                    self.assertEqual(members["app.Second"], {"name": True})

    def test_compact_reverse_members_match_legacy_member_responses(self):
        for relation in ["ForeignKey", "OneToOneField"]:
            namespace = self.namespace()
            index = self.index(namespace, relation=relation, accessor="children")
            legacy = json.loads(json.dumps(index))
            expected_type = (
                namespace["manager_type"]("app.Second", None)
                if relation == "ForeignKey"
                else "app.Second"
            )
            legacy["reverse_members"]["app.First"]["children"] = expected_type
            request = {
                "kind": "get-instance-member",
                "context": {"config": {}},
                "owner": {"expression": "app.First", "mode": "annotation"},
                "member-name": "children",
                "project-index": index,
            }
            actual = namespace["django_native_member"](request)
            expected = namespace["django_native_member"](
                {**request, "project-index": legacy}
            )
            self.assertIsNotNone(actual)
            self.assertEqual(actual, expected)

    def test_source_class_references_rebuild_same_deferred_requests(self):
        baseline = self.namespace()
        candidate = self.namespace()
        request = {
            "context": {"config": {}},
            "classes": [
                self.model("app.First"),
                self.model("app.Second", "ForeignKey"),
            ],
        }
        legacy = baseline["build_django_index"](request)["plugin-index"]
        key = "__ty_companion_source_classes__"
        snapshot = {
            "available": True,
            "classes": {item["qualified-name"]: item for item in request["classes"]},
        }
        current = {key: snapshot}

        def lookup(operation, path_json):
            value = current
            found = True
            for part in json.loads(path_json):
                if not isinstance(value, dict) or part not in value:
                    value = None
                    found = False
                    break
                value = value[part]
            return json.dumps(
                list(value)
                if operation == "keys" and isinstance(value, dict)
                else []
                if operation == "keys"
                else [found, value]
            )

        candidate["_ty_project_index_lookup"] = lookup
        compact = candidate["build_django_index"](request)["plugin-index"]
        self.assertEqual(compact[key], {"use": True})
        for record in compact["models"].values():
            self.assertTrue(record["h"])
            self.assertEqual(record["f"], [])
        current = {**compact, key: snapshot}
        before = json.dumps(current, sort_keys=True)
        for name in legacy["models"]:
            expected = baseline["deferred_request"]({"project-index": legacy}, name)
            actual = candidate["deferred_request"]({"project-index": None}, name)
            self.assertEqual(actual, expected)
        self.assertEqual(json.dumps(current, sort_keys=True), before)

    def test_query_overrides_do_not_leak_between_model_traits(self):
        index = self.index(self.namespace(), query="search_alias")
        self.assertEqual(
            index["models"]["app.First"]["j"], {"search_alias": "app.Second"}
        )
        self.assertNotIn("j", index["models"]["app.Second"])
