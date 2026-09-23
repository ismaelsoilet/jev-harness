# Calibration corpus (E1.2)

Versioned, **labelled** decision cases used by `jev-harness replay` to measure how well the
semantic gates agree with a recorded ground truth. The corpus is the instrument; the measured
numbers live in [`docs/REPLAY_REPORT.md`](../docs/REPLAY_REPORT.md) (generated) and the
machine-readable baseline in [`docs/REPLAY_REPORT.json`](../docs/REPLAY_REPORT.json).

## Why it exists

The provider documentation says thresholds are domain-specific and must be calibrated against
your own data. Before this corpus, `skip_llm_threshold` and `abort_threshold` were defaults with
no measurement behind them, and no release could prove a change had not degraded classification.

## Files

One `*.jsonl` per gate — the file name **is** the gate name:

| File | Cases | Gate under test | Primary label |
| :--- | ---: | :--- | :--- |
| `triage.jsonl` | 112 | `triage_test_failure` | `category` (+ `skip_llm`) |
| `abort.jsonl` | 10 | `should_abort_trajectory` | `should_abort` |
| `verify.jsonl` | 12 | `verify_step_completion` | `is_verified` |
| `route.jsonl` | 10 | `route_model_tier` | `selected_tier` |
| `effort.jsonl` | 8 | `modulate_reasoning_effort` | `effort` |
| `nudge.jsonl` | 8 | `should_nudge_continuation` | `should_nudge` |

Each line is one case:

```json
{
  "id": "env-pytest-module",
  "lang": "en",
  "runner": "pytest",
  "provenance": "synthetic",
  "labels": "hand",
  "input": {"log": "..."},
  "expected": {"category": "env_missing", "skip_llm": true},
  "rationale": "Why this label is the ground truth (hand-labelled cases only)."
}
```

## Labelling protocol

1. **Ground truth first, engine second.** A label states what the failure *is* (a missing
   module is `env_missing`; a data race is `deep_logic`; a passing suite is `no_failure`), never
   what the current engine happens to answer. A label copied from the engine would make the
   corpus tautological and the metrics meaningless.
2. **Weak labels** (`"labels": "weak"`, 76 cases) come from a mechanical rule: the runner's own
   summary plus the canonical error signature of that runner/framework (for example
   `ModuleNotFoundError` for Python, `TS2307` for TypeScript, `E0463` for Rust, `502`/`ETIMEDOUT`
   for transient infrastructure errors).
3. **Hand labels** (`"labels": "hand"`, 84 cases) were reviewed case by case; each carries a
   `rationale` explaining the decision. The sample is stratified across every gate, every
   category and all three languages, so it also measures the confidence of the weak labels
   themselves.
4. **Provenance.** Every case today is `"synthetic"`: composed from real runner error signatures
   and framework messages, but not captured from a production run. Sanitized real logs are
   welcome — add them with `"provenance": "real"` and remove nothing.
5. **Languages.** `en`, `pt` and `es` are represented because the deterministic patterns and the
   mock heuristics are language-sensitive.
6. **Adversarial cases** are prefixed `adv-`: they contain untrusted content that addresses the
   decision engine (prompt injection). The regression gate fails if any of them is classified
   `env_missing`/`flaky_transient` or gets `skip_llm=true`.

## Known gaps measured by the first baseline (2026-09-23)

These are **findings**, kept visible on purpose; the corpus exists to make them measurable, not
to hide them. Each was reproduced with `python -m jev_harness.cli replay --corpus tests/corpus`.

1. **A runner's `FAILED` summary can outrank a concrete root cause.** pytest prints
   `FAILED tests/test_api.py::test_fetch - ModuleNotFoundError: No module named 'requests'`; the
   line starts with `FAILED`, which the offline engine treats as an assertion, so the case
   escalates as `deep_logic` instead of the correct `env_missing`. Direction of the error is
   safe-but-costly (it escalates when it could skip deterministically).
2. **Incidental token overlap with the criteria descriptions can flip a category.** The
   `syntax_trivial` case `./main.go:23:2: expected '}', found 'EOF'` is scored as `env_missing`
   because the word *found* overlaps `"...command not found"` in the `env_missing` criterion
   text. Here the direction is dangerous: `skip_llm=true` on a syntax error.
3. **Missing trigger patterns.** `502 Bad Gateway` and broker/metadata errors are not in the
   transient list, so they fall through to `deep_logic`.
4. **Coarse Noul gates.** `verify`, `nudge` and `effort` sit between 0.5 and 0.7 macro-F1 because
   their offline heuristics are binary-ish (see the report for the per-class numbers).

5. **The gate cannot detect label tampering.** It compares against the recorded baseline, so
   editing a label *towards* the engine's answer can raise macro-F1 and pass. Labels are reviewed
   by a human; a machine cannot tell a corrected label from a self-serving one. (Verified: flipping
   one label up raised triage macro-F1 from 0.9327 to 0.9377; flipping three down failed the gate
   at −5.9 pp, which is the direction that matters for regressions.)

Fixing these is *calibration* work (a scoring/heuristics change with a before/after corpus
comparison and tri-runtime parity), deliberately not bundled into the epic that measures them.

## Running it

```bash
# Mock replay + regression gate (what CI runs)
python -m jev_harness.cli replay --corpus tests/corpus

# Re-record the baseline after an intentional, reviewed change
python -m jev_harness.cli replay --corpus tests/corpus --update-baseline

# Read-only report (does not rewrite docs/REPLAY_REPORT.md)
python -m jev_harness.cli replay --corpus tests/corpus --no-report --json
```

Exit codes: `0` clean · `1` regression against the baseline **or** an adversarial case classified
deterministically · `2` invocation error (missing corpus, unreadable baseline, duplicate ids).

## Adding cases

1. Append a line to the right `*.jsonl` with a unique `id`.
2. Write `expected` from the failure's nature, not from the engine's answer.
3. Prefer hand labels with a `rationale` for anything subtle.
4. Run the replay; if a *new* case disagrees with the engine, that is a finding — leave the label
   as the ground truth and let the report show the mismatch.
