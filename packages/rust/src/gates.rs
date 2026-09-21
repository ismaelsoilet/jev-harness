//! Semantic Decision Gates powered by TypeSafe Jev System One.
//!
//! Provides ultra-fast micro-decisions (<500µs local, 70-300ms remote) to optimize agentic loops,
//! triage test failures, prevent doomed circular paths, and route model tiers.

use crate::client::JevClient;
use crate::types::*;
use std::collections::HashMap;

/// Triages an execution or test failure log.
/// Returns whether expensive frontier LLM calls can be skipped.
pub async fn triage_test_failure(
    raw_error_log: &str,
    client: Option<&JevClient>,
) -> Result<TestTriageResult, JevError> {
    let default_client = JevClient::default();
    let active_client = client.unwrap_or(&default_client);

    let truncated_log = if raw_error_log.len() > 3000 {
        let half = 1400;
        format!(
            "{}\n\n... [TRUNCATED {} BYTES BY JEV HARNESS] ...\n\n{}",
            &raw_error_log[..half],
            raw_error_log.len() - (half * 2),
            &raw_error_log[raw_error_log.len() - half..]
        )
    } else {
        raw_error_log.to_string()
    };

    let mut questions = HashMap::new();

    let mut cat_criteria = HashMap::new();
    cat_criteria.insert(
        "env_missing".to_string(),
        "Missing dependency, package not found, uninstalled CLI tool, or environment path misconfiguration (e.g. TS2307, ModuleNotFoundError, E0463)".to_string(),
    );
    cat_criteria.insert(
        "flaky_transient".to_string(),
        "Transient network glitch, connection reset, socket timeout, port conflict, or busy worker (e.g. ETIMEDOUT, ECONNRESET)".to_string(),
    );
    cat_criteria.insert(
        "syntax_trivial".to_string(),
        "Simple syntax error, missing bracket, typo in variable, or formatting linter violation".to_string(),
    );
    cat_criteria.insert(
        "deep_logic".to_string(),
        "Real semantic bug, failed unit assertion, invariant violation, panic, or unexpected state".to_string(),
    );
    cat_criteria.insert(
        "test_redundant".to_string(),
        "Failure is due to an obsolete, redundant, or malformed test case rather than system defect".to_string(),
    );

    questions.insert(
        "category".to_string(),
        Question::Choice(ChoiceQuestion {
            instructions: "Categorize the primary root cause of this execution failure".to_string(),
            criteria: cat_criteria,
        }),
    );

    questions.insert(
        "skip_llm".to_string(),
        Question::Noul(NoulQuestion {
            instructions: "Can this failure be addressed deterministically (e.g. pip/npm install, retry worker, fix syntax) without dispatching full context to an expensive generative LLM?".to_string(),
        }),
    );

    questions.insert(
        "severity".to_string(),
        Question::Score(ScoreQuestion {
            instructions: "Rate the severity of this defect on application stability".to_string(),
            criteria: vec![
                "trivial_cleanup".to_string(),
                "blocking_env".to_string(),
                "feature_broken".to_string(),
                "systemic_disaster".to_string(),
            ],
        }),
    );

    let resp = active_client.system_one(&truncated_log, questions).await?;

    let cat_ans = resp.answers.get("category").and_then(|a| a.as_choice());
    let skip_ans = resp.answers.get("skip_llm").and_then(|a| a.as_noul());
    let sev_ans = resp.answers.get("severity").and_then(|a| a.as_score());

    let category = cat_ans.map(|a| a.choice.clone()).unwrap_or_else(|| "deep_logic".to_string());
    let confidence = cat_ans.map(|a| a.confidence).unwrap_or(0.5);
    let skip_prob = skip_ans.map(|a| a.noul).unwrap_or(0.0);
    let sev_score = sev_ans.map(|a| a.score as f64).unwrap_or(3.0);

    let skip_llm = skip_prob >= 0.65 || category == "env_missing" || category == "flaky_transient";

    let rec = match category.as_str() {
        "env_missing" => "AUTO-ACTION: Install missing dependency or check environment configuration (Do NOT call LLM).",
        "flaky_transient" => "AUTO-ACTION: Retry test once with fresh worker; do not generate code changes.",
        "syntax_trivial" => "LOW-COST: Fix typo locally or route to fastest lightweight tier.",
        "test_redundant" => "PRUNE: Test is redundant or obsolete; prune from test harness.",
        _ => "ESCALATE: Real logic defect; dispatch to System 2 LLM with targeted context.",
    };

    Ok(TestTriageResult {
        category,
        confidence,
        skip_llm,
        skip_llm_prob: skip_prob,
        severity_score: sev_score,
        action_recommendation: rec.to_string(),
        is_mock: resp.is_mock,
    })
}

/// Evaluates if current agent trajectory is trapped in a circular loop or unviable path.
pub async fn should_abort_trajectory(
    proposed_step: &str,
    recent_attempts_summary: &str,
    client: Option<&JevClient>,
) -> Result<AbortGateResult, JevError> {
    let default_client = JevClient::default();
    let active_client = client.unwrap_or(&default_client);

    let state = format!(
        "RECENT ATTEMPTS & CONTEXT:\n{}\n\nPROPOSED NEXT STEP:\n{}",
        recent_attempts_summary, proposed_step
    );

    let mut questions = HashMap::new();

    questions.insert(
        "dead_end".to_string(),
        Question::Noul(NoulQuestion {
            instructions: "Does this proposed step indicate a dead end, repeating a previously failed approach, or proposing an unviable/destructive path?".to_string(),
        }),
    );

    let mut action_criteria = HashMap::new();
    action_criteria.insert(
        "proceed".to_string(),
        "The step is logical, progress-oriented, and grounded in evidence".to_string(),
    );
    action_criteria.insert(
        "replan".to_string(),
        "The step is doubtful or weak; reconsider alternatives".to_string(),
    );
    action_criteria.insert(
        "abort_and_ask".to_string(),
        "The trajectory is circular or contradictory; stop and ask user for clarification".to_string(),
    );

    questions.insert(
        "action".to_string(),
        Question::Choice(ChoiceQuestion {
            instructions: "What should the orchestrator do with this proposed trajectory?".to_string(),
            criteria: action_criteria,
        }),
    );

    questions.insert(
        "viability".to_string(),
        Question::Score(ScoreQuestion {
            instructions: "Evaluate the technical viability of this step".to_string(),
            criteria: vec![
                "hopeless_circular".to_string(),
                "doubtful".to_string(),
                "plausible".to_string(),
                "highly_viable".to_string(),
            ],
        }),
    );

    let resp = active_client.system_one(&state, questions).await?;

    let dead_end_ans = resp.answers.get("dead_end").and_then(|a| a.as_noul());
    let action_ans = resp.answers.get("action").and_then(|a| a.as_choice());
    let viability_ans = resp.answers.get("viability").and_then(|a| a.as_score());

    let dead_end_prob = dead_end_ans.map(|a| a.noul).unwrap_or(0.0);
    let action = action_ans.map(|a| a.choice.clone()).unwrap_or_else(|| "proceed".to_string());
    let viability = viability_ans.map(|a| a.score as f64).unwrap_or(3.0);

    let should_abort = dead_end_prob >= 0.70 || action == "abort_and_ask" || viability <= 1.5;
    let effective_action = if should_abort && action == "proceed" {
        "abort_and_ask".to_string()
    } else {
        action
    };

    let summary = if should_abort {
        format!("Abort recommended (prob={:.2})", dead_end_prob)
    } else {
        format!("Safe to proceed (viability={:.1}, action={})", viability, effective_action)
    };

    Ok(AbortGateResult {
        should_abort,
        abort_probability: dead_end_prob,
        action: effective_action,
        viability_score: viability,
        reasoning_summary: summary,
        is_mock: resp.is_mock,
    })
}

/// Dynamically selects minimal sufficient model tier.
pub async fn route_model_tier(
    task_description: &str,
    client: Option<&JevClient>,
) -> Result<ModelRouteResult, JevError> {
    let default_client = JevClient::default();
    let active_client = client.unwrap_or(&default_client);

    let mut questions = HashMap::new();

    let mut tier_criteria = HashMap::new();
    tier_criteria.insert(
        "deterministic".to_string(),
        "Can be solved with bash, regex, deterministic script, or pure Jev classification".to_string(),
    );
    tier_criteria.insert(
        "lightweight_system2".to_string(),
        "Simple coding edit, formatting, documentation, or trivial unit test (e.g. Gemini 3.8 Flash)".to_string(),
    );
    tier_criteria.insert(
        "heavy_system2".to_string(),
        "Complex architecture, deep reasoning, multi-file refactoring, or difficult debugging (e.g. GPT-6 Astra, Claude Fable 5.1)".to_string(),
    );

    questions.insert(
        "tier".to_string(),
        Question::Choice(ChoiceQuestion {
            instructions: "Select the minimal sufficient model tier to solve this programming task".to_string(),
            criteria: tier_criteria,
        }),
    );

    questions.insert(
        "complexity".to_string(),
        Question::Score(ScoreQuestion {
            instructions: "Rate the cognitive complexity of this task".to_string(),
            criteria: vec![
                "trivial".to_string(),
                "straightforward".to_string(),
                "moderate".to_string(),
                "highly_complex".to_string(),
            ],
        }),
    );

    let resp = active_client.system_one(task_description, questions).await?;

    let tier_ans = resp.answers.get("tier").and_then(|a| a.as_choice());
    let comp_ans = resp.answers.get("complexity").and_then(|a| a.as_score());

    let selected_tier = tier_ans.map(|a| a.choice.clone()).unwrap_or_else(|| "lightweight_system2".to_string());
    let confidence = tier_ans.map(|a| a.confidence).unwrap_or(0.5);
    let complexity_score = comp_ans.map(|a| a.score as f64).unwrap_or(2.0);

    let (rec_model, rationale) = match selected_tier.as_str() {
        "deterministic" => (
            "Direct Python/Bash Script (0 LLM Tokens)",
            "Task does not require generative reasoning; execute mechanically.",
        ),
        "heavy_system2" => (
            "Claude Fable 5.1 / GPT-6 Astra (~$10.00 in / $50.00 out per 1M tokens)",
            "Task requires deep architectural synthesis or multi-file reasoning.",
        ),
        _ => (
            "Gemini 3.8 Flash (~$0.75 in / $3.75 out per 1M tokens)",
            "Straightforward generative task; lightweight fast agent tier is optimal.",
        ),
    };

    Ok(ModelRouteResult {
        selected_tier,
        confidence,
        complexity_score,
        recommended_model: rec_model.to_string(),
        rationale: rationale.to_string(),
        is_mock: resp.is_mock,
    })
}

/// Verifies whether step output meets criteria before concluding work.
pub async fn verify_step_completion(
    criteria: &str,
    output: &str,
    client: Option<&JevClient>,
) -> Result<VerificationResult, JevError> {
    let default_client = JevClient::default();
    let active_client = client.unwrap_or(&default_client);

    let state = format!("CRITERIA TO SATISFY:\n{}\n\nACTUAL STEP OUTPUT:\n{}", criteria, output);

    let mut questions = HashMap::new();

    questions.insert(
        "satisfied".to_string(),
        Question::Noul(NoulQuestion {
            instructions: "Does the output fully satisfy all required acceptance criteria without missing details?".to_string(),
        }),
    );

    questions.insert(
        "rigor".to_string(),
        Question::Score(ScoreQuestion {
            instructions: "Score the completeness and rigor of verification evidence".to_string(),
            criteria: vec![
                "unsupported_claim".to_string(),
                "partial_evidence".to_string(),
                "well_verified".to_string(),
                "exhaustively_proven".to_string(),
            ],
        }),
    );

    let resp = active_client.system_one(&state, questions).await?;

    let sat_ans = resp.answers.get("satisfied").and_then(|a| a.as_noul());
    let rig_ans = resp.answers.get("rigor").and_then(|a| a.as_score());

    let sat_prob = sat_ans.map(|a| a.noul).unwrap_or(0.0);
    let rig_score = rig_ans.map(|a| a.score as f64).unwrap_or(2.0);

    let is_verified = sat_prob >= 0.70 && rig_score >= 2.5;

    Ok(VerificationResult {
        is_verified,
        satisfaction_probability: sat_prob,
        rigor_score: rig_score,
        confidence: sat_prob,
        needs_rework: !is_verified,
        is_mock: resp.is_mock,
    })
}
