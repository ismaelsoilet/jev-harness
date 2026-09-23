//! E0.3/E1.1 - payload limits and shadow mode (decide without acting).
use jev_harness::cli::shadow_exit;
use jev_harness::client::MAX_STATE_CHARS;
use jev_harness::types::{NoulQuestion, Question};
use jev_harness::JevClient;
use std::collections::HashMap;

#[test]
fn shadow_exit_never_blocks() {
    assert_eq!(shadow_exit(true, 1), 0);
    assert_eq!(shadow_exit(true, 0), 0);
    assert_eq!(shadow_exit(false, 1), 1);
}

#[tokio::test]
async fn oversized_state_is_rejected_before_network() {
    let client = JevClient::with_provider("typesafe", Some("k".into()));
    let mut q = HashMap::new();
    q.insert(
        "q".to_string(),
        Question::Noul(NoulQuestion {
            instructions: "x".into(),
        }),
    );
    let big = "x".repeat(MAX_STATE_CHARS + 1);
    let err = client
        .system_one(&big, q)
        .await
        .expect_err("must reject oversized state");
    assert!(format!("{}", err).contains("exceeds"));
}

#[tokio::test]
async fn exact_state_limit_is_accepted() {
    let mut client =
        JevClient::with_provider("typesafe", Some("k".into())).with_failure_policy(true, 1, 0);
    client.base_url = "http://127.0.0.1:9/v1/systemone".to_string();
    let mut q = HashMap::new();
    q.insert(
        "q".to_string(),
        Question::Noul(NoulQuestion {
            instructions: "x".into(),
        }),
    );
    let state = "x".repeat(MAX_STATE_CHARS);
    let resp = client
        .system_one(&state, q)
        .await
        .expect("the boundary is inclusive of the limit");
    assert!(
        resp.is_mock,
        "accepted by the guard, degraded by the dead endpoint"
    );
}

#[test]
fn jev_json_shadow_key_is_parsed() {
    let dir = std::env::temp_dir().join(format!("jev-shadow-test-{}", std::process::id()));
    let _ = std::fs::create_dir_all(&dir);
    let config = dir.join(".jev.json");
    std::fs::write(&config, r#"{"shadow": true}"#).unwrap();
    let parsed = jev_harness::config::load_repo_config_from(&dir);
    assert!(parsed.shadow);
    std::fs::write(&config, r#"{"shadow": "yes"}"#).unwrap();
    let ignored = jev_harness::config::load_repo_config_from(&dir);
    assert!(!ignored.shadow);
    let _ = std::fs::remove_dir_all(&dir);
}
