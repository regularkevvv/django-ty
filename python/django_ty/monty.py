"""Django semantic hooks for Monty's restricted Python interpreter.

The host supplies ty.plugin_sdk and all project data. No Django code is imported
or executed. This file is also executable with the SDK prelude under CPython.
"""

import json
import typing

if typing.TYPE_CHECKING:
    from collections.abc import Collection
    from typing import Literal, overload

    from django_ty._monty_sdk import (
        call_return_patch,
        call_signature_patch,
        call_state_patch,
        callable_member,
        callable_signature,
        class_patch,
        class_target,
        contribution,
        diagnostic,
        field_contribution,
        field_patch,
        import_binding,
        instance_target,
        keyword_only,
        location,
        member,
        member_contribution,
        member_descriptor,
        mutation_diagnostics,
        on_call_return,
        on_call_signature,
        on_call_state,
        on_class_transform,
        on_mutation,
        on_project_index,
        optional,
        positional_or_keyword,
        project_index,
        set_manifest,
        snapshot_expression,
        snapshot_nominal,
        snapshot_tuple,
        type_annotation,
        type_expr,
        virtual_class,
        virtual_field,
        virtual_named_tuple,
        virtual_type,
        virtual_typed_dict,
    )
    from django_ty._monty_types import (
        Argument,
        CallRequest,
        CallReturnResponse,
        CallSignatureResponse,
        CallStateResponse,
        CallSummary,
        ClassRequest,
        ClassResponse,
        ClassSummary,
        Contribution,
        Diagnostic,
        FieldData,
        FieldPatch,
        FieldSummary,
        ImportBinding,
        IndexedRequest,
        JsonValue,
        LiteralValue,
        LocalModelIndex,
        MemberPatch,
        ModelIndex,
        MutationRequest,
        MutationResponse,
        ProjectIndexRequest,
        ProjectIndexResponse,
        RelationKind,
        SymbolRef,
        SymbolSource,
        TypeExpr,
        TypeSnapshot,
        VirtualType,
    )

    @overload
    def typed_literal(arg: "Argument | None", kind: Literal["str"]) -> str | None: ...

    @overload
    def typed_literal(arg: "Argument | None", kind: Literal["bool"]) -> bool | None: ...

    @overload
    def typed_literal(arg: "Argument | None", kind: Literal["int"]) -> int | None: ...


MODEL_BASES = [
    "django.db.models.base.Model",
    "django.db.models.Model",
    "django.db.models.base.ModelBase.__call__",
]
MANAGER_BASE = "django.db.models.manager.Manager"
BASE_MANAGER_BASE = "django.db.models.manager.BaseManager"
QUERYSET_BASE = "django.db.models.query.QuerySet"
OPTIONS_BASE = "django.db.models.options.Options"
DB_DEFAULT = "django.db.models.expressions.DatabaseDefault"
LOOKUP_METHODS = [
    "filter",
    "exclude",
    "get",
    "get_or_create",
    "update_or_create",
    "aget",
    "aget_or_create",
    "aupdate_or_create",
]
FIELD_NAME_METHODS = ["order_by", "distinct", "only", "defer", "select_related"]
QUERYSET_RETURNING_METHODS = [
    "all",
    "filter",
    "exclude",
    "complex_filter",
    "order_by",
    "distinct",
    "none",
    "only",
    "defer",
    "select_related",
    "prefetch_related",
    "select_for_update",
    "reverse",
    "using",
    "union",
    "intersection",
    "difference",
    "alias",
]
SCALAR_FIELDS = {
    "AutoField": "int",
    "BigAutoField": "int",
    "SmallAutoField": "int",
    "IntegerField": "int",
    "BigIntegerField": "int",
    "SmallIntegerField": "int",
    "PositiveIntegerField": "int",
    "PositiveSmallIntegerField": "int",
    "PositiveBigIntegerField": "int",
    "BooleanField": "bool",
    "FloatField": "float",
    "DecimalField": "decimal.Decimal",
    "CharField": "str",
    "TextField": "str",
    "SlugField": "str",
    "EmailField": "str",
    "URLField": "str",
    "FilePathField": "str",
    "GenericIPAddressField": "str",
    "UUIDField": "uuid.UUID",
    "BinaryField": "bytes",
    "DateField": "datetime.date",
    "DateTimeField": "datetime.datetime",
    "TimeField": "datetime.time",
    "DurationField": "datetime.timedelta",
    "JSONField": "object",
    "ArrayField": "object",
    "HStoreField": "object",
    "FileField": "django.db.models.fields.files.FieldFile",
    "ImageField": "django.db.models.fields.files.FieldFile",
}


def ann(text: str) -> "TypeExpr":
    imports = []
    for qualified, alias in [
        ("datetime.datetime", "__django_ty_datetime"),
        ("datetime.timedelta", "__django_ty_timedelta"),
        ("datetime.date", "__django_ty_date"),
        ("datetime.time", "__django_ty_time"),
        ("decimal.Decimal", "__django_ty_decimal"),
        ("uuid.UUID", "__django_ty_uuid"),
    ]:
        if qualified in text:
            module, name = qualified.rsplit(".", 1)
            text = text.replace(qualified, alias)
            imports.append(import_binding(module, name, alias))
    return type_annotation(text, imports=imports)


def canonical(ty: "TypeExpr") -> "str":
    text = ty["expression"]
    for binding in ty.get("imports", []):
        if binding.get("alias"):
            text = text.replace(
                binding["alias"], binding["module"] + "." + binding["name"]
            )
    return text


def snap(ty: "TypeExpr") -> "TypeSnapshot":
    return ty.get("snapshot") or snapshot_expression(
        ty["expression"], mode=ty.get("mode", "expression"), imports=ty.get("imports")
    )


def merge_imports(types: "list[TypeExpr]") -> "list[ImportBinding]":
    bindings = {}
    for ty in types:
        for binding in ty.get("imports", []):
            key = (binding["module"], binding["name"], binding.get("alias") or "")
            bindings[key] = binding
    return [bindings[key] for key in sorted(bindings)]


def qs_type(model: "TypeExpr", row: "TypeExpr") -> "TypeExpr":
    result = ann(
        "django.db.models.query.QuerySet["
        + model["expression"]
        + ", "
        + row["expression"]
        + "]"
    )
    result["imports"] = merge_imports([result, model, row])
    result["snapshot"] = snapshot_nominal(QUERYSET_BASE, [snap(model), snap(row)])
    return result


def tuple_type(elements: "list[TypeExpr]") -> "TypeExpr":
    result = ann(
        "tuple[" + ", ".join([element["expression"] for element in elements]) + "]"
    )
    result["imports"] = merge_imports(elements)
    result["snapshot"] = snapshot_tuple(prefix=[snap(element) for element in elements])
    return result


def module_of(name: str) -> "str":
    return name.rsplit(".", 1)[0] if "." in name else ""


def short(name: str) -> "str":
    return name.rsplit(".", 1)[-1]


def virtual_name(model: str, suffix: str) -> "str":
    return "django_ty.virtual." + model + "." + suffix


def replace_member(name: str, ty: "TypeExpr") -> "MemberPatch":
    return member(name, ty, mode="replace-existing")


def named(args: "list[Argument]", name: str) -> "Argument | None":
    for arg in args:
        if arg.get("name") == name:
            return arg
    return None


def typed_literal(arg: "Argument | None", kind: str) -> "bool | int | str | None":
    value = (arg or {}).get("value")
    if value is None:
        return None
    if kind == "str" and value["kind"] == "str":
        return value["value"]
    if kind == "bool" and value["kind"] == "bool":
        return value["value"]
    if kind == "int" and value["kind"] == "int":
        return value["value"]
    return None


def call_of(field: "FieldSummary") -> "CallSummary | None":
    assigned = field.get("assigned-value") or {}
    return assigned if assigned.get("kind") == "call" else None


def call_name(call: "CallSummary") -> "str":
    return (call.get("callee") or {}).get("qualified-name", "")


def manager_call(call: "CallSummary") -> "bool":
    name = short(call_name(call))
    return name == "as_manager" or name == "BaseManager" or name.endswith("Manager")


def auto_field(call: "CallSummary") -> "bool":
    return short(call_name(call)) in ["AutoField", "BigAutoField", "SmallAutoField"]


def relation_kind(call: "CallSummary") -> "RelationKind | None":
    kinds: "dict[str, RelationKind]" = {
        "ForeignKey": "foreign-key",
        "ForeignObject": "foreign-key",
        "OneToOneField": "one-to-one",
        "ManyToManyField": "many-to-many",
    }
    return kinds.get(short(call_name(call)))


def resolve_model(module: str, raw: str, models: "Collection[str]") -> "str":
    if "." not in raw:
        return module + "." + raw
    if raw in models:
        return raw
    app, name = raw.split(".", 1)
    for candidate in sorted(models):
        if candidate.endswith("." + name) and (
            candidate.startswith(app + ".") or "." + app + "." in candidate
        ):
            return candidate
    return raw


def relation_target(
    model: str, call: "CallSummary", settings: dict[str, str], models: "Collection[str]"
) -> "str | None":
    args = call.get("arguments", [])
    target = named(args, "to")
    if target is None:
        positional = [arg for arg in args if arg.get("kind") == "positional"]
        target = positional[0] if positional else None
    if target is None:
        return None
    value = target.get("value")
    kind = value["kind"] if value is not None else None
    symbol = (
        value["qualified-name"]
        if value is not None
        and (
            value["kind"] == "class-ref"
            or value["kind"] == "symbol-ref"
            or value["kind"] == "enum-ref"
        )
        else ""
    )
    raw = None
    if kind in ["enum-ref", "symbol-ref"] and symbol in settings:
        raw = settings[symbol]
    elif kind in ["class-ref", "symbol-ref", "enum-ref"]:
        raw = (target.get("type-expr") or {}).get("expression") or symbol
    elif value is not None and value["kind"] == "str":
        raw = value["value"]
        if raw == "self":
            raw = model
        elif raw in settings:
            raw = settings[raw]
    else:
        raw = (target.get("type-expr") or {}).get("expression")
    return resolve_model(module_of(model), raw, models) if raw is not None else None


def choice_target(model: str, call: "CallSummary") -> "str | None":
    value = (named(call.get("arguments", []), "choices") or {}).get("value")
    if value is None or (
        value["kind"] != "class-ref"
        and value["kind"] != "enum-ref"
        and value["kind"] != "symbol-ref"
    ):
        return None
    target = value["qualified-name"]
    return target if "." in target else model + "." + target


def field_data(
    model: str,
    field: "FieldSummary",
    settings: dict[str, str],
    models: "Collection[str]",
) -> "FieldData | None":
    call = call_of(field)
    if call is None or manager_call(call):
        return None
    args = call.get("arguments", [])
    nullable = typed_literal(named(args, "null"), "bool") is True
    default = any(
        arg.get("name") == "default"
        and (arg.get("value") or {}).get("kind") != "unknown"
        for arg in args
    )
    relation = relation_kind(call)
    target = relation_target(model, call, settings, models) if relation else None
    target_type = target or "django.db.models.base.Model"
    if relation == "many-to-many":
        get_text = MANAGER_BASE + "[" + target_type + "]"
    elif relation:
        get_text = target_type + (" | None" if nullable else "")
    else:
        get_text = SCALAR_FIELDS.get(short(call_name(call)))
        if get_text is None:
            return None
        if auto_field(call) and named(args, "db_default") is not None:
            get_text = "int | " + DB_DEFAULT
        if nullable or auto_field(call):
            get_text += " | None"
    set_text = (
        target_type + " | int" + (" | None" if nullable else "")
        if relation
        else get_text
    )
    return {
        "name": field["name"],
        "get": ann(get_text),
        "set": ann(set_text),
        "nullable": nullable,
        "default": default,
        "relation": relation,
        "target": target,
    }


def builtin_id(name: str, ty: "TypeExpr") -> "FieldPatch":
    return field_patch(
        name,
        ty,
        mode="replace-existing",
        instance_set_type=ty,
        constructor_parameter=keyword_only(name, ty, required=False),
        has_default=True,
    )


def field_patches(data: "FieldData") -> "list[FieldPatch]":
    name = data["name"]
    if data["relation"] == "many-to-many":
        return []
    patches = [
        field_patch(
            name,
            data["get"],
            mode="replace-existing",
            descriptor=member_descriptor(data["get"], instance_set_type=data["set"]),
            instance_set_type=data["set"],
            constructor_parameter=keyword_only(name, data["set"], required=False),
            has_default=data["default"] or data["nullable"],
        )
    ]
    if data["relation"] in ["foreign-key", "one-to-one"]:
        ty = ann("int | None" if data["nullable"] else "int")
        patches.append(
            field_patch(
                name + "_id",
                ann("int | None"),
                mode="replace-existing",
                instance_set_type=ty,
                constructor_parameter=keyword_only(name + "_id", ty, required=False),
                has_default=True,
            )
        )
    return patches


def field_class(model: str, call: "CallSummary") -> "str":
    name = call_name(call)
    if name.startswith("models."):
        name = "django.db." + name
    elif "." not in name:
        name = module_of(model) + "." + name
    return name + "[typing.Any, typing.Any]"


def default_members(model: str) -> "list[MemberPatch]":
    ty = ann(virtual_name(model, "Manager"))
    return [replace_member("objects", ty), replace_member("_default_manager", ty)]


def default_fields(default: str | None) -> "list[FieldPatch]":
    return [
        builtin_id("id", ann("int | None")),
        builtin_id(
            "pk",
            ann(
                "int | None | " + DB_DEFAULT if default == DB_DEFAULT else "int | None"
            ),
        ),
    ]


def diag(
    identifier: str,
    message: str,
    source: "SymbolSource | None" = None,
    metadata: "dict[str, JsonValue] | None" = None,
) -> "Diagnostic":
    source = source or {}
    loc = None
    if source.get("file-path") and source.get("start") and source.get("end"):
        loc = location(source["file-path"], source["start"], source["end"])
    return diagnostic(
        "django-ty." + identifier, message, location=loc, metadata=metadata
    )


def unknown_lookup_diag(model: str, lookup: str, arg: "Argument") -> "Diagnostic":
    return diag(
        "unknown-lookup",
        "Unknown Django lookup `" + lookup + "` for model `" + model + "`",
        arg.get("source"),
    )


def invalid_lookup_diag(
    model: str, field: str, lookup: str, expected: str, arg: "Argument"
) -> "Diagnostic":
    return diag(
        "invalid-lookup-value",
        "Invalid Django lookup value for `"
        + lookup
        + "` on `"
        + model
        + "."
        + field
        + "`; expected `"
        + expected
        + "`",
        arg.get("source"),
    )


def resolve_class(owner: str, text: str, names: "Collection[str]") -> "str | None":
    text = text.split("[", 1)[0]
    if text in names:
        return text
    candidate = module_of(owner) + "." + text
    return candidate if "." not in text and candidate in names else None


def derived_names(
    classes: "list[ClassSummary]", bases: list[str], generic: bool = False
) -> "set[str]":
    names = {cls["qualified-name"] for cls in classes}
    selected = set()
    while True:
        before = len(selected)
        for cls in classes:
            for base in cls.get("bases", []):
                text = base["expression"]
                if (
                    text.split("[", 1)[0] if generic else text
                ) in bases or resolve_class(
                    cls["qualified-name"], text, names
                ) in selected:
                    selected.add(cls["qualified-name"])
        if len(selected) == before:
            return selected


def meta_flag(cls: "ClassSummary", flag: str) -> "bool":
    return any(
        constant.get("name") == flag
        and (constant.get("value") or {}) == {"kind": "bool", "value": True}
        for nested in cls.get("nested-classes", [])
        if nested.get("name") == "Meta"
        for constant in nested.get("class-constants", [])
    )


def signal_receiver(
    request: "ProjectIndexRequest", model: str, decorators: "list[CallSummary]"
) -> "bool":
    for dec in decorators:
        if dec.get("kind") != "call" or short(call_name(dec)) != "receiver":
            continue
        sender = named(dec.get("arguments", []), "sender")
        if sender is None:
            return True
        ty = (sender.get("type-expr") or {}).get("expression")
        if ty == model:
            return True
        if any(cls["qualified-name"] == ty for cls in request.get("classes", [])):
            continue
        value = sender.get("value")
        if value is not None and (
            value["kind"] == "class-ref" or value["kind"] == "symbol-ref"
        ):
            symbol = value["qualified-name"]
            if symbol == model or ("." not in symbol and symbol == short(model)):
                return True
        elif value is not None and value["kind"] == "str":
            if short(value["value"]) == short(model):
                return True
        else:
            return True
    return False


def local_index(
    cls: "ClassSummary", settings: dict[str, str], models: "Collection[str]"
) -> "LocalModelIndex":
    name = cls["qualified-name"]
    result: "LocalModelIndex" = {
        "fields": {"id": "int", "pk": "int"},
        "field_types": {
            "id": "django.db.models.fields.AutoField[typing.Any, typing.Any]",
            "pk": "django.db.models.fields.AutoField[typing.Any, typing.Any]",
        },
        "auto_primary_key": None,
        "auto_primary_key_default": None,
        "custom_primary_key": False,
        "multi_table": False,
        "custom_loading": False,
        "custom_save": False,
    }
    primary = None
    for field in cls.get("fields", []):
        call = call_of(field)
        if call is None:
            continue
        data = field_data(name, field, settings, models)
        if data is not None:
            result["fields"][field["name"]] = (
                "int" if auto_field(call) else canonical(data["get"])
            )
            if data["relation"] in ["foreign-key", "one-to-one"]:
                result["fields"][field["name"] + "_id"] = (
                    "int | None" if data["nullable"] else "int"
                )
            result["field_types"][field["name"]] = field_class(name, call)
        if primary is None and (
            auto_field(call)
            or call_name(call).endswith(".CompositePrimaryKey")
            or typed_literal(named(call.get("arguments", []), "primary_key"), "bool")
            is True
        ):
            primary = (field, call)
    if primary is not None:
        primary_field, call = primary
        result["auto_primary_key"] = primary_field["name"] if auto_field(call) else None
        result["custom_primary_key"] = not auto_field(call)
        default = named(call.get("arguments", []), "default")
        kind = ((default or {}).get("value") or {}).get("kind")
        if kind == "int":
            default_type = "int"
        elif (
            default is None
            and named(call.get("arguments", []), "db_default") is not None
        ):
            default_type = DB_DEFAULT
        elif default is None or kind == "none":
            default_type = "None"
        else:
            default_type = "int | None"
        result["auto_primary_key_default"] = default_type
    methods = [method["name"] for method in cls.get("methods", [])]
    result["custom_loading"] = any(
        method in methods for method in ["__new__", "__init__", "from_db"]
    )
    result["custom_save"] = "save" in methods
    return result


def inherited_indexes(
    classes: "list[ClassSummary]", settings: dict[str, str], names: set[str]
) -> "dict[str, LocalModelIndex]":
    selected = {
        cls["qualified-name"]: cls for cls in classes if cls["qualified-name"] in names
    }
    local = {name: local_index(cls, settings, names) for name, cls in selected.items()}
    resolved = local
    for iteration in range(len(names)):
        following: "dict[str, LocalModelIndex]" = {}
        for name in sorted(selected):
            cls = selected[name]
            result: "LocalModelIndex" = {
                "fields": {},
                "field_types": {},
                "auto_primary_key": None,
                "auto_primary_key_default": None,
                "custom_primary_key": False,
                "multi_table": False,
                "custom_loading": False,
                "custom_save": False,
            }
            for base in cls.get("bases", []):
                base_name = resolve_class(name, base["expression"], names)
                if base_name not in resolved:
                    continue
                indexed = resolved[base_name]
                result["auto_primary_key"] = indexed["auto_primary_key"]
                result["auto_primary_key_default"] = indexed["auto_primary_key_default"]
                result["custom_primary_key"] = (
                    result["custom_primary_key"] or indexed["custom_primary_key"]
                )
                result["multi_table"] = (
                    result["multi_table"]
                    or indexed["multi_table"]
                    or (
                        not meta_flag(cls, "proxy")
                        and not meta_flag(selected[base_name], "abstract")
                    )
                )
                for flag in ["custom_loading", "custom_save"]:
                    result[flag] = result[flag] or indexed[flag]
                for field_map in ["fields", "field_types"]:
                    result[field_map].update(indexed[field_map])
            own = local[name]
            if own["auto_primary_key"] is not None or own["custom_primary_key"]:
                result["auto_primary_key"] = own["auto_primary_key"]
                result["auto_primary_key_default"] = own["auto_primary_key_default"]
                result["custom_primary_key"] = own["custom_primary_key"]
            for flag in ["custom_loading", "custom_save"]:
                result[flag] = result[flag] or own[flag]
            for field_map in ["fields", "field_types"]:
                result[field_map].update(own[field_map])
                result[field_map] = {
                    key: result[field_map][key] for key in sorted(result[field_map])
                }
            following[name] = result
        if following == resolved:
            break
        resolved = following
    return resolved


def queryset_manager_members(cls: "ClassSummary") -> "list[MemberPatch]":
    result = []
    for method in cls.get("methods", []):
        if not method.get("is-public", False):
            continue
        ret = method.get("return-type") or ann("typing.Any")
        if (ret.get("snapshot") or {}).get("kind") == "self-type" or ret[
            "expression"
        ] == "Self":
            ret = ann(cls["qualified-name"])
        result.append(
            callable_member(
                method["name"],
                callable_signature(method.get("parameters", [])[1:], ret),
                ann("typing.Callable[..., " + ret["expression"] + "]"),
                read_only=True,
            )
        )
    return result


def model_virtual_types(
    model: str, fields: dict[str, str], queryset: "ClassSummary | None"
) -> "list[VirtualType]":
    entries = [virtual_field(name, ann(fields[name])) for name in sorted(fields)]
    return [
        virtual_type(
            virtual_name(model, "Manager"),
            virtual_class(
                bases=[type_expr(MANAGER_BASE + "[" + model + "]")],
                members=queryset_manager_members(queryset) if queryset else [],
            ),
        ),
        virtual_type(
            virtual_name(model, "QuerySet"),
            virtual_class(
                bases=[type_expr(QUERYSET_BASE + "[" + model + ", " + model + "]")]
            ),
        ),
        virtual_type(virtual_name(model, "ValuesRow"), virtual_typed_dict(entries)),
        virtual_type(
            virtual_name(model, "ValuesListRow"), virtual_named_tuple(entries)
        ),
    ]


def symbol_name(
    module: str, symbol: "SymbolRef | LiteralValue | None", names: "Collection[str]"
) -> "str | None":
    name = (symbol or {}).get("qualified-name")
    if name in names:
        return name
    local = module + "." + (name or "")
    return local if local in names else None


def manager_queryset(
    cls: "ClassSummary", querysets: "dict[str, ClassSummary]", generated: dict[str, str]
) -> "str | None":
    for field in cls.get("fields", []):
        call = call_of(field)
        if call is None:
            continue
        if short(call_name(call)) == "as_manager":
            receiver = call.get("receiver") or {}
            name = symbol_name(
                module_of(cls["qualified-name"]), receiver.get("symbol"), querysets
            )
            if name is not None:
                return name
        name = call_name(call)
        if name not in generated and "." not in name:
            name = module_of(cls["qualified-name"]) + "." + name
        if name in generated:
            return generated[name]
    return None


@on_project_index
def build_django_index(request: "ProjectIndexRequest") -> "ProjectIndexResponse":
    settings: dict[str, str] = {}
    contributions: "list[Contribution]" = []
    for module in request.get("settings", []):
        for setting in module.get("values", []):
            value = setting.get("value")
            if value is None:
                continue
            if value["kind"] == "str":
                for key in [
                    setting["name"],
                    module["module"] + "." + setting["name"],
                    "django.conf.settings." + setting["name"],
                    "settings." + setting["name"],
                ]:
                    settings[key] = value["value"]
            ty = {
                "bool": "bool",
                "int": "int",
                "str": "str",
                "none": "None",
                "tuple": "tuple[object, ...]",
                "list": "list[object]",
                "dict": "dict[object, object]",
            }.get(value.get("kind"))
            if ty is not None:
                contributions.append(
                    contribution(
                        setting.get("source") or {},
                        instance_target("django.conf.LazySettings"),
                        member_contribution(replace_member(setting["name"], ann(ty))),
                        "django.conf.LazySettings." + setting["name"],
                    )
                )
    classes = request.get("classes", [])
    decorated = list(request.get("functions", []))
    for cls in classes:
        decorated.extend(cls.get("methods", []))
    decorators = [dec for item in decorated for dec in item.get("decorators", [])]
    names = derived_names(classes, MODEL_BASES)
    indexes = inherited_indexes(classes, settings, names)
    queryset_names = derived_names(classes, [QUERYSET_BASE], generic=True)
    querysets = {
        cls["qualified-name"]: cls
        for cls in classes
        if cls["qualified-name"] in queryset_names
    }
    generated = {}
    for assignment in request.get("assignments", []):
        call = call_of(assignment)
        if call is None or short(call_name(call)) != "from_queryset":
            continue
        positional = [
            arg for arg in call.get("arguments", []) if arg.get("kind") == "positional"
        ]
        if positional and (positional[0].get("value") or {}).get("kind") in [
            "class-ref",
            "symbol-ref",
        ]:
            name = symbol_name(
                module_of(assignment["qualified-name"]),
                positional[0]["value"],
                queryset_names,
            )
            if name:
                generated[assignment["qualified-name"]] = name
    auth = settings.get("AUTH_USER_MODEL")
    if auth is not None:
        resolved = resolve_model("", auth, names)
        auth = (
            resolved
            if resolved in names
            else auth.split(".", 1)[0] + ".models." + auth.split(".", 1)[1]
            if "." in auth
            else None
        )
    if auth is not None:
        contributions.append(
            contribution(
                {},
                instance_target("django.http.request.HttpRequest"),
                member_contribution(
                    replace_member(
                        "user",
                        ann(auth + " | django.contrib.auth.models.AnonymousUser"),
                    )
                ),
                "django.http.request.HttpRequest.user",
            )
        )
    models: "dict[str, ModelIndex]" = {}
    virtuals: "list[VirtualType]" = []
    diagnostics = []
    reverse_sources: "dict[str, SymbolSource]" = {}
    query_fields: dict[str, dict[str, str]] = {}
    for cls in classes:
        name = cls["qualified-name"]
        if name not in names:
            continue
        indexed = indexes[name]
        fields = indexed["fields"]
        queryset = manager_queryset(cls, querysets, generated)
        virtuals.extend(model_virtual_types(name, fields, querysets.get(queryset)))
        if not any(base["expression"] in MODEL_BASES for base in cls.get("bases", [])):
            for patch in default_members(name):
                contributions.append(
                    contribution(
                        cls.get("source") or {},
                        class_target(name),
                        member_contribution(patch),
                        name + "." + patch["name"],
                    )
                )
            for field in sorted(fields):
                ty = ann(fields[field])
                patch = field_patch(
                    field,
                    ty,
                    mode="replace-existing",
                    instance_set_type=ty,
                    has_default=True,
                )
                contributions.append(
                    contribution(
                        cls.get("source") or {},
                        instance_target(name),
                        field_contribution(patch),
                        name + "." + field,
                    )
                )
        models[name] = {
            "fields": fields,
            "field_types": indexed["field_types"],
            "manager_queryset": queryset,
            "auto_primary_key_default": indexed["auto_primary_key_default"],
            "auto_primary_key": None
            if indexed["custom_primary_key"] or indexed["multi_table"]
            else indexed["auto_primary_key"] or "id",
            "custom_loading": indexed["custom_loading"],
            "custom_save": indexed["custom_save"],
            "signal_receivers": signal_receiver(request, name, decorators),
        }
        for field in cls.get("fields", []):
            call = call_of(field)
            if call is None:
                continue
            choice = choice_target(name, call)
            if choice and any(
                nested["qualified-name"] == choice
                for nested in cls.get("nested-classes", [])
            ):
                contributions.append(
                    contribution(
                        field.get("source") or {},
                        instance_target(choice),
                        member_contribution(replace_member("label", ann("str"))),
                        choice + ".label",
                    )
                )
            kind = relation_kind(call)
            if kind is None:
                continue
            target = relation_target(name, call, settings, names)
            if target is None:
                continue
            if target not in names:
                diagnostics.append(
                    diag(
                        "unknown-relation-target",
                        "Unknown Django relation target `"
                        + target
                        + "` for field `"
                        + name
                        + "."
                        + field["name"]
                        + "`",
                        field.get("source"),
                    )
                )
                continue
            query_name = typed_literal(
                named(call.get("arguments", []), "related_query_name"), "str"
            )
            if query_name is not None and query_name != "+":
                query_fields.setdefault(target, {})[query_name] = name
            reverse = typed_literal(
                named(call.get("arguments", []), "related_name"), "str"
            )
            if reverse == "+":
                continue
            if reverse is None:
                reverse = short(name).lower() + ("" if kind == "one-to-one" else "_set")
            key = target + "." + reverse
            source = field.get("source") or {}
            if key in reverse_sources:
                first = reverse_sources[key]
                metadata = (
                    {"first-file-path": first["file-path"]}
                    if first.get("file-path")
                    else {}
                )
                diagnostics.append(
                    diag(
                        "reverse-relation-conflict",
                        "Conflicting Django reverse relation `" + key + "`",
                        source,
                        metadata,
                    )
                )
                reverse_sources[key] = source
                continue
            reverse_sources[key] = source
            ty = ann(name if kind == "one-to-one" else virtual_name(name, "Manager"))
            patch = field_patch(
                reverse,
                ty,
                mode="replace-existing",
                descriptor=member_descriptor(ty),
                has_default=True,
            )
            contributions.append(
                contribution(
                    source, instance_target(target), field_contribution(patch), key
                )
            )
    for name in sorted(query_fields):
        models[name]["query_fields"] = query_fields[name]
    deps = [
        dep
        for module in request.get("settings", [])
        for dep in module.get("dependencies", [])
    ]
    return project_index(
        {"models": models, "settings": settings, "auth_user_model": auth},
        contributions=contributions,
        virtual_types=virtuals,
        dependencies=deps,
        diagnostics=diagnostics,
    )


@on_class_transform
def analyze_django_class(request: "ClassRequest") -> "ClassResponse | None":
    cls = request["class"]
    name = cls["qualified-name"]
    indexed = (request.get("project-index") or {}).get("models") or {}
    if name not in indexed and not any(
        base["expression"] in MODEL_BASES for base in cls.get("bases", [])
    ):
        return None
    settings = (request.get("project-index") or {}).get("settings") or {}
    fields = default_fields((indexed.get(name) or {}).get("auto_primary_key_default"))
    members = default_members(name)
    instance = []
    for field in cls.get("fields", []):
        call = call_of(field)
        if call is None:
            continue
        if manager_call(call):
            callee_name = call_name(call)
            if isinstance(
                (indexed.get(name) or {}).get("manager_queryset"), str
            ) or callee_name.startswith("django.db.models."):
                ty = virtual_name(name, "Manager")
            else:
                ty = (
                    callee_name
                    if "." in callee_name
                    else module_of(name) + "." + callee_name
                )
            members.append(replace_member(field["name"], ann(ty)))
            continue
        if choice_target(name, call):
            instance.append(
                callable_member(
                    "get_" + field["name"] + "_display",
                    callable_signature(return_type=ann("str")),
                    ann("typing.Callable[..., str]"),
                    mode="replace-existing",
                    read_only=True,
                )
            )
        data = field_data(name, field, settings, indexed)
        if data is not None:
            fields.extend(field_patches(data))
    return class_patch(fields=fields, class_members=members, instance_members=instance)


def model_entry(request: "IndexedRequest", name: str) -> "ModelIndex | None":
    return ((request.get("project-index") or {}).get("models") or {}).get(name)


def model_fields(request: "IndexedRequest", name: str) -> "dict[str, str] | None":
    model = model_entry(request, name)
    return model.get("fields") if model is not None else None


def related_model(request: "IndexedRequest", field_type: str) -> "str | None":
    for candidate in field_type.split("|"):
        candidate = candidate.strip()
        if (
            candidate not in ["None", "int"]
            and model_fields(request, candidate) is not None
        ):
            return candidate
    return None


TERMINAL_LOOKUPS = [
    "exact",
    "iexact",
    "contains",
    "icontains",
    "startswith",
    "istartswith",
    "endswith",
    "iendswith",
    "regex",
    "iregex",
    "gt",
    "gte",
    "lt",
    "lte",
    "in",
    "range",
    "isnull",
    "year",
    "month",
    "day",
    "date",
]


def lookup_type(
    request: "CallRequest", model: str, lookup: str
) -> "tuple[str, str, str | None] | None":
    parts = lookup.split("__")
    if not parts or any(not part for part in parts):
        return None
    terminal = parts[-1] if parts[-1] in TERMINAL_LOOKUPS else None
    path = parts[:-1] if terminal else parts
    if not path:
        return None
    for name in path[:-1]:
        entry = model_entry(request, model) or {}
        ty = (entry.get("fields") or {}).get(name) or (
            entry.get("query_fields") or {}
        ).get(name)
        if ty is None:
            return None
        related = related_model(request, ty)
        if related is None:
            return None
        model = related
    ty = (model_fields(request, model) or {}).get(path[-1])
    return (path[-1], ty, terminal) if ty is not None else None


def field_allows(expected: str, actual: str) -> "bool":
    return actual in [part.strip() for part in expected.split("|")]


def literal_matches(expected: str, value: "LiteralValue") -> "bool":
    kind = value.get("kind", "unknown")
    if kind in ["unknown", "class-ref", "enum-ref", "symbol-ref"]:
        return True
    if kind == "bool":
        return field_allows(expected, "bool") or field_allows(expected, "int")
    actual = {"none": "None", "int": "int", "str": "str"}.get(kind)
    return actual is not None and field_allows(expected, actual)


def top_parts(text: str, delimiter: str) -> "list[str]":
    parts = []
    start = 0
    depth = 0
    quote = None
    escaped = False
    for index, char in enumerate(text):
        if escaped:
            escaped = False
            continue
        if quote is not None:
            if char == "\\":
                escaped = True
            elif char == quote:
                quote = None
            continue
        if char in ["'", '"']:
            quote = char
        elif char in "([{":
            depth += 1
        elif char in ")]}":
            depth -= 1
        elif char == delimiter and depth == 0:
            parts.append(text[start:index].strip())
            start = index + 1
    parts.append(text[start:].strip())
    return parts


def unparen(text: str) -> "str":
    while text.startswith("(") and text.endswith(")"):
        depth = 0
        enclosed = True
        for index, char in enumerate(text):
            if char == "(":
                depth += 1
            elif char == ")":
                depth -= 1
            if depth == 0 and index + 1 != len(text):
                enclosed = False
                break
        if not enclosed:
            break
        text = text[1:-1].strip()
    return text


def generic_args(text: str, origin: str) -> "list[str] | None":
    text = text.strip()
    prefix = origin + "["
    if not text.startswith(prefix) or not text.endswith("]"):
        return None
    # The Rust parser treats double-quoted text specially; keep the same grammar.
    text = text[len(prefix) : -1]
    parts = []
    start = 0
    depth = 0
    quoted = False
    for index, char in enumerate(text):
        if char == '"':
            quoted = not quoted
        elif char in "[({" and not quoted:
            depth += 1
        elif char in "])}" and not quoted:
            depth = max(0, depth - 1)
        elif char == "," and depth == 0 and not quoted:
            parts.append(text[start:index].strip())
            start = index + 1
    parts.append(text[start:].strip())
    return parts


def type_may_match(expected: str, actual: str) -> "bool":
    actual = unparen(actual.strip())
    parts = top_parts(actual, "|")
    if len(parts) > 1:
        return any(type_may_match(expected, part) for part in parts)
    if actual.startswith("builtins."):
        actual = actual[len("builtins.") :]
    if actual in ["Any", "typing.Any", "Unknown", "object"]:
        return True
    if actual.startswith("Literal[") and actual.endswith("]"):
        literal = actual[len("Literal[") : -1]
        if literal.startswith('"') or literal.startswith("'"):
            actual = "str"
        elif literal in ["True", "False"]:
            actual = "bool"
        else:
            try:
                number = int(literal)
                if -(2**63) <= number < 2**63:
                    actual = "int"
            except ValueError:
                pass
    expected_parts = [part.strip() for part in expected.split("|")]
    if any(part.strip() in expected_parts for part in actual.split("|")):
        return True
    scalar = any(
        part
        in [
            "bool",
            "bytes",
            "float",
            "int",
            "str",
            "None",
            "decimal.Decimal",
            "uuid.UUID",
        ]
        or part.startswith("datetime.")
        for part in expected_parts
    )
    return not scalar


def argument_matches(expected: str, argument: "Argument") -> "bool":
    value = argument.get("value") or {"kind": "unknown"}
    if value.get("kind") != "unknown":
        return literal_matches(expected, value)
    actual = argument.get("type-expr")
    if actual is None:
        return True
    snapshot = actual.get("snapshot") or {}
    text = (
        snapshot["qualified-name"]
        if snapshot.get("kind") == "nominal"
        else canonical(actual)
    )
    return type_may_match(expected, text)


def string_items_match(expected: str, text: str) -> "bool":
    return all(
        field_allows(expected, "str")
        or (field_allows(expected, "int") and (char in "0123456789" or ord(char) > 127))
        for char in text
    )


def lookup_matches(expected: str, terminal: str | None, arg: "Argument") -> "bool":
    lookup = terminal or "exact"
    value: "LiteralValue" = arg.get("value") or {"kind": "unknown"}
    kind = value["kind"]
    if lookup == "isnull":
        return kind in ["bool", "unknown"]
    if lookup in ["in", "range"]:
        if value["kind"] == "list" or value["kind"] == "tuple":
            items = value["items"]
            return (lookup == "in" or len(items) == 2) and all(
                literal_matches(expected, item) for item in items
            )
        if value["kind"] == "str":
            text = value["value"]
            return (lookup == "in" or len(text) == 2) and string_items_match(
                expected, text
            )
        return kind == "unknown"
    if lookup in [
        "contains",
        "icontains",
        "startswith",
        "istartswith",
        "endswith",
        "iendswith",
        "regex",
        "iregex",
    ]:
        return field_allows(expected, "str") and kind in ["str", "unknown"]
    if lookup in ["year", "month", "day"]:
        return argument_matches("int", arg)
    if lookup == "date":
        return argument_matches("datetime.date | datetime.datetime | str", arg)
    if lookup in ["exact", "iexact"] and kind == "none":
        return True
    return argument_matches(expected, arg)


def validate_lookup(
    request: "CallRequest", model: str, arg: "Argument"
) -> "Diagnostic | None":
    lookup = arg.get("name")
    if lookup is None:
        return None
    found = lookup_type(request, model, lookup)
    if found is None:
        return unknown_lookup_diag(model, lookup, arg)
    field, expected, terminal = found
    return (
        None
        if lookup_matches(expected, terminal, arg)
        else invalid_lookup_diag(model, field, lookup, expected, arg)
    )


def validate_field_value(
    request: "CallRequest", model: str, arg: "Argument"
) -> "Diagnostic | None":
    name = arg.get("name")
    fields = model_fields(request, model)
    if name is None or fields is None:
        return None
    expected = fields.get(name)
    if expected is None:
        return unknown_lookup_diag(model, name, arg)
    return (
        None
        if argument_matches(expected, arg)
        else invalid_lookup_diag(model, name, name, expected, arg)
    )


def callable_result(text: str) -> "str":
    text = unparen(text.strip())
    parts = top_parts(text, "|")
    if len(parts) > 1:
        return " | ".join([callable_result(part) for part in parts])
    for origin in ["typing.Callable", "collections.abc.Callable", "Callable"]:
        args = generic_args(text, origin)
        if args is not None:
            return args[1] if len(args) > 1 else "Unknown"
    if text.startswith("type[") and text.endswith("]"):
        return text[5:-1]
    depth = 0
    for index, char in enumerate(text):
        if char in "([{":
            depth += 1
        elif char in ")]}":
            depth -= 1
        elif char == "-" and depth == 0 and text[index:].startswith("->"):
            return text[index + 2 :].strip()
    return "Unknown" if "Callable[" in text else text


def validate_defaults(
    request: "CallRequest", model: str, arg: "Argument"
) -> "list[Diagnostic]":
    value = arg.get("value")
    if value is None or value["kind"] != "dict":
        return []
    value_type = None
    argument_type = arg.get("type-expr")
    if argument_type:
        text = canonical(argument_type)
        for origin in [
            "dict",
            "builtins.dict",
            "typing.Mapping",
            "collections.abc.Mapping",
            "Mapping",
        ]:
            args = generic_args(text, origin)
            if args is not None and len(args) > 1:
                value_type = args[1]
                break
    resolves = value_type is not None and any(
        marker in value_type for marker in ["->", "Callable[", "type["]
    )
    result = []
    for entry in value.get("entries", []):
        key = entry["key"]
        if key["kind"] != "str":
            continue
        nested_value: "LiteralValue" = entry["value"]
        if resolves and nested_value.get("kind") in [
            "symbol-ref",
            "enum-ref",
            "class-ref",
        ]:
            nested_value = {"kind": "unknown"}
        nested: "Argument" = {
            "kind": "keyword",
            "name": key["value"],
            "value": nested_value,
            "type-expr": ann(callable_result(value_type))
            if value_type is not None
            else None,
            "source": arg.get("source"),
        }
        diagnostic_value = validate_field_value(request, model, nested)
        if diagnostic_value is not None:
            result.append(diagnostic_value)
    return result


def creation_defaults(method: str, arg: "Argument") -> "bool":
    name = arg.get("name")
    return (
        name == "defaults"
        and method
        in ["get_or_create", "update_or_create", "aget_or_create", "aupdate_or_create"]
    ) or (
        name == "create_defaults"
        and method in ["update_or_create", "aupdate_or_create"]
    )


def validate_field_name(
    request: "CallRequest", model: str, arg: "Argument"
) -> "Diagnostic | None":
    fields = model_fields(request, model)
    value = typed_literal(arg, "str")
    if fields is None or value is None or value in fields:
        return None
    return unknown_lookup_diag(model, value, arg)


def validate_method_field(
    request: "CallRequest", model: str, method: str, arg: "Argument"
) -> "Diagnostic | None":
    value = typed_literal(arg, "str")
    if value is None:
        return None
    value = value[1:] if value.startswith("-") else value
    if method == "order_by":
        if value == "?":
            return None
        generic = (request.get("receiver") or {}).get("generic-arguments", [])
        if len(generic) > 1 and json.dumps(value) + ":" in generic[1]["expression"]:
            return None
    found = lookup_type(request, model, value)
    if found is not None:
        field, expected, terminal = found
        valid = terminal is None
        if method == "order_by":
            valid = terminal is None or terminal in ["year", "month", "day", "date"]
        elif method == "select_related":
            valid = terminal is None and related_model(request, expected) is not None
        if valid:
            return None
    candidate: "Argument" = {**arg}
    candidate["value"] = {"kind": "str", "value": value}
    return validate_field_name(request, model, candidate)


def validate_field_collection(
    request: "CallRequest", model: str, arg: "Argument"
) -> "list[Diagnostic]":
    value = arg.get("value") or {}
    if value.get("kind") not in ["list", "tuple"]:
        return []
    result = []
    for item in value.get("items", []):
        found = validate_field_name(
            request,
            model,
            {"kind": "positional", "value": item, "source": arg.get("source")},
        )
        if found is not None:
            result.append(found)
    return result


def validate_arguments(
    request: "CallRequest", model: str, method: str
) -> "list[Diagnostic]":
    if model_fields(request, model) is None:
        return []
    result = []
    args = request.get("arguments", [])
    if method in LOOKUP_METHODS:
        for arg in args:
            if arg.get("kind") == "keyword" and not creation_defaults(method, arg):
                found = validate_lookup(request, model, arg)
                if found is not None:
                    result.append(found)
        for arg in args:
            if creation_defaults(method, arg):
                result.extend(validate_defaults(request, model, arg))
    elif (
        method in ["create", "acreate", "values", "values_list"]
        or method in FIELD_NAME_METHODS
    ):
        for arg in args:
            found = None
            if method in ["create", "acreate"] and arg.get("kind") == "keyword":
                found = validate_field_value(request, model, arg)
            elif (
                method in ["values", "values_list"] and arg.get("kind") == "positional"
            ):
                found = validate_field_name(request, model, arg)
            elif method in FIELD_NAME_METHODS and arg.get("kind") == "positional":
                found = validate_method_field(request, model, method, arg)
            if found is not None:
                result.append(found)
    elif method == "bulk_update":
        for index, arg in enumerate(args):
            if arg.get("name") == "fields" or (arg.get("name") is None and index == 1):
                result.extend(validate_field_collection(request, model, arg))
    return result


def positional_strings(request: "CallRequest") -> "list[str]":
    strings: list[str] = []
    for arg in request.get("arguments", []):
        value = arg.get("value")
        if arg["kind"] == "positional" and value is not None and value["kind"] == "str":
            strings.append(value["value"])
    return strings


def bool_keyword(request: "CallRequest", name: str) -> "bool | None":
    return typed_literal(
        named(
            [
                arg
                for arg in request.get("arguments", [])
                if arg.get("kind") == "keyword"
            ],
            name,
        ),
        "bool",
    )


def values_row(request: "CallRequest", model: str) -> "TypeExpr | None":
    fields = model_fields(request, model)
    if fields is None:
        return None
    names = positional_strings(request)
    if not names:
        return ann(virtual_name(model, "ValuesRow"))
    return ann(
        "TypedDict({"
        + ", ".join(
            [json.dumps(name) + ": " + fields.get(name, "object") for name in names]
        )
        + "})"
    )


def values_list_row(
    request: "CallRequest", model: str, valid: bool
) -> "TypeExpr | None":
    names = positional_strings(request)
    flat = bool_keyword(request, "flat") is True
    named_row = bool_keyword(request, "named") is True
    if flat and named_row:
        return None
    fields = model_fields(request, model)
    if named_row:
        if fields is None:
            return None
        if not names:
            return ann(virtual_name(model, "ValuesListRow"))
        return ann(
            'NamedTuple("DjangoTyValuesListRow", {'
            + ", ".join(
                [json.dumps(name) + ": " + fields.get(name, "object") for name in names]
            )
            + "})"
        )
    if not names:
        if flat or fields is None:
            return None
        return tuple_type([ann(fields[name]) for name in sorted(fields)])
    if flat:
        return ann((fields or {}).get(names[0], "object"))
    if not valid:
        return ann("tuple[object, ...]")
    return tuple_type([ann((fields or {}).get(name, "object")) for name in names])


def qualified_model(request: "CallRequest", name: str) -> "str":
    models = (request.get("project-index") or {}).get("models") or {}
    if name in models:
        return name
    matches = [candidate for candidate in sorted(models) if short(candidate) == name]
    return matches[0] if len(matches) == 1 else name


def prefetched_row(request: "CallRequest", row: "TypeExpr") -> "TypeExpr | None":
    entries = []
    for arg in request.get("arguments", []):
        ty = arg.get("type-expr")
        if ty is None:
            continue
        parts = generic_args(ty["expression"], "Prefetch")
        if parts is None or len(parts) != 3:
            continue
        queryset = generic_args(parts[1], "QuerySet")
        attr = parts[2].strip()
        if not queryset or not attr.startswith('Literal["') or not attr.endswith('"]'):
            continue
        name = attr[len('Literal["') : -2]
        entries.append(
            json.dumps(name)
            + ": list["
            + qualified_model(request, queryset[-1].strip())
            + "]"
        )
    return (
        ann(
            'Class("DjangoTyPrefetchedRow", {'
            + ", ".join(entries)
            + "}, "
            + row["expression"]
            + ")"
        )
        if entries
        else None
    )


def query_return(request: "CallRequest", method: str) -> "CallReturnResponse | None":
    receiver_value = request.get("receiver") or {}
    arguments = receiver_value.get("generic-arguments", [])
    if not arguments:
        return None
    model = arguments[0]
    is_queryset = (receiver_value.get("nominal-class") or "").endswith("QuerySet")
    row = arguments[1] if is_queryset and len(arguments) > 1 else model
    diagnostics = validate_arguments(request, model["expression"], method)
    if method == "prefetch_related":
        prefetched = prefetched_row(request, row)
        if prefetched is not None:
            return call_return_patch(qs_type(model, prefetched), diagnostics)
    if method in QUERYSET_RETURNING_METHODS:
        ty = receiver_value["type-expr"]
        if (ty.get("snapshot") or {}).get("kind") == "self-type":
            return call_return_patch(ty, diagnostics)
        if (
            is_queryset
            and receiver_value.get("nominal-class") != QUERYSET_BASE
            and "django_ty.virtual." not in ty["expression"]
        ):
            return None
        return call_return_patch(
            ty if is_queryset else qs_type(model, row), diagnostics
        )
    row_or_model = row if is_queryset else model
    if method in ["get", "earliest", "latest", "aget"]:
        result = row_or_model
    elif method in ["create", "acreate"]:
        result = model
    elif method == "bulk_create":
        result = ann("list[" + model["expression"] + "]")
    elif method in [
        "get_or_create",
        "update_or_create",
        "aget_or_create",
        "aupdate_or_create",
    ]:
        result = ann("tuple[" + model["expression"] + ", bool]")
    elif method in ["first", "last", "afirst", "alast"]:
        result = ann(row_or_model["expression"] + " | None")
    elif method in ["count", "bulk_update", "acount"]:
        result = ann("int")
    elif method in ["exists", "aexists"]:
        result = ann("bool")
    elif method == "values":
        result = qs_type(
            model, values_row(request, model["expression"]) or ann("dict[str, object]")
        )
    elif method == "values_list":
        values = values_list_row(request, model["expression"], not diagnostics)
        if values is None:
            return None
        result = qs_type(model, values)
    elif method == "annotate":
        entries = []
        for arg in request.get("arguments", []):
            if arg.get("kind") != "keyword" or arg.get("name") is None:
                continue
            ty = arg.get("type-expr") or ann(
                {"bool": "bool", "int": "int", "str": "str", "none": "None"}.get(
                    (arg.get("value") or {}).get("kind"), "object"
                )
            )
            entries.append(json.dumps(arg["name"]) + ": " + ty["expression"])
        annotated = (
            ann(
                'Class("DjangoTyAnnotatedRow", {'
                + ", ".join(entries)
                + "}, "
                + row["expression"]
                + ")"
            )
            if entries
            else row
        )
        result = qs_type(model, annotated)
    else:
        return None
    if method in [
        "aget",
        "acreate",
        "aget_or_create",
        "aupdate_or_create",
        "afirst",
        "alast",
        "acount",
        "aexists",
    ]:
        coroutine = ann(
            "typing.Coroutine[object, object, " + result["expression"] + "]"
        )
        coroutine["imports"] = coroutine.get("imports", []) + result.get("imports", [])
        result = coroutine
    return call_return_patch(result, diagnostics)


def get_registry_model(request: "CallRequest") -> "CallReturnResponse | None":
    args = request.get("arguments", [])
    positional = [arg for arg in args if arg.get("kind") == "positional"]
    app = named(args, "app_label") or (positional[0] if positional else None)
    app_text = typed_literal(app, "str")
    if app_text is None:
        return None
    model = named(args, "model_name") or (
        positional[1] if len(positional) > 1 else None
    )
    if model is not None:
        text = typed_literal(model, "str")
        if text is None:
            return None
        reference = app_text + "." + text
    else:
        reference = app_text
    if "." not in reference:
        return None
    app_text, model_text = reference.split(".", 1)
    matches = []
    for name in sorted((request.get("project-index") or {}).get("models") or {}):
        if "." not in name:
            continue
        module = module_of(name)
        if module.endswith(".models"):
            module = module[:-7]
        if short(module) == app_text and short(name).lower() == model_text.lower():
            matches.append(name)
    return (
        call_return_patch(ann("type[" + matches[0] + "]"))
        if len(matches) == 1
        else None
    )


@on_call_return
def django_call_return(request: "CallRequest") -> "CallReturnResponse | None":
    callee_text = request["callee"]["expression"]
    if callee_text == "django.http.request.HttpRequest":
        return call_return_patch(ann("django.http.request._MutableHttpRequest"))
    if callee_text == "django.apps.registry.Apps.get_model":
        return get_registry_model(request)
    if callee_text == "django.utils.translation.gettext_lazy":
        return call_return_patch(ann("str"))
    if callee_text == "django.contrib.auth.get_user_model":
        model = (request.get("project-index") or {}).get("auth_user_model")
        return (
            call_return_patch(ann("type[" + model + "]"))
            if isinstance(model, str)
            else None
        )
    receiver_value = request.get("receiver")
    if receiver_value is None:
        return None
    method = short(callee_text)
    if method == "save":
        model = (
            receiver_value.get("nominal-class")
            or receiver_value["type-expr"]["expression"]
        )
        if model_fields(request, model) is None:
            return None
        diagnostics = []
        for arg in request.get("arguments", []):
            if arg.get("name") == "update_fields":
                diagnostics.extend(validate_field_collection(request, model, arg))
        return call_return_patch(
            request.get("default-return-type") or ann("None"), diagnostics
        )
    nominal = receiver_value.get("nominal-class") or ""
    if method == "get_field" and (
        nominal == OPTIONS_BASE or nominal.endswith(".Options")
    ):
        generic = receiver_value.get("generic-arguments", [])
        positional = [
            arg
            for arg in request.get("arguments", [])
            if arg.get("kind") == "positional"
        ]
        if not generic or not positional:
            return None
        name = typed_literal(positional[0], "str")
        model = generic[0]["expression"]
        field_types = (model_entry(request, model) or {}).get("field_types")
        if name is None or field_types is None:
            return None
        if name not in field_types:
            return call_return_patch(
                request.get("default-return-type")
                or ann("django.db.models.fields.Field[typing.Any, typing.Any]"),
                [unknown_lookup_diag(model, name, positional[0])],
            )
        return call_return_patch(ann(field_types[name]))
    if (
        nominal not in [BASE_MANAGER_BASE, MANAGER_BASE, QUERYSET_BASE]
        and not nominal.endswith("Manager")
        and not nominal.endswith("BaseManager")
        and not nominal.endswith("QuerySet")
        and "django_ty.virtual." not in nominal
    ):
        return None
    return query_return(request, method)


@on_call_signature
def django_signature(request: "CallRequest") -> "CallSignatureResponse | None":
    if short(request["callee"]["expression"]) != "from_queryset":
        return None
    ret = (request.get("receiver") or {}).get("type-expr") or ann(
        "type[django.db.models.manager.BaseManager[typing.Any]]"
    )
    return call_signature_patch(
        callable_signature(
            [
                positional_or_keyword(
                    "queryset_class",
                    ann(
                        "type[django.db.models.query.QuerySet[typing.Any, typing.Any]]"
                    ),
                ),
                optional("class_name", ann("str | None")),
            ],
            ret,
        )
    )


@on_mutation
def django_mutation(request: "MutationRequest") -> "MutationResponse | None":
    if request.get("operation") != "item-set":
        return None
    return mutation_diagnostics(
        [
            diag(
                "immutable-querydict-write",
                "Django request query parameters are immutable",
                request.get("source"),
            )
        ]
    )


def definitely_saves(value: "LiteralValue | None") -> "bool":
    if value is None:
        return False
    kind = value["kind"]
    return kind == "none" or (kind in ["list", "tuple"] and bool(value.get("items")))


@on_call_state
def django_state(request: "CallRequest") -> "CallStateResponse | None":
    if ((request.get("context") or {}).get("config") or {}).get("model-state") is False:
        return None
    receiver_value = request.get("receiver")
    if receiver_value is None:
        model = model_entry(request, request["callee"]["expression"])
        key = model.get("auto_primary_key") if model is not None else None
        if (
            model is None
            or not isinstance(key, str)
            or model.get("custom_loading") is True
            or model.get("signal_receivers") is True
        ):
            return None
        uncertain = (
            "int | None | " + DB_DEFAULT
            if model.get("auto_primary_key_default") == DB_DEFAULT
            else "int | None"
        )
        args = request.get("arguments", [])
        argument = named(args, "pk") or named(args, key)
        if any(
            arg.get("kind") in ["positional", "star-args", "star-kwargs"]
            for arg in args
        ):
            value = uncertain
        elif argument is not None:
            kind = (argument.get("value") or {}).get("kind")
            if kind == "none":
                value = "None"
            elif (
                kind == "int"
                or (argument.get("type-expr") or {}).get("expression") == "int"
            ):
                value = "int"
            else:
                value = uncertain
        else:
            value = model.get("auto_primary_key_default") or "None"
        return call_state_patch(
            result_members={key: ann(value), "pk": ann(value)}, fresh_result=True
        )
    method = short(request["callee"]["expression"])
    model_method = method in ["save", "delete"]
    if model_method:
        name = (
            receiver_value.get("nominal-class")
            or receiver_value["type-expr"]["expression"]
        )
    elif method in ["get", "create", "earliest", "latest"]:
        generic = receiver_value.get("generic-arguments", [])
        if not generic or (len(generic) > 1 and generic[1] != generic[0]):
            return None
        name = generic[0]["expression"]
    else:
        return None
    model = model_entry(request, name)
    key = model.get("auto_primary_key") if model is not None else None
    if model is None or not isinstance(key, str):
        return None
    if not model_method and model.get("custom_loading") is True:
        return None
    if method == "create" and model.get("custom_save") is True:
        return None
    if method != "delete" and model.get("signal_receivers") is True:
        return None
    if method == "save" and any(
        arg.get("kind") in ["positional", "star-args", "star-kwargs"]
        or (
            arg.get("name") == "update_fields"
            and not definitely_saves(arg.get("value"))
        )
        for arg in request.get("arguments", [])
    ):
        return None
    ty = ann("None" if method == "delete" else "int")
    members = {key: ty, "pk": ty}
    return (
        call_state_patch(receiver_members=members)
        if model_method
        else call_state_patch(result_members=members, fresh_result=True)
    )


# Packaged manifest
set_manifest(
    json.loads(r"""
{
  "id": "django-ty",
  "name": "Django ty plugin",
  "version": "0.5.0",
  "protocol-version": {
    "major": 0,
    "minor": 7
  },
  "ty-compatibility": {
    "requirement": ">=0.84.4,<0.85.0"
  },
  "runtime": {
    "kind": "monty",
    "artifact": "monty.py"
  },
  "capabilities": {
    "stub-overlays": true,
    "class-transform": true,
    "class-member": false,
    "instance-member": false,
    "call-signature": true,
    "call-return": true,
    "call-state": true,
    "additional-dependencies": false,
    "project-index": true,
    "cross-symbol-contributions": true,
    "settings-data": true,
    "virtual-types": true,
    "mutation-validation": true
  },
  "claims": {
    "classes": [
      {
        "kind": "subclass-of",
        "base-qualified-name": "django.db.models.base.Model"
      },
      {
        "kind": "subclass-of",
        "base-qualified-name": "django.db.models.Model"
      },
      {
        "kind": "subclass-of",
        "base-qualified-name": "django.db.models.base.ModelBase.__call__"
      }
    ],
    "functions": [
      {
        "qualified-name": "django.http.request.HttpRequest"
      },
      {
        "qualified-name": "django.contrib.auth.get_user_model"
      },
      {
        "qualified-name": "django.contrib.auth.__init__.get_user_model"
      },
      {
        "qualified-name": "django.utils.translation.gettext_lazy"
      }
    ],
    "constructors": [
      {
        "kind": "subclass-of",
        "base-qualified-name": "django.db.models.base.Model"
      },
      {
        "kind": "subclass-of",
        "base-qualified-name": "django.db.models.Model"
      },
      {
        "kind": "subclass-of",
        "base-qualified-name": "django.db.models.base.ModelBase.__call__"
      }
    ],
    "methods": [
      {
        "kind": "exact",
        "class-qualified-name": "django.db.models.manager.BaseManager",
        "method-name": "from_queryset"
      },
      {
        "kind": "on-subclass-of",
        "base-qualified-name": "django.apps.registry.Apps",
        "method-name": "get_model"
      },
      {
        "kind": "on-subclass-of",
        "base-qualified-name": "django.db.models.base.Model",
        "method-name": "save"
      },
      {
        "kind": "on-subclass-of",
        "base-qualified-name": "django.db.models.base.Model",
        "method-name": "save"
      },
      {
        "kind": "on-subclass-of",
        "base-qualified-name": "django.db.models.base.Model",
        "method-name": "delete"
      },
      {
        "kind": "on-subclass-of",
        "base-qualified-name": "django.db.models.Model",
        "method-name": "save"
      },
      {
        "kind": "on-subclass-of",
        "base-qualified-name": "django.db.models.Model",
        "method-name": "save"
      },
      {
        "kind": "on-subclass-of",
        "base-qualified-name": "django.db.models.Model",
        "method-name": "delete"
      },
      {
        "kind": "on-subclass-of",
        "base-qualified-name": "django.db.models.base.ModelBase.__call__",
        "method-name": "save"
      },
      {
        "kind": "on-subclass-of",
        "base-qualified-name": "django.db.models.base.ModelBase.__call__",
        "method-name": "save"
      },
      {
        "kind": "on-subclass-of",
        "base-qualified-name": "django.db.models.base.ModelBase.__call__",
        "method-name": "delete"
      },
      {
        "kind": "on-subclass-of",
        "base-qualified-name": "django.db.models.manager.BaseManager",
        "method-name": "all"
      },
      {
        "kind": "on-subclass-of",
        "base-qualified-name": "django.db.models.manager.BaseManager",
        "method-name": "filter"
      },
      {
        "kind": "on-subclass-of",
        "base-qualified-name": "django.db.models.manager.BaseManager",
        "method-name": "exclude"
      },
      {
        "kind": "on-subclass-of",
        "base-qualified-name": "django.db.models.manager.BaseManager",
        "method-name": "complex_filter"
      },
      {
        "kind": "on-subclass-of",
        "base-qualified-name": "django.db.models.manager.BaseManager",
        "method-name": "get"
      },
      {
        "kind": "on-subclass-of",
        "base-qualified-name": "django.db.models.manager.BaseManager",
        "method-name": "create"
      },
      {
        "kind": "on-subclass-of",
        "base-qualified-name": "django.db.models.manager.BaseManager",
        "method-name": "bulk_create"
      },
      {
        "kind": "on-subclass-of",
        "base-qualified-name": "django.db.models.manager.BaseManager",
        "method-name": "bulk_update"
      },
      {
        "kind": "on-subclass-of",
        "base-qualified-name": "django.db.models.manager.BaseManager",
        "method-name": "get_or_create"
      },
      {
        "kind": "on-subclass-of",
        "base-qualified-name": "django.db.models.manager.BaseManager",
        "method-name": "update_or_create"
      },
      {
        "kind": "on-subclass-of",
        "base-qualified-name": "django.db.models.manager.BaseManager",
        "method-name": "first"
      },
      {
        "kind": "on-subclass-of",
        "base-qualified-name": "django.db.models.manager.BaseManager",
        "method-name": "last"
      },
      {
        "kind": "on-subclass-of",
        "base-qualified-name": "django.db.models.manager.BaseManager",
        "method-name": "earliest"
      },
      {
        "kind": "on-subclass-of",
        "base-qualified-name": "django.db.models.manager.BaseManager",
        "method-name": "latest"
      },
      {
        "kind": "on-subclass-of",
        "base-qualified-name": "django.db.models.manager.BaseManager",
        "method-name": "count"
      },
      {
        "kind": "on-subclass-of",
        "base-qualified-name": "django.db.models.manager.BaseManager",
        "method-name": "exists"
      },
      {
        "kind": "on-subclass-of",
        "base-qualified-name": "django.db.models.manager.BaseManager",
        "method-name": "values"
      },
      {
        "kind": "on-subclass-of",
        "base-qualified-name": "django.db.models.manager.BaseManager",
        "method-name": "values_list"
      },
      {
        "kind": "on-subclass-of",
        "base-qualified-name": "django.db.models.manager.BaseManager",
        "method-name": "annotate"
      },
      {
        "kind": "on-subclass-of",
        "base-qualified-name": "django.db.models.manager.BaseManager",
        "method-name": "alias"
      },
      {
        "kind": "on-subclass-of",
        "base-qualified-name": "django.db.models.manager.BaseManager",
        "method-name": "order_by"
      },
      {
        "kind": "on-subclass-of",
        "base-qualified-name": "django.db.models.manager.BaseManager",
        "method-name": "distinct"
      },
      {
        "kind": "on-subclass-of",
        "base-qualified-name": "django.db.models.manager.BaseManager",
        "method-name": "none"
      },
      {
        "kind": "on-subclass-of",
        "base-qualified-name": "django.db.models.manager.BaseManager",
        "method-name": "only"
      },
      {
        "kind": "on-subclass-of",
        "base-qualified-name": "django.db.models.manager.BaseManager",
        "method-name": "defer"
      },
      {
        "kind": "on-subclass-of",
        "base-qualified-name": "django.db.models.manager.BaseManager",
        "method-name": "select_related"
      },
      {
        "kind": "on-subclass-of",
        "base-qualified-name": "django.db.models.manager.BaseManager",
        "method-name": "prefetch_related"
      },
      {
        "kind": "on-subclass-of",
        "base-qualified-name": "django.db.models.manager.BaseManager",
        "method-name": "select_for_update"
      },
      {
        "kind": "on-subclass-of",
        "base-qualified-name": "django.db.models.manager.BaseManager",
        "method-name": "reverse"
      },
      {
        "kind": "on-subclass-of",
        "base-qualified-name": "django.db.models.manager.BaseManager",
        "method-name": "using"
      },
      {
        "kind": "on-subclass-of",
        "base-qualified-name": "django.db.models.manager.BaseManager",
        "method-name": "union"
      },
      {
        "kind": "on-subclass-of",
        "base-qualified-name": "django.db.models.manager.BaseManager",
        "method-name": "intersection"
      },
      {
        "kind": "on-subclass-of",
        "base-qualified-name": "django.db.models.manager.BaseManager",
        "method-name": "difference"
      },
      {
        "kind": "on-subclass-of",
        "base-qualified-name": "django.db.models.manager.BaseManager",
        "method-name": "aget"
      },
      {
        "kind": "on-subclass-of",
        "base-qualified-name": "django.db.models.manager.BaseManager",
        "method-name": "acreate"
      },
      {
        "kind": "on-subclass-of",
        "base-qualified-name": "django.db.models.manager.BaseManager",
        "method-name": "aget_or_create"
      },
      {
        "kind": "on-subclass-of",
        "base-qualified-name": "django.db.models.manager.BaseManager",
        "method-name": "aupdate_or_create"
      },
      {
        "kind": "on-subclass-of",
        "base-qualified-name": "django.db.models.manager.BaseManager",
        "method-name": "afirst"
      },
      {
        "kind": "on-subclass-of",
        "base-qualified-name": "django.db.models.manager.BaseManager",
        "method-name": "alast"
      },
      {
        "kind": "on-subclass-of",
        "base-qualified-name": "django.db.models.manager.BaseManager",
        "method-name": "acount"
      },
      {
        "kind": "on-subclass-of",
        "base-qualified-name": "django.db.models.manager.BaseManager",
        "method-name": "aexists"
      },
      {
        "kind": "on-subclass-of",
        "base-qualified-name": "django.db.models.manager.Manager",
        "method-name": "all"
      },
      {
        "kind": "on-subclass-of",
        "base-qualified-name": "django.db.models.manager.Manager",
        "method-name": "filter"
      },
      {
        "kind": "on-subclass-of",
        "base-qualified-name": "django.db.models.manager.Manager",
        "method-name": "exclude"
      },
      {
        "kind": "on-subclass-of",
        "base-qualified-name": "django.db.models.manager.Manager",
        "method-name": "complex_filter"
      },
      {
        "kind": "on-subclass-of",
        "base-qualified-name": "django.db.models.manager.Manager",
        "method-name": "get"
      },
      {
        "kind": "on-subclass-of",
        "base-qualified-name": "django.db.models.manager.Manager",
        "method-name": "create"
      },
      {
        "kind": "on-subclass-of",
        "base-qualified-name": "django.db.models.manager.Manager",
        "method-name": "bulk_create"
      },
      {
        "kind": "on-subclass-of",
        "base-qualified-name": "django.db.models.manager.Manager",
        "method-name": "bulk_update"
      },
      {
        "kind": "on-subclass-of",
        "base-qualified-name": "django.db.models.manager.Manager",
        "method-name": "get_or_create"
      },
      {
        "kind": "on-subclass-of",
        "base-qualified-name": "django.db.models.manager.Manager",
        "method-name": "update_or_create"
      },
      {
        "kind": "on-subclass-of",
        "base-qualified-name": "django.db.models.manager.Manager",
        "method-name": "first"
      },
      {
        "kind": "on-subclass-of",
        "base-qualified-name": "django.db.models.manager.Manager",
        "method-name": "last"
      },
      {
        "kind": "on-subclass-of",
        "base-qualified-name": "django.db.models.manager.Manager",
        "method-name": "earliest"
      },
      {
        "kind": "on-subclass-of",
        "base-qualified-name": "django.db.models.manager.Manager",
        "method-name": "latest"
      },
      {
        "kind": "on-subclass-of",
        "base-qualified-name": "django.db.models.manager.Manager",
        "method-name": "count"
      },
      {
        "kind": "on-subclass-of",
        "base-qualified-name": "django.db.models.manager.Manager",
        "method-name": "exists"
      },
      {
        "kind": "on-subclass-of",
        "base-qualified-name": "django.db.models.manager.Manager",
        "method-name": "values"
      },
      {
        "kind": "on-subclass-of",
        "base-qualified-name": "django.db.models.manager.Manager",
        "method-name": "values_list"
      },
      {
        "kind": "on-subclass-of",
        "base-qualified-name": "django.db.models.manager.Manager",
        "method-name": "annotate"
      },
      {
        "kind": "on-subclass-of",
        "base-qualified-name": "django.db.models.manager.Manager",
        "method-name": "alias"
      },
      {
        "kind": "on-subclass-of",
        "base-qualified-name": "django.db.models.manager.Manager",
        "method-name": "order_by"
      },
      {
        "kind": "on-subclass-of",
        "base-qualified-name": "django.db.models.manager.Manager",
        "method-name": "distinct"
      },
      {
        "kind": "on-subclass-of",
        "base-qualified-name": "django.db.models.manager.Manager",
        "method-name": "none"
      },
      {
        "kind": "on-subclass-of",
        "base-qualified-name": "django.db.models.manager.Manager",
        "method-name": "only"
      },
      {
        "kind": "on-subclass-of",
        "base-qualified-name": "django.db.models.manager.Manager",
        "method-name": "defer"
      },
      {
        "kind": "on-subclass-of",
        "base-qualified-name": "django.db.models.manager.Manager",
        "method-name": "select_related"
      },
      {
        "kind": "on-subclass-of",
        "base-qualified-name": "django.db.models.manager.Manager",
        "method-name": "prefetch_related"
      },
      {
        "kind": "on-subclass-of",
        "base-qualified-name": "django.db.models.manager.Manager",
        "method-name": "select_for_update"
      },
      {
        "kind": "on-subclass-of",
        "base-qualified-name": "django.db.models.manager.Manager",
        "method-name": "reverse"
      },
      {
        "kind": "on-subclass-of",
        "base-qualified-name": "django.db.models.manager.Manager",
        "method-name": "using"
      },
      {
        "kind": "on-subclass-of",
        "base-qualified-name": "django.db.models.manager.Manager",
        "method-name": "union"
      },
      {
        "kind": "on-subclass-of",
        "base-qualified-name": "django.db.models.manager.Manager",
        "method-name": "intersection"
      },
      {
        "kind": "on-subclass-of",
        "base-qualified-name": "django.db.models.manager.Manager",
        "method-name": "difference"
      },
      {
        "kind": "on-subclass-of",
        "base-qualified-name": "django.db.models.manager.Manager",
        "method-name": "aget"
      },
      {
        "kind": "on-subclass-of",
        "base-qualified-name": "django.db.models.manager.Manager",
        "method-name": "acreate"
      },
      {
        "kind": "on-subclass-of",
        "base-qualified-name": "django.db.models.manager.Manager",
        "method-name": "aget_or_create"
      },
      {
        "kind": "on-subclass-of",
        "base-qualified-name": "django.db.models.manager.Manager",
        "method-name": "aupdate_or_create"
      },
      {
        "kind": "on-subclass-of",
        "base-qualified-name": "django.db.models.manager.Manager",
        "method-name": "afirst"
      },
      {
        "kind": "on-subclass-of",
        "base-qualified-name": "django.db.models.manager.Manager",
        "method-name": "alast"
      },
      {
        "kind": "on-subclass-of",
        "base-qualified-name": "django.db.models.manager.Manager",
        "method-name": "acount"
      },
      {
        "kind": "on-subclass-of",
        "base-qualified-name": "django.db.models.manager.Manager",
        "method-name": "aexists"
      },
      {
        "kind": "on-subclass-of",
        "base-qualified-name": "django.db.models.query.QuerySet",
        "method-name": "all"
      },
      {
        "kind": "on-subclass-of",
        "base-qualified-name": "django.db.models.query.QuerySet",
        "method-name": "filter"
      },
      {
        "kind": "on-subclass-of",
        "base-qualified-name": "django.db.models.query.QuerySet",
        "method-name": "exclude"
      },
      {
        "kind": "on-subclass-of",
        "base-qualified-name": "django.db.models.query.QuerySet",
        "method-name": "complex_filter"
      },
      {
        "kind": "on-subclass-of",
        "base-qualified-name": "django.db.models.query.QuerySet",
        "method-name": "get"
      },
      {
        "kind": "on-subclass-of",
        "base-qualified-name": "django.db.models.query.QuerySet",
        "method-name": "create"
      },
      {
        "kind": "on-subclass-of",
        "base-qualified-name": "django.db.models.query.QuerySet",
        "method-name": "bulk_create"
      },
      {
        "kind": "on-subclass-of",
        "base-qualified-name": "django.db.models.query.QuerySet",
        "method-name": "bulk_update"
      },
      {
        "kind": "on-subclass-of",
        "base-qualified-name": "django.db.models.query.QuerySet",
        "method-name": "get_or_create"
      },
      {
        "kind": "on-subclass-of",
        "base-qualified-name": "django.db.models.query.QuerySet",
        "method-name": "update_or_create"
      },
      {
        "kind": "on-subclass-of",
        "base-qualified-name": "django.db.models.query.QuerySet",
        "method-name": "first"
      },
      {
        "kind": "on-subclass-of",
        "base-qualified-name": "django.db.models.query.QuerySet",
        "method-name": "last"
      },
      {
        "kind": "on-subclass-of",
        "base-qualified-name": "django.db.models.query.QuerySet",
        "method-name": "earliest"
      },
      {
        "kind": "on-subclass-of",
        "base-qualified-name": "django.db.models.query.QuerySet",
        "method-name": "latest"
      },
      {
        "kind": "on-subclass-of",
        "base-qualified-name": "django.db.models.query.QuerySet",
        "method-name": "count"
      },
      {
        "kind": "on-subclass-of",
        "base-qualified-name": "django.db.models.query.QuerySet",
        "method-name": "exists"
      },
      {
        "kind": "on-subclass-of",
        "base-qualified-name": "django.db.models.query.QuerySet",
        "method-name": "values"
      },
      {
        "kind": "on-subclass-of",
        "base-qualified-name": "django.db.models.query.QuerySet",
        "method-name": "values_list"
      },
      {
        "kind": "on-subclass-of",
        "base-qualified-name": "django.db.models.query.QuerySet",
        "method-name": "annotate"
      },
      {
        "kind": "on-subclass-of",
        "base-qualified-name": "django.db.models.query.QuerySet",
        "method-name": "alias"
      },
      {
        "kind": "on-subclass-of",
        "base-qualified-name": "django.db.models.query.QuerySet",
        "method-name": "order_by"
      },
      {
        "kind": "on-subclass-of",
        "base-qualified-name": "django.db.models.query.QuerySet",
        "method-name": "distinct"
      },
      {
        "kind": "on-subclass-of",
        "base-qualified-name": "django.db.models.query.QuerySet",
        "method-name": "none"
      },
      {
        "kind": "on-subclass-of",
        "base-qualified-name": "django.db.models.query.QuerySet",
        "method-name": "only"
      },
      {
        "kind": "on-subclass-of",
        "base-qualified-name": "django.db.models.query.QuerySet",
        "method-name": "defer"
      },
      {
        "kind": "on-subclass-of",
        "base-qualified-name": "django.db.models.query.QuerySet",
        "method-name": "select_related"
      },
      {
        "kind": "on-subclass-of",
        "base-qualified-name": "django.db.models.query.QuerySet",
        "method-name": "prefetch_related"
      },
      {
        "kind": "on-subclass-of",
        "base-qualified-name": "django.db.models.query.QuerySet",
        "method-name": "select_for_update"
      },
      {
        "kind": "on-subclass-of",
        "base-qualified-name": "django.db.models.query.QuerySet",
        "method-name": "reverse"
      },
      {
        "kind": "on-subclass-of",
        "base-qualified-name": "django.db.models.query.QuerySet",
        "method-name": "using"
      },
      {
        "kind": "on-subclass-of",
        "base-qualified-name": "django.db.models.query.QuerySet",
        "method-name": "union"
      },
      {
        "kind": "on-subclass-of",
        "base-qualified-name": "django.db.models.query.QuerySet",
        "method-name": "intersection"
      },
      {
        "kind": "on-subclass-of",
        "base-qualified-name": "django.db.models.query.QuerySet",
        "method-name": "difference"
      },
      {
        "kind": "on-subclass-of",
        "base-qualified-name": "django.db.models.query.QuerySet",
        "method-name": "aget"
      },
      {
        "kind": "on-subclass-of",
        "base-qualified-name": "django.db.models.query.QuerySet",
        "method-name": "acreate"
      },
      {
        "kind": "on-subclass-of",
        "base-qualified-name": "django.db.models.query.QuerySet",
        "method-name": "aget_or_create"
      },
      {
        "kind": "on-subclass-of",
        "base-qualified-name": "django.db.models.query.QuerySet",
        "method-name": "aupdate_or_create"
      },
      {
        "kind": "on-subclass-of",
        "base-qualified-name": "django.db.models.query.QuerySet",
        "method-name": "afirst"
      },
      {
        "kind": "on-subclass-of",
        "base-qualified-name": "django.db.models.query.QuerySet",
        "method-name": "alast"
      },
      {
        "kind": "on-subclass-of",
        "base-qualified-name": "django.db.models.query.QuerySet",
        "method-name": "acount"
      },
      {
        "kind": "on-subclass-of",
        "base-qualified-name": "django.db.models.query.QuerySet",
        "method-name": "aexists"
      },
      {
        "kind": "on-subclass-of",
        "base-qualified-name": "django.db.models.options.Options",
        "method-name": "get_field"
      }
    ],
    "attributes": [
      {
        "kind": "contribution-target",
        "owner-base-qualified-name": "django.conf.LazySettings",
        "scope": "instance"
      },
      {
        "kind": "contribution-target",
        "owner-base-qualified-name": "django.http.request.HttpRequest",
        "scope": "instance"
      },
      {
        "kind": "contribution-target",
        "owner-base-qualified-name": "django.db.models.base.Model",
        "scope": "class"
      },
      {
        "kind": "contribution-target",
        "owner-base-qualified-name": "django.db.models.base.Model",
        "scope": "instance"
      },
      {
        "kind": "contribution-target",
        "owner-base-qualified-name": "django.db.models.Model",
        "scope": "class"
      },
      {
        "kind": "contribution-target",
        "owner-base-qualified-name": "django.db.models.Model",
        "scope": "instance"
      },
      {
        "kind": "contribution-target",
        "owner-base-qualified-name": "django.db.models.base.ModelBase.__call__",
        "scope": "class"
      },
      {
        "kind": "contribution-target",
        "owner-base-qualified-name": "django.db.models.base.ModelBase.__call__",
        "scope": "instance"
      },
      {
        "kind": "contribution-target",
        "owner-base-qualified-name": "django.db.models.enums.Choices",
        "scope": "instance"
      },
      {
        "kind": "contribution-target",
        "owner-base-qualified-name": "django.db.models.enums.TextChoices",
        "scope": "instance"
      },
      {
        "kind": "contribution-target",
        "owner-base-qualified-name": "django.db.models.enums.IntegerChoices",
        "scope": "instance"
      }
    ],
    "settings": [
      {
        "module": "settings"
      },
      {
        "module": "project.settings"
      },
      {
        "config-key": "django-settings-module"
      }
    ],
    "mutations": [
      {
        "kind": "exact",
        "qualified-name": "django.http.request._ImmutableQueryDict"
      }
    ]
  },
  "stub-overlays": [
    {
      "module": "django.db.models.manager",
      "path": "stubs/django/db/models/manager.pyi"
    },
    {
      "module": "django.db.models.query",
      "path": "stubs/django/db/models/query.pyi"
    }
  ]
}
""")
)
