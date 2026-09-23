"""
E3.2 / E3.3 — decision cache keyed by a content hash, plus the debounce window for the
turn-by-turn gates.

CI reruns the same log, and integrations evaluate "materially the same" input several times per
turn. The cache answers the first question (identical input → identical decision, no provider
round trip) and the debounce window answers the second (repeated nudge/abort evaluations inside
a short window coalesce into one, reported as `debounced: true`).

Safety rules, in order of importance:
* `--shadow` decisions are never cached: a measurement run must always see real decisions.
* the cache key includes the gate, the input, the model, the provider and whether the answer was
  a mock — an offline answer can never satisfy an online request.
* a degraded (fallback) answer is never stored: it is a symptom, not a decision.
* the cache is local state with TTL and a size cap, 0600, and can be bypassed with `--no-cache`.
"""
from __future__ import annotations

import json
import math
import os
import time
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from .config import load_repo_config
from .receipts import compute_input_hash, receipts_dir
from .session import _harden_permissions, _session_lock

DEFAULT_TTL_SECONDS = 3600
DEFAULT_DEBOUNCE_SECONDS = 5
DEFAULT_MAX_ENTRIES = 500
CACHE_VERSION = 1

# Gates whose repeated evaluation inside a short window is coalesced (turn-by-turn surfaces).
# These names must match the `gate=` argument the gate functions pass to `system_one`.
DEBOUNCE_GATES = ("nudge", "abort")


def cache_path() -> Path:
    return receipts_dir() / "cache.json"


def _config_int(key: str, default: int) -> int:
    value = load_repo_config().get(key, default)
    try:
        return max(0, int(value))
    except (TypeError, ValueError):
        return default


def ttl_seconds() -> int:
    return _config_int("cache_ttl_seconds", DEFAULT_TTL_SECONDS)


def debounce_seconds() -> int:
    return _config_int("debounce_seconds", DEFAULT_DEBOUNCE_SECONDS)


def cache_enabled() -> bool:
    env = os.getenv("JEV_CACHE")
    if env is not None and env.strip() in ("0", "false", "off", "no"):
        return False
    return bool(load_repo_config().get("cache", True))


def cache_key(gate: str, input_text: str, model: str, provider: str, is_mock: bool) -> str:
    """Content hash of everything that can change the answer."""
    material = "\x00".join([gate, model, provider, "mock" if is_mock else "live"])
    return compute_input_hash(material, input_text)


def _empty_cache() -> Dict[str, Any]:
    return {"cache_version": CACHE_VERSION, "entries": {}, "hits": 0, "misses": 0, "debounced": 0}


def _number(value: Any, default: float) -> float:
    """Coerces a state field to a finite number: a corrupted cache file must never raise."""
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    return number if math.isfinite(number) else default


def _load(path: Path) -> Dict[str, Any]:
    if not path.is_file():
        return _empty_cache()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return _empty_cache()
    if not isinstance(data, dict):
        return _empty_cache()
    data.setdefault("entries", {})
    data.setdefault("hits", 0)
    data.setdefault("misses", 0)
    data.setdefault("debounced", 0)
    return data


def _store(path: Path, data: Dict[str, Any], max_entries: int = DEFAULT_MAX_ENTRIES) -> None:
    entries: Dict[str, Any] = data.get("entries", {})
    if max_entries and len(entries) > max_entries:
        ordered = sorted(entries.items(), key=lambda item: _number(item[1].get("stored_at"), 0.0))
        data["entries"] = dict(ordered[-max_entries:])
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        _harden_permissions(path.parent, 0o700)
        tmp = path.with_name(f"{path.name}.{os.getpid()}_{time.time_ns()}.tmp")
        tmp.write_text(json.dumps(data, ensure_ascii=False) + "\n", encoding="utf-8")
        _harden_permissions(tmp, 0o600)
        tmp.replace(path)
        _harden_permissions(path, 0o600)
    except Exception:
        pass


def get(
    gate: str,
    input_text: str,
    model: str,
    provider: str,
    is_mock: bool,
    window_seconds: Optional[int] = None,
    now: Optional[float] = None,
) -> Tuple[Optional[Dict[str, Any]], bool]:
    """Returns (cached payload, debounced). The window overrides the TTL for coalescing."""
    if not cache_enabled():
        return None, False
    path = cache_path()
    key = cache_key(gate, input_text, model, provider, is_mock)
    reference = time.time() if now is None else now
    with _session_lock(path):
        data = _load(path)
        entry = data.get("entries", {}).get(key)
        if entry:
            lifetime = (
                window_seconds
                if window_seconds is not None
                else _number(entry.get("ttl_seconds"), ttl_seconds())
            )
            stored_at = _number(entry.get("stored_at"), 0.0)
            expires_at = stored_at + max(0.0, lifetime)
            if reference <= expires_at:
                data["hits"] = int(_number(data.get("hits"), 0.0)) + 1
                debounced = window_seconds is not None and reference <= stored_at + max(0.0, float(window_seconds))
                if debounced:
                    data["debounced"] = int(_number(data.get("debounced"), 0.0)) + 1
                _store(path, data)
                return dict(entry.get("payload", {})), debounced
        data["misses"] = int(_number(data.get("misses"), 0.0)) + 1
        _store(path, data)
    return None, False


def put(
    gate: str,
    input_text: str,
    model: str,
    provider: str,
    is_mock: bool,
    payload: Dict[str, Any],
    shadow: bool = False,
    degraded: bool = False,
    now: Optional[float] = None,
) -> bool:
    """Stores a decision. Shadow runs and degraded answers are never cached."""
    if not cache_enabled() or shadow or degraded:
        return False
    path = cache_path()
    key = cache_key(gate, input_text, model, provider, is_mock)
    reference = time.time() if now is None else now
    with _session_lock(path):
        data = _load(path)
        data.setdefault("entries", {})[key] = {
            "stored_at": reference,
            "ttl_seconds": ttl_seconds(),
            "gate": gate,
            "payload": payload,
        }
        _store(path, data)
    return True


def clear() -> int:
    """Drops every cached decision. Returns how many entries were removed."""
    path = cache_path()
    with _session_lock(path):
        data = _load(path)
        removed = len(data.get("entries", {}))
        _store(path, _empty_cache())
    return removed


def stats(now: Optional[float] = None, prune: bool = False) -> Dict[str, Any]:
    """Cache hit-rate for `metrics`, optionally pruning expired entries first."""
    path = cache_path()
    reference = time.time() if now is None else now
    with _session_lock(path):
        data = _load(path)
        entries = data.get("entries", {})
        if prune:
            entries = {
                key: entry
                for key, entry in entries.items()
                if reference <= _number(entry.get("stored_at"), 0.0)
                + max(0.0, _number(entry.get("ttl_seconds"), float(ttl_seconds())))
            }
            data["entries"] = entries
            _store(path, data)
        hits = int(_number(data.get("hits"), 0.0))
        misses = int(_number(data.get("misses"), 0.0))
        total = hits + misses
        return {
            "entries": len(entries),
            "hits": hits,
            "misses": misses,
            "debounced": int(_number(data.get("debounced"), 0.0)),
            "hit_rate": (hits / total) if total else None,
            "ttl_seconds": ttl_seconds(),
            "debounce_seconds": debounce_seconds(),
            "enabled": cache_enabled(),
        }


def prune(now: Optional[float] = None) -> int:
    """Drops expired entries (called by the receipts/state maintenance path)."""
    before = stats(now=now)["entries"]
    after = stats(now=now, prune=True)["entries"]
    return max(0, before - after)
