//! Compare responses after SDK deserialization, including protocol defaults.
use std::io::BufRead;
use ty_plugin_sdk::protocol::PluginResponse;
use ty_plugin_sdk::serde_json::{self, Value};

#[test]
#[ignore = "requires regression responses from scripts/check-monty-parity.sh"]
fn responses_match_rust_regressions() -> Result<(), Box<dyn std::error::Error>> {
    let path = std::env::var("DJANGO_TY_MONTY_RESPONSES")?;
    let input = std::io::BufReader::new(std::fs::File::open(path)?);
    let mut count = 0;
    for line in input.lines() {
        let record: Value = serde_json::from_str(&line?)?;
        let expected: PluginResponse = serde_json::from_value(record["expected"].clone())?;
        let actual: PluginResponse = serde_json::from_value(record["actual"].clone())?;
        if actual != expected {
            eprintln!("Mismatch at record {count}: {}", record["request"]);
            eprintln!("expected: {}", serde_json::to_string(&expected)?);
            eprintln!("actual: {}", serde_json::to_string(&actual)?);
            return Err("Python/Rust response mismatch".into());
        }
        count += 1;
    }
    if count < 150 {
        return Err("Regression corpus unexpectedly small".into());
    }
    println!("All {count} Python responses match the Rust plugin.");
    Ok(())
}
