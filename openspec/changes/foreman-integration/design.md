# Design: Native Foreman Integration in Jev Harness

## Context

[thruwire/foreman](https://github.com/thruwire/foreman) (v0.3.0, 535★, inspected 2026-09-23) coordinates multi-turn autonomous software engineering tasks, supervising coding workers (`Codex`, `OpenCode`) with TypeSafe Jev System One micro-decisions.

**Verified properties of Foreman (primary sources, 2026-09-23):**

1. `FactoryObservation.test_results: list[dict[str, Any]]` is real and `ObservationBuilder.build()` hardcodes `test_results=[]` (`observation.py`).
2. Verifier output is stored as a raw tail: `summary=(record.stdout or record.stderr)[-output_limit:]`, default 12,000 chars (`runtime.py`).
3. Worker stagnation is detected **only** semantically — `worker_stuck` is one Noul at `min_threshold = 0.80` (`core.worker-health.toml`), and Foreman's README warns that uncalibrated semantic scores produce both false positives and false negatives.
4. Responsibility configuration is central to the installation; `.foreman/` in a managed repository is run state (`docs/routing.md`, `README.md`).
5. A TOML configures an **installed** class; a TOML without one is a hard startup error: `configuration has no installed responsibility implementation: <id>` (`configuration.py`).
6. Extension points: `ResponsibilityRegistry`, `directives(state, result)`, the sealed directive set, plus `configured(settings)` / `configured_checks(checks)` required of additional implementations (`policy.py`, `configuration.py`).
7. `configured_registry(..., additional=[...])` accepts third-party classes, but the stock `foreman run` CLI passes no `additional=` (`cli.py`) — loading a class today needs a Foreman-side patch or a custom launcher.
8. The **only** state channel into the Jev prompt is the observation (`jev.py`: `state=observation.model_dump(mode="json")`); responsibilities contribute question instructions only.
9. `test_results` is **additive**: `latest_worker_output` keeps its raw 12,000-char tail, so the field adds structure and tokens rather than replacing tokens.

**Corrections applied since the first draft (2026-09-23):** the draft's `triage_failure()`, `check_abort()` (<100µs "edit entropy"), `latency_us` and shell-string `suggested_recovery` do not exist; the triage control flow is binary, not ambiguity-gated (Decision 2); the delivery target was wrong (Decision 4); the token-saving claim was inverted (see §Risks and proposal fact 10).

**Adversarial pass (2026-09-23) — what it changed:** A1 capability matrix (parity cannot include `recovery` today) → Decision 1/7; A2 cwd/config determinism → Decision 2; A3 `total_failures` unimplementable → Decision 1; A4 breaker inputs absent in Foreman → Decision 3 rewritten; A5 the adapter is inert and the companion class was unspecified → Decisions 5/6; A6 additive token effect → Risks; A7 default-offline means heuristic verdicts → Decision 2; A8 stdout/stderr concatenation edge cases and A9 nested CLI/byte identity → Tasks. The full table lives in `explore.md` §7.

## Goals / Non-Goals

**Goals:**

- `extract_test_results(stdout, stderr="", repo_root=None, client=None)` — one record per log, triage vocabulary, offline by default, `recovery` in Python.
- `evaluate_worker_health(snapshots, window=5)` — deterministic stagnation evidence built from what Foreman actually produces.
- `FOREMAN_RESPONSIBILITY_TOML` + an exported **companion responsibility class** that makes the preset executable.
- `jev-harness export foreman` writing the three-file operator bundle to an operator directory.
- Shared fixtures locking the capability matrix across Python, TypeScript and Rust.
- Zero external dependencies in every runtime.

**Non-Goals:**

- Modifying `thruwire/foreman` in this phase; porting E3.6 `recovery` to TS/Rust now; command-cycle detection; core-gate/MCP promotion of the breaker; writing into a managed repository's `.foreman/`.

## Decisions

### Decision 1: One vocabulary plus a declared capability matrix

- **Choice:** records reuse the triage vocabulary (`category`, `severity_score`, `confidence`, `skip_llm`, `action_recommendation`, `recovery`, `is_mock`, `degraded_reason`); exactly two adapter-level keys are added — `assertion_slice` (from `perception.find_assertion_line`, truncated to 500 chars) and `foreman_schema_version: 1`. One record per log; `total_failures` and the multi-failure cap are **dropped** (the engine classifies a log, not individual failures; A3).
- **Capability matrix (declared, tested, never accidental):**

| Field | Python | TypeScript | Rust |
| :--- | :--- | :--- | :--- |
| `category`, `skip_llm`, `confidence`, `severity_score`, `action_recommendation` | yes | yes | yes |
| `assertion_slice` | yes (`perception`) | yes (ported in this change) | yes (ported in this change) |
| `recovery` (E3.6) | yes | `null` (declared divergence; follow-up port) | `null` (declared divergence) |

- **Rationale:** `recovery` and perception were never mirrored (they are Python-only today), so promising strict parity would ship a false claim. Declaring the divergence keeps the parity tests meaningful for everything else.

### Decision 2: Accurate control flow, deterministic by default, repository-scoped

- **Choice:** default to the offline engine (`JevClient(force_mock=True)`), accept an injected live client, and accept `repo_root` which is forwarded to `build_recovery`.
- **Actual control flow** (`client.system_one`): offline deterministic heuristics without credentials or with `force_mock`; provider (70–300ms, cached) with credentials. The only pre-engine deterministic checks are the green-run short-circuit and the injection guard. There is no ambiguity-gated escalation.
- **Determinism caveats (A2), documented in the adapter:** `load_repo_config()` resolves `.jev.json` by walking up from the **process CWD** (4 levels), so `skip_llm_threshold` — and therefore `skip_llm` — can vary with the Foreman process's working directory; `build_recovery` likewise defaults to `Path.cwd()`. Passing `repo_root` fixes the recovery side; the config side cannot be pinned by a caller today and is disclosed as a known limitation (fixtures run under a controlled CWD).
- **A7 trade-off:** the default path reports `is_mock: true` — the supervisor consumes heuristic verdicts, not Jev ones. Live mode would add one provider call per assessment (~12/min at the 5s debounce floor). Offline is the deliberate default; it is documented, not hidden.

### Decision 3: `ForemanCircuitBreaker` — deterministic stagnation evidence from available evidence

- **Choice:** `evaluate_worker_health(snapshots, window=5)` where each snapshot is `{"output": str, "diff": str | null}` (newest last), returning `{"should_abort": bool, "reason": str, "evidence": {...}}`.
- **Signals:** (1) normalized-output fingerprint — collapse whitespace and drop volatile tokens (timestamps, durations, line numbers, temp paths, hex digests); (2) diff fingerprint — the (possibly truncated) diff, or `null`. The fingerprint algorithm is a **runtime-local implementation detail, never part of the contract**: Python uses `hashlib.sha256`, TypeScript `node:crypto` (a Node builtin, not a dependency), and Rust compares the normalized strings directly or uses a standard-library hasher — because only *equality inside one process* matters, and the parity fixture compares `should_abort`/`reason`, never a hex value (B1). Abort only when **both** fingerprints are identical across the whole window (`reason: "STAGNANT_EVIDENCE"`). If no snapshot carries a diff, the breaker **declines** (`complete_signals: false`) rather than judging on one signal; fewer than `window` snapshots → `insufficient_history: true`.
- **Why not commands (A4):** Foreman exposes no structured command history — only output tails and a bounded `git_diff`. A command-repetition signal would be inert in practice and would encourage fragile parsing of worker text. Recorded as a future opportunity if Foreman ever surfaces commands.
- **Rejected:** "normalized edit entropy" as the primary signal (needs calibration data we do not have; frequency ratios flag legitimate fix-and-retry cycles), and single-signal aborting (safety: one signal is not enough to recommend stopping a worker).
- **Composition:** advisory evidence for Foreman's policy; jev-harness never decides to stop a worker (`SYSTEM_1_5_OPPORTUNITIES.md` §3.1 item 5).

### Decision 4: Delivery is an operator bundle, not a repository artifact

- **Choice:** `export foreman` writes `quality.jev-triage.toml`, `quality_jev_triage.py` and `README.md` into `--out-dir` (default `./foreman-responsibilities/`).
- **Rationale:** configuration is central (fact 4); the class is mandatory (fact 5); and the operator needs to know both. The README states the two activation paths: (a) patch/pass `additional=[JevTriageResponsibility()]` to `configured_registry` (or register it in `builtin_registry`), or (b) wait for the upstream registration. It names **both** failure modes and that the directory and the class always ship together (B5): class without the central TOML → `ResponsibilityConfigError: installed responsibility has no central configuration: quality.jev-triage`; TOML without the class → `ResponsibilityConfigError: configuration has no installed responsibility implementation: quality.jev-triage` — both exit code 2.
- **Rejected:** writing into `<repo>/.foreman/` (fact 4); the draft's `.foreman/hooks/triage_observer.py` (no hooks mechanism); shipping the TOML alone (facts 5/8 make it actively harmful); a companion installable package (6th release channel outside quad-sync — deferred).

### Decision 5: The upstream patch is specified now, proposed later

- **Choice:** document the minimal upstream change; do not fork.
- **Draft, in three parts:**
  1. `observation.py`: an optional `test_results_provider: Callable[[FactoryState], list[dict[str, Any]]] | None` on `ObservationBuilder`, used where `test_results=[]` is hardcoded. No model change needed (the inner `list[dict[str, Any]]` accepts arbitrary keys; `extra="forbid"` applies to top-level fields only) — and this is the only seam that reaches the Jev prompt (fact 9).
  2. A `quality.jev-triage` responsibility: the TOML this change ships plus a `JevTriageResponsibility` class implementing `checks()`, `route()`, `directives`, `configured` and `configured_checks`, reading `min_threshold` from its bound check. The registry calls `checks()` unconditionally and raises `ValueError("responsibility <id> has no checks")` when empty.
  3. **Registration (fact 7/8):** the PR must let stock `foreman run` load the class — either by registering it in `builtin_registry` or by teaching the CLI/environment an `additional` source. Without this, the TOML alone is a hard error.
- **Rationale:** the adapter is inert for stock Foreman until part 1 lands (facts 1/9); the PR #22 bar is "code, tests, and neutral documentation", so the draft carries code shapes, not claims. The five cited files are `observation.py` (the seam), `configuration.py` (the class contract and the two error paths), `cli.py` (registration), `jev.py` (the prompt channel) and `policy.py` (directive ranking and guardrails).

### Decision 6: Companion responsibility contract (the piece that makes the preset real)

- **Choice:** the exported class is a small, deterministic reference implementation:
  - **Identity:** `id = "quality.jev-triage"` (must equal the TOML stem); implements the full `Responsibility` surface — `checks()`, `route()`, `directives(state, result)`, `configured(settings)`, `configured_checks(checks)`. `checks()` must return the configured checks: `ResponsibilityRegistry` calls it unconditionally and raises `ValueError("responsibility <id> has no checks")` when empty. Every proposed directive must carry `responsibility_id = "quality.jev-triage"`: the registry raises `ValueError` on a mismatch.
  - **Reads:** `state.workers[-1]` output (bounded by the worker's `output_limit`), `state.repository`, `state.iteration`, `state.run_id`, and its own check probabilities from `result` (the retry budget belongs to Foreman's policy guardrails, not to this class).
  - **Window:** an in-memory ring buffer **keyed by `(run_id, iteration)`**: an already-seen iteration keeps its single entry (insert-once), so one assessment is never double-counted and identical inputs yield identical proposals (B4). The diff fingerprint comes from a bounded `git -C <repository> diff --no-ext-diff` collected through an **injectable runner** (default `subprocess.run(..., timeout=<settings.diff_timeout_seconds>)`, 5s by default to mirror the observer). Because `directives()` is synchronous on Foreman's event loop, the call carries a **hard timeout and is fail-open**: on timeout or missing git the diff fingerprint is `null`, the breaker declines (`complete_signals: false`), and the class abstains — it never stalls the loop **beyond `diff_timeout_seconds` plus the child's teardown**, i.e. it is a bounded blocking call and not a non-blocking one (D1), the stall the observer's async `ObservationBuilder._git` avoids entirely with `asyncio.wait_for(timeout=5.0)` (C2). State is lost on restart → the window is incomplete → the class declines to propose (safe).
  - **Proposals (never outside the sealed set):** `RETRY_WORKER` with a deterministic `reason` when (a) the breaker returns `should_abort` (stagnation) or (b) triage returns `skip_llm: true` for an environmentally-classified failure; it abstains until the window holds `window` assessments (restart safety) and whenever the triage record is insufficient. The `reason` is **audit evidence only**: Foreman builds the worker steering text from check probabilities (`foreman/steering.py`), never from a directive's reason, so the class must not be described as instructing the worker — delivering an instruction would need a separate upstream change (recorded as a future opportunity, not part of this draft).
  - **Gating by its own checks:** proposals require the corresponding Jev check (`deterministic_recovery_available` / `assertion_failure_critical`) to clear its `min_threshold`; the Jev probability gates the deterministic action.
  - **Priorities:** the packaged directives use an explicit numeric scale: safety-critical runtime directives sit in the high band (the runtime iteration-limit is `950`; neutral `CONTINUE` is `0` — `policy.py`), so the class's directive must sit **below** the safety-critical ones and above `CONTINUE`. Exact value calibrated at implementation against the packaged definitions. Retry is bounded by `max_retries=1` / `max_workers=3` and may be upgraded to `ESCALATE` by the policy guardrails.
  - **No network by default** (offline engine); never raises into the factory loop (fail-open, degrade to no proposal).
- **Rationale:** without this contract the exported TOML has no runtime behaviour, the breaker has no caller, and the "how it works in practice" story is undefined. The class's influence is the directive choice; its reason is observable in `FOREMAN_INTERVENED` events and `foreman inspect`.

### Decision 7: Parity is scoped by the capability matrix and locked by fixtures

- **Choice:** `tests/fixtures/foreman_cases.json` + `tests/fixtures/foreman_responsibility.toml` drive identical assertions in the three runtimes: exact match for `category`/`skip_llm`/`action_recommendation`/`should_abort`/`reason`/`assertion_slice` (under each runtime's naming convention), 1e-9 for `severity_score`/`confidence`, `recovery is null` asserted in TS/Rust, byte identity for the TOML constant.
- **Rationale:** category parity already has a real mechanism (the 112-case corpus + `triage_parity` tests); this change extends the same pattern to the adapter surface and makes the Python-only `recovery` explicit instead of accidental.

### Decision 8: Foreman-schema validation is opt-in, never a dependency

- **Choice:** the optional test validating records against Foreman's Pydantic model is guarded (`skipUnless(foreman importable)`); the suite stays stdlib-only and green without Foreman.
- **Rationale:** the first draft required Pydantic validation and a stdlib-only suite simultaneously; skipping is reported as `skipped`, never as passed.

## Risks / Trade-offs

- **[Risk] False positives stop useful workers.** Foreman's own documented limitation.
  - *Mitigation:* require both fingerprints (Decision 3), decline on incomplete signals, advisory-only output, priorities below safety directives.
- **[Risk] The exported TOML without the class breaks Foreman.** Verified hard error (fact 5).
  - *Mitigation:* explicit header + README + a test asserting the header contains the warning; never ship the TOML alone.
- **[Risk] `skip_llm` varies with the Foreman process CWD.** `load_repo_config()` walks up from CWD (A2).
  - *Mitigation:* `repo_root` covers `recovery`; the config caveat is documented; fixtures run under a controlled CWD; a config-pin override is recorded as a future core task.
- **[Risk] Token effect is additive, not a saving.** Adding records increases the observation; the raw tail remains (fact 9).
  - *Mitigation:* position the value as structure + preserved assertion line + machine-actionable recovery; do not claim token savings; a tail-replacement change is a separate upstream discussion.
- **[Risk] The companion class is unverified against a live Foreman** (no foreman install in this repo).
  - *Mitigation:* implement against the documented API shapes, keep the class fail-open, and re-verify line/file references before the upstream PR; dogfood before proposing upstream.
- **[Risk] Stale claims elsewhere in the repository.** The interop table recorded 517★ while the repository showed 535★ (both 2026-09-23); task 6.1 corrected it during implementation.
  - *Mitigation:* the dated-source rule (`tests/test_docs_links.py`) keeps the corrected table honest; re-verify after 2026-10-23.

## Rejected alternatives (summary)

| Alternative | Why rejected |
| :--- | :--- |
| Pydantic model coupling / importing `foreman` | Breaks the zero-dependency invariant in every runtime |
| Second vocabulary (`classification`, `root_cause`, `latency_us`, shell-string recovery) | Splits corpus/parity, contradicts E3.6, no source of truth |
| Writing into a managed repo's `.foreman/` or inventing `hooks/` | Contradicts Foreman's configuration model |
| Command-cycle detection in v1 | Foreman exposes no command history; would be inert (A4) |
| Porting E3.6 `recovery` to TS/Rust now | Pre-existing parity gap, not created here; declared in the matrix with a follow-up |
| Breaker as a core gate (CLI verdict + MCP + corpus) | Large parity/corpus cost before the signal is proven; promotion path in Tasks §5.4 |
| Companion installable package in this change | New release channel outside quad-sync; depends on upstream acceptance |
