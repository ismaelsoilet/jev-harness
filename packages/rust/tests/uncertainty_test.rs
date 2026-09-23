//! E3.1 — the uncertainty math must be identical in Python, TypeScript and Rust.
use jev_harness::uncertainty::{
    build_uncertainty, distribution_shape, normalize_level_keys, validate_question_options,
    LOW_CONFIDENCE_THRESHOLD,
};
use serde_json::Value;
use std::collections::HashMap;

const FIXTURE: &str = include_str!("../../../tests/fixtures/uncertainty_golden.json");

fn fixture() -> Value {
    serde_json::from_str(FIXTURE).expect("golden fixture is valid JSON")
}

fn probabilities(value: &Value) -> HashMap<String, f64> {
    value
        .as_object()
        .expect("probabilities object")
        .iter()
        .map(|(key, value)| (key.clone(), value.as_f64().unwrap_or(f64::NAN)))
        .collect()
}

fn nearly(actual: Option<f64>, expected: Option<f64>, label: &str) {
    match expected {
        None => assert!(actual.is_none(), "{label}: expected None, got {actual:?}"),
        Some(want) => {
            let got = actual.unwrap_or_else(|| panic!("{label}: expected {want}, got None"));
            assert!((got - want).abs() < 1e-8, "{label}: {got} != {want}");
        }
    }
}

#[test]
fn shape_metrics_match_the_golden_vectors() {
    let fx = fixture();
    for (name, vector) in fx["vectors"].as_object().expect("vectors") {
        let shape = distribution_shape(Some(&probabilities(&vector["probabilities"])));
        assert_eq!(
            shape.levels,
            vector["shape"]["levels"]
                .as_u64()
                .map(|value| value as usize),
            "{name} levels"
        );
        nearly(
            shape.margin,
            vector["shape"]["margin"].as_f64(),
            &format!("{name} margin"),
        );
        nearly(
            shape.normalized_entropy,
            vector["shape"]["normalized_entropy"].as_f64(),
            &format!("{name} entropy"),
        );
    }
}

#[test]
fn escalation_precedence_matches_the_golden_vectors() {
    let fx = fixture();
    for (key, case) in fx["escalation"].as_object().expect("escalation") {
        let expected = &case["expected"];
        let result = build_uncertainty(
            Some(&probabilities(&case["probabilities"])),
            case["confidence"].as_f64(),
            case["category"].as_str().unwrap_or(""),
            LOW_CONFIDENCE_THRESHOLD,
        );
        assert_eq!(
            result.escalate_to_system2,
            expected["escalate_to_system2"].as_bool().unwrap(),
            "{key}"
        );
        nearly(
            result.margin,
            expected["margin"].as_f64(),
            &format!("{key} margin"),
        );
        nearly(
            result.normalized_entropy,
            expected["normalized_entropy"].as_f64(),
            &format!("{key} entropy"),
        );
        nearly(
            result.confidence,
            expected["confidence"].as_f64(),
            &format!("{key} confidence"),
        );
    }
}

#[test]
fn guards_cover_zeros_single_level_and_both_key_conventions() {
    let mut with_zeros = HashMap::new();
    with_zeros.insert("0".to_string(), 0.7);
    with_zeros.insert("1".to_string(), 0.3);
    with_zeros.insert("2".to_string(), 0.0);
    let shape = distribution_shape(Some(&with_zeros));
    assert_eq!(
        shape.levels,
        Some(2),
        "a zero-probability level is not a level"
    );
    nearly(shape.margin, Some(0.4), "zeros margin");

    let mut single = HashMap::new();
    single.insert("1".to_string(), 1.0);
    assert!(distribution_shape(Some(&single))
        .normalized_entropy
        .is_none());
    assert!(distribution_shape(None).margin.is_none());

    let mut zero_based = HashMap::new();
    zero_based.insert("0".to_string(), 0.5);
    zero_based.insert("1".to_string(), 0.5);
    let mut one_based = HashMap::new();
    one_based.insert("1".to_string(), 0.5);
    one_based.insert("2".to_string(), 0.5);
    let mut zero_keys: Vec<usize> = normalize_level_keys(&zero_based).keys().copied().collect();
    let mut one_keys: Vec<usize> = normalize_level_keys(&one_based).keys().copied().collect();
    zero_keys.sort();
    one_keys.sort();
    assert_eq!(zero_keys, one_keys);
}

#[test]
fn threshold_line_and_single_option_rejection() {
    assert!((LOW_CONFIDENCE_THRESHOLD - 0.65).abs() < 1e-12);
    assert!(
        build_uncertainty(None, Some(0.64), "route", LOW_CONFIDENCE_THRESHOLD).escalate_to_system2
    );
    assert!(
        !build_uncertainty(None, Some(0.66), "route", LOW_CONFIDENCE_THRESHOLD).escalate_to_system2
    );
    assert!(validate_question_options(1).is_err());
    assert!(validate_question_options(2).is_ok());
}
