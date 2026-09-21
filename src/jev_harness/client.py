"""
Jev System One HTTP Client.
Connects to TypeSafe AI's System One API (POST https://api.typesafe.ai/v1/systemone)
with zero external dependencies (pure Python standard library) and fallback simulation mode.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import json
import os
from pathlib import Path
import re
from typing import Any, Dict, List, Optional, Union
import urllib.error
import urllib.request

TYPESAFE_API_URL = "https://api.typesafe.ai/v1/systemone"
OPENCODE_API_URL = "https://opencode.ai/zen/v1/systemone"
OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"
DEFAULT_MODEL = "jev-latest"


@dataclass
class ChoiceQuestion:
    """
    Choice Question: evaluates state and selects exactly one option from criteria map.
    Returns chosen key, confidence (0-1), and probability distribution across all choices.
    """
    instructions: str
    criteria: Dict[str, str]

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
    legend: List[str] = field(default_factory=list)


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
    ):
        self.timeout = timeout
        self.force_mock = force_mock
        resolved_key, resolved_provider = self._resolve_credentials()
        self.provider = provider or resolved_provider
        self.api_key = api_key or resolved_key

        # Configure URL and model based on provider
        if base_url:
            self.base_url = base_url
        elif self.provider == "opencode":
            self.base_url = OPENCODE_API_URL
        elif self.provider == "openrouter":
            self.base_url = OPENROUTER_API_URL
        else:
            self.base_url = TYPESAFE_API_URL

        if model:
            self.model = model
        elif self.provider == "opencode":
            self.model = "jev-1.13-free"
        elif self.provider == "openrouter":
            self.model = "google/gemini-flash-1.5"
        else:
            self.model = DEFAULT_MODEL

    @staticmethod
    def _resolve_credentials() -> tuple[Optional[str], str]:
        """Resolves API key and provider using hierarchical cascade."""
        # 1. Environment variables
        if os.getenv("TYPESAFE_API_KEY"):
            return os.getenv("TYPESAFE_API_KEY"), "typesafe"
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
                        if data.get("api_key"):
                            return data["api_key"], provider
                    except Exception:
                        pass

                dotenv_file = candidate / ".env"
                if dotenv_file.exists():
                    try:
                        content = dotenv_file.read_text(encoding="utf-8")
                        for line in content.splitlines():
                            line = line.strip()
                            if line.startswith("TYPESAFE_API_KEY="):
                                return line.split("=", 1)[1].strip(" '\""), "typesafe"
                            if line.startswith("OPENCODE_API_KEY="):
                                return line.split("=", 1)[1].strip(" '\""), "opencode"
                            if line.startswith("OPENROUTER_API_KEY="):
                                return line.split("=", 1)[1].strip(" '\""), "openrouter"
                    except Exception:
                        pass
        except Exception:
            pass

        # 3. Global user config (~/.config/jev/credentials.env)
        try:
            global_creds = Path.home() / ".config" / "jev" / "credentials.env"
            if global_creds.exists():
                content = global_creds.read_text(encoding="utf-8")
                for line in content.splitlines():
                    line = line.strip()
                    if line.startswith("TYPESAFE_API_KEY="):
                        return line.split("=", 1)[1].strip(" '\""), "typesafe"
                    if line.startswith("OPENCODE_API_KEY="):
                        return line.split("=", 1)[1].strip(" '\""), "opencode"
                    if line.startswith("OPENROUTER_API_KEY="):
                        return line.split("=", 1)[1].strip(" '\""), "openrouter"
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
    ) -> JevResponse:
        """
        Sends a single batch request to Jev System One API.
        All questions are evaluated in parallel in one pass against state.
        """
        if not questions:
            raise ValueError("Questions dictionary cannot be empty.")

        state_str = json.dumps(state) if isinstance(state, (dict, list)) else str(state)
        chosen_model = model or self.model

        # Fallback to simulation/mock if no key is configured or forced mock
        if not self.is_live:
            return self._simulate_system_one(state_str, questions, chosen_model)

        if self.provider == "openrouter":
            return self._call_openrouter(state_str, questions, chosen_model)

        payload = {
            "model": chosen_model,
            "state": state_str,
            "questions": {qid: q.to_dict() for qid, q in questions.items()},
        }

        headers = {
            "Content-Type": "application/json",
            "User-Agent": "JevHarness/0.1.0",
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        req_data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(self.base_url, data=req_data, headers=headers, method="POST")

        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                resp_data = json.loads(resp.read().decode("utf-8"))
                return self._parse_response(resp_data, chosen_model, is_mock=False)
        except urllib.error.HTTPError as e:
            if self.provider == "opencode":
                return self._simulate_system_one(state_str, questions, chosen_model)
            err_body = e.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"TypeSafe API returned HTTP {e.code}: {err_body}") from e
        except (urllib.error.URLError, TimeoutError) as e:
            if self.provider == "opencode":
                return self._simulate_system_one(state_str, questions, chosen_model)
            raise RuntimeError(f"Failed to connect to TypeSafe API ({self.base_url}): {e.reason if hasattr(e, 'reason') else e}") from e

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
            "Authorization": f"Bearer {self.api_key}",
            "HTTP-Referer": "https://github.com/ismaelsoilet/jev-harness",
            "X-Title": "Jev Harness",
        }
        req_data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(self.base_url, data=req_data, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                content = data["choices"][0]["message"]["content"]
                parsed_json = json.loads(content)
                return self._parse_response(parsed_json, model, is_mock=False)
        except Exception:
            return self._simulate_system_one(state_str, questions, model)

    def _parse_response(self, data: Dict[str, Any], model: str, is_mock: bool) -> JevResponse:
        parsed_answers: Dict[str, AnswerType] = {}
        raw_answers = data.get("answers", {})

        for qid, ans in raw_answers.items():
            ans_type = ans.get("type")
            if ans_type == "choice":
                parsed_answers[qid] = ChoiceAnswer(
                    choice=ans.get("choice", ""),
                    confidence=float(ans.get("confidence", 1.0)),
                    probabilities=ans.get("probabilities", {}),
                )
            elif ans_type == "score":
                parsed_answers[qid] = ScoreAnswer(
                    score=float(ans.get("score", 0.0)),
                    confidence=float(ans.get("confidence", 1.0)),
                    probabilities=ans.get("probabilities", {}),
                    legend=ans.get("legend", []),
                )
            elif ans_type == "noul":
                parsed_answers[qid] = NoulAnswer(
                    noul=float(ans.get("noul", 0.0)),
                )
            else:
                if "choice" in ans:
                    parsed_answers[qid] = ChoiceAnswer(
                        choice=ans.get("choice", ""),
                        confidence=float(ans.get("confidence", 1.0)),
                        probabilities=ans.get("probabilities", {}),
                    )
                elif "score" in ans:
                    parsed_answers[qid] = ScoreAnswer(
                        score=float(ans.get("score", 0.0)),
                        confidence=float(ans.get("confidence", 1.0)),
                        probabilities=ans.get("probabilities", {}),
                        legend=ans.get("legend", []),
                    )
                elif "noul" in ans:
                    parsed_answers[qid] = NoulAnswer(noul=float(ans.get("noul", 0.0)))

        usage = data.get("usage", {"input_tokens": len(data.get("state", "")) // 4, "output_tokens": 0})
        return JevResponse(
            model=data.get("model", model),
            answers=parsed_answers,
            usage=usage,
            is_mock=is_mock,
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
        state_lower = state.lower()
        state_tokens = set(re.findall(r"\w+", state_lower))

        is_explicit_assertion = any(
            re.match(r"^(?:failed\s+.*assertionerror|e\s+assertionerror|assertionerror:|>\s+assert\s+|assert\s+)", line.strip())
            for line in state_lower.splitlines()
        )
        has_heavy_keywords = any(k in state_lower for k in [
            "kernel", "distributed", "architecture", "refactor", "concurrency", "deadlock", "multi-file", "consensus", "supervision tree"
        ])

        for qid, q in questions.items():
            if isinstance(q, ChoiceQuestion):
                best_choice = list(q.criteria.keys())[0]
                best_score = -1
                for opt, desc in q.criteria.items():
                    opt_tokens = set(re.findall(r"\w+", f"{opt} {desc}".lower()))
                    common = opt_tokens.intersection(state_tokens)
                    match_score = len(common)
                    if opt in state_lower:
                        match_score += 3
                    if opt == "deep_logic":
                        if any(k in state_lower for k in [
                            "assertionerror", "assert ", "panicked at", "panic:", "panic",
                            "deadlock", "goroutines are asleep", "segmentation fault",
                            "nullpointerexception", "nil pointer dereference", "index out of bounds"
                        ]):
                            match_score += 8
                        if is_explicit_assertion:
                            match_score += 6
                    elif opt == "env_missing" and any(k in state_lower for k in [
                        "modulenotfounderror", "no module named", "not found", "importerror",
                        "cannot find module", "err_module_not_found", "ts2307", "cannot find crate",
                        "can't find crate", "find crate", "e0463",
                        "cannot find package", "no required module provides package"
                    ]):
                        # If it's just an AssertionError testing module strings, don't over-boost
                        match_score += 4 if is_explicit_assertion else 7
                    elif opt == "flaky_transient" and any(k in state_lower for k in [
                        "connectionreset", "timeout", "timed out", "econnreset", "econnrefused",
                        "etimedout", "socket hang up", "gateway timeout", "503 service unavailable"
                    ]):
                        match_score += 7
                    elif opt == "syntax_trivial" and any(k in state_lower for k in [
                        "syntaxerror", "indentationerror", "expected ';'", "ts1005", "missing bracket"
                    ]):
                        match_score += 6
                    elif opt == "deterministic" and any(k in state_lower for k in [
                        "typo", "format", "black", "prettier", "eslint", "lint", "bash", "regex", "script", "renomear"
                    ]):
                        # If task is inherently heavy architectural, deterministic cannot override
                        match_score += 2 if has_heavy_keywords else 7
                    elif opt == "heavy_system2" and has_heavy_keywords:
                        match_score += 15

                    if match_score > best_score:
                        best_score = match_score
                        best_choice = opt

                probs = {k: (0.85 if k == best_choice else 0.15 / max(1, len(q.criteria) - 1)) for k in q.criteria}
                answers[qid] = ChoiceAnswer(choice=best_choice, confidence=0.88, probabilities=probs)

            elif isinstance(q, ScoreQuestion):
                n_levels = len(q.criteria)
                matched_idx = 2
                if any(w in state_lower for w in ["satisfy", "satisfaz", "atende", "passed", "passou", "sucesso", "pass", "success", "excellent", "exhaustively", "complete", "concluido"]):
                    matched_idx = n_levels
                elif any(w in state_lower for w in ["trivial", "minor", "pequeno"]) and not has_heavy_keywords:
                    matched_idx = 1
                elif has_heavy_keywords or any(w in state_lower for w in ["critical", "critico", "fatal", "disaster", "destrutivo", "complex"]):
                    matched_idx = n_levels

                for idx, level_label in enumerate(q.criteria, start=1):
                    lvl_tokens = set(re.findall(r"\w+", level_label.lower()))
                    if lvl_tokens.intersection(state_tokens):
                        matched_idx = idx

                score_val = float(matched_idx)
                probs = {str(i): (0.80 if i == matched_idx else 0.20 / max(1, n_levels - 1)) for i in range(1, n_levels + 1)}
                answers[qid] = ScoreAnswer(score=score_val, confidence=0.85, probabilities=probs, legend=q.criteria)

            elif isinstance(q, NoulQuestion):
                inst = q.instructions.lower()
                prob = 0.15
                negative_signals = ["abort", "abortar", "fail", "falha", "error", "erro", "impossible", "impossivel", "fatal", "circular", "deadlock", "dead end", "broken", "quebrado", "unviable", "inviavel", "deletar", "apagar", "destrutivo"]
                positive_signals = ["pass", "passed", "passou", "success", "sucesso", "resolved", "resolvido", "good", "bom", "valid", "valido", "satisfy", "satisfaz", "atende", "all criteria", "todos os criterios", "concluido", "complete", "proceed", "linear"]

                negation_pattern = r"\b(?:not|do\s+not|don't|não|nao|never|sem|evitar|avoid)\s+(?:\w+\s+){0,3}(?:abort|abortar|stop|parar|falhar|fail|deadlock|circular|dead\s*end)"
                is_negated_abort = bool(re.search(negation_pattern, state_lower))

                if is_negated_abort and any(w in inst for w in ["abort", "dead", "unviable", "destructive"]):
                    prob = 0.08
                elif any(w in state_lower for w in negative_signals):
                    if any(w in inst for w in ["abort", "dead", "fail", "urgent", "invalid", "unviable", "destructive", "dead end"]):
                        prob = 0.88
                    else:
                        prob = 0.15
                if any(w in state_lower for w in positive_signals):
                    if any(w in inst for w in ["pass", "valid", "satisfy", "complete", "verif"]):
                        prob = 0.92
                    elif any(w in inst for w in ["abort", "dead", "unviable"]):
                        prob = 0.08
                if any(w in state_lower for w in ["modulenotfounderror", "no module named", "pip install", "npm install"]) and not is_explicit_assertion:
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
