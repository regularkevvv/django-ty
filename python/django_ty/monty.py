"""Django semantic hooks for Monty's restricted Python interpreter.

The host supplies ty_extended.plugin_sdk and all project data. No Django code is imported
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
        class_batch,
        class_patch,
        class_target,
        contribution,
        diagnostic,
        field_patch,
        import_binding,
        instance_target,
        keyword_only,
        location,
        member,
        member_contribution,
        member_descriptor,
        member_patch,
        member_response,
        mutation_diagnostics,
        on_call_return,
        on_call_signature,
        on_call_state,
        on_class_batch,
        on_class_transform,
        on_instance_member,
        on_manifest,
        on_mutation,
        on_project_index,
        optional,
        positional_or_keyword,
        project_index,
        project_index_keys,
        project_index_value,
        snapshot_expression,
        snapshot_nominal,
        snapshot_tuple,
        type_annotation,
        type_expr,
        virtual_class,
        virtual_type,
    )
    from django_ty._monty_types import (
        Argument,
        CallRequest,
        CallReturnResponse,
        CallSignatureResponse,
        CallStateResponse,
        CallSummary,
        ClassBatchRequest,
        ClassBatchResponse,
        ClassModelIndex,
        ClassRequest,
        ClassResponse,
        ClassSummary,
        CompactClass,
        CompactField,
        CompactModelIndex,
        Contribution,
        Diagnostic,
        DjangoIndex,
        FieldData,
        FieldPatch,
        FieldSummary,
        ImportBinding,
        IndexedRequest,
        JsonValue,
        LiteralValue,
        LocalModelIndex,
        MemberPatch,
        MemberRequest,
        MemberResponse,
        ModelIndex,
        ModelTraits,
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
    if "." not in text:
        return type_annotation(text)
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
        "django.db.models.query.ValuesQuerySet["
        + model["expression"]
        + ", "
        + row["expression"]
        + "]"
    )
    result["imports"] = merge_imports([result, model, row])
    result["snapshot"] = snapshot_nominal(
        "django.db.models.query.ValuesQuerySet", [snap(model), snap(row)]
    )
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


RELATION_FIELDS: "dict[str, RelationKind]" = {
    "ForeignKey": "foreign-key",
    "ForeignObject": "foreign-key",
    "OneToOneField": "one-to-one",
    "ManyToManyField": "many-to-many",
}


def relation_kind(call: "CallSummary") -> "RelationKind | None":
    return RELATION_FIELDS.get(short(call_name(call)))


def model_scope(module: str) -> str | None:
    parts = module.split(".")
    scope = None
    for index, part in enumerate(parts):
        if part == "models":
            scope = ".".join(parts[: index + 1])
    return scope


def model_name_lookup(models: "Collection[str]") -> dict[str, str | None]:
    """Index conventional models packages once per project, including ambiguity."""
    lookup: dict[str, str | None] = {}
    scopes: dict[str, str | None] = {}
    for name in models:
        module = module_of(name)
        if module not in scopes:
            scopes[module] = model_scope(module)
        scope = scopes[module]
        if scope is not None:
            key = name if scope == module else scope + "." + short(name)
            lookup[key] = None if key in lookup else name
    return lookup


def resolve_model(
    module: str,
    raw: str,
    models: "Collection[str]",
    lookup: dict[str, str | None] | None = None,
) -> "str":
    if "." not in raw:
        local = module + "." + raw
        if local in models:
            return local
        scope = model_scope(module)
        if scope is None:
            return local
        if lookup is None:
            lookup = model_name_lookup(models)
        return lookup.get(scope + "." + raw) or local
    if raw in models:
        return raw
    if lookup is not None:
        # Preserve sorted-first resolution for every qualified spelling,
        # including nested and ambiguous module scopes. Build only on demand;
        # repeated app.Model relations must not sort and scan the project.
        if "@qualified" not in lookup:
            for candidate in sorted(models):
                parts = candidate.split(".")
                for component in parts[:-1]:
                    for start in range(1, len(parts)):
                        key = "@qualified:" + component + "." + ".".join(parts[start:])
                        if key not in lookup:
                            lookup[key] = candidate
            lookup["@qualified"] = None
        return lookup.get("@qualified:" + raw) or raw
    app, name = raw.split(".", 1)
    for candidate in sorted(models):
        if candidate.endswith("." + name) and (
            candidate.startswith(app + ".") or "." + app + "." in candidate
        ):
            return candidate
    return raw


def relation_argument(call: "CallSummary") -> "Argument | None":
    args = call.get("arguments", [])
    target = named(args, "to")
    if target is not None:
        return target
    for argument in args:
        if argument.get("kind") == "positional":
            return argument
    return None


def relation_target(
    model: str,
    call: "CallSummary",
    settings: dict[str, str],
    models: "Collection[str]",
    lookup: dict[str, str | None] | None = None,
) -> "str | None":
    target = relation_argument(call)
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
    return (
        resolve_model(module_of(model), raw, models, lookup)
        if raw is not None
        else None
    )


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
    lookup: dict[str, str | None] | None = None,
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
    target = (
        relation_target(model, call, settings, models, lookup) if relation else None
    )
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
    return name


def manager_type(model: str, queryset: str | None) -> str:
    return (
        virtual_name(model, "Manager") if queryset else MANAGER_BASE + "[" + model + "]"
    )


def default_members(model: str, queryset: str | None = None) -> "list[MemberPatch]":
    ty = ann(manager_type(model, queryset))
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
    if "." in text:
        return None
    candidate = module_of(owner) + "." + text
    return candidate if candidate in names else None


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
        if len(selected) == before or len(selected) == len(names):
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
    cls: "ClassSummary",
    settings: dict[str, str],
    models: "Collection[str]",
    lookup: dict[str, str | None],
    include_fields: bool = True,
) -> "LocalModelIndex":
    name = cls["qualified-name"]
    result: "LocalModelIndex" = {
        "fields": {"id": "int", "pk": "int"},
        "field_types": {
            "id": settings.get("DEFAULT_AUTO_FIELD", "django.db.models.AutoField"),
        },
        "auto_primary_key": None,
        "auto_primary_key_default": None,
        "custom_primary_key": False,
        "multi_table": False,
        "custom_loading": False,
        "custom_save": False,
    }
    primary = None
    declared_id = False
    for field in cls.get("fields", []):
        call = call_of(field)
        if call is None:
            continue
        declared_id = declared_id or field["name"] == "id"
        data = (
            field_data(name, field, settings, models, lookup)
            if include_fields
            else None
        )
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
        if primary_field["name"] != "id" and not declared_id:
            # The pk query alias is separate from Options.get_field(). A
            # custom primary key also prevents Django creating an implicit id.
            result["field_types"].pop("id", None)
            result["fields"].pop("id", None)
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
        data = field_data(name, primary_field, settings, models, lookup)
        pk_patch: "FieldPatch | None" = None
        if auto_field(call):
            pk_patch = default_fields(default_type)[1]
            result["fields"]["pk"] = "int"
        elif data is not None:
            patches = field_patches(data)
            if patches:
                template = (
                    patches[-1]
                    if data["relation"] in ["foreign-key", "one-to-one"]
                    else patches[0]
                )
                pk_patch = {**template, "name": "pk"}
                parameter = template.get("constructor-parameter")
                if parameter is not None:
                    pk_patch["constructor-parameter"] = {**parameter, "name": "pk"}
            result["fields"]["pk"] = (
                "int"
                if data["relation"] in ["foreign-key", "one-to-one"]
                else canonical(data["get"])
            )
        else:
            # An unsupported explicit key must retain native inference rather
            # than acquiring the implicit integer key's descriptor.
            result["fields"]["pk"] = "typing.Any"
        result["primary_key_patch"] = pk_patch
    methods = [method["name"] for method in cls.get("methods", [])]
    result["custom_loading"] = any(
        method in methods for method in ["__new__", "__init__", "from_db"]
    )
    result["custom_save"] = "save" in methods
    return result


def inherited_indexes(
    classes: "list[ClassSummary]",
    settings: dict[str, str],
    names: set[str],
    lookup: dict[str, str | None],
) -> "dict[str, LocalModelIndex]":
    selected = {
        cls["qualified-name"]: cls for cls in classes if cls["qualified-name"] in names
    }
    local = {
        name: local_index(cls, settings, names, lookup)
        for name, cls in selected.items()
    }
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
                if "primary_key_patch" in indexed and "primary_key_patch" not in result:
                    result["primary_key_patch"] = indexed["primary_key_patch"]
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
            if "primary_key_patch" in own:
                result["primary_key_patch"] = own["primary_key_patch"]
            if own["auto_primary_key"] is not None or own["custom_primary_key"]:
                result["auto_primary_key"] = own["auto_primary_key"]
                result["auto_primary_key_default"] = own["auto_primary_key_default"]
                result["custom_primary_key"] = own["custom_primary_key"]
            for flag in ["custom_loading", "custom_save"]:
                result[flag] = result[flag] or own[flag]
            for field_map in ["fields", "field_types"]:
                values = own[field_map]
                if "primary_key_patch" in result and "primary_key_patch" not in own:
                    declared_id = any(
                        field["name"] == "id" for field in cls.get("fields", [])
                    )
                    values = {
                        key: value
                        for key, value in values.items()
                        if key != "pk" and (key != "id" or declared_id)
                    }
                result[field_map].update(values)
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
    # Row declarations are built only when a query actually requests them.
    # Class manager identities still need an index-time nominal declaration.
    result = []
    if queryset is not None:
        result.append(
            virtual_type(
                virtual_name(model, "Manager"),
                virtual_class(
                    bases=[type_expr(MANAGER_BASE + "[" + model + "]")],
                    members=queryset_manager_members(queryset),
                ),
            )
        )
    return result


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


def deferred_model_class(cls: "ClassSummary") -> "ClassSummary":
    fields: "list[FieldSummary]" = []
    for field in cls.get("fields", []):
        call = call_of(field)
        if call is None:
            continue
        relation = relation_kind(call) is not None
        arguments: "list[Argument]" = []
        for argument in call.get("arguments", []):
            if argument.get("name") not in [
                "null",
                "default",
                "db_default",
                "primary_key",
                "choices",
                "to",
            ] and not (relation and argument.get("kind") == "positional"):
                continue
            # Retain typed values; argument locations do not participate in
            # deferred model semantics. Field locations still own diagnostics.
            compact: "Argument" = {"kind": argument["kind"]}
            if "name" in argument:
                compact["name"] = argument["name"]
            if "value" in argument:
                compact["value"] = argument["value"]
            if "type-expr" in argument:
                compact["type-expr"] = argument["type-expr"]
            arguments.append(compact)
        fields.append(
            {
                "name": field["name"],
                "assigned-value": {
                    "kind": "call",
                    "callee": {"qualified-name": call_name(call)},
                    "arguments": arguments,
                },
            }
        )
    return {
        "qualified-name": cls["qualified-name"],
        "bases": cls.get("bases", []),
        "fields": fields,
        "methods": [{"name": method["name"]} for method in cls.get("methods", [])],
    }


def plain_model_index(
    classes: "list[ClassSummary]",
    settings: dict[str, str],
    names: set[str],
    lookup: dict[str, str | None],
    model_aliases: dict[str, str | None],
    auth: str | None,
    generated: dict[str, str],
    decorators: "list[CallSummary]",
) -> "tuple[DjangoIndex, list[Diagnostic]] | None":
    """Fuse the index for direct, undecorated models with implicit keys.

    Custom keys, model methods, Meta, managers and inheritance keep the general
    path. The result is the same private format and retains global relation
    diagnostics even when no call site uses a model.
    """
    if decorators:
        return None
    native_members: dict[str, dict[str, bool]] = {}
    models: "dict[str, CompactModelIndex]" = {}
    deferred: "dict[str, ClassRequest | CompactClass]" = {}
    reverse: dict[str, dict[str, str]] = {}
    queries: dict[str, dict[str, str]] = {}
    reverse_sources: "dict[str, SymbolSource]" = {}
    diagnostics: "list[Diagnostic]" = []
    for cls in classes:
        name = cls["qualified-name"]
        if name not in names:
            continue
        bases = cls.get("bases", [])
        if (
            len(bases) != 1
            or bases[0]["expression"] not in MODEL_BASES
            or cls.get("decorators")
            or cls.get("methods")
            or cls.get("nested-classes")
        ):
            return None
        decisions: dict[str, bool] = {}
        fields: "list[CompactField]" = []
        targets: list[str] = []
        used_settings: dict[str, str] = {}
        for field in cls.get("fields", []):
            if field["name"] == "objects":
                return None
            call = call_of(field)
            if call is None:
                continue
            callee = call_name(call)
            factory = short(callee)
            if (
                factory in ["AutoField", "BigAutoField", "SmallAutoField"]
                or callee.endswith(".CompositePrimaryKey")
                or typed_literal(
                    named(call.get("arguments", []), "primary_key"), "bool"
                )
                is True
                or factory in ["as_manager", "BaseManager"]
                or factory.endswith("Manager")
                or callee in generated
                or ("." not in callee and module_of(name) + "." + callee in generated)
            ):
                return None
            kind = RELATION_FIELDS.get(factory)
            member_name = field["name"]
            if member_name not in decisions:
                decisions[member_name] = (
                    member_name not in ["id", "pk"]
                    and kind is None
                    and factory in SCALAR_FIELDS
                )
            if kind in ["foreign-key", "one-to-one"]:
                decisions.setdefault(member_name + "_id", False)
            arguments: "list[Argument]" = []
            for argument in call.get("arguments", []):
                if argument.get("name") not in [
                    "null",
                    "default",
                    "db_default",
                    "primary_key",
                    "choices",
                    "to",
                ] and not (kind is not None and argument.get("kind") == "positional"):
                    continue
                item: "Argument" = {"kind": argument["kind"]}
                if "name" in argument:
                    item["name"] = argument["name"]
                if "value" in argument:
                    item["value"] = argument["value"]
                if "type-expr" in argument:
                    item["type-expr"] = argument["type-expr"]
                arguments.append(item)
            fields.append({"n": field["name"], "c": callee, "a": arguments})
            if kind is None:
                continue
            argument = relation_argument(call)
            value = argument.get("value") if argument is not None else None
            key = None
            if value is not None:
                if value["kind"] == "str":
                    key = value["value"]
                elif value["kind"] == "enum-ref" or value["kind"] == "symbol-ref":
                    key = value["qualified-name"]
            if key is not None and key in settings and key != "DEFAULT_AUTO_FIELD":
                used_settings[key] = settings[key]
            target = relation_target(name, call, settings, names, lookup)
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
            if target != name and target not in targets:
                targets.append(target)
            query_name = typed_literal(
                named(call.get("arguments", []), "related_query_name"), "str"
            )
            if query_name is not None and query_name != "+":
                queries.setdefault(target, {})[query_name] = name
            accessor = typed_literal(
                named(call.get("arguments", []), "related_name"), "str"
            )
            if accessor == "+":
                continue
            if accessor is None:
                accessor = short(name).lower() + (
                    "" if kind == "one-to-one" else "_set"
                )
            key = target + "." + accessor
            source = field.get("source") or {}
            if key in reverse_sources:
                first = reverse_sources[key]
                metadata: "dict[str, JsonValue]" = (
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
            reverse.setdefault(target, {})[accessor] = (
                name if kind == "one-to-one" else manager_type(name, None)
            )
        record: "CompactClass" = {"v": 1, "f": fields}
        if bases != [
            {"expression": "django.db.models.base.Model", "mode": "annotation"}
        ]:
            record["b"] = bases
        if targets:
            record["t"] = targets
        if "DEFAULT_AUTO_FIELD" in settings:
            record["a"] = settings["DEFAULT_AUTO_FIELD"]
        if used_settings:
            record["s"] = used_settings
        models[name] = {"v": 1}
        deferred[name] = record
        native_members[name] = {
            member: True for member, native in decisions.items() if native
        }
    for name in sorted(queries):
        model = models[name]
        model["j"] = queries[name]
    return {
        "index_format": 1,
        "native_member_abstentions": native_members,
        "models": {name: model for name, model in models.items()},
        "deferred_classes": deferred,
        "model_aliases": model_aliases,
        "settings": settings,
        "auth_user_model": auth,
        "reverse_members": reverse,
    }, diagnostics


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
    lookup = model_name_lookup(names)
    model_aliases: dict[str, str | None] = {}
    for name in names:
        alias = short(name)
        model_aliases[alias] = None if alias in model_aliases else name
    # Plain models do not need a QuerySet hierarchy. Resolve it only for a
    # from_queryset assignment or after the direct-model path declines.
    queryset_names: set[str] | None = None
    generated = {}
    for assignment in request.get("assignments", []):
        call = call_of(assignment)
        if call is None or short(call_name(call)) != "from_queryset":
            continue
        if queryset_names is None:
            queryset_names = derived_names(classes, [QUERYSET_BASE], generic=True)
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
    if (
        request.get("context", {}).get("config", {}).get("compact-model-index")
        is not False
    ):
        fused = plain_model_index(
            classes, settings, names, lookup, model_aliases, auth, generated, decorators
        )
        if fused is not None:
            data, diagnostics = fused
            declare_native_member_abstentions(data)
            return project_index(
                data,
                contributions=contributions,
                dependencies=[
                    dep
                    for module in request.get("settings", [])
                    for dep in module.get("dependencies", [])
                ],
                diagnostics=diagnostics,
            )
    # The direct path has already checked its bases. Inheritance and custom
    # managers retain the complete general hierarchy and schema path.
    flat_models = not any(
        resolve_class(cls["qualified-name"], base["expression"], names) in names
        for cls in classes
        if cls["qualified-name"] in names
        for base in cls.get("bases", [])
    )
    if queryset_names is None:
        queryset_names = derived_names(classes, [QUERYSET_BASE], generic=True)
    querysets = {
        cls["qualified-name"]: cls
        for cls in classes
        if cls["qualified-name"] in queryset_names
    }
    indexes = (
        {
            cls["qualified-name"]: local_index(cls, settings, names, lookup, False)
            for cls in classes
            if cls["qualified-name"] in names
        }
        if flat_models
        else inherited_indexes(classes, settings, names, lookup)
    )
    models: "dict[str, ModelIndex]" = {}
    virtuals: "list[VirtualType]" = []
    diagnostics = []
    reverse_sources: "dict[str, SymbolSource]" = {}
    query_fields: dict[str, dict[str, str]] = {}
    reverse_members: dict[str, dict[str, str]] = {}
    for cls in classes:
        name = cls["qualified-name"]
        if name not in names:
            continue
        indexed = indexes[name]
        fields = indexed["fields"]
        queryset = manager_queryset(cls, querysets, generated)
        virtuals.extend(model_virtual_types(name, fields, querysets.get(queryset)))
        models[name] = {
            "native_default_manager": (
                len(cls.get("bases", [])) == 1
                and cls["bases"][0]["expression"] in MODEL_BASES
                and not cls.get("decorators")
                and not cls.get("methods")
                and not cls.get("nested-classes")
                and not any(
                    field["name"] == "objects" for field in cls.get("fields", [])
                )
            ),
            "lazy_fields": flat_models,
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
        if "primary_key_patch" in indexed:
            models[name]["primary_key_patch"] = indexed["primary_key_patch"]
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
            target = relation_target(name, call, settings, names, lookup)
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
                metadata: "dict[str, JsonValue]" = (
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
            reverse_members.setdefault(target, {})[reverse] = (
                name
                if kind == "one-to-one"
                else manager_type(name, models[name]["manager_queryset"])
            )
    for name in sorted(query_fields):
        models[name]["query_fields"] = query_fields[name]
    deps = [
        dep
        for module in request.get("settings", [])
        for dep in module.get("dependencies", [])
    ]
    deferred: "dict[str, ClassRequest]" = {
        cls["qualified-name"]: {
            "class": deferred_model_class(cls),
            "project-index": class_project_index(cls, settings, models, lookup),
        }
        for cls in classes
        if cls["qualified-name"] in models
    }
    # Custom querysets add class members that native lookup must see directly.
    # Ordinary model fields stay in the unchanged native declaration tree.
    for name in models:
        if not models[name]["manager_queryset"]:
            continue
        patch = analyze_django_class(deferred[name])
        for member_patch in (patch or {}).get("class-members", []):
            contributions.append(
                contribution(
                    {},
                    class_target(name),
                    member_contribution(member_patch),
                    name + "." + member_patch["name"],
                )
            )
    stored_models: "dict[str, ModelIndex | CompactModelIndex]" = {
        name: model for name, model in models.items()
    }
    stored_classes: "dict[str, ClassRequest | CompactClass]" = {
        name: item for name, item in deferred.items()
    }
    compact = (
        flat_models
        and request.get("context", {}).get("config", {}).get("compact-model-index")
        is not False
    )
    if compact:
        stored_models = {name: compact_model(model) for name, model in models.items()}
        stored_classes = {
            name: compact_class(name, item) for name, item in deferred.items()
        }
    data: "DjangoIndex" = {
        "models": stored_models,
        "model_aliases": model_aliases,
        "settings": settings,
        "auth_user_model": auth,
        "deferred_classes": stored_classes,
        "reverse_members": reverse_members,
    }
    if compact:
        data["index_format"] = 1
    declare_native_member_abstentions(data)
    return project_index(
        data,
        contributions=contributions,
        virtual_types=virtuals,
        dependencies=deps,
        diagnostics=diagnostics,
    )


def compact_model(model: "ModelIndex") -> "CompactModelIndex":
    """Flat models resolve field maps only on use; retain nondefault traits."""
    result: "CompactModelIndex" = {"v": 1}
    if model["auto_primary_key"] != "id":
        result["p"] = model["auto_primary_key"]
    if model["auto_primary_key_default"] is not None:
        result["d"] = model["auto_primary_key_default"]
    if model["manager_queryset"] is not None:
        result["q"] = model["manager_queryset"]
    if model["custom_loading"]:
        result["l"] = True
    if model["custom_save"]:
        result["s"] = True
    if model["signal_receivers"]:
        result["r"] = True
    if not model.get("native_default_manager", False):
        result["n"] = False
    if "query_fields" in model:
        result["j"] = model["query_fields"]
    if "primary_key_patch" in model:
        result["k"] = model["primary_key_patch"]
    return result


def expanded_traits(model: "CompactModelIndex") -> "ModelTraits":
    result: "ModelTraits" = {
        "native_default_manager": model.get("n", True),
        "lazy_fields": True,
        "manager_queryset": model.get("q"),
        "auto_primary_key": model.get("p", "id"),
        "auto_primary_key_default": model.get("d"),
        "custom_loading": model.get("l", False),
        "custom_save": model.get("s", False),
        "signal_receivers": model.get("r", False),
    }
    if "j" in model:
        result["query_fields"] = model["j"]
    if "k" in model:
        result["primary_key_patch"] = model["k"]
    return result


def compact_class(name: str, request: "ClassRequest") -> "ClassRequest | CompactClass":
    cls = request["class"]
    scoped = request.get("project-index") or {}
    owners = scoped.get("class_models", {})
    # Preserve any future scope shape this codec does not know how to encode.
    if any(value for owner, value in owners.items() if owner != name):
        return request
    if any(
        key not in ["auto_primary_key_default", "manager_queryset"]
        for key in owners.get(name, {})
    ):
        return request
    fields: "list[CompactField]" = []
    for field in cls.get("fields", []):
        call = call_of(field)
        assert call is not None  # deferred_model_class retains calls only.
        fields.append(
            {"n": field["name"], "c": call_name(call), "a": call.get("arguments", [])}
        )
    result: "CompactClass" = {"v": 1, "f": fields}
    bases = cls.get("bases", [])
    if bases != [{"expression": "django.db.models.base.Model", "mode": "annotation"}]:
        result["b"] = bases
    methods = [method["name"] for method in cls.get("methods", [])]
    if methods:
        result["m"] = methods
    targets = [owner for owner in owners if owner != name]
    if targets:
        result["t"] = targets
    own = owners.get(name, {})
    default = own.get("auto_primary_key_default")
    if default is not None:
        result["d"] = default
    queryset = own.get("manager_queryset")
    if queryset is not None:
        result["q"] = queryset
    settings = scoped.get("settings", {})
    if "DEFAULT_AUTO_FIELD" in settings:
        result["a"] = settings["DEFAULT_AUTO_FIELD"]
    extra = {
        key: value for key, value in settings.items() if key != "DEFAULT_AUTO_FIELD"
    }
    if extra:
        result["s"] = extra
    return result


def deferred_request(request: "IndexedRequest", name: str) -> "ClassRequest | None":
    stored = project_index_value(request, ["deferred_classes", name])
    if stored is None or "class" in stored or stored.get("v") != 1:
        return stored
    return expanded_class(name, stored)


def expanded_class(name: str, stored: "CompactClass") -> "ClassRequest":
    owners: "dict[str, ClassModelIndex]" = {
        name: {
            "auto_primary_key_default": stored.get("d"),
            "manager_queryset": stored.get("q"),
        }
    }
    for target in stored.get("t", []):
        owners[target] = {}
    settings = dict(stored.get("s", {}))
    if "a" in stored:
        settings["DEFAULT_AUTO_FIELD"] = stored["a"]
    return {
        "class": {
            "qualified-name": name,
            "bases": stored.get(
                "b",
                [{"expression": "django.db.models.base.Model", "mode": "annotation"}],
            ),
            "methods": [{"name": method} for method in stored.get("m", [])],
            "fields": [
                {
                    "name": field["n"],
                    "assigned-value": {
                        "kind": "call",
                        "callee": {"qualified-name": field["c"]},
                        "arguments": field["a"],
                    },
                }
                for field in stored["f"]
            ],
        },
        "project-index": {"class_models": owners, "settings": settings},
    }


def class_project_index(
    cls: "ClassSummary",
    settings: dict[str, str],
    models: "dict[str, ModelIndex]",
    lookup: dict[str, str | None] | None = None,
) -> "DjangoIndex":
    """Keep the model and resolved relation targets needed by its class hook."""
    name = cls["qualified-name"]
    scoped: "dict[str, ClassModelIndex]" = {}
    used_settings: dict[str, str] = {}
    if "DEFAULT_AUTO_FIELD" in settings:
        used_settings["DEFAULT_AUTO_FIELD"] = settings["DEFAULT_AUTO_FIELD"]
    if name in models:
        scoped[name] = {
            "auto_primary_key_default": models[name]["auto_primary_key_default"],
            "manager_queryset": models[name]["manager_queryset"],
        }
        if "primary_key_patch" in models[name]:
            scoped[name]["primary_key_patch"] = models[name]["primary_key_patch"]
    for field in cls.get("fields", []):
        call = call_of(field)
        if call is not None and relation_kind(call):
            argument = relation_argument(call)
            value = argument.get("value") if argument is not None else None
            key = None
            if value is not None:
                if value["kind"] == "str":
                    key = value["value"]
                elif value["kind"] == "enum-ref" or value["kind"] == "symbol-ref":
                    key = value["qualified-name"]
            if key is not None and key in settings:
                used_settings[key] = settings[key]
            target = relation_target(name, call, settings, models, lookup)
            if target is not None and target in models:
                if target not in scoped:
                    scoped[target] = {}
    return {"class_models": scoped, "settings": used_settings}


@on_class_transform
def analyze_django_class(request: "ClassRequest") -> "ClassResponse | None":
    cls = request["class"]
    name = cls["qualified-name"]
    scoped = request.get("project-index") or {}
    if isinstance(scoped.get("class_models"), dict):
        # Class-scoped requests already own these dictionaries. This hook only
        # reads them, so the SDK's defensive JSON copies are unnecessary here.
        indexed = scoped["class_models"]
        settings = scoped.get("settings", {}) or {}
    else:
        indexed = project_index_value(request, ["class_models"])
        if indexed is None:
            indexed = project_index_value(request, ["models"], {}) or {}
            indexed = {
                owner: expanded_traits(model) if model.get("v") == 1 else model
                for owner, model in indexed.items()
            }
        settings = project_index_value(request, ["settings"], {}) or {}
    if name not in indexed and not any(
        base["expression"] in MODEL_BASES for base in cls.get("bases", [])
    ):
        return None
    own = indexed.get(name) or {}
    if "primary_key_patch" in own:
        primary_key = own["primary_key_patch"]
        fields = [primary_key] if primary_key is not None else []
    else:
        fields = default_fields(own.get("auto_primary_key_default"))
    queryset = (indexed.get(name) or {}).get("manager_queryset")
    members = default_members(name, queryset) if queryset else []
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
                ty = manager_type(
                    name, (indexed.get(name) or {}).get("manager_queryset")
                )
            else:
                ty = (
                    callee_name
                    if "." in callee_name
                    else module_of(name) + "." + callee_name
                )
            if isinstance((indexed.get(name) or {}).get("manager_queryset"), str):
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
            patches = field_patches(data)
            if data["relation"] is None and not auto_field(call):
                for patch in patches:
                    patch["mode"] = "fill-on-miss"
            fields.extend(patches)
    return class_patch(fields=fields, class_members=members, instance_members=instance)


@on_class_batch
def analyze_django_classes(request: "ClassBatchRequest") -> "ClassBatchResponse":
    """Share interpreter setup; each class keeps its own complete input index."""
    return class_batch([analyze_django_class(item) for item in request["requests"]])


def model_traits(request: "IndexedRequest", name: str) -> "ModelTraits | None":
    name = qualified_model(request, name)
    model = project_index_value(request, ["models", name])
    if model is not None and model.get("v") == 1:
        return expanded_traits(model)
    return model


def model_entry(request: "IndexedRequest", name: str) -> "ModelIndex | None":
    name = qualified_model(request, name)
    model = project_index_value(request, ["models", name])
    if model is not None and model.get("v") == 1:
        expanded: "ModelIndex" = {
            **expanded_traits(model),
            "fields": {},
            "field_types": {},
        }
        model = expanded
    if model is not None and model.get("lazy_fields"):
        deferred = deferred_request(request, name)
        if deferred is not None:
            scoped = deferred["project-index"]
            indexed = local_index(
                deferred["class"],
                scoped.get("settings", {}),
                scoped["class_models"],
                model_name_lookup(scoped["class_models"]),
            )
            model["fields"] = indexed["fields"]
            model["field_types"] = indexed["field_types"]
    return model


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
    fields = model_fields(request, model)
    if fields is None:
        return []
    result = []
    args = request.get("arguments", [])
    if method in LOOKUP_METHODS:
        for arg in args:
            if arg.get("kind") == "keyword" and not creation_defaults(method, arg):
                name = arg.get("name")
                if name is not None and "__" not in name and name in fields:
                    expected = fields[name]
                    found = (
                        None
                        if lookup_matches(expected, None, arg)
                        else invalid_lookup_diag(model, name, name, expected, arg)
                    )
                else:
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
        names = sorted(fields)
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
            names = sorted(fields)
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


def qualified_model(request: "IndexedRequest", name: str) -> "str":
    if "." in name:
        return name
    resolved = project_index_value(request, ["model_aliases", name])
    return resolved if isinstance(resolved, str) else name


def prefetched_row(request: "CallRequest", row: "TypeExpr") -> "TypeExpr | None":
    entries = []
    for arg in request.get("arguments", []):
        ty = arg.get("type-expr")
        if ty is None:
            continue
        parts = generic_args(ty["expression"], "Prefetch")
        if parts is None or len(parts) != 3:
            continue
        queryset = generic_args(parts[1], "QuerySet") or generic_args(
            parts[1], "ValuesQuerySet"
        )
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
    original_model = model["expression"]
    qualified = qualified_model(request, original_model)
    if qualified != original_model:
        model = ann(qualified)
        model["snapshot"] = snapshot_nominal(qualified)
    if request.get("context", {}).get("speculative", False):
        indexed = model_traits(request, qualified)
        actual = canonical(receiver_value.get("type-expr") or ann("object"))
        if (
            method != "get"
            or actual.split("[", 1)[0] not in [BASE_MANAGER_BASE, MANAGER_BASE]
            or indexed is None
            or not indexed.get("native_default_manager", False)
        ):
            return None
        return call_return_patch(
            ann(qualified), validate_arguments(request, qualified, method)
        )
    is_queryset = (receiver_value.get("nominal-class") or "").endswith("QuerySet")
    row = arguments[1] if is_queryset and len(arguments) > 1 else model
    if row["expression"] == original_model:
        row = model
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
    native = request.get("default-return-type")
    if native is not None:
        native_snapshot = snap(native)
        if native_snapshot.get("kind") == "nominal" and native_snapshot == snap(result):
            # Keep native inference when its complete nominal identity and type
            # arguments match. Other snapshots retain the explicit projection.
            if not diagnostics:
                return None
            result = native
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
    for name in sorted(project_index_keys(request, ["models"])):
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
        model = project_index_value(request, ["auth_user_model"])
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


def deferred_class_patch(
    request: "IndexedRequest", name: str
) -> "ClassResponse | None":
    deferred = deferred_request(request, name)
    return analyze_django_class(deferred) if deferred is not None else None


def declare_native_member_abstentions(data: "DjangoIndex") -> None:
    """Publish exact scalar abstentions with one classification per field."""
    prepared = data.get("native_member_abstentions")
    if prepared is None:
        prepared = {}
        for name, stored in data.get("deferred_classes", {}).items():
            if "class" in stored or stored.get("v") != 1:
                continue
            decisions: dict[str, bool] = {}
            for field in stored["f"]:
                call: "CallSummary" = {
                    "kind": "call",
                    "callee": {"qualified-name": field["c"]},
                }
                kind = relation_kind(call)
                member_name = field["n"]
                if member_name not in decisions:
                    decisions[member_name] = (
                        member_name not in ["id", "pk"]
                        and kind is None
                        and not auto_field(call)
                        and short(field["c"]) in SCALAR_FIELDS
                    )
                if kind in ["foreign-key", "one-to-one"]:
                    decisions.setdefault(member_name + "_id", False)
            prepared[name] = {
                member: True for member, native in decisions.items() if native
            }
    result: dict[str, dict[str, bool]] = {}
    for name, members in prepared.items():
        reverse = data.get("reverse_members", {}).get(name, {})
        selected = {
            member: True
            for member, native in members.items()
            if native and member not in reverse
        }
        if selected:
            result[name] = selected
    data["native_member_abstentions"] = result


def native_scalar_member(stored: "CompactClass", member_name: str) -> bool:
    """Ordinary scalar fields already use their native descriptor.

    Default key aliases and earlier relation descriptors retain precedence;
    a later scalar with a colliding name must not hide their replacement.
    """
    if member_name in ["id", "pk"]:
        return False
    for field in stored["f"]:
        call: "CallSummary" = {"kind": "call", "callee": {"qualified-name": field["c"]}}
        relation = relation_kind(call)
        if field["n"] == member_name:
            return (
                relation is None
                and not auto_field(call)
                and short(field["c"]) in SCALAR_FIELDS
            )
        if (
            relation in ["foreign-key", "one-to-one"]
            and field["n"] + "_id" == member_name
        ):
            return False
    return False


@on_instance_member
def django_native_member(request: "MemberRequest") -> "MemberResponse | None":
    name = request["owner"]["expression"]
    reverse = project_index_value(
        request, ["reverse_members", name, request["member-name"]]
    )
    if isinstance(reverse, str):
        return member_response(replace_member(request["member-name"], ann(reverse)))
    stored = project_index_value(request, ["deferred_classes", name])
    if stored is None:
        return None
    member_name = request["member-name"]
    if "class" not in stored and stored.get("v") == 1:
        if native_scalar_member(stored, member_name):
            return None
        deferred = expanded_class(name, stored)
    else:
        deferred = stored
    patch = analyze_django_class(deferred)
    if patch is None:
        return None
    for field in patch.get("fields", []):
        if field["name"] == member_name:
            if field["mode"] != "replace-existing":
                return None
            return member_response(
                member_patch(
                    member_name,
                    field.get("descriptor")
                    or member_descriptor(
                        field["instance-get-type"],
                        instance_set_type=field.get("instance-set-type"),
                    ),
                    mode="replace-existing",
                )
            )
    for candidate in patch.get("instance-members", []):
        if candidate["name"] == member_name:
            return member_response(candidate)
    return None


@on_call_signature
def django_signature(request: "CallRequest") -> "CallSignatureResponse | None":
    callee = request["callee"]["expression"]
    if request.get("receiver") is None:
        deferred = deferred_request(request, callee)
        if deferred is not None:
            own = (
                (deferred.get("project-index") or {})
                .get("class_models", {})
                .get(callee, {})
            )
            if "primary_key_patch" in own and own["primary_key_patch"] is None:
                return None
            if any(
                method["name"] == "__init__"
                for method in deferred["class"].get("methods", [])
            ):
                return None
            patch = analyze_django_class(deferred)
            parameters = {}
            for field in (patch or {}).get("fields", []):
                parameter = field.get("constructor-parameter")
                if parameter is not None:
                    parameters[parameter["name"]] = parameter
            return call_signature_patch(
                callable_signature(
                    [parameters[name] for name in sorted(parameters)], ann(callee)
                )
            )
    if short(callee) != "from_queryset":
        return None
    ret = (request.get("receiver") or {}).get("type-expr") or ann(
        "type[django.db.models.manager.BaseManager[typing.Any]]"
    )
    return call_signature_patch(
        callable_signature(
            [
                positional_or_keyword(
                    "queryset_class",
                    ann("type[django.db.models.query.QuerySet[typing.Any]]"),
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
        model = model_traits(request, request["callee"]["expression"])
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
    model = model_traits(request, name)
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
@on_manifest
def packaged_manifest(request: dict[str, JsonValue]) -> dict[str, JsonValue]:
    return json.loads(r"""
{
  "id": "django-ty",
  "name": "Django ty plugin",
  "version": "0.7.0",
  "protocol-version": {
    "major": 0,
    "minor": 9
  },
  "ty-compatibility": {
    "requirement": ">=0.89.0,<0.90.0"
  },
  "runtime": {
    "kind": "monty",
    "artifact": "monty.py"
  },
  "capabilities": {
    "stub-overlays": true,
    "class-transform": false,
    "class-member": false,
    "instance-member": true,
    "call-signature": true,
    "call-return": true,
    "call-state": true,
    "additional-dependencies": false,
    "project-index": true,
    "cross-symbol-contributions": true,
    "settings-data": true,
    "virtual-types": true,
    "mutation-validation": true,
    "project-index-lookup": true,
    "class-batch": false
  },
  "claims": {
    "classes": [],
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
      },
      {
        "kind": "on-subclass-of",
        "base-qualified-name": "django.db.models.query._BaseQuerySet",
        "method-name": "all"
      },
      {
        "kind": "on-subclass-of",
        "base-qualified-name": "django.db.models.query.ValuesQuerySet",
        "method-name": "all"
      },
      {
        "kind": "on-subclass-of",
        "base-qualified-name": "django.db.models.query._BaseQuerySet",
        "method-name": "filter"
      },
      {
        "kind": "on-subclass-of",
        "base-qualified-name": "django.db.models.query.ValuesQuerySet",
        "method-name": "filter"
      },
      {
        "kind": "on-subclass-of",
        "base-qualified-name": "django.db.models.query._BaseQuerySet",
        "method-name": "exclude"
      },
      {
        "kind": "on-subclass-of",
        "base-qualified-name": "django.db.models.query.ValuesQuerySet",
        "method-name": "exclude"
      },
      {
        "kind": "on-subclass-of",
        "base-qualified-name": "django.db.models.query._BaseQuerySet",
        "method-name": "complex_filter"
      },
      {
        "kind": "on-subclass-of",
        "base-qualified-name": "django.db.models.query.ValuesQuerySet",
        "method-name": "complex_filter"
      },
      {
        "kind": "on-subclass-of",
        "base-qualified-name": "django.db.models.query._BaseQuerySet",
        "method-name": "get"
      },
      {
        "kind": "on-subclass-of",
        "base-qualified-name": "django.db.models.query.ValuesQuerySet",
        "method-name": "get"
      },
      {
        "kind": "on-subclass-of",
        "base-qualified-name": "django.db.models.query._BaseQuerySet",
        "method-name": "create"
      },
      {
        "kind": "on-subclass-of",
        "base-qualified-name": "django.db.models.query.ValuesQuerySet",
        "method-name": "create"
      },
      {
        "kind": "on-subclass-of",
        "base-qualified-name": "django.db.models.query._BaseQuerySet",
        "method-name": "bulk_create"
      },
      {
        "kind": "on-subclass-of",
        "base-qualified-name": "django.db.models.query.ValuesQuerySet",
        "method-name": "bulk_create"
      },
      {
        "kind": "on-subclass-of",
        "base-qualified-name": "django.db.models.query._BaseQuerySet",
        "method-name": "bulk_update"
      },
      {
        "kind": "on-subclass-of",
        "base-qualified-name": "django.db.models.query.ValuesQuerySet",
        "method-name": "bulk_update"
      },
      {
        "kind": "on-subclass-of",
        "base-qualified-name": "django.db.models.query._BaseQuerySet",
        "method-name": "get_or_create"
      },
      {
        "kind": "on-subclass-of",
        "base-qualified-name": "django.db.models.query.ValuesQuerySet",
        "method-name": "get_or_create"
      },
      {
        "kind": "on-subclass-of",
        "base-qualified-name": "django.db.models.query._BaseQuerySet",
        "method-name": "update_or_create"
      },
      {
        "kind": "on-subclass-of",
        "base-qualified-name": "django.db.models.query.ValuesQuerySet",
        "method-name": "update_or_create"
      },
      {
        "kind": "on-subclass-of",
        "base-qualified-name": "django.db.models.query._BaseQuerySet",
        "method-name": "first"
      },
      {
        "kind": "on-subclass-of",
        "base-qualified-name": "django.db.models.query.ValuesQuerySet",
        "method-name": "first"
      },
      {
        "kind": "on-subclass-of",
        "base-qualified-name": "django.db.models.query._BaseQuerySet",
        "method-name": "last"
      },
      {
        "kind": "on-subclass-of",
        "base-qualified-name": "django.db.models.query.ValuesQuerySet",
        "method-name": "last"
      },
      {
        "kind": "on-subclass-of",
        "base-qualified-name": "django.db.models.query._BaseQuerySet",
        "method-name": "earliest"
      },
      {
        "kind": "on-subclass-of",
        "base-qualified-name": "django.db.models.query.ValuesQuerySet",
        "method-name": "earliest"
      },
      {
        "kind": "on-subclass-of",
        "base-qualified-name": "django.db.models.query._BaseQuerySet",
        "method-name": "latest"
      },
      {
        "kind": "on-subclass-of",
        "base-qualified-name": "django.db.models.query.ValuesQuerySet",
        "method-name": "latest"
      },
      {
        "kind": "on-subclass-of",
        "base-qualified-name": "django.db.models.query._BaseQuerySet",
        "method-name": "count"
      },
      {
        "kind": "on-subclass-of",
        "base-qualified-name": "django.db.models.query.ValuesQuerySet",
        "method-name": "count"
      },
      {
        "kind": "on-subclass-of",
        "base-qualified-name": "django.db.models.query._BaseQuerySet",
        "method-name": "exists"
      },
      {
        "kind": "on-subclass-of",
        "base-qualified-name": "django.db.models.query.ValuesQuerySet",
        "method-name": "exists"
      },
      {
        "kind": "on-subclass-of",
        "base-qualified-name": "django.db.models.query._BaseQuerySet",
        "method-name": "values"
      },
      {
        "kind": "on-subclass-of",
        "base-qualified-name": "django.db.models.query.ValuesQuerySet",
        "method-name": "values"
      },
      {
        "kind": "on-subclass-of",
        "base-qualified-name": "django.db.models.query._BaseQuerySet",
        "method-name": "values_list"
      },
      {
        "kind": "on-subclass-of",
        "base-qualified-name": "django.db.models.query.ValuesQuerySet",
        "method-name": "values_list"
      },
      {
        "kind": "on-subclass-of",
        "base-qualified-name": "django.db.models.query._BaseQuerySet",
        "method-name": "annotate"
      },
      {
        "kind": "on-subclass-of",
        "base-qualified-name": "django.db.models.query.ValuesQuerySet",
        "method-name": "annotate"
      },
      {
        "kind": "on-subclass-of",
        "base-qualified-name": "django.db.models.query._BaseQuerySet",
        "method-name": "alias"
      },
      {
        "kind": "on-subclass-of",
        "base-qualified-name": "django.db.models.query.ValuesQuerySet",
        "method-name": "alias"
      },
      {
        "kind": "on-subclass-of",
        "base-qualified-name": "django.db.models.query._BaseQuerySet",
        "method-name": "order_by"
      },
      {
        "kind": "on-subclass-of",
        "base-qualified-name": "django.db.models.query.ValuesQuerySet",
        "method-name": "order_by"
      },
      {
        "kind": "on-subclass-of",
        "base-qualified-name": "django.db.models.query._BaseQuerySet",
        "method-name": "distinct"
      },
      {
        "kind": "on-subclass-of",
        "base-qualified-name": "django.db.models.query.ValuesQuerySet",
        "method-name": "distinct"
      },
      {
        "kind": "on-subclass-of",
        "base-qualified-name": "django.db.models.query._BaseQuerySet",
        "method-name": "none"
      },
      {
        "kind": "on-subclass-of",
        "base-qualified-name": "django.db.models.query.ValuesQuerySet",
        "method-name": "none"
      },
      {
        "kind": "on-subclass-of",
        "base-qualified-name": "django.db.models.query._BaseQuerySet",
        "method-name": "only"
      },
      {
        "kind": "on-subclass-of",
        "base-qualified-name": "django.db.models.query.ValuesQuerySet",
        "method-name": "only"
      },
      {
        "kind": "on-subclass-of",
        "base-qualified-name": "django.db.models.query._BaseQuerySet",
        "method-name": "defer"
      },
      {
        "kind": "on-subclass-of",
        "base-qualified-name": "django.db.models.query.ValuesQuerySet",
        "method-name": "defer"
      },
      {
        "kind": "on-subclass-of",
        "base-qualified-name": "django.db.models.query._BaseQuerySet",
        "method-name": "select_related"
      },
      {
        "kind": "on-subclass-of",
        "base-qualified-name": "django.db.models.query.ValuesQuerySet",
        "method-name": "select_related"
      },
      {
        "kind": "on-subclass-of",
        "base-qualified-name": "django.db.models.query._BaseQuerySet",
        "method-name": "prefetch_related"
      },
      {
        "kind": "on-subclass-of",
        "base-qualified-name": "django.db.models.query.ValuesQuerySet",
        "method-name": "prefetch_related"
      },
      {
        "kind": "on-subclass-of",
        "base-qualified-name": "django.db.models.query._BaseQuerySet",
        "method-name": "select_for_update"
      },
      {
        "kind": "on-subclass-of",
        "base-qualified-name": "django.db.models.query.ValuesQuerySet",
        "method-name": "select_for_update"
      },
      {
        "kind": "on-subclass-of",
        "base-qualified-name": "django.db.models.query._BaseQuerySet",
        "method-name": "reverse"
      },
      {
        "kind": "on-subclass-of",
        "base-qualified-name": "django.db.models.query.ValuesQuerySet",
        "method-name": "reverse"
      },
      {
        "kind": "on-subclass-of",
        "base-qualified-name": "django.db.models.query._BaseQuerySet",
        "method-name": "using"
      },
      {
        "kind": "on-subclass-of",
        "base-qualified-name": "django.db.models.query.ValuesQuerySet",
        "method-name": "using"
      },
      {
        "kind": "on-subclass-of",
        "base-qualified-name": "django.db.models.query._BaseQuerySet",
        "method-name": "union"
      },
      {
        "kind": "on-subclass-of",
        "base-qualified-name": "django.db.models.query.ValuesQuerySet",
        "method-name": "union"
      },
      {
        "kind": "on-subclass-of",
        "base-qualified-name": "django.db.models.query._BaseQuerySet",
        "method-name": "intersection"
      },
      {
        "kind": "on-subclass-of",
        "base-qualified-name": "django.db.models.query.ValuesQuerySet",
        "method-name": "intersection"
      },
      {
        "kind": "on-subclass-of",
        "base-qualified-name": "django.db.models.query._BaseQuerySet",
        "method-name": "difference"
      },
      {
        "kind": "on-subclass-of",
        "base-qualified-name": "django.db.models.query.ValuesQuerySet",
        "method-name": "difference"
      },
      {
        "kind": "on-subclass-of",
        "base-qualified-name": "django.db.models.query._BaseQuerySet",
        "method-name": "aget"
      },
      {
        "kind": "on-subclass-of",
        "base-qualified-name": "django.db.models.query.ValuesQuerySet",
        "method-name": "aget"
      },
      {
        "kind": "on-subclass-of",
        "base-qualified-name": "django.db.models.query._BaseQuerySet",
        "method-name": "acreate"
      },
      {
        "kind": "on-subclass-of",
        "base-qualified-name": "django.db.models.query.ValuesQuerySet",
        "method-name": "acreate"
      },
      {
        "kind": "on-subclass-of",
        "base-qualified-name": "django.db.models.query._BaseQuerySet",
        "method-name": "aget_or_create"
      },
      {
        "kind": "on-subclass-of",
        "base-qualified-name": "django.db.models.query.ValuesQuerySet",
        "method-name": "aget_or_create"
      },
      {
        "kind": "on-subclass-of",
        "base-qualified-name": "django.db.models.query._BaseQuerySet",
        "method-name": "aupdate_or_create"
      },
      {
        "kind": "on-subclass-of",
        "base-qualified-name": "django.db.models.query.ValuesQuerySet",
        "method-name": "aupdate_or_create"
      },
      {
        "kind": "on-subclass-of",
        "base-qualified-name": "django.db.models.query._BaseQuerySet",
        "method-name": "afirst"
      },
      {
        "kind": "on-subclass-of",
        "base-qualified-name": "django.db.models.query.ValuesQuerySet",
        "method-name": "afirst"
      },
      {
        "kind": "on-subclass-of",
        "base-qualified-name": "django.db.models.query._BaseQuerySet",
        "method-name": "alast"
      },
      {
        "kind": "on-subclass-of",
        "base-qualified-name": "django.db.models.query.ValuesQuerySet",
        "method-name": "alast"
      },
      {
        "kind": "on-subclass-of",
        "base-qualified-name": "django.db.models.query._BaseQuerySet",
        "method-name": "acount"
      },
      {
        "kind": "on-subclass-of",
        "base-qualified-name": "django.db.models.query.ValuesQuerySet",
        "method-name": "acount"
      },
      {
        "kind": "on-subclass-of",
        "base-qualified-name": "django.db.models.query._BaseQuerySet",
        "method-name": "aexists"
      },
      {
        "kind": "on-subclass-of",
        "base-qualified-name": "django.db.models.query.ValuesQuerySet",
        "method-name": "aexists"
      }
    ],
    "attributes": [
      {
        "kind": "on-subclass-of",
        "owner-base-qualified-name": "django.db.models.base.Model",
        "scope": "instance"
      },
      {
        "kind": "on-subclass-of",
        "owner-base-qualified-name": "django.db.models.Model",
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
  ],
  "default-config": {
    "companion-project-inputs": {
      "assignment-kinds": [
        "call"
      ],
      "class-source": false,
      "field-call-keywords": [
        "null",
        "default",
        "db_default",
        "primary_key",
        "choices",
        "to",
        "to_field",
        "related_name",
        "related_query_name"
      ],
      "overlay-index": "imports",
      "field-call-argument-source": false
    },
    "companion-early-call-returns": [
      "get"
    ],
    "companion-native-member-abstentions": "native_member_abstentions",
    "companion-native-fields": true,
    "companion-native-call-returns": [
      "get"
    ],
    "companion-call-signature-methods": [
      "from_queryset"
    ],
    "companion-parallel-calls": true
  }
}
""")
