# Tasks: Native Foreman Integration in Jev Harness

## 1. Adapter surface (Python)

- [x] 1.1 Implement `ForemanTriageObserver.extract_test_results(stdout, stderr="", repo_root=None, client=None)` in `src/jev_harness/integrations/foreman.py`: offline client by default, `repo_root` forwarded to the recovery builder, exactly one record per log (no `total_failures`), vocabulary per `design.md` §Decision 1, `assertion_slice` from `perception.find_assertion_line` capped at 500 chars. Verify with tests: green → `[]`; `ModuleNotFoundError: No module named 'requests'` → `env_missing` + `skip_llm: true` + `recovery.argv`; `repo_root` changes the recovery rationale against a fixture repository.
- [x] 1.2 Implement `ForemanCircuitBreaker.evaluate_worker_health(snapshots, window=5)` per `design.md` §Decision 3: normalized-output fingerprint + diff fingerprint (runtime-local algorithm; only equality is contractual), abort only when both are stagnant (`reason: "STAGNANT_EVIDENCE"`), decline with `complete_signals: false` when no diff is present, `insufficient_history: true` under `window` samples. Unit tests for stagnant, healthy, single-signal-decline, and short-history cases.
- [x] 1.3 Add `FOREMAN_RESPONSIBILITY_TOML` (`quality.jev-triage.toml`) using only accepted keys (`enabled`, `always`, `routing_instructions`, `routing_threshold`, `[checks.deterministic_recovery_available]`, `[checks.assertion_failure_critical]`, `min_threshold`, `[settings]`), with a header stating the companion-class requirement and the `ResponsibilityConfigError` consequence. The `[settings]` block carries `diff_timeout_seconds = 5`, applied by the class's `configured()`. Verify it parses as TOML and that a test asserts the warning text is present.
- [x] 1.4 Export the surface in `src/jev_harness/integrations/__init__.py` (extending the docstring beyond host presets) and confirm the module imports with no `pydantic`/`foreman` present.
- [x] 1.5 Implement the reference companion class per `design.md` §Decision 6 (`id = "quality.jev-triage"`, `checks()`, `route()`, `directives(state, result)`, `configured(settings)`, `configured_checks(checks)`, proposals carrying `responsibility_id` equal to the class id, in-memory window keyed by `(run_id, iteration)` with idempotent re-evaluation, sealed directives only, audit-only reason, fail-open, offline by default, injectable diff runner with the hard timeout and decline-on-timeout path). Unguarded tests with a fake `state`/`result` double and a fake diff runner (no Foreman import — the stdlib-only invariant stays intact): abstains without evidence; abstains when the diff runner times out or git is absent; proposes `RETRY_WORKER` for stagnation and for `skip_llm` environmental failures; identical proposal for identical inputs (including re-evaluating the same iteration); the exported class's own surface (`id` equals the TOML stem, `checks()` returns a non-empty sequence, directive `responsibility_id` matches the class id). Foreman-side validation against the real `ResponsibilityRegistry` (empty `checks()` rejection, mismatched `responsibility_id`) runs **under the optional-Foreman skip guard** and reports `skipped` — never by mirroring the registry locally, which Rule 04 would treat as a tautological test (C1).

## 2. CLI export command (Python)

- [x] 2.1 Implement the nested `export foreman` subcommand in `src/jev_harness/cli.py` (first nested subcommand in this CLI) with `--out-dir` defaulting to `./foreman-responsibilities/`; write `quality.jev-triage.toml`, `quality_jev_triage.py` and `README.md`, and print the activation hint. The README must name both `ResponsibilityConfigError` variants (class-without-TOML and TOML-without-class, both exit 2) and state that the directory and the class ship together.
- [x] 2.2 CLI tests: directory creation, default never resolving inside `.foreman/`, byte-identical idempotent re-export, exit code `0`, and the three expected filenames.

## 3. Tri-runtime parity (TypeScript + Rust)

- [x] 3.1 Create `tests/fixtures/foreman_cases.json` (triage cases including a `recovery`-expectation flag, health cases including `diff: null` and short history) and `tests/fixtures/foreman_responsibility.toml` (canonical preset). Document the capability matrix in the fixture header.
- [x] 3.2 Port `perception.find_assertion_line` to TypeScript (pure function, same regex family) and implement the mirrored surface in `packages/ts/src/foreman.ts` (`extractTestResults`, `evaluateWorkerHealth`, `FOREMAN_RESPONSIBILITY_TOML` with `recovery: null`); export from `packages/ts/src/index.ts`; add `packages/ts/tests/foreman.test.ts` consuming the shared fixtures (exact match for the common fields, 1e-9 for numbers, `recovery === null` asserted, constant byte-compared with the fixture).
- [x] 3.3 Same for Rust: port `find_assertion_line` into `packages/rust/src/foreman.rs`, re-export from `packages/rust/src/lib.rs`, add `packages/rust/tests/foreman_test.rs` with the same assertions.
- [x] 3.4 Add `export foreman` to the TypeScript CLI (`packages/ts/src/cli.ts`) and the Rust CLI (`packages/rust/src/cli.rs`, clap nested subcommand) with the same default, the same three files and byte-identical TOML output; extend each runtime's CLI tests, including the byte-identity assertion across runtimes.
- [x] 3.5 Add the capability-matrix test: TS/Rust records have `recovery === null`/`None` and a fixture-driven test asserts the declared divergence (never silently absent).

## 4. Tests, invariants and battery bookkeeping

- [x] 4.1 `tests/test_foreman_integration.py` covers: passing run → `[]`, missing dependency, assertion slice, absence of invented labels, `repo_root` scoping, breaker scenarios, preset parse + header warning, companion class behaviour, CLI export.
- [x] 4.2 Output-concatenation edge cases: empty stderr, a green run whose stderr contains "failed to …" warnings (must not classify as failure), and a traceback split across the stdout/stderr boundary.
- [x] 4.3 Zero-dependency invariant: module and suite run without `pydantic`/`foreman`; the optional Foreman-schema test uses a skip guard and reports `skipped`.
- [x] 4.4 Update the battery counts in the living documents (`AGENTS.md`, `AGENTS.pt-BR.md`, `.agents/rules/01_project_blueprint.md` (count line **and** the inventory in task 5.3), `.agents/rules/04_testing_and_truthfulness.md`, `.agents/rules/05_release_and_quad_sync_protocol.md`, `README.md`, `README.pt-BR.md`, `SYSTEM_1_5_IMPLEMENTATION.md`, `SYSTEM_1_5_PLAN.md`, `SYSTEM_1_5_OPPORTUNITIES.md`, `docs/NOTORIETY_PR_STRATEGY.md`) with the observed total. `grep -rln "569" --include="*.md" .` is the checklist; `docs/RELEASE_NOTES_v0.2.0.md` stays untouched as history.
- [x] 4.5 Run `./scripts/release.sh --check` and, before any version bump, `./scripts/release.sh --verify-sync`.

## 5. Documentation

- [x] 5.1 Write `docs/integrations/foreman.md`: the capability matrix, the dated source table for every Foreman claim (inspected 2026-09-23, re-verify by 2026-10-23), the two activation paths (patched `additional=` launcher vs. upstream registration), the hard-error warning, the `repo_root`/CWD determinism caveats, the additive token effect, and the adapter's inert status without the upstream seam.
- [x] 5.2 Update the README integrations section in `README.md` and `README.pt-BR.md`; verify with `python scripts/check_links.py --root .`.
- [x] 5.3 Update `.agents/rules/01_project_blueprint.md`: add `integrations/foreman.py`, the three test files, the exported bundle, the fixtures and the `export` command to the map.
- [x] 5.4 Record that the breaker is deliberately **not** a core gate, with the promotion path (corpus + CLI verdict + MCP tool + parity review), gated on corpus evidence. Any future MCP exposure must follow `.agents/rules/07_mcp_quality_and_tdqs_standards.md`: canonical `verb_noun` naming in `<namespace>_<verbo>_<substantivo>` form (e.g. `jev_evaluate_worker_health`), never noun-verb forms or `should_` prefixes.
- [x] 5.5 Record the follow-up task to port E3.6 `recovery` to TS/Rust (declared divergence today) with its trigger: when a non-Python consumer needs deterministic recovery.

## 6. Sourcing, freshness and the upstream draft

- [x] 6.1 Re-verify the `SYSTEM_1_5_OPPORTUNITIES.md` §3.1 interop table (stars, links, inspection dates) and update under the dated-source rule enforced by `tests/test_docs_links.py` (the table records 517★ while the repository showed 535★ on 2026-09-23).
- [x] 6.2 Keep `design.md` §Decision 5 as the source of truth; before any upstream PR re-verify all cited files (`observation.py`, `configuration.py`, `cli.py`, `jev.py`, `policy.py`) against the then-current `main`, and include the registration path (fact 8) — a TOML without a registered class is a hard error.
- [x] 6.3 Refresh the dated sections of the change if more than 30 days pass (freshness deadline 2026-10-23).

## 7. Validation and archive

- [x] 7.1 Run `openspec validate foreman-integration --json` (positional change name; `--change` does not exist in this CLI) and confirm zero issues.
- [x] 7.2 Run the tri-runtime tests explicitly (`python -m unittest tests.test_foreman_integration`, `npm test` in `packages/ts`, `cargo test` in `packages/rust`) and record the observed counts.
- [x] 7.3 Confirm the exported bundle is byte-identical across the three runtimes before archiving the change.

## Adversarial review (2026-09-24, SureForge — standard tier, 28/28 units)

Unchecked above = **for adjustment**. Verdict detail:

- **1.5** — (a) `test_proposes_retry_for_environment_recovery` locks a `RETRY_WORKER` proposal with `diff=None` and 1/5 window samples, contradicting spec "No evidence, no proposal" (`spec.md:95-98`: incomplete window → proposes nothing) and `design.md` §Decision 6 ("diff null → the class abstains"; "window incomplete → declines to propose"). Fix impl + test (complete window, collected diff) **or** amend spec/design with approval. (b) The required optional-Foreman `ResponsibilityRegistry` test (empty `checks()` rejection, mismatched `responsibility_id`) is missing — `grep` over `tests/` returns none. (c) Minors: `state.retry_count` (design "Reads") never read; window is insert-once where spec says "replaces"; README claims a general `assertion_failure_critical` veto but the stagnation path returns before the veto (`foreman_responsibility.py:223` vs `:240`).
- **2.1 / 3.4** — Explicit `--out-dir` inside `.foreman/` is written without refusal (`cli.py:591-592`, `cli.ts:495-496`, `cli.rs:498-500`), against `spec.md:102` ("SHALL NOT write into … `.foreman/`") and the binding explore decision (refuse with exit 2, all three runtimes). **3.4 additionally:** Rust has no CLI export test at all (`packages/rust` contains no `cfg(test)`/CLI test; task requires extending *each* runtime's CLI tests).
- **4.4** — `.agents/rules/01_project_blueprint.md` map counts stale vs fresh runs: `:88 49→50`, `:93 12→13`, `:111 45→49`, `:115 16→17`; and the task's own pointer "§5.3" is wrong (the map is §2; the blueprint has §1–§4). Totals elsewhere verified correct (619 = 427 + 98 + 94).
- **5.3** — §2 map lacks `packages/ts/tests/foreman.test.ts`, `packages/rust/tests/foreman_test.rs` (and `src/foreman.ts` / `src/foreman.rs`), the exported bundle (`foreman-responsibilities/` + the three filenames), and the fixture filenames (line 154 is generic).
- **5.4** — `docs/integrations/foreman.md:153-157` records corpus → CLI verdict → MCP tool but omits the required 4th element **parity review**.
- **6.1** — Stale `517★` remains at `SYSTEM_1_5_OPPORTUNITIES.md:12,155` and `docs/NOTORIETY_PR_STRATEGY.md:12,70`; `design.md:117` and `proposal.md:29` still assert in the present tense that the table "records 517★" (false after the §3.1 fix). §3.1 itself, `test_docs_links` and `check_links` are green.
- **6.2 kept `[x]` (adjudication):** independent review flagged that §Decision 5 names only `observation.py`; overruled after investigation — `design.md:13-16` cite the other four files, `design.md:80` carries the registration path (fact 8), `design.md:116` + `docs/integrations/foreman.md` §5 carry the re-verify obligation and the dated five-file table. Non-blocking improvement: cite all five files inside Decision 5.
- **1.4 observation (kept `[x]`):** docstring says "adapter surface in `.foreman`" — defensible as the relative-module notation (`from .foreman import`, line 14) but ambiguous with the forbidden `.foreman/` run-state dir; prefer `foreman.py`.

### Resolution (2026-09-24) — all seven adjustments applied

| # | Adjustment | Fix |
| :--- | :--- | :--- |
| 1.5a | Incomplete window contradicted the spec scenario | The class returns no proposal until the window holds `window` assessments; `test_environment_recovery_requires_a_complete_window` locks the spec scenario, and the env/veto/gate tests now fill the window first (they prove what their names say). |
| 1.5b | Missing Foreman-side registry test | `TestForemanRegistryIntegration` (skip-guarded): empty-`checks()` rejection, mismatched-`responsibility_id` rejection, and the real registry forwarding the exported proposal. Reported as `skipped` here (foreman absent); nothing mirrors the registry locally (Rule 04). |
| 1.5c | `retry_count` never read; "replaces" vs insert-once; README's general veto claim | Design documents insert-once and drops `state.retry_count` (the retry budget belongs to the policy guardrails); the README and the guide state that the veto applies to the **environment-recovery** retry — a provably stagnant worker is retried regardless. |
| 2.1/3.4 | `.foreman/` written without refusal; no Rust CLI test | All three CLIs refuse a `.foreman/` target with exit 2 and write nothing; each suite tests it. Rust gained a CLI test that spawns the binary, validates the three files against the constants and the refusal. |
| 4.4 | Stale per-file counts; wrong "§5.3" pointer | Map counts corrected to the observed values (`gates_test` 50, `provider_resilience` 13, `gates.test` 49, `resilience.test` 17); the pointer now says "the inventory in task 5.3". |
| 5.3 | Map incomplete | Added `foreman.ts` / `foreman.rs`, `foreman.test.ts` (10) / `foreman_test.rs` (8), the `export foreman` bundle filenames and the three fixture names. |
| 5.4 | Promotion path missing the parity review | `docs/integrations/foreman.md` §6 now lists corpus → CLI verdict → MCP tool → tri-runtime parity review. |
| 6.1 | Residual 517★ and present-tense claims | Corrected to 535★ in `SYSTEM_1_5_OPPORTUNITIES.md` (summary + N3) and `docs/NOTORIETY_PR_STRATEGY.md`; the change artifacts describe the correction in the past tense. Also applied the 6.2 improvement (Decision 5 now names the five cited files) and the 1.4 wording fix. |

**Re-verified after the adjustments:** battery green (Python **432** — 4 skipped · TypeScript **99** · Rust **95** = **626**), `openspec validate` valid with zero issues, link check OK (67 external links), the three runtimes still export byte-identical bundles (TOML 1,952 B · class 11,598 B · README 2,813 B), and the `.foreman/` refusal exits 2 in all three.
