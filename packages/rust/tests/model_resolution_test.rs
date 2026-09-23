//! E0.3 - model pinning: resolution order, reported origin and the payload that reaches the wire.
//! The `.jev.json` path is exercised through the real binary (with its own working directory) so
//! no test changes this process's CWD, which would race with the parallel test threads.
use jev_harness::cli::model_origin_label;
use jev_harness::client::MAX_STATE_CHARS;
use jev_harness::types::{NoulQuestion, Question};
use jev_harness::JevClient;
use std::collections::HashMap;
use std::process::Command;
use std::time::Duration;
use tokio::io::{AsyncReadExt, AsyncWriteExt};
use tokio::net::TcpListener;

fn temp_dir(tag: &str) -> std::path::PathBuf {
    let dir = std::env::temp_dir().join(format!("jev-model-{}-{}", tag, std::process::id()));
    let _ = std::fs::remove_dir_all(&dir);
    std::fs::create_dir_all(&dir).unwrap();
    dir
}

fn status_output_in(dir: &std::path::Path) -> String {
    // Hermetic child: a developer's real credentials (~/.commandcode/auth.json, provider env
    // vars) must not decide which provider this assertion sees.
    let out = Command::new(env!("CARGO_BIN_EXE_jev"))
        .arg("status")
        .arg("--mock")
        .current_dir(dir)
        .env_clear()
        .env("HOME", dir)
        .env("USERPROFILE", dir)
        .output()
        .expect("binary runs");
    String::from_utf8_lossy(&out.stdout).to_string()
}

#[test]
fn explicit_argument_always_wins_and_is_labelled() {
    let (model, source) = JevClient::resolve_model(Some("from-argument".to_string()), "typesafe");
    assert_eq!(model, "from-argument");
    assert_eq!(source, "argument");
}

#[test]
fn provider_default_is_used_when_nothing_pins_the_model() {
    let dir = temp_dir("default");
    let output = status_output_in(&dir);
    assert!(
        output.contains("Model:       jev-latest"),
        "unexpected status output: {}",
        output
    );
    assert!(
        output.contains("Model origin: provider default"),
        "unexpected status output: {}",
        output
    );
    assert!(
        output.contains("moving alias"),
        "the jev-latest alias must warn that it moves: {}",
        output
    );
    let _ = std::fs::remove_dir_all(&dir);
}

#[test]
fn repo_config_pin_is_reported_with_its_origin() {
    let dir = temp_dir("pin");
    std::fs::write(dir.join(".jev.json"), r#"{"model": "jev-1.13.0"}"#).unwrap();
    let output = status_output_in(&dir);
    assert!(
        output.contains("Model:       jev-1.13.0"),
        "the pinned model must be the effective one: {}",
        output
    );
    assert!(
        output.contains("Model origin: repository .jev.json"),
        "the origin must be named: {}",
        output
    );
    let _ = std::fs::remove_dir_all(&dir);
}

#[test]
fn env_var_wins_over_repo_config_and_is_labelled() {
    let previous = std::env::var("JEV_MODEL").ok();
    std::env::set_var("JEV_MODEL", "jev-1.13.0");
    let (model, source) = JevClient::resolve_model(None, "typesafe");
    match previous {
        Some(value) => std::env::set_var("JEV_MODEL", value),
        None => std::env::remove_var("JEV_MODEL"),
    }
    assert_eq!(model, "jev-1.13.0");
    assert_eq!(source, "env");
    assert_eq!(model_origin_label("env"), "JEV_MODEL environment variable");
}

#[test]
fn shadow_masks_gate_failures_but_not_cli_misuse() {
    let dir = temp_dir("shadow-precedence");
    let huge = "x".repeat(MAX_STATE_CHARS + 1);

    let shadowed = Command::new(env!("CARGO_BIN_EXE_jev"))
        .args([
            "route",
            "--provider",
            "opencode",
            "--shadow",
            "--fail-closed",
            "--task",
            &huge,
        ])
        .current_dir(&dir)
        .env_clear()
        .env("HOME", &dir)
        .output()
        .expect("binary runs");
    assert_eq!(
        shadowed.status.code(),
        Some(0),
        "shadow must not break the pipeline on a provider/payload failure: {}",
        String::from_utf8_lossy(&shadowed.stderr)
    );
    assert!(String::from_utf8_lossy(&shadowed.stderr).contains("[SHADOW] would exit 2"));

    let unguarded = Command::new(env!("CARGO_BIN_EXE_jev"))
        .args([
            "route",
            "--provider",
            "opencode",
            "--fail-closed",
            "--task",
            &huge,
        ])
        .current_dir(&dir)
        .env_clear()
        .env("HOME", &dir)
        .output()
        .expect("binary runs");
    assert_eq!(
        unguarded.status.code(),
        Some(2),
        "without shadow the failure is surfaced"
    );

    let misuse = Command::new(env!("CARGO_BIN_EXE_jev"))
        .args(["test-gate", "--shadow", "--log", "/definitely/not/here.log"])
        .current_dir(&dir)
        .env_clear()
        .env("HOME", &dir)
        .output()
        .expect("binary runs");
    assert_eq!(
        misuse.status.code(),
        Some(2),
        "CLI misuse is not a gate outcome and must stay 2"
    );

    let _ = std::fs::remove_dir_all(&dir);
}

#[tokio::test]
async fn pinned_model_is_the_one_sent_in_the_request_payload() {
    let listener = TcpListener::bind("127.0.0.1:0").await.unwrap();
    let addr = listener.local_addr().unwrap();
    let server = tokio::spawn(async move {
        let (mut sock, _) = listener.accept().await.unwrap();
        let mut buf = vec![0u8; 8192];
        let read = sock.read(&mut buf).await.unwrap();
        let body = String::from_utf8_lossy(&buf[..read]).to_string();
        let payload = r#"{"model":"jev-test","answers":{"q":{"type":"noul","noul":0.9}},"usage":{"input_tokens":1,"output_tokens":1}}"#;
        let response = format!(
            "HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nContent-Length: {}\r\nConnection: close\r\n\r\n{}",
            payload.len(),
            payload
        );
        let _ = sock.write_all(response.as_bytes()).await;
        let _ = sock.flush().await;
        body
    });

    let mut client = JevClient::new(
        Some("test-key".to_string()),
        None,
        Some("jev-1.13.0".to_string()),
        None,
        false,
    );
    client.base_url = format!("http://{}/v1/systemone", addr);
    let mut questions = HashMap::new();
    questions.insert(
        "q".to_string(),
        Question::Noul(NoulQuestion {
            instructions: "x".into(),
        }),
    );
    let _ = client.system_one("state", questions).await;

    let request = tokio::time::timeout(Duration::from_secs(5), server)
        .await
        .expect("server finished")
        .expect("request captured");
    assert!(
        request.contains(r#""model":"jev-1.13.0""#),
        "the request must carry the pinned model: {}",
        request
    );
}
