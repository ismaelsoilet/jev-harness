"""
Session & Trajectory Tracker for Jev Harness.
Detects circular doom loops across multi-turn agent runs and tracks token ROI metrics.
Zero external dependencies (pure Python standard library).
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile
import time
from typing import Any, Dict, List, Optional


@dataclass
class AttemptRecord:
    timestamp: float
    step: str
    error_snippet: str
    diff_hash: str
    action_taken: str


@dataclass
class SessionState:
    history: List[AttemptRecord] = field(default_factory=list)
    total_triage_calls: int = 0
    skipped_llm_calls: int = 0
    abort_guards_triggered: int = 0
    deterministic_routes: int = 0
    effort_modulations: int = 0
    estimated_tokens_saved: int = 0
    estimated_cost_saved_usd: float = 0.0


def _get_storage_path() -> Path:
    """Returns path to storage file, preferring repo .jev or ~/.config/jev."""
    try:
        local_dir = Path.cwd() / ".jev"
        if local_dir.exists() and os.access(local_dir, os.W_OK):
            return local_dir / "session.json"
    except Exception:
        pass

    global_dir = Path.home() / ".config" / "jev"
    try:
        global_dir.mkdir(parents=True, exist_ok=True)
        return global_dir / "session.json"
    except Exception:
        return Path(tempfile.gettempdir()) / "jev_session_default.json"


def load_session() -> SessionState:
    p = _get_storage_path()
    if p.exists():
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
            hist = [
                AttemptRecord(**h) for h in data.get("history", []) if isinstance(h, dict)
            ]
            return SessionState(
                history=hist,
                total_triage_calls=data.get("total_triage_calls", 0),
                skipped_llm_calls=data.get("skipped_llm_calls", 0),
                abort_guards_triggered=data.get("abort_guards_triggered", 0),
                deterministic_routes=data.get("deterministic_routes", 0),
                effort_modulations=data.get("effort_modulations", 0),
                estimated_tokens_saved=data.get("estimated_tokens_saved", 0),
                estimated_cost_saved_usd=data.get("estimated_cost_saved_usd", 0.0),
            )
        except Exception:
            pass
    return SessionState()


def save_session(session: SessionState) -> None:
    p = _get_storage_path()
    try:
        data = {
            "history": [asdict(h) for h in session.history[-10:]],
            "total_triage_calls": session.total_triage_calls,
            "skipped_llm_calls": session.skipped_llm_calls,
            "abort_guards_triggered": session.abort_guards_triggered,
            "deterministic_routes": session.deterministic_routes,
            "effort_modulations": session.effort_modulations,
            "estimated_tokens_saved": session.estimated_tokens_saved,
            "estimated_cost_saved_usd": session.estimated_cost_saved_usd,
            "last_updated": time.time(),
        }
        # Atomic file write to avoid corrupted JSON on dirty process kill
        temp_file = p.with_name(f"{p.name}.{os.getpid()}.tmp")
        temp_file.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
        temp_file.replace(p)
    except Exception:
        pass


def record_triage_event(skip_llm: bool, category: str) -> None:
    session = load_session()
    session.total_triage_calls += 1
    if skip_llm:
        session.skipped_llm_calls += 1
        tokens = 26200
        cost = 0.31
        session.estimated_tokens_saved += tokens
        session.estimated_cost_saved_usd += cost
    save_session(session)


def record_abort_event(triggered: bool) -> None:
    session = load_session()
    if triggered:
        session.abort_guards_triggered += 1
        tokens = 80000
        cost = 1.20
        session.estimated_tokens_saved += tokens
        session.estimated_cost_saved_usd += cost
    save_session(session)


def record_route_event(selected_tier: str) -> None:
    if selected_tier == "deterministic":
        session = load_session()
        session.deterministic_routes += 1
        tokens = 5000
        cost = 0.05
        session.estimated_tokens_saved += tokens
        session.estimated_cost_saved_usd += cost
        save_session(session)


def record_reasoning_effort_event(effort: str, provider: str = "openai") -> None:
    session = load_session()
    session.effort_modulations += 1
    if effort == "low":
        # Turning high reasoning to low saves ~7,000 reasoning tokens per turn
        tokens = 7000
        cost = 0.21
        session.estimated_tokens_saved += tokens
        session.estimated_cost_saved_usd += cost
    save_session(session)


def _normalize_snippet(text: str) -> str:
    """Strips volatile dynamic memory addresses, timestamps, thread IDs, and line numbers."""
    if not text:
        return ""
    t = re.sub(r"0x[0-9a-fA-F]+", "<HEX>", text)
    t = re.sub(r"\b\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}(?:\.\d+)?\b", "<TIME>", t)
    t = re.sub(r"\[Thread-\d+\]|\bthread '[^']+'\b", "<THREAD>", t)
    t = re.sub(r":\d+:\d+|\bline \d+\b", ":<LINE>", t)
    return " ".join(t.strip().split()[:20]).lower()


def detect_repeated_failure(snippet: str, max_repeats: int = 2) -> bool:
    """Returns True if the normalized error snippet or proposed step has appeared 2 or more times recently."""
    if not snippet or len(snippet.strip()) < 10:
        return False
    session = load_session()
    clean_target = _normalize_snippet(snippet)
    if not clean_target:
        return False
    matches = 0
    for h in session.history[-5:]:
        h_err = _normalize_snippet(h.error_snippet)
        h_step = _normalize_snippet(h.step)
        if clean_target and (clean_target in h_err or clean_target in h_step or (len(h_err) > 15 and h_err in clean_target)):
            matches += 1
    return matches >= max_repeats


def record_step_attempt(step: str, error_snippet: str = "", diff_content: str = "", action: str = "") -> None:
    session = load_session()
    diff_hash = hashlib.sha256(diff_content.encode("utf-8")).hexdigest()[:12] if diff_content else ""
    session.history.append(
        AttemptRecord(
            timestamp=time.time(),
            step=step[:300],
            error_snippet=error_snippet[:300],
            diff_hash=diff_hash,
            action_taken=action[:100],
        )
    )
    if len(session.history) > 20:
        session.history = session.history[-20:]
    save_session(session)


def record_triage_step(skip_llm: bool, category: str, error_snippet: str = "", action: str = "") -> None:
    """Single-pass atomic telemetry and history update for test triage."""
    session = load_session()
    session.total_triage_calls += 1
    if skip_llm:
        session.skipped_llm_calls += 1
        session.estimated_tokens_saved += 26200
        session.estimated_cost_saved_usd += 0.31
    session.history.append(
        AttemptRecord(
            timestamp=time.time(),
            step="test-gate",
            error_snippet=error_snippet[:300],
            diff_hash="",
            action_taken=action[:100],
        )
    )
    if len(session.history) > 20:
        session.history = session.history[-20:]
    save_session(session)


def record_abort_step(should_abort: bool, proposed_step: str, action: str = "") -> None:
    """Single-pass atomic telemetry and history update for abort gate."""
    session = load_session()
    if should_abort:
        session.abort_guards_triggered += 1
        session.estimated_tokens_saved += 80000
        session.estimated_cost_saved_usd += 1.20
    session.history.append(
        AttemptRecord(
            timestamp=time.time(),
            step=proposed_step[:300],
            error_snippet="",
            diff_hash="",
            action_taken=action[:100],
        )
    )
    if len(session.history) > 20:
        session.history = session.history[-20:]
    save_session(session)


def reset_metrics() -> None:
    session = SessionState()
    save_session(session)
