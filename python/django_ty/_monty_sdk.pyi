"""Precise declarations for the ambient SDK builders used by this plugin.

Runtime implementations are ty.plugin_sdk (0.0.8). This stub refines its
broad JSON aliases without adding runtime imports or changing the checker SDK.
"""

from collections.abc import Callable
from typing import Literal

from ._monty_types import (
    CallableSignature,
    CallRequest,
    CallReturnResponse,
    CallSignatureResponse,
    CallStateResponse,
    ClassRequest,
    ClassResponse,
    Contribution,
    ContributionPatch,
    ContributionTarget,
    Dependency,
    Diagnostic,
    DjangoIndex,
    FieldPatch,
    ImportBinding,
    JsonValue,
    Location,
    MemberAccess,
    MemberPatch,
    MutationRequest,
    MutationResponse,
    Parameter,
    PatchMode,
    ProjectIndexRequest,
    ProjectIndexResponse,
    SymbolSource,
    TextPosition,
    TypeExpr,
    TypeMode,
    TypeSnapshot,
    VirtualField,
    VirtualShape,
    VirtualType,
)

def on_project_index(
    fn: Callable[[ProjectIndexRequest], ProjectIndexResponse],
) -> Callable[[ProjectIndexRequest], ProjectIndexResponse]: ...
def on_class_transform(
    fn: Callable[[ClassRequest], ClassResponse | None],
) -> Callable[[ClassRequest], ClassResponse | None]: ...
def on_call_return(
    fn: Callable[[CallRequest], CallReturnResponse | None],
) -> Callable[[CallRequest], CallReturnResponse | None]: ...
def on_call_signature(
    fn: Callable[[CallRequest], CallSignatureResponse | None],
) -> Callable[[CallRequest], CallSignatureResponse | None]: ...
def on_call_state(
    fn: Callable[[CallRequest], CallStateResponse | None],
) -> Callable[[CallRequest], CallStateResponse | None]: ...
def on_mutation(
    fn: Callable[[MutationRequest], MutationResponse | None],
) -> Callable[[MutationRequest], MutationResponse | None]: ...
def type_expr(
    expression: str,
    mode: TypeMode = ...,
    imports: list[ImportBinding] | None = ...,
    snapshot: TypeSnapshot | None = ...,
) -> TypeExpr: ...
def type_annotation(
    expression: str,
    imports: list[ImportBinding] | None = ...,
    snapshot: TypeSnapshot | None = ...,
) -> TypeExpr: ...
def import_binding(
    module: str, name: str, alias: str | None = ...
) -> ImportBinding: ...
def snapshot_expression(
    expression: str, mode: TypeMode = ..., imports: list[ImportBinding] | None = ...
) -> TypeSnapshot: ...
def snapshot_nominal(
    qualified_name: str, arguments: list[TypeSnapshot] | None = ...
) -> TypeSnapshot: ...
def snapshot_tuple(
    prefix: list[TypeSnapshot] | None = ...,
    variadic: TypeSnapshot | None = ...,
    suffix: list[TypeSnapshot] | None = ...,
) -> TypeSnapshot: ...
def member(
    name: str,
    type: TypeExpr,
    mode: PatchMode = ...,
    read_only: bool = ...,
    diagnostics: list[Diagnostic] | None = ...,
) -> MemberPatch: ...
def callable_member(
    name: str,
    signature: CallableSignature,
    fallback_type: TypeExpr,
    mode: PatchMode = ...,
    read_only: bool = ...,
    diagnostics: list[Diagnostic] | None = ...,
) -> MemberPatch: ...
def member_descriptor(
    instance_get_type: TypeExpr,
    class_type: TypeExpr | None = ...,
    instance_set_type: TypeExpr | None = ...,
) -> MemberAccess: ...
def field_patch(
    name: str,
    instance_get_type: TypeExpr,
    mode: PatchMode = ...,
    descriptor: MemberAccess | None = ...,
    instance_set_type: TypeExpr | None = ...,
    constructor_parameter: Parameter | None = ...,
    has_default: bool = ...,
) -> FieldPatch: ...
def callable_signature(
    parameters: list[Parameter] | None = ..., return_type: TypeExpr | None = ...
) -> CallableSignature: ...
def positional_or_keyword(
    name: str, type: TypeExpr, required: bool = ...
) -> Parameter: ...
def keyword_only(name: str, type: TypeExpr, required: bool = ...) -> Parameter: ...
def optional(
    name: str,
    type: TypeExpr,
    kind: Literal["positional-only", "positional-or-keyword", "keyword-only"] = ...,
) -> Parameter: ...
def location(file_path: str, start: TextPosition, end: TextPosition) -> Location: ...
def diagnostic(
    id: str,
    message: str,
    severity: Literal["error", "warning", "info"] = ...,
    location: Location | None = ...,
    metadata: dict[str, JsonValue] | None = ...,
) -> Diagnostic: ...
def class_target(qualified_name: str) -> ContributionTarget: ...
def instance_target(qualified_name: str) -> ContributionTarget: ...
def member_contribution(patch: MemberPatch) -> ContributionPatch: ...
def field_contribution(patch: FieldPatch) -> ContributionPatch: ...
def contribution(
    source: SymbolSource,
    target: ContributionTarget,
    patch: ContributionPatch,
    conflict_key: str,
    diagnostics: list[Diagnostic] | None = ...,
) -> Contribution: ...
def virtual_field(
    name: str, type: TypeExpr, required: bool = ..., read_only: bool = ...
) -> VirtualField: ...
def virtual_class(
    bases: list[TypeExpr] | None = ..., members: list[MemberPatch] | None = ...
) -> VirtualShape: ...
def virtual_typed_dict(
    fields: list[VirtualField] | None = ..., total: bool = ...
) -> VirtualShape: ...
def virtual_named_tuple(fields: list[VirtualField] | None = ...) -> VirtualShape: ...
def virtual_type(
    name: str, shape: VirtualShape, metadata: dict[str, JsonValue] | None = ...
) -> VirtualType: ...
def project_index(
    plugin_index: DjangoIndex | None = ...,
    contributions: list[Contribution] | None = ...,
    virtual_types: list[VirtualType] | None = ...,
    dependencies: list[Dependency] | None = ...,
    diagnostics: list[Diagnostic] | None = ...,
) -> ProjectIndexResponse: ...
def class_patch(
    fields: list[FieldPatch] | None = ...,
    class_members: list[MemberPatch] | None = ...,
    instance_members: list[MemberPatch] | None = ...,
    constructor: CallableSignature | None = ...,
    diagnostics: list[Diagnostic] | None = ...,
) -> ClassResponse: ...
def call_return_patch(
    return_type: TypeExpr,
    diagnostics: list[Diagnostic] | None = ...,
    result_metadata: dict[str, JsonValue] | None = ...,
) -> CallReturnResponse: ...
def call_signature_patch(
    signature: CallableSignature, diagnostics: list[Diagnostic] | None = ...
) -> CallSignatureResponse: ...
def call_state_patch(
    receiver_members: dict[str, TypeExpr] | None = ...,
    result_members: dict[str, TypeExpr] | None = ...,
    *,
    fresh_result: bool = ...,
    preserves_other_objects: bool = ...,
) -> CallStateResponse: ...
def mutation_diagnostics(items: list[Diagnostic]) -> MutationResponse: ...
def set_manifest(manifest_dict: dict[str, JsonValue]) -> None: ...
