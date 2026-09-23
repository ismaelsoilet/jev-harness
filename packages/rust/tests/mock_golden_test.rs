//! E3.9 — golden vectors for the offline mock, shared with Python and TypeScript.
//! The fixture is the same file the other runtimes read: any drift in one runtime breaks parity
//! here instead of shipping a false claim.
use jev_harness::client::{
    MOCK_CHOICE_BEST_CONFLICT, MOCK_CHOICE_BEST_PEAKED, MOCK_SCORE_BEST_PEAKED,
};
use jev_harness::types::{ChoiceQuestion, NoulQuestion, Question, ScoreQuestion};
use jev_harness::JevClient;
use serde_json::Value;
use std::collections::HashMap;

const FIXTURE: &str = include_str!("../../../tests/fixtures/mock_golden.json");

fn fixture() -> Value {
    serde_json::from_str(FIXTURE).expect("golden fixture is valid JSON")
}

fn criteria(value: &Value) -> HashMap<String, String> {
    value
        .as_object()
        .expect("criteria object")
        .iter()
        .map(|(k, v)| (k.clone(), v.as_str().unwrap_or_default().to_string()))
        .collect()
}

fn choice_answer(state: &str) -> (String, HashMap<String, f64>) {
    let fx = fixture();
    let mut questions = HashMap::new();
    questions.insert(
        "category".to_string(),
        Question::Choice(ChoiceQuestion {
            instructions: "What is the root failure type in this error trace?".into(),
            criteria: criteria(&fx["choice_criteria"]),
        }),
    );
    let client = JevClient::with_mock();
    let resp = client.simulate_system_one(state, &questions, &client.model);
    match resp.answers.get("category").expect("category answer") {
        jev_harness::types::Answer::Choice(a) => (
            a.choice.clone(),
            a.probabilities.clone().unwrap_or_default(),
        ),
        other => panic!("expected a choice answer, got {:?}", other),
    }
}

fn nearly(actual: f64, expected: f64, label: &str) {
    assert!(
        (actual - expected).abs() < 1e-9,
        "{label}: {actual} != {expected}"
    );
}

#[test]
fn mock_constants_match_the_cross_runtime_contract() {
    nearly(MOCK_CHOICE_BEST_PEAKED, 0.85, "peaked");
    nearly(MOCK_CHOICE_BEST_CONFLICT, 0.55, "conflict");
    nearly(MOCK_SCORE_BEST_PEAKED, 0.80, "score");
}

#[test]
fn peaked_choice_distribution_matches_the_golden_vector() {
    let fx = fixture();
    let (choice, probs) = choice_answer(fx["peaked"]["state"].as_str().unwrap());
    assert_eq!(choice, fx["peaked"]["expected"]["choice"].as_str().unwrap());
    assert_eq!(
        probs.len(),
        fx["choice_criteria"].as_object().unwrap().len(),
        "every option must carry a probability"
    );
    for (key, value) in fx["peaked"]["expected"]["probabilities"]
        .as_object()
        .unwrap()
    {
        nearly(probs[key], value.as_f64().unwrap(), key);
    }
}

#[test]
fn conflicting_signals_lower_the_peak() {
    let fx = fixture();
    let (choice, probs) = choice_answer(fx["conflict"]["state"].as_str().unwrap());
    assert_eq!(
        choice,
        fx["conflict"]["expected"]["choice"].as_str().unwrap()
    );
    for (key, value) in fx["conflict"]["expected"]["probabilities"]
        .as_object()
        .unwrap()
    {
        nearly(probs[key], value.as_f64().unwrap(), key);
    }
    nearly(probs[&choice], MOCK_CHOICE_BEST_CONFLICT, "conflict peak");
    assert!(probs[&choice] < MOCK_CHOICE_BEST_PEAKED);
}

#[test]
fn distributions_sum_to_one() {
    let fx = fixture();
    for name in ["peaked", "conflict"] {
        let (_choice, probs) = choice_answer(fx[name]["state"].as_str().unwrap());
        let total: f64 = probs.values().sum();
        nearly(total, 1.0, name);
    }
}

#[test]
fn score_distribution_is_exposed() {
    let fx = fixture();
    let levels: Vec<String> = fx["score"]["levels"]
        .as_array()
        .unwrap()
        .iter()
        .map(|v| v.as_str().unwrap().to_string())
        .collect();
    let mut questions = HashMap::new();
    questions.insert(
        "severity".to_string(),
        Question::Score(ScoreQuestion {
            instructions: "How severe is this failure?".into(),
            criteria: levels.clone(),
        }),
    );
    let client = JevClient::with_mock();
    let resp = client.simulate_system_one(
        fx["score"]["state"].as_str().unwrap(),
        &questions,
        &client.model,
    );
    let answer = match resp.answers.get("severity").expect("severity answer") {
        jev_harness::types::Answer::Score(a) => a,
        other => panic!("expected a score answer, got {:?}", other),
    };
    nearly(
        answer.score,
        fx["score"]["expected"]["score"].as_f64().unwrap(),
        "score",
    );
    let probs = answer
        .probabilities
        .as_ref()
        .expect("score probabilities exposed");
    assert_eq!(probs.len(), levels.len(), "one probability per level");
    for (key, value) in fx["score"]["expected"]["probabilities"]
        .as_object()
        .unwrap()
    {
        nearly(probs[key], value.as_f64().unwrap(), key);
    }
    nearly(probs.values().sum::<f64>(), 1.0, "score sum");
}

#[test]
fn noul_stays_a_scalar() {
    let fx = fixture();
    let mut questions = HashMap::new();
    questions.insert(
        "skip_llm".to_string(),
        Question::Noul(NoulQuestion {
            instructions: fx["noul"]["instruction"].as_str().unwrap().to_string(),
        }),
    );
    let client = JevClient::with_mock();
    let resp = client.simulate_system_one(
        fx["noul"]["state"].as_str().unwrap(),
        &questions,
        &client.model,
    );
    match resp.answers.get("skip_llm").expect("noul answer") {
        jev_harness::types::Answer::Noul(a) => nearly(
            a.noul,
            fx["noul"]["expected"]["noul"].as_f64().unwrap(),
            "noul",
        ),
        other => panic!("expected a noul answer, got {:?}", other),
    }
}
