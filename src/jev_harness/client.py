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
import socket
from typing import Any, Dict, List, Optional, Union
import urllib.error
import urllib.request

TYPESAFE_API_URL = "https://api.typesafe.ai/v1/systemone"
OPENCODE_API_URL = "https://opencode.ai/zen/v1/systemone"
OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"
DEFAULT_MODEL = "jev-latest"
DEFAULT_USER_AGENT = "Mozilla/5.0 (compatible; JevHarness/0.1.6; +https://github.com/ismaelsoilet/jev-harness)"


def _urlopen_with_ipv4_fallback(req: urllib.request.Request, timeout: float):
    """Attempts normal urlopen, falling back to IPv4 socket resolution if IPv6 network is unreachable."""
    try:
        return urllib.request.urlopen(req, timeout=timeout)
    except urllib.error.URLError as e:
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
            self.model = "google/gemini-2.5-flash"
        else:
            self.model = DEFAULT_MODEL

    @staticmethod
    def _resolve_credentials() -> tuple[Optional[str], str]:
        """Resolves API key and provider using hierarchical cascade."""
        # 1. Environment variables
        if os.getenv("JEV_PROVIDER") == "opencode":
            return os.getenv("OPENCODE_API_KEY"), "opencode"
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
            "User-Agent": DEFAULT_USER_AGENT,
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        req_data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(self.base_url, data=req_data, headers=headers, method="POST")

        try:
            with _urlopen_with_ipv4_fallback(req, timeout=self.timeout) as resp:
                resp_data = json.loads(resp.read().decode("utf-8"))
                return self._parse_response(resp_data, chosen_model, is_mock=False)
        except urllib.error.HTTPError as e:
            try:
                err_body = e.read().decode("utf-8", errors="replace") if getattr(e, "fp", None) is not None else str(e)
            except Exception:
                err_body = str(e)
            provider_label = "OpenCode Zen" if self.provider == "opencode" else "TypeSafe"
            raise RuntimeError(f"{provider_label} API returned HTTP {e.code}: {err_body}") from e
        except (urllib.error.URLError, TimeoutError) as e:
            provider_label = "OpenCode Zen" if self.provider == "opencode" else "TypeSafe"
            reason = e.reason if hasattr(e, "reason") else e
            raise RuntimeError(f"Failed to connect to {provider_label} API ({self.base_url}): {reason}") from e

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
        try:
            with _urlopen_with_ipv4_fallback(req, timeout=self.timeout) as resp:
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
            re.search(
                r"(?:assertionerror|assert\b|expect\(.*?\)\.to|assert_eq!|failures?:|expected:.*received:|^fail\s+|^failed\s+test)",
                line.strip(),
            )
            for line in state_lower.splitlines()
        )
        has_heavy_keywords = any(k in state_lower for k in [
            "kernel", "distributed", "architecture", "refactor", "concurrency", "deadlock", "multi-file", "consensus", "supervision tree"
        ])

        for qid, q in questions.items():
            if isinstance(q, ChoiceQuestion):
                if "deep_logic" in q.criteria:
                    best_choice = "deep_logic"
                elif "lightweight_system2" in q.criteria:
                    best_choice = "lightweight_system2"
                elif "proceed" in q.criteria:
                    best_choice = "proceed"
                else:
                    best_choice = list(q.criteria.keys())[0]
                best_score = 0
                for opt, desc in q.criteria.items():
                    opt_tokens = set(re.findall(r"\w+", f"{opt} {desc}".lower()))
                    common = opt_tokens.intersection(state_tokens)
                    match_score = len(common)
                    if opt in state_lower:
                        match_score += 3
                    has_deadlock_or_loop = any(k in state_lower for k in [
                        "infinite loop", "loop infinito", "deadlock", "deadlock!", "goroutines are asleep", "mutex", "thread hung"
                    ])
                    if opt == "deep_logic":
                        if any(k in state_lower for k in [
                            "assertionerror", "assert ", "panicked at", "panic:", "panic",
                            "deadlock", "goroutines are asleep", "infinite loop", "loop infinito", "mutex", "segmentation fault",
                            "nullpointerexception", "nil pointer dereference", "index out of bounds",
                            "falha de asserção", "asserção", "erro de lógica", "expect("
                        ]):
                            match_score += 8
                        if is_explicit_assertion or has_deadlock_or_loop:
                            match_score += 18
                    elif opt == "env_missing" and any(k in state_lower for k in [
                        "modulenotfounderror", "no module named", "not found", "importerror",
                        "cannot find module", "err_module_not_found", "ts2307", "cannot find crate",
                        "can't find crate", "find crate", "e0463",
                        "cannot find package", "no required module provides package",
                        "módulo não encontrado", "nenhum módulo chamado", "pacote não encontrado"
                    ]):
                        if not is_explicit_assertion:
                            match_score += 7
                    elif opt == "flaky_transient" and not has_deadlock_or_loop and any(k in state_lower for k in [
                        "connectionreset", "timeout", "timed out", "econnreset", "econnrefused",
                        "etimedout", "socket hang up", "gateway timeout", "503 service unavailable",
                        "tempo limite", "tempo limite esgotado", "conexão recusada"
                    ]):
                        if not is_explicit_assertion:
                            match_score += 7
                    elif opt == "syntax_trivial" and any(k in state_lower for k in [
                        "syntaxerror", "indentationerror", "expected ';'", "ts1005", "missing bracket",
                        "erro de sintaxe", "sintaxe inválida", "indentação inesperada"
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
                if "low" in q.criteria and "high" in q.criteria:
                    # Specialized reasoning effort modulation question
                    if has_heavy_keywords or any(k in state_lower for k in [
                        "deadlock", "race condition", "distributed", "concurrency", "kernel", "supervision",
                        "architectural", "complex", "algorithmic", "deadlocks", "concorrência", "arquitetura"
                    ]):
                        best_choice = "high"
                    elif any(k in state_lower for k in [
                        "git", "status", "diff", "ls", "cat", "view", "read", "typo", "format", "black",
                        "lint", "flake8", "eslint", "prettier", "import", "version", "trivial", "linter", "echo"
                    ]) and not has_heavy_keywords:
                        best_choice = "low"
                    else:
                        best_choice = "medium"
                    probs = {k: (0.90 if k == best_choice else 0.10 / max(1, len(q.criteria) - 1)) for k in q.criteria}

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

                proposed_part = state_lower.split("proposed next step:")[-1] if "proposed next step:" in state_lower else state_lower
                is_forward_progress = any(w in proposed_part for w in [
                    "implement", "fix", "resolve", "correct", "update", "create", "write", "corrigir", "implementar", "executar", "validar"
                ])
                is_repetitive_loop = any(w in proposed_part for w in ["same", "repetir", "tentar novamente", "4a vez", "again", "identical"])
                is_fatal_deadlock = any(k in state_lower for k in ["impossible", "impossivel", "circular", "deadlock", "dead end", "inviavel", "hopeless", "fatal"])

                if is_negated_abort and any(w in inst for w in ["abort", "dead", "unviable", "destructive"]):
                    prob = 0.08
                elif is_fatal_deadlock and any(w in inst for w in ["abort", "dead", "fail", "urgent", "invalid", "unviable", "destructive", "dead end"]):
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
                if any(w in state_lower for w in positive_signals):
                    if any(w in inst for w in ["pass", "valid", "satisfy", "complete", "verif"]):
                        prob = 0.92
                    elif any(w in inst for w in ["abort", "dead", "unviable"]):
                        prob = 0.08
                has_deadlock_or_loop = any(k in state_lower for k in [
                    "infinite loop", "loop infinito", "deadlock", "deadlock!", "goroutines are asleep", "mutex"
                ])
                if (is_explicit_assertion or has_deadlock_or_loop) and ("deterministically" in inst or "skip" in inst):
                    prob = 0.05
                elif any(w in state_lower for w in ["modulenotfounderror", "no module named", "pip install", "npm install"]) and not (is_explicit_assertion or has_deadlock_or_loop):
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
