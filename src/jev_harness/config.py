"""
Repository-local configuration loader for `.jev.json`.

Zero external dependencies. Walks up from the current working directory (max 4
levels) looking for a `.jev.json` file, merges it over safe defaults, and caches
the parsed result by file fingerprint so the semantic gates keep their
sub-millisecond latency contract even when called in tight loops.

Honored keys:
    - model                 (str)   -> overrides the provider default model
    - skip_llm_threshold    (float) -> triage gate confidence threshold
    - abort_threshold       (float) -> trajectory abort gate threshold

Credential keys (`api_key`, `provider`) are intentionally resolved by
`JevClient._resolve_credentials`, which owns the environment/global cascade.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional

DEFAULT_SKIP_LLM_THRESHOLD = 0.65
DEFAULT_ABORT_THRESHOLD = 0.70

_DEFAULTS: Dict[str, Any] = {
    "model": None,
    "skip_llm_threshold": DEFAULT_SKIP_LLM_THRESHOLD,
    "abort_threshold": DEFAULT_ABORT_THRESHOLD,
}

# Cache keyed by (resolved path, mtime_ns, size) to avoid repeated disk reads.
_CACHE: Dict[str, Any] = {"fingerprint": None, "config": None}


def find_repo_config_path() -> Optional[Path]:
    """Returns the nearest `.jev.json` walking up from the CWD, or None."""
    try:
        current = Path.cwd()
        candidates = [current, *current.parents]
    except Exception:
        return None

    for candidate in candidates[:4]:
        try:
            jev_json = candidate / ".jev.json"
            if jev_json.is_file():
                return jev_json
        except Exception:
            continue
    return None


def _clamp_probability(value: float) -> float:
    """Clamps a probability-like threshold into the [0.0, 1.0] range."""
    if value < 0.0:
        return 0.0
    if value > 1.0:
        return 1.0
    return value


def load_repo_config() -> Dict[str, Any]:
    """
    Loads `.jev.json` merged over defaults. Never raises: a corrupted or
    unreadable config file degrades to defaults so gates and CI never break.
    """
    path = find_repo_config_path()
    if path is None:
        return dict(_DEFAULTS)

    try:
        stat = path.stat()
        fingerprint = (str(path), stat.st_mtime_ns, stat.st_size)
    except Exception:
        fingerprint = None

    cached = _CACHE.get("config")
    if fingerprint is not None and _CACHE.get("fingerprint") == fingerprint and cached is not None:
        return dict(cached)

    config = dict(_DEFAULTS)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            model = data.get("model")
            if isinstance(model, str) and model.strip():
                config["model"] = model.strip()

            for key in ("skip_llm_threshold", "abort_threshold"):
                value = data.get(key)
                if isinstance(value, (int, float)) and not isinstance(value, bool):
                    config[key] = _clamp_probability(float(value))
    except Exception:
        pass

    if fingerprint is not None:
        _CACHE["fingerprint"] = fingerprint
        _CACHE["config"] = dict(config)
    return config
