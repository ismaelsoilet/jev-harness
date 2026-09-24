# Exploration: Foreman Integration in Jev Harness (`opsx-explore`)

- **Change ID:** `foreman-integration`
- **Component:** `jev-harness` (Python, TypeScript, Rust runtimes + CLI)
- **Target System:** [thruwire/foreman](https://github.com/thruwire/foreman) (535★, 38 forks, v0.3.0)
- **Status:** Proposed / Exploration — superseded in authority by `proposal.md`, `design.md` and `spec.md`
- **Author:** Ismael Soilet
- **Date:** 2026-09-23 · **Adversarial pass:** 2026-09-23 (findings A1–A10, §7)
- **Upstream facts verified:** 2026-09-23 (`main`) · **Re-verify by:** 2026-10-23

---

## 1. Context & Motivation

### Background

`thruwire/foreman` supervises coding workers (`Codex`, `OpenCode`) across structured responsibilities (`core.completion`, `core.verification`, `core.worker-health`, `core.human-escalation`, `quality.documentation`, `repository.instructions`) and issues interventions from a sealed set (`CONTINUE`, `START_WORKER`, `START_VERIFIER`, `STEER_WORKER`, `STOP_WORKER`, `RETRY_WORKER`, `FINISH`, `ESCALATE`).

`jev-harness` is a deterministic-first System 1.5 quality gate: a zero-dependency offline engine (heuristic, sub-millisecond), a live Jev path (70–300 ms) when credentials exist, structured recovery contracts (`argv`, never shell strings) and a semantic abort gate — the same surface in Python, TypeScript and Rust.

### Two integration paths (verified mechanics)

- **Path A — companion responsibility (works without touching Foreman's source, but needs a launcher/patch to register the class).** `FactoryPolicy.evaluate` calls `responsibilities.directives(state, result)` (`policy.py`), so a class can read worker output, call jev-harness and propose a sealed directive with a deterministic reason. It **cannot** enrich the Jev prompt: `JevForemanModel.assess` sends `state=observation.model_dump(mode="json")` (`foreman/jev.py`).
- **Path B — populated observation (needs the upstream seam).** `ObservationBuilder.build()` hardcodes `test_results=[]` (`observation.py`); a pluggable provider is the smallest change that puts structured records in front of the supervisor.

### The maintainer response (JARosen)

PR #22 (`docs: add System 1.5 ecosystem interop reference (Foreman + Jev Harness)`) was **closed** on 2026-09-23 by contributor JARosen with:

> *"Thanks for thinking about how these projects might interoperate. We don't currently maintain an ecosystem directory or publish unverified claims about third-party tools in Foreman's documentation. We'd be happy to consider a concrete integration PR with code, tests, and neutral documentation if a real Foreman integration is developed."*

Hence: build the working integration in `jev-harness` first, then propose the seam (`design.md` §Decision 5).

---

## 2. Foreman architecture & the three integration surfaces (verified 2026-09-23)

```
+--------------------------------------------------------------------------+
|                          THRUWIRE / FOREMAN                              |
|                                                                          |
|   +--------------------+        +------------------------------------+   |
|   | Worker execution   |        |        ObservationBuilder          |   |
|   | (Codex / OpenCode) |------->|  git status/diff, output tails     |   |
|   | stdout / stderr    |        |  test_results: []       <-- POINT 1|   |
|   +--------------------+        |  verification_results              |   |
|                                 +------------------------------------+   |
|                                                  |                       |
|                                                  v                       |
|   +--------------------+        +------------------------------------+   |
|   |    ForemanModel    |<-------|     ResponsibilityRegistry         |   |
|   | (Jev system_one)   |        |  packaged + central overrides      |   |
|   | state=observation  |        |  --responsibilities-dir  <-- POINT 2|   |
|   +--------------------+        +------------------------------------+   |
|            |                                                             |
|            v                worker-health checks are SEMANTIC ONLY  <-- POINT 3
|   FactoryPolicy.directives(state, result)   (worker_stuck 0.80)
+--------------------------------------------------------------------------+
```

### Point 1: Evidence is unstructured — and `test_results` is additive

- **Sources:** `observation.py` (`test_results: list[dict[str, Any]]`, hardcoded `[]`; `latest_worker_output` = raw `stdout + "\n" + stderr` tailed to 12,000 chars), `runtime.py` (`VerificationResult(summary=(record.stdout or record.stderr)[-output_limit:])`).
- **Opportunity:** a structured record per failure (category, assertion slice, recovery) that the supervisor can act on — with the honest caveat that the raw tail stays, so this adds structure (~250 tokens/record), it does not replace tokens.

### Point 2: Configuration is central, and a lone TOML is a hard error

- **Sources:** `docs/routing.md`, `README.md`, `configuration.py`, `cli.py`.
- **Verified mechanics:** overrides load from `--responsibilities-dir` / `FOREMAN_RESPONSIBILITIES_DIR`; `configured_registry(config, config_dir=…, additional=[…])` accepts third-party classes that implement `configured(settings)` and `configured_checks(checks)`; a TOML whose stem has no installed class raises `ResponsibilityConfigError: configuration has no installed responsibility implementation: <id>`; and the stock `foreman run` CLI passes **no** `additional=`, so the class must come from a patch or a custom launcher.

### Point 3: Worker stagnation detection is semantic only

- **Source:** `core.worker-health.toml` — `worker_stuck` is one Noul at `min_threshold = 0.80`; Foreman's README warns that uncalibrated semantic scores produce both false positives and false negatives.
- **Opportunity:** deterministic stagnation evidence built from what Foreman actually produces (output tails + bounded `git_diff`), delivered as advisory evidence — never as an order (`SYSTEM_1_5_OPPORTUNITIES.md` §3.1 item 5).

---

## 3. Proposed integration design in `jev-harness`

Authority for the contract lives in `specs/foreman-integration/spec.md`; decisions and rationale in `design.md`. Summary:

### 3.1 `ForemanTriageObserver.extract_test_results(stdout, stderr="", repo_root=None, client=None)`

Built on the real entry point `gates.triage_test_failure(failure_log, client=..., repo_root=...)`, offline by default, one record per log:

```python
result = triage_test_failure(output, client=client or JevClient(force_mock=True), repo_root=repo_root)
if result.category == "no_failure":
    return []
return [{
    "category": result.category, "severity_score": result.severity_score,
    "confidence": result.confidence, "skip_llm": result.skip_llm,
    "action_recommendation": result.action_recommendation,
    "assertion_slice": (find_assertion_line(output) or "")[:500],
    "recovery": result.recovery,          # Python only (capability matrix)
    "is_mock": result.is_mock, "degraded_reason": result.degraded_reason,
    "foreman_schema_version": 1,
}]
```

### 3.2 `ForemanCircuitBreaker.evaluate_worker_health(snapshots, window=5)`

Deterministic stagnation evidence (new work): normalized-output fingerprint + diff fingerprint, abort **only** when both are unchanged across the window (`STAGNANT_EVIDENCE`), decline when the diff is unavailable. See `design.md` §Decision 3 for the rejected "command cycle" and "edit entropy" formulations.

### 3.3 Operator bundle

- `FOREMAN_RESPONSIBILITY_TOML` (`quality.jev-triage.toml`) with the real key set, plus the exported **companion class** (`quality_jev_triage.py`) and a `README.md` stating the activation paths and the hard-error consequence.
- `jev-harness export foreman [--out-dir ./foreman-responsibilities]` writes the three files.

### 3.4 Out of scope for v1

`ForemanVerifierWrapper` (dropped — evidence belongs to the adapter, execution belongs to Foreman); companion installable package (deferred); core-gate promotion of the breaker (recorded path); E3.6 `recovery` port to TS/Rust (declared divergence + follow-up).

---

## 4. Feasibility & trade-off analysis

| Dimension | Assessment | Details |
| :--- | :--- | :--- |
| **Runtime dependencies** | **No new dependency anywhere** | Foreman carries 5 dependencies; Python keeps `dependencies = []`, TypeScript keeps zero runtime deps, Rust keeps its existing crates (`serde`, `serde_json`, `reqwest`, `tokio`, `clap`, `regex`); no runtime imports `foreman` or `pydantic`. |
| **Latency budget** | **Sub-millisecond by default** | Offline deterministic engine, no network; live decisions (only when a client is injected) are 70–300 ms against a debounced 5 s floor / 30 s periodic assessment. |
| **Token effect** | **Additive, not a saving** | The record adds ~250 tokens per failure while `latest_worker_output` keeps its up-to-12,000-char tail (default) or 20,000-char diff. Value = preserved assertion line + machine-actionable category/recovery; a tail-replacement change is a separate upstream discussion. |
| **Adoption friction** | **Medium** | Requires installing jev-harness in the Foreman environment, a launcher/registration patch for the class, and (for prompt enrichment) the upstream seam. Stated plainly in the docs. |
| **Upstream PR feasibility** | **Higher than the first draft** | PR #22 set the bar: code, tests, neutral docs. This change delivers code/tests for the adapter and specifies seam + registration precisely. |
| **Parity cost** | **Bounded but real** | `perception.find_assertion_line` is ported to TS/Rust in this change; `recovery` (E3.6) is a declared divergence with a follow-up. |

---

## 5. Alternatives considered

1. **Ecosystem-directory PR only (PR #22 approach):** closed by the maintainer as unverified claims. Not repeated.
2. **Code directly into Foreman first:** rejected — we would ship without a dogfooded implementation to reference.
3. **MCP-only integration:** rejected — Foreman is an orchestration runtime, not an MCP host.
4. **Adapter as a companion installable package:** deferred — 6th release channel outside quad-sync.
5. **Monkey-patching Foreman internals:** rejected — fragile and hostile to an upstream PR.
6. **Command-cycle detection in v1:** rejected — Foreman exposes no structured command history; the signal would be inert (A4).
7. **Porting E3.6 `recovery` to TS/Rust now:** deferred — pre-existing parity gap, declared in the matrix with a trigger.

---

## 6. Next steps

1. Implement the adapter, the companion class and the CLI in Python (tasks §1–§2); lock the contract with fixtures (tasks §3.1).
2. Port `find_assertion_line` and mirror the surface in TypeScript and Rust; prove parity on the shared fixtures (tasks §3).
3. Update battery counts, living docs and the directory map (tasks §4–§5).
4. Re-verify upstream facts, then prepare the minimal upstream PR — seam **plus registration** (tasks §6).

---

## 7. Corrections applied on 2026-09-23 (truthfulness trail)

### First revision (before code archaeology and primary-source verification)

| Claimed | Verified reality | Fixed in |
| :--- | :--- | :--- |
| `from jev_harness.gates import triage_failure` | `triage_test_failure(failure_log, client=..., repo_root=...)` is the real entry point | §3.1 |
| "deterministic `check_abort()` with normalized edit entropy in <100µs" | No such engine exists; the semantic abort gate is `should_abort_trajectory` | `design.md` §Decision 3 |
| A `latency_us` field | No latency is measured offline | `design.md` §Decision 1 |
| `suggested_recovery` as a shell command | The contract is an `argv` list (E3.6) | `design.md` §Decision 1 |
| `.foreman/responsibilities/` and `.foreman/hooks/triage_observer.py` | Configuration is central; no hooks mechanism exists | `design.md` §Decision 4 |
| "TOML enables zero-code configuration" | A TOML configures an installed class; without it Foreman fails at startup | `design.md` §Decision 4 |
| "533★" | 535★ (the repo's own interop table recorded a stale 517★, corrected by this change) | `proposal.md` §1 |

### Adversarial pass (A1–A10)

| # | Finding | Resolution |
| :--- | :--- | :--- |
| A1 | `recovery` and `assertion_slice` are Python-only; `packages/` has neither (`redactSecrets` only) — strict tri-runtime parity was unachievable as promised | Capability matrix; port `find_assertion_line`; `recovery` declared as divergence with follow-up (`design.md` §Decisions 1/7) |
| A2 | `load_repo_config()` and `build_recovery` resolve from the process CWD → the same log can yield a different `skip_llm` and a rationale computed against the wrong manifests | `repo_root` added to the adapter signature; config caveat documented (`design.md` §Decision 2) |
| A3 | `total_failures` / 5-record cap was unimplementable: one triage call classifies a log, not individual failures | Dropped; one record per log (`design.md` §Decision 1) |
| A4 | The breaker required `commands` / `diff_history`, which Foreman does not produce — it would never fire | Signals redefined to output + diff fingerprint stagnation, with decline on missing signal (`design.md` §Decision 3) |
| A5 | The adapter is inert in stock Foreman (only the observation reaches Jev) and the design never specified the class that makes the preset real | Two paths documented; companion-class contract added (`design.md` §Decision 6) |
| A6 | Token claim inverted: `test_results` is additive, the raw tail remains | Corrected in §4, `design.md` §Risks, `proposal.md` fact 10 |
| A7 | Offline default means the supervisor consumes heuristic verdicts (`is_mock: true`), with a live-call cost trade-off | Documented in `design.md` §Decision 2 |
| A8 | stdout/stderr concatenation can affect the green-run short-circuit | Dedicated edge-case tests (tasks §4.2) |
| A9 | Nested CLI subcommand (3 parsers) and byte-identity of exported files | Tasks §2/§3.4/§7.3 |
| A10 | Category parity is real (triggers in all runtimes + 112-case corpus) — a confirmation, not a defect | Kept; extended to the adapter surface via fixtures |

### Second verification pass (B1–B7, 2026-09-23)

| # | Finding | Resolution |
| :--- | :--- | :--- |
| B1 | `sha256` was mandated for the fingerprints while Rust has no hashing crate and the crate list is frozen — a blocker for the breaker task | Fingerprints are now runtime-local; only the equality verdict is contractual (`design.md` §Decision 3, `spec.md` requirement text, terminology normalized to "fingerprint") |
| B2 | `proposal.md` claimed `assertion_slice` exists in all three runtimes — false (it exists only in `src/jev_harness/perception.py`) | Reworded: `assertion_slice` is ported by this change; `recovery` remains the only declared divergence |
| B3 | Battery-count task missed `.agents/rules/01_project_blueprint.md` and `docs/NOTORIETY_PR_STRATEGY.md` | Added to tasks §4.4 with `grep -rln "569" --include="*.md"` as the checklist |
| B4 | Determinism scenario vs. stateful window: a second call with identical inputs could append and change the verdict | Window keyed by `(run_id, iteration)` with idempotent replacement (`design.md` §Decision 6, `spec.md`, tasks §1.5) |
| B5 | Activation doc named only one failure mode | Both `ResponsibilityConfigError` variants named; directory and class must always ship together (`design.md` §Decision 4, `spec.md` scenario, tasks §2.1) |
| B6 | Purpose still said observations "fill" `test_results` (present tense, no seam exists) | Softened to "can fill … once the upstream seam lands" |
| B7 | The promotion path did not cite the MCP naming rule | tasks §5.4 cites `.agents/rules/07_mcp_quality_and_tdqs_standards.md` with `jev_evaluate_worker_health` as the `verb_noun` example |

### Third pass (C1–C2, 2026-09-23)

| # | Finding | Resolution |
| :--- | :--- | :--- |
| C1 | Task 1.5 required registry-level tests against Foreman's real `ResponsibilityRegistry` (which imports pydantic), contradicting the stdlib-only invariant of task 4.3 — the 3.2/3.3 contradiction relocated | Tests split: unguarded fake-double and fake-runner tests for the exported surface; registry validation under the optional-Foreman skip guard, reported as `skipped`; mirroring the registry locally is explicitly ruled out (Rule 04) |
| C2 | The companion class's `git diff` call is synchronous on Foreman's event loop (`policy.evaluate` is called from `async def _assess`), so an unbounded subprocess would stall worker streaming — the failure `ObservationBuilder._git` avoids with `asyncio.wait_for(timeout=5.0)` | Hard timeout via an injectable runner (`[settings] diff_timeout_seconds`, default 5) with fail-open → diff `null` → breaker declines → class abstains; the trade-off is stated in `design.md` §Decision 6 |

### Fourth pass (D1, 2026-09-23)

| # | Finding | Resolution |
| :--- | :--- | :--- |
| D1 | `design.md` §Decision 6 concluded "it never stalls the loop waiting on git", which over-promises: `subprocess.run(timeout=N)` blocks the calling thread for up to `N` (plus child teardown) before `TimeoutExpired` | The closing clause now states the bounded blocking call precisely — "never stalls the loop beyond `diff_timeout_seconds` plus the child's teardown" — while keeping the fail-open mechanism unchanged |

### Implementation completion notes (2026-09-23)

- **Battery after implementation:** Python **432** · TypeScript **99** · Rust **95** = **626** (documented before: 569 = 393+89+87). The Python baseline was already **395 observed** vs 393 documented — a pre-existing 2-test drift, now recorded at the observed value. `./scripts/release.sh --check` and `./scripts/release.sh --verify-sync` both passed; the replay calibration gate reported OK.
- **Post-review adjustment round (2026-09-24):** the adversarial review's seven adjustments were applied — the class now requires a complete evidence window before any proposal (spec-conformant, with the registry-side tests added under the skip guard), all three CLIs refuse a `.foreman/` target with exit 2, Rust gained a CLI test, and the living-doc counts/map/promotion-path/517★ residuals were corrected. Counts moved 619 → **626** (the adjustment round added 5 Python, 1 TypeScript and 1 Rust test).
- **Cross-runtime byte identity (task 7.3):** the three CLIs exported identical bundles — TOML 1,952 B, companion class 11,598 B, README 2,813 B — verified with `cmp` per file (sizes re-verified after the 2026-09-24 adjustment round).
- **Fixture set extended by one file beyond task 3.1's two:** `tests/fixtures/foreman_operator_readme.md` (the canonical operator README). It is what makes task 7.3 testable from all three runtimes without invoking Python; the companion class needs no extra fixture because the TypeScript/Rust suites compare against the canonical Python module source.
- **Signature parity with a documented no-op:** the TypeScript/Rust `extractTestResults` accept `repoRoot`/`repo_root` and ignore it — `recovery` is Python-only (capability matrix), so there is nothing to scope there.
- **Conditional tasks 6.2 and 6.3** are marked complete as standing guards whose triggers have **not** fired: no upstream PR was opened by this change, and the freshness deadline (2026-10-23) has not passed.
- **Rust implementation detail:** the `regex` crate has no look-around, so the line-reference normalizer consumes the following character and re-inserts it through a capture group; the shared fixture proves verdict equality with the Python/TypeScript implementations.
- **Minor CLI adaptation (task 2.1):** the Python CLI imports `FOREMAN_DEFAULT_OUT_DIR` at module level so the argparse help text and the writer share one source of truth.
