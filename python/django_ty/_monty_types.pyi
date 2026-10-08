"""Static wire schemas for protocol 0.7 / SDK 0.0.8; never loaded by Monty."""

from typing import Literal, TypeAlias, TypedDict

from typing_extensions import NotRequired, Required

JsonValue: TypeAlias = (
    None | bool | int | float | str | list[JsonValue] | dict[str, JsonValue]
)
TypeMode: TypeAlias = Literal["expression", "annotation", "stub"]
PatchMode: TypeAlias = Literal["fill-on-miss", "replace-existing"]
ArgumentKind: TypeAlias = Literal["positional", "keyword", "star-args", "star-kwargs"]
RelationKind: TypeAlias = Literal["foreign-key", "one-to-one", "many-to-many"]

class TextPosition(TypedDict):
    line: int
    column: int

SymbolSource = TypedDict(
    "SymbolSource",
    {
        "module": str,
        "qualified-name": str,
        "file-path": str,
        "start": TextPosition,
        "end": TextPosition,
    },
    total=False,
)
SymbolRef = TypedDict("SymbolRef", {"qualified-name": Required[str]}, total=False)
ImportBinding = TypedDict(
    "ImportBinding", {"module": str, "name": str, "alias": NotRequired[str]}
)
TypeExpr = TypedDict(
    "TypeExpr",
    {
        "expression": str,
        "mode": TypeMode,
        "imports": NotRequired[list[ImportBinding]],
        "snapshot": NotRequired[TypeSnapshot | None],
    },
)
# Snapshots are recursive wire records. Only the fields read or built by this port
# are listed; the host may provide additional structural fields that pass through.
TypeSnapshot = TypedDict(
    "TypeSnapshot",
    {
        "kind": str,
        "expression": str,
        "mode": TypeMode,
        "imports": list[ImportBinding],
        "qualified-name": str,
        "arguments": list[TypeSnapshot],
        "prefix": list[TypeSnapshot],
        "variadic": TypeSnapshot,
        "suffix": list[TypeSnapshot],
    },
    total=False,
)

BoolLiteral = TypedDict("BoolLiteral", {"kind": Literal["bool"], "value": bool})
IntLiteral = TypedDict("IntLiteral", {"kind": Literal["int"], "value": int})
StrLiteral = TypedDict("StrLiteral", {"kind": Literal["str"], "value": str})
SymbolLiteral = TypedDict(
    "SymbolLiteral",
    {"kind": Literal["enum-ref", "symbol-ref", "class-ref"], "qualified-name": str},
)
SequenceLiteral = TypedDict(
    "SequenceLiteral", {"kind": Literal["tuple", "list"], "items": list[LiteralValue]}
)
DictLiteral = TypedDict(
    "DictLiteral", {"kind": Literal["dict"], "entries": list[LiteralDictEntry]}
)
EmptyLiteral = TypedDict("EmptyLiteral", {"kind": Literal["none", "unknown"]})
LiteralValue: TypeAlias = (
    BoolLiteral
    | IntLiteral
    | StrLiteral
    | SymbolLiteral
    | SequenceLiteral
    | DictLiteral
    | EmptyLiteral
)

class LiteralDictEntry(TypedDict):
    key: LiteralValue
    value: LiteralValue

Argument = TypedDict(
    "Argument",
    {
        "kind": Required[ArgumentKind],
        "name": str | None,
        "type-expr": TypeExpr | None,
        "value": LiteralValue,
        "source": SymbolSource | None,
    },
    total=False,
)
Receiver = TypedDict(
    "Receiver",
    {
        "type-expr": Required[TypeExpr],
        "nominal-class": str | None,
        "generic-arguments": list[TypeExpr],
        "plugin-metadata": JsonValue,
    },
    total=False,
)
ValueSummary = TypedDict(
    "ValueSummary", {"symbol": SymbolRef, "type-expr": TypeExpr}, total=False
)
CallSummary = TypedDict(
    "CallSummary",
    {
        "kind": Literal["call", "symbol", "name", "attribute", "literal", "other"],
        "callee": SymbolRef,
        "receiver": ValueSummary,
        "arguments": list[Argument],
        "qualified-name": str,
        "value": LiteralValue,
        "inferred-type": TypeExpr,
    },
    total=False,
)
FieldSummary = TypedDict(
    "FieldSummary",
    {
        "name": Required[str],
        "qualified-name": str,
        "assigned-value": CallSummary,
        "annotation": TypeExpr,
        "inferred-type": TypeExpr,
        "has-default": bool,
        "source": SymbolSource,
    },
    total=False,
)
Parameter = TypedDict(
    "Parameter",
    {
        "kind": Required[
            Literal[
                "positional-only",
                "positional-or-keyword",
                "var-args",
                "keyword-only",
                "kwargs",
            ]
        ],
        "name": str,
        "type-expr": TypeExpr,
        "required": bool,
    },
    total=False,
)
MethodSummary = TypedDict(
    "MethodSummary",
    {
        "name": str,
        "qualified-name": str,
        "decorators": list[CallSummary],
        "parameters": list[Parameter],
        "return-type": TypeExpr,
        "is-public": bool,
        "source": SymbolSource,
    },
    total=False,
)
ConstantSummary = TypedDict(
    "ConstantSummary",
    {"name": str, "value": LiteralValue, "type-expr": TypeExpr, "source": SymbolSource},
    total=False,
)
ClassSummary = TypedDict(
    "ClassSummary",
    {
        "qualified-name": Required[str],
        "name": str,
        "bases": list[TypeExpr],
        "decorators": list[CallSummary],
        "fields": list[FieldSummary],
        "methods": list[MethodSummary],
        "nested-classes": list[ClassSummary],
        "class-constants": list[ConstantSummary],
        "source": SymbolSource,
    },
    total=False,
)
Dependency = TypedDict("Dependency", {"path": str, "sha256": NotRequired[str]})
SettingsModule = TypedDict(
    "SettingsModule",
    {
        "module": Required[str],
        "values": list[ConstantSummary],
        "dependencies": list[Dependency],
    },
    total=False,
)
Context = TypedDict(
    "Context",
    {
        "root": str,
        "module": str,
        "file-path": str,
        "python-version": str,
        "platform": str,
        "config": dict[str, JsonValue],
        "speculative": bool,
    },
    total=False,
)
ProjectIndexRequest = TypedDict(
    "ProjectIndexRequest",
    {
        "context": Context,
        "classes": list[ClassSummary],
        "settings": list[SettingsModule],
        "assignments": list[FieldSummary],
        "functions": list[MethodSummary],
    },
    total=False,
)
ClassRequest = TypedDict(
    "ClassRequest",
    {"class": Required[ClassSummary], "context": Context, "project-index": DjangoIndex},
    total=False,
)
CallRequest = TypedDict(
    "CallRequest",
    {
        "callee": Required[TypeExpr],
        "context": Context,
        "project-index": DjangoIndex,
        "receiver": Receiver,
        "arguments": list[Argument],
        "default-return-type": TypeExpr,
    },
    total=False,
)
MutationRequest = TypedDict(
    "MutationRequest",
    {
        "context": Context,
        "operation": Literal[
            "attribute-set", "item-set", "attribute-delete", "item-delete"
        ],
        "receiver": TypeExpr,
        "source": SymbolSource,
    },
    total=False,
)
IndexedRequest: TypeAlias = ClassRequest | CallRequest

class FieldData(TypedDict):
    name: str
    get: TypeExpr
    set: TypeExpr
    nullable: bool
    default: bool
    relation: RelationKind | None
    target: str | None

class LocalModelIndex(TypedDict):
    fields: dict[str, str]
    field_types: dict[str, str]
    auto_primary_key: str | None
    auto_primary_key_default: str | None
    custom_primary_key: bool
    multi_table: bool
    custom_loading: bool
    custom_save: bool

class ModelIndex(TypedDict):
    fields: dict[str, str]
    field_types: dict[str, str]
    manager_queryset: str | None
    auto_primary_key: str | None
    auto_primary_key_default: str | None
    custom_loading: bool
    custom_save: bool
    signal_receivers: bool
    query_fields: NotRequired[dict[str, str]]

class DjangoIndex(TypedDict, total=False):
    models: dict[str, ModelIndex]
    settings: dict[str, str]
    auth_user_model: str | None

Location = TypedDict(
    "Location", {"file-path": str, "start": TextPosition, "end": TextPosition}
)
Diagnostic = TypedDict(
    "Diagnostic",
    {
        "id": str,
        "message": str,
        "severity": Literal["error", "warning", "info"],
        "location": NotRequired[Location],
        "metadata": NotRequired[dict[str, JsonValue]],
    },
)
CallableSignature = TypedDict(
    "CallableSignature",
    {"return-type": TypeExpr, "parameters": NotRequired[list[Parameter]]},
)
MemberAccess = TypedDict(
    "MemberAccess",
    {
        "kind": str,
        "type-expr": TypeExpr,
        "instance-get-type": TypeExpr,
        "instance-set-type": TypeExpr,
        "class-type": TypeExpr,
        "signature": CallableSignature,
        "fallback-type": TypeExpr,
    },
    total=False,
)
MemberPatch = TypedDict(
    "MemberPatch",
    {
        "name": str,
        "mode": PatchMode,
        "access": MemberAccess,
        "read-only": bool,
        "diagnostics": NotRequired[list[Diagnostic]],
    },
)
FieldPatch = TypedDict(
    "FieldPatch",
    {
        "name": str,
        "mode": PatchMode,
        "instance-get-type": TypeExpr,
        "has-default": bool,
        "descriptor": NotRequired[MemberAccess],
        "instance-set-type": NotRequired[TypeExpr],
        "constructor-parameter": NotRequired[Parameter],
    },
)
ContributionTarget = TypedDict(
    "ContributionTarget", {"kind": Literal["class", "instance"], "qualified-name": str}
)
# Contribution patches flatten their underlying field/member record on the wire.
ContributionPatch = TypedDict(
    "ContributionPatch",
    {
        "kind": Literal["member", "field"],
        "name": str,
        "mode": PatchMode,
        "access": MemberAccess,
        "read-only": bool,
        "instance-get-type": TypeExpr,
        "has-default": bool,
        "descriptor": MemberAccess,
        "instance-set-type": TypeExpr,
        "constructor-parameter": Parameter,
    },
    total=False,
)
Contribution = TypedDict(
    "Contribution",
    {
        "source": SymbolSource,
        "target": ContributionTarget,
        "patch": ContributionPatch,
        "conflict-key": str,
        "diagnostics": NotRequired[list[Diagnostic]],
    },
)
VirtualField = TypedDict(
    "VirtualField",
    {"name": str, "type-expr": TypeExpr, "required": bool, "read-only": bool},
)
VirtualShape = TypedDict(
    "VirtualShape",
    {
        "kind": Literal["class", "typed-dict", "named-tuple"],
        "bases": list[TypeExpr],
        "members": list[MemberPatch],
        "fields": list[VirtualField],
        "total": bool,
    },
    total=False,
)

class VirtualType(TypedDict):
    name: str
    shape: VirtualShape
    metadata: NotRequired[dict[str, JsonValue]]

ProjectIndexResponse = TypedDict(
    "ProjectIndexResponse",
    {
        "kind": Literal["project-index"],
        "plugin-index": DjangoIndex,
        "contributions": NotRequired[list[Contribution]],
        "virtual-types": NotRequired[list[VirtualType]],
        "dependencies": NotRequired[list[Dependency]],
        "diagnostics": NotRequired[list[Diagnostic]],
    },
)
ClassResponse = TypedDict(
    "ClassResponse",
    {
        "kind": Required[Literal["class-patch"]],
        "fields": list[FieldPatch],
        "class-members": list[MemberPatch],
        "instance-members": list[MemberPatch],
        "constructor": CallableSignature,
        "diagnostics": list[Diagnostic],
    },
    total=False,
)
CallReturnResponse = TypedDict(
    "CallReturnResponse",
    {
        "kind": Literal["call-return-patch"],
        "return-type": TypeExpr,
        "result-metadata": NotRequired[dict[str, JsonValue]],
        "diagnostics": NotRequired[list[Diagnostic]],
    },
)
CallSignatureResponse = TypedDict(
    "CallSignatureResponse",
    {
        "kind": Literal["call-signature-patch"],
        "signature": CallableSignature,
        "diagnostics": NotRequired[list[Diagnostic]],
    },
)
CallStateResponse = TypedDict(
    "CallStateResponse",
    {
        "kind": Literal["call-state-patch"],
        "receiver-members": dict[str, TypeExpr],
        "result-members": dict[str, TypeExpr],
        "fresh-result": bool,
        "preserves-other-objects": bool,
    },
)
MutationResponse = TypedDict(
    "MutationResponse",
    {"kind": Literal["mutation-diagnostics"], "diagnostics": list[Diagnostic]},
)
