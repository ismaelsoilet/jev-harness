"""
E0.4 — structured state for the gates.

The provider's own guidance is to give the judge *structure* plus explicit path references
instead of one concatenated string: a structured state keeps the failure log, the command that
produced it, the repository and the referenced files apart, so the answer can point at a field.

Design choice worth stating: the wire format stays a **JSON string**. The official client
declares `state` as text, so a gate builds a mapping here and `JevClient` serialises it
deterministically (sorted keys, compact separators) before it leaves the process. That keeps the
structured contract internally without risking a provider-side type rejection, and it keeps the
cache key, the payload guard and the offline engine working on one canonical string.

A plain string remains a supported fallback everywhere: callers that pass text keep working.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Mapping, Optional, Sequence

# Fields that carry no signal: dropping them keeps the state compact and the mock's token
# overlap from being polluted by empty keys.
_EMPTY = (None, "", [], {}, ())

def build_state(**fields: Any) -> Dict[str, Any]:
    """Builds the structured state for one gate, dropping empty fields.

    Keys are stable per gate so a caller (and the cache key) can rely on them:
    `failure_log`, `test_command`, `repo`, `proposed_step`, `previous_attempts`, `task`,
    `acceptance_criteria`, `produced_output`, `context`, `transcript_tail`, `previous_nudge`,
    plus whatever the caller adds with `--state-json`.
    """
    state: Dict[str, Any] = {}
    for key, value in fields.items():
        if value in _EMPTY:
            continue
        state[key] = value
    return state


def merge_state(state: Mapping[str, Any], extra: Optional[Mapping[str, Any]]) -> Dict[str, Any]:
    """Merges caller-provided context over the gate's own fields (caller wins on a clash)."""
    if not extra:
        return dict(state)
    merged = dict(state)
    for key, value in extra.items():
        if value in _EMPTY:
            continue
        merged[str(key)] = value
    return merged


def parse_state_json(raw: Optional[str]) -> Dict[str, Any]:
    """Parses `--state-json`: either an inline JSON object or a path to a JSON file.

    Raises ValueError with an actionable message when the value is neither, so the CLI can exit
    `2` instead of guessing.
    """
    if raw is None:
        return {}
    text = raw.strip()
    if not text:
        return {}
    if text[0] in "{[\"":  # inline JSON (object, array or scalar)
        try:
            data = json.loads(text)
        except ValueError as exc:
            raise ValueError(f"--state-json is not valid JSON: {exc}") from exc
    else:
        path = Path(text)
        if not path.is_file():
            raise ValueError(f"--state-json is neither an inline object nor an existing file: {text}")
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except ValueError as exc:
            raise ValueError(f"--state-json file {text} is not valid JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError("--state-json must be a JSON object (for example {\"test_command\": \"pytest -q\"})")
    return data


def serialize_state(state: Any) -> str:
    """Canonical serialisation used for the wire, the payload guard and the cache key."""
    if isinstance(state, str):
        return state
    return json.dumps(state, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


# Perception fields are provider-facing metadata: the offline engine keeps scoring the full
# (redacted) log, so its deterministic verdicts stay comparable across runtimes.
_OFFLINE_IGNORED_KEYS = ("focused_slice", "causal_context", "raw_log_ref")


def render_state_text(state: Any) -> str:
    """Renders a structured state as labelled text with **real newlines**.

    The wire keeps the JSON form (structure, path references), but the offline engine is
    line-oriented: `json.dumps` escapes every newline as `\\n`, which would collapse a
    multi-line failure log into a single line and silently change every line-anchored pattern.
    Rendering the fields back as labelled text keeps the offline verdicts equivalent to the
    plain-text contract. Provider-facing perception metadata (E3.5) is skipped: the engine keeps
    scoring the full (redacted) log, so its verdicts stay comparable across runtimes.
    """
    parsed: Any = state
    if isinstance(state, str):
        try:
            parsed = json.loads(state)
        except ValueError:
            return state
    if not isinstance(parsed, dict):
        return serialize_state(parsed)
    parts: list[str] = []
    for key, value in parsed.items():
        if key in _OFFLINE_IGNORED_KEYS:
            continue
        if isinstance(value, (dict, list, tuple)):
            rendered = json.dumps(value, ensure_ascii=False, sort_keys=True)
        else:
            rendered = str(value)
        parts.append(f"{key}:\n{rendered}")
    return "\n\n".join(parts)
