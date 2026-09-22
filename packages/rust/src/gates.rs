//! Semantic Decision Gates powered by TypeSafe Jev System One.
//!
//! Provides ultra-fast micro-decisions (<500µs local, 70-300ms remote) to optimize agentic loops,
//! triage test failures, prevent doomed circular paths, and route model tiers.

use crate::client::JevClient;
use crate::types::*;
use std::collections::HashMap;

/// Truncates a log string preserving the head and tail while guaranteeing valid UTF-8 char boundaries.
pub fn safe_truncate_head_tail(s: &str, max_head: usize, max_tail: usize) -> String {
    if s.len() <= max_head + max_tail {
        return s.to_string();
    }

    let mut head_end = max_head;
    while head_end > 0 && !s.is_char_boundary(head_end) {
        head_end -= 1;
    }

    let mut tail_start = s.len().saturating_sub(max_tail);
    while tail_start < s.len() && !s.is_char_boundary(tail_start) {
        tail_start += 1;
    }

    if head_end >= tail_start {
        return s.to_string();
    }

    let truncated_bytes = tail_start - head_end;
    format!(
        "{}\n\n... [TRUNCATED {} BYTES BY JEV HARNESS] ...\n\n{}",
        &s[..head_end],
        truncated_bytes,
        &s[tail_start..]
    )
}

/// Triages an execution or test failure log.
/// Returns whether expensive frontier LLM calls can be skipped.
pub async fn triage_test_failure(
    raw_error_log: &str,
    client: Option<&JevClient>,
) -> Result<TestTriageResult, JevError> {
    let default_client = JevClient::default();
    let active_client = client.unwrap_or(&default_client);

    let truncated_log = if raw_error_log.len() > 6000 {
        safe_truncate_head_tail(raw_error_log, 2000, 4000)
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
        "Simple syntax error, missing bracket, typo in variable, or formatting linter violation"
            .to_string(),
    );
    cat_criteria.insert(
        "deep_logic".to_string(),
        "Real semantic bug, failed unit assertion, invariant violation, panic, or unexpected state"
            .to_string(),
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
            instructions: "Can this error be handled deterministically (e.g. running pip/npm/cargo install, retrying, or fixing a simple typo) without calling an expensive System 2 generative LLM?".to_string(),
        }),
    );

    questions.insert(
        "severity".to_string(),
        Question::Score(ScoreQuestion {
            instructions: "Rate the severity of this defect on application stability".to_string(),
            criteria: vec![
                "trivial_env".to_string(),
                "minor_syntax".to_string(),
                "moderate_bug".to_string(),
                "critical_systemic".to_string(),
            ],
        }),
    );

    let resp = active_client.system_one(&truncated_log, questions).await?;

    let cat_ans = resp.answers.get("category").and_then(|a| a.as_choice());
    let skip_ans = resp.answers.get("skip_llm").and_then(|a| a.as_noul());
    let sev_ans = resp.answers.get("severity").and_then(|a| a.as_score());

    let category = cat_ans
        .map(|a| a.choice.clone())
        .unwrap_or_else(|| "deep_logic".to_string());
    let confidence = cat_ans.map(|a| a.confidence).unwrap_or(0.5);
    let sev_score = sev_ans.map(|a| a.score as f64).unwrap_or(3.0);
    let skip_prob = skip_ans.map(|a| a.noul).unwrap_or(0.0);
    let skip_llm = category != "deep_logic"
        && (skip_prob >= 0.65 || category == "env_missing" || category == "flaky_transient");

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
        "The trajectory is circular or contradictory; stop and ask user for clarification"
            .to_string(),
    );

    questions.insert(
        "action".to_string(),
        Question::Choice(ChoiceQuestion {
            instructions: "What should the orchestrator do with this proposed trajectory?"
                .to_string(),
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
    let action = action_ans
        .map(|a| a.choice.clone())
        .unwrap_or_else(|| "proceed".to_string());
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
        format!(
            "Safe to proceed (viability={:.1}, action={})",
            viability, effective_action
        )
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
        "Can be solved with bash, regex, deterministic script, or pure Jev classification"
            .to_string(),
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
            instructions: "Select the minimal sufficient model tier to solve this programming task"
                .to_string(),
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

    let resp = active_client
        .system_one(task_description, questions)
        .await?;

    let tier_ans = resp.answers.get("tier").and_then(|a| a.as_choice());
    let comp_ans = resp.answers.get("complexity").and_then(|a| a.as_score());

    let selected_tier = tier_ans
        .map(|a| a.choice.clone())
        .unwrap_or_else(|| "lightweight_system2".to_string());
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

    let state = format!(
        "CRITERIA TO SATISFY:\n{}\n\nACTUAL STEP OUTPUT:\n{}",
        criteria, output
    );

    let mut questions = HashMap::new();

    questions.insert(
        "satisfaction".to_string(),
        Question::Noul(NoulQuestion {
            instructions: "Does the produced output satisfy the acceptance criteria with concrete verifiable evidence?".to_string(),
        }),
    );

    questions.insert(
        "rigor".to_string(),
        Question::Score(ScoreQuestion {
            instructions: "Rate how rigorously the criteria are verified by the evidence".to_string(),
            criteria: vec![
                "unverified".to_string(),
                "partially_verified".to_string(),
                "well_verified".to_string(),
                "exhaustively_proven".to_string(),
            ],
        }),
    );

    let resp = active_client.system_one(&state, questions).await?;

    let sat_ans = resp.answers.get("satisfaction").and_then(|a| a.as_noul());
    let rig_ans = resp.answers.get("rigor").and_then(|a| a.as_score());

    let sat_prob = sat_ans.map(|a| a.noul).unwrap_or(0.0);
    let rig_score = rig_ans.map(|a| a.score as f64).unwrap_or(2.0);
    let confidence = rig_ans.map(|a| a.confidence).unwrap_or(0.8);

    let is_verified = sat_prob >= 0.80 && rig_score >= 2.5;

    Ok(VerificationResult {
        is_verified,
        satisfaction_probability: sat_prob,
        rigor_score: rig_score,
        confidence,
        needs_rework: !is_verified,
        is_mock: resp.is_mock,
    })
}

pub fn build_provider_params(
    provider: &str,
    effort: &str,
    model: Option<&str>,
) -> (serde_json::Value, bool, String, String) {
    let norm_provider = provider.trim().to_lowercase();
    let norm_model = model.unwrap_or("").trim().to_lowercase();

    let direct_models = [
        "gpt-5.6-luna",
        "gpt-5.5",
        "gpt-4o",
        "gpt-4o-mini",
        "gpt-4-turbo",
        "gpt-4",
        "gemini-3.8-live",
        "gemini-2.5-flash",
        "gemini-2.0-flash",
        "gemini-1.5-flash",
        "claude-3-5-haiku",
        "claude-3-haiku",
        "claude-3-5-sonnet",
        "deepseek-chat",
        "qwen-3.8-flash-standard",
        "qwen-2.5-coder",
        "qwen-2.5-72b",
        "llama-3.3",
        "llama-3.1",
        "codestral",
        "mistral",
    ];
    if direct_models.iter().any(|dm| norm_model.contains(dm)) {
        let display_model = model.unwrap_or("unknown");
        return (
            serde_json::json!({}),
            false,
            format!("Model '{}' is a direct single-pass model without internal reasoning CoT. Do NOT inject reasoning parameters.", display_model),
            "Cache unaffected. Model runs in direct generation mode.".to_string(),
        );
    }

    let cache_rec = if effort != "low" {
        "Keep reasoning effort stable across related sub-steps to preserve Prompt Cache (KV Cache)."
    } else {
        "Low reasoning effort saves ~7,000 reasoning tokens. Safe to use for mechanical tool calls."
    };

    if norm_provider == "openai" || norm_provider == "codex" {
        (
            serde_json::json!({ "reasoning_effort": effort }),
            true,
            format!("Configured OpenAI reasoning_effort='{}' for target model. Note: Ensure temperature=1.0 or omitted to prevent HTTP 400.", effort),
            cache_rec.to_string(),
        )
    } else if norm_provider == "deepseek" || norm_provider == "deepseek-ai" {
        let effort_val = if effort == "low" { "low" } else { "high" };
        (
            serde_json::json!({
                "extra_body": { "thinking": { "type": "enabled" } },
                "reasoning_effort": effort_val
            }),
            true,
            format!("DeepSeek Thinking mode configured with effort='{}'. Preserves reasoning_content in multi-turn tool calling.", effort_val),
            if effort == "low" { "Cuts latency by ~200s in mechanical steps when set to low.".to_string() } else { cache_rec.to_string() },
        )
    } else if norm_provider == "qwen" || norm_provider == "alibaba" || norm_provider == "dashscope"
    {
        if effort == "low" {
            (
                serde_json::json!({ "enable_thinking": false }),
                true,
                "Disabled Qwen thinking CoT for mechanical/terminal step to minimize latency. Wrap in extra_body={'enable_thinking': false} when using OpenAI client.".to_string(),
                "Zero tokens spent on reasoning trace.".to_string(),
            )
        } else {
            let budget = if effort == "medium" { 4096 } else { 16384 };
            (
                serde_json::json!({ "enable_thinking": true, "thinking_budget": budget }),
                true,
                format!("Enabled Qwen thinking budget ({} tokens). Wrap in extra_body when using OpenAI client.", budget),
                cache_rec.to_string(),
            )
        }
    } else if norm_provider == "anthropic" || norm_provider == "claude" {
        let chosen = match effort {
            "low" => "low",
            "medium" => "medium",
            _ => "max",
        };
        (
            serde_json::json!({
                "thinking": { "type": "adaptive" },
                "output_config": { "effort": chosen }
            }),
            true,
            format!(
                "Configured Anthropic Adaptive Thinking with effort='{}'.",
                chosen
            ),
            cache_rec.to_string(),
        )
    } else if norm_provider == "gemini" || norm_provider == "google" {
        let chosen = match effort {
            "low" => "minimal",
            "medium" => "medium",
            _ => "high",
        };
        (
            serde_json::json!({
                "thinking_config": { "thinking_level": chosen }
            }),
            true,
            format!("Configured Gemini thinking_level='{}'.", chosen),
            cache_rec.to_string(),
        )
    } else if norm_provider == "kimi" || norm_provider == "moonshot" {
        if effort == "low" {
            (
                serde_json::json!({ "extra_body": { "thinking": false } }),
                true,
                "Enabled Kimi Instant Mode (thinking disabled) for zero-latency execution."
                    .to_string(),
                "Eliminates internal CoT overhead.".to_string(),
            )
        } else {
            let k_effort = if effort == "high" { "high" } else { "low" };
            (
                serde_json::json!({ "reasoning_effort": k_effort }),
                true,
                format!("Configured Kimi reasoning_effort='{}'.", k_effort),
                cache_rec.to_string(),
            )
        }
    } else if norm_provider == "mimo" || norm_provider == "xiaomi" {
        if effort == "low" {
            (
                serde_json::json!({ "thinking": { "type": "disabled" } }),
                true,
                "Disabled MiMo CoT for terminal command to free GPU inference.".to_string(),
                "Immediate generation without scratchpad.".to_string(),
            )
        } else {
            (
                serde_json::json!({
                    "thinking": { "type": "enabled" },
                    "reasoning": { "effort": effort }
                }),
                true,
                format!("Enabled MiMo deep reasoning with effort='{}'.", effort),
                cache_rec.to_string(),
            )
        }
    } else {
        (
            serde_json::json!({ "reasoning_effort": effort }),
            true,
            format!("Generic reasoning effort='{}'.", effort),
            cache_rec.to_string(),
        )
    }
}

pub async fn modulate_reasoning_effort_with_tokens(
    context: &str,
    provider: &str,
    model: Option<&str>,
    session_context_tokens: usize,
    client: Option<&JevClient>,
) -> Result<ReasoningEffortResult, JevError> {
    let default_client = JevClient::default();
    let active_client = client.unwrap_or(&default_client);

    let mut questions = HashMap::new();

    let mut effort_criteria = HashMap::new();
    effort_criteria.insert(
        "low".to_string(),
        "Mechanical action: run bash command, check git status, view file, format code, linter check, simple import, or trivial syntax edit".to_string(),
    );
    effort_criteria.insert(
        "medium".to_string(),
        "Standard code modification: implement bounded function, write standard unit test, add parameter, or localized refactoring".to_string(),
    );
    effort_criteria.insert(
        "high".to_string(),
        "Deep cognitive task: architectural design, race condition, distributed deadlock, concurrency kernel bug, or complex multi-file debugging".to_string(),
    );

    questions.insert(
        "effort".to_string(),
        Question::Choice(ChoiceQuestion {
            instructions: "Select the minimal sufficient reasoning effort needed for this immediate agent step".to_string(),
            criteria: effort_criteria,
        }),
    );

    questions.insert(
        "complexity".to_string(),
        Question::Score(ScoreQuestion {
            instructions: "Rate the cognitive depth required for this next step".to_string(),
            criteria: vec![
                "trivial_mechanical".to_string(),
                "standard_implementation".to_string(),
                "complex_logic".to_string(),
                "exceptional_architecture".to_string(),
            ],
        }),
    );

    let clean_context = if context.len() > 4000 {
        safe_truncate_head_tail(context, 1500, 2500)
    } else {
        context.to_string()
    };

    let resp = active_client.system_one(&clean_context, questions).await?;

    let effort_ans = resp.answers.get("effort").and_then(|a| a.as_choice());
    let comp_ans = resp.answers.get("complexity").and_then(|a| a.as_score());

    let effort = effort_ans
        .map(|a| a.choice.clone())
        .unwrap_or_else(|| "medium".to_string());
    let confidence = effort_ans.map(|a| a.confidence).unwrap_or(0.85);
    let complexity_score = comp_ans.map(|a| a.score as f64).unwrap_or(2.0);

    let (provider_params, is_supported, rationale, mut cache_rec) =
        build_provider_params(provider, &effort, model);

    if session_context_tokens > 30000 && is_supported {
        cache_rec = format!(
            "HIGH CACHE RISK ({} tokens active): Modulating reasoning effort across turns may invalidate prefix KV cache. Hysteresis recommended: preserve stable reasoning effort across active sub-steps.",
            session_context_tokens
        );
    }

    Ok(ReasoningEffortResult {
        effort,
        confidence,
        complexity_score,
        rationale,
        provider: provider.to_string(),
        provider_params,
        is_reasoning_supported: is_supported,
        cache_safe_recommendation: cache_rec,
        is_mock: resp.is_mock,
    })
}

pub async fn modulate_reasoning_effort(
    context: &str,
    provider: &str,
    model: Option<&str>,
    client: Option<&JevClient>,
) -> Result<ReasoningEffortResult, JevError> {
    modulate_reasoning_effort_with_tokens(context, provider, model, 0, client).await
}
