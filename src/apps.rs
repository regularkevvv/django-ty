use ty_plugin_sdk::protocol::{
    ArgumentKind, ArgumentSummary, CallRequest, LiteralValue, PluginResponse,
};

use crate::types::annotation;

pub fn get_model(request: &CallRequest) -> PluginResponse {
    let argument = |name: &str, position: usize| {
        request
            .arguments
            .iter()
            .find(|argument| argument.name.as_deref() == Some(name))
            .or_else(|| {
                request
                    .arguments
                    .iter()
                    .filter(|argument| argument.kind == ArgumentKind::Positional)
                    .nth(position)
            })
    };
    let text = |argument: &ArgumentSummary| match &argument.value {
        LiteralValue::Str { value } => Some(value.clone()),
        _ => None,
    };
    let Some(app) = argument("app_label", 0).and_then(text) else {
        return PluginResponse::NoChange;
    };
    let reference = match argument("model_name", 1) {
        Some(argument) => match text(argument) {
            Some(model) => format!("{app}.{model}"),
            None => return PluginResponse::NoChange,
        },
        None => app,
    };
    let Some((app, model)) = reference.split_once('.') else {
        return PluginResponse::NoChange;
    };
    let Some(models) = request
        .project_index
        .as_ref()
        .and_then(|index| index.get("models"))
        .and_then(ty_plugin_sdk::serde_json::Value::as_object)
    else {
        return PluginResponse::NoChange;
    };
    let mut matches = models.keys().filter(|qualified| {
        let Some((module, name)) = qualified.rsplit_once('.') else {
            return false;
        };
        let module = module.strip_suffix(".models").unwrap_or(module);
        module.rsplit('.').next() == Some(app) && name.eq_ignore_ascii_case(model)
    });
    let Some(qualified) = matches.next() else {
        return PluginResponse::NoChange;
    };
    if matches.next().is_some() {
        return PluginResponse::NoChange;
    }
    ty_plugin_sdk::dsl::call_return(annotation(format!("type[{qualified}]")))
}

#[cfg(test)]
mod tests {
    use ty_plugin_sdk::protocol::{SemanticContext, TypeExpr};
    use ty_plugin_sdk::serde_json::json;

    use super::*;

    fn request(arguments: Vec<ArgumentSummary>) -> CallRequest {
        CallRequest {
            context: SemanticContext {
                module: "library.use".to_string(),
                file_path: "/project/library/use.py".to_string(),
                python_version: "3.13".to_string(),
                platform: "linux".to_string(),
                config: ty_plugin_sdk::serde_json::json!({}),
                speculative: false,
            },
            callee: TypeExpr::expression("django.apps.registry.Apps.get_model"),
            receiver: None,
            arguments,
            existing_signature: None,
            default_return_type: None,
            project_index: Some(json!({"models": {"invalid": {}, "library.models.Book": {}}})),
        }
    }

    fn argument(name: Option<&str>, value: LiteralValue) -> ArgumentSummary {
        ArgumentSummary {
            name: name.map(str::to_string),
            kind: if name.is_some() {
                ArgumentKind::Keyword
            } else {
                ArgumentKind::Positional
            },
            type_expr: None,
            value,
            source: None,
        }
    }

    fn string(name: Option<&str>, value: &str) -> ArgumentSummary {
        argument(
            name,
            LiteralValue::Str {
                value: value.to_string(),
            },
        )
    }

    #[test]
    fn literal_registry_references_resolve_without_guessing() {
        for arguments in [
            vec![string(None, "library.Book")],
            vec![string(None, "library"), string(None, "book")],
            vec![
                string(Some("app_label"), "library"),
                string(Some("model_name"), "Book"),
            ],
        ] {
            let PluginResponse::CallReturnPatch(patch) = get_model(&request(arguments)) else {
                panic!("expected registry type");
            };
            assert_eq!(patch.return_type.expression, "type[library.models.Book]");
        }
        for arguments in [
            vec![],
            vec![argument(None, LiteralValue::Unknown)],
            vec![
                string(None, "library"),
                argument(None, LiteralValue::Unknown),
            ],
            vec![string(None, "library")],
            vec![string(None, "missing.Book")],
        ] {
            assert!(matches!(
                get_model(&request(arguments)),
                PluginResponse::NoChange
            ));
        }
        let mut call = request(vec![string(None, "library.Book")]);
        call.project_index = None;
        assert!(matches!(get_model(&call), PluginResponse::NoChange));
        call.project_index =
            Some(json!({"models": {"library.models.Book": {}, "other.library.models.Book": {}}}));
        assert!(matches!(get_model(&call), PluginResponse::NoChange));
    }
}
