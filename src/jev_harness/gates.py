"""
Semantic Decision Gates powered by Jev System One.
Designed to prevent token waste, filter test suites, abort hallucinated trajectories,
and route tasks to the cheapest effective model tier.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from .client import ChoiceQuestion, JevClient, NoulQuestion, ScoreQuestion
from .session import (
    detect_repeated_failure,
    record_abort_event,
    record_reasoning_effort_event,
    record_route_event,
    record_step_attempt,
    record_triage_event,
)


@dataclass
class TestTriageResult:
    category: str
    confidence: float
    skip_llm: bool
    skip_llm_prob: float
    severity_score: float
    action_recommendation: str
    is_mock: bool = False
    details: Optional[Dict[str, Any]] = None


@dataclass
class AbortGateResult:
    should_abort: bool
    abort_probability: float
    action: str
    viability_score: float
    reasoning_summary: str
    is_mock: bool = False


# Alias for compatibility
AbortDecision = AbortGateResult


@dataclass
class ModelRouteResult:
    selected_tier: str  # 'deterministic', 'lightweight_system2', 'heavy_system2'
    confidence: float
    complexity_score: float
    rationale: str
    recommended_model: str
    is_mock: bool = False


# Alias for compatibility
ModelRouteDecision = ModelRouteResult


@dataclass
class VerificationResult:
    is_verified: bool
    satisfaction_probability: float
    rigor_score: float
    confidence: float
    needs_rework: bool
    is_mock: bool = False


@dataclass
class ReasoningEffortResult:
    effort: str  # 'low', 'medium', 'high'
    confidence: float
    complexity_score: float
    rationale: str
    provider: str
    provider_params: Dict[str, Any]
    is_reasoning_supported: bool = True
    cache_safe_recommendation: str = ""
    is_mock: bool = False


def triage_test_failure(
    failure_log: str,
    client: Optional[JevClient] = None,
) -> TestTriageResult:
    """
    Evaluates a test error or traceback to determine whether calling a heavy System 2 LLM
    is actually needed or if it can be resolved cheaply (or skipped).
    """
    client = client or JevClient()

    questions = {
        "category": ChoiceQuestion(
            instructions="What is the root failure type in this error trace?",
            criteria={
                "env_missing": "Missing module, package not installed, environment variable missing, or runtime command not found",
                "flaky_transient": "Network timeout, port already in use, race condition, or transient socket hangup",
                "syntax_trivial": "Small typo, missing bracket, indentation error, or simple import name mismatch",
                "test_redundant": "Deprecated test, duplicate assertion, or obsolete fixture",
                "deep_logic": "Complex algorithmic bug, business logic defect, or architectural regression",
            },
        ),
        "skip_llm": NoulQuestion(
            instructions="Can this error be handled deterministically (e.g. running pip/npm install, retrying, or fixing a simple typo) without calling an expensive System 2 generative LLM?",
        ),
        "severity": ScoreQuestion(
            instructions="Rate the architectural severity of this test failure",
            criteria=["trivial_env", "minor_syntax", "moderate_bug", "critical_systemic"],
        ),
    }

    clean_log = failure_log.strip()
    if len(clean_log) > 6000:
        clean_log = clean_log[:2000] + "\n...[truncated]...\n" + clean_log[-4000:]

    resp = client.system_one(state=clean_log, questions=questions)

    cat_ans = resp.answers.get("category")
    skip_ans = resp.answers.get("skip_llm")
    sev_ans = resp.answers.get("severity")

    category = cat_ans.choice if cat_ans and hasattr(cat_ans, "choice") else "deep_logic"
    confidence = cat_ans.confidence if cat_ans and hasattr(cat_ans, "confidence") else 0.5
    skip_prob = skip_ans.noul if skip_ans and hasattr(skip_ans, "noul") else 0.0
    sev_score = sev_ans.score if sev_ans and hasattr(sev_ans, "score") else 3.0

    skip_llm = (category != "deep_logic") and (
        skip_prob >= 0.65 or category in ["env_missing", "flaky_transient"]
    )

    if category == "env_missing":
        rec = "AUTO-ACTION: Install missing dependency or check environment configuration (Do NOT call LLM)."
    elif category == "flaky_transient":
        rec = "AUTO-ACTION: Retry test once with fresh worker; do not generate code changes."
    elif category == "syntax_trivial":
        rec = "LOW-COST: Fix typo locally or route to fastest lightweight tier."
    elif category == "test_redundant":
        rec = "PRUNE: Test is redundant or obsolete; prune from test harness."
    else:
        rec = "ESCALATE: Real logic defect; dispatch to System 2 LLM with targeted context."

    result = TestTriageResult(
        category=category,
        confidence=confidence,
        skip_llm=skip_llm,
        skip_llm_prob=skip_prob,
        severity_score=sev_score,
        action_recommendation=rec,
        is_mock=resp.is_mock,
        details={"model": resp.model, "usage": resp.usage},
    )
    try:
        record_triage_event(result.skip_llm, result.category)
        record_step_attempt("test-gate", error_snippet=clean_log[:200], action=rec)
    except Exception:
        pass
    return result


def should_abort_trajectory(
    proposed_step: str,
    recent_attempts_summary: str = "",
    client: Optional[JevClient] = None,
) -> AbortGateResult:
    """
    Early-abort check: Determines if the agent's proposed plan or refactor direction
    is circular, unviable, or headed towards a dead end before burning tens of thousands of tokens.
    """
    client = client or JevClient()

    auto_history = recent_attempts_summary
    if not auto_history:
        try:
            if detect_repeated_failure(proposed_step):
                auto_history = "WARNING: Identical failure or refactor pattern repeated across recent agent turns."
        except Exception:
            pass

    state = f"RECENT ATTEMPTS & CONTEXT:\n{auto_history}\n\nPROPOSED NEXT STEP:\n{proposed_step}"

    questions = {
        "dead_end": NoulQuestion(
            instructions="Does this proposed step indicate a dead end, repeating a previously failed approach, or proposing an unviable/destructive path?"
        ),
        "action": ChoiceQuestion(
            instructions="What should the orchestrator do with this proposed trajectory?",
            criteria={
                "proceed": "The step is logical, progress-oriented, and grounded in evidence",
                "replan": "The step is doubtful or weak; reconsider alternatives",
                "abort_and_ask": "The trajectory is circular or contradictory; stop and ask user for clarification",
            },
        ),
        "viability": ScoreQuestion(
            instructions="Evaluate the technical viability of this step",
            criteria=["hopeless_circular", "doubtful", "plausible", "highly_viable"],
        ),
    }

    resp = client.system_one(state=state, questions=questions)

    dead_end_ans = resp.answers.get("dead_end")
    action_ans = resp.answers.get("action")
    viability_ans = resp.answers.get("viability")

    dead_end_prob = dead_end_ans.noul if dead_end_ans and hasattr(dead_end_ans, "noul") else 0.0
    action = action_ans.choice if action_ans and hasattr(action_ans, "choice") else "proceed"
    viability = viability_ans.score if viability_ans and hasattr(viability_ans, "score") else 3.0

    should_abort = dead_end_prob >= 0.70 or action == "abort_and_ask" or viability <= 1.5
    effective_action = "abort_and_ask" if should_abort and action == "proceed" else action

    summary = (
        f"Abort recommended (prob={dead_end_prob:.2f})"
        if should_abort
        else f"Safe to proceed (viability={viability:.1f}, action={action})"
    )

    abort_res = AbortGateResult(
        should_abort=should_abort,
        abort_probability=dead_end_prob,
        action=effective_action,
        viability_score=viability,
        reasoning_summary=summary,
        is_mock=resp.is_mock,
    )
    try:
        record_abort_event(abort_res.should_abort)
        record_step_attempt(proposed_step, action=abort_res.action)
    except Exception:
        pass
    return abort_res


def route_model_tier(
    task_description: str,
    client: Optional[JevClient] = None,
) -> ModelRouteResult:
    """
    Decides the most cost-effective intelligence tier for a given task.
    """
    client = client or JevClient()

    questions = {
        "tier": ChoiceQuestion(
            instructions="Select the minimal sufficient model tier to solve this programming task",
            criteria={
                "deterministic": "Can be solved with bash, regex, deterministic script, or pure Jev classification",
                "lightweight_system2": "Simple coding edit, formatting, documentation, or trivial unit test (e.g. Gemini 3.8 Flash)",
                "heavy_system2": "Complex architecture, deep reasoning, multi-file refactoring, or difficult debugging (e.g. GPT-6 Astra, Claude Fable 5.1)",
            },
        ),
        "complexity": ScoreQuestion(
            instructions="Rate the cognitive complexity of this task",
            criteria=["trivial", "straightforward", "moderate", "highly_complex"],
        ),
    }

    resp = client.system_one(state=task_description, questions=questions)

    tier_ans = resp.answers.get("tier")
    comp_ans = resp.answers.get("complexity")

    tier = tier_ans.choice if tier_ans and hasattr(tier_ans, "choice") else "lightweight_system2"
    conf = tier_ans.confidence if tier_ans and hasattr(tier_ans, "confidence") else 0.8
    comp = comp_ans.score if comp_ans and hasattr(comp_ans, "score") else 2.0

    if tier == "deterministic":
        model_rec = "Direct Python/Bash Script (0 LLM Tokens)"
        rationale = "Task does not require generative reasoning; execute mechanically."
    elif tier == "lightweight_system2":
        model_rec = "Gemini 3.8 Flash (~$0.75 in / $3.75 out per 1M tokens)"
        rationale = "Task is bounded and straightforward; save frontier tokens."
    else:
        model_rec = "Claude Fable 5.1 / GPT-6 Astra (~$10.00 in / $50.00 out per 1M tokens)"
        rationale = "Task requires deep architectural synthesis or multi-file reasoning."

    route_res = ModelRouteResult(
        selected_tier=tier,
        confidence=conf,
        complexity_score=comp,
        rationale=rationale,
        recommended_model=model_rec,
        is_mock=resp.is_mock,
    )
    try:
        record_route_event(route_res.selected_tier)
    except Exception:
        pass
    return route_res


def verify_step_completion(
    acceptance_criteria: str,
    produced_output: str,
    client: Optional[JevClient] = None,
) -> VerificationResult:
    """
    Evaluates whether a code change or artifact actually satisfies acceptance criteria
    before dispatching expensive additional review agents.
    """
    client = client or JevClient()

    state = f"ACCEPTANCE CRITERIA:\n{acceptance_criteria}\n\nPRODUCED EVIDENCE / OUTPUT:\n{produced_output}"

    questions = {
        "satisfaction": NoulQuestion(
            instructions="Does the produced output satisfy the acceptance criteria with concrete verifiable evidence?"
        ),
        "rigor": ScoreQuestion(
            instructions="Rate how rigorously the criteria are verified by the evidence",
            criteria=["unverified", "partially_verified", "well_verified", "exhaustively_proven"],
        ),
    }

    resp = client.system_one(state=state, questions=questions)

    sat_ans = resp.answers.get("satisfaction")
    rigor_ans = resp.answers.get("rigor")

    sat_prob = sat_ans.noul if sat_ans and hasattr(sat_ans, "noul") else 0.0
    rigor_score = rigor_ans.score if rigor_ans and hasattr(rigor_ans, "score") else 2.0
    conf = rigor_ans.confidence if rigor_ans and hasattr(rigor_ans, "confidence") else 0.8

    is_verified = sat_prob >= 0.80 and rigor_score >= 2.5
    needs_rework = not is_verified

    return VerificationResult(
        is_verified=is_verified,
        satisfaction_probability=sat_prob,
        rigor_score=rigor_score,
        confidence=conf,
        needs_rework=needs_rework,
        is_mock=resp.is_mock,
    )


def build_provider_params(
    provider: str, effort: str, model: Optional[str] = None
) -> tuple[Dict[str, Any], bool, str, str]:
    """
    Compiles typed provider payload for the target model family.
    Returns: (provider_params, is_supported, rationale, cache_safe_recommendation)
    """
    norm_provider = provider.strip().lower() if provider else "openai"
    norm_model = (model or "").strip().lower()

    # Detect non-reasoning direct execution models that would return HTTP 400
    direct_models = [
        "gpt-5.6-luna",
        "gpt-5.5",
        "gpt-4o",
        "gpt-4o-mini",
        "gemini-3.8-live",
        "gemini-2.5-flash",
        "gemini-2.0-flash",
        "gemini-1.5-flash",
        "claude-3-5-haiku",
        "qwen-3.8-flash-standard",
        "qwen-2.5-coder",
        "llama-3.3",
        "llama-3.1",
    ]
    if any(dm in norm_model for dm in direct_models):
        return (
            {},
            False,
            f"Model '{model}' is a direct single-pass model without internal reasoning CoT. Do NOT inject reasoning parameters to avoid HTTP 400. Use route_model_tier instead.",
            "Cache unaffected. Model runs in direct generation mode.",
        )

    cache_rec = (
        "Keep reasoning effort stable across related sub-steps to preserve Prompt Cache (KV Cache)."
        if effort != "low"
        else "Low reasoning effort saves ~7,000 reasoning tokens. Safe to use for mechanical tool calls."
    )

    if norm_provider in ["openai", "codex", "azure"]:
        # Frontier 2026: GPT-6 Astra, o3, o4, GPT-5.6 Sol/Terra
        return (
            {"reasoning_effort": effort},
            True,
            f"Configured OpenAI reasoning_effort='{effort}' for target model. Note: Ensure temperature=1.0 or omitted to prevent HTTP 400.",
            cache_rec,
        )

    elif norm_provider in ["deepseek", "deepseek-ai"]:
        # DeepSeek V4.1-Flash / V4-Pro / R1
        # In multi-turn tool conversations, reasoning_content must be preserved
        effort_val = "low" if effort == "low" else "high"
        return (
            {
                "extra_body": {"thinking": {"type": "enabled"}},
                "reasoning_effort": effort_val,
            },
            True,
            f"DeepSeek Thinking mode configured with effort='{effort_val}'. Preserves reasoning_content in multi-turn tool calling.",
            "Cuts latency by ~200s in mechanical steps when set to low." if effort == "low" else cache_rec,
        )

    elif norm_provider in ["qwen", "alibaba", "dashscope"]:
        # Qwen 3.8 Max (2.4T MoE), Qwen 3.8-Omni-Flash
        # DashScope native parameters (wrap in extra_body if using OpenAI client)
        if effort == "low":
            return (
                {"enable_thinking": False},
                True,
                "Disabled Qwen thinking CoT for mechanical/terminal step to minimize latency. Wrap in extra_body={'enable_thinking': False} when using OpenAI client.",
                "Zero tokens spent on reasoning trace.",
            )
        elif effort == "medium":
            return (
                {"enable_thinking": True, "thinking_budget": 4096},
                True,
                "Enabled balanced Qwen thinking budget (4096 tokens). Wrap in extra_body when using OpenAI client.",
                cache_rec,
            )
        else:
            return (
                {"enable_thinking": True, "thinking_budget": 16384},
                True,
                "Enabled frontier deep reasoning budget (16384 tokens) on Qwen 3.8 Max. Wrap in extra_body when using OpenAI client.",
                cache_rec,
            )

    elif norm_provider in ["anthropic", "claude"]:
        # Claude Fable 5.1 / Claude 5 Sonnet / Claude Opus 5
        effort_map = {"low": "low", "medium": "medium", "high": "max"}
        chosen = effort_map.get(effort, "medium")
        return (
            {
                "thinking": {"type": "adaptive"},
                "output_config": {"effort": chosen},
            },
            True,
            f"Configured Anthropic Adaptive Thinking with effort='{chosen}'.",
            cache_rec,
        )

    elif norm_provider in ["gemini", "google"]:
        # Gemini 3.8 Flash Thinking / Gemini 3.5 Pro Thinking
        gemini_map = {"low": "minimal", "medium": "medium", "high": "high"}
        chosen = gemini_map.get(effort, "medium")
        return (
            {"thinking_config": {"thinking_level": chosen}},
            True,
            f"Configured Gemini thinking_level='{chosen}'.",
            cache_rec,
        )

    elif norm_provider in ["kimi", "moonshot"]:
        # Moonshot Kimi-k3
        if effort == "low":
            return (
                {"extra_body": {"thinking": False}},
                True,
                "Enabled Kimi Instant Mode (thinking disabled) for zero-latency execution.",
                "Eliminates internal CoT overhead.",
            )
        else:
            k_effort = "high" if effort == "high" else "low"
            return (
                {"reasoning_effort": k_effort},
                True,
                f"Configured Kimi reasoning_effort='{k_effort}'.",
                cache_rec,
            )

    elif norm_provider in ["mimo", "xiaomi"]:
        # Xiaomi MiMo-v2.6-pro / flash
        if effort == "low":
            return (
                {"thinking": {"type": "disabled"}},
                True,
                "Disabled MiMo CoT for terminal command to free GPU inference.",
                "Immediate generation without scratchpad.",
            )
        else:
            return (
                {"thinking": {"type": "enabled"}, "reasoning": {"effort": effort}},
                True,
                f"Enabled MiMo deep reasoning with effort='{effort}'.",
                cache_rec,
            )

    else:
        # Generic / OpenAI-compatible
        return (
            {"reasoning_effort": effort},
            True,
            f"Generic reasoning effort='{effort}'.",
            cache_rec,
        )


def modulate_reasoning_effort(
    context: str,
    provider: str = "openai",
    model: Optional[str] = None,
    session_context_tokens: int = 0,
    client: Optional[JevClient] = None,
) -> ReasoningEffortResult:
    """
    Dynamically decides the optimal reasoning effort ('low', 'medium', 'high')
    for the immediate next generation step, mapping typed parameters to the target provider.
    Eliminates reasoning token waste on mechanical tool calls and cuts multi-minute delays.
    """
    client = client or JevClient()

    questions = {
        "effort": ChoiceQuestion(
            instructions="Select the minimal sufficient reasoning effort needed for this immediate agent step",
            criteria={
                "low": "Mechanical action: run bash command, check git status, view file, format code, linter check, simple import, or trivial syntax edit",
                "medium": "Standard code modification: implement bounded function, write standard unit test, add parameter, or localized refactoring",
                "high": "Deep cognitive task: architectural design, race condition, distributed deadlock, concurrency kernel bug, or complex multi-file debugging",
            },
        ),
        "complexity": ScoreQuestion(
            instructions="Rate the cognitive depth required for this next step",
            criteria=["trivial_mechanical", "standard_implementation", "complex_logic", "exceptional_architecture"],
        ),
    }

    clean_context = context.strip()
    if len(clean_context) > 4000:
        clean_context = clean_context[:1500] + "\n...[truncated]...\n" + clean_context[-2500:]

    resp = client.system_one(state=clean_context, questions=questions)

    effort_ans = resp.answers.get("effort")
    comp_ans = resp.answers.get("complexity")

    effort = effort_ans.choice if effort_ans and hasattr(effort_ans, "choice") else "medium"
    conf = effort_ans.confidence if effort_ans and hasattr(effort_ans, "confidence") else 0.85
    comp_score = comp_ans.score if comp_ans and hasattr(comp_ans, "score") else 2.0

    params, is_supported, rationale, cache_rec = build_provider_params(provider, effort, model)

    if session_context_tokens > 30000 and is_supported:
        cache_rec = (
            f"HIGH CACHE RISK ({session_context_tokens} tokens active): Modulating reasoning effort across turns "
            "may invalidate prefix KV cache. Hysteresis recommended: preserve stable reasoning effort across active sub-steps."
        )

    result = ReasoningEffortResult(
        effort=effort,
        confidence=conf,
        complexity_score=comp_score,
        rationale=rationale,
        provider=provider,
        provider_params=params,
        is_reasoning_supported=is_supported,
        cache_safe_recommendation=cache_rec,
        is_mock=resp.is_mock,
    )

    try:
        record_reasoning_effort_event(result.effort, provider=provider)
    except Exception:
        pass

    return result
