use std::collections::{BTreeMap, BTreeSet};

use ty_plugin_sdk::protocol::{
    BuildProjectIndexRequest, Contribution, ContributionPatch, ContributionTarget, FieldPatch,
    LiteralValue, MemberAccessPatch, MemberPatchMode, MethodSummary, ProjectIndexResponse,
    SymbolRef, SymbolSource, TypeSnapshot, VirtualTypeDefinition, VirtualTypeShape,
};
use ty_plugin_sdk::serde_json::{Value, json};

use crate::constants::{MANAGER_BASE, MODEL_BASES, QUERYSET_BASE};
use crate::diagnostics::{reverse_relation_conflict, unknown_relation_target};
use crate::fields::{
    RelationKind, choice_enum_target, django_field_class_type, django_field_from_summary,
    field_call, is_manager_call, is_relation_call, optional_builtin_id_field, relation_target_name,
    reverse_relation_name, string_call_argument,
};
use crate::settings::{SettingsIndex, settings_index};
use crate::types::{
    annotation, canonical_type_expression, expression, manager_virtual_type_name, member,
    queryset_virtual_type_name, values_list_row_virtual_type_name, values_row_virtual_type_name,
    virtual_field,
};

pub fn build_index_response(request: &BuildProjectIndexRequest) -> ProjectIndexResponse {
    let settings = settings_index(request);
    let model_names = model_class_names(request);
    let model_indexes = inherited_model_indexes(request, &settings, &model_names);
    let queryset_classes = project_queryset_classes(request);
    let generated_managers = generated_manager_querysets(request, &queryset_classes);
    let auth_user_model = settings.get("AUTH_USER_MODEL").and_then(|target| {
        resolve_settings_model_name(target, &model_names)
            .or_else(|| conventional_settings_model_name(target))
    });
    let mut diagnostics = Vec::new();
    let mut contributions = Vec::new();
    let mut models = ty_plugin_sdk::serde_json::Map::new();
    let mut reverse_names = BTreeMap::<String, SymbolSource>::new();
    let mut related_query_fields =
        BTreeMap::<String, ty_plugin_sdk::serde_json::Map<String, Value>>::new();
    let mut virtual_types = Vec::new();

    contributions.extend(settings_member_contributions(request));
    if let Some(user_model) = auth_user_model.as_deref() {
        contributions.push(Contribution {
            source: SymbolSource::default(),
            target: ContributionTarget::Instance {
                qualified_name: "django.http.request.HttpRequest".to_string(),
            },
            patch: ContributionPatch::Member(member(
                "user",
                annotation(format!(
                    "{user_model} | django.contrib.auth.models.AnonymousUser"
                )),
            )),
            conflict_key: "django.http.request.HttpRequest.user".to_string(),
            diagnostics: Vec::new(),
        });
    }

    for class in request
        .classes
        .iter()
        .filter(|class| model_names.contains(&class.qualified_name))
    {
        let model_index = model_indexes
            .get(&class.qualified_name)
            .cloned()
            .unwrap_or_default();
        let fields = model_index.fields;
        let manager_queryset =
            model_manager_queryset(class, &queryset_classes, &generated_managers);
        virtual_types.extend(model_virtual_types(
            &class.qualified_name,
            &fields,
            manager_queryset.and_then(|name| queryset_classes.get(name)),
        ));
        if !derives_from_model_class(class) {
            contributions.extend(inherited_model_contributions(class, &fields));
        }
        models.insert(
            class.qualified_name.clone(),
            json!({
                "fields": fields,
                "field_types": model_index.field_types,
                "manager_queryset": manager_queryset,
            }),
        );

        for field in &class.fields {
            let Some(call) = field_call(field.assigned_value.as_ref()) else {
                continue;
            };
            if let Some(choice_target) = choice_enum_target(&class.qualified_name, call)
                && class
                    .nested_classes
                    .iter()
                    .any(|nested| nested.qualified_name == choice_target)
            {
                contributions.push(Contribution {
                    source: field.source.clone(),
                    target: ContributionTarget::Instance {
                        qualified_name: choice_target.clone(),
                    },
                    patch: ContributionPatch::Member(member("label", annotation("str"))),
                    conflict_key: format!("{choice_target}.label"),
                    diagnostics: Vec::new(),
                });
            }
            let Some(kind) = is_relation_call(call) else {
                continue;
            };
            let Some(target) = relation_target_name(
                crate::types::class_module_name(&class.qualified_name),
                &class.qualified_name,
                call,
                &settings,
                &model_names,
                kind,
            ) else {
                continue;
            };
            if !model_names.contains(&target) {
                diagnostics.push(unknown_relation_target(
                    &class.qualified_name,
                    &field.name,
                    &target,
                    &field.source,
                ));
                continue;
            }
            if let Some(related_query_name) = string_call_argument(call, "related_query_name")
                && related_query_name != "+"
            {
                related_query_fields
                    .entry(target.clone())
                    .or_default()
                    .insert(related_query_name.to_string(), json!(class.qualified_name));
            }
            let Some(reverse_name) = reverse_relation_name(&class.qualified_name, call, kind)
            else {
                continue;
            };
            let conflict_key = format!("{target}.{reverse_name}");
            if let Some(first_source) =
                reverse_names.insert(conflict_key.clone(), field.source.clone())
            {
                diagnostics.push(reverse_relation_conflict(
                    &target,
                    &reverse_name,
                    &field.source,
                    &first_source,
                ));
                continue;
            }
            contributions.push(reverse_contribution(
                &class.qualified_name,
                &target,
                &reverse_name,
                kind,
                conflict_key,
                field.source.clone(),
            ));
        }
    }

    for (model_name, query_fields) in related_query_fields {
        if let Some(model) = models.get_mut(&model_name).and_then(Value::as_object_mut) {
            model.insert("query_fields".to_string(), Value::Object(query_fields));
        }
    }

    ProjectIndexResponse {
        plugin_index: json!({
            "models": models,
            "settings": settings,
            "auth_user_model": auth_user_model,
        }),
        contributions,
        virtual_types,
        dependencies: request
            .settings
            .iter()
            .flat_map(|settings| settings.dependencies.clone())
            .collect(),
        diagnostics,
    }
}

fn settings_member_contributions(request: &BuildProjectIndexRequest) -> Vec<Contribution> {
    request
        .settings
        .iter()
        .flat_map(|module| {
            module.values.iter().filter_map(|setting| {
                let ty = match setting.value {
                    LiteralValue::Bool { .. } => "bool",
                    LiteralValue::Int { .. } => "int",
                    LiteralValue::Str { .. } => "str",
                    LiteralValue::None => "None",
                    LiteralValue::Tuple { .. } => "tuple[object, ...]",
                    LiteralValue::List { .. } => "list[object]",
                    LiteralValue::Dict { .. } => "dict[object, object]",
                    LiteralValue::EnumRef(_)
                    | LiteralValue::SymbolRef(_)
                    | LiteralValue::ClassRef(_)
                    | LiteralValue::Unknown => return None,
                };
                Some(Contribution {
                    source: setting.source.clone(),
                    target: ContributionTarget::Instance {
                        qualified_name: "django.conf.LazySettings".to_string(),
                    },
                    patch: ContributionPatch::Member(member(&setting.name, annotation(ty))),
                    conflict_key: format!("django.conf.LazySettings.{}", setting.name),
                    diagnostics: Vec::new(),
                })
            })
        })
        .collect()
}

fn resolve_settings_model_name(raw: &str, model_names: &BTreeSet<String>) -> Option<String> {
    if model_names.contains(raw) {
        return Some(raw.to_string());
    }
    let (app_label, class_name) = raw.split_once('.')?;
    model_names
        .iter()
        .find(|candidate| {
            candidate.ends_with(&format!(".{class_name}"))
                && (candidate.starts_with(&format!("{app_label}."))
                    || candidate.contains(&format!(".{app_label}.")))
        })
        .cloned()
}

fn conventional_settings_model_name(raw: &str) -> Option<String> {
    let (app_module, class_name) = raw.split_once('.')?;
    Some(format!("{app_module}.models.{class_name}"))
}

fn inherited_model_contributions(
    class: &ty_plugin_sdk::protocol::ClassSummary,
    fields: &ty_plugin_sdk::serde_json::Map<String, Value>,
) -> Vec<Contribution> {
    let mut contributions = default_model_members(&class.qualified_name)
        .into_iter()
        .map(|member| Contribution {
            source: class.source.clone(),
            target: ContributionTarget::Class {
                qualified_name: class.qualified_name.clone(),
            },
            conflict_key: format!("{}.{}", class.qualified_name, member.name),
            patch: ContributionPatch::Member(member),
            diagnostics: Vec::new(),
        })
        .collect::<Vec<_>>();
    contributions.extend(fields.iter().filter_map(|(name, get_type)| {
        let get_type = get_type.as_str()?;
        let set_type = annotation(get_type.to_string());
        Some(Contribution {
            source: class.source.clone(),
            target: ContributionTarget::Instance {
                qualified_name: class.qualified_name.clone(),
            },
            patch: ContributionPatch::Field(FieldPatch {
                name: name.clone(),
                mode: MemberPatchMode::ReplaceExisting,
                descriptor: None,
                instance_get_type: annotation(get_type.to_string()),
                instance_set_type: Some(set_type),
                constructor_parameter: None,
                has_default: true,
            }),
            conflict_key: format!("{}.{}", class.qualified_name, name),
            diagnostics: Vec::new(),
        })
    }));
    contributions
}

#[derive(Debug, Default, Clone, PartialEq)]
struct ModelIndex {
    fields: ty_plugin_sdk::serde_json::Map<String, Value>,
    field_types: ty_plugin_sdk::serde_json::Map<String, Value>,
}

pub fn model_class_names(request: &BuildProjectIndexRequest) -> BTreeSet<String> {
    let all_class_names = request
        .classes
        .iter()
        .map(|class| class.qualified_name.clone())
        .collect::<BTreeSet<_>>();
    let mut model_names = BTreeSet::new();
    loop {
        let before = model_names.len();
        for class in &request.classes {
            if class.bases.iter().any(|base| {
                MODEL_BASES.contains(&base.expression.as_str())
                    || resolve_project_class_name(
                        &class.qualified_name,
                        &base.expression,
                        &all_class_names,
                    )
                    .is_some_and(|base| model_names.contains(&base))
            }) {
                model_names.insert(class.qualified_name.clone());
            }
        }
        if model_names.len() == before {
            return model_names;
        }
    }
}

fn inherited_model_indexes(
    request: &BuildProjectIndexRequest,
    settings: &SettingsIndex,
    model_names: &BTreeSet<String>,
) -> BTreeMap<String, ModelIndex> {
    let classes = request
        .classes
        .iter()
        .filter(|class| model_names.contains(&class.qualified_name))
        .map(|class| (class.qualified_name.as_str(), class))
        .collect::<BTreeMap<_, _>>();
    let local = classes
        .iter()
        .map(|(name, class)| {
            (
                (*name).to_string(),
                local_model_index(class, settings, model_names),
            )
        })
        .collect::<BTreeMap<_, _>>();
    let mut resolved = local.clone();

    for _ in 0..model_names.len() {
        let mut next = BTreeMap::new();
        for (name, class) in &classes {
            let mut model_index = ModelIndex::default();
            for base in &class.bases {
                let Some(base_name) = resolve_project_class_name(
                    &class.qualified_name,
                    &base.expression,
                    model_names,
                ) else {
                    continue;
                };
                let Some(base_index) = resolved.get(&base_name) else {
                    continue;
                };
                model_index.fields.extend(base_index.fields.clone());
                model_index
                    .field_types
                    .extend(base_index.field_types.clone());
            }
            if let Some(local_index) = local.get(*name) {
                model_index.fields.extend(local_index.fields.clone());
                model_index
                    .field_types
                    .extend(local_index.field_types.clone());
            }
            next.insert((*name).to_string(), model_index);
        }
        resolved = next;
    }
    resolved
}

fn resolve_project_class_name(
    owner: &str,
    expression: &str,
    class_names: &BTreeSet<String>,
) -> Option<String> {
    let expression = expression.split('[').next().unwrap_or(expression);
    if class_names.contains(expression) {
        return Some(expression.to_string());
    }
    if !expression.contains('.') {
        let candidate = format!("{}.{}", crate::types::class_module_name(owner), expression);
        if class_names.contains(&candidate) {
            return Some(candidate);
        }
    }
    None
}

fn local_model_index(
    class: &ty_plugin_sdk::protocol::ClassSummary,
    settings: &SettingsIndex,
    model_names: &BTreeSet<String>,
) -> ModelIndex {
    let fields = model_field_index(class, settings, model_names);
    let mut field_types = ty_plugin_sdk::serde_json::Map::new();
    field_types.insert(
        "id".to_string(),
        json!("django.db.models.fields.AutoField[typing.Any, typing.Any]"),
    );
    field_types.insert(
        "pk".to_string(),
        json!("django.db.models.fields.AutoField[typing.Any, typing.Any]"),
    );
    for field in &class.fields {
        let Some(call) = field_call(field.assigned_value.as_ref()) else {
            continue;
        };
        if is_manager_call(call)
            || django_field_from_summary(&class.qualified_name, field, settings, model_names)
                .is_none()
        {
            continue;
        }
        field_types.insert(
            field.name.clone(),
            json!(django_field_class_type(&class.qualified_name, call).expression),
        );
    }
    ModelIndex {
        fields,
        field_types,
    }
}

pub fn derives_from_model_class(class: &ty_plugin_sdk::protocol::ClassSummary) -> bool {
    class
        .bases
        .iter()
        .any(|base| MODEL_BASES.contains(&base.expression.as_str()))
}

pub fn model_field_index(
    class: &ty_plugin_sdk::protocol::ClassSummary,
    settings: &SettingsIndex,
    model_names: &BTreeSet<String>,
) -> ty_plugin_sdk::serde_json::Map<String, Value> {
    let mut fields = ty_plugin_sdk::serde_json::Map::new();
    fields.insert("id".to_string(), json!("int"));
    fields.insert("pk".to_string(), json!("int"));

    for field in &class.fields {
        let Some(call) = field_call(field.assigned_value.as_ref()) else {
            continue;
        };
        if is_manager_call(call) {
            continue;
        }
        let Some(django_field) =
            django_field_from_summary(&class.qualified_name, field, settings, model_names)
        else {
            continue;
        };
        fields.insert(
            field.name.clone(),
            json!(canonical_type_expression(&django_field.get_type)),
        );
        if matches!(
            django_field.relation,
            Some(RelationKind::ForeignKey | RelationKind::OneToOne)
        ) {
            fields.insert(
                format!("{}_id", field.name),
                json!(if django_field.nullable {
                    "int | None"
                } else {
                    "int"
                }),
            );
        }
    }

    fields
}

pub fn model_virtual_types(
    model_name: &str,
    fields: &ty_plugin_sdk::serde_json::Map<String, Value>,
    manager_queryset: Option<&&ty_plugin_sdk::protocol::ClassSummary>,
) -> Vec<VirtualTypeDefinition> {
    vec![
        VirtualTypeDefinition {
            name: manager_virtual_type_name(model_name),
            shape: VirtualTypeShape::Class {
                bases: vec![expression(format!("{MANAGER_BASE}[{model_name}]"))],
                members: manager_queryset
                    .map(|queryset| queryset_manager_members(queryset))
                    .unwrap_or_default(),
            },
            metadata: Default::default(),
        },
        VirtualTypeDefinition {
            name: queryset_virtual_type_name(model_name),
            shape: VirtualTypeShape::Class {
                bases: vec![expression(format!(
                    "{QUERYSET_BASE}[{model_name}, {model_name}]"
                ))],
                members: Vec::new(),
            },
            metadata: Default::default(),
        },
        VirtualTypeDefinition {
            name: values_row_virtual_type_name(model_name),
            shape: VirtualTypeShape::TypedDict {
                fields: virtual_type_fields(fields),
                total: true,
            },
            metadata: Default::default(),
        },
        VirtualTypeDefinition {
            name: values_list_row_virtual_type_name(model_name),
            shape: VirtualTypeShape::NamedTuple {
                fields: virtual_type_fields(fields),
            },
            metadata: Default::default(),
        },
    ]
}

fn project_queryset_classes<'a>(
    request: &'a BuildProjectIndexRequest,
) -> BTreeMap<String, &'a ty_plugin_sdk::protocol::ClassSummary> {
    let all_class_names = request
        .classes
        .iter()
        .map(|class| class.qualified_name.clone())
        .collect::<BTreeSet<_>>();
    let mut queryset_names = BTreeSet::new();
    loop {
        let before = queryset_names.len();
        for class in &request.classes {
            if class.bases.iter().any(|base| {
                base.expression.split('[').next() == Some(QUERYSET_BASE)
                    || resolve_project_class_name(
                        &class.qualified_name,
                        &base.expression,
                        &all_class_names,
                    )
                    .is_some_and(|base| queryset_names.contains(&base))
            }) {
                queryset_names.insert(class.qualified_name.clone());
            }
        }
        if queryset_names.len() == before {
            break;
        }
    }
    request
        .classes
        .iter()
        .filter(|class| queryset_names.contains(&class.qualified_name))
        .map(|class| (class.qualified_name.clone(), class))
        .collect()
}

fn generated_manager_querysets(
    request: &BuildProjectIndexRequest,
    queryset_classes: &BTreeMap<String, &ty_plugin_sdk::protocol::ClassSummary>,
) -> BTreeMap<String, String> {
    let queryset_names = queryset_classes.keys().cloned().collect::<BTreeSet<_>>();
    request
        .assignments
        .iter()
        .filter_map(|assignment| {
            let ty_plugin_sdk::protocol::AssignedValueSummary::Call(call) =
                &assignment.assigned_value
            else {
                return None;
            };
            if call.callee.qualified_name.rsplit('.').next() != Some("from_queryset") {
                return None;
            }
            let argument = call.arguments.iter().find(|argument| {
                argument.kind == ty_plugin_sdk::protocol::ArgumentKind::Positional
            })?;
            let symbol = match &argument.value {
                LiteralValue::ClassRef(symbol) | LiteralValue::SymbolRef(symbol) => symbol,
                _ => return None,
            };
            let queryset = resolve_symbol_name(
                crate::types::class_module_name(&assignment.qualified_name),
                symbol,
                &queryset_names,
            )?;
            Some((assignment.qualified_name.clone(), queryset))
        })
        .collect()
}

fn model_manager_queryset<'a>(
    class: &ty_plugin_sdk::protocol::ClassSummary,
    queryset_classes: &'a BTreeMap<String, &ty_plugin_sdk::protocol::ClassSummary>,
    generated_managers: &'a BTreeMap<String, String>,
) -> Option<&'a str> {
    let queryset_names = queryset_classes.keys().cloned().collect::<BTreeSet<_>>();
    for field in &class.fields {
        let Some(call) = field_call(field.assigned_value.as_ref()) else {
            continue;
        };
        if call.callee.qualified_name.rsplit('.').next() == Some("as_manager")
            && let Some(symbol) = call
                .receiver
                .as_ref()
                .and_then(|receiver| receiver.symbol.as_ref())
            && let Some(queryset) = resolve_symbol_name(
                crate::types::class_module_name(&class.qualified_name),
                symbol,
                &queryset_names,
            )
        {
            return queryset_classes
                .get_key_value(&queryset)
                .map(|(name, _)| name.as_str());
        }

        let callee = &call.callee.qualified_name;
        let manager_name = if generated_managers.contains_key(callee) {
            Some(callee.clone())
        } else if !callee.contains('.') {
            Some(format!(
                "{}.{}",
                crate::types::class_module_name(&class.qualified_name),
                callee,
            ))
        } else {
            None
        };
        if let Some(queryset) = manager_name.and_then(|name| generated_managers.get(&name)) {
            return Some(queryset.as_str());
        }
    }
    None
}

fn resolve_symbol_name(
    module: &str,
    symbol: &SymbolRef,
    names: &BTreeSet<String>,
) -> Option<String> {
    if names.contains(&symbol.qualified_name) {
        return Some(symbol.qualified_name.clone());
    }
    let local = format!("{module}.{}", symbol.qualified_name);
    names.contains(&local).then_some(local)
}

fn queryset_manager_members(
    queryset: &ty_plugin_sdk::protocol::ClassSummary,
) -> Vec<ty_plugin_sdk::protocol::MemberPatch> {
    queryset
        .methods
        .iter()
        .filter(|method| method.is_public)
        .map(|method| queryset_manager_member(queryset, method))
        .collect()
}

fn queryset_manager_member(
    queryset: &ty_plugin_sdk::protocol::ClassSummary,
    method: &MethodSummary,
) -> ty_plugin_sdk::protocol::MemberPatch {
    let return_type = method
        .return_type
        .clone()
        .map(|return_type| {
            if matches!(
                return_type.snapshot.as_deref(),
                Some(TypeSnapshot::SelfType { .. })
            ) || return_type.expression == "Self"
            {
                annotation(queryset.qualified_name.clone())
            } else {
                return_type
            }
        })
        .unwrap_or_else(|| annotation("typing.Any"));
    ty_plugin_sdk::dsl::callable_member(
        &method.name,
        ty_plugin_sdk::dsl::signature(
            method.parameters.iter().skip(1).cloned(),
            return_type.clone(),
        ),
        annotation(format!("typing.Callable[..., {}]", return_type.expression)),
    )
}

fn virtual_type_fields(
    fields: &ty_plugin_sdk::serde_json::Map<String, Value>,
) -> Vec<ty_plugin_sdk::protocol::VirtualTypeField> {
    fields
        .iter()
        .filter_map(|(name, ty)| Some(virtual_field(name.clone(), ty.as_str()?.to_string())))
        .collect()
}

fn reverse_contribution(
    source_model: &str,
    target_model: &str,
    reverse_name: &str,
    kind: RelationKind,
    conflict_key: String,
    source: SymbolSource,
) -> Contribution {
    let return_type = match kind {
        RelationKind::OneToOne => annotation(source_model.to_string()),
        RelationKind::ForeignKey | RelationKind::ManyToMany => {
            annotation(manager_virtual_type_name(source_model))
        }
    };
    Contribution {
        source,
        target: ContributionTarget::Instance {
            qualified_name: target_model.to_string(),
        },
        patch: ContributionPatch::Field(FieldPatch {
            name: reverse_name.to_string(),
            mode: MemberPatchMode::ReplaceExisting,
            descriptor: Some(MemberAccessPatch::Descriptor {
                class_type: None,
                instance_get_type: return_type.clone(),
                instance_set_type: None,
            }),
            instance_get_type: return_type,
            instance_set_type: None,
            constructor_parameter: None,
            has_default: true,
        }),
        conflict_key,
        diagnostics: Vec::new(),
    }
}

pub fn default_model_fields() -> Vec<FieldPatch> {
    vec![
        optional_builtin_id_field("id", annotation("int")),
        optional_builtin_id_field("pk", annotation("int")),
    ]
}

pub fn default_model_members(model_name: &str) -> Vec<ty_plugin_sdk::protocol::MemberPatch> {
    let manager = annotation(manager_virtual_type_name(model_name));
    vec![
        member("objects", manager.clone()),
        member("_default_manager", manager),
    ]
}
