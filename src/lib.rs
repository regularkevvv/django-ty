//! Django semantic plugin for `ty`.
//!
//! The crate intentionally depends only on `ty_plugin_sdk`. It is an external plugin package,
//! not a checker patch, and all Django behavior is expressed through the public protocol hooks.

mod constants;
mod diagnostics;
mod fields;
mod index;
mod plugin;
mod querysets;
mod settings;
mod types;

pub use plugin::DjangoTyPlugin;

pub fn packaged_manifest() -> ty_plugin_sdk::protocol::PluginManifest {
    use ty_plugin_sdk::Plugin;
    use ty_plugin_sdk::protocol::{RuntimeSpec, WasmRuntimeSpec};

    let mut manifest = DjangoTyPlugin.manifest();
    manifest.runtime = RuntimeSpec::Wasm(WasmRuntimeSpec {
        artifact: "django_ty.wasm".to_string(),
        sha256: None,
    });
    manifest
}

ty_plugin_sdk::export_plugin!(DjangoTyPlugin);
