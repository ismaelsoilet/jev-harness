//! Tri-runtime parity lock covering every gate: the Rust offline mock must reach exactly the same
//! verdicts as the Python runtime recorded in `tests/fixtures/corpus_parity.json`.
//! The logs themselves stay in `tests/corpus` (this file only carries the verdicts).
use jev_harness::gates::{
    modulate_reasoning_effort, route_model_tier, should_abort_trajectory,
    should_nudge_continuation, triage_test_failure, verify_step_completion,
};
use jev_harness::JevClient;
use serde_json::{json, Map, Value};

const PARITY: &str = include_str!("../../../tests/fixtures/corpus_parity.json");
const CORPUS: [(&str, &str); 6] = [
    ("triage", include_str!("../../../tests/corpus/triage.jsonl")),
    ("abort", include_str!("../../../tests/corpus/abort.jsonl")),
    ("verify", include_str!("../../../tests/corpus/verify.jsonl")),
    ("route", include_str!("../../../tests/corpus/route.jsonl")),
    ("effort", include_str!("../../../tests/corpus/effort.jsonl")),
    ("nudge", include_str!("../../../tests/corpus/nudge.jsonl")),
];

async fn observe(gate: &str, input: &Value, client: &JevClient) -> Map<String, Value> {
    let mut out = Map::new();
    match gate {
        "triage" => {
            let res = triage_test_failure(input["log"].as_str().unwrap(), Some(client))
                .await
                .expect("triage runs offline");
            out.insert("category".into(), json!(res.category));
            out.insert("skip_llm".into(), json!(res.skip_llm));
        }
        "abort" => {
            let res = should_abort_trajectory(
                input["proposed_step"].as_str().unwrap(),
                input["history"].as_str().unwrap_or(""),
                Some(client),
            )
            .await
            .expect("abort runs offline");
            out.insert("should_abort".into(), json!(res.should_abort));
        }
        "verify" => {
            let res = verify_step_completion(
                input["criteria"].as_str().unwrap(),
                input["output"].as_str().unwrap(),
                Some(client),
            )
            .await
            .expect("verify runs offline");
            out.insert("is_verified".into(), json!(res.is_verified));
        }
        "route" => {
            let res = route_model_tier(input["task"].as_str().unwrap(), Some(client))
                .await
                .expect("route runs offline");
            out.insert("selected_tier".into(), json!(res.selected_tier));
        }
        "effort" => {
            let res = modulate_reasoning_effort(
                input["context"].as_str().unwrap(),
                input["provider"].as_str().unwrap_or("openai"),
                input["model"].as_str(),
                Some(client),
            )
            .await
            .expect("effort runs offline");
            out.insert("effort".into(), json!(res.effort));
        }
        "nudge" => {
            let res = should_nudge_continuation(
                input["transcript_tail"].as_str().unwrap(),
                "",
                0.5,
                Some(client),
            )
            .await
            .expect("nudge runs offline");
            out.insert("should_nudge".into(), json!(res.should_nudge));
            out.insert("workflow_phase".into(), json!(res.workflow_phase));
        }
        other => panic!("unknown gate {other}"),
    }
    out
}

#[tokio::test]
async fn every_corpus_case_matches_the_recorded_python_verdict() {
    let parity: Value = serde_json::from_str(PARITY).expect("parity fixture is valid JSON");
    let expected = parity["cases"].as_object().expect("cases object");
    let client = JevClient::with_mock();
    let mut mismatches: Vec<String> = Vec::new();
    let mut checked = 0usize;

    for (gate, corpus) in CORPUS {
        for line in corpus.lines().filter(|l| !l.trim().is_empty()) {
            let entry: Value = serde_json::from_str(line).expect("corpus line is valid JSON");
            let id = entry["id"].as_str().expect("corpus id");
            let want = expected
                .get(id)
                .unwrap_or_else(|| panic!("no recorded verdict for {id}"));
            assert_eq!(
                want["gate"].as_str().unwrap_or_default(),
                gate,
                "{id} gate mismatch"
            );
            let observed = observe(gate, &entry["input"], &client).await;
            checked += 1;
            for (key, want_value) in want["observed"].as_object().expect("observed object") {
                let got = observed.get(key).cloned().unwrap_or(Value::Null);
                if &got != want_value {
                    mismatches.push(format!(
                        "{id} ({gate}) {key}: rust={got} expected={want_value}"
                    ));
                }
            }
        }
    }

    assert_eq!(checked, 160, "the corpus must keep its size");
    assert!(
        mismatches.is_empty(),
        "tri-runtime divergence:\n{}",
        mismatches.join("\n")
    );
}

#[tokio::test]
async fn injected_logs_escalate_in_rust_too() {
    let client = JevClient::with_mock();
    let mut adversarial = 0usize;
    for (gate, corpus) in CORPUS {
        if gate != "triage" {
            continue;
        }
        for line in corpus.lines().filter(|l| !l.trim().is_empty()) {
            let entry: Value = serde_json::from_str(line).expect("corpus line is valid JSON");
            let id = entry["id"].as_str().expect("corpus id");
            if !id.starts_with("adv-") {
                continue;
            }
            adversarial += 1;
            let res = triage_test_failure(entry["input"]["log"].as_str().unwrap(), Some(&client))
                .await
                .expect("triage runs offline");
            assert_eq!(res.category, "deep_logic", "{id}");
            assert!(!res.skip_llm, "{id}");
        }
    }
    assert!(
        adversarial >= 8,
        "the corpus must keep its adversarial cases"
    );
}
