"""
Jev System One Decision Harness & Token Optimizer.
Fast, non-autoregressive semantic decisions for AI coding agents.
"""

__version__ = "0.1.13"
__author__ = "Ismael Hosni Soilet de Lima"
__license__ = "MIT"

from .config import (
    DEFAULT_ABORT_THRESHOLD,
    DEFAULT_SKIP_LLM_THRESHOLD,
    load_repo_config,
)
from .client import (
    COMMANDCODE_API_URL,
    AnswerType,
    looks_like_test_success,
    ChoiceAnswer,
    ChoiceQuestion,
    JevClient,
    JevResponse,
    NoulAnswer,
    NoulQuestion,
    QuestionType,
    ScoreAnswer,
    ScoreQuestion,
)
from .gates import (
    AbortGateResult,
    ModelRouteResult,
    NudgeGateResult,
    ReasoningEffortResult,
    TestTriageResult,
    VerificationResult,
    modulate_reasoning_effort,
    route_model_tier,
    should_abort_trajectory,
    should_nudge_continuation,
    triage_test_failure,
    verify_step_completion,
)

__all__ = [
    "__version__",
    "COMMANDCODE_API_URL",
    "looks_like_test_success",
    "DEFAULT_ABORT_THRESHOLD",
    "DEFAULT_SKIP_LLM_THRESHOLD",
    "load_repo_config",
    "JevClient",
    "ChoiceQuestion",
    "ScoreQuestion",
    "NoulQuestion",
    "QuestionType",
    "ChoiceAnswer",
    "ScoreAnswer",
    "NoulAnswer",
    "AnswerType",
    "JevResponse",
    "triage_test_failure",
    "TestTriageResult",
    "should_abort_trajectory",
    "AbortGateResult",
    "route_model_tier",
    "ModelRouteResult",
    "verify_step_completion",
    "VerificationResult",
    "modulate_reasoning_effort",
    "ReasoningEffortResult",
    "should_nudge_continuation",
    "NudgeGateResult",
]
