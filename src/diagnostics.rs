use std::collections::BTreeMap;

use ty_plugin_sdk::protocol::{
    ArgumentSummary, DiagnosticLocation, DiagnosticSeverity, PluginDiagnostic, SymbolSource,
};
use ty_plugin_sdk::serde_json::json;

pub fn diagnostic_location_from_source(source: &SymbolSource) -> Option<DiagnosticLocation> {
    Some(DiagnosticLocation {
        file_path: source.file_path.clone()?,
        start: source.start?,
        end: source.end?,
    })
}

pub fn unknown_relation_target(
    model_name: &str,
    field_name: &str,
    target_name: &str,
    source: &SymbolSource,
) -> PluginDiagnostic {
    PluginDiagnostic {
        id: "django-ty.unknown-relation-target".to_string(),
        message: format!(
            "Unknown Django relation target `{target_name}` for field `{model_name}.{field_name}`"
        ),
        severity: DiagnosticSeverity::Error,
        location: diagnostic_location_from_source(source),
        metadata: BTreeMap::new(),
    }
}

pub fn reverse_relation_conflict(
    target_name: &str,
    reverse_name: &str,
    source: &SymbolSource,
    first_source: &SymbolSource,
) -> PluginDiagnostic {
    let mut metadata = BTreeMap::new();
    if let Some(file_path) = first_source.file_path.as_ref() {
        metadata.insert("first-file-path".to_string(), json!(file_path));
    }
    PluginDiagnostic {
        id: "django-ty.reverse-relation-conflict".to_string(),
        message: format!("Conflicting Django reverse relation `{target_name}.{reverse_name}`"),
        severity: DiagnosticSeverity::Error,
        location: diagnostic_location_from_source(source),
        metadata,
    }
}

pub fn unknown_lookup(
    model_name: &str,
    lookup: &str,
    argument: &ArgumentSummary,
) -> PluginDiagnostic {
    PluginDiagnostic {
        id: "django-ty.unknown-lookup".to_string(),
        message: format!("Unknown Django lookup `{lookup}` for model `{model_name}`"),
        severity: DiagnosticSeverity::Error,
        location: argument
            .source
            .as_ref()
            .and_then(diagnostic_location_from_source),
        metadata: BTreeMap::new(),
    }
}

pub fn invalid_lookup_value(
    model_name: &str,
    field_name: &str,
    lookup: &str,
    field_type: &str,
    argument: &ArgumentSummary,
) -> PluginDiagnostic {
    PluginDiagnostic {
        id: "django-ty.invalid-lookup-value".to_string(),
        message: format!(
            "Invalid Django lookup value for `{lookup}` on `{model_name}.{field_name}`; expected `{field_type}`"
        ),
        severity: DiagnosticSeverity::Error,
        location: argument
            .source
            .as_ref()
            .and_then(diagnostic_location_from_source),
        metadata: BTreeMap::new(),
    }
}

pub fn immutable_querydict_write(source: &SymbolSource) -> PluginDiagnostic {
    PluginDiagnostic {
        id: "django-ty.immutable-querydict-write".to_string(),
        message: "Django request query parameters are immutable".to_string(),
        severity: DiagnosticSeverity::Error,
        location: diagnostic_location_from_source(source),
        metadata: BTreeMap::new(),
    }
}
