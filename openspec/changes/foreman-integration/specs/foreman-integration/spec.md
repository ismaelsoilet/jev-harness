# Spec Delta

## Purpose

Provides native no-new-dependency integration between jev-harness and thruwire/foreman autonomous factories: structured test observations that can fill Foreman's `FactoryObservation.test_results` once the upstream seam lands, deterministic stagnation evidence for worker-health decisions, an operator preset with its companion responsibility class, and an export command — across the Python, TypeScript and Rust runtimes under an explicit capability matrix, where each runtime follows its own naming convention (`extract_test_results` / `extractTestResults`).

## ADDED Requirements

### Requirement: Foreman Triage Extraction

The system SHALL provide `ForemanTriageObserver.extract_test_results(stdout, stderr="", repo_root=None, client=None)` in the Python, TypeScript and Rust runtimes (TypeScript exports `extractTestResults` per that runtime's convention). It SHALL return an empty list or exactly **one** record per log (the triage engine classifies a log, not individual failures), directly assignable to Foreman's `FactoryObservation.test_results: list[dict[str, Any]]`, using the triage vocabulary (`category`, `severity_score`, `confidence`, `skip_llm`, `action_recommendation`, `is_mock`, `degraded_reason`) plus `assertion_slice` and `foreman_schema_version`. `recovery` SHALL be populated in Python only. It SHALL NOT perform network I/O unless a caller injects a live client.

#### Scenario: Deterministic missing dependency failure

- **WHEN** stdout/stderr contains `ModuleNotFoundError: No module named 'requests'`
- **THEN** the system returns one record with `category: "env_missing"`, `skip_llm: true`, and (in Python) `recovery.argv` as a list with `recovery.is_safe_auto_run: false`.

#### Scenario: Passing test output returns empty list

- **WHEN** the output indicates tests passed without failure classifications
- **THEN** the system returns an empty list.

#### Scenario: Assertion slice extraction

- **WHEN** the output contains a pytest or unittest assertion failure
- **THEN** `assertion_slice` carries the root-cause assertion line truncated to at most 500 characters, and redundant traceback lines are discarded.

#### Scenario: Repository-scoped recovery evaluation

- **WHEN** `repo_root` is provided
- **THEN** `recovery.rationale` and `recovery.is_safe_auto_run` are evaluated against that repository's manifests, not against the process working directory.

#### Scenario: No invented classification vocabulary

- **WHEN** any record is produced
- **THEN** `category` is one of `env_missing`, `flaky_transient`, `syntax_trivial`, `test_redundant`, `deep_logic`, `no_failure`, never an invented label such as `MISSING_DEPENDENCY`.

### Requirement: Deterministic Stagnation Evidence for Foreman

The system SHALL provide `ForemanCircuitBreaker.evaluate_worker_health(snapshots, window=5)` in the three runtimes, where each snapshot is `{"output": str, "diff": str | null}` and returns `{"should_abort": bool, "reason": str, "evidence": {...}}` computed only from its arguments (no network, no filesystem, no clock). It SHALL use only evidence Foreman actually produces (latest worker output; `git_diff` / `changed_files`), never a structured command history. The fingerprint algorithm is runtime-local (Python `hashlib`, TypeScript `node:crypto`, Rust a standard-library comparison or hasher) and is never part of the contract — only the equality verdict is. The verdict is advisory evidence for Foreman's own policy, never an order.

#### Scenario: Stagnant output and diff trigger abort evidence

- **WHEN** the normalized output fingerprint and the diff fingerprint are both identical across the last `window` snapshots
- **THEN** the system returns `should_abort: true` with `reason: "STAGNANT_EVIDENCE"`.

#### Scenario: Healthy forward progress allows continuation

- **WHEN** either the output fingerprint or the diff fingerprint changes within the window
- **THEN** the system returns `should_abort: false`.

#### Scenario: Missing signal declines to judge

- **WHEN** no snapshot in the window carries a diff (`diff: null`)
- **THEN** the system returns `should_abort: false` with `evidence.complete_signals: false`, and never treats a single signal as sufficient.

#### Scenario: Insufficient history never triggers

- **WHEN** fewer than `window` snapshots are supplied
- **THEN** the system returns `should_abort: false` with `evidence.insufficient_history: true`.

### Requirement: Foreman Responsibility Preset

The system SHALL expose `FOREMAN_RESPONSIBILITY_TOML` — a TOML document using only keys Foreman v0.3.0 accepts (`enabled`, `always`, `routing_instructions`, `routing_threshold`, `[checks.<id>]` with `instructions`/`min_threshold`, `[settings]`) — and SHALL state in its exported header that the preset only configures an **installed** responsibility implementation and that foreman exits with `ResponsibilityConfigError` when the companion class is absent.

#### Scenario: Valid, Foreman-parseable definition

- **WHEN** the preset is parsed as TOML
- **THEN** it yields `enabled`, `always = false`, `routing_instructions`, `routing_threshold`, and `checks.deterministic_recovery_available` plus `checks.assertion_failure_critical`, each with `instructions` and `min_threshold`.

#### Scenario: Honest operator header

- **WHEN** the preset is exported
- **THEN** its header names the companion class file, the `--responsibilities-dir` / `FOREMAN_RESPONSIBILITIES_DIR` activation, and the hard startup failure that occurs without the class.

#### Scenario: Canonical identity across runtimes

- **WHEN** each runtime's `FOREMAN_RESPONSIBILITY_TOML` constant is compared with `tests/fixtures/foreman_responsibility.toml`
- **THEN** the three constants are byte-identical to the canonical fixture.

### Requirement: Companion Responsibility Reference

The system SHALL export a reference responsibility class implementing the full Foreman `Responsibility` surface — `id`, `checks()` (the registry calls it unconditionally), `route()`, `directives(state, result)`, `configured(settings)` and `configured_checks(checks)` — which consumes the adapter surface without network access by default.

#### Scenario: Sealed directives only

- **WHEN** the class proposes a directive
- **THEN** the action is one of Foreman's sealed set (`CONTINUE`, `START_WORKER`, `START_VERIFIER`, `STEER_WORKER`, `STOP_WORKER`, `RETRY_WORKER`, `FINISH`, `ESCALATE`) and the proposal carries a deterministic `reason` that is **audit evidence** — Foreman's steering text is built from check probabilities, so the reason must not be described as reaching the worker.

#### Scenario: Deterministic given the same inputs

- **WHEN** the class is invoked twice with the same `(state, result)`
- **THEN** it proposes the same directive with the same priority and confidence — its evidence window is keyed by `(run_id, iteration)`, so re-evaluating an assessment never appends a second entry (insert-once).

#### Scenario: No evidence, no proposal

- **WHEN** there is no worker output to triage or the evidence window is incomplete
- **THEN** the class proposes nothing (the policy falls back to `CONTINUE`) rather than guessing.

### Requirement: CLI Scaffolding for Foreman Operators

`jev-harness export foreman` SHALL exist in all three runtimes and write `quality.jev-triage.toml`, `quality_jev_triage.py` and `README.md` into `--out-dir` (default `./foreman-responsibilities/`), creating parent directories as needed. It SHALL NOT write into a managed repository's `.foreman/` run-state directory.

#### Scenario: Exporting the operator bundle

- **WHEN** the user runs `jev-harness export foreman`
- **THEN** the system creates the three files under `./foreman-responsibilities/` and exits `0`, printing the activation hint.

#### Scenario: README names both failure modes

- **WHEN** the bundle is exported
- **THEN** the README states that the directory and the class must always ship together and names both errors verbatim: `installed responsibility has no central configuration: quality.jev-triage` (class without the central TOML) and `configuration has no installed responsibility implementation: quality.jev-triage` (TOML without the class), both exiting with code 2.

#### Scenario: Idempotent re-export

- **WHEN** the command runs twice with unchanged inputs
- **THEN** the second run leaves all three files byte-identical.

#### Scenario: Never targets run state

- **WHEN** `--out-dir` is omitted
- **THEN** the resolved directory is `./foreman-responsibilities/`, never a managed repository's `.foreman/`.

### Requirement: Capability Matrix and Tri-Runtime Parity

The system SHALL document and test a capability matrix, and the three runtimes SHALL produce identical results on the shared golden fixtures for every field in that matrix.

#### Scenario: Shared fixture produces identical verdicts

- **WHEN** each runtime evaluates every case in `foreman_cases.json`
- **THEN** the common fields (`category`, `skip_llm`, `action_recommendation`, `should_abort`, `reason`, `assertion_slice`) match exactly — under each runtime's naming convention — and the numeric fields (`severity_score`, `confidence`) match within 1e-9.

#### Scenario: Declared divergence is explicit, never accidental

- **WHEN** the TS and Rust runtimes produce a record
- **THEN** `recovery` is `null` and a test asserts this declared divergence against the documented capability matrix (Python: present; TS/Rust: `null` until E3.6 is ported).

#### Scenario: Surface completeness

- **WHEN** a runtime does not export `extract_test_results`, `evaluate_worker_health`, `FOREMAN_RESPONSIBILITY_TOML` or the exported class/TOML pair
- **THEN** the parity test for that runtime fails.

### Requirement: Zero External Dependencies Invariant

The integration SHALL add no new dependency to any runtime and SHALL NOT require `pydantic` or `foreman` in any runtime: Python uses only the standard library and existing internals, TypeScript adds no runtime dependency, and Rust uses only crates already declared in `Cargo.toml`. Optional validation against Foreman's Pydantic model MUST skip when those packages are unavailable.

#### Scenario: Clean standard library import

- **WHEN** `jev_harness.integrations.foreman` is imported in a minimal environment lacking `pydantic` and `foreman`
- **THEN** the import succeeds without raising `ImportError` or `ModuleNotFoundError`.

#### Scenario: Stdlib-only test battery

- **WHEN** the integration test suites run on a machine without Foreman installed
- **THEN** they pass, and tests requiring Foreman's model report `skipped`, never failed.
