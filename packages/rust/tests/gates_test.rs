use jev_harness::{
    client::JevClient,
    gates::{route_model_tier, should_abort_trajectory, triage_test_failure, verify_step_completion},
};

#[tokio::test]
async fn test_triage_detects_python_missing_module() {
    let client = JevClient::with_mock();
    let res = triage_test_failure("ModuleNotFoundError: No module named 'pandas'", Some(&client))
        .await
        .expect("Triage failed");

    assert_eq!(res.category, "env_missing");
    assert!(res.skip_llm);
    assert!(res.action_recommendation.contains("AUTO-ACTION"));
}

#[tokio::test]
async fn test_triage_detects_typescript_missing_module() {
    let client = JevClient::with_mock();
    let res = triage_test_failure(
        "src/app.ts: error TS2307: Cannot find module '@vue/runtime-core'",
        Some(&client),
    )
    .await
    .expect("Triage failed");

    assert_eq!(res.category, "env_missing");
    assert!(res.skip_llm);
}

#[tokio::test]
async fn test_triage_detects_rust_cant_find_crate() {
    let client = JevClient::with_mock();
    let res = triage_test_failure(
        "error[E0463]: can't find crate for 'serde_json'",
        Some(&client),
    )
    .await
    .expect("Triage failed");

    assert_eq!(res.category, "env_missing");
    assert!(res.skip_llm);
}

#[tokio::test]
async fn test_triage_detects_flaky_transient_network() {
    let client = JevClient::with_mock();
    let res = triage_test_failure(
        "Error: connect ETIMEDOUT 127.0.0.1:5432",
        Some(&client),
    )
    .await
    .expect("Triage failed");

    assert_eq!(res.category, "flaky_transient");
    assert!(res.skip_llm);
    assert!(res.action_recommendation.contains("Retry test once"));
}

#[tokio::test]
async fn test_triage_detects_deep_logic_defect() {
    let client = JevClient::with_mock();
    let res = triage_test_failure(
        "AssertionError: expected { ok: false } to be { ok: true }",
        Some(&client),
    )
    .await
    .expect("Triage failed");

    assert_eq!(res.category, "deep_logic");
    assert!(!res.skip_llm);
    assert!(res.action_recommendation.contains("ESCALATE"));
}

#[tokio::test]
async fn test_abort_gate_detects_circular_loop() {
    let client = JevClient::with_mock();
    let history = "Attempt 1 failed with TypeError\nAttempt 2 failed with TypeError\nAttempt 3 failed with TypeError";
    let res = should_abort_trajectory(
        "Repeat the exact same prompt with no changes",
        history,
        Some(&client),
    )
    .await
    .expect("Abort check failed");

    assert!(res.should_abort);
    assert_eq!(res.action, "abort_and_ask");
}

#[tokio::test]
async fn test_abort_gate_allows_safe_step() {
    let client = JevClient::with_mock();
    let res = should_abort_trajectory(
        "Add unit test verifying edge case handling for empty input array",
        "",
        Some(&client),
    )
    .await
    .expect("Abort check failed");

    assert!(!res.should_abort);
    assert_eq!(res.action, "proceed");
}

#[tokio::test]
async fn test_route_model_tier_deterministic() {
    let client = JevClient::with_mock();
    let res = route_model_tier("Fix typo in variable name in src/utils.rs", Some(&client))
        .await
        .expect("Route failed");

    assert_eq!(res.selected_tier, "deterministic");
    assert!(res.recommended_model.contains("0 LLM Tokens"));
}

#[tokio::test]
async fn test_route_model_tier_heavy_reasoning() {
    let client = JevClient::with_mock();
    let res = route_model_tier(
        "Architect enterprise distributed consensus and transaction deadlock detection kernel",
        Some(&client),
    )
    .await
    .expect("Route failed");

    assert_eq!(res.selected_tier, "heavy_system2");
    assert!(res.recommended_model.contains("Claude Fable 5.1"));
}

#[tokio::test]
async fn test_verify_step_completion() {
    let client = JevClient::with_mock();
    let criteria = "All unit tests must pass and code must be formatted";
    let output = "Unit tests passed with 100% success. Formatter ran clean. Complete.";

    let res = verify_step_completion(criteria, output, Some(&client))
        .await
        .expect("Verify failed");

    assert!(res.is_verified);
    assert!(!res.needs_rework);
}
