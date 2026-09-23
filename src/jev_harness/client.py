"""
Jev System One HTTP Client.
Connects to TypeSafe AI's System One API (POST https://api.typesafe.ai/v1/systemone)
with zero external dependencies (pure Python standard library) and fallback simulation mode.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import http.client
import json
import math
import os
from pathlib import Path
import re
import socket
import sys
import time
from typing import Any, Dict, List, Optional, Union
import urllib.error
import urllib.request

from .config import load_repo_config
from .perception import redact_secrets
from .uncertainty import validate_question_options
from .state import render_state_text

TYPESAFE_API_URL = "https://api.typesafe.ai/v1/systemone"
OPENCODE_API_URL = "https://opencode.ai/zen/v1/systemone"
COMMANDCODE_API_URL = "https://api.commandcode.ai/provider/v1/systemone"
OPENROUTER_API_URL = "https://openrouter.ai/api/alpha/decisions"
OPENROUTER_CHAT_API_URL = "https://openrouter.ai/api/v1/chat/completions"
VERCEL_API_URL = "https://ai-gateway.vercel.sh/v1/evaluate"
DEFAULT_MODEL = "jev-latest"

# Provider payload limits (jev-1.13: 64k tokens total; 32k for state + longest question).
# Characters are a conservative proxy (~4 chars/token) with no external tokenizer.
MAX_STATE_CHARS = 128_000
MAX_TOTAL_CHARS = 256_000
DEFAULT_USER_AGENT = "Mozilla/5.0 (compatible; JevHarness/0.2.0; +https://github.com/ismaelsoilet/jev-harness)"

# Success summaries emitted by common runners when a suite is green. Used to short-circuit
# triage: a passing run must never be escalated, and it must never cost an API call.
# Non-zero pass counts are required so an empty suite ("0 passed, 0 total") is not a claim.
_SUCCESS_PATTERNS = (
    r"test result:\s*ok",                          # cargo test
    r"[1-9][\d,]*\s+passed\b",                     # pytest / vitest / jest
    r"[1-9]\d*\s+passing\b",                     # mocha
    r"test suites?:\s*[1-9]\d*\s+passed",         # jest summary
    r"[1-9]\d*\s+examples?,\s*0\s+failures",      # rspec
    r"all tests? passed",
    r"\bbuild success(?:ful)?\b",
    r"^\s*ok\s+\S+",                              # go test
)

# Evidence that vetoes the success short-circuit: a non-zero failure count or a concrete
# failure marker. "0 failed" / "0 errors" / "failures: 0" / "0 failing" are NOT vetoes.
_FAILURE_COUNT_PATTERN = (
    r"{first}{rest}*\s*(?:failures|failure|failed|failing|errors?)\b"
).format(first=r"[1-9１-９١-٩۱-۹]", rest=r"[\d,._  ０-９٠-٩۰-۹]")
_FAILURE_ASSIGN_PATTERN = r"(?:failures?|errors?|failed|failing)\s*[:=]\s*[1-9]"
_FAILURE_NOUN_PATTERN = (
    r"\b{first}{rest}*\s+tests?\s+failed\b"
).format(first=r"[1-9１-９١-٩۱-۹]", rest=r"[\d,._  ０-９٠-٩۰-۹]")
# NOTE: `error:` must not be followed by `\b` — a colon before a space has no word boundary,
# which would silently disable this veto (caught by adversarial review).
_FAILURE_MARKER_PATTERN = (
    r"\b(?:traceback|panic|panicked|assertionerror|assertion failed|not ok)\b|error\s*:"
)
_FAILURE_GLYPHS = ("✗", "✘", "✕", "×", "‼", "❌")
_UNCLEAN_SIGNALS = (
    "module not found",
    "no module named",
    "cannot find module",
    "cannot find crate",
    "command not found",
    "connection refused",
    "connection reset",
    "econnrefused",
    "econnreset",
    "etimedout",
    "socket hang up",
    "address already in use",
    "timed out",
    "timeout",
)


# A failure log is *untrusted input*: the model-jaggedness docs show that adversarial
# content in the state can steer a decision. These markers mean "this text is trying to
# give the judge instructions", so the log is escalated instead of classified.
_INJECTION_PATTERNS = (
    # Instruction override aimed at the judge.
    r"ignore\s+(?:all\s+|any\s+|the\s+)?(?:previous|prior|above|earlier|foregoing)\s+"
    r"(?:instruction|prompt|rule|direction|message)s?",
    r"disregard\s+(?:all\s+|any\s+|the\s+)?(?:above|previous|prior|earlier|system)",
    r"\b(?:ignore|bypass|override)\s+(?:the\s+)?(?:gate|harness|instructions?|safety|polic(?:y|ies))\b",
    # Chat-template turn markers: a real failure log never carries them.
    r"<\|(?:im_start|im_end|system|assistant|user)\|>",
    r"\[/?(?:INST|SYS)\]",
    r"###\s*(?:system|instruction|assistant)\b",
    r'"role"\s*:\s*"(?:system|assistant)"\s*,\s*"content"',
    # The log dictating the harness verdict (verb-based, so quoting harness *output* as
    # data is not flagged).
    r"\bskip_llm\s*[:=]\s*(?:true|false)\b",
    r"\b(?:classif|labell?|mark|report|record|return|output|respond|answer)\w*\b[^.\n]{0,60}\b"
    r"(?:as\s+)?(?:env_missing|flaky_transient|syntax_trivial|no_failure)\b",
    r"\b(?:do\s+not|don't|never)\s+(?:call|invoke|use|escalate\s+to)\s+(?:the\s+)?"
    r"(?:llm|model|api|system\s*2|frontier)\b",
)


def looks_like_prompt_injection(log: str) -> bool:
    """
    Returns True when a failure log is trying to address the judge instead of describing a
    failure. Untrusted log content must never be able to talk the harness into skipping the
    expensive path, so a match escalates the triage (`deep_logic`, `skip_llm=False`).
    """
    if not log:
        return False
    return any(re.search(pattern, log, re.IGNORECASE | re.MULTILINE) for pattern in _INJECTION_PATTERNS)


def looks_like_test_success(log: str) -> bool:
    """
    Returns True only when a log is unequivocally a *successful* run summary.

    Strict by design: a positive success summary is required AND every failure signal
    (non-zero counts, FAIL/FAILED markers, tracebacks, panics, dependency or transient
    errors, failure glyphs) must be absent. This guarantees a real failure can never be
    short-circuited into the `no_failure` verdict.
    """
    if not log or not log.strip():
        return False

    text = log.lower()

    # 1. Failure vetoes.
    if re.search(_FAILURE_COUNT_PATTERN, text):
        return False
    if re.search(_FAILURE_NOUN_PATTERN, text):
        return False
    if re.search(_FAILURE_ASSIGN_PATTERN, text):
        return False
    if re.search(_FAILURE_MARKER_PATTERN, text):
        return False
    if (
        re.search(r"\bFAILED\b", log)
        or re.search(r"(?:^|\n)\s*FAIL\b", log)
        or re.search(r"---\s*FAIL\b", log)
    ):
        return False
    if any(marker in log for marker in _FAILURE_GLYPHS):
        return False
    if any(signal in text for signal in _UNCLEAN_SIGNALS):
        return False

    # 2. Positive success summaries.
    if any(re.search(pattern, text, re.MULTILINE) for pattern in _SUCCESS_PATTERNS):
        return True
    if re.search(r"ran\s+[1-9]\d*\s+tests?", text) and re.search(
        r"^\s*ok\s*$", text, re.MULTILINE
    ):
        return True
    return False


# Mock distribution contract (E3.9). The three runtimes must produce identical probabilities
# for the same input, so these constants are mirrored in `packages/ts/src/client.ts` and
# `packages/rust/src/client.rs` and asserted against `tests/fixtures/mock_golden.json`.
# A signal *conflict* (an explicit assertion next to an environment/transient signal) lowers
# the peak on purpose: the CI can then exercise `escalate_to_system2` deterministically.
MOCK_CHOICE_BEST_PEAKED = 0.85
MOCK_CHOICE_BEST_CONFLICT = 0.55
MOCK_SCORE_BEST_PEAKED = 0.80


def _parse_cost(value: Any) -> float:
    """Provider cost for one decision: accepts a number or a numeric string, else 0.0."""
    if isinstance(value, bool) or value is None:
        return 0.0
    try:
        cost = float(value)
    except (TypeError, ValueError):
        return 0.0
    return cost if math.isfinite(cost) and cost >= 0 else 0.0


def _mock_abort_step_text(structured: Optional[Dict[str, Any]], state_lower: str) -> str:
    """The proposed step as plain text: the structured field first, the legacy marker second."""
    if structured is not None:
        value = structured.get("proposed_step")
        if isinstance(value, str) and value.strip():
            return value.lower()
    text = state_lower
    for marker in ("proposed next step:", "proposed_next_step:"):
        if marker in text:
            text = text.split(marker)[-1]
    return text


def _mock_is_abort_action(
    question: "ChoiceQuestion", structured: Optional[Dict[str, Any]], state_lower: str
) -> bool:
    """True for the abort gate's action question (proceed / replan / abort_and_ask)."""
    del structured, state_lower
    return "abort_and_ask" in question.criteria and "proceed" in question.criteria


def _mock_abort_action_choice(
    question: "ChoiceQuestion", structured: Optional[Dict[str, Any]], state_lower: str
) -> str:
    """Derives the action from the same signals the dead-end question uses."""
    step = _mock_abort_step_text(structured, state_lower)
    forward = any(
        word in step
        for word in [
            "implement", "fix", "resolve", "correct", "update", "create", "write", "add",
            "install", "apply", "corrigir", "implementar", "executar", "validar", "corregir",
        ]
    )
    repetitive = any(
        word in step
        for word in ["same", "repetir", "tentar novamente", "intentar de nuevo", "4a vez", "again", "identical"]
    )
    fatal = any(
        key in state_lower
        for key in [
            "impossible", "impossivel", "imposible", "circular", "deadlock", "dead end",
            "inviavel", "inviable", "hopeless", "fatal",
        ]
    )
    if repetitive or fatal:
        return "abort_and_ask" if "abort_and_ask" in question.criteria else list(question.criteria)[0]
    if forward and "proceed" in question.criteria:
        return "proceed"
    return ""


def _mock_distribution(options: Sequence[str], best: str, peak: float) -> Dict[str, float]:
    """Peaked distribution over `options` summing to 1.0 (1.0 when there is a single option)."""
    if len(options) <= 1:
        return {opt: 1.0 for opt in options}
    rest = (1.0 - peak) / (len(options) - 1)
    return {opt: (peak if opt == best else rest) for opt in options}


def _mock_has_signal_conflict(
    is_explicit_assertion: bool,
    has_deadlock_or_loop: bool,
    has_env_signal: bool,
    has_flaky_signal: bool,
) -> bool:
    """Two signal families disagreeing (an assertion/deadlock next to an environment or
    transient cause) lowers the mock's peak so escalation can be exercised deterministically."""
    return (is_explicit_assertion or has_deadlock_or_loop) and (has_env_signal or has_flaky_signal)


def _required_number(answer: Dict[str, Any], key: str, qid: str) -> float:
    """Reads a required JSON number. A missing, boolean, textual or non-finite value is a
    malformed answer, matching the strictness the Rust runtime gets from serde."""
    value = answer.get(key)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"malformed response: answer '{qid}' is missing a numeric {key!r}")
    try:
        number = float(value)
    except OverflowError:
        raise ValueError(f"malformed response: answer '{qid}' has an out-of-range {key!r}")
    if not math.isfinite(number):
        # `json.loads` accepts the non-standard NaN/Infinity literals; TS and Rust reject them.
        raise ValueError(f"malformed response: answer '{qid}' has a non-finite {key!r}")
    return number


def _required_text(answer: Dict[str, Any], key: str, qid: str) -> str:
    """Reads a required string field. A missing or type-mismatched value is a malformed answer."""
    value = answer.get(key)
    if not isinstance(value, str):
        raise ValueError(f"malformed response: answer '{qid}' is missing a textual {key!r}")
    return value


def _urlopen_with_ipv4_fallback(req: urllib.request.Request, timeout: float):
    """Attempts urlopen, retrying with IPv4-only DNS only when IPv6 resolution fails.

    HTTPError and other transport errors must propagate untouched: retrying them here would
    multiply provider requests and bypass the caller's Retry-After/backoff policy.
    """
    try:
        return urllib.request.urlopen(req, timeout=timeout)
    except urllib.error.HTTPError:
        raise
    except urllib.error.URLError as e:
        reason = getattr(e, "reason", e)
        if not isinstance(reason, socket.gaierror):
            raise
        orig_getaddrinfo = socket.getaddrinfo

        def ipv4_getaddrinfo(host, port, family=0, type=0, proto=0, flags=0):
            return orig_getaddrinfo(host, port, socket.AF_INET, type, proto, flags)

        try:
            socket.getaddrinfo = ipv4_getaddrinfo
            return urllib.request.urlopen(req, timeout=timeout)
        except Exception:
            raise e
        finally:
            socket.getaddrinfo = orig_getaddrinfo


@dataclass
class ChoiceQuestion:
    """
    Choice Question: evaluates state and selects exactly one option from criteria map.
    Returns chosen key, confidence (0-1), and probability distribution across all choices.
    """
    instructions: str
    criteria: Dict[str, str]

    def __post_init__(self) -> None:
        # E3.1: a single-option question has no distribution to measure.
        from .uncertainty import validate_question_options

        validate_question_options(list(self.criteria))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "choice",
            "instructions": self.instructions,
            "criteria": self.criteria,
        }


@dataclass
class ScoreQuestion:
    """
    Score Question: rates state against an ordered rubric scale.
    criteria must contain at least 2 ordered levels (e.g. ["poor", "acceptable", "good", "excellent"]).
    Returns numeric score, confidence, and probability distribution.
    """
    instructions: str
    criteria: List[str]

    def __post_init__(self) -> None:
        from .uncertainty import validate_question_options

        validate_question_options(list(self.criteria))

    def __post_init__(self) -> None:
        if len(self.criteria) < 2:
            raise ValueError("Score question criteria must contain at least 2 ordered levels.")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "score",
            "instructions": self.instructions,
            "criteria": self.criteria,
        }


@dataclass
class NoulQuestion:
    """
    Noul Question: evaluates boolean truth probability (0.0 to 1.0) that answer is affirmative.
    """
    instructions: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "noul",
            "instructions": self.instructions,
        }


QuestionType = Union[ChoiceQuestion, ScoreQuestion, NoulQuestion]


@dataclass
class ChoiceAnswer:
    choice: str
    confidence: float
    probabilities: Dict[str, float] = field(default_factory=dict)


@dataclass
class ScoreAnswer:
    score: float
    confidence: float
    probabilities: Dict[str, float] = field(default_factory=dict)
    legend: Any = field(default_factory=list)  # live: level -> description map; clients may send a list


@dataclass
class NoulAnswer:
    noul: float  # probability 0.0 to 1.0 that answer is affirmative/yes


AnswerType = Union[ChoiceAnswer, ScoreAnswer, NoulAnswer]


@dataclass
class JevResponse:
    model: str
    answers: Dict[str, AnswerType]
    usage: Dict[str, int]
    is_mock: bool = False
    degraded_reason: str = ""
    # Provider-reported spend for this decision (0.0 when the provider omits it, or in mock
    # mode). Deliberately separate from the session's *estimated* savings model.
    cost_usd: float = 0.0
    # Provenance for a decision served from the local cache (E3.2) / coalesced (E3.3).
    cached: bool = False
    debounced: bool = False
    raw_response: Optional[Dict[str, Any]] = None


class JevClient:
    """
    Zero-dependency client for TypeSafe AI Jev System One API.
    Supports TypeSafe direct, OpenCode Zen, and OpenRouter, with offline heuristic simulation.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        timeout: float = 15.0,
        force_mock: bool = False,
        provider: Optional[str] = None,
        max_retries: int = 3,
        retry_base_delay: float = 0.5,
        fail_open: bool = True,
        measure_usage: bool = True,
        cache: bool = False,
    ):
        self.timeout = timeout
        self.force_mock = force_mock
        self.max_retries = max(1, int(max_retries))
        self.retry_base_delay = max(0.0, float(retry_base_delay))
        self.fail_open = bool(fail_open)
        self.measure_usage = bool(measure_usage)
        # Opt-in for embedders: a library caller asking twice for the same decision gets two
        # decisions unless they ask for the cache. The CLI enables it (and offers --no-cache).
        self.cache = bool(cache)
        resolved_key, resolved_provider = self._resolve_credentials()
        self.provider = provider or resolved_provider
        self.api_key = api_key or resolved_key

        # Configure URL and model based on provider
        if base_url:
            self.base_url = base_url
        elif self.provider == "opencode":
            self.base_url = OPENCODE_API_URL
        elif self.provider == "commandcode":
            self.base_url = COMMANDCODE_API_URL
        elif self.provider == "openrouter":
            self.base_url = OPENROUTER_API_URL
        elif self.provider == "vercel":
            self.base_url = VERCEL_API_URL
        else:
            self.base_url = TYPESAFE_API_URL

        # Resolution order: explicit argument > `JEV_MODEL` env var > repository `.jev.json`
        # override > provider default. The generic placeholder (`jev-latest`, what
        # `jev-harness init` scaffolds) is treated as "no override" so scaffolded configs never
        # clobber provider model IDs.
        repo_model = load_repo_config().get("model")
        env_model = os.getenv("JEV_MODEL")
        if model:
            self.model = model
            self.model_source = "argument"
        elif env_model and env_model.strip():
            self.model = env_model.strip()
            self.model_source = "env"
        elif repo_model and repo_model != DEFAULT_MODEL:
            self.model = str(repo_model)
            self.model_source = ".jev.json"
        elif self.provider == "opencode":
            self.model = "jev-1.13-free"
            self.model_source = "provider_default"
        elif self.provider == "commandcode":
            self.model = "typesafe/jev"
            self.model_source = "provider_default"
        elif self.provider == "openrouter":
            self.model = "typesafe/jev-1.13"
            self.model_source = "provider_default"
        elif self.provider == "vercel":
            self.model = "typesafe-ai/jev"
            self.model_source = "provider_default"
        else:
            self.model = DEFAULT_MODEL
            self.model_source = "provider_default"

    @staticmethod
    def _resolve_credentials() -> tuple[Optional[str], str]:
        """Resolves API key and provider using hierarchical cascade."""
        # 1. Environment variables
        if os.getenv("JEV_PROVIDER") == "opencode":
            return os.getenv("OPENCODE_API_KEY"), "opencode"
        if os.getenv("JEV_PROVIDER") == "commandcode":
            return (
                os.getenv("CMD_API_KEY") or os.getenv("COMMAND_CODE_API_KEY"),
                "commandcode",
            )
        if os.getenv("TYPESAFE_API_KEY"):
            return os.getenv("TYPESAFE_API_KEY"), "typesafe"
        if os.getenv("CMD_API_KEY"):
            return os.getenv("CMD_API_KEY"), "commandcode"
        if os.getenv("COMMAND_CODE_API_KEY"):
            return os.getenv("COMMAND_CODE_API_KEY"), "commandcode"
        if os.getenv("VERCEL_AI_GATEWAY_API_KEY"):
            return os.getenv("VERCEL_AI_GATEWAY_API_KEY"), "vercel"
        if os.getenv("VERCEL_API_KEY"):
            return os.getenv("VERCEL_API_KEY"), "vercel"
        if os.getenv("AI_GATEWAY_API_KEY"):
            return os.getenv("AI_GATEWAY_API_KEY"), "vercel"
        if os.getenv("OPENCODE_API_KEY"):
            return os.getenv("OPENCODE_API_KEY"), "opencode"
        if os.getenv("OPENROUTER_API_KEY"):
            return os.getenv("OPENROUTER_API_KEY"), "openrouter"

        # 2. Local repo config (.jev.json or .env in CWD or parent directories)
        try:
            current = Path.cwd()
            candidates = [current, *current.parents]
            for candidate in candidates[:4]:
                jev_json = candidate / ".jev.json"
                if jev_json.exists():
                    try:
                        data = json.loads(jev_json.read_text(encoding="utf-8"))
                        provider = data.get("provider", "typesafe")
                        if provider == "opencode" or data.get("api_key"):
                            return data.get("api_key"), provider
                    except Exception:
                        pass

                dotenv_file = candidate / ".env"
                if dotenv_file.exists():
                    try:
                        content = dotenv_file.read_text(encoding="utf-8")
                        for line in content.splitlines():
                            line = line.strip()
                            if line.startswith("JEV_PROVIDER=") and line.split("=", 1)[1].strip(" '\"") == "opencode":
                                return None, "opencode"
                            if line.startswith("TYPESAFE_API_KEY="):
                                return line.split("=", 1)[1].strip(" '\""), "typesafe"
                            if line.startswith(("CMD_API_KEY=", "COMMAND_CODE_API_KEY=")):
                                return line.split("=", 1)[1].strip(" '\""), "commandcode"
                            if line.startswith(("VERCEL_AI_GATEWAY_API_KEY=", "VERCEL_API_KEY=", "AI_GATEWAY_API_KEY=")):
                                return line.split("=", 1)[1].strip(" '\""), "vercel"
                            if line.startswith("OPENCODE_API_KEY="):
                                return line.split("=", 1)[1].strip(" '\""), "opencode"
                            if line.startswith("OPENROUTER_API_KEY="):
                                return line.split("=", 1)[1].strip(" '\""), "openrouter"
                    except Exception:
                        pass
        except Exception:
            pass

        # 3. Global user config (~/.config/jev/credentials.env or ~/.commandcode/auth.json)
        try:
            global_creds = Path.home() / ".config" / "jev" / "credentials.env"
            if global_creds.exists():
                content = global_creds.read_text(encoding="utf-8")
                for line in content.splitlines():
                    line = line.strip()
                    if line.startswith("TYPESAFE_API_KEY="):
                        return line.split("=", 1)[1].strip(" '\""), "typesafe"
                    if line.startswith(("CMD_API_KEY=", "COMMAND_CODE_API_KEY=")):
                        return line.split("=", 1)[1].strip(" '\""), "commandcode"
                    if line.startswith(("VERCEL_AI_GATEWAY_API_KEY=", "VERCEL_API_KEY=", "AI_GATEWAY_API_KEY=")):
                        return line.split("=", 1)[1].strip(" '\""), "vercel"
                    if line.startswith("OPENCODE_API_KEY="):
                        return line.split("=", 1)[1].strip(" '\""), "opencode"
                    if line.startswith("OPENROUTER_API_KEY="):
                        return line.split("=", 1)[1].strip(" '\""), "openrouter"
        except Exception:
            pass

        try:
            cmd_auth = Path.home() / ".commandcode" / "auth.json"
            if cmd_auth.exists():
                data = json.loads(cmd_auth.read_text(encoding="utf-8"))
                cmd_key = data.get("apiKey") or data.get("api_key")
                if cmd_key and str(cmd_key).strip():
                    return str(cmd_key).strip(), "commandcode"
        except Exception:
            pass

        return None, "mock"

    @property
    def is_live(self) -> bool:
        if self.force_mock:
            return False
        if self.provider == "opencode":
            return True
        return bool(self.api_key)

    def system_one(
        self,
        state: Union[str, Dict[str, Any], List[Any]],
        questions: Dict[str, QuestionType],
        model: Optional[str] = None,
        gate: str = "system_one",
    ) -> JevResponse:
        """
        Sends a single batch request to Jev System One API.
        All questions are evaluated in parallel in one pass against state.
        """
        if not questions:
            raise ValueError("Questions dictionary cannot be empty.")

        state_str = json.dumps(state) if isinstance(state, (dict, list)) else str(state)
        # E3.5: redact before anything is transmitted, for every gate (the CLI, MCP and SDK all
        # funnel through here). The guard below then measures the string that actually leaves.
        state_str = redact_secrets(state_str)
        chosen_model = model or self.model

        # Fallback to simulation/mock if no key is configured or forced mock
        if not self.is_live:
            return self._simulate_system_one(state_str, questions, chosen_model)

        questions_chars = len(json.dumps({qid: q.to_dict() for qid, q in questions.items()}))
        if len(state_str) > MAX_STATE_CHARS or len(state_str) + questions_chars > MAX_TOTAL_CHARS:
            raise RuntimeError(
                f"Payload exceeds the provider limit: {len(state_str)} state chars + {questions_chars} question chars "
                f"(limit: {MAX_STATE_CHARS} state / {MAX_TOTAL_CHARS} total, ~32k/64k tokens). "
                "Trim the state or split the questions."
            )

        if self.provider == "openrouter" and "chat/completions" in self.base_url:
            return self._call_openrouter(state_str, questions, chosen_model)

        # E3.1: a question with a single option has no distribution to measure; refuse it here so
        # every runtime (CLI, MCP, SDK) behaves the same way.
        for question in questions.values():
            if isinstance(question, (ChoiceQuestion, ScoreQuestion)):
                validate_question_options(list(question.criteria))

        payload: Dict[str, Any] = {
            "model": chosen_model,
            "state": state_str,
            "questions": {qid: q.to_dict() for qid, q in questions.items()},
        }
        if self.provider == "openrouter":
            payload["provider"] = {"only": ["typesafe"], "allow_fallbacks": False}
        elif self.provider == "vercel":
            payload["providerOptions"] = {"gateway": {"only": ["typesafe-ai"]}}

        headers = {
            "Content-Type": "application/json",
            "User-Agent": DEFAULT_USER_AGENT,
        }
        if self.api_key and self.api_key != "zen":
            headers["Authorization"] = f"Bearer {self.api_key}"

        req_data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(self.base_url, data=req_data, headers=headers, method="POST")

        cache_hit = None
        cache_gate = gate
        if self.cache and self.is_live:
            cache_hit = self._cache_lookup(cache_gate, state_str, questions, chosen_model)

        provider_map = {
            "opencode": "OpenCode Zen",
            "commandcode": "Command Code",
            "openrouter": "OpenRouter",
            "vercel": "Vercel AI Gateway",
        }
        provider_label = provider_map.get(self.provider, "TypeSafe")

        if cache_hit is not None:
            return cache_hit

        attempt = 0
        while True:
            attempt += 1
            attempt_started = time.monotonic()
            try:
                with _urlopen_with_ipv4_fallback(req, timeout=self.timeout) as resp:
                    raw_body = resp.read().decode("utf-8", errors="replace")
                try:
                    resp_data = json.loads(raw_body)
                except ValueError:
                    if attempt < self.max_retries:
                        time.sleep(self._retry_delay(attempt))
                        continue
                    return self._degrade_or_raise(
                        f"{provider_label} returned a non-JSON response",
                        "invalid_response",
                        state_str,
                        questions,
                        chosen_model,
                    )
                try:
                    response = self._parse_response(resp_data, chosen_model, is_mock=False)
                    self._record_measurement(response, time.monotonic() - attempt_started)
                    self._cache_store(cache_gate, state_str, questions, chosen_model, resp_data, response)
                    return response
                except (ValueError, TypeError, AttributeError, KeyError) as e:
                    # A 200 with type-mismatched fields (score: "N/A", answers: [...]) is a parse
                    # failure, not a crash: it follows the same failure policy as a bad status.
                    if attempt < self.max_retries:
                        time.sleep(self._retry_delay(attempt))
                        continue
                    return self._degrade_or_raise(
                        f"{provider_label} returned a malformed response: {self._redact_secrets(str(e), self.api_key)}",
                        "invalid_response",
                        state_str,
                        questions,
                        chosen_model,
                    )
            except urllib.error.HTTPError as e:
                try:
                    err_body = e.read().decode("utf-8", errors="replace") if getattr(e, "fp", None) is not None else str(e)
                except Exception:
                    err_body = str(e)
                err_body = self._redact_secrets(err_body, self.api_key)
                if e.code in (401, 403):
                    try:
                        return self._degrade_or_raise(
                            f"{provider_label} auth failed (HTTP {e.code})",
                            f"auth_{e.code}",
                            state_str,
                            questions,
                            chosen_model,
                        )
                    except RuntimeError as err:
                        raise err from e
                retryable = e.code == 429 or e.code >= 500
                if retryable and attempt < self.max_retries:
                    retry_after = e.headers.get("Retry-After") if getattr(e, "headers", None) else None
                    time.sleep(self._retry_delay(attempt, retry_after))
                    continue
                try:
                    return self._degrade_or_raise(
                        f"{provider_label} API returned HTTP {e.code}: {err_body}",
                        f"http_{e.code}",
                        state_str,
                        questions,
                        chosen_model,
                    )
                except RuntimeError as err:
                    raise err from e
            except (urllib.error.URLError, TimeoutError, OSError, http.client.HTTPException) as e:
                # Dropped connections raise RemoteDisconnected/ConnectionResetError (OSError) and
                # malformed responses raise BadStatusLine (HTTPException): both are transport
                # failures and must follow the policy, never escape as a traceback.
                reason = self._redact_secrets(str(e.reason if hasattr(e, "reason") else e), self.api_key)
                if attempt < self.max_retries:
                    time.sleep(self._retry_delay(attempt))
                    continue
                # A read timeout surfaces as URLError(socket.timeout) on some platforms:
                # classify by elapsed time so the marker matches the other runtimes.
                elapsed = time.monotonic() - attempt_started
                timed_out = isinstance(e, TimeoutError) or elapsed >= max(0.1, self.timeout * 0.9)
                try:
                    return self._degrade_or_raise(
                        f"Failed to connect to {provider_label} API ({self.base_url}): {reason}",
                        "timeout" if timed_out else "connection",
                        state_str,
                        questions,
                        chosen_model,
                    )
                except RuntimeError as err:
                    raise err from e

    def _cache_key(self, gate: str, state_str: str, questions: Dict[str, QuestionType], model: str) -> str:
        from .cache import cache_key

        material = json.dumps({qid: q.to_dict() for qid, q in questions.items()}, sort_keys=True, ensure_ascii=False)
        return cache_key(gate, f"{state_str}\x00{material}", model, self.provider, False)

    def _cache_lookup(
        self, gate: str, state_str: str, questions: Dict[str, QuestionType], model: str
    ) -> Optional["JevResponse"]:
        """E3.2/E3.3: returns a cached live decision, or None. Never used in shadow mode."""
        try:
            from .cache import DEBOUNCE_GATES, debounce_seconds, get as cache_get

            window = debounce_seconds() if gate in DEBOUNCE_GATES else None
            payload, debounced = cache_get(
                gate, self._cache_key(gate, state_str, questions, model), model, self.provider, False,
                window_seconds=window,
            )
            if payload is None:
                return None
            response = self._parse_response(payload, model, is_mock=False)
            response.cached = True
            response.debounced = bool(debounced)
            return response
        except Exception:
            return None

    def _cache_store(
        self,
        gate: str,
        state_str: str,
        questions: Dict[str, QuestionType],
        model: str,
        raw: Dict[str, Any],
        response: "JevResponse",
    ) -> None:
        """Stores a live decision. A degraded answer is a symptom, never a cacheable decision."""
        if not self.cache or not self.is_live or response.degraded_reason:
            return
        try:
            from .cache import put as cache_put

            sanitized = {
                key: raw.get(key)
                for key in ("model", "answers", "usage", "cost")
                if raw.get(key) is not None
            }
            cache_put(
                gate,
                self._cache_key(gate, state_str, questions, model),
                model,
                self.provider,
                False,
                sanitized,
            )
        except Exception:
            return

    def _record_measurement(self, response: "JevResponse", duration_s: float) -> None:
        """E1.4: records what the provider reported for a live decision (never for mock/fallback)."""
        if response.is_mock or self.measure_usage is False:
            return
        usage = response.usage if isinstance(response.usage, dict) else {}
        try:
            from .session import record_measured_usage

            record_measured_usage(
                int(usage.get("input_tokens", 0) or 0),
                int(usage.get("output_tokens", 0) or 0),
                response.cost_usd,
                int(max(0.0, duration_s) * 1000),
            )
        except Exception:
            # Telemetry must never break a decision.
            pass

    def _degrade_or_raise(
        self,
        message: str,
        reason: str,
        state_str: str,
        questions: Dict[str, Any],
        chosen_model: str,
    ) -> "JevResponse":
        """Applies the failure policy: fail-open marks the degraded answer, fail-closed raises."""
        if self.fail_open:
            sys.stderr.write(f"[JEV WARNING] {message}; falling back to offline simulation.\n")
            return self._mark_degraded(self._simulate_system_one(state_str, questions, chosen_model), reason)
        raise RuntimeError(message)

    def _retry_delay(self, attempt: int, retry_after: Optional[str] = None) -> float:
        """Exponential backoff, honoring a provider Retry-After, capped to keep CI fast."""
        if retry_after:
            try:
                seconds = float(str(retry_after).strip())
            except Exception:
                seconds = None
            # A negative or non-finite Retry-After is meaningless: fall back to the backoff,
            # as TS and Rust do.
            if seconds is not None and math.isfinite(seconds) and seconds >= 0:
                return min(30.0, seconds)
        return max(0.0, min(5.0, self.retry_base_delay * (2 ** max(0, attempt - 1))))

    @staticmethod
    def _mark_degraded(resp: "JevResponse", reason: str) -> "JevResponse":
        """Flags a fallback response so consumers can distinguish it from a real decision."""
        resp.degraded_reason = reason
        return resp

    @staticmethod
    def _redact_secrets(text: str, secret: Optional[str] = None) -> str:
        """Redacts API keys and Bearer tokens from error payloads (Astra-Ares provider-error parity)."""
        if not text:
            return ""
        cleaned = text
        if secret and len(secret) >= 4:
            cleaned = cleaned.replace(secret, "[REDACTED]")
        cleaned = re.sub(r"(?:Bearer\s+|(?:vck_|sk-))[A-Za-z0-9._-]+", "[REDACTED]", cleaned, flags=re.IGNORECASE)
        return cleaned[:400]

    def _call_openrouter(
        self, state_str: str, questions: Dict[str, QuestionType], model: str
    ) -> JevResponse:
        """Translates Jev Typed questions to OpenAI-compatible OpenRouter format."""
        if not self.api_key:
            return self._simulate_system_one(state_str, questions, model)

        q_dict = {qid: q.to_dict() for qid, q in questions.items()}
        prompt = (
            "You are Jev System One non-autoregressive decision engine.\n"
            "Evaluate each question against the given STATE.\n"
            "Respond ONLY with a valid JSON object matching this schema:\n"
            "{\n"
            '  "answers": {\n'
            '    "<qid>": {"type": "choice", "choice": "<selected_key>", "confidence": 0.85} OR\n'
            '    "<qid>": {"type": "score", "score": <number>, "confidence": 0.85} OR\n'
            '    "<qid>": {"type": "noul", "noul": <float_0_to_1>}\n'
            "  }\n"
            "}\n\n"
            f"STATE:\n{state_str}\n\n"
            f"QUESTIONS:\n{json.dumps(q_dict, indent=2)}"
        )
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "response_format": {"type": "json_object"},
            "temperature": 0.0,
        }
        headers = {
            "Content-Type": "application/json",
            "User-Agent": DEFAULT_USER_AGENT,
            "Authorization": f"Bearer {self.api_key}",
            "HTTP-Referer": "https://github.com/ismaelsoilet/jev-harness",
            "X-Title": "Jev Harness",
        }
        req_data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(self.base_url, data=req_data, headers=headers, method="POST")
        cache_hit = self._cache_lookup("openrouter-chat", state_str, questions, model) if self.cache else None
        if cache_hit is not None:
            return cache_hit
        attempt = 0
        while True:
            attempt += 1
            attempt_started = time.monotonic()
            try:
                with _urlopen_with_ipv4_fallback(req, timeout=self.timeout) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                    content = data["choices"][0]["message"]["content"]
                    parsed_json = json.loads(content)
                    response = self._parse_response(parsed_json, model, is_mock=False)
                    self._record_measurement(response, time.monotonic() - attempt_started)
                    self._cache_store("openrouter-chat", state_str, questions, model, parsed_json, response)
                    return response
            except Exception as e:
                retryable = isinstance(
                    e, (urllib.error.URLError, TimeoutError, OSError, http.client.HTTPException, ValueError, KeyError)
                )
                if retryable and attempt < self.max_retries:
                    time.sleep(self._retry_delay(attempt))
                    continue
                # Same failure policy as the native endpoint: fail-open marks the fallback,
                # fail-closed surfaces the error instead of returning a silent simulation.
                return self._degrade_or_raise(
                    f"OpenRouter-compatible endpoint failed ({self._redact_secrets(str(e), self.api_key)})",
                    "invalid_response",
                    state_str,
                    questions,
                    model,
                )

    def _parse_response(self, data: Dict[str, Any], model: str, is_mock: bool) -> JevResponse:
        parsed_answers: Dict[str, AnswerType] = {}
        raw_answers = data.get("answers")
        if raw_answers is None:
            raw_answers = {}
        if not isinstance(raw_answers, dict):
            raise ValueError("malformed response: 'answers' must be a JSON object")

        for qid, ans in raw_answers.items():
            if not isinstance(ans, dict):
                raise ValueError(f"malformed response: answer '{qid}' must be a JSON object")
            ans_type = ans.get("type")
            if ans_type == "choice":
                parsed_answers[qid] = ChoiceAnswer(
                    choice=_required_text(ans, "choice", qid),
                    confidence=_required_number(ans, "confidence", qid),
                    probabilities=ans.get("probabilities", {}),
                )
            elif ans_type == "score":
                parsed_answers[qid] = ScoreAnswer(
                    score=_required_number(ans, "score", qid),
                    confidence=_required_number(ans, "confidence", qid),
                    probabilities=ans.get("probabilities", {}),
                    legend=ans.get("legend", []),
                )
            elif ans_type == "noul":
                parsed_answers[qid] = NoulAnswer(noul=_required_number(ans, "noul", qid))
            else:
                # An answer the runtime cannot interpret must never be dropped: the gate would
                # silently use its default score instead of the provider's judgement.
                raise ValueError(f"malformed response: answer '{qid}' has an unsupported type {ans_type!r}")

        raw_usage = data.get("usage")
        usage = raw_usage if isinstance(raw_usage, dict) else {
            "input_tokens": len(str(data.get("state", ""))) // 4,
            "output_tokens": 0,
        }
        if not parsed_answers and not is_mock:
            # A live response with nothing usable would silently make every gate fall back to
            # its defaults; that must be a visible degradation instead.
            raise ValueError("malformed response: no answers could be parsed")
        return JevResponse(
            model=data.get("model", model),
            answers=parsed_answers,
            usage=usage,
            is_mock=is_mock,
            cost_usd=_parse_cost(data.get("cost")),
            raw_response=data,
        )

    def _simulate_system_one(
        self, state: str, questions: Dict[str, QuestionType], model: str
    ) -> JevResponse:
        """
        Intelligent local simulation engine for testing, CI and dry-runs without API keys.
        Uses deterministic heuristic pattern-matching to provide realistic, valid answers.
        """
        answers: Dict[str, AnswerType] = {}
        structured_state: Optional[Dict[str, Any]] = state if isinstance(state, dict) else None
        state = render_state_text(state)
        state_lower = state.lower()
        state_tokens = set(re.findall(r"\w+", state_lower))

        # Concrete assertion signals, split from bare exception names so that a concrete
        # dependency/transient root cause is never masked by a generic "RuntimeError:" line.
        real_assertion = any(
            re.search(
                r"(?:assertionerror|assertionfailed|assertionfailederror|assert\b|assert_eq!|assertthat|expect\(.*?\)\.to|expected:.*received:|failures?:|fail(?:ed)?\s+test|^fail(?:ed)?(?!\s+to\b)\b|falha de asserção|fallo de aserción|opentest4j)",
                line.strip(),
            )
            for line in state_lower.splitlines()
        ) or bool(
            # Cross-line Expectation/Reality pairs (rules/04 precedence) remain explicit assertions.
            re.search(r"expected:[\s\S]{0,300}?received:", state_lower)
        )
        bare_exception = any(
            re.search(
                r"^(?:valueerror|runtimeerror|typeerror|keyerror|indexerror|zerodivisionerror|attributeerror|overflowerror|arithmeticerror|illegalargumentexception|illegalstateexception):",
                line.strip(),
            )
            for line in state_lower.splitlines()
        )
        has_explicit_failure = bool(re.search(
            r"(?:assertionerror|assertionfailed|assertionfailederror|failures?:\s*[1-9]|failed\b|falhou\b|\d+\s+failed\b|not\s+ok\b|segmentation\s+fault|sigsegv|panic\b|core\s+dumped)",
            state_lower
        ))
        has_heavy_keywords = any(k in state_lower for k in [
            "kernel", "distributed", "architecture", "refactor", "concurrency", "deadlock", "multi-file", "consensus", "supervision tree",
            "arquitetura", "distribuído", "distribuída", "distribuido", "refatorar", "refatoração", "concorrência", "concorrencia", "consenso", "múltiplos arquivos", "condição de corrida",
            "arquitectura", "concurrencia", "condición de carrera", "múltiples archivos"
        ])
        has_deadlock_or_loop = any(k in state_lower for k in [
            "infinite loop", "loop infinito", "bucle infinito", "deadlock", "deadlock!", "bloqueo mutuo", "goroutines are asleep", "mutex", "thread hung"
        ])
        env_missing_triggers = [
            "modulenotfounderror", "no module named", "importerror",
            "cannot find module", "err_module_not_found", "ts2307", "cannot find crate",
            "can't find crate", "e0463",
            "cannot find package", "no required module provides package",
            "classnotfoundexception", "noclassdeffounderror", "package does not exist",
            "no such file or directory", "command not found", "module not found", "package not found", "crate not found",
            "cs0246", "type or namespace name", "cannot load such file", "loaderror",
            "módulo não encontrado", "modulo nao encontrado", "nenhum módulo chamado", "pacote não encontrado",
            "módulo no encontrado", "modulo no encontrado", "no se encontró el módulo", "paquete no encontrado"
        ]
        flaky_triggers = [
            "connectionreset", "timeout", "timed out", "econnreset", "econnrefused",
            "etimedout", "socket hang up", "gateway timeout", "503 service unavailable",
            "already in use", "address already in use", "eaddrinuse", "port already in use", "port is already in use",
            "tempo limite", "tempo limite esgotado", "conexão recusada", "conexao recusada",
            "tiempo de espera agotado", "conexión rechazada", "conexion rechazada",
            "porta já está em uso", "puerto ya está en uso"
        ]

        # Precedence rule (.agents/rules/04_testing_and_truthfulness.md): an explicit
        # assertion/expectation mismatch always outranks dependency or transient words in the
        # same log. A bare exception name is logic evidence only when the log does not also
        # contain a concrete env/flaky root cause, so deterministic fixes are never escalated.
        has_env_signal = any(k in state_lower for k in env_missing_triggers)
        has_flaky_signal = any(k in state_lower for k in flaky_triggers)
        is_explicit_assertion = real_assertion or (
            bare_exception and not (has_env_signal or has_flaky_signal)
        )
        syntax_triggers = [
            "syntaxerror", "indentationerror", "expected ';'", "ts1005", "missing bracket",
            "erro de sintaxe", "sintaxe inválida", "indentação inesperada",
            "error de sintaxis", "sintaxis inválida"
        ]
        deep_logic_triggers = [
            "assertionerror", "assertionfailed", "assertionfailederror", "assert ", "panicked at", "panic:", "panic",
            "deadlock", "goroutines are asleep", "infinite loop", "loop infinito", "bucle infinito", "bloqueo mutuo",
            "mutex", "segmentation fault", "sigsegv", "addresssanitizer", "core dumped",
            "nullpointerexception", "nullreferenceexception", "arrayindexoutofboundsexception",
            "nil pointer dereference", "index out of bounds",
            "falha de asserção", "asserção", "erro de lógica", "fallo de aserción", "error de lógica", "expect("
        ]
        single_word_mech = {
            "git", "diff", "typo", "flake8", "eslint", "prettier", "linter",
            "echo", "pwd", "format", "black", "lint", "cat", "ls"
        }
        multi_word_mech = [
            "git status", "git diff", "git log", "view file", "read file", "cat file",
            "check status", "run linter", "fix typo", "ler arquivo", "verificar arquivo",
            "formatar código", "leer archivo", "corregir errata", "listar arquivos",
            "listar diretório"
        ]
        has_mech_trigger = bool(
            state_tokens.intersection(single_word_mech)
            or any(p in state_lower for p in multi_word_mech)
        )

        for qid, q in questions.items():
            if isinstance(q, ChoiceQuestion):
                if "deep_logic" in q.criteria:
                    best_choice = "deep_logic"

                elif "lightweight_system2" in q.criteria:
                    best_choice = "lightweight_system2"
                elif "proceed" in q.criteria:
                    best_choice = "proceed"
                    # The abort gate's action must agree with this engine's own dead-end signal:
                    # token overlap picking "abort_and_ask" beside a low dead-end probability made
                    # the gate contradict its own evidence. An undecidable case keeps "proceed" and
                    # the generic scoring below decides.
                    if _mock_is_abort_action(q, structured_state, state_lower):
                        derived_abort = _mock_abort_action_choice(q, structured_state, state_lower)
                        if derived_abort:
                            best_choice = derived_abort
                else:
                    best_choice = list(q.criteria.keys())[0]
                derived_choice = ""
                if _mock_is_abort_action(q, structured_state, state_lower):
                    derived_choice = _mock_abort_action_choice(q, structured_state, state_lower)
                best_score = 0
                for opt in sorted(q.criteria):
                    desc = q.criteria[opt]
                    opt_tokens = set(re.findall(r"\w+", f"{opt} {desc}".lower()))
                    common = opt_tokens.intersection(state_tokens)
                    match_score = len(common)
                    if opt in state_lower:
                        match_score += 3
                    has_deadlock_or_loop = any(k in state_lower for k in [
                        "infinite loop", "loop infinito", "bucle infinito", "deadlock", "deadlock!", "bloqueo mutuo", "goroutines are asleep", "mutex", "thread hung"
                    ])
                    if opt == "deep_logic":
                        if any(k in state_lower for k in deep_logic_triggers):
                            match_score += 8
                        if is_explicit_assertion or has_deadlock_or_loop:
                            match_score += 18
                    elif opt == "env_missing" and any(k in state_lower for k in env_missing_triggers):
                        if not is_explicit_assertion:
                            match_score += 7
                    elif opt == "flaky_transient" and not has_deadlock_or_loop and any(k in state_lower for k in flaky_triggers):
                        if not is_explicit_assertion:
                            match_score += 7
                    elif opt == "syntax_trivial" and any(k in state_lower for k in syntax_triggers):
                        match_score += 6
                    elif opt == "deterministic" and (has_mech_trigger or any(k in state_tokens for k in ["bash", "regex", "script"])):
                        match_score += 2 if has_heavy_keywords else 7
                    elif opt == "heavy_system2" and has_heavy_keywords:
                        match_score += 15

                    if derived_choice:
                        continue  # the action is derived from the dead-end signal, not overlap
                    if match_score > best_score:
                        best_score = match_score
                        best_choice = opt

                probs = _mock_distribution(
                    list(q.criteria),
                    best_choice,
                    MOCK_CHOICE_BEST_CONFLICT
                    if _mock_has_signal_conflict(
                        is_explicit_assertion, has_deadlock_or_loop, has_env_signal, has_flaky_signal
                    )
                    else MOCK_CHOICE_BEST_PEAKED,
                )
                is_effort_q = (
                    qid == "effort"
                    or any(eff in q.criteria for eff in ("none", "minimal", "low", "medium", "high", "xhigh", "max", "ultra"))
                )
                if is_effort_q:
                    # Specialized reasoning effort modulation question (supports 3-level and 8-level Astra-Ares scales)
                    if has_heavy_keywords or any(k in state_lower for k in [
                        "deadlock", "race condition", "distributed", "concurrency", "kernel", "supervision",
                        "architectural", "complex", "algorithmic", "deadlocks", "concorrência", "arquitetura",
                        "condição de corrida", "arquitectura", "concurrencia"
                    ]):
                        if "ultra" in q.criteria and "beyond max" in state_lower:
                            best_choice = "ultra"
                        elif "max" in q.criteria and ("first principles" in state_lower or "proof" in state_lower):
                            best_choice = "max"
                        elif "xhigh" in q.criteria and ("first principles" in state_lower or "subsystems" in state_lower):
                            best_choice = "xhigh"
                        elif "high" in q.criteria:
                            best_choice = "high"
                        elif "xhigh" in q.criteria:
                            best_choice = "xhigh"
                        elif "max" in q.criteria:
                            best_choice = "max"
                        elif "medium" in q.criteria:
                            best_choice = "medium"
                        else:
                            best_choice = list(q.criteria.keys())[-1]
                    elif has_mech_trigger and not has_heavy_keywords:
                        if "none" in q.criteria and any(m in state_lower for m in ["git status", "pwd", "echo", "version"]):
                            best_choice = "none"
                        elif "minimal" in q.criteria and any(m in state_lower for m in ["git status", "pwd", "echo", "version"]):
                            best_choice = "minimal"
                        elif "low" in q.criteria:
                            best_choice = "low"
                        elif "minimal" in q.criteria:
                            best_choice = "minimal"
                        elif "none" in q.criteria:
                            best_choice = "none"
                        elif "medium" in q.criteria:
                            best_choice = "medium"
                        else:
                            best_choice = list(q.criteria.keys())[0]
                    else:
                        if "medium" in q.criteria:
                            best_choice = "medium"
                        elif "high" in q.criteria:
                            best_choice = "high"
                        elif "low" in q.criteria:
                            best_choice = "low"
                        else:
                            best_choice = list(q.criteria.keys())[0]
                    probs = {k: (0.90 if k == best_choice else 0.10 / max(1, len(q.criteria) - 1)) for k in q.criteria}
                elif qid == "lease" or ("1" in q.criteria and any(x in q.criteria for x in ("2", "5", "10"))):
                    # Astra-Ares multi-generation lease question ("1" | "2" | "5" | "10")
                    if any(k in state_lower for k in ["error", "fail", "erro", "falha", "deadlock", "panic", "exception"]):
                        best_choice = "1"
                    elif has_mech_trigger and not has_heavy_keywords:
                        if "5" in q.criteria:
                            best_choice = "5"
                        elif "2" in q.criteria:
                            best_choice = "2"
                        else:
                            best_choice = "1"
                    else:
                        if "2" in q.criteria:
                            best_choice = "2"
                        elif "5" in q.criteria:
                            best_choice = "5"
                        else:
                            best_choice = "1"
                    if best_choice not in q.criteria:
                        best_choice = list(q.criteria.keys())[0]
                    probs = _mock_distribution(
                        list(q.criteria),
                        best_choice,
                        MOCK_CHOICE_BEST_CONFLICT
                        if _mock_has_signal_conflict(
                            is_explicit_assertion, has_deadlock_or_loop, has_env_signal, has_flaky_signal
                        )
                        else MOCK_CHOICE_BEST_PEAKED,
                    )

                elif qid == "workflow_phase" or ("execute" in q.criteria and "complete" in q.criteria):
                    # Canonical phase contract (parity with TypeScript/Rust): same lists, same
                    # precedence, so the three runtimes classify a transcript identically.
                    is_waiting_user = "?" in state_lower or any(k in state_lower for k in ["waiting for your", "waiting on user", "wait for my go-ahead", "please confirm", "which option", "do you approve", "would you like me to", "do you want me to", "need your api key", "aguardando sua aprovação", "aguardando usuário", "qual opção você prefere", "qual opção", "preciso que você confirme", "preciso de permissão", "need clarification", "please clarify", "need permission"])
                    is_unverified = any(k in state_lower for k in ["without running tests", "tests not run", "unverified", "haven't run pytest", "todo: run tests", "falta rodar os testes", "sem testar", "need to verify", "to verify", "run pytest", "run cargo test", "run npm test", "need to run", "updated file", "edited file", "finished editing", "modified file", "wrote code", "atualizei o arquivo", "alterei o arquivo", "terminei de editar", "arquivo alterado"])
                    is_unfinished = any(k in state_lower for k in ["next i'll", "next i will", "now i will", "continuarei", "a seguir vou", "próximo passo farei", "1 of 5", "2 of 5", "3 of 5", "4 of 5", "step 1 of", "step 1 done", "unfinished", "remaining", "todo:", "pendente", "partial", "parcial", "in progress", "falta implementar", "falta rodar os testes", "sem testar", "without running tests", "tests not run", "haven't run pytest", "need to run", "need to verify", "to verify", "unverified", "run pytest", "run cargo test", "run npm test", "updated file", "edited file", "finished editing", "modified file", "wrote code", "atualizei o arquivo", "alterei o arquivo", "terminei de editar", "arquivo alterado", "next step"])
                    is_done = any(k in state_lower for k in ["all done", "100% passing", "all criteria satisfied", "tudo concluído", "todas as etapas concluídas", "task complete", "konnichiwa! all done", "all tests passed", "tests passed (0 failed)", "completed and verified", "completed all", "concluído com sucesso", "todos os testes passaram"])
                    if is_waiting_user and "ask" in q.criteria:
                        best_choice = "ask"
                    elif is_done and "complete" in q.criteria:
                        best_choice = "complete"
                    elif is_unverified and "verify" in q.criteria:
                        best_choice = "verify"
                    elif is_unfinished and "execute" in q.criteria:
                        best_choice = "execute"
                        best_choice = "execute"
                    probs = _mock_distribution(
                        list(q.criteria),
                        best_choice,
                        MOCK_CHOICE_BEST_CONFLICT
                        if _mock_has_signal_conflict(
                            is_explicit_assertion, has_deadlock_or_loop, has_env_signal, has_flaky_signal
                        )
                        else MOCK_CHOICE_BEST_PEAKED,
                    )

                answers[qid] = ChoiceAnswer(choice=best_choice, confidence=0.88, probabilities=probs)

            elif isinstance(q, ScoreQuestion):
                n_levels = len(q.criteria)
                matched_idx = 3 if qid == "viability" else 2
                has_deadlock_or_loop = any(k in state_lower for k in [
                    "infinite loop", "loop infinito", "bucle infinito", "deadlock", "deadlock!", "bloqueo mutuo", "goroutines are asleep", "mutex"
                ])

                if has_explicit_failure and qid in ["satisfaction", "rigor"]:
                    matched_idx = 1
                elif qid == "viability" and (any(w in state_lower for w in ["deadlock", "circular", "impossible", "impossivel", "imposible", "doomed", "inviavel", "inviable"]) or has_deadlock_or_loop):
                    matched_idx = 1
                elif not has_explicit_failure and any(w in state_lower for w in ["satisfy", "satisfaz", "satisface", "atende", "passed", "passou", "pasó", "pass", "sucesso", "éxito", "success", "excellent", "exhaustively", "complete", "concluido", "completado", "proceed"]) and not any(neg in state_lower for neg in ["not ok", "failed", "falhou"]):
                    matched_idx = n_levels
                elif qid != "viability" and any(w in state_lower for w in ["trivial", "minor", "pequeno", "menor"]) and not has_heavy_keywords:
                    matched_idx = 1
                elif qid != "viability" and (has_heavy_keywords or any(w in state_lower for w in ["critical", "critico", "crítico", "fatal", "disaster", "destrutivo", "complex", "complexo", "complejo"])):
                    matched_idx = n_levels

                for idx, level_label in enumerate(q.criteria, start=1):
                    lvl_tokens = set(re.findall(r"\w+", level_label.lower()))
                    if lvl_tokens.intersection(state_tokens) and not (has_explicit_failure and idx > 1 and qid in ["satisfaction", "rigor"]):
                        matched_idx = idx

                score_val = float(matched_idx)
                probs = _mock_distribution(
                    [str(i) for i in range(1, n_levels + 1)], str(matched_idx), MOCK_SCORE_BEST_PEAKED
                )
                answers[qid] = ScoreAnswer(score=score_val, confidence=0.85, probabilities=probs, legend=q.criteria)

            elif isinstance(q, NoulQuestion):
                inst = q.instructions.lower()
                prob = 0.15
                negative_signals = ["abort", "abortar", "fail", "falha", "fallo", "error", "erro", "impossible", "impossivel", "imposible", "fatal", "circular", "deadlock", "dead end", "broken", "quebrado", "unviable", "inviavel", "inviable", "deletar", "apagar", "destrutivo"]
                positive_signals = ["pass", "passed", "passou", "pasó", "success", "sucesso", "éxito", "resolved", "resolvido", "resuelto", "good", "bom", "valid", "valido", "válido", "satisfy", "satisfaz", "satisface", "atende", "all criteria", "todos os criterios", "concluido", "completado", "complete", "proceed", "linear"]

                negation_pattern = r"\b(?:not|do\s+not|don't|não|nao|no|never|sem|evitar|avoid)\s+(?:\w+\s+){0,3}(?:abort|abortar|stop|parar|detener|falhar|fail|deadlock|circular|dead\s*end)"
                is_negated_abort = bool(re.search(negation_pattern, state_lower))

                # Prefer the structured field (E0.4); fall back to the legacy textual split.
                proposed_part = ""
                if structured_state is not None:
                    field_value = structured_state.get("proposed_step")
                    if isinstance(field_value, str):
                        proposed_part = field_value.lower()
                if not proposed_part:
                    proposed_part = state_lower
                    for marker in ("proposed next step:", "proposed_next_step:"):
                        if marker in proposed_part:
                            proposed_part = proposed_part.split(marker)[-1]
                is_forward_progress = any(w in proposed_part for w in [
                    "implement", "fix", "resolve", "correct", "update", "create", "write", "corrigir", "implementar", "executar", "validar", "corregir"
                ])
                is_repetitive_loop = any(w in proposed_part for w in ["same", "repetir", "tentar novamente", "intentar de nuevo", "4a vez", "again", "identical"])
                is_fatal_deadlock = any(k in state_lower for k in ["impossible", "impossivel", "imposible", "circular", "deadlock", "dead end", "inviavel", "inviable", "hopeless", "fatal"])

                if qid == "nudge" or "gentle nudge" in inst or "advance useful work" in inst:
                    is_waiting_user = "?" in state_lower or any(k in state_lower for k in [
                        "waiting for your", "waiting on user", "wait for my go-ahead", "please confirm", "which option",
                        "do you approve", "would you like me to", "do you want me to", "need your api key", "aguardando sua aprovação",
                        "qual opção você prefere", "preciso que você confirme", "need clarification", "need permission"
                    ])
                    is_done = any(k in state_lower for k in [
                        "all done", "100% passing", "all criteria satisfied", "tudo concluído",
                        "todas as etapas concluídas", "task complete", "konnichiwa! all done",
                        "all tests passed", "tests passed (0 failed)", "completed and verified"
                    ])
                    is_unfinished = any(k in state_lower for k in [
                        "next i'll", "next i will", "1 of 5", "2 of 5", "3 of 5", "4 of 5",
                        "step 1 done", "unfinished", "a seguir vou", "próximo passo farei",
                        "falta implementar", "todo:", "remaining", "continuarei", "now i will",
                        "partial", "parcial", "without running tests", "tests not run", "unverified",
                        "haven't run pytest", "todo: run tests", "falta rodar os testes", "sem testar",
                        "need to verify", "to verify", "run pytest", "run cargo test", "run npm test",
                        "need to run", "next step",
                        "updated file", "edited file", "finished editing", "modified file", "wrote code",
                        "atualizei o arquivo", "alterei o arquivo", "terminei de editar", "arquivo alterado"
                    ])
                    if is_waiting_user or is_done:
                        prob = 0.06
                    elif is_unfinished:
                        prob = 0.82
                    else:
                        prob = 0.20
                elif qid == "waiting" or "waiting on the user" in inst:
                    is_waiting_user = "?" in state_lower or any(k in state_lower for k in [
                        "waiting for your", "waiting on user", "wait for my go-ahead", "please confirm", "which option",
                        "do you approve", "would you like me to", "do you want me to", "need your api key", "aguardando sua aprovação",
                        "qual opção você prefere", "preciso que você confirme", "need clarification", "need permission"
                    ])
                    prob = 0.88 if is_waiting_user else 0.08
                elif qid == "progress" or "last nudge produce" in inst:
                    no_prog = any(k in state_lower for k in [
                        "0 tool calls", "no progress", "sem progresso", "nothing done",
                        "tool_calls_after: 0", "toolcallsafter: 0", "identical reply"
                    ])
                    prob = 0.12 if no_prog else 0.85
                elif has_explicit_failure and any(w in inst for w in ["pass", "valid", "satisfy", "complete", "verif"]):
                    prob = 0.05
                elif is_negated_abort and any(w in inst for w in ["abort", "dead", "unviable", "destructive"]):
                    prob = 0.08
                elif (is_fatal_deadlock or has_deadlock_or_loop) and any(w in inst for w in ["abort", "dead", "fail", "urgent", "invalid", "unviable", "destructive", "dead end"]):
                    prob = 0.88
                elif any(w in inst for w in ["abort", "dead", "fail", "urgent", "invalid", "unviable", "destructive", "dead end"]):
                    if is_repetitive_loop:
                        prob = 0.88
                    elif is_forward_progress:
                        prob = 0.12
                    elif any(w in state_lower for w in negative_signals):
                        prob = 0.85
                    else:
                        prob = 0.15
                if qid not in ("nudge", "waiting", "progress") and not has_explicit_failure and any(w in state_lower for w in positive_signals) and not any(neg in state_lower for neg in ["not ok", "failed", "falhou"]):
                    if any(w in inst for w in ["pass", "valid", "satisfy", "complete", "verif"]):
                        prob = 0.92
                    elif any(w in inst for w in ["abort", "dead", "unviable"]):
                        prob = 0.08
                has_deadlock_or_loop = any(k in state_lower for k in [
                    "infinite loop", "loop infinito", "bucle infinito", "deadlock", "deadlock!", "bloqueo mutuo", "goroutines are asleep", "mutex"
                ])
                if (is_explicit_assertion or has_deadlock_or_loop) and ("deterministically" in inst or "skip" in inst):
                    prob = 0.05
                elif any(w in state_lower for w in env_missing_triggers + flaky_triggers + ["pip install", "npm install", "cargo add"]) and not (is_explicit_assertion or has_deadlock_or_loop):
                    if "deterministically" in inst or "skip" in inst:
                        prob = 0.95
                answers[qid] = NoulAnswer(noul=prob)

        input_toks = max(10, len(state) // 4)
        return JevResponse(
            model=f"{model}-simulation",
            answers=answers,
            usage={"input_tokens": input_toks, "output_tokens": 0},
            is_mock=True,
            raw_response={"simulated": True},
        )
