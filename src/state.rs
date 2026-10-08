use std::collections::BTreeMap;

use ty_plugin_sdk::protocol::{
    ArgumentKind, BuildProjectIndexRequest, CallOrSymbolSummary, CallRequest, CallStatePatch,
    LiteralValue, PluginResponse,
};

use crate::types::annotation;

pub fn adjust_call_state(request: &CallRequest) -> PluginResponse {
    if request
        .context
        .config
        .get("model-state")
        .and_then(|value| value.as_bool())
        == Some(false)
    {
        return PluginResponse::NoChange;
    }
    let Some(receiver) = &request.receiver else {
        return constructor_state(request);
    };
    let method = request
        .callee
        .expression
        .rsplit('.')
        .next()
        .unwrap_or_default();
    let is_model_method = matches!(method, "save" | "delete");
    let model_name = if is_model_method {
        receiver
            .nominal_class
            .as_deref()
            .unwrap_or(&receiver.type_expr.expression)
    } else if matches!(method, "get" | "create" | "earliest" | "latest") {
        let Some(model) = receiver.generic_arguments.first() else {
            return PluginResponse::NoChange;
        };
        // values()/values_list() return rows, not fresh model instances.
        if receiver
            .generic_arguments
            .get(1)
            .is_some_and(|row| row != model)
        {
            return PluginResponse::NoChange;
        }
        &model.expression
    } else {
        return PluginResponse::NoChange;
    };
    let Some(model) = request
        .project_index
        .as_ref()
        .and_then(|index| index.get("models"))
        .and_then(|models| models.get(model_name))
    else {
        return PluginResponse::NoChange;
    };
    let Some(primary_key) = model.get("auto_primary_key").and_then(|key| key.as_str()) else {
        return PluginResponse::NoChange;
    };
    if !is_model_method
        && model
            .get("custom_loading")
            .and_then(|value| value.as_bool())
            == Some(true)
    {
        return PluginResponse::NoChange;
    }
    if method == "create"
        && model.get("custom_save").and_then(|value| value.as_bool()) == Some(true)
    {
        return PluginResponse::NoChange;
    }
    if method != "delete"
        && model
            .get("signal_receivers")
            .and_then(|value| value.as_bool())
            == Some(true)
    {
        return PluginResponse::NoChange;
    }
    // Empty or unknown update_fields may skip saving. Positional arguments and
    // **kwargs can supply update_fields too; never assume they perform a save.
    if method == "save"
        && request.arguments.iter().any(|argument| {
            matches!(
                argument.kind,
                ArgumentKind::Positional | ArgumentKind::StarArgs | ArgumentKind::StarKwargs
            ) || argument.name.as_deref() == Some("update_fields")
                && !definitely_saves(&argument.value)
        })
    {
        return PluginResponse::NoChange;
    }
    let members = BTreeMap::from([
        (
            primary_key.to_string(),
            annotation(if method == "delete" { "None" } else { "int" }),
        ),
        (
            "pk".to_string(),
            annotation(if method == "delete" { "None" } else { "int" }),
        ),
    ]);
    let mut patch = CallStatePatch::default();
    if is_model_method {
        patch.receiver_members = members;
    } else {
        patch.fresh_result = true;
        patch.result_members = members;
    }
    // Django signals and routers may mutate other objects.
    ty_plugin_sdk::dsl::call_state(patch)
}

fn definitely_saves(value: &LiteralValue) -> bool {
    match value {
        LiteralValue::None => true,
        LiteralValue::List { items } | LiteralValue::Tuple { items } => !items.is_empty(),
        _ => false,
    }
}

fn constructor_state(request: &CallRequest) -> PluginResponse {
    let Some(model) = request
        .project_index
        .as_ref()
        .and_then(|index| index.get("models"))
        .and_then(|models| models.get(&request.callee.expression))
    else {
        return PluginResponse::NoChange;
    };
    let Some(primary_key) = model.get("auto_primary_key").and_then(|key| key.as_str()) else {
        return PluginResponse::NoChange;
    };
    if model
        .get("custom_loading")
        .and_then(|value| value.as_bool())
        == Some(true)
    {
        return PluginResponse::NoChange;
    }
    if model
        .get("signal_receivers")
        .and_then(|value| value.as_bool())
        == Some(true)
    {
        return PluginResponse::NoChange;
    }
    let uncertain_type = if model
        .get("auto_primary_key_default")
        .and_then(|value| value.as_str())
        == Some("django.db.models.expressions.DatabaseDefault")
    {
        "int | None | django.db.models.expressions.DatabaseDefault"
    } else {
        "int | None"
    };
    let uncertain_arguments = request.arguments.iter().any(|argument| {
        matches!(
            argument.kind,
            ArgumentKind::Positional | ArgumentKind::StarArgs | ArgumentKind::StarKwargs
        )
    });
    let argument = request
        .arguments
        .iter()
        .find(|argument| argument.name.as_deref() == Some("pk"))
        .or_else(|| {
            request
                .arguments
                .iter()
                .find(|argument| argument.name.as_deref() == Some(primary_key))
        });
    let value = if uncertain_arguments {
        uncertain_type
    } else if let Some(argument) = argument {
        match &argument.value {
            LiteralValue::None => "None",
            LiteralValue::Int { .. } => "int",
            _ if argument
                .type_expr
                .as_ref()
                .is_some_and(|ty| ty.expression == "int") =>
            {
                "int"
            }
            _ => uncertain_type,
        }
    } else {
        model
            .get("auto_primary_key_default")
            .and_then(|value| value.as_str())
            .unwrap_or("None")
    };
    ty_plugin_sdk::dsl::call_state(CallStatePatch {
        result_members: BTreeMap::from([
            (primary_key.to_string(), annotation(value)),
            ("pk".to_string(), annotation(value)),
        ]),
        fresh_result: true,
        ..Default::default()
    })
}

pub fn has_signal_receiver(request: &BuildProjectIndexRequest, model_name: &str) -> bool {
    request
        .functions
        .iter()
        .flat_map(|function| &function.decorators)
        .chain(
            request
                .classes
                .iter()
                .flat_map(|class| &class.methods)
                .flat_map(|method| &method.decorators),
        )
        .any(|decorator| {
            let CallOrSymbolSummary::Call(call) = decorator else {
                return false;
            };
            // Decorator summaries preserve source spelling, including bare imports.
            // A different decorator named receiver may suppress tracking conservatively.
            if call.callee.qualified_name.rsplit('.').next() != Some("receiver") {
                return false;
            }
            let Some(sender) = call
                .arguments
                .iter()
                .find(|argument| argument.name.as_deref() == Some("sender"))
            else {
                return true;
            };
            // The semantic type resolves imported names and aliases to the model.
            if let Some(sender_type) = &sender.type_expr {
                if sender_type.expression == model_name {
                    return true;
                }
                if request
                    .classes
                    .iter()
                    .any(|class| class.qualified_name == sender_type.expression)
                {
                    return false;
                }
            }
            match &sender.value {
                LiteralValue::ClassRef(symbol) | LiteralValue::SymbolRef(symbol) => {
                    symbol.qualified_name == model_name
                        || !symbol.qualified_name.contains('.')
                            && symbol.qualified_name == crate::types::class_short_name(model_name)
                }
                LiteralValue::Str { value } => {
                    value.rsplit('.').next() == Some(crate::types::class_short_name(model_name))
                }
                _ => true,
            }
        })
}

#[cfg(test)]
mod tests {
    use super::*;
    use ty_plugin_sdk::protocol::{
        ArgumentSummary, CallValueSummary, FunctionSummary, ProjectContext, SymbolRef, SymbolSource,
    };
    use ty_plugin_sdk::serde_json::json;

    #[test]
    fn signal_receivers_match_sender_models_and_conservative_unknowns() {
        let mut request = BuildProjectIndexRequest {
            context: ProjectContext {
                root: "/project".into(),
                python_version: "3.13".into(),
                platform: "linux".into(),
                config: json!({}),
            },
            classes: vec![],
            settings: vec![],
            assignments: vec![],
            functions: vec![],
            previous_index_fingerprint: None,
        };
        for (callee, sender, expected) in [
            (
                "receiver",
                Some(LiteralValue::ClassRef(SymbolRef {
                    qualified_name: "Book".into(),
                })),
                true,
            ),
            (
                "django.dispatch.receiver",
                Some(LiteralValue::SymbolRef(SymbolRef {
                    qualified_name: "library.models.Book".into(),
                })),
                true,
            ),
            (
                "dispatch.receiver",
                Some(LiteralValue::Str {
                    value: "library.Book".into(),
                }),
                true,
            ),
            (
                "receiver",
                Some(LiteralValue::ClassRef(SymbolRef {
                    qualified_name: "other.models.Book".into(),
                })),
                false,
            ),
            (
                "receiver",
                Some(LiteralValue::Str {
                    value: "library.Author".into(),
                }),
                false,
            ),
            ("receiver", Some(LiteralValue::Unknown), true),
            ("receiver", None, true),
            ("unrelated", None, false),
        ] {
            request.functions = vec![FunctionSummary {
                qualified_name: "library.models.callback".into(),
                decorators: vec![CallOrSymbolSummary::Call(CallValueSummary {
                    callee: SymbolRef {
                        qualified_name: callee.into(),
                    },
                    receiver: None,
                    arguments: sender
                        .into_iter()
                        .map(|value| ArgumentSummary {
                            name: Some("sender".into()),
                            kind: ArgumentKind::Keyword,
                            value,
                            type_expr: None,
                            source: None,
                        })
                        .collect(),
                    return_type: None,
                })],
                inferred_type: None,
                source: SymbolSource::default(),
            }];
            assert_eq!(
                has_signal_receiver(&request, "library.models.Book"),
                expected,
                "{callee}"
            );
        }
        request.functions[0].decorators = vec![CallOrSymbolSummary::Call(CallValueSummary {
            callee: SymbolRef {
                qualified_name: "receiver".into(),
            },
            receiver: None,
            arguments: vec![ArgumentSummary {
                name: Some("sender".into()),
                kind: ArgumentKind::Keyword,
                value: LiteralValue::SymbolRef(SymbolRef {
                    qualified_name: "Alias".into(),
                }),
                type_expr: Some(ty_plugin_sdk::protocol::TypeExpr::annotation(
                    "library.models.Book",
                )),
                source: None,
            }],
            return_type: None,
        })];
        assert!(has_signal_receiver(&request, "library.models.Book"));
        request.classes.push(ty_plugin_sdk::protocol::ClassSummary {
            qualified_name: "library.models.Book".into(),
            bases: vec![],
            decorators: vec![],
            metaclass: None,
            fields: vec![],
            methods: vec![],
            nested_classes: vec![],
            class_constants: vec![],
            source: SymbolSource::default(),
        });
        let CallOrSymbolSummary::Call(call) = &mut request.functions[0].decorators[0] else {
            panic!()
        };
        call.arguments[0].value = LiteralValue::SymbolRef(SymbolRef {
            qualified_name: "Book".into(),
        });
        assert!(!has_signal_receiver(&request, "other.models.Book"));
        let CallOrSymbolSummary::Call(call) = &mut request.functions[0].decorators[0] else {
            panic!()
        };
        call.arguments[0].type_expr =
            Some(ty_plugin_sdk::protocol::TypeExpr::annotation("Unknown"));
        assert!(has_signal_receiver(&request, "library.models.Book"));
        request.functions[0].decorators = vec![CallOrSymbolSummary::Symbol(SymbolRef {
            qualified_name: "receiver".into(),
        })];
        assert!(!has_signal_receiver(&request, "library.models.Book"));
    }
}
