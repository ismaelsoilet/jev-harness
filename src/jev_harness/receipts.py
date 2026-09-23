"""
E1.3 — append-only decision receipts (local audit trail), and the retention rules that keep
them from becoming a leak (E3.8).

Each receipt is a single JSON line in `.jev/receipts.jsonl` (0600) carrying **no raw log
content**: the decision, the confidence, the model, whether it was a mock/degraded answer, and a
stable hash of the input. That makes the trail auditable without storing what was audited.

State lives in the same place the session does (repository `.jev/`, else `~/.config/jev`), and
retention is bounded in both age and size so `--no-receipts` is not the only privacy control.

Concurrency reuses the session's cross-process lock, so `receipts`/`--tail` are safe while other
processes keep deciding.
"""
from __future__ import annotations

import hashlib
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from .config import load_repo_config
from .session import _harden_permissions, _session_lock, _get_storage_path

RECEIPTS_VERSION = 1
DEFAULT_MAX_ENTRIES = 5000
DEFAULT_TTL_DAYS = 30


def receipts_dir() -> Path:
    """The state directory, next to the session file (repository-first, then user config)."""
    return _get_storage_path().parent


def receipts_path() -> Path:
    return receipts_dir() / "receipts.jsonl"


def compute_input_hash(gate: str, input_text: str) -> str:
    """Stable, content-free fingerprint of a decision input.

    Deterministic across runs and platforms (UTF-8, fixed separators), so the same failure
    produces the same hash and two receipts can be correlated without storing the log.
    """
    digest = hashlib.sha256()
    digest.update(gate.encode("utf-8"))
    digest.update(b"\x00")
    digest.update((input_text or "").encode("utf-8"))
    return digest.hexdigest()[:32]


def _config_value(key: str, default: Any) -> Any:
    value = load_repo_config().get(key, default)
    return default if value is None else value


def receipts_enabled() -> bool:
    """`.jev.json` `"receipts": false` or `JEV_RECEIPTS=0` disables the trail entirely."""
    env = os.getenv("JEV_RECEIPTS")
    if env is not None and env.strip() in ("0", "false", "off", "no"):
        return False
    return bool(_config_value("receipts", True))


def _retention_limits() -> Dict[str, int]:
    try:
        max_entries = int(_config_value("receipts_max_entries", DEFAULT_MAX_ENTRIES))
    except (TypeError, ValueError):
        max_entries = DEFAULT_MAX_ENTRIES
    try:
        ttl_days = int(_config_value("receipts_ttl_days", DEFAULT_TTL_DAYS))
    except (TypeError, ValueError):
        ttl_days = DEFAULT_TTL_DAYS
    return {"max_entries": max(0, max_entries), "ttl_days": max(0, ttl_days)}


def record_receipt(
    gate: str,
    input_text: str,
    decision: str,
    confidence: Optional[float] = None,
    model: str = "",
    is_mock: bool = False,
    degraded_reason: str = "",
    shadow: bool = False,
    extra: Optional[Dict[str, Any]] = None,
) -> Optional[Dict[str, Any]]:
    """Appends one receipt. Returns the record, or None when receipts are disabled."""
    if not receipts_enabled():
        return None

    receipt: Dict[str, Any] = {
        "receipt_version": RECEIPTS_VERSION,
        "ts": round(time.time(), 3),
        "utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "gate": gate,
        "input_hash": compute_input_hash(gate, input_text),
        "decision": decision,
        "confidence": None if confidence is None else round(float(confidence), 6),
        "model": model,
        "is_mock": bool(is_mock),
        "degraded_reason": degraded_reason,
        "shadow": bool(shadow),
    }
    if extra:
        for key, value in extra.items():
            receipt.setdefault(key, value)

    path = receipts_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        _harden_permissions(path.parent, 0o700)
        with _session_lock(path):
            with path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(receipt, ensure_ascii=False) + "\n")
            _harden_permissions(path, 0o600)
            prune_receipts(path=path)
    except Exception:
        # An audit trail must never break a decision.
        return receipt
    return receipt


def _read_lines(path: Path) -> List[Dict[str, Any]]:
    if not path.is_file():
        return []
    records: List[Dict[str, Any]] = []
    try:
        for raw in path.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except ValueError:
                continue
    except Exception:
        return records
    return records


def read_receipts(tail: int = 20, path: Optional[Path] = None) -> List[Dict[str, Any]]:
    """Returns the newest `tail` receipts (oldest first)."""
    records = _read_lines(path or receipts_path())
    if tail is None or tail <= 0:
        return records
    return records[-tail:]


def prune_receipts(
    ttl_days: Optional[int] = None,
    max_entries: Optional[int] = None,
    path: Optional[Path] = None,
    now: Optional[float] = None,
) -> int:
    """Applies the retention policy (age then size). Returns how many receipts were dropped."""
    limits = _retention_limits()
    ttl = limits["ttl_days"] if ttl_days is None else ttl_days
    cap = limits["max_entries"] if max_entries is None else max_entries
    target = path or receipts_path()
    reference = time.time() if now is None else now

    records = _read_lines(target)
    if not records:
        return 0

    kept = records
    if ttl > 0:
        cutoff = reference - ttl * 86400
        kept = [r for r in kept if float(r.get("ts", 0) or 0) >= cutoff]
    if cap > 0:
        kept = kept[-cap:]
    elif cap == 0:
        kept = []

    dropped = len(records) - len(kept)
    if dropped <= 0:
        return 0
    try:
        tmp = target.with_name(f"{target.name}.{os.getpid()}_{time.time_ns()}.tmp")
        tmp.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in kept), encoding="utf-8")
        _harden_permissions(tmp, 0o600)
        tmp.replace(target)
        _harden_permissions(target, 0o600)
    except Exception:
        return 0
    return dropped


def receipts_summary(path: Optional[Path] = None) -> Dict[str, Any]:
    """Cheap aggregate for `receipts --json` and for `doctor`."""
    records = _read_lines(path or receipts_path())
    gates: Dict[str, int] = {}
    degraded = 0
    shadowed = 0
    for record in records:
        gates[str(record.get("gate", "?"))] = gates.get(str(record.get("gate", "?")), 0) + 1
        degraded += 1 if record.get("degraded_reason") else 0
        shadowed += 1 if record.get("shadow") else 0
    return {
        "total": len(records),
        "first_ts": records[0].get("ts") if records else None,
        "last_ts": records[-1].get("ts") if records else None,
        "per_gate": gates,
        "degraded": degraded,
        "shadow": shadowed,
        **{f"retention_{k}": v for k, v in _retention_limits().items()},
    }


def ensure_state_ignored(cwd: Path) -> Optional[str]:
    """Ensures `.jev/` is git-ignored in `cwd` (creating `.gitignore` when absent).

    Local state (sessions, receipts, caches) must never end up in a commit: it can contain
    failure snippets and hashes of untrusted logs. Returns the entry when it was added.
    """
    gitignore = cwd / ".gitignore"
    entry = ".jev/"
    try:
        existing = gitignore.read_text(encoding="utf-8") if gitignore.is_file() else ""
    except Exception:
        return None
    ignored = {".jev/", ".jev", "/.jev/", "/.jev"}
    if any(line.strip() in ignored for line in existing.splitlines()):
        return None
    separator = "" if not existing or existing.endswith("\n") else "\n"
    header = "" if existing else "# Added by jev-harness: local decision state (sessions, receipts, cache)\n"
    try:
        gitignore.write_text(existing + separator + header + entry + "\n", encoding="utf-8")
    except Exception:
        return None
    return entry
