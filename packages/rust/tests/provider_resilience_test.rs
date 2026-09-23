//! E0.2 - provider resilience: retry with backoff, Retry-After, fail-open/fail-closed.
//! Runs a local TCP server so the retry/fallback policy is exercised end to end.
use jev_harness::client::MAX_STATE_CHARS;
use jev_harness::types::{NoulQuestion, Question};
use jev_harness::{JevClient, JevError};
use serde_json::json;
use std::collections::HashMap;
use std::time::Duration;
use tokio::io::{AsyncReadExt, AsyncWriteExt};
use tokio::net::TcpListener;

const SUCCESS_BODY: &str = r#"{"model":"jev-test","answers":{"q":{"type":"noul","noul":0.9}},"usage":{"input_tokens":1,"output_tokens":1}}"#;

fn http_429() -> String {
    "HTTP/1.1 429 Too Many Requests\r\nRetry-After: 0\r\nContent-Length: 0\r\nConnection: close\r\n\r\n".to_string()
}
fn http_500() -> String {
    "HTTP/1.1 500 Internal Server Error\r\nContent-Length: 0\r\nConnection: close\r\n\r\n"
        .to_string()
}
fn http_401() -> String {
    "HTTP/1.1 401 Unauthorized\r\nContent-Length: 0\r\nConnection: close\r\n\r\n".to_string()
}
fn http_200() -> String {
    format!(
        "HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nContent-Length: {}\r\nConnection: close\r\n\r\n{}",
        SUCCESS_BODY.len(),
        SUCCESS_BODY
    )
}

async fn spawn_server(responses: Vec<String>) -> (String, tokio::task::JoinHandle<usize>) {
    let listener = TcpListener::bind("127.0.0.1:0").await.unwrap();
    let addr = listener.local_addr().unwrap();
    let handle = tokio::spawn(async move {
        let mut count = 0usize;
        for body in responses {
            let (mut sock, _) = listener.accept().await.unwrap();
            let mut buf = [0u8; 8192];
            let _ = sock.read(&mut buf).await;
            let _ = sock.write_all(body.as_bytes()).await;
            let _ = sock.flush().await;
            drop(sock);
            count += 1;
        }
        count
    });
    (format!("http://{}/v1/systemone", addr), handle)
}

fn client(url: &str, fail_open: bool) -> JevClient {
    let mut c = JevClient::with_provider("typesafe", Some("test-key".to_string()))
        .with_failure_policy(fail_open, 3, 0);
    c.base_url = url.to_string();
    c
}

fn questions() -> HashMap<String, Question> {
    let mut q = HashMap::new();
    q.insert(
        "q".to_string(),
        Question::Noul(NoulQuestion {
            instructions: "x".into(),
        }),
    );
    q
}

#[tokio::test]
async fn retries_429_then_succeeds_live() {
    let (url, server) = spawn_server(vec![http_429(), http_200()]).await;
    let c = client(&url, true);
    let resp = c
        .system_one("state", questions())
        .await
        .expect("should succeed after one retry");
    assert!(!resp.is_mock);
    assert_eq!(resp.degraded_reason, "");
    let seen = tokio::time::timeout(Duration::from_secs(5), server)
        .await
        .expect("server finished")
        .unwrap();
    assert_eq!(seen, 2);
}

#[tokio::test]
async fn repeated_429_falls_back_marked() {
    let (url, server) = spawn_server(vec![http_429(), http_429(), http_429()]).await;
    let c = client(&url, true);
    let resp = c
        .system_one("state", questions())
        .await
        .expect("fail-open must return a decision");
    assert!(resp.is_mock);
    assert_eq!(resp.degraded_reason, "http_429");
    let seen = tokio::time::timeout(Duration::from_secs(5), server)
        .await
        .expect("server finished")
        .unwrap();
    assert_eq!(seen, 3);
}

#[tokio::test]
async fn fail_closed_returns_error_on_5xx() {
    let (url, _server) = spawn_server(vec![http_500(), http_500(), http_500()]).await;
    let c = client(&url, false);
    let err = c
        .system_one("state", questions())
        .await
        .expect_err("fail-closed must error");
    match err {
        JevError::Api { status, .. } => assert_eq!(status, 500),
        other => panic!("expected JevError::Api, got {}", other),
    }
}

#[tokio::test]
async fn auth_failure_falls_back_immediately() {
    let (url, server) = spawn_server(vec![http_401()]).await;
    let c = client(&url, true);
    let resp = c
        .system_one("state", questions())
        .await
        .expect("auth failure degrades");
    assert!(resp.is_mock);
    assert_eq!(resp.degraded_reason, "auth_401");
    let seen = tokio::time::timeout(Duration::from_secs(5), server)
        .await
        .expect("server finished")
        .unwrap();
    assert_eq!(seen, 1);
}

async fn spawn_silent_server() -> (String, tokio::task::JoinHandle<()>) {
    let listener = TcpListener::bind("127.0.0.1:0").await.unwrap();
    let addr = listener.local_addr().unwrap();
    let handle = tokio::spawn(async move {
        let (mut sock, _) = listener.accept().await.unwrap();
        let mut buf = [0u8; 8192];
        let _ = sock.read(&mut buf).await;
        // Hold the connection open without ever responding.
        tokio::time::sleep(Duration::from_secs(10)).await;
        let _ = sock.shutdown().await;
    });
    (format!("http://{}/v1/systemone", addr), handle)
}

#[tokio::test]
async fn read_timeout_is_marked_as_timeout() {
    let (url, _server) = spawn_silent_server().await;
    let c = JevClient::new(
        Some("test-key".to_string()),
        Some(url),
        Some("jev-test".to_string()),
        Some(300),
        false,
    )
    .with_failure_policy(true, 1, 0);
    let started = std::time::Instant::now();
    let resp = c
        .system_one("state", questions())
        .await
        .expect("fail-open must return a decision");
    assert!(resp.is_mock);
    assert_eq!(resp.degraded_reason, "timeout");
    assert!(started.elapsed() < Duration::from_secs(5), "must not hang");
}

#[tokio::test]
async fn invalid_json_body_degrades_marked() {
    let (url, _server) = spawn_server(vec![
        "HTTP/1.1 200 OK\r\nContent-Type: text/html\r\nContent-Length: 20\r\nConnection: close\r\n\r\n<html>gateway</html>".to_string(),
    ])
    .await;
    let c = JevClient::new(
        Some("test-key".to_string()),
        Some(url),
        Some("jev-test".to_string()),
        Some(2000),
        false,
    )
    .with_failure_policy(true, 1, 0);
    let resp = c.system_one("state", questions()).await.expect("degrades");
    assert!(resp.is_mock);
    assert_eq!(resp.degraded_reason, "invalid_response");
}

#[tokio::test]
async fn fail_closed_errors_on_401_without_retry() {
    let (url, server) = spawn_server(vec![http_401()]).await;
    let c = JevClient::new(
        Some("test-key".to_string()),
        Some(url),
        Some("jev-test".to_string()),
        Some(2000),
        false,
    )
    .with_failure_policy(false, 3, 0);
    let err = c
        .system_one("state", questions())
        .await
        .expect_err("strict auth must error");
    match err {
        JevError::Api { status, .. } => assert_eq!(status, 401),
        other => panic!("expected JevError::Api, got {}", other),
    }
    let seen = tokio::time::timeout(Duration::from_secs(5), server)
        .await
        .expect("server finished")
        .unwrap();
    assert_eq!(seen, 1);
}

#[tokio::test]
async fn unicode_state_counts_code_points_not_bytes() {
    let mut c =
        JevClient::with_provider("typesafe", Some("k".to_string())).with_failure_policy(true, 1, 0);
    c.base_url = "http://127.0.0.1:9/v1/systemone".to_string();
    let big = "é".repeat(MAX_STATE_CHARS - 1); // 2 bytes per char in UTF-8
    let resp = c
        .system_one(&big, questions())
        .await
        .expect("code-point count accepted; dead endpoint degrades");
    assert!(resp.is_mock);
}

fn http_200_with(body: &str) -> String {
    format!(
        "HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nContent-Length: {}\r\nConnection: close\r\n\r\n{}",
        body.len(),
        body
    )
}

#[test]
fn malformed_payload_is_a_parse_error_not_a_silently_dropped_answer() {
    let c = JevClient::with_mock();
    let malformed = json!({
        "model": "jev-test",
        "answers": {"severity": {"type": "score", "score": "N/A", "confidence": 0.5}}
    });
    let err = c
        .parse_api_response(&malformed)
        .expect_err("a type-mismatched answer must not be dropped silently");
    assert!(format!("{}", err).contains("malformed response"), "{err}");

    let not_an_object = json!({"model": "jev-test", "answers": [{"type": "score", "score": 1.0}]});
    assert!(c.parse_api_response(&not_an_object).is_err());

    let no_answers = json!({"model": "jev-test", "answers": {}});
    assert!(c.parse_api_response(&no_answers).is_err());

    // A valid answer next to an uninterpretable one must not hide the bad one.
    let mixed = json!({
        "model": "jev-test",
        "answers": {
            "category": {"type": "choice", "choice": "env_missing", "confidence": 0.98},
            "skip_llm": {"type": "noul", "noul": 0.9},
            "severity": {"type": "score_v2", "value": 3}
        }
    });
    assert!(c.parse_api_response(&mixed).is_err());

    for payload in [
        json!({"answers": {"q": {"type": "score"}}}),
        json!({"answers": {"q": {"type": "score", "score": "1.0", "confidence": 0.9}}}),
        json!({"answers": {"q": {"score": 1.0, "confidence": 0.5}}}),
        json!({"answers": {"q": "boom"}}),
    ] {
        assert!(
            c.parse_api_response(&payload).is_err(),
            "must reject {payload}"
        );
    }
}

#[tokio::test]
async fn malformed_provider_payload_degrades_and_is_marked() {
    let malformed = r#"{"model":"jev-test","answers":{"severity":{"type":"score","score":"N/A","confidence":0.5}}}"#;
    let (url, server) = spawn_server(vec![
        http_200_with(malformed),
        http_200_with(malformed),
        http_200_with(malformed),
    ])
    .await;
    let c = client(&url, true);
    let resp = c
        .system_one("state", questions())
        .await
        .expect("fail-open must degrade, never crash");
    assert!(resp.is_mock);
    assert_eq!(resp.degraded_reason, "invalid_response");
    let seen = tokio::time::timeout(Duration::from_secs(5), server)
        .await
        .expect("server finished")
        .unwrap();
    assert_eq!(
        seen, 3,
        "a malformed payload retries like a bad status before degrading"
    );
}

#[tokio::test]
async fn malformed_provider_payload_raises_under_fail_closed() {
    let malformed = r#"{"model":"jev-test","answers":{"severity":{"type":"score","score":"N/A","confidence":0.5}}}"#;
    let (url, _server) = spawn_server(vec![http_200_with(malformed)]).await;
    let c = client(&url, false).with_failure_policy(false, 1, 0);
    let err = c
        .system_one("state", questions())
        .await
        .expect_err("fail-closed must surface the malformed payload");
    assert!(format!("{}", err).contains("malformed response"), "{err}");
}

#[test]
fn retry_delay_honors_retry_after_and_caps_backoff() {
    let c =
        JevClient::with_provider("typesafe", Some("k".into())).with_failure_policy(true, 3, 500);
    assert_eq!(c.retry_delay_ms(1, Some(2.0)), 2000);
    assert_eq!(c.retry_delay_ms(1, Some(1.5)), 1500); // fractional seconds, as in Python/TS
    assert_eq!(c.retry_delay_ms(1, Some(999.0)), 30_000); // capped
    assert_eq!(c.retry_delay_ms(1, Some(-1.0)), 500); // ignored
    assert_eq!(c.retry_delay_ms(1, None), 500);
    assert_eq!(c.retry_delay_ms(9, None), 5000); // capped
}

#[test]
fn credential_shaped_material_is_masked_before_the_state_leaves() {
    use jev_harness::client::redact_secrets;

    let secrets = [
        (
            "api key",
            r#"api_key = "vck_live_9f8a7b6c5d4e3f2a1b0c""#,
            "vck_live_9f8a7b6c5d4e3f2a1b0c",
        ),
        (
            "bearer jwt",
            "Authorization: Bearer eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxIn0.abcdefghijklmnop",
            "eyJhbGciOiJIUzI1NiJ9",
        ),
        (
            "github token",
            "token ghp_AAAAAAAAAAAAAAAAAAAAAAAA",
            "ghp_AAAAAAAAAAAAAAAAAAAAAAAA",
        ),
        ("aws key", "AKIAIOSFODNN7EXAMPLE", "AKIAIOSFODNN7EXAMPLE"),
        (
            "database url",
            "postgres://admin:hunter2@db.internal:5432/app",
            "hunter2",
        ),
    ];
    for (name, secret, fragment) in secrets {
        let cleaned = redact_secrets(secret);
        assert!(cleaned.contains("[REDACTED"), "{name}: {cleaned}");
        assert!(!cleaned.contains(fragment), "{name} leaked {fragment}");
    }
    let plain = "AssertionError: assert 4 == 5";
    assert_eq!(redact_secrets(plain), plain);
}
