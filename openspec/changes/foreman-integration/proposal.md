# Proposal: Native Foreman Integration in Jev Harness

- **Change ID:** `foreman-integration`
- **Component:** `jev-harness` (Python, TypeScript and Rust runtimes + CLI)
- **Status:** Proposed
- **Date:** 2026-09-23 · **Verification passes:** 2026-09-23 (adversarial A1–A10, parity/bookkeeping B1–B7, implementation-readiness C1–C2 — all recorded in `explore.md` §7)
- **Upstream facts verified:** 2026-09-23 (`thruwire/foreman` @ `main`, `v0.3.0`) · **Re-verify by:** 2026-10-23 (30-day freshness rule)

---

## 1. Problem Statement & Verified Facts

Autonomous factories using [thruwire/foreman](https://github.com/thruwire/foreman) supervise coding workers (Codex/OpenCode) and evaluate health through TypeSafe Jev System One micro-decisions. Primary-source inspection on 2026-09-23 confirms the integration opportunities and the exact extension mechanics.

| # | Verified fact | Primary source (inspected 2026-09-23) |
| :--- | :--- | :--- |
| 1 | `FactoryObservation.test_results` is typed `list[dict[str, Any]]` and `ObservationBuilder.build()` hardcodes `test_results=[]`. | `src/foreman/observation.py` |
| 2 | The verifier summary is a raw output tail: `summary=(record.stdout or record.stderr)[-self.config.output_limit:]` (default 12,000 chars). | `src/foreman/runtime.py` |
| 3 | Worker-health detection is **semantic only**: `meaningful_progress`, `worker_stuck`, `work_off_track` are one Noul each; only `worker_stuck` and `work_off_track` declare `min_threshold = 0.80`; no deterministic cycle, command or diff signal exists. | `src/foreman/responsibilities/definitions/core.worker-health.toml` |
| 4 | Responsibility configuration is **central to the Foreman installation** (`--responsibilities-dir` / `FOREMAN_RESPONSIBILITIES_DIR`); a managed repository never supplies it, and its `.foreman/` is ignored run state. | `docs/routing.md`, `README.md` |
| 5 | A definition TOML only **configures an installed responsibility implementation**. A TOML with no matching installed class makes Foreman exit with `ResponsibilityConfigError: configuration has no installed responsibility implementation: <id>` — a hard startup failure, not a no-op. | `src/foreman/responsibilities/configuration.py` |
| 6 | There is **no hooks mechanism**. The extension points are `ResponsibilityRegistry` + the class API `directives(state, result)` and the sealed directive set `CONTINUE / START_WORKER / START_VERIFIER / STEER_WORKER / STOP_WORKER / RETRY_WORKER / FINISH / ESCALATE`. | repository tree, `src/foreman/policy.py` |
| 7 | Third-party implementations are accepted **programmatically**: `configured_registry(config, config_dir=..., additional=[...])`, where each class must expose `configured(settings)` and `configured_checks(checks)`. | `src/foreman/responsibilities/configuration.py` |
| 8 | The stock `foreman run` CLI passes **no** `additional=` to `configured_registry`, so loading a third-party class today requires a Foreman-side patch or a custom launcher. | `src/foreman/cli.py` |
| 9 | The **only** state channel into the Jev prompt is the observation: `JevForemanModel.assess` sends `state=observation.model_dump(mode="json")`; responsibilities contribute question instructions only. Populating `test_results` is therefore the smallest seam that reaches the supervisor. | `src/foreman/foreman/jev.py`, `src/foreman/foreman/base.py` |
| 10 | `test_results` is **additive**: `latest_worker_output` keeps the raw tail, so the field adds structure (and tokens) rather than replacing the tail. Saving tokens would require a separate, larger upstream change. | `src/foreman/observation.py` |
| 11 | Foreman is **not** zero-dependency: `pydantic>=2.7,<3`, `python-dotenv>=1.0,<2`, `rich>=13.7,<15`, `typer>=0.12,<1`, `typesafe-sdk>=0.2.0,<1` (`v0.3.0`, `requires-python >=3.11`). | `pyproject.toml` |
| 12 | Upstream feedback (PR #22, **closed** 2026-09-23): *"We'd be happy to consider a concrete integration PR with code, tests, and neutral documentation if a real Foreman integration is developed."* | PR #22 |
| 13 | Repository state: 535★, 38 forks. (The interop table in `SYSTEM_1_5_OPPORTUNITIES.md` recorded a stale 517★ until this change corrected it in §3.1.) | repository page |

**Corrections applied since the first draft (all dated 2026-09-23):** the draft cited a non-existent `hooks/` directory (fact 6), claimed a TOML alone enables "zero-code configuration" (facts 5/7), targeted the managed repository's `.foreman/` (fact 4), assumed a "token replacement" effect (fact 10), and relied on `check_abort()`, `triage_failure()`, `latency_us` and `suggested_recovery`-as-shell-string — none of which exist in any jev-harness runtime.

## 2. Dependency Architecture Clarification

- **Foreman:** 5 packages (fact 11). **jev-harness:** Python has `dependencies = []` (pure standard library); TypeScript has zero runtime dependencies; Rust uses its existing crate set (`serde`, `serde_json`, `reqwest`, `tokio`, `clap`, `regex`). This change adds no new dependency to any runtime, and no runtime imports `foreman` or `pydantic`.
- **Coupling direction:** jev-harness → Foreman. Nothing here requires Foreman or pydantic to be installed or importable.
- **Capability matrix (agreed 2026-09-23):** `category`, `skip_llm`, `confidence`, `severity_score` and `action_recommendation` exist in all three runtimes today; **`assertion_slice` is ported to TS/Rust by this change** (today it exists only in `src/jev_harness/perception.py`); `recovery` (E3.6) is **Python-only today** and stays `null` in TS/Rust as a declared divergence with a follow-up port task — both gaps predate this change.

## 3. Capabilities

### Capability: `foreman-integration`

Deterministic triage records for Foreman observations, deterministic stagnation evidence for worker-health decisions, an operator preset **plus its companion responsibility class**, and an export command — in all three jev-harness runtimes, with an explicit capability matrix.

## 4. Proposed Deliverables in `jev-harness`

### Deliverable 1: adapter surface (three runtimes)

- `src/jev_harness/integrations/foreman.py`, `packages/ts/src/foreman.ts`, `packages/rust/src/foreman.rs`:
  - `ForemanTriageObserver.extract_test_results(stdout, stderr="", repo_root=None, client=None)` → `[]` or **one** record per log, reusing the triage vocabulary (`category`, `severity_score`, `confidence`, `skip_llm`, `action_recommendation`, `recovery`, `is_mock`, `degraded_reason`) plus `assertion_slice` and `foreman_schema_version`. `recovery` is `null` in TS/Rust (declared divergence).
  - `ForemanCircuitBreaker.evaluate_worker_health(snapshots, window=5)` → `{"should_abort": bool, "reason": str, "evidence": {...}}`, pure and conservative: aborts only when **output and diff fingerprints are both unchanged** across the window (`reason: "STAGNANT_EVIDENCE"`), and declines (`complete_signals: false`) when the diff is unavailable. The fingerprint algorithm is runtime-local; only the equality verdict is contractual.
  - `FOREMAN_RESPONSIBILITY_TOML` → the operator preset.

### Deliverable 2: exported companion responsibility class

`export foreman` writes a reference `quality_jev_triage.py` implementing the full Foreman `Responsibility` surface — `id`, `checks()`, `route()`, `directives(state, result)`, `configured(settings)`, `configured_checks(checks)` — because a TOML without an installed class is a **hard startup error** (fact 5) and `ResponsibilityRegistry` calls `checks()` unconditionally. The class proposes only sealed directives whose `reason` is **audit evidence** (Foreman builds the steering text from check probabilities, never from directive reasons — fact 9's neighbour: `foreman/steering.py`), never touches the network by default, and keeps its evidence window in memory.

### Deliverable 3: CLI export command (three runtimes)

```bash
jev-harness export foreman [--out-dir ./foreman-responsibilities]
```

Writes `quality.jev-triage.toml`, `quality_jev_triage.py` and `README.md` (activation paths: patched launcher vs. upstream registration; **both** failure modes named — the directory and the class must ship together; never place these in a managed repository's `.foreman/`).

### Deliverable 4: shared golden fixtures

`tests/fixtures/foreman_cases.json` (triage and health cases, including the `diff: null` decline case) and `tests/fixtures/foreman_responsibility.toml` (canonical preset), consumed by all three test suites.

### Deliverable 5: test suites (three runtimes)

`tests/test_foreman_integration.py`, `packages/ts/tests/foreman.test.ts`, `packages/rust/tests/foreman_test.rs` — stdlib-only on the Python side; optional Foreman-schema validation skips when `foreman`/`pydantic` are absent.

### Deliverable 6: documentation

`docs/integrations/foreman.md` (operator guide with the dated source table, capability matrix, activation paths and the hard-error warning) plus README updates EN/PT-BR.

### Deliverable 7: documented upstream draft (not shipped)

Specified in `design.md` §Decision 5: the `test_results` provider seam in `observation.py`, the `quality.jev-triage` TOML + class, and — critically — a registration path so stock `foreman run` can load the class (fact 8).

## 5. Non-Goals

- Modifying `thruwire/foreman` in this phase (draft only).
- Any external dependency in jev-harness; any import of `foreman`/`pydantic`.
- Porting E3.6 `recovery` to TS/Rust in this change (declared divergence + follow-up task).
- Command-cycle detection (Foreman exposes no structured command history — recorded as a future upstream opportunity).
- Promoting the breaker to a core gate / CLI verdict / MCP tool (recorded promotion path).
- Writing into a managed repository's `.foreman/`, or inventing a hooks mechanism.

## 6. Freshness

Every Foreman claim is pinned to 2026-09-23 and must be re-verified before the upstream PR and after 2026-10-23.
