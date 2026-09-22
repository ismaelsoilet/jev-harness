use jev_harness::{
    client::JevClient,
    gates::{
        build_provider_params, modulate_reasoning_effort, modulate_reasoning_effort_with_tokens,
        route_model_tier, should_abort_trajectory, triage_test_failure, verify_step_completion,
    },
};

#[tokio::test]
async fn test_triage_detects_python_missing_module() {
    let client = JevClient::with_mock();
    let res = triage_test_failure(
        "ModuleNotFoundError: No module named 'pandas'",
        Some(&client),
    )
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
    let res = triage_test_failure("Error: connect ETIMEDOUT 127.0.0.1:5432", Some(&client))
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

#[tokio::test]
async fn test_adversarial_negated_abort() {
    let client = JevClient::with_mock();
    let res = should_abort_trajectory(
        "Do NOT abort, proceed with database migration steps",
        "Previous step completed migration script",
        Some(&client),
    )
    .await
    .expect("Abort check failed");

    assert!(
        !res.should_abort,
        "Negated abort statement must NOT trigger abort"
    );
    assert_eq!(res.action, "proceed");
}

#[tokio::test]
async fn test_adversarial_assertion_testing_module() {
    let client = JevClient::with_mock();
    let res = triage_test_failure(
        "FAILED tests/test_loader.py::test_missing - AssertionError: expected 'No module named foo' to be raised",
        Some(&client),
    )
    .await
    .expect("Triage failed");

    assert_eq!(
        res.category, "deep_logic",
        "AssertionError must take precedence over substring module names"
    );
    assert!(!res.skip_llm, "Logic failure must NOT skip LLM");
}

#[tokio::test]
async fn test_adversarial_heavy_priority_over_typo() {
    let client = JevClient::with_mock();
    let res = route_model_tier(
        "Architect enterprise distributed kernel allocator and fix typo in docstring",
        Some(&client),
    )
    .await
    .expect("Route failed");

    assert_eq!(
        res.selected_tier, "heavy_system2",
        "Heavy architectural keywords must override typo in routing"
    );
}

#[tokio::test]
async fn test_safe_utf8_truncation() {
    use jev_harness::gates::safe_truncate_head_tail;

    // Construct a string where byte 1400 lands right in the middle of 4-byte emoji 🦀
    let mut s = String::new();
    s.push_str(&"a".repeat(1398));
    s.push_str("🦀🔥⚡");
    s.push_str(&"b".repeat(3000));

    let truncated = safe_truncate_head_tail(&s, 1400, 1400);
    assert!(truncated.contains("... [TRUNCATED"));
    assert!(!truncated.is_empty());

    // Also verify via triage_test_failure
    let client = JevClient::with_mock();
    let triage_res = triage_test_failure(&s, Some(&client)).await;
    assert!(
        triage_res.is_ok(),
        "triage_test_failure must never panic on multi-byte UTF-8 boundaries"
    );
}

#[tokio::test]
async fn test_adversarial_portuguese_and_safe_fallback() {
    let client = JevClient::with_mock();

    let res_assert = triage_test_failure(
        "Falha de asserção: esperava 10 mas obteve 20",
        Some(&client),
    )
    .await
    .expect("Triage failed");
    assert_eq!(res_assert.category, "deep_logic");
    assert!(!res_assert.skip_llm);

    let res_mod = triage_test_failure("Módulo não encontrado: pandas", Some(&client))
        .await
        .expect("Triage failed");
    assert_eq!(res_mod.category, "env_missing");
    assert!(res_mod.skip_llm);

    let res_fallback = triage_test_failure(
        "xyz123 uninformative random text with no keywords",
        Some(&client),
    )
    .await
    .expect("Triage failed");
    assert_eq!(res_fallback.category, "deep_logic");
    assert!(!res_fallback.skip_llm);
}

#[tokio::test]
async fn test_modulate_reasoning_effort_mechanical_bash() {
    let client = JevClient::with_mock();
    let res = modulate_reasoning_effort(
        "Run bash command 'git status' to inspect modified files",
        "openai",
        None,
        Some(&client),
    )
    .await
    .expect("Reasoning effort modulation failed");

    assert_eq!(res.effort, "low");
    assert!(res.is_reasoning_supported);
    assert_eq!(res.provider_params["reasoning_effort"], "low");
}

#[tokio::test]
async fn test_modulate_reasoning_effort_heavy_architecture() {
    let client = JevClient::with_mock();
    let res = modulate_reasoning_effort(
        "Architect enterprise distributed consensus and transaction deadlock detection kernel",
        "anthropic",
        None,
        Some(&client),
    )
    .await
    .expect("Reasoning effort modulation failed");

    assert_eq!(res.effort, "high");
    assert!(res.is_reasoning_supported);
    assert_eq!(res.provider_params["thinking"]["type"], "adaptive");
    assert_eq!(res.provider_params["output_config"]["effort"], "max");
}

#[tokio::test]
async fn test_build_provider_params_dialects() {
    // DeepSeek
    let (ds_low, ds_sup, _, _) =
        build_provider_params("deepseek", "low", Some("deepseek-v4.1-flash"));
    assert!(ds_sup);
    assert_eq!(ds_low["reasoning_effort"], "low");

    let (ds_high, _, _, _) = build_provider_params("deepseek", "high", Some("deepseek-v4-pro"));
    assert_eq!(ds_high["reasoning_effort"], "high");

    // Qwen
    let (qw_low, qw_sup, _, _) = build_provider_params("qwen", "low", Some("qwen-3.8-omni-flash"));
    assert!(qw_sup);
    assert_eq!(qw_low["enable_thinking"], false);

    let (qw_high, _, _, _) = build_provider_params("qwen", "high", Some("qwen-3.8-max"));
    assert_eq!(qw_high["enable_thinking"], true);
    assert_eq!(qw_high["thinking_budget"], 16384);

    // Unsupported model (direct single-pass)
    let (direct_params, direct_sup, rationale, _) =
        build_provider_params("openai", "low", Some("gpt-5.6-luna"));
    assert!(!direct_sup);
    assert_eq!(direct_params, serde_json::json!({}));
    assert!(rationale.contains("direct single-pass model"));
}

#[tokio::test]
async fn test_adversarial_jest_assertion_with_modulenotfound() {
    let client = JevClient::with_mock();
    let jest_log = r#"
FAIL src/plugin.test.ts
  ● Plugin Loader › handles failure gracefully

    expect(received).toBe(expected) // Object.is equality

    Expected: "READY"
    Received: "ModuleNotFoundError: No module named 'foo'"

      18 |     const res = await loader.load();
    > 19 |     expect(res.status).toBe("READY");
"#;
    let res = triage_test_failure(jest_log, Some(&client))
        .await
        .expect("Triage failed");
    assert_eq!(
        res.category, "deep_logic",
        "Jest assertion failure must be classified as deep_logic"
    );
    assert!(!res.skip_llm, "Deep logic failure must NEVER skip LLM");
}

#[tokio::test]
async fn test_adversarial_warning_with_transient_string_does_not_mask_assertion() {
    let client = JevClient::with_mock();
    let log = r#"
test_service.py:10: UserWarning: transient network timeout was safely handled by retry handler
FAILED test_service.py::test_calculation
Calculation returned 42, expected 100
"#;
    let res = triage_test_failure(log, Some(&client))
        .await
        .expect("Triage failed");
    assert_eq!(res.category, "deep_logic");
    assert!(!res.skip_llm);
}

#[tokio::test]
async fn test_adversarial_forward_progress_not_aborted() {
    let client = JevClient::with_mock();
    let res = should_abort_trajectory(
        "Implement the missing function to fix the error",
        "Previous attempt had a compilation error",
        Some(&client),
    )
    .await
    .expect("Abort check failed");
    assert!(
        !res.should_abort,
        "Forward progress implementation must NOT be aborted"
    );
    assert!(res.abort_probability < 0.50);
}

#[tokio::test]
async fn test_adversarial_direct_models_expanded_safeguards() {
    let client = JevClient::with_mock();
    for model in &[
        "gpt-4o",
        "gpt-4o-mini",
        "gpt-4-turbo",
        "claude-3-5-haiku",
        "claude-3-5-sonnet",
        "deepseek-chat",
        "gpt-5.6-luna",
        "codestral",
    ] {
        let res = modulate_reasoning_effort("git status", "openai", Some(model), Some(&client))
            .await
            .expect("Modulation failed");
        assert!(
            !res.is_reasoning_supported,
            "{} must be recognized as non-reasoning direct model",
            model
        );
        assert_eq!(res.provider_params, serde_json::json!({}));
    }
}

#[tokio::test]
async fn test_adversarial_cache_risk_on_high_context() {
    let client = JevClient::with_mock();
    let res = modulate_reasoning_effort_with_tokens(
        "git status",
        "openai",
        Some("o3-mini"),
        45000,
        Some(&client),
    )
    .await
    .expect("Modulation failed");
    assert!(res.is_reasoning_supported);
    assert!(res.cache_safe_recommendation.contains("HIGH CACHE RISK"));
}

#[tokio::test]
async fn test_modulate_reasoning_effort_utf8_char_boundary() {
    let client = JevClient::with_mock();
    // Build string where byte 4000 falls inside multi-byte 🦀 emoji
    let mut context = "a".repeat(3998);
    context.push_str("🦀🔥⚡");
    context.push_str(&"b".repeat(1000));

    let res = modulate_reasoning_effort(&context, "openai", None, Some(&client)).await;
    assert!(
        res.is_ok(),
        "modulate_reasoning_effort must NEVER panic on multi-byte UTF-8 char boundaries"
    );
}

#[tokio::test]
async fn test_adversarial_infinite_loop_timeout_is_deep_logic() {
    let client = JevClient::with_mock();
    let trace = "TimeoutError: infinite loop detected in worker thread while waiting on mutex deadlock";
    let res = triage_test_failure(trace, Some(&client))
        .await
        .expect("Triage failed");
    assert_eq!(
        res.category, "deep_logic",
        "Infinite loops and deadlocks must NOT be classified as flaky transient"
    );
    assert!(
        !res.skip_llm,
        "Deep logic defects must NEVER skip LLM calls"
    );
}
