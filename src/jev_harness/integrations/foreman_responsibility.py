"""
Foreman responsibility: `quality.jev-triage` (reference implementation shipped with jev-harness).

This file is exported verbatim by `jev-harness export foreman` into an operator directory and is
loaded by a Foreman installation through `configured_registry(..., additional=[...])` (or an
upstream registration). It pairs with `quality.jev-triage.toml`: the TOML only *configures* an
installed class, and Foreman fails at startup when either half is missing.

Design constraints (change `foreman-integration`, §Decision 6):
    - deterministic given `(state, result)`; the evidence window is keyed by `(run_id, iteration)`
      and never double-counts an assessment;
    - proposes only Foreman's sealed directives, with the `reason` as audit evidence (Foreman
      builds the worker steering text from check probabilities, never from a directive reason);
    - the diff reader is injected, bounded and fail-open: a timeout or a missing `git` yields
      `diff = None`, the breaker declines and the class abstains — it never stalls the event loop
      beyond `diff_timeout_seconds` plus the child teardown;
    - no network by default (the triage uses the offline engine); it never raises into the
      factory loop (fail-open to "no proposal").

`foreman` is imported lazily and optionally: inside a real Foreman installation the genuine
`Directive`/`InterventionType` are used; without it the module still imports and behaves (the
jev-harness test suite exercises this path without installing Foreman).
"""
from __future__ import annotations

import subprocess
from dataclasses import dataclass
from typing import Any, Dict, Iterable, Optional, Sequence, Tuple

from jev_harness.integrations.foreman import ForemanCircuitBreaker, ForemanTriageObserver

try:  # pragma: no cover - the real path runs inside a Foreman installation
    from foreman.models import Directive, InterventionType  # type: ignore
except ImportError:  # pragma: no cover - stdlib-only fallbacks for jev-harness's own suite

    class InterventionType:  # type: ignore[no-redef]
        CONTINUE = "CONTINUE"
        RETRY_WORKER = "RETRY_WORKER"

    @dataclass
    class Directive:  # type: ignore[no-redef]
        action: Any
        reason: str
        assessment_iteration: int
        responsibility_id: str
        priority: int
        confidence: Optional[float] = None


RESPONSIBILITY_ID = "quality.jev-triage"
RETRY_PRIORITY = 700  # below the safety-critical runtime directives (iteration limit is 950)
DEFAULT_DIFF_TIMEOUT_SECONDS = 5
DEFAULT_WINDOW = 5
DIFF_LIMIT_CHARS = 20_000  # mirrors ObservationBuilder's diff bound
ENVIRONMENT_CATEGORIES = ("env_missing", "flaky_transient")
_ALLOWED_SETTINGS = ("diff_timeout_seconds", "window")


@dataclass
class _Check:
    """Duck-typed stand-in for `foreman.responsibilities.Check` (same attribute surface)."""

    responsibility_id: str
    check_id: str
    instructions: str = ""
    min_threshold: Optional[float] = None

    @property
    def key(self) -> str:
        return f"{self.responsibility_id}__{self.check_id}"


@dataclass
class _Route:
    """Duck-typed stand-in for `foreman.responsibilities.ResponsibilityRoute`."""

    always: bool = False
    instructions: Optional[str] = None
    threshold: float = 0.5


def _default_diff_runner(repository: str, timeout_seconds: float) -> Optional[str]:
    """Bounded `git diff` read. Any failure (timeout, missing git, non-repo) yields `None`."""
    try:
        completed = subprocess.run(
            ["git", "-C", str(repository), "diff", "--no-ext-diff"],
            capture_output=True,
            text=True,
            errors="replace",
            timeout=timeout_seconds,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return None
    if completed.returncode != 0:
        return None
    return completed.stdout[-DIFF_LIMIT_CHARS:]


class JevTriageResponsibility:
    """Deterministic worker-health and recovery evidence for Foreman's policy arbiter."""

    id = RESPONSIBILITY_ID

    def __init__(
        self,
        *,
        checks: Sequence[Any] = (),
        diff_runner: Any = None,
        diff_timeout_seconds: float = DEFAULT_DIFF_TIMEOUT_SECONDS,
        window: int = DEFAULT_WINDOW,
    ) -> None:
        self._checks = tuple(checks)
        self._diff_runner = diff_runner or _default_diff_runner
        self._diff_timeout_seconds = float(diff_timeout_seconds)
        self._window_size = max(2, int(window))
        self._window: Dict[Tuple[str, int], Dict[str, Any]] = {}

    # -- Foreman `Responsibility` protocol (duck-typed; no foreman import needed) -----------

    def configured(self, settings: Dict[str, Any]) -> "JevTriageResponsibility":
        unknown = sorted(set(settings) - set(_ALLOWED_SETTINGS))
        if unknown:
            raise ValueError(f"unknown settings for {self.id}: {', '.join(unknown)}")
        window = settings.get("window", self._window_size)
        try:
            window_int = max(2, int(window))
        except (TypeError, ValueError) as error:
            raise ValueError(f"invalid window for {self.id}: {window!r}") from error
        timeout = settings.get("diff_timeout_seconds", self._diff_timeout_seconds)
        try:
            timeout_float = float(timeout)
        except (TypeError, ValueError) as error:
            raise ValueError(f"invalid diff_timeout_seconds for {self.id}: {timeout!r}") from error
        if timeout_float <= 0:
            raise ValueError(f"diff_timeout_seconds must be positive for {self.id}")
        return JevTriageResponsibility(
            checks=self._checks,
            diff_runner=self._diff_runner,
            diff_timeout_seconds=timeout_float,
            window=window_int,
        )

    def configured_checks(self, checks: Iterable[Any]) -> "JevTriageResponsibility":
        return JevTriageResponsibility(
            checks=tuple(checks),
            diff_runner=self._diff_runner,
            diff_timeout_seconds=self._diff_timeout_seconds,
            window=self._window_size,
        )

    def route(self) -> Any:
        return _Route(
            always=False,
            instructions=(
                "Does this job involve running automated tests, compilers, or test-suite "
                "verification where a deterministic failure classification or stagnation signal "
                "would change the next supervisory action?"
            ),
            threshold=0.5,
        )

    def checks(self) -> Tuple[Any, ...]:
        return self._checks

    def directives(self, state: Any, result: Any) -> Sequence[Any]:
        try:
            return self._directives(state, result)
        except Exception:  # fail-open: a broken proposal must never break the factory loop
            return []

    # -- internals --------------------------------------------------------------------------

    def _check_clears(self, result: Any, check_id: str) -> bool:
        """True when the named check's probability clears its own `min_threshold`."""
        grouped = getattr(result, "checks", None) or {}
        probability = (grouped.get(self.id) or {}).get(check_id)
        if not isinstance(probability, (int, float)) or isinstance(probability, bool):
            return False
        for check in self._checks:
            if getattr(check, "responsibility_id", None) != self.id:
                continue
            if getattr(check, "check_id", None) != check_id:
                continue
            threshold = getattr(check, "min_threshold", None)
            return threshold is None or float(probability) >= float(threshold)
        return False

    def _score(self, result: Any, check_id: str) -> Optional[float]:
        grouped = getattr(result, "checks", None) or {}
        probability = (grouped.get(self.id) or {}).get(check_id)
        if isinstance(probability, (int, float)) and not isinstance(probability, bool):
            return float(probability)
        return None

    def _record_evidence(self, state: Any) -> Optional[str]:
        """Adds one `(run_id, iteration)`-keyed snapshot (insert-once) and returns the output."""
        workers = list(getattr(state, "workers", None) or [])
        if not workers:
            return None
        latest = workers[-1]
        output = f"{getattr(latest, 'stdout', '') or ''}\n{getattr(latest, 'stderr', '') or ''}".strip()
        if not output:
            return None
        key = (str(getattr(state, "run_id", "")), int(getattr(state, "iteration", 0)))
        if key not in self._window:
            diff = self._diff_runner(str(getattr(state, "repository", "") or ""), self._diff_timeout_seconds)
            self._window[key] = {"output": output, "diff": diff if isinstance(diff, str) else None}
            if len(self._window) > self._window_size:
                oldest = next(iter(self._window))
                self._window.pop(oldest, None)
        return output

    def _directives(self, state: Any, result: Any) -> Sequence[Any]:
        output = self._record_evidence(state)
        if output is None:
            return []
        if not self._check_clears(result, "deterministic_recovery_available"):
            return []

        iteration = int(getattr(state, "iteration", 0) or 0)
        samples = list(self._window.values())
        verdict = ForemanCircuitBreaker.evaluate_worker_health(samples, window=self._window_size)
        # No proposal until the evidence window is complete: the spec's "no evidence, no
        # proposal" scenario and the restart-safety property both require it, and a single
        # assessment cannot distinguish a fixed transient error from a live one.
        if verdict["evidence"]["insufficient_history"]:
            return []
        if verdict["should_abort"]:
            return [
                Directive(
                    action=InterventionType.RETRY_WORKER,
                    reason=(
                        f"{verdict['reason']}: worker output and repository diff were unchanged "
                        f"across {verdict['evidence']['samples']} assessments"
                    ),
                    assessment_iteration=max(1, iteration),
                    responsibility_id=self.id,
                    priority=RETRY_PRIORITY,
                    confidence=self._score(result, "deterministic_recovery_available"),
                )
            ]

        # A genuine logic regression vetoes a "deterministic recovery" retry: retrying would be a
        # false claim of determinism, so the semantic path keeps that decision.
        if self._check_clears(result, "assertion_failure_critical"):
            return []

        records = ForemanTriageObserver.extract_test_results(
            output, repo_root=getattr(state, "repository", None)
        )
        if not records:
            return []
        record = records[0]
        if not record["skip_llm"] or record["category"] not in ENVIRONMENT_CATEGORIES:
            return []
        recovery = record.get("recovery") or {}
        detail = recovery.get("rationale") or record["action_recommendation"]
        return [
            Directive(
                action=InterventionType.RETRY_WORKER,
                reason=(
                    f"deterministic recovery available ({record['category']}): {detail}"
                ),
                assessment_iteration=max(1, iteration),
                responsibility_id=self.id,
                priority=RETRY_PRIORITY,
                confidence=self._score(result, "deterministic_recovery_available"),
            )
        ]
