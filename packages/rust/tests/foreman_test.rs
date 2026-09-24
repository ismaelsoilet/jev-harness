//! Foreman integration parity tests (change `foreman-integration`).
//!
//! The golden values live in `tests/fixtures/foreman_cases.json`, shared verbatim with the Python
//! and TypeScript suites. Capability matrix: `recovery` is Python-only, so this runtime always
//! yields `recovery: None` — a declared divergence, never a silently absent field.
use jev_harness::client::JevClient;
use jev_harness::foreman::{
    evaluate_worker_health, extract_test_results, find_assertion_line, ForemanSnapshot,
    FOREMAN_COMPANION_CLASS_SOURCE, FOREMAN_OPERATOR_README, FOREMAN_RESPONSIBILITY_TOML,
    FOREMAN_SCHEMA_VERSION, STAGNANT_EVIDENCE,
};
use serde_json::Value;

const CASES: &str = include_str!("../../../tests/fixtures/foreman_cases.json");
const TOML_FIXTURE: &str = include_str!("../../../tests/fixtures/foreman_responsibility.toml");
const README_FIXTURE: &str = include_str!("../../../tests/fixtures/foreman_operator_readme.md");
const CLASS_SOURCE: &str = include_str!("../../../src/jev_harness/integrations/foreman_responsibility.py");

#[tokio::test]
async fn triage_cases_match_the_shared_golden_values() {
    let cases: Value = serde_json::from_str(CASES).expect("fixture is valid JSON");
    for case in cases["triage_cases"].as_array().expect("triage_cases array") {
        let name = case["name"].as_str().unwrap();
        let stdout = case["stdout"].as_str().unwrap();
        let stderr = case["stderr"].as_str().unwrap();
        let records = extract_test_results(stdout, stderr, None, None)
            .await
            .expect("offline triage must not fail");
        let expected = &case["expect"];

        assert_eq!(
            records.len(),
            expected["records"].as_u64().unwrap() as usize,
            "{name}"
        );
        if records.is_empty() {
            continue;
        }
        let record = &records[0];
        assert_eq!(record.category, expected["category"].as_str().unwrap(), "{name}");
        assert_eq!(record.skip_llm, expected["skip_llm"].as_bool().unwrap(), "{name}");
        assert_eq!(
            record.action_recommendation,
            expected["action_recommendation"].as_str().unwrap(),
            "{name}"
        );
        assert_eq!(
            record.assertion_slice,
            expected["assertion_slice"].as_str().unwrap(),
            "{name}"
        );
        assert!(
            (record.severity_score - expected["severity_score"].as_f64().unwrap()).abs() < 1e-9,
            "{name}"
        );
        assert!(
            (record.confidence - expected["confidence"].as_f64().unwrap()).abs() < 1e-9,
            "{name}"
        );
        assert_eq!(record.foreman_schema_version, FOREMAN_SCHEMA_VERSION);
        assert!(record.recovery.is_none(), "declared divergence: recovery is Python-only ({name})");
    }
}

#[test]
fn health_cases_match_the_shared_golden_values() {
    let cases: Value = serde_json::from_str(CASES).expect("fixture is valid JSON");
    for case in cases["health_cases"].as_array().expect("health_cases array") {
        let name = case["name"].as_str().unwrap();
        let snapshots: Vec<ForemanSnapshot> = case["snapshots"]
            .as_array()
            .unwrap()
            .iter()
            .map(|snapshot| ForemanSnapshot {
                output: snapshot["output"].as_str().unwrap().to_string(),
                diff: snapshot["diff"].as_str().map(|diff| diff.to_string()),
            })
            .collect();
        let window = case["window"].as_u64().unwrap() as usize;
        let verdict = evaluate_worker_health(&snapshots, window);
        let expected = &case["expect"];

        assert_eq!(verdict.should_abort, expected["should_abort"].as_bool().unwrap(), "{name}");
        assert_eq!(verdict.reason, expected["reason"].as_str().unwrap(), "{name}");
        assert_eq!(
            verdict.evidence.complete_signals,
            expected["complete_signals"].as_bool().unwrap(),
            "{name}"
        );
        assert_eq!(
            verdict.evidence.insufficient_history,
            expected["insufficient_history"].as_bool().unwrap(),
            "{name}"
        );
        assert_eq!(
            verdict.evidence.stagnant_output,
            expected["stagnant_output"].as_bool().unwrap(),
            "{name}"
        );
        assert_eq!(
            verdict.evidence.stagnant_diff,
            expected["stagnant_diff"].as_bool().unwrap(),
            "{name}"
        );
    }
}

#[test]
fn stagnation_reason_constant_is_shared() {
    let cases: Value = serde_json::from_str(CASES).expect("fixture is valid JSON");
    let case = cases["health_cases"]
        .as_array()
        .unwrap()
        .iter()
        .find(|case| case["name"] == "stagnant_output_and_diff")
        .expect("fixture carries the stagnant case");
    let snapshots: Vec<ForemanSnapshot> = case["snapshots"]
        .as_array()
        .unwrap()
        .iter()
        .map(|snapshot| ForemanSnapshot {
            output: snapshot["output"].as_str().unwrap().to_string(),
            diff: snapshot["diff"].as_str().map(|diff| diff.to_string()),
        })
        .collect();
    let verdict = evaluate_worker_health(&snapshots, 5);
    assert_eq!(verdict.reason, STAGNANT_EVIDENCE);
}

#[test]
fn find_assertion_line_ports_the_perception_primitive() {
    assert_eq!(
        find_assertion_line("collected 1 item\nE   ModuleNotFoundError: No module named 'requests'"),
        Some("E   ModuleNotFoundError: No module named 'requests'".to_string())
    );
    assert_eq!(find_assertion_line("12 passed in 0.31s"), None);
    assert_eq!(find_assertion_line(""), None);
}

#[test]
fn canonical_artifacts_are_byte_identical() {
    assert_eq!(FOREMAN_RESPONSIBILITY_TOML, TOML_FIXTURE);
    assert_eq!(FOREMAN_OPERATOR_README, README_FIXTURE);
    assert_eq!(FOREMAN_COMPANION_CLASS_SOURCE, CLASS_SOURCE);
}

#[test]
fn cli_export_writes_the_bundle_and_refuses_run_state() {
    let binary = env!("CARGO_BIN_EXE_jev-harness");
    let base = std::env::temp_dir().join(format!("jev-foreman-cli-{}", std::process::id()));
    let _ = std::fs::remove_dir_all(&base);
    let bundle = base.join("bundle");

    let status = std::process::Command::new(binary)
        .args(["export", "foreman", "--out-dir"])
        .arg(&bundle)
        .status()
        .expect("binary runs");
    assert!(status.success());
    assert_eq!(
        std::fs::read_to_string(bundle.join("quality.jev-triage.toml")).unwrap(),
        FOREMAN_RESPONSIBILITY_TOML
    );
    assert_eq!(
        std::fs::read_to_string(bundle.join("quality_jev_triage.py")).unwrap(),
        FOREMAN_COMPANION_CLASS_SOURCE
    );
    assert_eq!(
        std::fs::read_to_string(bundle.join("README.md")).unwrap(),
        FOREMAN_OPERATOR_README
    );

    let refused = base.join(".foreman").join("responsibilities");
    let status = std::process::Command::new(binary)
        .args(["export", "foreman", "--out-dir"])
        .arg(&refused)
        .status()
        .expect("binary runs");
    assert_eq!(status.code(), Some(2), "a .foreman/ target must be refused");
    assert!(!refused.exists(), "nothing may be written into run state");

    let _ = std::fs::remove_dir_all(&base);
}

#[test]
fn capability_matrix_declares_the_recovery_divergence() {
    let cases: Value = serde_json::from_str(CASES).expect("fixture is valid JSON");
    let matrix = &cases["capability_matrix"];
    assert!(matrix["python"]
        .as_array()
        .unwrap()
        .iter()
        .any(|key| key.as_str() == Some("recovery")));
    assert!(!matrix["rust"]
        .as_array()
        .unwrap()
        .iter()
        .any(|key| key.as_str() == Some("recovery")));
    // The struct exposes the field so it is never silently absent from the record shape.
    let record = jev_harness::foreman::ForemanTriageRecord {
        category: "env_missing".to_string(),
        severity_score: 1.0,
        confidence: 1.0,
        skip_llm: true,
        action_recommendation: String::new(),
        assertion_slice: String::new(),
        recovery: None,
        is_mock: true,
        degraded_reason: String::new(),
        foreman_schema_version: FOREMAN_SCHEMA_VERSION,
    };
    assert!(record.recovery.is_none());
}

#[test]
fn offline_triage_accepts_an_explicit_mock_client() {
    let client = JevClient::with_mock();
    let runtime = tokio::runtime::Builder::new_current_thread().enable_all().build().unwrap();
    let records = runtime
        .block_on(extract_test_results(
            "E   ModuleNotFoundError: No module named 'requests'",
            "",
            Some("/tmp/scope"),
            Some(&client),
        ))
        .expect("triage runs");
    assert_eq!(records.len(), 1);
    assert_eq!(records[0].category, "env_missing");
}
