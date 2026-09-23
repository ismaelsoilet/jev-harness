"""
E3.5 — perception: send the judge the precise signal, without noise and without secrets.

A raw test log is mostly noise: setup chatter, progress dots, stack frames. The provider's own
jaggedness docs warn that a large `state` degrades accuracy, so the triage gate sends a small
*focused slice* (the assertion/test line and its immediate neighbourhood) plus a *causal context*
block, and keeps a *reference* to the raw log instead of pasting it twice.

Two safety rules ride along:

* **the slice is provider-facing metadata.** The offline engine keeps scoring the full (redacted)
  log, so the deterministic verdicts stay comparable across runtimes and against the corpus.
* **secrets are redacted before the state leaves the process** — not only in error messages.

Zero external dependencies: standard library only.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Sequence, Tuple

# Field names the offline engine ignores (provider-facing perception metadata).
PERCEPTION_FIELDS = ("focused_slice", "causal_context", "raw_log_ref")

SLICE_MAX_LINES = 15
CAUSAL_MAX_LINES = 10

# A line that *is* the failure: an assertion, a runner failure marker, a compiler error, a panic.
_ASSERTION_LINE = re.compile(
    r"(?:assertionerror|assertion failed|assert\s|assert_eq!|expected:.*received:|"
    r"^\s*(?:FAILED|FAIL|not ok|E\s{2,})\b|error(?:\[[A-Z]+\d+\]| TS\d+| CS\d+)?:|"
    r"panic:|panicked at|segmentation fault|sigsegv|core dumped|"
    r"falha de asserção|fallo de aserción|assertionerror)",
    re.IGNORECASE | re.MULTILINE,
)

# Secret shapes worth masking in a log before it is transmitted.
_SECRET_PATTERNS = (
    r"(?i)\b(?:api[_-]?key|apikey|access[_-]?token|auth[_-]?token|secret|password|passwd|pwd|"
    r"client[_-]?secret|private[_-]?key|bearer)\b\s*[:=]\s*[\"']?([A-Za-z0-9._\-/+]{6,})[\"']?",
    r"(?i)\b(?:sk|pk|rk|vck|xox[baprs])[-_][A-Za-z0-9._\-]{12,}",
    r"(?i)\bgh[pousr]_[A-Za-z0-9]{20,}",
    r"(?i)\bAKIA[0-9A-Z]{16}\b",
    r"-----BEGIN [A-Z ]*PRIVATE KEY-----[\s\S]*?-----END [A-Z ]*PRIVATE KEY-----",
    r"(?i)\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}",  # JWT
    r"(?i)(?:postgres|mysql|mongodb|redis)(?:\+\w+)?://[^\s:@/]+:[^\s@/]+@",
)


def redact_secrets(text: str, limit: Optional[int] = None) -> str:
    """Masks credential-looking material in a log before it is sent or stored."""
    if not text:
        return text
    redacted = text
    for pattern in _SECRET_PATTERNS:
        redacted = re.sub(pattern, lambda match: _mask(match), redacted)
    return redacted if limit is None else redacted[:limit]


def _mask(match: "re.Match[str]") -> str:
    """Keeps the field name/shape, replaces the value: `api_key = [REDACTED]`."""
    whole = match.group(0)
    if match.groups():
        value = match.group(1)
        return whole.replace(value, "[REDACTED]")
    if whole.lower().startswith("-----begin"):
        return "[REDACTED PRIVATE KEY]"
    if "://" in whole:
        scheme, _, rest = whole.partition("://")
        return f"{scheme}://[REDACTED]@"
    return "[REDACTED]"


def _lines(text: str) -> List[str]:
    return text.splitlines()


def find_assertion_line(text: str) -> Optional[str]:
    """The single most informative line of a failure log, or None when there is no clear one."""
    for index, line in enumerate(_lines(text)):
        if _ASSERTION_LINE.search(line):
            return line.strip()
    return None


def _assertion_index(lines: Sequence[str]) -> Optional[int]:
    for index, line in enumerate(lines):
        if _ASSERTION_LINE.search(line):
            return index
    return None


def slice_failure(log_text: str) -> Dict[str, str]:
    """Builds `focused_slice` (assertion + neighbours), `causal_context` and a raw reference.

    Returns an empty mapping when no reliable anchor exists: the caller then keeps its current
    truncation behaviour instead of sending a slice that might drop the signal.
    """
    if not log_text or not log_text.strip():
        return {}
    lines = _lines(log_text)
    anchor = _assertion_index(lines)
    if anchor is None:
        return {}

    half = SLICE_MAX_LINES // 2
    start = max(0, anchor - half)
    end = min(len(lines), start + SLICE_MAX_LINES)
    start = max(0, end - SLICE_MAX_LINES)
    focused = "\n".join(line.rstrip() for line in lines[start:end]).strip()
    if not focused:
        return {}

    # The causal context is what came *before* the anchor: the setup that produced the failure.
    context_start = max(0, start - CAUSAL_MAX_LINES)
    context = "\n".join(line.rstrip() for line in lines[context_start:start]).strip()

    return {
        "focused_slice": focused,
        "causal_context": context,
        "raw_log_ref": f"log:{len(log_text)}chars" if not context else f"log:{len(log_text)}chars",
    }


def perception_fields(log_text: str) -> Dict[str, Any]:
    """The provider-facing perception fields for one failure log (redacted, provider-only)."""
    redacted = redact_secrets(log_text)
    return slice_failure(redacted)


def slice_contains_assertion(slice_text: str) -> bool:
    """Measurement helper for the E1.2 corpus gate (the slice must carry the assertion)."""
    return bool(slice_text) and bool(_ASSERTION_LINE.search(slice_text))
