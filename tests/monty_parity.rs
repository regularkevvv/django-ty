//! Compare every raw response field across independent CPython and Monty runs.
use std::io::BufRead;
use ty_plugin_sdk::serde_json::{self, Value};

#[test]
#[ignore = "requires regression responses from scripts/check-monty-parity.sh"]
fn monty_responses_match_cpython() -> Result<(), Box<dyn std::error::Error>> {
    let path = std::env::var("DJANGO_TY_MONTY_RESPONSES")?;
    let input = std::io::BufReader::new(std::fs::File::open(path)?);
    let mut count = 0;
    for line in input.lines() {
        let record: Value = serde_json::from_str(&line?)?;
        let expected = record.get("expected").ok_or("missing CPython response")?;
        let actual = record.get("actual").ok_or("missing Monty response")?;
        if expected.get("kind").and_then(Value::as_str).is_none()
            || actual.get("kind").and_then(Value::as_str).is_none()
        {
            return Err("malformed parity response".into());
        }
        if actual != expected {
            eprintln!("Mismatch at record {count}: {}", record["request"]);
            eprintln!("expected: {}", serde_json::to_string(expected)?);
            eprintln!("actual: {}", serde_json::to_string(actual)?);
            return Err("Monty/CPython response mismatch".into());
        }
        count += 1;
    }
    if count < 150 {
        return Err("Regression corpus unexpectedly small".into());
    }
    println!(
        "All {count} Monty responses match CPython, including opaque indexes and new protocol fields."
    );
    Ok(())
}
