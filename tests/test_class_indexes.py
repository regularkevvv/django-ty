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

    def test_explicit_primary_keys_preserve_schema_and_class_aliases(self):
        for field_type, key_name, query_type, instance_type in [
            ("CharField", "slug", "str", "str"),
            ("UUIDField", "key", "uuid.UUID", "uuid.UUID"),
            ("AutoField", "row_id", "int", "int | None"),
        ]:
            with self.subTest(field_type=field_type):
                field = {
                    "name": key_name,
                    "assigned-value": {
                        "kind": "call",
                        "callee": {"qualified-name": "django.db.models." + field_type},
                        "arguments": [
                            {
                                "kind": "keyword",
                                "name": "primary_key",
                                "value": {"kind": "bool", "value": True},
                            }
                        ],
                    },
                }
                name = "app.models.Keyed"
                response = self.response(
                    {
                        "kind": "build-project-index",
                        "context": {"config": {}},
                        "classes": [self.model(name, [field])],
                    }
                )
                request = {"project-index": response["plugin-index"]}
                indexed = self.namespace["model_entry"](request, name)
                self.assertNotIn("id", indexed["fields"])
                self.assertNotIn("id", indexed["field_types"])
                self.assertEqual(indexed["fields"]["pk"], query_type)
                patch = self.namespace["deferred_class_patch"](request, name)
                fields = {field["name"]: field for field in patch["fields"]}
                self.assertNotIn("id", fields)
                self.assertEqual(
                    self.namespace["canonical"](fields["pk"]["instance-get-type"]),
                    instance_type,
                )

    def test_inherited_custom_primary_key_keeps_alias_and_absent_id(self):
        parent = self.model(
            "app.models.Parent",
            [
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
            ],
        )
        child = self.model("app.models.Child", base="app.models.Parent")
        response = self.response(
            {
                "kind": "build-project-index",
                "context": {"config": {}},
                "classes": [parent, child],
            }
        )
        request = {"project-index": response["plugin-index"]}
        indexed = self.namespace["model_entry"](request, "app.models.Child")
        self.assertNotIn("id", indexed["fields"])
        self.assertEqual(indexed["fields"]["pk"], "str")
        patch = self.namespace["deferred_class_patch"](request, "app.models.Child")
        fields = {field["name"]: field for field in patch["fields"]}
        self.assertNotIn("id", fields)
        self.assertEqual(fields["pk"]["instance-get-type"]["expression"], "str")

    def test_unmodeled_explicit_key_preserves_native_constructor(self):
        name = "app.models.Composite"
        key = {
            "name": "pk",
            "assigned-value": {
                "kind": "call",
                "callee": {"qualified-name": "django.db.models.CompositePrimaryKey"},
                "arguments": [],
            },
        }
        response = self.response(
            {
                "kind": "build-project-index",
                "context": {"config": {}},
                "classes": [self.model(name, [key])],
            }
        )
        request = {"project-index": response["plugin-index"]}
        patch = self.namespace["deferred_class_patch"](request, name)
        self.assertEqual(patch.get("fields", []), [])
        self.assertIsNone(
            self.namespace["django_signature"](
                {**request, "callee": {"expression": name, "mode": "annotation"}}
            )
        )

    def test_qualified_model_lookup_preserves_legacy_order_without_repeated_scans(self):
        class CountedModels(set):
            iterations = 0

            def __iter__(self):
                self.iterations += 1
                return super().__iter__()

        names = {
            "app.models.Book",
            "nested.app.models.Book",
            "aaa.app.models.Book",
            "other.models.Book",
            "deep.app.extra.Nested.Book",
        }
        models = CountedModels(names)
        lookup = self.namespace["model_name_lookup"](models)
        queries = [
            "app.Book",
            "app.models.Book",
            "app.Nested.Book",
            "other.Book",
            "missing.Book",
        ]
        expected = []
        for raw in queries:
            if raw in names:
                expected.append(raw)
                continue
            app, suffix = raw.split(".", 1)
            expected.append(
                next(
                    (
                        name
                        for name in sorted(names)
                        if name.endswith("." + suffix)
                        and (name.startswith(app + ".") or "." + app + "." in name)
                    ),
                    raw,
                )
            )
        for _ in range(5):
            actual = [
                self.namespace["resolve_model"](
                    "irrelevant.models", raw, models, lookup
                )
                for raw in queries
            ]
            self.assertEqual(actual, expected)
        self.assertLessEqual(
            models.iterations, 2, "qualified lookups must reuse a single project index"
        )

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

    def scopes(self, response):
        return {
            name: self.namespace["deferred_request"](
                {"project-index": response["plugin-index"]}, name
            )["project-index"]
            for name in response["plugin-index"]["deferred_classes"]
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
                call["project-index"] = self.scopes(response).get(
                    model["qualified-name"], {"class_models": {}}
                )
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

    def compact_fixture(self):
        classes = []
        for number in range(12):
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
            if number:
                fields.append(
                    self.relation(
                        "parent", {"kind": "str", "value": f"Item{number - 1:04}"}
                    )
                )
            classes.append(
                self.model(
                    f"app.models.Item{number:04}",
                    fields,
                    base="django.db.models.base.Model",
                )
            )
        return {
            "kind": "build-project-index",
            "context": {"config": {}},
            "classes": classes,
            "settings": [
                {
                    "module": "settings",
                    "values": [
                        {
                            "name": "DEFAULT_AUTO_FIELD",
                            "value": {
                                "kind": "str",
                                "value": "django.db.models.BigAutoField",
                            },
                        }
                    ],
                }
            ],
        }

    def compare_fused_and_general(self, request, expected_fast):
        general = self.namespace["plain_model_index"]
        observed = []

        def capture(*args):
            response = general(*args)
            observed.append(response is not None)
            return response

        self.namespace["plain_model_index"] = capture
        try:
            actual = self.response(request)
            self.namespace["plain_model_index"] = lambda *args: None
            expected = self.response(request)
        finally:
            self.namespace["plain_model_index"] = general
        self.assertEqual(actual["kind"], "project-index", actual)
        self.assertEqual(actual, expected)
        self.assertEqual(any(observed), expected_fast)
        return actual

    def test_fused_index_preserves_global_relations_and_diagnostics(self):
        self.compare_fused_and_general(self.compact_fixture(), True)
        request = self.compact_fixture()
        for number, cls in enumerate(request["classes"]):
            field = self.relation(
                "shared",
                {"kind": "str", "value": "app.Item0000"},
                keyword=number % 2 == 0,
            )
            field["source"] = {
                "file-path": "models.py",
                "start": {"line": number + 1, "column": 1},
            }
            call = field["assigned-value"]
            call["callee"]["qualified-name"] = [
                "django.db.models.ForeignKey",
                "django.db.models.OneToOneField",
                "django.db.models.ManyToManyField",
            ][number % 3]
            call["arguments"].extend(
                [
                    {
                        "kind": "keyword",
                        "name": "related_name",
                        "value": {"kind": "str", "value": "shared"},
                    },
                    {
                        "kind": "keyword",
                        "name": "related_query_name",
                        "value": {"kind": "str", "value": "query"},
                    },
                    {
                        "kind": "keyword",
                        "name": "null",
                        "value": {"kind": "bool", "value": True},
                    },
                ]
            )
            cls["fields"].append(field)
        request["classes"][-1]["fields"].append(
            self.relation("missing", {"kind": "str", "value": "app.Absent"})
        )
        response = self.compare_fused_and_general(request, True)
        codes = [item["message"] for item in response["diagnostics"]]
        self.assertTrue(
            any("Unknown Django relation target" in message for message in codes)
        )
        self.assertTrue(
            any("Conflicting Django reverse relation" in message for message in codes)
        )

    def test_fused_index_defers_custom_model_behavior_to_general_path(self):
        for change in [
            "primary",
            "auto",
            "methods",
            "decorators",
            "meta",
            "manager",
            "inheritance",
            "signal",
        ]:
            with self.subTest(change=change):
                request = self.compact_fixture()
                cls = request["classes"][-1]
                if change == "primary":
                    cls["fields"][0]["assigned-value"]["arguments"].append(
                        {
                            "kind": "keyword",
                            "name": "primary_key",
                            "value": {"kind": "bool", "value": True},
                        }
                    )
                elif change == "auto":
                    cls["fields"][0]["assigned-value"]["callee"]["qualified-name"] = (
                        "django.db.models.AutoField"
                    )
                elif change == "methods":
                    cls["methods"] = [{"name": "save"}]
                elif change == "decorators":
                    cls["decorators"] = [{"qualified-name": "app.decorate"}]
                elif change == "meta":
                    cls["nested-classes"] = [
                        {
                            "name": "Meta",
                            "qualified-name": cls["qualified-name"] + ".Meta",
                        }
                    ]
                elif change == "manager":
                    cls["fields"][0]["name"] = "objects"
                elif change == "inheritance":
                    cls["bases"][0]["expression"] = request["classes"][0][
                        "qualified-name"
                    ]
                else:
                    request["functions"] = [
                        {
                            "name": "receiver",
                            "decorators": [
                                {
                                    "kind": "call",
                                    "callee": {
                                        "qualified-name": "django.dispatch.receiver"
                                    },
                                    "arguments": [],
                                }
                            ],
                        }
                    ]
                self.compare_fused_and_general(request, False)

    def compact_and_legacy(self):
        request = self.compact_fixture()
        compact = self.response(request)
        request["context"]["config"]["compact-model-index"] = False
        legacy = self.response(request)
        return request, compact, legacy

    def test_compact_flat_index_preserves_hydrated_schemas_and_hook_contracts(self):
        request, compact, legacy = self.compact_and_legacy()
        self.assertEqual(compact["plugin-index"].get("index_format"), 1)
        self.assertLess(len(json.dumps(compact)), len(json.dumps(legacy)))
        for cls in request["classes"]:
            name = cls["qualified-name"]
            for helper in ["model_entry", "deferred_request"]:
                self.assertEqual(
                    self.namespace[helper](
                        {"project-index": compact["plugin-index"]}, name
                    ),
                    self.namespace[helper](
                        {"project-index": legacy["plugin-index"]}, name
                    ),
                )
            calls = [
                {"kind": "analyze-class", "class": cls},
                {
                    "kind": "adjust-call-signature",
                    "callee": {"expression": name, "mode": "annotation"},
                    "arguments": [],
                },
                {
                    "kind": "adjust-call-state",
                    "callee": {"expression": name, "mode": "annotation"},
                    "arguments": [],
                },
            ]
            for member in ["name", "parent", "parent_id", "id", "pk", "_meta"]:
                calls.append(
                    {
                        "kind": "resolve-instance-member",
                        "owner": {"expression": name, "mode": "annotation"},
                        "member-name": member,
                    }
                )
            for method in ["get", "filter", "values", "values_list"]:
                calls.append(
                    {
                        "kind": "adjust-call-return",
                        "callee": {
                            "expression": "django.db.models.manager.Manager." + method,
                            "mode": "annotation",
                        },
                        "receiver": {
                            "type-expr": {
                                "expression": "django.db.models.manager.Manager["
                                + name
                                + "]",
                                "mode": "annotation",
                            },
                            "nominal-class": "django.db.models.manager.Manager",
                            "generic-arguments": [
                                {"expression": name, "mode": "annotation"}
                            ],
                        },
                        "arguments": [
                            {
                                "kind": "keyword",
                                "name": "id",
                                "value": {"kind": "int", "value": 1},
                            }
                        ]
                        if method in ["get", "filter"]
                        else [
                            {
                                "kind": "positional",
                                "value": {"kind": "str", "value": "name"},
                            }
                        ],
                    }
                )
            for call in calls:
                call["context"] = {
                    "config": {},
                    "python-version": "3.13",
                    "platform": "linux",
                    "module": "check",
                }
                call["project-index"] = legacy["plugin-index"]
                expected = self.response(call)
                self.assertNotEqual(expected["kind"], "error", expected)
                call["project-index"] = compact["plugin-index"]
                self.assertEqual(self.response(call), expected, (name, call["kind"]))

    def test_native_scalar_members_skip_hydration_and_keep_descriptor_precedence(self):
        request = self.compact_fixture()
        response = self.response(request)
        index = response["plugin-index"]
        name = request["classes"][-1]["qualified-name"]
        original = self.namespace["analyze_django_class"]

        def unexpected(*args, **kwargs):
            raise AssertionError("native scalar members must not build a class patch")

        self.namespace["analyze_django_class"] = unexpected
        try:
            self.assertIsNone(
                self.namespace["django_native_member"](
                    {
                        "owner": {"expression": name},
                        "member-name": "name",
                        "project-index": index,
                    }
                )
            )
        finally:
            self.namespace["analyze_django_class"] = original
        for member in ["id", "pk", "parent_id"]:
            self.assertIsNotNone(
                self.namespace["django_native_member"](
                    {
                        "owner": {"expression": name},
                        "member-name": member,
                        "project-index": index,
                    }
                ),
                member,
            )
        index["reverse_members"].setdefault(name, {})["name"] = name
        self.assertIsNotNone(
            self.namespace["django_native_member"](
                {
                    "owner": {"expression": name},
                    "member-name": "name",
                    "project-index": index,
                }
            )
        )
        relation = self.relation("parent", {"kind": "str", "value": "self"})
        scalar = {
            "name": "parent_id",
            "assigned-value": {
                "kind": "call",
                "callee": {"qualified-name": "django.db.models.CharField"},
                "arguments": [],
            },
        }
        for fields, replaced in [
            ([relation, scalar], True),
            ([scalar, relation], False),
        ]:
            result = self.response(
                {
                    "kind": "build-project-index",
                    "context": {"config": {}},
                    "classes": [self.model(name, fields)],
                }
            )
            patch = self.namespace["django_native_member"](
                {
                    "owner": {"expression": name},
                    "member-name": "parent_id",
                    "project-index": result["plugin-index"],
                }
            )
            self.assertEqual(patch is not None, replaced)

    def test_state_does_not_expand_unused_field_schemas(self):
        request = self.compact_fixture()
        index = self.response(request)["plugin-index"]
        name = request["classes"][-1]["qualified-name"]
        call = {
            "kind": "adjust-call-state",
            "context": {"config": {}},
            "callee": {"expression": name, "mode": "annotation"},
            "arguments": [],
            "project-index": index,
        }
        expected = self.response(call)
        self.assertEqual(expected["kind"], "call-state-patch")
        original = self.namespace["local_index"]

        def unexpected(*args, **kwargs):
            raise AssertionError("state must not expand a field schema")

        self.namespace["local_index"] = unexpected
        try:
            self.assertEqual(self.response(call), expected)
        finally:
            self.namespace["local_index"] = original

    def test_compact_index_lookup_copies_remain_isolated(self):
        request, response, _ = self.compact_and_legacy()
        name = request["classes"][-1]["qualified-name"]
        indexed = {"project-index": response["plugin-index"]}
        before = json.dumps(response, sort_keys=True)
        first = self.namespace["model_entry"](indexed, name)
        first["fields"]["name"] = "corrupted"
        self.assertEqual(
            self.namespace["model_entry"](indexed, name)["fields"]["name"], "str"
        )
        deferred = self.namespace["deferred_request"](indexed, name)
        deferred["class"]["fields"][0]["assigned-value"]["arguments"].append(
            {
                "kind": "keyword",
                "name": "null",
                "value": {"kind": "bool", "value": True},
            }
        )
        self.assertEqual(json.dumps(response, sort_keys=True), before)

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
        scoped = self.scopes(response)["books.models.Book"]
        self.assertNotIn("UNRELATED", scoped["settings"])
        self.assertIn("one.accounts.models.User", scoped["class_models"])
        self.assertIn("two.accounts.models.User", scoped["class_models"])

    def test_managers_keep_qualified_models_and_custom_queryset_methods(self):
        queryset = self.model(
            "left.Rows",
            base="django.db.models.query.QuerySet[left.Custom, left.Custom]",
        )
        queryset["methods"] = [
            {
                "name": "active",
                "is-public": True,
                "parameters": [{"name": "self", "kind": "positional-or-keyword"}],
                "return-type": {"expression": "Self", "mode": "annotation"},
            }
        ]
        custom = self.model(
            "left.Custom",
            fields=[
                {
                    "name": "objects",
                    "assigned-value": {
                        "kind": "call",
                        "callee": {"qualified-name": "left.Rows.as_manager"},
                        "receiver": {"symbol": {"qualified-name": "left.Rows"}},
                        "arguments": [],
                    },
                }
            ],
        )
        classes = [
            self.model("left.Record"),
            self.model("right.Record"),
            custom,
            queryset,
        ]
        request = {
            "kind": "build-project-index",
            "context": {
                "config": {},
                "python-version": "3.13",
                "platform": "linux",
                "root": "/project",
            },
            "classes": classes,
            "settings": [],
        }
        index = self.compare_classes(request)
        for model in classes[:3]:
            name = model["qualified-name"]
            response = self.response(
                {
                    "kind": "analyze-class",
                    "context": request["context"],
                    "class": model,
                    "project-index": self.scopes(index)[name],
                }
            )
            members = {
                m["name"]: m["access"]["type-expr"]
                for m in response.get("class-members", [])
            }
            if name != "left.Custom":
                self.assertEqual(members, {})
                continue
            expected = (
                "django_ty.virtual.left.Custom.Manager"
                if name == "left.Custom"
                else f"django.db.models.manager.Manager[{name}]"
            )
            for member in ["objects", "_default_manager"]:
                self.assertEqual(members[member]["expression"], expected)
        definitions = {v["name"]: v for v in index["virtual-types"]}
        custom_manager = definitions["django_ty.virtual.left.Custom.Manager"]
        self.assertEqual(
            custom_manager["shape"]["members"][0]["access"]["signature"]["return-type"][
                "expression"
            ],
            "left.Rows",
        )

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
        model = self.namespace["model_entry"](
            {"project-index": response["plugin-index"]}, book["qualified-name"]
        )
        self.assertEqual(model["fields"]["author"], target["qualified-name"])
        scoped = self.scopes(response)[book["qualified-name"]]["class_models"]
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

    def test_field_argument_locations_do_not_change_the_semantic_index(self):
        field = self.relation(
            "parent",
            {"kind": "class-ref", "qualified-name": "app.models.Parent"},
            annotation="type[app.models.Parent]",
        )
        args = field["assigned-value"]["arguments"]
        args.append(
            {
                "kind": "keyword",
                "name": "null",
                "value": {"kind": "bool", "value": True},
            }
        )
        location = {
            "module": "app.models",
            "file-path": "app/models.py",
            "start": {"line": 5, "column": 12},
            "end": {"line": 5, "column": 20},
        }
        field["source"] = location
        for argument in args:
            argument["source"] = location
        request = {
            "kind": "build-project-index",
            "context": {"config": {}},
            "classes": [
                self.model("app.models.Parent"),
                self.model("app.models.Child", [field]),
            ],
            "settings": [],
        }
        original = json.dumps(request, sort_keys=True)
        without_locations = json.loads(original)
        for cls in without_locations["classes"]:
            for field in cls.get("fields", []):
                for argument in field["assigned-value"]["arguments"]:
                    argument.pop("source", None)
        with_index = self.response(request)
        self.assertEqual(with_index, self.response(without_locations))
        deferred = self.namespace["deferred_request"](
            {"project-index": with_index["plugin-index"]}, "app.models.Child"
        )
        retained = deferred["class"]["fields"][0]["assigned-value"]["arguments"]
        self.assertEqual(retained[0]["value"], args[0]["value"])
        self.assertEqual(retained[0]["type-expr"], args[0]["type-expr"])
        self.assertEqual(retained[1]["value"], args[1]["value"])
        self.assertEqual(json.dumps(request, sort_keys=True), original)

    def test_metadata_distinguishes_implicit_ids_and_pk_aliases(self):
        index = self.namespace["local_index"]
        implicit = self.model("app.models.Implicit")
        settings = {"DEFAULT_AUTO_FIELD": "django.db.models.BigAutoField"}
        result = index(implicit, settings, [implicit["qualified-name"]], {})
        self.assertEqual(result["field_types"], {"id": "django.db.models.BigAutoField"})
        self.assertEqual(result["fields"]["pk"], "int")
        custom = self.model(
            "app.models.Custom",
            [
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
            ],
        )
        result = index(custom, settings, [custom["qualified-name"]], {})
        self.assertEqual(set(result["field_types"]), {"slug"})
        custom["fields"].append(
            {
                "name": "id",
                "assigned-value": {
                    "kind": "call",
                    "callee": {"qualified-name": "django.db.models.IntegerField"},
                    "arguments": [],
                },
            }
        )
        result = index(custom, settings, [custom["qualified-name"]], {})
        self.assertEqual(set(result["field_types"]), {"slug", "id"})

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
            scopes = self.scopes(response)
            self.assertEqual(len(scopes), count)
            self.assertTrue(
                all(len(scope["class_models"]) <= 2 for scope in scopes.values())
            )
            sizes.append(len(json.dumps(scopes)))
        self.assertLess(sizes[1], sizes[0] * 2.1)
        self.assertLess(sizes[2], sizes[1] * 2.1)

    def test_lazy_model_schema_preserves_fields_and_does_not_mutate_the_host_index(
        self,
    ):
        parent = self.model("app.models.parents.Parent")
        child = self.model(
            "app.models.children.Child",
            [self.relation("parent", {"kind": "str", "value": "Parent"})],
        )
        response = self.response(
            {
                "kind": "build-project-index",
                "context": {"config": {}},
                "classes": [child, parent],
                "settings": [],
            }
        )
        index = response["plugin-index"]
        before = json.dumps(index, sort_keys=True)
        self.assertTrue(
            self.namespace["model_traits"](
                {"project-index": index}, child["qualified-name"]
            )["lazy_fields"]
        )
        self.assertNotIn(
            "parent", index["models"][child["qualified-name"]].get("fields", {})
        )
        resolved = self.namespace["model_entry"](
            {"project-index": index}, child["qualified-name"]
        )
        self.assertEqual(resolved["fields"]["parent"], parent["qualified-name"])
        self.assertEqual(resolved["fields"]["parent_id"], "int")
        self.assertEqual(json.dumps(index, sort_keys=True), before)
        resolved["fields"]["parent"] = "wrong"
        self.assertEqual(
            self.namespace["model_entry"](
                {"project-index": index}, child["qualified-name"]
            )["fields"]["parent"],
            parent["qualified-name"],
        )

    def query_request(self, model, native, arguments=()):
        return {
            "callee": {
                "expression": "django.db.models.query._BaseQuerySet.get",
                "mode": "expression",
            },
            "receiver": {
                "type-expr": {
                    "expression": "django.db.models.manager.BaseManager[one.Book]",
                    "mode": "annotation",
                },
                "nominal-class": "django.db.models.manager.BaseManager",
                "generic-arguments": [model],
            },
            "arguments": list(arguments),
            "default-return-type": native,
            "project-index": {"models": {"one.Book": {"fields": {"name": "str"}}}},
        }

    def test_matching_native_model_return_keeps_its_original_type(self):
        model = {
            "expression": "one.Book",
            "mode": "annotation",
            "snapshot": {"kind": "nominal", "qualified-name": "one.Book"},
        }
        native = {**model, "expression": "Book"}
        response = self.namespace["query_return"](
            self.query_request(model, native), "get"
        )
        self.assertIsNone(response)

    def test_speculative_get_requires_a_plain_default_manager(self):
        for case in [
            "simple",
            "custom-manager",
            "methods",
            "meta",
            "decorator",
            "inherited",
        ]:
            with self.subTest(case=case):
                cls = self.model("one.Book")
                if case == "custom-manager":
                    cls["fields"] = [
                        {
                            "name": "objects",
                            "assigned-value": {
                                "kind": "call",
                                "callee": {"qualified-name": "one.Manager"},
                                "arguments": [],
                            },
                        }
                    ]
                if case == "methods":
                    cls["methods"] = [
                        {
                            "name": "save",
                            "qualified-name": "one.Book.save",
                            "parameters": [],
                        }
                    ]
                if case == "meta":
                    cls["nested-classes"] = [
                        {
                            "name": "Meta",
                            "qualified-name": "one.Book.Meta",
                            "fields": [],
                        }
                    ]
                if case == "decorator":
                    cls["decorators"] = [
                        {"expression": "typing.final", "mode": "annotation"}
                    ]
                if case == "inherited":
                    cls["bases"] = [{"expression": "one.Parent", "mode": "annotation"}]
                index = self.response(
                    {
                        "kind": "build-project-index",
                        "context": {"config": {}},
                        "classes": [self.model("one.Parent"), cls],
                        "settings": [],
                    }
                )["plugin-index"]
                model = {"expression": "one.Book", "mode": "annotation"}
                request = self.query_request(model, model)
                request["project-index"] = index
                request["context"] = {"speculative": True}
                response = self.namespace["query_return"](request, "get")
                if case == "simple":
                    self.assertEqual(response["return-type"], model)
                else:
                    self.assertIsNone(response)

    def test_native_return_reuse_preserves_namespace_and_generic_arguments(self):
        model = {
            "expression": "one.Book",
            "mode": "annotation",
            "snapshot": {"kind": "nominal", "qualified-name": "one.Book"},
        }
        for snapshot in [
            {"kind": "nominal", "qualified-name": "two.Book"},
            {
                "kind": "nominal",
                "qualified-name": "one.Book",
                "arguments": [{"kind": "nominal", "qualified-name": "builtins.str"}],
            },
            {"kind": "unknown"},
        ]:
            with self.subTest(snapshot=snapshot):
                native = {**model, "snapshot": snapshot}
                response = self.namespace["query_return"](
                    self.query_request(model, native), "get"
                )
                self.assertEqual(response["return-type"], model)

    def test_native_return_reuse_retains_query_validation_diagnostics(self):
        model = {
            "expression": "one.Book",
            "mode": "annotation",
            "snapshot": {"kind": "nominal", "qualified-name": "one.Book"},
        }
        native = {**model, "expression": "Book"}
        argument = {
            "kind": "keyword",
            "name": "missing",
            "value": {"kind": "str", "value": "bad"},
        }
        response = self.namespace["query_return"](
            self.query_request(model, native, [argument]), "get"
        )
        self.assertEqual(response["return-type"], native)
        self.assertEqual(len(response["diagnostics"]), 1)
        self.assertIn("unknown-lookup", response["diagnostics"][0]["id"])

    def test_simple_lookup_validation_reuses_its_request_schema(self):
        name = "app.models.Item"
        field = {
            "name": "title",
            "assigned-value": {
                "kind": "call",
                "callee": {"qualified-name": "django.db.models.CharField"},
                "arguments": [],
            },
        }
        index = self.response(
            {
                "kind": "build-project-index",
                "context": {"config": {}},
                "classes": [self.model(name, [field])],
                "settings": [],
            }
        )["plugin-index"]
        args = [
            {"kind": "keyword", "name": "id", "value": {"kind": "int", "value": 1}},
            {
                "kind": "keyword",
                "name": "title",
                "value": {"kind": "str", "value": "ok"},
            },
        ]
        request = {"context": {"config": {}}, "project-index": index, "arguments": args}
        original = self.namespace["model_fields"]
        reads = []

        def tracked(request, model):
            reads.append(model)
            return original(request, model)

        self.namespace["model_fields"] = tracked
        try:
            self.assertEqual(
                self.namespace["validate_arguments"](request, name, "get"), []
            )
            self.assertEqual(reads, [name])
            args[0]["value"] = {"kind": "str", "value": "wrong"}
            diagnostics = self.namespace["validate_arguments"](request, name, "get")
            self.assertEqual(len(diagnostics), 1)
            self.assertIn("invalid-lookup", diagnostics[0]["id"])
        finally:
            self.namespace["model_fields"] = original

    def test_inline_class_hooks_do_not_mutate_or_alias_their_index(self):
        model = self.model(
            "app.models.Item",
            [self.relation("parent", {"kind": "str", "value": "self"})],
        )
        response = self.response(
            {
                "kind": "build-project-index",
                "context": {"config": {}},
                "classes": [model],
                "settings": [],
            }
        )
        hook = self.namespace["analyze_django_class"]
        for index in [
            response["plugin-index"],
            self.scopes(response)[model["qualified-name"]],
        ]:
            with self.subTest(scoped="class_models" in index):
                request = {
                    "kind": "analyze-class",
                    "context": {"config": {}},
                    "class": model,
                    "project-index": index,
                }
                original = json.dumps(request, sort_keys=True)
                expected = json.loads(json.dumps(hook(request)))
                changed = hook(request)
                changed["fields"][0]["instance-get-type"]["expression"] = "bytes"
                changed.get("class-members", []).clear()
                self.assertEqual(hook(request), expected)
                self.assertEqual(json.dumps(request, sort_keys=True), original)


if __name__ == "__main__":
    unittest.main()
