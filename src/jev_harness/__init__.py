"""
Jev System One Decision Harness & Token Optimizer.
Fast, non-autoregressive semantic decisions for AI coding agents.
"""

__version__ = "0.1.2"
__author__ = "Ismael Hosni Soilet de Lima"
__license__ = "MIT"

from .client import (
    AnswerType,
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
    TestTriageResult,
    VerificationResult,
    route_model_tier,
    should_abort_trajectory,
    triage_test_failure,
    verify_step_completion,
)

__all__ = [
    "__version__",
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
]
