//! Record the existing regression suite's protocol traffic for the Python port.
use std::io::Write;
use std::sync::Mutex;

use ty_plugin_sdk::Plugin;
use ty_plugin_sdk::protocol::{
    AnalyzeClassRequest, BuildProjectIndexRequest, CallRequest, MutationRequest, PluginManifest,
    PluginRequest, PluginResponse,
};
use ty_plugin_sdk::serde_json::json;

pub struct DjangoTyPlugin;
static RECORD_LOCK: Mutex<()> = Mutex::new(());

fn record(request: PluginRequest, response: PluginResponse) -> PluginResponse {
    if let Ok(path) = std::env::var("DJANGO_TY_ORACLE_PATH") {
        let _guard = RECORD_LOCK.lock().unwrap();
        let mut file = std::fs::OpenOptions::new()
            .create(true)
            .append(true)
            .open(path)
            .unwrap();
        writeln!(
            file,
            "{}",
            json!({"request": request, "expected": response})
        )
        .unwrap();
    }
    response
}

impl Plugin for DjangoTyPlugin {
    fn manifest(&self) -> PluginManifest {
        django_ty::DjangoTyPlugin.manifest()
    }
    fn build_project_index(&self, request: &BuildProjectIndexRequest) -> PluginResponse {
        record(
            PluginRequest::BuildProjectIndex(request.clone()),
            django_ty::DjangoTyPlugin.build_project_index(request),
        )
    }
    fn analyze_class(&self, request: &AnalyzeClassRequest) -> PluginResponse {
        record(
            PluginRequest::AnalyzeClass(request.clone()),
            django_ty::DjangoTyPlugin.analyze_class(request),
        )
    }
    fn adjust_call_return(&self, request: &CallRequest) -> PluginResponse {
        record(
            PluginRequest::AdjustCallReturn(request.clone()),
            django_ty::DjangoTyPlugin.adjust_call_return(request),
        )
    }
    fn adjust_call_state(&self, request: &CallRequest) -> PluginResponse {
        record(
            PluginRequest::AdjustCallState(request.clone()),
            django_ty::DjangoTyPlugin.adjust_call_state(request),
        )
    }
    fn adjust_call_signature(&self, request: &CallRequest) -> PluginResponse {
        record(
            PluginRequest::AdjustCallSignature(request.clone()),
            django_ty::DjangoTyPlugin.adjust_call_signature(request),
        )
    }
    fn validate_mutation(&self, request: &MutationRequest) -> PluginResponse {
        record(
            PluginRequest::ValidateMutation(Box::new(request.clone())),
            django_ty::DjangoTyPlugin.validate_mutation(request),
        )
    }
}
