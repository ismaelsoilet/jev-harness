//! E0.1 — recorded live System One payloads must parse identically in every runtime.
//! Regression for the v0.1.14 bug where `score: i32` + `legend: Vec` silently dropped
//! every Score answer in live mode (severity/viability/rigor/complexity fell back to defaults).
use jev_harness::JevClient;
use serde_json::json;

const FIXTURE: &str = include_str!("../../../tests/fixtures/systemone_live_score.json");

#[test]
fn parses_live_score_payload_with_probabilities_and_map_legend() {
    let client = JevClient::with_mock();
    let val: serde_json::Value = serde_json::from_str(FIXTURE).expect("fixture is valid JSON");
    let resp = client
        .parse_api_response(&val)
        .expect("live payload must parse");
    assert!(!resp.is_mock);

    let severity = resp
        .answers
        .get("severity")
        .and_then(|a| a.as_score())
        .expect("severity must parse (regression: was dropped)");
    assert!(
        (severity.score - 1.76).abs() < 1e-9,
        "score={}",
        severity.score
    );
    let probs = severity
        .probabilities
        .as_ref()
        .expect("probabilities present");
    assert!((probs.get("1").copied().unwrap_or(0.0) - 0.44).abs() < 1e-9);
    assert!(
        severity
            .legend
            .as_ref()
            .map(|l| l.is_object())
            .unwrap_or(false),
        "map legend preserved"
    );

    let viability = resp
        .answers
        .get("viability")
        .and_then(|a| a.as_score())
        .expect("viability parsed");
    assert!((viability.score - 2.11).abs() < 1e-9);

    let category = resp
        .answers
        .get("category")
        .and_then(|a| a.as_choice())
        .expect("category parsed");
    assert_eq!(category.choice, "env_missing");
    assert!((category.confidence - 0.98).abs() < 1e-9);
}

#[test]
fn accepts_legacy_list_legend_and_integer_scores() {
    let client = JevClient::with_mock();
    let val = json!({
        "model": "jev-test",
        "answers": {
            "severity": {"type": "score", "score": 2, "confidence": 0.9, "legend": ["a", "b", "c"]}
        }
    });
    let resp = client
        .parse_api_response(&val)
        .expect("legacy payload must parse");
    let severity = resp
        .answers
        .get("severity")
        .and_then(|a| a.as_score())
        .expect("severity parsed");
    assert!((severity.score - 2.0).abs() < 1e-9);
    assert!(severity
        .legend
        .as_ref()
        .map(|l| l.is_array())
        .unwrap_or(false));
}
