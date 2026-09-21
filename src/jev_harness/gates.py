"""
Semantic Decision Gates powered by Jev System One.
Designed to prevent token waste, filter test suites, abort hallucinated trajectories,
and route tasks to the cheapest effective model tier.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from .client import ChoiceQuestion, JevClient, NoulQuestion, ScoreQuestion


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
        clean_log = "...[truncated]...\n" + clean_log[-5500:]

    resp = client.system_one(state=clean_log, questions=questions)

    cat_ans = resp.answers.get("category")
    skip_ans = resp.answers.get("skip_llm")
    sev_ans = resp.answers.get("severity")

    category = cat_ans.choice if cat_ans and hasattr(cat_ans, "choice") else "deep_logic"
    confidence = cat_ans.confidence if cat_ans and hasattr(cat_ans, "confidence") else 0.5
    skip_prob = skip_ans.noul if skip_ans and hasattr(skip_ans, "noul") else 0.0
    sev_score = sev_ans.score if sev_ans and hasattr(sev_ans, "score") else 3.0

    skip_llm = skip_prob >= 0.65 or category in ["env_missing", "flaky_transient"]

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

    return TestTriageResult(
        category=category,
        confidence=confidence,
        skip_llm=skip_llm,
        skip_llm_prob=skip_prob,
        severity_score=sev_score,
        action_recommendation=rec,
        is_mock=resp.is_mock,
        details={"model": resp.model, "usage": resp.usage},
    )


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

    state = f"RECENT ATTEMPTS & CONTEXT:\n{recent_attempts_summary}\n\nPROPOSED NEXT STEP:\n{proposed_step}"

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

    return AbortGateResult(
        should_abort=should_abort,
        abort_probability=dead_end_prob,
        action=effective_action,
        viability_score=viability,
        reasoning_summary=summary,
        is_mock=resp.is_mock,
    )


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

    return ModelRouteResult(
        selected_tier=tier,
        confidence=conf,
        complexity_score=comp,
        rationale=rationale,
        recommended_model=model_rec,
        is_mock=resp.is_mock,
    )


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
