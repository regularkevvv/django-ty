fn main() {
    println!("{}", manifest_json());
}

fn manifest_json() -> String {
    ty_plugin_sdk::serde_json::to_string_pretty(&django_ty::packaged_manifest())
        .expect("django-ty manifest serializes")
}

#[cfg(test)]
mod tests {
    use ty_plugin_sdk::serde_json::Value;

    use super::manifest_json;

    #[test]
    fn serializes_the_packaged_wasm_manifest() {
        let manifest: Value = ty_plugin_sdk::serde_json::from_str(&manifest_json()).unwrap();

        assert_eq!(manifest["id"], "django-ty");
        assert_eq!(manifest["runtime"]["kind"], "wasm");
        assert_eq!(manifest["runtime"]["artifact"], "django_ty.wasm");
    }
}
