use ty_plugin_sdk::protocol::{
    ArgumentKind, ArgumentSummary, CallRequest, CallReturnPatch, LiteralValue, PluginDiagnostic,
    PluginResponse, TypeExpr, TypeSnapshot,
};
use ty_plugin_sdk::serde_json::{Value, json};

use crate::constants::{FIELD_NAME_METHODS, LOOKUP_METHODS, QUERYSET_RETURNING_METHODS};
use crate::diagnostics::{invalid_lookup_value, unknown_lookup};
use crate::types::{
    annotation, queryset_type, type_snapshot, values_list_row_virtual_type_name,
    values_row_virtual_type_name,
};

pub fn adjust_queryset_return(request: &CallRequest, method_name: &str) -> PluginResponse {
    let Some(receiver) = &request.receiver else {
        return PluginResponse::NoChange;
    };
    let Some(model_type) = receiver.generic_arguments.first().cloned() else {
        return PluginResponse::NoChange;
    };
    let receiver_is_queryset = receiver
        .nominal_class
        .as_deref()
        .is_some_and(|name| name.ends_with("QuerySet"));
    let row_type = if receiver_is_queryset {
        receiver
            .generic_arguments
            .get(1)
            .cloned()
            .unwrap_or_else(|| model_type.clone())
    } else {
        model_type.clone()
    };
    let diagnostics = validate_call_arguments(method_name, &model_type.expression, request);

    if method_name == "prefetch_related"
        && let Some(prefetched_row) = prefetched_row_type(request, &row_type)
    {
        return call_return(queryset_type(&model_type, &prefetched_row), diagnostics);
    }

    if QUERYSET_RETURNING_METHODS.contains(&method_name) {
        if matches!(
            receiver.type_expr.snapshot.as_deref(),
            Some(TypeSnapshot::SelfType { .. })
        ) {
            return call_return(receiver.type_expr.clone(), diagnostics);
        }
        if receiver_is_queryset
            && receiver
                .nominal_class
                .as_deref()
                .is_some_and(|name| name != crate::constants::QUERYSET_BASE)
            && !receiver.type_expr.expression.contains("django_ty.virtual.")
        {
            return PluginResponse::NoChange;
        }
        let return_type = if receiver_is_queryset {
            receiver.type_expr.clone()
        } else {
            queryset_type(&model_type, &row_type)
        };
        return call_return(return_type, diagnostics);
    }

    match method_name {
        "get" => call_return(
            row_or_model(receiver_is_queryset, &model_type, &row_type),
            diagnostics,
        ),
        "create" => call_return(model_type, diagnostics),
        "bulk_create" => call_return(
            annotation(format!("list[{}]", model_type.expression)),
            diagnostics,
        ),
        "bulk_update" => call_return(annotation("int"), diagnostics),
        "get_or_create" | "update_or_create" => call_return(
            annotation(format!("tuple[{}, bool]", model_type.expression)),
            diagnostics,
        ),
        "first" | "last" => call_return(
            annotation(format!(
                "{} | None",
                row_or_model(receiver_is_queryset, &model_type, &row_type).expression
            )),
            diagnostics,
        ),
        "earliest" | "latest" => call_return(
            row_or_model(receiver_is_queryset, &model_type, &row_type),
            diagnostics,
        ),
        "count" => call_return(annotation("int"), diagnostics),
        "exists" => call_return(annotation("bool"), diagnostics),
        "values" => call_return(
            queryset_type(
                &model_type,
                &values_row_type(request, &model_type.expression)
                    .unwrap_or_else(|| annotation("dict[str, object]")),
            ),
            diagnostics,
        ),
        "values_list" => {
            let Some(row_type) =
                values_list_row_type(request, &model_type.expression, diagnostics.is_empty())
            else {
                return PluginResponse::NoChange;
            };
            call_return(queryset_type(&model_type, &row_type), diagnostics)
        }
        "annotate" => {
            let annotated_row = annotated_row_type(request, &row_type).unwrap_or(row_type);
            call_return(queryset_type(&model_type, &annotated_row), diagnostics)
        }
        "aget" => async_call(
            row_or_model(receiver_is_queryset, &model_type, &row_type),
            diagnostics,
        ),
        "acreate" => async_call(model_type, diagnostics),
        "aget_or_create" | "aupdate_or_create" => async_call(
            annotation(format!("tuple[{}, bool]", model_type.expression)),
            diagnostics,
        ),
        "afirst" | "alast" => async_call(
            annotation(format!(
                "{} | None",
                row_or_model(receiver_is_queryset, &model_type, &row_type).expression
            )),
            diagnostics,
        ),
        "acount" => async_call(annotation("int"), diagnostics),
        "aexists" => async_call(annotation("bool"), diagnostics),
        _ => PluginResponse::NoChange,
    }
}

pub fn adjust_model_method(request: &CallRequest, method_name: &str) -> PluginResponse {
    let Some(receiver) = &request.receiver else {
        return PluginResponse::NoChange;
    };
    let model_name = receiver
        .nominal_class
        .as_deref()
        .unwrap_or(receiver.type_expr.expression.as_str());
    if model_fields(request, model_name).is_none() {
        return PluginResponse::NoChange;
    }
    let diagnostics = if method_name == "save" {
        validate_update_fields_argument(model_name, request)
    } else {
        Vec::new()
    };
    call_return(
        request
            .default_return_type
            .clone()
            .unwrap_or_else(|| annotation("None")),
        diagnostics,
    )
}

pub fn adjust_options_get_field(request: &CallRequest) -> PluginResponse {
    let Some(receiver) = &request.receiver else {
        return PluginResponse::NoChange;
    };
    let Some(model_name) = receiver
        .generic_arguments
        .first()
        .map(|ty| ty.expression.as_str())
    else {
        return PluginResponse::NoChange;
    };
    let Some(argument) = request
        .arguments
        .iter()
        .find(|argument| argument.kind == ArgumentKind::Positional)
    else {
        return PluginResponse::NoChange;
    };
    let LiteralValue::Str { value: field_name } = &argument.value else {
        return PluginResponse::NoChange;
    };
    let Some(field_types) = model_field_types(request, model_name) else {
        return PluginResponse::NoChange;
    };
    let Some(field_type) = field_types.get(field_name).and_then(Value::as_str) else {
        return call_return(
            request.default_return_type.clone().unwrap_or_else(|| {
                annotation("django.db.models.fields.Field[typing.Any, typing.Any]")
            }),
            vec![unknown_lookup(model_name, field_name, argument)],
        );
    };
    call_return(annotation(field_type.to_string()), Vec::new())
}

fn row_or_model(
    receiver_is_queryset: bool,
    model_type: &TypeExpr,
    row_type: &TypeExpr,
) -> TypeExpr {
    if receiver_is_queryset {
        row_type.clone()
    } else {
        model_type.clone()
    }
}

fn call_return(return_type: TypeExpr, diagnostics: Vec<PluginDiagnostic>) -> PluginResponse {
    PluginResponse::CallReturnPatch(CallReturnPatch {
        return_type,
        diagnostics,
        result_metadata: None,
    })
}

fn async_call(return_type: TypeExpr, diagnostics: Vec<PluginDiagnostic>) -> PluginResponse {
    let mut coroutine = annotation(format!(
        "typing.Coroutine[object, object, {}]",
        return_type.expression
    ));
    coroutine.imports.extend(return_type.imports);
    call_return(coroutine, diagnostics)
}

fn annotated_row_type(request: &CallRequest, base_row_type: &TypeExpr) -> Option<TypeExpr> {
    let entries = request
        .arguments
        .iter()
        .filter(|argument| argument.kind == ArgumentKind::Keyword)
        .filter_map(|argument| {
            let name = argument.name.as_deref()?;
            let key = ty_plugin_sdk::serde_json::to_string(name).ok()?;
            Some(format!("{key}: {}", argument_type(argument).expression))
        })
        .collect::<Vec<_>>();
    if entries.is_empty() {
        None
    } else {
        Some(annotation(format!(
            r#"Class("DjangoTyAnnotatedRow", {{{}}}, {})"#,
            entries.join(", "),
            base_row_type.expression
        )))
    }
}

fn prefetched_row_type(request: &CallRequest, base_row_type: &TypeExpr) -> Option<TypeExpr> {
    let entries = request
        .arguments
        .iter()
        .filter_map(|argument| argument.type_expr.as_ref())
        .filter_map(|ty| prefetch_annotation(request, &ty.expression))
        .map(|(name, row_type)| format!("{}: list[{row_type}]", json!(name)))
        .collect::<Vec<_>>();
    if entries.is_empty() {
        None
    } else {
        Some(annotation(format!(
            r#"Class("DjangoTyPrefetchedRow", {{{}}}, {})"#,
            entries.join(", "),
            base_row_type.expression
        )))
    }
}

fn prefetch_annotation<'a>(
    request: &CallRequest,
    expression: &'a str,
) -> Option<(&'a str, String)> {
    let arguments = generic_arguments(expression, "Prefetch")?;
    let [_, queryset, to_attr] = arguments.as_slice() else {
        return None;
    };
    let queryset_arguments = generic_arguments(queryset, "QuerySet")?;
    let row_type = queryset_arguments.last()?.trim();
    let to_attr = to_attr
        .trim()
        .strip_prefix("Literal[\"")?
        .strip_suffix("\"]")?;
    Some((to_attr, qualified_model_name(request, row_type)))
}

fn qualified_model_name(request: &CallRequest, model_name: &str) -> String {
    let Some(models) = request
        .project_index
        .as_ref()
        .and_then(|index| index.get("models"))
        .and_then(Value::as_object)
    else {
        return model_name.to_string();
    };
    if models.contains_key(model_name) {
        return model_name.to_string();
    }
    let mut matches = models
        .keys()
        .filter(|candidate| candidate.rsplit('.').next() == Some(model_name));
    let Some(qualified_name) = matches.next() else {
        return model_name.to_string();
    };
    if matches.next().is_some() {
        model_name.to_string()
    } else {
        qualified_name.clone()
    }
}

fn generic_arguments<'a>(expression: &'a str, origin: &str) -> Option<Vec<&'a str>> {
    let arguments = expression
        .trim()
        .strip_prefix(origin)?
        .strip_prefix('[')?
        .strip_suffix(']')?;
    let mut parts = Vec::new();
    let mut start = 0;
    let mut depth = 0_u32;
    let mut quoted = false;
    for (index, character) in arguments.char_indices() {
        match character {
            '"' => quoted = !quoted,
            '[' | '(' | '{' if !quoted => depth += 1,
            ']' | ')' | '}' if !quoted => depth = depth.saturating_sub(1),
            ',' if depth == 0 && !quoted => {
                parts.push(arguments[start..index].trim());
                start = index + character.len_utf8();
            }
            _ => {}
        }
    }
    parts.push(arguments[start..].trim());
    Some(parts)
}

fn argument_type(argument: &ArgumentSummary) -> TypeExpr {
    argument
        .type_expr
        .clone()
        .unwrap_or_else(|| match &argument.value {
            LiteralValue::Bool { .. } => annotation("bool"),
            LiteralValue::Int { .. } => annotation("int"),
            LiteralValue::Str { .. } => annotation("str"),
            LiteralValue::None => annotation("None"),
            _ => annotation("object"),
        })
}

fn values_row_type(request: &CallRequest, model_name: &str) -> Option<TypeExpr> {
    let fields = model_fields(request, model_name)?;
    let field_names = positional_string_arguments(request);
    if field_names.is_empty() {
        return Some(annotation(values_row_virtual_type_name(model_name)));
    }
    let entries = field_names
        .into_iter()
        .map(|field_name| {
            let field_type = fields
                .get(field_name)
                .and_then(Value::as_str)
                .unwrap_or("object");
            format!("{}: {field_type}", json!(field_name))
        })
        .collect::<Vec<_>>();
    Some(annotation(format!("TypedDict({{{}}})", entries.join(", "))))
}

fn values_list_row_type(
    request: &CallRequest,
    model_name: &str,
    lookups_are_valid: bool,
) -> Option<TypeExpr> {
    let field_names = positional_string_arguments(request);
    if bool_keyword_argument(&request.arguments, "flat") == Some(true)
        && bool_keyword_argument(&request.arguments, "named") == Some(true)
    {
        return None;
    }
    if bool_keyword_argument(&request.arguments, "named") == Some(true) {
        if field_names.is_empty() {
            model_fields(request, model_name)?;
            return Some(annotation(values_list_row_virtual_type_name(model_name)));
        }
        return named_tuple_row_type(request, model_name, &field_names);
    }
    if field_names.is_empty() {
        if bool_keyword_argument(&request.arguments, "flat") == Some(true) {
            return None;
        }
        let fields = model_fields(request, model_name)?;
        let row_types = fields
            .iter()
            .map(|(_, field_type)| annotation(field_type.as_str().unwrap_or("object").to_string()))
            .collect::<Vec<_>>();
        return Some(tuple_type(row_types));
    }
    if bool_keyword_argument(&request.arguments, "flat") == Some(true) {
        return Some(
            field_type_for_name(request, model_name, field_names[0])
                .unwrap_or_else(|| annotation("object")),
        );
    }
    if !lookups_are_valid {
        return Some(annotation("tuple[object, ...]"));
    }
    let row_types = field_names
        .into_iter()
        .map(|field_name| {
            field_type_for_name(request, model_name, field_name)
                .unwrap_or_else(|| annotation("object"))
        })
        .collect::<Vec<_>>();
    Some(tuple_type(row_types))
}

fn tuple_type(elements: Vec<TypeExpr>) -> TypeExpr {
    let mut tuple = annotation(format!(
        "tuple[{}]",
        elements
            .iter()
            .map(|element| element.expression.as_str())
            .collect::<Vec<_>>()
            .join(", ")
    ));
    tuple.imports = elements
        .iter()
        .flat_map(|element| element.imports.iter().cloned())
        .collect();
    tuple.imports.sort_by(|left, right| {
        (&left.module, &left.name, &left.alias).cmp(&(&right.module, &right.name, &right.alias))
    });
    tuple.imports.dedup();
    tuple.snapshot = Some(Box::new(ty_plugin_sdk::protocol::TypeSnapshot::Tuple {
        prefix: elements.iter().map(type_snapshot).collect(),
        variadic: None,
        suffix: Vec::new(),
    }));
    tuple
}

fn named_tuple_row_type(
    request: &CallRequest,
    model_name: &str,
    field_names: &[&str],
) -> Option<TypeExpr> {
    let fields = model_fields(request, model_name)?;
    let entries = field_names
        .iter()
        .map(|field_name| {
            let field_type = fields
                .get(*field_name)
                .and_then(Value::as_str)
                .unwrap_or("object");
            format!("{}: {field_type}", json!(field_name))
        })
        .collect::<Vec<_>>();
    Some(annotation(format!(
        r#"NamedTuple("DjangoTyValuesListRow", {{{}}})"#,
        entries.join(", ")
    )))
}

fn validate_call_arguments(
    method_name: &str,
    model_name: &str,
    request: &CallRequest,
) -> Vec<PluginDiagnostic> {
    if model_fields(request, model_name).is_none() {
        return Vec::new();
    }
    if LOOKUP_METHODS.contains(&method_name) {
        let mut diagnostics = request
            .arguments
            .iter()
            .filter(|argument| argument.kind == ArgumentKind::Keyword)
            .filter(|argument| !is_creation_defaults_argument(method_name, argument))
            .filter_map(|argument| validate_lookup_argument(model_name, request, argument))
            .collect::<Vec<_>>();
        diagnostics.extend(
            request
                .arguments
                .iter()
                .filter(|argument| is_creation_defaults_argument(method_name, argument))
                .flat_map(|argument| validate_defaults_argument(model_name, request, argument)),
        );
        return diagnostics;
    }
    if matches!(method_name, "create" | "acreate") {
        return request
            .arguments
            .iter()
            .filter(|argument| argument.kind == ArgumentKind::Keyword)
            .filter_map(|argument| validate_model_field_argument(model_name, request, argument))
            .collect();
    }
    if matches!(method_name, "values" | "values_list") {
        return request
            .arguments
            .iter()
            .filter(|argument| argument.kind == ArgumentKind::Positional)
            .filter_map(|argument| validate_field_name_argument(model_name, request, argument))
            .collect();
    }
    if FIELD_NAME_METHODS.contains(&method_name) {
        return request
            .arguments
            .iter()
            .filter(|argument| argument.kind == ArgumentKind::Positional)
            .filter_map(|argument| {
                validate_field_name_argument_for_method(model_name, request, method_name, argument)
            })
            .collect();
    }
    if method_name == "bulk_update" {
        return request
            .arguments
            .iter()
            .enumerate()
            .filter(|(index, argument)| {
                argument.name.as_deref() == Some("fields")
                    || (argument.name.is_none() && *index == 1)
            })
            .map(|(_, argument)| argument)
            .flat_map(|argument| validate_field_name_collection(model_name, request, argument))
            .collect();
    }
    Vec::new()
}

fn is_creation_defaults_argument(method_name: &str, argument: &ArgumentSummary) -> bool {
    match argument.name.as_deref() {
        Some("defaults") => matches!(
            method_name,
            "get_or_create" | "update_or_create" | "aget_or_create" | "aupdate_or_create"
        ),
        Some("create_defaults") => matches!(method_name, "update_or_create" | "aupdate_or_create"),
        _ => false,
    }
}

fn validate_lookup_argument(
    model_name: &str,
    request: &CallRequest,
    argument: &ArgumentSummary,
) -> Option<PluginDiagnostic> {
    let lookup = argument.name.as_deref()?;
    let Some((field_name, field_type, terminal_lookup)) =
        lookup_field_type(request, model_name, lookup)
    else {
        return Some(unknown_lookup(model_name, lookup, argument));
    };
    if lookup_value_is_compatible(field_type, terminal_lookup, argument) {
        None
    } else {
        Some(invalid_lookup_value(
            model_name, field_name, lookup, field_type, argument,
        ))
    }
}

fn validate_model_field_argument(
    model_name: &str,
    request: &CallRequest,
    argument: &ArgumentSummary,
) -> Option<PluginDiagnostic> {
    let field_name = argument.name.as_deref()?;
    let Some(field_type) = model_fields(request, model_name)?
        .get(field_name)
        .and_then(Value::as_str)
    else {
        return Some(unknown_lookup(model_name, field_name, argument));
    };
    if argument_value_matches_field_type(field_type, argument) {
        None
    } else {
        Some(invalid_lookup_value(
            model_name, field_name, field_name, field_type, argument,
        ))
    }
}

fn validate_defaults_argument(
    model_name: &str,
    request: &CallRequest,
    argument: &ArgumentSummary,
) -> Vec<PluginDiagnostic> {
    let LiteralValue::Dict { entries } = &argument.value else {
        return Vec::new();
    };
    let value_type = argument
        .type_expr
        .as_ref()
        .and_then(|ty| mapping_value_type(&ty.expression));
    entries
        .iter()
        .filter_map(|entry| {
            let LiteralValue::Str { value: field_name } = &entry.key else {
                return None;
            };
            let nested = ArgumentSummary {
                name: Some(field_name.clone()),
                kind: ArgumentKind::Keyword,
                type_expr: value_type.clone().map(TypeExpr::annotation),
                value: entry.value.clone(),
                source: argument.source.clone(),
            };
            validate_model_field_argument(model_name, request, &nested)
        })
        .collect()
}

fn mapping_value_type(expression: &str) -> Option<String> {
    let arguments = expression.split_once('[')?.1.strip_suffix(']')?;
    let (_, value) = arguments.split_once(',')?;
    Some(value.trim().to_string())
}

fn validate_field_name_argument(
    model_name: &str,
    request: &CallRequest,
    argument: &ArgumentSummary,
) -> Option<PluginDiagnostic> {
    let fields = model_fields(request, model_name)?;
    let LiteralValue::Str { value } = &argument.value else {
        return None;
    };
    if fields.contains_key(value) {
        None
    } else {
        Some(unknown_lookup(model_name, value, argument))
    }
}

fn validate_field_name_argument_for_method(
    model_name: &str,
    request: &CallRequest,
    method_name: &str,
    argument: &ArgumentSummary,
) -> Option<PluginDiagnostic> {
    let LiteralValue::Str { value } = &argument.value else {
        return None;
    };
    let value = value.strip_prefix('-').unwrap_or(value);
    if method_name == "order_by" && value == "?" {
        return None;
    }
    if method_name == "order_by" && row_type_has_member(request, value) {
        return None;
    }
    if let Some((_, field_type, terminal_lookup)) = lookup_field_type(request, model_name, value) {
        let valid = match method_name {
            "order_by" => terminal_lookup
                .is_none_or(|lookup| matches!(lookup, "year" | "month" | "day" | "date")),
            "select_related" => {
                terminal_lookup.is_none() && related_model_name(request, field_type).is_some()
            }
            _ => terminal_lookup.is_none(),
        };
        if valid {
            return None;
        }
    }
    let candidate = ArgumentSummary {
        value: LiteralValue::Str {
            value: value.to_string(),
        },
        ..argument.clone()
    };
    validate_field_name_argument(model_name, request, &candidate)
}

fn row_type_has_member(request: &CallRequest, member_name: &str) -> bool {
    let Some(row_type) = request
        .receiver
        .as_ref()
        .and_then(|receiver| receiver.generic_arguments.get(1))
    else {
        return false;
    };
    row_type
        .expression
        .contains(&format!("{}:", json!(member_name)))
}

fn validate_field_name_collection(
    model_name: &str,
    request: &CallRequest,
    argument: &ArgumentSummary,
) -> Vec<PluginDiagnostic> {
    let items = match &argument.value {
        LiteralValue::List { items } | LiteralValue::Tuple { items } => items,
        _ => return Vec::new(),
    };
    items
        .iter()
        .filter_map(|item| {
            let candidate = ArgumentSummary {
                name: None,
                kind: ArgumentKind::Positional,
                type_expr: None,
                value: item.clone(),
                source: argument.source.clone(),
            };
            validate_field_name_argument(model_name, request, &candidate)
        })
        .collect()
}

fn validate_update_fields_argument(
    model_name: &str,
    request: &CallRequest,
) -> Vec<PluginDiagnostic> {
    request
        .arguments
        .iter()
        .filter(|argument| argument.name.as_deref() == Some("update_fields"))
        .flat_map(|argument| validate_field_name_collection(model_name, request, argument))
        .collect()
}

fn lookup_field_type<'a>(
    request: &'a CallRequest,
    model_name: &str,
    lookup: &'a str,
) -> Option<(&'a str, &'a str, Option<&'a str>)> {
    let parts = lookup.split("__").collect::<Vec<_>>();
    if parts.is_empty() || parts.iter().any(|part| part.is_empty()) {
        return None;
    }
    let (path, terminal_lookup) = if parts
        .last()
        .is_some_and(|lookup_name| terminal_lookup_is_supported(lookup_name))
    {
        (&parts[..parts.len() - 1], parts.last().copied())
    } else {
        (parts.as_slice(), None)
    };
    field_path_type(request, model_name, path)
        .map(|(field_name, field_type)| (field_name, field_type, terminal_lookup))
}

fn terminal_lookup_is_supported(lookup_name: &str) -> bool {
    matches!(
        lookup_name,
        "exact"
            | "iexact"
            | "contains"
            | "icontains"
            | "startswith"
            | "istartswith"
            | "endswith"
            | "iendswith"
            | "regex"
            | "iregex"
            | "gt"
            | "gte"
            | "lt"
            | "lte"
            | "in"
            | "range"
            | "isnull"
            | "year"
            | "month"
            | "day"
            | "date"
    )
}

fn field_path_type<'a>(
    request: &'a CallRequest,
    model_name: &str,
    path: &[&'a str],
) -> Option<(&'a str, &'a str)> {
    let (last, prefix) = path.split_last()?;
    let mut current_model = model_name.to_string();
    for field_name in prefix {
        let field_type = model_fields(request, &current_model)
            .and_then(|fields| fields.get(*field_name))
            .and_then(Value::as_str)
            .or_else(|| model_query_field(request, &current_model, field_name))?;
        current_model = related_model_name(request, field_type)?;
    }
    model_fields(request, &current_model)
        .and_then(|fields| fields.get(*last))
        .and_then(Value::as_str)
        .map(|field_type| (*last, field_type))
}

fn model_query_field<'a>(
    request: &'a CallRequest,
    model_name: &str,
    field_name: &str,
) -> Option<&'a str> {
    request
        .project_index
        .as_ref()?
        .get("models")?
        .get(model_name)?
        .get("query_fields")?
        .get(field_name)?
        .as_str()
}

fn lookup_value_is_compatible(
    field_type: &str,
    terminal_lookup: Option<&str>,
    argument: &ArgumentSummary,
) -> bool {
    let lookup = terminal_lookup.unwrap_or("exact");
    if lookup == "isnull" {
        matches!(
            argument.value,
            LiteralValue::Bool { .. } | LiteralValue::Unknown
        )
    } else if lookup == "in" {
        match &argument.value {
            LiteralValue::List { items } | LiteralValue::Tuple { items } => items
                .iter()
                .all(|item| literal_value_matches_field_type(field_type, item)),
            LiteralValue::Unknown => true,
            _ => false,
        }
    } else if lookup == "range" {
        match &argument.value {
            LiteralValue::List { items } | LiteralValue::Tuple { items } if items.len() == 2 => {
                items
                    .iter()
                    .all(|item| literal_value_matches_field_type(field_type, item))
            }
            LiteralValue::Unknown => true,
            _ => false,
        }
    } else if matches!(
        lookup,
        "contains"
            | "icontains"
            | "startswith"
            | "istartswith"
            | "endswith"
            | "iendswith"
            | "regex"
            | "iregex"
    ) {
        field_type_allows(field_type, "str")
            && matches!(
                argument.value,
                LiteralValue::Str { .. } | LiteralValue::Unknown
            )
    } else {
        argument_value_matches_field_type(field_type, argument)
    }
}

fn argument_value_matches_field_type(field_type: &str, argument: &ArgumentSummary) -> bool {
    if !matches!(argument.value, LiteralValue::Unknown) {
        return literal_value_matches_field_type(field_type, &argument.value);
    }
    argument
        .type_expr
        .as_ref()
        .is_none_or(|actual| type_expr_may_match_field_type(field_type, &actual.expression))
}

fn type_expr_may_match_field_type(field_type: &str, actual_type: &str) -> bool {
    if matches!(actual_type, "Any" | "typing.Any" | "Unknown" | "object") {
        return true;
    }
    let expected = field_type.split('|').map(str::trim).collect::<Vec<_>>();
    let actual = actual_type.split('|').map(str::trim).collect::<Vec<_>>();
    if actual
        .iter()
        .any(|actual| expected.iter().any(|expected| actual == expected))
    {
        return true;
    }
    let expected_is_scalar = expected.iter().any(|expected| {
        matches!(
            *expected,
            "bool" | "bytes" | "float" | "int" | "str" | "None"
        ) || expected.starts_with("datetime.")
            || *expected == "decimal.Decimal"
            || *expected == "uuid.UUID"
    });
    !expected_is_scalar
}

fn literal_value_matches_field_type(field_type: &str, value: &LiteralValue) -> bool {
    match value {
        LiteralValue::Unknown => true,
        LiteralValue::None => field_type_allows(field_type, "None"),
        LiteralValue::Bool { .. } => {
            field_type_allows(field_type, "bool") || field_type_allows(field_type, "int")
        }
        LiteralValue::Int { .. } => field_type_allows(field_type, "int"),
        LiteralValue::Str { .. } => field_type_allows(field_type, "str"),
        LiteralValue::ClassRef(_) | LiteralValue::EnumRef(_) | LiteralValue::SymbolRef(_) => true,
        LiteralValue::List { .. } | LiteralValue::Tuple { .. } | LiteralValue::Dict { .. } => false,
    }
}

fn field_type_allows(field_type: &str, expected: &str) -> bool {
    field_type
        .split('|')
        .map(str::trim)
        .any(|candidate| candidate == expected)
}

fn related_model_name(request: &CallRequest, field_type: &str) -> Option<String> {
    field_type
        .split('|')
        .map(str::trim)
        .filter(|candidate| *candidate != "None" && *candidate != "int")
        .find(|candidate| model_fields(request, candidate).is_some())
        .map(ToString::to_string)
}

fn field_type_for_name(
    request: &CallRequest,
    model_name: &str,
    field_name: &str,
) -> Option<TypeExpr> {
    model_fields(request, model_name)?
        .get(field_name)?
        .as_str()
        .map(annotation)
}

fn positional_string_arguments(request: &CallRequest) -> Vec<&str> {
    request
        .arguments
        .iter()
        .filter_map(|argument| {
            if argument.kind != ArgumentKind::Positional {
                return None;
            }
            let LiteralValue::Str { value } = &argument.value else {
                return None;
            };
            Some(value.as_str())
        })
        .collect()
}

fn bool_keyword_argument(arguments: &[ArgumentSummary], name: &str) -> Option<bool> {
    arguments.iter().find_map(|argument| {
        if argument.name.as_deref() != Some(name) || argument.kind != ArgumentKind::Keyword {
            return None;
        }
        let LiteralValue::Bool { value } = argument.value else {
            return None;
        };
        Some(value)
    })
}

fn model_fields<'a>(
    request: &'a CallRequest,
    model_name: &str,
) -> Option<&'a ty_plugin_sdk::serde_json::Map<String, Value>> {
    request
        .project_index
        .as_ref()?
        .get("models")?
        .get(model_name)?
        .get("fields")?
        .as_object()
}

fn model_field_types<'a>(
    request: &'a CallRequest,
    model_name: &str,
) -> Option<&'a ty_plugin_sdk::serde_json::Map<String, Value>> {
    request
        .project_index
        .as_ref()?
        .get("models")?
        .get(model_name)?
        .get("field_types")?
        .as_object()
}

#[cfg(test)]
mod tests {
    use ty_plugin_sdk::protocol::{ReceiverSummary, SemanticContext};

    use super::*;

    const MODEL: &str = "library.models.Book";

    fn context() -> SemanticContext {
        SemanticContext {
            module: "library.use".to_string(),
            file_path: "/project/library/use.py".to_string(),
            python_version: "3.13".to_string(),
            platform: "linux".to_string(),
            speculative: false,
        }
    }

    fn argument(
        name: Option<&str>,
        kind: ArgumentKind,
        value: LiteralValue,
        type_expr: Option<&str>,
    ) -> ArgumentSummary {
        ArgumentSummary {
            name: name.map(str::to_string),
            kind,
            type_expr: type_expr.map(TypeExpr::annotation),
            value,
            source: None,
        }
    }

    fn request(receiver: Option<ReceiverSummary>, arguments: Vec<ArgumentSummary>) -> CallRequest {
        CallRequest {
            context: context(),
            callee: TypeExpr::expression("django.db.models.manager.Manager.values_list"),
            receiver,
            arguments,
            existing_signature: None,
            default_return_type: None,
            project_index: Some(json!({
                "models": {
                    MODEL: {
                        "fields": {
                            "id": "int",
                            "title": "str",
                            "pages": "int",
                            "author": "library.models.Author"
                        }
                    },
                    "library.models.Author": {
                        "fields": {
                            "name": "str"
                        }
                    }
                }
            })),
        }
    }

    fn receiver(arguments: Vec<TypeExpr>) -> ReceiverSummary {
        ReceiverSummary {
            type_expr: TypeExpr::annotation("django.db.models.manager.Manager"),
            nominal_class: Some("django.db.models.manager.Manager".to_string()),
            generic_arguments: arguments,
            plugin_metadata: json!({}),
        }
    }

    #[test]
    fn tuple_rows_preserve_nested_imports_and_snapshots() {
        let tuple = tuple_type(vec![annotation("str"), annotation("datetime.datetime")]);

        assert_eq!(tuple.imports.len(), 1);
        let Some(ty_plugin_sdk::protocol::TypeSnapshot::Tuple { prefix, .. }) =
            tuple.snapshot.as_deref()
        else {
            panic!("tuple row should carry a structural snapshot");
        };
        assert_eq!(prefix.len(), 2);
    }

    #[test]
    fn adjust_return_rejects_missing_receiver_or_model_argument() {
        assert_eq!(
            adjust_queryset_return(&request(None, Vec::new()), "values_list"),
            PluginResponse::NoChange
        );
        assert_eq!(
            adjust_queryset_return(
                &request(Some(receiver(Vec::new())), Vec::new()),
                "values_list"
            ),
            PluginResponse::NoChange
        );
    }

    #[test]
    fn values_list_falls_back_when_lookup_diagnostics_exist() {
        let request = request(
            Some(receiver(vec![TypeExpr::annotation(MODEL)])),
            vec![argument(
                None,
                ArgumentKind::Positional,
                LiteralValue::Str {
                    value: "missing".to_string(),
                },
                Some("str"),
            )],
        );
        assert_eq!(
            values_list_row_type(&request, MODEL, false)
                .map(|ty| ty.expression)
                .as_deref(),
            Some("tuple[object, ...]")
        );
    }

    #[test]
    fn lookup_value_helpers_cover_collection_and_literal_edges() {
        assert!(lookup_value_is_compatible(
            "int",
            Some("in"),
            &argument(None, ArgumentKind::Keyword, LiteralValue::Unknown, None)
        ));
        assert!(lookup_value_is_compatible(
            "int",
            Some("range"),
            &argument(
                None,
                ArgumentKind::Keyword,
                LiteralValue::Tuple {
                    items: vec![
                        LiteralValue::Int { value: 1 },
                        LiteralValue::Int { value: 2 }
                    ]
                },
                None,
            )
        ));
        assert!(lookup_value_is_compatible(
            "str",
            Some("contains"),
            &argument(None, ArgumentKind::Keyword, LiteralValue::Unknown, None)
        ));
        assert!(lookup_value_is_compatible(
            "str",
            Some("contains"),
            &argument(
                None,
                ArgumentKind::Keyword,
                LiteralValue::Str {
                    value: "needle".to_string()
                },
                Some("str")
            )
        ));
        assert!(!lookup_value_is_compatible(
            "int",
            Some("contains"),
            &argument(None, ArgumentKind::Keyword, LiteralValue::Unknown, None)
        ));
        assert!(literal_value_matches_field_type(
            "int",
            &LiteralValue::Unknown
        ));
        assert!(literal_value_matches_field_type(
            "int",
            &LiteralValue::Bool { value: true }
        ));
        assert!(!literal_value_matches_field_type(
            "str",
            &LiteralValue::List { items: Vec::new() }
        ));
    }

    #[test]
    fn bool_keyword_argument_rejects_non_bool_values() {
        assert_eq!(
            bool_keyword_argument(
                &[argument(
                    Some("flat"),
                    ArgumentKind::Keyword,
                    LiteralValue::Str {
                        value: "yes".to_string()
                    },
                    Some("str"),
                )],
                "flat",
            ),
            None
        );
    }

    #[test]
    fn related_query_paths_and_static_type_compatibility_cover_precise_edges() {
        let mut request = request(
            Some(receiver(vec![TypeExpr::annotation(MODEL)])),
            Vec::new(),
        );
        request.project_index = Some(json!({
            "models": {
                MODEL: {
                    "fields": {"title": "str"},
                    "query_fields": {"writer": "library.models.Author"}
                },
                "library.models.Author": {
                    "fields": {"name": "str"}
                }
            }
        }));

        assert_eq!(
            lookup_field_type(&request, MODEL, "writer__name__exact"),
            Some(("name", "str", Some("exact")))
        );
        assert_eq!(
            model_query_field(&request, MODEL, "writer"),
            Some("library.models.Author")
        );
        assert!(type_expr_may_match_field_type("int", "Any"));
        assert!(type_expr_may_match_field_type("int | None", "int"));
        assert!(!type_expr_may_match_field_type("datetime.datetime", "str"));
        assert!(!type_expr_may_match_field_type("decimal.Decimal", "str"));
        assert!(!type_expr_may_match_field_type("uuid.UUID", "str"));
        assert!(type_expr_may_match_field_type(
            "library.models.Author",
            "library.models.Other"
        ));
        let ordering_argument = |value: &str| {
            argument(
                None,
                ArgumentKind::Positional,
                LiteralValue::Str {
                    value: value.to_string(),
                },
                Some("str"),
            )
        };
        assert!(
            validate_field_name_argument_for_method(
                MODEL,
                &request,
                "order_by",
                &ordering_argument("?")
            )
            .is_none()
        );
        assert!(
            validate_field_name_argument_for_method(
                MODEL,
                &request,
                "order_by",
                &ordering_argument("writer__name")
            )
            .is_none()
        );
        assert!(
            validate_field_name_argument_for_method(
                MODEL,
                &request,
                "order_by",
                &ordering_argument("title__exact")
            )
            .is_some()
        );

        let mut annotated_request = request.clone();
        annotated_request.receiver = Some(ReceiverSummary {
            type_expr: TypeExpr::annotation("django.db.models.query.QuerySet"),
            nominal_class: Some("django.db.models.query.QuerySet".to_string()),
            generic_arguments: vec![
                TypeExpr::annotation(MODEL),
                TypeExpr::annotation(r#"Class("Annotated", {"score": int}, library.models.Book)"#),
            ],
            plugin_metadata: json!({}),
        });
        assert!(
            validate_field_name_argument_for_method(
                MODEL,
                &annotated_request,
                "order_by",
                &ordering_argument("score")
            )
            .is_none()
        );
    }

    #[test]
    fn prefetch_parsing_and_validation_fallbacks_are_conservative() {
        let base = TypeExpr::annotation(MODEL);
        let mut no_index = request(
            Some(receiver(vec![TypeExpr::annotation(MODEL)])),
            vec![argument(
                None,
                ArgumentKind::Positional,
                LiteralValue::Unknown,
                Some(r#"Prefetch[Literal["tags"], QuerySet[Tag, Tag], Literal["loaded"]]"#),
            )],
        );
        no_index.project_index = None;
        assert!(
            prefetched_row_type(&no_index, &base)
                .unwrap()
                .expression
                .contains("list[Tag]")
        );
        assert_eq!(qualified_model_name(&no_index, "Tag"), "Tag");

        let mut ambiguous = request(None, Vec::new());
        ambiguous.project_index = Some(json!({
            "models": {
                "one.models.Tag": {"fields": {}},
                "two.models.Tag": {"fields": {}}
            }
        }));
        assert_eq!(qualified_model_name(&ambiguous, "Tag"), "Tag");
        assert_eq!(
            qualified_model_name(&ambiguous, "one.models.Tag"),
            "one.models.Tag"
        );
        assert_eq!(qualified_model_name(&ambiguous, "Missing"), "Missing");
        assert!(prefetched_row_type(&ambiguous, &base).is_none());
        assert!(prefetch_annotation(&ambiguous, "Prefetch[str, QuerySet[Tag, Tag]]").is_none());

        let non_dict = argument(
            Some("defaults"),
            ArgumentKind::Keyword,
            LiteralValue::Unknown,
            None,
        );
        assert!(validate_defaults_argument(MODEL, &ambiguous, &non_dict).is_empty());
        assert!(validate_field_name_collection(MODEL, &ambiguous, &non_dict).is_empty());
        assert!(
            validate_field_name_argument_for_method(MODEL, &ambiguous, "distinct", &non_dict)
                .is_none()
        );

        let non_string_key = argument(
            Some("defaults"),
            ArgumentKind::Keyword,
            LiteralValue::Dict {
                entries: vec![ty_plugin_sdk::protocol::LiteralDictEntry {
                    key: LiteralValue::Int { value: 1 },
                    value: LiteralValue::Int { value: 2 },
                }],
            },
            None,
        );
        assert!(validate_defaults_argument(MODEL, &ambiguous, &non_string_key).is_empty());

        let mut with_title = ambiguous.clone();
        with_title.project_index = Some(json!({
            "models": {MODEL: {"fields": {"title": "str"}}}
        }));
        let title = argument(
            None,
            ArgumentKind::Positional,
            LiteralValue::Str {
                value: "title".to_string(),
            },
            Some("str"),
        );
        assert!(
            validate_field_name_argument_for_method(MODEL, &with_title, "distinct", &title)
                .is_none()
        );
    }

    #[test]
    fn model_and_options_hooks_reject_incomplete_requests() {
        let empty = request(None, Vec::new());
        assert_eq!(
            adjust_model_method(&empty, "save"),
            PluginResponse::NoChange
        );
        assert_eq!(adjust_options_get_field(&empty), PluginResponse::NoChange);

        let no_model = request(
            Some(receiver(vec![TypeExpr::annotation("missing.Model")])),
            Vec::new(),
        );
        assert_eq!(
            adjust_model_method(&no_model, "delete"),
            PluginResponse::NoChange
        );
        assert_eq!(
            adjust_options_get_field(&no_model),
            PluginResponse::NoChange
        );

        let mut model_receiver = receiver(Vec::new());
        model_receiver.nominal_class = Some(MODEL.to_string());
        model_receiver.type_expr = TypeExpr::annotation(MODEL);
        let valid_model = request(Some(model_receiver), Vec::new());
        assert!(matches!(
            adjust_model_method(&valid_model, "delete"),
            PluginResponse::CallReturnPatch(_)
        ));

        let no_generic = request(Some(receiver(Vec::new())), Vec::new());
        assert_eq!(
            adjust_options_get_field(&no_generic),
            PluginResponse::NoChange
        );
        let non_string = request(
            Some(receiver(vec![TypeExpr::annotation(MODEL)])),
            vec![argument(
                None,
                ArgumentKind::Positional,
                LiteralValue::Int { value: 1 },
                Some("int"),
            )],
        );
        assert_eq!(
            adjust_options_get_field(&non_string),
            PluginResponse::NoChange
        );
        let no_field_types = request(
            Some(receiver(vec![TypeExpr::annotation(MODEL)])),
            vec![argument(
                None,
                ArgumentKind::Positional,
                LiteralValue::Str {
                    value: "title".to_string(),
                },
                Some("str"),
            )],
        );
        assert_eq!(
            adjust_options_get_field(&no_field_types),
            PluginResponse::NoChange
        );
    }
}
