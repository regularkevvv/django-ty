use ty_plugin_sdk::protocol::{
    AnalyzeClassRequest, BuildProjectIndexRequest, CallRequest, MutationOperation, MutationRequest,
    MutationResponse, PluginManifest, PluginResponse, ReceiverSummary,
};
use ty_plugin_sdk::{ManifestBuilder, Plugin};

use crate::constants::{
    BASE_MANAGER_BASE, CHOICES_BASES, MANAGER_BASE, MANAGER_METHODS, MODEL_BASES, OPTIONS_BASE,
    QUERYSET_BASE,
};
use crate::diagnostics::immutable_querydict_write;
use crate::fields::{choice_enum_target, django_field_from_summary, field_call, is_manager_call};
use crate::index::{
    build_index_response, default_model_fields, default_model_members, derives_from_model_class,
};
use crate::querysets::{adjust_model_method, adjust_options_get_field, adjust_queryset_return};
use crate::settings::settings_index_from_project_index;
use crate::types::{annotation, manager_virtual_type_name, member};

#[derive(Debug, Default, Clone, Copy)]
pub struct DjangoTyPlugin;

impl Plugin for DjangoTyPlugin {
    fn manifest(&self) -> PluginManifest {
        let mut builder =
            ManifestBuilder::new("django-ty", "Django ty plugin", env!("CARGO_PKG_VERSION"))
                .ty_compatibility(">=0.59.0,<0.60.0")
                .settings_module("settings")
                .settings_module("project.settings")
                .settings_module_from_config("django-settings-module")
                .claim_instance_contribution_target("django.conf.LazySettings")
                .claim_instance_contribution_target("django.http.request.HttpRequest")
                .claim_call_return("django.contrib.auth.get_user_model")
                .claim_call_return("django.contrib.auth.__init__.get_user_model")
                .claim_call_signature_method(BASE_MANAGER_BASE, "from_queryset")
                .claim_mutations("django.http.request._ImmutableQueryDict")
                .stub_overlay(
                    "django.db.models.manager",
                    "stubs/django/db/models/manager.pyi",
                )
                .stub_overlay("django.db.models.query", "stubs/django/db/models/query.pyi")
                .virtual_types();
        for base in MODEL_BASES {
            builder = builder
                .claim_subclass_transform(*base)
                .claim_class_contribution_target(*base)
                .claim_instance_contribution_target(*base)
                .claim_call_return_method_on_subclass(*base, "save");
        }
        for base in CHOICES_BASES {
            builder = builder.claim_instance_contribution_target(*base);
        }
        for base in [BASE_MANAGER_BASE, MANAGER_BASE, QUERYSET_BASE] {
            for method in MANAGER_METHODS {
                builder = builder.claim_call_return_method_on_subclass(base, *method);
            }
        }
        builder = builder.claim_call_return_method_on_subclass(OPTIONS_BASE, "get_field");
        builder = builder.claim_call_return("django.utils.translation.gettext_lazy");
        builder.build()
    }

    fn build_project_index(&self, request: &BuildProjectIndexRequest) -> PluginResponse {
        PluginResponse::ProjectIndex(build_index_response(request))
    }

    fn analyze_class(&self, request: &AnalyzeClassRequest) -> PluginResponse {
        let indexed_model = request
            .project_index
            .as_ref()
            .and_then(|index| index.get("models"))
            .and_then(|models| models.get(&request.class.qualified_name))
            .is_some();
        if !indexed_model && !derives_from_model_class(&request.class) {
            return PluginResponse::NoChange;
        }
        let settings = settings_index_from_project_index(request.project_index.as_ref());
        let model_names = request
            .project_index
            .as_ref()
            .and_then(|index| index.get("models"))
            .and_then(|models| models.as_object())
            .map(|models| models.keys().cloned().collect())
            .unwrap_or_default();

        let mut patch = ty_plugin_sdk::dsl::ClassPatchBuilder::new();
        for field in default_model_fields() {
            patch = patch.field(field);
        }
        for member_patch in default_model_members(&request.class.qualified_name) {
            patch = patch.class_member(member_patch);
        }

        for field in &request.class.fields {
            let Some(call) = field_call(field.assigned_value.as_ref()) else {
                continue;
            };
            if is_manager_call(call) {
                patch = patch.class_member(member(
                    &field.name,
                    manager_member_type(
                        call,
                        &request.class.qualified_name,
                        request.project_index.as_ref(),
                    ),
                ));
                continue;
            }
            if choice_enum_target(&request.class.qualified_name, call).is_some() {
                patch = patch.instance_member(ty_plugin_sdk::dsl::replace_existing_member(
                    ty_plugin_sdk::dsl::callable_member(
                        format!("get_{}_display", field.name),
                        ty_plugin_sdk::dsl::signature(std::iter::empty(), annotation("str")),
                        annotation("typing.Callable[..., str]"),
                    ),
                ));
            }
            let Some(django_field) = django_field_from_summary(
                &request.class.qualified_name,
                field,
                &settings,
                &model_names,
            ) else {
                continue;
            };
            if let Some(field_patch) = django_field.patch() {
                patch = patch.field(field_patch);
            }
            if let Some(id_patch) = django_field.id_patch() {
                patch = patch.field(id_patch);
            }
        }

        patch.response()
    }

    fn adjust_call_return(&self, request: &CallRequest) -> PluginResponse {
        if request.callee.expression == "django.utils.translation.gettext_lazy" {
            return ty_plugin_sdk::dsl::call_return(annotation("str"));
        }
        if request.callee.expression == "django.contrib.auth.get_user_model" {
            let Some(user_model) = request
                .project_index
                .as_ref()
                .and_then(|index| index.get("auth_user_model"))
                .and_then(ty_plugin_sdk::serde_json::Value::as_str)
            else {
                return PluginResponse::NoChange;
            };
            return ty_plugin_sdk::dsl::call_return(annotation(format!("type[{user_model}]")));
        }
        let Some(receiver) = &request.receiver else {
            return PluginResponse::NoChange;
        };
        let method_name = request
            .callee
            .expression
            .rsplit('.')
            .next()
            .unwrap_or_default();
        if method_name == "save" {
            return adjust_model_method(request, method_name);
        }
        if method_name == "get_field"
            && receiver
                .nominal_class
                .as_deref()
                .is_some_and(|name| name == OPTIONS_BASE || name.ends_with(".Options"))
        {
            return adjust_options_get_field(request);
        }
        if !receiver_is_manager_or_queryset(receiver) {
            return PluginResponse::NoChange;
        }
        adjust_queryset_return(request, method_name)
    }

    fn adjust_call_signature(&self, request: &CallRequest) -> PluginResponse {
        if request.callee.expression.rsplit('.').next() != Some("from_queryset") {
            return PluginResponse::NoChange;
        }

        let return_type = request
            .receiver
            .as_ref()
            .map(|receiver| receiver.type_expr.clone())
            .unwrap_or_else(|| {
                annotation("type[django.db.models.manager.BaseManager[typing.Any]]")
            });
        ty_plugin_sdk::dsl::call_signature(ty_plugin_sdk::dsl::signature(
            [
                ty_plugin_sdk::dsl::positional_or_keyword(
                    "queryset_class",
                    annotation("type[django.db.models.query.QuerySet[typing.Any, typing.Any]]"),
                ),
                ty_plugin_sdk::dsl::optional(ty_plugin_sdk::dsl::positional_or_keyword(
                    "class_name",
                    annotation("str | None"),
                )),
            ],
            return_type,
        ))
    }

    fn validate_mutation(&self, request: &MutationRequest) -> PluginResponse {
        if request.operation != MutationOperation::ItemSet {
            return PluginResponse::NoChange;
        }
        PluginResponse::MutationDiagnostics(MutationResponse {
            diagnostics: vec![immutable_querydict_write(&request.source)],
        })
    }
}

fn manager_member_type(
    call: &ty_plugin_sdk::protocol::CallValueSummary,
    model_name: &str,
    project_index: Option<&ty_plugin_sdk::serde_json::Value>,
) -> ty_plugin_sdk::protocol::TypeExpr {
    let qualified_name = &call.callee.qualified_name;
    let project_manager = project_index
        .and_then(|index| index.get("models"))
        .and_then(|models| models.get(model_name))
        .and_then(|model| model.get("manager_queryset"))
        .is_some_and(|queryset| queryset.is_string());
    if project_manager || qualified_name.starts_with("django.db.models.") {
        annotation(manager_virtual_type_name(model_name))
    } else {
        let qualified_name = if qualified_name.contains('.') {
            qualified_name.clone()
        } else {
            format!(
                "{}.{}",
                crate::types::class_module_name(model_name),
                qualified_name
            )
        };
        annotation(qualified_name)
    }
}

fn receiver_is_manager_or_queryset(receiver: &ReceiverSummary) -> bool {
    receiver.nominal_class.as_deref().is_some_and(|name| {
        matches!(name, BASE_MANAGER_BASE | MANAGER_BASE | QUERYSET_BASE)
            || name.ends_with("Manager")
            || name.ends_with("BaseManager")
            || name.ends_with("QuerySet")
            || name.contains("django_ty.virtual.")
    })
}
