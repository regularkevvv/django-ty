use std::collections::BTreeMap;

use ty_plugin_sdk::protocol::{BuildProjectIndexRequest, LiteralValue};
use ty_plugin_sdk::serde_json::Value;

pub type SettingsIndex = BTreeMap<String, String>;

pub fn settings_index(request: &BuildProjectIndexRequest) -> SettingsIndex {
    let mut values = BTreeMap::new();
    for module in &request.settings {
        for setting in &module.values {
            let LiteralValue::Str { value } = &setting.value else {
                continue;
            };
            values.insert(setting.name.clone(), value.clone());
            values.insert(format!("{}.{}", module.module, setting.name), value.clone());
            values.insert(
                format!("django.conf.settings.{}", setting.name),
                value.clone(),
            );
            values.insert(format!("settings.{}", setting.name), value.clone());
        }
    }
    values
}

pub fn settings_index_from_project_index(project_index: Option<&Value>) -> SettingsIndex {
    project_index
        .and_then(|index| index.get("settings"))
        .and_then(Value::as_object)
        .map(|settings| {
            settings
                .iter()
                .filter_map(|(key, value)| Some((key.clone(), value.as_str()?.to_string())))
                .collect()
        })
        .unwrap_or_default()
}
