"""
E1.2 — corpus replay, calibration metrics and the regression gate.

The corpus under `tests/corpus/` holds labelled cases (ground truth written down before the
run) for every semantic gate. `replay` runs them through a real client, prints a confusion
matrix per gate plus precision/recall/F1 and the expected calibration error, and compares the
result with a recorded baseline. It is the tool that turns "the thresholds are defaults" into
a measured statement.

Exit codes (UNIX, same contract as the gates):
    0 — every gate is at or above the baseline and no adversarial case was misclassified
    1 — regression against the baseline, or an adversarial case classified deterministically
    2 — invocation error (missing corpus, unreadable baseline, unknown label)

Zero external dependencies: pure standard library, like the rest of the core.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

from .gates import (
    modulate_reasoning_effort,
    route_model_tier,
    should_abort_trajectory,
    should_nudge_continuation,
    triage_test_failure,
    verify_step_completion,
)

# Regression budget: the macro-F1 of a gate may not drop more than this against the baseline.
MACRO_F1_REGRESSION_TOLERANCE = 0.02

# Classes an untrusted log must never be able to talk the harness into.
ADVERSARIAL_FORBIDDEN_CATEGORIES = ("env_missing", "flaky_transient")

BASELINE_VERSION = 1


@dataclass
class CaseResult:
    case_id: str
    gate: str
    provenance: str
    labels: str
    expected: Dict[str, Any]
    observed: Dict[str, Any]
    confidence: Optional[float] = None
    error: str = ""

    def matches(self, key: str) -> bool:
        return self.observed.get(key) == self.expected.get(key)


@dataclass
class GateMetrics:
    gate: str
    total: int = 0
    accuracy: float = 0.0
    macro_f1: float = 0.0
    per_class: Dict[str, Dict[str, float]] = field(default_factory=dict)
    confusion: Dict[str, Dict[str, int]] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    ece: Optional[float] = None


@dataclass
class ReplayOutcome:
    metrics: Dict[str, GateMetrics]
    results: List[CaseResult]
    adversarial_violations: List[CaseResult]


def _labels_for(gate: str) -> Tuple[str, List[str]]:
    """Returns (primary label key, the keys that must match) for a gate."""
    if gate == "triage":
        return "category", ["category", "skip_llm"]
    if gate == "abort":
        return "should_abort", ["should_abort"]
    if gate == "verify":
        return "is_verified", ["is_verified"]
    if gate == "route":
        return "selected_tier", ["selected_tier"]
    if gate == "effort":
        return "effort", ["effort"]
    if gate == "nudge":
        return "should_nudge", ["should_nudge"]
    raise ValueError(f"unknown gate in corpus: {gate}")


def _run_case(gate: str, case: Dict[str, Any], client: Any) -> Tuple[Dict[str, Any], Optional[float]]:
    payload = case.get("input", {})
    if gate == "triage":
        res = triage_test_failure(payload["log"], client=client, record_session=False)
        return {"category": res.category, "skip_llm": res.skip_llm}, getattr(res, "confidence", None)
    if gate == "abort":
        res = should_abort_trajectory(
            payload["proposed_step"], payload.get("history", ""), client=client, record_session=False
        )
        return {"should_abort": res.should_abort}, getattr(res, "confidence", None)
    if gate == "verify":
        res = verify_step_completion(payload["criteria"], payload["output"], client=client)
        return {"is_verified": res.is_verified}, getattr(res, "confidence", None)
    if gate == "route":
        res = route_model_tier(payload["task"], client=client, record_session=False)
        return {"selected_tier": res.selected_tier}, getattr(res, "confidence", None)
    if gate == "effort":
        res = modulate_reasoning_effort(
            payload["context"],
            provider=payload.get("provider", "openai"),
            model=payload.get("model"),
            client=client,
            record_session=False,
        )
        return {"effort": res.effort}, getattr(res, "confidence", None)
    if gate == "nudge":
        res = should_nudge_continuation(payload["transcript_tail"], client=client, record_session=False)
        return (
            {"should_nudge": res.should_nudge, "workflow_phase": res.workflow_phase},
            getattr(res, "confidence", None),
        )
    raise ValueError(f"unknown gate: {gate}")


def load_corpus(corpus_dir: Path) -> List[Dict[str, Any]]:
    """Loads every `*.jsonl` case in the corpus directory, validating its shape."""
    if not corpus_dir.is_dir():
        raise FileNotFoundError(f"corpus directory not found: {corpus_dir}")

    cases: List[Dict[str, Any]] = []
    seen: Dict[str, str] = {}
    for path in sorted(corpus_dir.glob("*.jsonl")):
        gate = path.stem
        _labels_for(gate)  # fail fast on an unknown gate file
        for lineno, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            line = raw.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
            except ValueError as exc:
                raise ValueError(f"{path.name}:{lineno}: invalid JSON ({exc})") from exc
            for key in ("id", "input", "expected"):
                if key not in entry:
                    raise ValueError(f"{path.name}:{lineno}: missing '{key}'")
            if entry["id"] in seen:
                raise ValueError(f"duplicate case id '{entry['id']}' ({path.name} and {seen[entry['id']]})")
            seen[entry["id"]] = path.name
            entry["gate"] = gate
            entry.setdefault("provenance", "unknown")
            entry.setdefault("labels", "weak")
            cases.append(entry)
    if not cases:
        raise ValueError(f"no corpus cases found in {corpus_dir}")
    return cases


def _confusion(expected: Sequence[Any], observed: Sequence[Any]) -> Dict[str, Dict[str, int]]:
    matrix: Dict[str, Dict[str, int]] = {}
    for exp, obs in zip(expected, observed):
        matrix.setdefault(str(exp), {})
        matrix[str(exp)][str(obs)] = matrix[str(exp)].get(str(obs), 0) + 1
    return matrix


def _prf(confusion: Dict[str, Dict[str, int]]) -> Tuple[float, Dict[str, Dict[str, float]]]:
    """Per-class precision/recall/F1 plus the macro average (over expected classes)."""
    classes = sorted(set(confusion) | {obs for row in confusion.values() for obs in row})
    per_class: Dict[str, Dict[str, float]] = {}
    for cls in classes:
        tp = confusion.get(cls, {}).get(cls, 0)
        fn = sum(v for k, v in confusion.get(cls, {}).items() if k != cls)
        fp = sum(confusion.get(other, {}).get(cls, 0) for other in confusion if other != cls)
        precision = tp / (tp + fp) if (tp + fp) else 0.0
        recall = tp / (tp + fn) if (tp + fn) else 0.0
        f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) else 0.0
        per_class[cls] = {"precision": precision, "recall": recall, "f1": f1, "support": float(tp + fn)}
    macro = sum(v["f1"] for v in per_class.values()) / len(per_class) if per_class else 0.0
    return macro, per_class


def _ece(confidences: Sequence[float], correct: Sequence[bool], bins: int = 10) -> Optional[float]:
    """Expected calibration error over the provided (confidence, correct) pairs."""
    if not confidences:
        return None
    total = len(confidences)
    error = 0.0
    for index in range(bins):
        low, high = index / bins, (index + 1) / bins
        bucket = [
            (c, ok)
            for c, ok in zip(confidences, correct)
            if (low < c <= high) or (index == 0 and c <= high)
        ]
        if not bucket:
            continue
        avg_conf = sum(c for c, _ in bucket) / len(bucket)
        avg_acc = sum(1 for _, ok in bucket if ok) / len(bucket)
        error += (len(bucket) / total) * abs(avg_acc - avg_conf)
    return error


def compute_metrics(results: Sequence[CaseResult]) -> Dict[str, GateMetrics]:
    metrics: Dict[str, GateMetrics] = {}
    gates = sorted({r.gate for r in results})
    for gate in gates:
        gate_results = [r for r in results if r.gate == gate]
        label_key, keys = _labels_for(gate)
        expected = [r.expected.get(label_key) for r in gate_results]
        observed = [r.observed.get(label_key) for r in gate_results]
        confusion = _confusion(expected, observed)
        macro_f1, per_class = _prf(confusion)

        strict_correct = [all(r.expected.get(k) == r.observed.get(k) for k in keys) for r in gate_results]
        confidence_pairs = [
            (r.confidence, strict)
            for r, strict in zip(gate_results, strict_correct)
            if isinstance(r.confidence, (int, float))
        ]
        metrics[gate] = GateMetrics(
            gate=gate,
            total=len(gate_results),
            accuracy=sum(1 for ok in strict_correct if ok) / len(strict_correct) if strict_correct else 0.0,
            macro_f1=macro_f1,
            per_class=per_class,
            confusion=confusion,
            errors=[r.case_id for r, ok in zip(gate_results, strict_correct) if not ok],
            ece=_ece([c for c, _ in confidence_pairs], [ok for _, ok in confidence_pairs]),
        )
    return metrics


def run_corpus(cases: Sequence[Dict[str, Any]], client: Any) -> ReplayOutcome:
    """Runs every case through the real gate and collects the observations."""
    results: List[CaseResult] = []
    for case in cases:
        gate = case["gate"]
        try:
            observed, confidence = _run_case(gate, case, client)
            error = ""
        except Exception as exc:  # a corpus case must never abort the whole replay
            observed, confidence, error = {}, None, f"{type(exc).__name__}: {exc}"
        results.append(
            CaseResult(
                case_id=case["id"],
                gate=gate,
                provenance=case.get("provenance", "unknown"),
                labels=case.get("labels", "weak"),
                expected=case.get("expected", {}),
                observed=observed,
                confidence=confidence if isinstance(confidence, (int, float)) else None,
                error=error,
            )
        )

    violations = [
        r
        for r in results
        if r.case_id.startswith("adv-")
        and (
            r.observed.get("category") in ADVERSARIAL_FORBIDDEN_CATEGORIES
            or r.observed.get("skip_llm") is True
        )
    ]
    return ReplayOutcome(metrics=compute_metrics(results), results=results, adversarial_violations=violations)


def baseline_payload(outcome: ReplayOutcome, engine: str, model: str) -> Dict[str, Any]:
    return {
        "baseline_version": BASELINE_VERSION,
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "engine": engine,
        "model": model,
        "gates": {
            gate: {
                "total": m.total,
                "accuracy": round(m.accuracy, 6),
                "macro_f1": round(m.macro_f1, 6),
                "ece": None if m.ece is None else round(m.ece, 6),
                "per_class": {
                    cls: {k: round(v, 6) for k, v in stats.items()} for cls, stats in m.per_class.items()
                },
            }
            for gate, m in outcome.metrics.items()
        },
        "totals": {
            "cases": len(outcome.results),
            "hand_labeled": sum(1 for r in outcome.results if r.labels == "hand"),
            "adversarial_violations": len(outcome.adversarial_violations),
        },
    }


def regressions_against(baseline: Dict[str, Any], outcome: ReplayOutcome) -> List[str]:
    """Returns the human explanations of every regression (empty list = clean)."""
    findings: List[str] = []
    base_gates = baseline.get("gates", {})
    for gate, metrics in outcome.metrics.items():
        base = base_gates.get(gate)
        if not base:
            findings.append(f"{gate}: no baseline entry (record one with --update-baseline)")
            continue
        delta = metrics.macro_f1 - float(base.get("macro_f1", 0.0))
        if delta < -MACRO_F1_REGRESSION_TOLERANCE:
            findings.append(
                f"{gate}: macro-F1 {metrics.macro_f1:.4f} dropped {abs(delta):.4f} "
                f"(> {MACRO_F1_REGRESSION_TOLERANCE:.2f}) vs baseline {float(base.get('macro_f1', 0.0)):.4f}"
            )
    for gate in base_gates:
        if gate not in outcome.metrics:
            findings.append(f"{gate}: present in the baseline but missing from this run")
    for violation in outcome.adversarial_violations:
        findings.append(
            f"{violation.case_id}: adversarial case classified as "
            f"{violation.observed.get('category')!r} (skip_llm={violation.observed.get('skip_llm')})"
        )
    return findings


def render_markdown(outcome: ReplayOutcome, engine: str, model: str, findings: Sequence[str]) -> str:
    """Human-readable calibration report, regenerated by `replay --report`."""
    lines: List[str] = []
    lines.append("# Replay & Calibration Report")
    lines.append("")
    lines.append(
        f"- Generated: **{datetime.now(timezone.utc).strftime('%Y-%m-%d')}** "
        f"(`jev-harness replay --corpus tests/corpus`)"
    )
    lines.append(f"- Engine: **{engine}** · model: **{model}**")
    lines.append(
        f"- Corpus: **{len(outcome.results)} cases** "
        f"({sum(1 for r in outcome.results if r.labels == 'hand')} hand-labelled, "
        f"{sum(1 for r in outcome.results if r.labels != 'hand')} weak-labelled)"
    )
    lines.append(
        "- Labels are ground truth recorded in `tests/corpus/`; the numbers below measure how "
        "well the gates agree with them. A low number is a finding, not a failure — the CI gate "
        "only fails when a number *drops* against the recorded baseline."
    )
    lines.append("")

    lines.append("## Summary")
    lines.append("")
    lines.append("| Gate | Cases | Accuracy | Macro-F1 | ECE | Mismatches |")
    lines.append("| :--- | ---: | ---: | ---: | ---: | ---: |")
    for gate, m in sorted(outcome.metrics.items()):
        ece = "—" if m.ece is None else f"{m.ece:.3f}"
        lines.append(
            f"| `{gate}` | {m.total} | {m.accuracy:.3f} | {m.macro_f1:.3f} | {ece} | {len(m.errors)} |"
        )
    lines.append("")

    for gate, m in sorted(outcome.metrics.items()):
        lines.append(f"## `{gate}`")
        lines.append("")
        lines.append("| Expected class | Precision | Recall | F1 | Support |")
        lines.append("| :--- | ---: | ---: | ---: | ---: |")
        for cls, stats in sorted(m.per_class.items()):
            lines.append(
                f"| `{cls}` | {stats['precision']:.3f} | {stats['recall']:.3f} | "
                f"{stats['f1']:.3f} | {int(stats['support'])} |"
            )
        lines.append("")
        lines.append("<details><summary>Confusion matrix (expected → observed)</summary>")
        lines.append("")
        observed_classes = sorted({obs for row in m.confusion.values() for obs in row})
        lines.append("| expected \\ observed | " + " | ".join(f"`{c}`" for c in observed_classes) + " |")
        lines.append("| :--- | " + " | ".join("---:" for _ in observed_classes) + " |")
        for expected_class in sorted(m.confusion):
            cells = [str(m.confusion[expected_class].get(observed, 0)) for observed in observed_classes]
            lines.append(f"| `{expected_class}` | " + " | ".join(cells) + " |")
        lines.append("")
        lines.append("</details>")
        lines.append("")
        if m.errors:
            lines.append(f"Mismatches ({len(m.errors)}): " + ", ".join(f"`{e}`" for e in m.errors[:25]))
            if len(m.errors) > 25:
                lines.append(f"… and {len(m.errors) - 25} more.")
            lines.append("")

    lines.append("## Regression gate")
    lines.append("")
    if findings:
        lines.append("**FAILED** — the following findings fail the mock replay gate:")
        lines.append("")
        for finding in findings:
            lines.append(f"- {finding}")
    else:
        lines.append(
            "Clean: every gate is within the regression budget and no adversarial case was "
            "classified deterministically."
        )
    lines.append("")
    lines.append(
        "> Re-record the baseline with `python -m jev_harness.cli replay --corpus tests/corpus "
        "--update-baseline` **only** when a change is intended and reviewed."
    )
    lines.append("")

    adversarial = [r for r in outcome.results if r.case_id.startswith("adv-")]
    if adversarial:
        lines.append("## Adversarial cases (untrusted log content)")
        lines.append("")
        lines.append("| Case | Observed category | skip_llm |")
        lines.append("| :--- | :--- | :--- |")
        for result in adversarial:
            lines.append(
                f"| `{result.case_id}` | `{result.observed.get('category', '—')}` | "
                f"{result.observed.get('skip_llm', '—')} |"
            )
        lines.append("")
    return "\n".join(lines)


def find_baseline_path(corpus_dir: Path) -> Path:
    """The recorded baseline lives next to the docs, derived from the corpus location."""
    root = corpus_dir.resolve().parent.parent
    return root / "docs" / "REPLAY_REPORT.json"


def find_report_path(corpus_dir: Path) -> Path:
    return find_baseline_path(corpus_dir).with_suffix(".md")


def replay(
    corpus_dir: Path,
    client: Any,
    engine: str,
    baseline_path: Optional[Path] = None,
    update_baseline: bool = False,
    allow_regression: bool = False,
    write_report: bool = True,
) -> Tuple[ReplayOutcome, List[str], Dict[str, Any]]:
    """Runs the corpus, compares against the baseline and (optionally) rewrites both artifacts."""
    cases = load_corpus(corpus_dir)
    outcome = run_corpus(cases, client)
    payload = baseline_payload(outcome, engine, getattr(client, "model", "unknown"))
    baseline_path = baseline_path or find_baseline_path(corpus_dir)

    findings: List[str] = []
    if update_baseline:
        baseline_path.parent.mkdir(parents=True, exist_ok=True)
        baseline_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    elif baseline_path.is_file():
        try:
            baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
        except ValueError as exc:
            raise ValueError(f"unreadable baseline {baseline_path}: {exc}") from exc
        findings = regressions_against(baseline, outcome)
    else:
        findings = [
            f"no baseline recorded at {baseline_path}; run `replay --update-baseline` once, "
            "review the report and commit it"
        ]

    if write_report:
        report_path = find_report_path(corpus_dir)
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(
            render_markdown(outcome, engine, getattr(client, "model", "unknown"), findings),
            encoding="utf-8",
        )

    return outcome, findings, payload


def render_json(outcome: ReplayOutcome, findings: Sequence[str], engine: str, model: str) -> str:
    return json.dumps(
        {
            "engine": engine,
            "model": model,
            "gates": {
                gate: {
                    "total": m.total,
                    "accuracy": round(m.accuracy, 6),
                    "macro_f1": round(m.macro_f1, 6),
                    "ece": None if m.ece is None else round(m.ece, 6),
                    "mismatches": m.errors,
                }
                for gate, m in sorted(outcome.metrics.items())
            },
            "adversarial_violations": [r.case_id for r in outcome.adversarial_violations],
            "findings": list(findings),
            "ok": not findings,
        },
        indent=2,
    )


def render_console(outcome: ReplayOutcome, findings: Sequence[str], engine: str, model: str) -> str:
    lines = ["", "--- JEV REPLAY / CALIBRATION ---", f"Engine:  {engine}  Model: {model}"]
    lines.append(f"Cases:   {len(outcome.results)}")
    lines.append("")
    lines.append(f"{'Gate':<10}{'Cases':>7}{'Acc':>9}{'MacroF1':>10}{'ECE':>9}{'Miss':>7}")
    for gate, m in sorted(outcome.metrics.items()):
        ece = "—" if m.ece is None else f"{m.ece:.3f}"
        lines.append(
            f"{gate:<10}{m.total:>7}{m.accuracy:>9.3f}{m.macro_f1:>10.3f}{ece:>9}{len(m.errors):>7}"
        )
    lines.append("")
    if findings:
        lines.append("RESULT: FAIL (regression gate)")
        for finding in findings:
            lines.append(f"  - {finding}")
    else:
        lines.append("RESULT: OK (every gate within the regression budget, no adversarial violation)")
    lines.append("--------------------------------\n")
    return "\n".join(lines)
