"""
Session & Trajectory Tracker for Jev Harness.
Detects circular doom loops across multi-turn agent runs and tracks token ROI metrics.
Zero external dependencies (pure Python standard library).
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
import contextlib
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile
import threading
import time
from typing import Any, Dict, List, Optional


_IN_PROCESS_LOCK = threading.RLock()


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
    nudge_continuations: int = 0
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


@contextlib.contextmanager
def _session_lock(storage_path: Path):
    """Acquires an in-process thread lock and cross-process file lock."""
    _IN_PROCESS_LOCK.acquire()
    lock_path = storage_path.with_name(f"{storage_path.stem}.lock")
    lock_file = None
    has_msvcrt_lock = False
    try:
        try:
            lock_file = open(lock_path, "a+")
        except Exception:
            pass

        if lock_file is not None:
            try:
                import fcntl
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
            except ImportError:
                try:
                    import msvcrt
                    lock_file.seek(0)
                    msvcrt.locking(lock_file.fileno(), msvcrt.LK_LOCK, 1)
                    has_msvcrt_lock = True
                except Exception:
                    pass
            except Exception:
                pass
        yield
    finally:
        if lock_file is not None:
            try:
                import fcntl
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
            except Exception:
                pass
            if has_msvcrt_lock:
                try:
                    import msvcrt
                    lock_file.seek(0)
                    msvcrt.locking(lock_file.fileno(), msvcrt.LK_UNLCK, 1)
                except Exception:
                    pass
            try:
                lock_file.close()
            except Exception:
                pass
        _IN_PROCESS_LOCK.release()


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
                nudge_continuations=data.get("nudge_continuations", 0),
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
            "nudge_continuations": session.nudge_continuations,
            "estimated_tokens_saved": session.estimated_tokens_saved,
            "estimated_cost_saved_usd": session.estimated_cost_saved_usd,
            "last_updated": time.time(),
        }
        # Atomic file write with thread/pid unique suffix to avoid collisions on Windows/Unix
        temp_file = p.with_name(f"{p.name}.{os.getpid()}_{threading.get_ident()}_{time.time_ns()}.tmp")
        temp_file.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
        temp_file.replace(p)
    except Exception:
        pass


def update_session(modifier_fn) -> SessionState:
    """Safely updates session state with an exclusive file lock across concurrent processes."""
    p = _get_storage_path()
    with _session_lock(p):
        session = load_session()
        modifier_fn(session)
        save_session(session)
        return session


def record_triage_event(skip_llm: bool, category: str) -> None:
    def _mod(session: SessionState) -> None:
        session.total_triage_calls += 1
        if skip_llm:
            session.skipped_llm_calls += 1
            tokens = 26200
            cost = 0.31
            session.estimated_tokens_saved += tokens
            session.estimated_cost_saved_usd += cost
    update_session(_mod)


def record_abort_event(triggered: bool) -> None:
    def _mod(session: SessionState) -> None:
        if triggered:
            session.abort_guards_triggered += 1
            tokens = 80000
            cost = 1.20
            session.estimated_tokens_saved += tokens
            session.estimated_cost_saved_usd += cost
    update_session(_mod)


def record_route_event(selected_tier: str) -> None:
    if selected_tier == "deterministic":
        def _mod(session: SessionState) -> None:
            session.deterministic_routes += 1
            tokens = 5000
            cost = 0.05
            session.estimated_tokens_saved += tokens
            session.estimated_cost_saved_usd += cost
        update_session(_mod)


def record_reasoning_effort_event(effort: str, provider: str = "openai") -> None:
    def _mod(session: SessionState) -> None:
        session.effort_modulations += 1
        if effort == "low":
            # Turning high reasoning to low saves ~7,000 reasoning tokens per turn
            tokens = 7000
            cost = 0.21
            session.estimated_tokens_saved += tokens
            session.estimated_cost_saved_usd += cost
    update_session(_mod)


def record_nudge_event(should_nudge: bool) -> None:
    if should_nudge:
        def _mod(session: SessionState) -> None:
            session.nudge_continuations += 1
        update_session(_mod)


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
    diff_hash = hashlib.sha256(diff_content.encode("utf-8")).hexdigest()[:12] if diff_content else ""
    def _mod(session: SessionState) -> None:
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
    update_session(_mod)


def record_triage_step(skip_llm: bool, category: str, error_snippet: str = "", action: str = "") -> None:
    """Single-pass atomic telemetry and history update for test triage."""
    def _mod(session: SessionState) -> None:
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
    update_session(_mod)


def record_abort_step(should_abort: bool, proposed_step: str, action: str = "") -> None:
    """Single-pass atomic telemetry and history update for abort gate."""
    def _mod(session: SessionState) -> None:
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
    update_session(_mod)


def reset_metrics() -> None:
    session = SessionState()
    save_session(session)
