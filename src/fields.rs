use std::collections::BTreeSet;

use ty_plugin_sdk::dsl;
use ty_plugin_sdk::protocol::{
    ArgumentKind, ArgumentSummary, AssignedValueSummary, CallValueSummary, FieldPatch,
    FieldSummary, LiteralValue, MemberAccessPatch, MemberPatchMode, Parameter, SymbolRef, TypeExpr,
};

use crate::settings::SettingsIndex;
use crate::types::{annotation, class_module_name, nullable};

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum RelationKind {
    ForeignKey,
    OneToOne,
    ManyToMany,
}

#[derive(Debug, Clone, PartialEq)]
pub struct DjangoField {
    pub name: String,
    pub get_type: TypeExpr,
    pub set_type: TypeExpr,
    pub nullable: bool,
    pub has_default: bool,
    pub relation: Option<RelationKind>,
    pub relation_target: Option<String>,
}

impl DjangoField {
    pub fn patch(&self) -> Option<FieldPatch> {
        if self.relation == Some(RelationKind::ManyToMany) {
            return None;
        }
        let mut parameter = dsl::keyword_only(self.name.clone(), self.set_type.clone());
        parameter.required = false;
        Some(FieldPatch {
            name: self.name.clone(),
            mode: MemberPatchMode::ReplaceExisting,
            descriptor: Some(MemberAccessPatch::Descriptor {
                class_type: None,
                instance_get_type: self.get_type.clone(),
                instance_set_type: Some(self.set_type.clone()),
            }),
            instance_get_type: self.get_type.clone(),
            instance_set_type: Some(self.set_type.clone()),
            constructor_parameter: Some(parameter),
            has_default: self.has_default || self.nullable,
        })
    }

    pub fn id_patch(&self) -> Option<FieldPatch> {
        if !matches!(
            self.relation,
            Some(RelationKind::ForeignKey | RelationKind::OneToOne)
        ) {
            return None;
        }
        let ty = nullable("int", self.nullable);
        Some(FieldPatch {
            name: format!("{}_id", self.name),
            mode: MemberPatchMode::ReplaceExisting,
            descriptor: None,
            instance_get_type: ty.clone(),
            instance_set_type: Some(ty),
            constructor_parameter: None,
            has_default: true,
        })
    }
}

pub fn field_call(assigned_value: Option<&AssignedValueSummary>) -> Option<&CallValueSummary> {
    let Some(AssignedValueSummary::Call(call)) = assigned_value else {
        return None;
    };
    Some(call)
}

pub fn is_manager_call(call: &CallValueSummary) -> bool {
    call.callee
        .qualified_name
        .rsplit('.')
        .next()
        .is_some_and(|last| {
            last == "as_manager"
                || last == "Manager"
                || last == "BaseManager"
                || last.ends_with("Manager")
        })
}

pub fn django_field_class_type(model_name: &str, call: &CallValueSummary) -> TypeExpr {
    let qualified_name = if let Some(name) = call.callee.qualified_name.strip_prefix("models.") {
        format!("django.db.models.{name}")
    } else if call.callee.qualified_name.contains('.') {
        call.callee.qualified_name.clone()
    } else {
        format!(
            "{}.{}",
            class_module_name(model_name),
            call.callee.qualified_name
        )
    };
    annotation(format!("{qualified_name}[typing.Any, typing.Any]"))
}

pub fn is_relation_call(call: &CallValueSummary) -> Option<RelationKind> {
    if callee_matches(call, "ForeignKey") || callee_matches(call, "ForeignObject") {
        Some(RelationKind::ForeignKey)
    } else if callee_matches(call, "OneToOneField") {
        Some(RelationKind::OneToOne)
    } else if callee_matches(call, "ManyToManyField") {
        Some(RelationKind::ManyToMany)
    } else {
        None
    }
}

pub fn django_field_from_summary(
    model_name: &str,
    field: &FieldSummary,
    settings: &SettingsIndex,
    model_names: &BTreeSet<String>,
) -> Option<DjangoField> {
    let call = field_call(field.assigned_value.as_ref())?;
    django_field_from_call(
        class_module_name(model_name),
        model_name,
        &field.name,
        call,
        settings,
        model_names,
    )
}

pub fn django_field_from_call(
    module: &str,
    model_name: &str,
    field_name: &str,
    call: &CallValueSummary,
    settings: &SettingsIndex,
    model_names: &BTreeSet<String>,
) -> Option<DjangoField> {
    if is_manager_call(call) {
        return None;
    }
    let is_nullable = bool_call_argument(call, "null") == Some(true);
    let has_default = call.arguments.iter().any(|argument| {
        argument.name.as_deref() == Some("default")
            && !matches!(argument.value, LiteralValue::Unknown)
    });
    let relation = is_relation_call(call);
    let relation_target = relation.and_then(|kind| {
        relation_target_name(module, model_name, call, settings, model_names, kind)
    });
    let relation_model = relation_target
        .clone()
        .unwrap_or_else(|| "django.db.models.base.Model".to_string());
    let get_type = if relation == Some(RelationKind::ManyToMany) {
        annotation(format!(
            "django.db.models.manager.Manager[{relation_model}]"
        ))
    } else if relation.is_some() {
        nullable(relation_model.clone(), is_nullable)
    } else {
        scalar_field_type(call, is_nullable)?
    };
    let set_type = if relation.is_some() {
        let expression = if is_nullable {
            format!("{relation_model} | int | None")
        } else {
            format!("{relation_model} | int")
        };
        annotation(expression)
    } else {
        get_type.clone()
    };
    Some(DjangoField {
        name: field_name.to_string(),
        get_type,
        set_type,
        nullable: is_nullable,
        has_default,
        relation,
        relation_target,
    })
}

pub fn relation_target_name(
    module: &str,
    model_name: &str,
    call: &CallValueSummary,
    settings: &SettingsIndex,
    model_names: &BTreeSet<String>,
    _kind: RelationKind,
) -> Option<String> {
    let target = named_argument(&call.arguments, "to").or_else(|| {
        call.arguments
            .iter()
            .find(|argument| argument.kind == ArgumentKind::Positional)
    })?;

    let raw = match &target.value {
        LiteralValue::EnumRef(symbol) | LiteralValue::SymbolRef(symbol)
            if settings.contains_key(&symbol.qualified_name) =>
        {
            settings.get(&symbol.qualified_name).cloned()
        }
        LiteralValue::ClassRef(symbol) | LiteralValue::SymbolRef(symbol) => target
            .type_expr
            .as_ref()
            .map(|ty| ty.expression.clone())
            .or_else(|| Some(symbol.qualified_name.clone())),
        LiteralValue::EnumRef(SymbolRef { qualified_name }) => target
            .type_expr
            .as_ref()
            .map(|ty| ty.expression.clone())
            .or_else(|| Some(qualified_name.clone())),
        LiteralValue::Str { value } if value == "self" => Some(model_name.to_string()),
        LiteralValue::Str { value } if settings.contains_key(value) => settings.get(value).cloned(),
        LiteralValue::Str { value } => Some(value.clone()),
        _ => target.type_expr.as_ref().map(|ty| ty.expression.clone()),
    }?;

    Some(resolve_model_name(module, &raw, model_names))
}

pub fn reverse_relation_name(
    model_name: &str,
    call: &CallValueSummary,
    kind: RelationKind,
) -> Option<String> {
    if let Some(related_name) = string_call_argument(call, "related_name") {
        if related_name == "+" {
            return None;
        }
        return Some(related_name.to_string());
    }
    let lower = crate::types::lower_model_name(model_name);
    match kind {
        RelationKind::OneToOne => Some(lower),
        RelationKind::ForeignKey | RelationKind::ManyToMany => Some(format!("{lower}_set")),
    }
}

pub fn bool_call_argument(call: &CallValueSummary, name: &str) -> Option<bool> {
    call.arguments.iter().find_map(|argument| {
        if argument.name.as_deref() != Some(name) {
            return None;
        }
        let LiteralValue::Bool { value } = argument.value else {
            return None;
        };
        Some(value)
    })
}

pub fn string_call_argument<'a>(call: &'a CallValueSummary, name: &str) -> Option<&'a str> {
    call.arguments.iter().find_map(|argument| {
        if argument.name.as_deref() != Some(name) {
            return None;
        }
        let LiteralValue::Str { value } = &argument.value else {
            return None;
        };
        Some(value.as_str())
    })
}

pub fn choice_enum_target(model_name: &str, call: &CallValueSummary) -> Option<String> {
    let argument = named_argument(&call.arguments, "choices")?;
    let symbol = match &argument.value {
        LiteralValue::ClassRef(symbol)
        | LiteralValue::EnumRef(symbol)
        | LiteralValue::SymbolRef(symbol) => &symbol.qualified_name,
        _ => return None,
    };
    if symbol.contains('.') {
        Some(symbol.clone())
    } else {
        Some(format!("{model_name}.{symbol}"))
    }
}

fn named_argument<'a>(arguments: &'a [ArgumentSummary], name: &str) -> Option<&'a ArgumentSummary> {
    arguments
        .iter()
        .find(|argument| argument.name.as_deref() == Some(name))
}

fn resolve_model_name(module: &str, raw: &str, model_names: &BTreeSet<String>) -> String {
    if raw.contains('.') {
        if model_names.contains(raw) {
            return raw.to_string();
        }
        let (app_label, class_name) = raw
            .split_once('.')
            .expect("a dotted model label has a separator");
        if let Some(model) = model_names.iter().find(|candidate| {
            candidate.ends_with(&format!(".{class_name}"))
                && (candidate.starts_with(&format!("{app_label}."))
                    || candidate.contains(&format!(".{app_label}.")))
        }) {
            return model.clone();
        }
        return raw.to_string();
    }
    format!("{module}.{raw}")
}

fn scalar_field_type(call: &CallValueSummary, is_nullable: bool) -> Option<TypeExpr> {
    let last = call.callee.qualified_name.rsplit('.').next().unwrap_or("");
    let expression = match last {
        "AutoField"
        | "BigAutoField"
        | "SmallAutoField"
        | "IntegerField"
        | "BigIntegerField"
        | "SmallIntegerField"
        | "PositiveIntegerField"
        | "PositiveSmallIntegerField"
        | "PositiveBigIntegerField" => "int",
        "BooleanField" => "bool",
        "FloatField" => "float",
        "DecimalField" => "decimal.Decimal",
        "CharField"
        | "TextField"
        | "SlugField"
        | "EmailField"
        | "URLField"
        | "FilePathField"
        | "GenericIPAddressField" => "str",
        "UUIDField" => "uuid.UUID",
        "BinaryField" => "bytes",
        "DateField" => "datetime.date",
        "DateTimeField" => "datetime.datetime",
        "TimeField" => "datetime.time",
        "DurationField" => "datetime.timedelta",
        "JSONField" | "ArrayField" | "HStoreField" => "object",
        "FileField" | "ImageField" => "django.db.models.fields.files.FieldFile",
        _ => return None,
    };
    Some(nullable(expression, is_nullable))
}

fn callee_matches(call: &CallValueSummary, name: &str) -> bool {
    call.callee
        .qualified_name
        .rsplit('.')
        .next()
        .is_some_and(|last| last == name)
}

pub fn optional_builtin_id_field(name: impl Into<String>, ty: TypeExpr) -> FieldPatch {
    FieldPatch {
        name: name.into(),
        mode: MemberPatchMode::ReplaceExisting,
        descriptor: None,
        instance_get_type: ty.clone(),
        instance_set_type: Some(ty),
        constructor_parameter: None::<Parameter>,
        has_default: true,
    }
}

#[cfg(test)]
mod tests {
    use std::collections::{BTreeMap, BTreeSet};

    use ty_plugin_sdk::protocol::{ArgumentSummary, SymbolRef};

    use super::*;

    fn call(name: &str, arguments: Vec<ArgumentSummary>) -> CallValueSummary {
        CallValueSummary {
            callee: SymbolRef {
                qualified_name: format!("django.db.models.{name}"),
            },
            receiver: None,
            arguments,
            return_type: None,
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

    #[test]
    fn field_helpers_cover_defensive_relation_paths() {
        let settings = BTreeMap::new();
        let mut models = BTreeSet::new();
        models.insert("project.accounts.models.User".to_string());

        assert!(
            django_field_from_call(
                "app.models",
                "app.models.Book",
                "objects",
                &call("BookManager", Vec::new()),
                &settings,
                &models,
            )
            .is_none()
        );

        let fallback = call(
            "ForeignKey",
            vec![argument(
                None,
                ArgumentKind::Positional,
                LiteralValue::Unknown,
                Some("fallback.models.Target"),
            )],
        );
        assert_eq!(
            relation_target_name(
                "app.models",
                "app.models.Book",
                &fallback,
                &settings,
                &models,
                RelationKind::ForeignKey,
            )
            .as_deref(),
            Some("fallback.models.Target")
        );

        let app_label = call(
            "ForeignKey",
            vec![argument(
                None,
                ArgumentKind::Positional,
                LiteralValue::Str {
                    value: "accounts.User".to_string(),
                },
                None,
            )],
        );
        assert_eq!(
            relation_target_name(
                "app.models",
                "app.models.Book",
                &app_label,
                &settings,
                &models,
                RelationKind::ForeignKey,
            )
            .as_deref(),
            Some("project.accounts.models.User")
        );

        let no_target = call("ForeignKey", Vec::new());
        assert!(
            relation_target_name(
                "app.models",
                "app.models.Book",
                &no_target,
                &settings,
                &models,
                RelationKind::ForeignKey,
            )
            .is_none()
        );

        let unknown_without_type = call(
            "ForeignKey",
            vec![argument(
                None,
                ArgumentKind::Positional,
                LiteralValue::Unknown,
                None,
            )],
        );
        assert!(
            relation_target_name(
                "app.models",
                "app.models.Book",
                &unknown_without_type,
                &settings,
                &models,
                RelationKind::ForeignKey,
            )
            .is_none()
        );
    }

    #[test]
    fn argument_helpers_reject_wrong_literal_shapes() {
        let call = call(
            "ForeignKey",
            vec![
                argument(
                    Some("null"),
                    ArgumentKind::Keyword,
                    LiteralValue::Str {
                        value: "true".to_string(),
                    },
                    Some("str"),
                ),
                argument(
                    Some("related_name"),
                    ArgumentKind::Keyword,
                    LiteralValue::Int { value: 1 },
                    Some("int"),
                ),
            ],
        );
        assert_eq!(bool_call_argument(&call, "null"), None);
        assert_eq!(string_call_argument(&call, "related_name"), None);
        assert_eq!(
            reverse_relation_name("accounts.models.Profile", &call, RelationKind::OneToOne),
            Some("profile".to_string())
        );
    }

    #[test]
    fn field_class_and_choice_targets_are_canonicalized() {
        let local_field = CallValueSummary {
            callee: SymbolRef {
                qualified_name: "CustomField".to_string(),
            },
            receiver: None,
            arguments: Vec::new(),
            return_type: None,
        };
        assert_eq!(
            django_field_class_type("library.models.Book", &local_field).expression,
            "library.models.CustomField[typing.Any, typing.Any]"
        );

        for value in [
            LiteralValue::ClassRef(SymbolRef {
                qualified_name: "Status".to_string(),
            }),
            LiteralValue::EnumRef(SymbolRef {
                qualified_name: "library.models.Book.Status".to_string(),
            }),
            LiteralValue::SymbolRef(SymbolRef {
                qualified_name: "Status".to_string(),
            }),
        ] {
            let choices = call(
                "CharField",
                vec![argument(
                    Some("choices"),
                    ArgumentKind::Keyword,
                    value,
                    None,
                )],
            );
            assert_eq!(
                choice_enum_target("library.models.Book", &choices).as_deref(),
                Some("library.models.Book.Status")
            );
        }

        let invalid = call(
            "CharField",
            vec![argument(
                Some("choices"),
                ArgumentKind::Keyword,
                LiteralValue::Int { value: 1 },
                None,
            )],
        );
        assert_eq!(choice_enum_target("library.models.Book", &invalid), None);
    }
}
