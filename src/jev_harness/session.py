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

# Heuristic savings model. These are documented planning assumptions, NOT measured
# token counts: they translate intercepted failures into an estimated ROI. The CLI
# and MCP surfaces label every derived number as a heuristic estimate.
ASSUMED_TOKENS_PER_TRIAGE_SKIP = 26200
ASSUMED_COST_PER_TRIAGE_SKIP_USD = 0.31
ASSUMED_TOKENS_PER_ABORT = 80000
ASSUMED_COST_PER_ABORT_USD = 1.20
ASSUMED_TOKENS_PER_DETERMINISTIC_ROUTE = 5000
ASSUMED_COST_PER_DETERMINISTIC_ROUTE_USD = 0.05
ASSUMED_TOKENS_PER_EFFORT_DOWNGRADE = 7000
ASSUMED_COST_PER_EFFORT_DOWNGRADE_USD = 0.21


@dataclass
class AttemptRecord:
    timestamp: float
    step: str
    error_snippet: str
    diff_hash: str
    action_taken: str


# Bumped when the persisted shape changes. Readers merge tolerantly: a writer from an older
# version must never erase fields it does not know (E3.7).
SESSION_SCHEMA_VERSION = 2


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
    # Measured (E1.4): what the provider actually reported for the decisions that used the
    # network. Always kept apart from the heuristic *estimated* savings above.
    measured_requests: int = 0
    measured_input_tokens: int = 0
    measured_output_tokens: int = 0
    measured_cost_usd: float = 0.0
    measured_duration_ms: int = 0
    schema_version: int = SESSION_SCHEMA_VERSION
    # E3.4: the last decisions per gate, so a gate can use real history instead of whatever the
    # caller remembered to send. Hashes and metadata only: no raw log content.
    gate_decisions: List[Dict[str, Any]] = field(default_factory=list)
    # E3.7: an effort lease with a TTL and a break-glass reported by the caller.
    lease: Optional[Dict[str, Any]] = None
    last_tool_error: str = ""
    # Unknown keys written by another (possibly newer) writer, preserved verbatim on save.
    _extra: Dict[str, Any] = field(default_factory=dict)


def _get_storage_path() -> Path:
    """Returns path to storage file, preferring repo .jev or ~/.config/jev."""
    try:
        # Repository-scoped state is opt-in: `jev-harness init` creates `.jev/` (git-ignored), and
        # while it exists the session, the receipts and the lease stay inside that repository.
        # Without it the state lives in the user-scoped config directory, shared by every project.
        local_dir = Path.cwd() / ".jev"
        if local_dir.exists() and os.access(local_dir, os.W_OK):
            return local_dir / "session.json"
    except Exception:
        pass

    global_dir = Path.home() / ".config" / "jev"
    try:
        global_dir.mkdir(parents=True, exist_ok=True)
        _harden_permissions(global_dir, 0o700)
        return global_dir / "session.json"
    except Exception:
        return Path(tempfile.gettempdir()) / "jev_session_default.json"


def _harden_permissions(path: Path, mode: int = 0o600) -> None:
    """Best-effort POSIX permission hardening (no-op where unsupported)."""
    try:
        if path.exists():
            os.chmod(path, mode)
    except Exception:
        pass


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
            _harden_permissions(lock_path, 0o600)
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
                schema_version=int(data.get("schema_version", 1) or 1),
                gate_decisions=[d for d in data.get("gate_decisions", []) if isinstance(d, dict)][-200:],
                lease=data.get("lease") if isinstance(data.get("lease"), dict) else None,
                last_tool_error=str(data.get("last_tool_error", "")),
                _extra={
                    key: value
                    for key, value in data.items()
                    if key
                    not in {
                        "history", "total_triage_calls", "skipped_llm_calls", "abort_guards_triggered",
                        "deterministic_routes", "effort_modulations", "nudge_continuations",
                        "estimated_tokens_saved", "estimated_cost_saved_usd", "measured_requests",
                        "measured_input_tokens", "measured_output_tokens", "measured_cost_usd",
                        "measured_duration_ms", "schema_version", "gate_decisions", "lease",
                        "last_tool_error", "last_updated",
                    }
                },
                measured_requests=data.get("measured_requests", 0),
                measured_input_tokens=data.get("measured_input_tokens", 0),
                measured_output_tokens=data.get("measured_output_tokens", 0),
                measured_cost_usd=data.get("measured_cost_usd", 0.0),
                measured_duration_ms=data.get("measured_duration_ms", 0),
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
            "measured_requests": session.measured_requests,
            "measured_input_tokens": session.measured_input_tokens,
            "measured_output_tokens": session.measured_output_tokens,
            "measured_cost_usd": session.measured_cost_usd,
            "measured_duration_ms": session.measured_duration_ms,
            "schema_version": SESSION_SCHEMA_VERSION,
            "gate_decisions": session.gate_decisions[-200:],
            "lease": session.lease,
            "last_tool_error": session.last_tool_error,
            "last_updated": time.time(),
        }
        # Never erase fields written by another version of the tool.
        for key, value in getattr(session, "_extra", {}).items():
            data.setdefault(key, value)
        # Atomic file write with thread/pid unique suffix to avoid collisions on Windows/Unix
        temp_file = p.with_name(f"{p.name}.{os.getpid()}_{threading.get_ident()}_{time.time_ns()}.tmp")
        temp_file.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
        _harden_permissions(temp_file, 0o600)
        temp_file.replace(p)
        _harden_permissions(p, 0o600)
    except Exception:
        pass


def record_measured_usage(
    input_tokens: int, output_tokens: int, cost_usd: float = 0.0, duration_ms: int = 0
) -> None:
    """Accumulates what the provider actually reported for one live decision (E1.4).

    Mock/offline answers never call this: their "usage" is local arithmetic, not a measurement.
    """

    def _mod(session: SessionState) -> None:
        session.measured_requests += 1
        session.measured_input_tokens += max(0, int(input_tokens))
        session.measured_output_tokens += max(0, int(output_tokens))
        session.measured_cost_usd += max(0.0, float(cost_usd))
        session.measured_duration_ms += max(0, int(duration_ms))

    update_session(_mod)


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
            session.estimated_tokens_saved += ASSUMED_TOKENS_PER_TRIAGE_SKIP
            session.estimated_cost_saved_usd += ASSUMED_COST_PER_TRIAGE_SKIP_USD
    update_session(_mod)


def record_abort_event(triggered: bool) -> None:
    def _mod(session: SessionState) -> None:
        if triggered:
            session.abort_guards_triggered += 1
            session.estimated_tokens_saved += ASSUMED_TOKENS_PER_ABORT
            session.estimated_cost_saved_usd += ASSUMED_COST_PER_ABORT_USD
    update_session(_mod)


def record_route_event(selected_tier: str) -> None:
    if selected_tier == "deterministic":
        def _mod(session: SessionState) -> None:
            session.deterministic_routes += 1
            session.estimated_tokens_saved += ASSUMED_TOKENS_PER_DETERMINISTIC_ROUTE
            session.estimated_cost_saved_usd += ASSUMED_COST_PER_DETERMINISTIC_ROUTE_USD
        update_session(_mod)


def record_reasoning_effort_event(effort: str, provider: str = "openai") -> None:
    def _mod(session: SessionState) -> None:
        session.effort_modulations += 1
        if effort == "low":
            # Downgrading heavy reasoning to low is modeled as one avoided reasoning burst.
            session.estimated_tokens_saved += ASSUMED_TOKENS_PER_EFFORT_DOWNGRADE
            session.estimated_cost_saved_usd += ASSUMED_COST_PER_EFFORT_DOWNGRADE_USD
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
            session.estimated_tokens_saved += ASSUMED_TOKENS_PER_TRIAGE_SKIP
            session.estimated_cost_saved_usd += ASSUMED_COST_PER_TRIAGE_SKIP_USD
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
            session.estimated_tokens_saved += ASSUMED_TOKENS_PER_ABORT
            session.estimated_cost_saved_usd += ASSUMED_COST_PER_ABORT_USD
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


MAX_GATE_DECISIONS = 20
DEFAULT_LEASE_TTL_SECONDS = 1800


def record_gate_decision(gate: str, decision: str, action: str = "", input_hash: str = "") -> None:
    """E3.4: remembers one decision so the gates can use real history on the next call."""

    def _mod(session: SessionState) -> None:
        session.gate_decisions.append(
            {
                "gate": gate,
                "decision": decision,
                "action": action,
                "input_hash": input_hash,
                "ts": round(time.time(), 3),
            }
        )
        kept: List[Dict[str, Any]] = []
        per_gate: Dict[str, int] = {}
        for record in reversed(session.gate_decisions):
            name = str(record.get("gate", ""))
            per_gate[name] = per_gate.get(name, 0) + 1
            if per_gate[name] <= MAX_GATE_DECISIONS:
                kept.append(record)
        session.gate_decisions = list(reversed(kept))

    update_session(_mod)


def gate_history(gate: str) -> List[Dict[str, Any]]:
    """The remembered decisions for one gate, oldest first."""
    return [record for record in load_session().gate_decisions if record.get("gate") == gate]


def set_lease(effort: str, provider_params: Optional[Dict[str, Any]] = None, steps_remaining: int = 1) -> None:
    """E3.7: stores the effort lease with its contract (`schema_version`, TTL, steps)."""

    def _mod(session: SessionState) -> None:
        # A new decision is a fresh start: the previous break-glass no longer applies.
        session.last_tool_error = ""
        session.lease = {
            "effort": effort,
            "provider_params": provider_params or {},
            "steps_remaining": max(0, int(steps_remaining)),
            "issued_at": round(time.time(), 3),
            "ttl_seconds": DEFAULT_LEASE_TTL_SECONDS,
            "schema_version": SESSION_SCHEMA_VERSION,
        }

    update_session(_mod)


def get_lease(now: Optional[float] = None) -> Optional[Dict[str, Any]]:
    """The live lease, or None when it is exhausted, expired or invalidated by a tool error."""
    session = load_session()
    lease = session.lease
    if not isinstance(lease, dict):
        return None
    if session.last_tool_error:
        return None
    if int(lease.get("steps_remaining", 0) or 0) <= 0:
        return None
    issued_at = float(lease.get("issued_at", 0) or 0)
    ttl = int(lease.get("ttl_seconds", DEFAULT_LEASE_TTL_SECONDS) or DEFAULT_LEASE_TTL_SECONDS)
    reference = time.time() if now is None else now
    if issued_at <= 0 or reference - issued_at > ttl:
        return None
    return lease


def consume_lease() -> Optional[Dict[str, Any]]:
    """Returns the live lease and spends one step of it."""
    lease = get_lease()
    if lease is None:
        return None

    def _mod(session: SessionState) -> None:
        if isinstance(session.lease, dict):
            session.lease["steps_remaining"] = max(0, int(session.lease.get("steps_remaining", 0)) - 1)

    update_session(_mod)
    remaining = max(0, int(lease.get("steps_remaining", 0) or 0) - 1)
    return {**lease, "steps_remaining": remaining}


def record_tool_error(summary: str) -> None:
    """E3.7 break-glass: a tool error invalidates the lease immediately."""

    def _mod(session: SessionState) -> None:
        session.last_tool_error = summary[:400]
        session.lease = None

    update_session(_mod)


def clear_tool_error() -> None:
    def _mod(session: SessionState) -> None:
        session.last_tool_error = ""

    update_session(_mod)
