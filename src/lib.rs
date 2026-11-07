//! Native regression oracle for Django Monty semantics.
//! Consumer wheels execute Python hooks through the published companion.

mod apps;
mod constants;
mod diagnostics;
mod fields;
mod index;
mod plugin;
mod querysets;
mod settings;
mod state;
mod types;

pub use plugin::DjangoTyPlugin;

pub fn packaged_manifest() -> ty_plugin_sdk::protocol::PluginManifest {
    use ty_plugin_sdk::Plugin;
    use ty_plugin_sdk::protocol::{MontyRuntimeSpec, RuntimeSpec};

    let mut manifest = DjangoTyPlugin.manifest();
    // Keep the semantic oracle on its original SDK while matching the packaged
    // plugin protocol. Optional wire fields are covered by the Python SDK tests.
    manifest.protocol_version.minor = 8;
    manifest.runtime = RuntimeSpec::Monty(MontyRuntimeSpec {
        artifact: "monty.py".to_string(),
        sha256: None,
    });
    manifest
}
