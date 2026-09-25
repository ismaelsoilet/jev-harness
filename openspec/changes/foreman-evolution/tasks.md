# Tasks

## 0. Legacy Freeze

- [ ] 0.1 Freeze `G0_BASELINE_COMMIT=8c3fe0e1f347bb6fe8f20ba69003c88a6af12584` and create a reproducible `legacy-freeze.sha256` manifest before any adapter, fixture, or bundle edit. The manifest lists the legacy-only sections of `src/jev_harness/integrations/foreman_responsibility.py`, `foreman.py`, `packages/ts/src/foreman.ts`, `packages/rust/src/foreman.rs`, `tests/fixtures/foreman_responsibility.toml`, `tests/fixtures/foreman_operator_readme.md`, and `tests/fixtures/foreman_cases.json`; whole files may evolve outside those sections, and the manifest must explicitly mark allowed evolution paths. Hash the committed baseline, not the untracked planning directory. Verify export idempotence, manual registry activation, Python-only recovery, and `.foreman/` refusal.

## 1. Upstream API-2 Contract and Release Gate

- [ ] 1.1 Define the upstream API-2 source contract, repository, branch, provenance, test-double, and pinned-baseline fields; do not require a published wheel for U0.
- [ ] 1.2 Implement API negotiation with two separate tests: the host rejects an API-2 manifest before `activate()`/contribution registration/worker start after discovery, and the JEV module itself passes the side-effect-free import/singleton conformance test. Verify API-2 host/API-1 extension compatibility.
- [ ] 1.3 Define closed API-2 schemas for `PublicSupervisionState`, `EventEvidence`, `SanitizedObservation`, `RepositoryEvidence`, `EnrichmentRecord`, `Api2AssessmentEnvelope`, `PublicAssessmentResult`, and `PrivateExtensionCapabilities`; validate bounds, `extra="forbid"`, nullable worker, and unknown-version rejection.
- [ ] 1.4 Implement side-effect-free API-2 module/singleton construction, deterministic `submission_id`/`assessment_id`/`work_unit_id`/`assessment_sequence` persistence, the `assess_api2(Api2AssessmentEnvelope, checks)` provider seam, and a `FactoryPolicy` adapter that reuses the existing check IDs, probabilities, thresholds, and selection path. Verify raw `FactoryState` cannot reach API-2 callbacks, the wrong provider path is rejected, and missing event identity fails before assessment.
- [ ] 1.5 Add a per-assessment `RepositoryEvidence` collector with resolved `HEAD`, status, index diff, worktree diff, untracked detection, neutral Git configuration, no textconv/external diff, byte/deadline limits, and process-group cleanup; verify clean/staged/unstaged/untracked/ignored/submodule/failure/non-atomic cases.
- [ ] 1.6 Add API-2 enricher registration, transport, configuration-once, owner filtering, namespace validation, and CLI/runtime delivery; verify API-1 compatibility and provider receives only sanitized data.
- [ ] 1.7 Add `RedactionProfile(redaction-v1)` before every API-2 DTO/provider call: reject non-JSON/binary values, redact credential keys/headers/URL userinfo/private keys/JWTs, enforce depth/node/UTF-8 string limits, and test every API-2 sink; verify API-1 persistence is explicitly outside this profile's guarantee.
- [ ] 1.8 Add the minimal U0 fixture/registry and execute the host/test-double subset of S01–S24; explicitly separate upstream host evidence from JEV-component evidence, reject missing, duplicate, orphan, or unexecuted required rows, and do not use a test double as U1 evidence.
- [ ] 1.9 Build and publish the API-2 wheel, record exact filename/version/tag/index/URL/Python/SHA-256, install it outside the checkout with an isolated environment, and run the upstream API-2 suite with an explicit skip allowlist.

## 2. Local `jev-harness` Diagnostic Layer

- [ ] 2.1 Add `foreman_evidence.py` with `JevDiagnosticRecord`, `JevDiagnosticJournal`, and a pure `JevDiagnosticEvaluator`; consume only the private `JournalHandle` from `PrivateExtensionCapabilities`, use opaque work-unit IDs, metadata-only fields, owner-only permissions, and strict bounds.
- [ ] 2.2 Implement a closed `JevDiagnosticRecord` and `JevDiagnosticJournal`: exact replay is a no-op, conflicting replay is a conflict, terminal/cleanup errors are fail-open, and `close()` cannot fail the hook. Verify crash, timeout, stale lock, symlink, permission, cleanup, and late-write cases without lifecycle fields.
- [ ] 2.3 Implement `jev-output-v1` canonical normalization, versioned digest metadata, truncation barriers, and a diagnostic-only repetition report; verify prefix collisions, Unicode, version mixing, input-size limits, and that reports never select lifecycle actions.
- [ ] 2.4 Implement a bounded executor for journal/enricher I/O with cancellation and late-write diagnostics that cannot alter worker lifecycle; verify blocked lock, slow filesystem, timeout, cancellation, crash, restart, and heartbeat behavior.
- [ ] 2.5 Implement `JevForemanObservationEnricher` as the only native enrichment/journal owner; verify redaction, closed records, no recovery argv, no automatic execution, and safe degradation.
- [ ] 2.6 Implement `JevTriageResponsibilityV2` with fixed `jev.triage`, `[]` abstention, optional first deterministic `STEER_WORKER`, null/exhausted-worker vetoes, and no `STOP_WORKER`/`RETRY_WORKER`; verify all directive matrices.

## 3. Cross-Runtime Hook and Configuration

- [ ] 3.1 Implement Python canonical hook normalization with event precedence, nested responses, output/stderr aliases, exit aliases/conflicts, invalid types, trusted repository capability/string, and redaction; run direct and persisted-line tests.
- [ ] 3.2 Implement the exact persisted `after_tool: {...}` compatibility parser with prefix removal, JSON validation, truncation rejection, nested response extraction, and untrusted diagnostic-only behavior; it must never assert current-turn identity, repository binding, steering, or lifecycle authority.
- [ ] 3.3 Port canonical hook parsing to TypeScript and Rust with common fixtures, no new runtime dependencies, and explicit recovery capability divergence; verify all runtime rows.
- [ ] 3.4 Implement Python repository-root discovery with canonicalization, file-parent resolution, missing defaults, four-level search, ownership/mode checks, symlink/outside-target rejection, safe reads, and path-aware cache.
- [ ] 3.5 Port repository-root discovery and the common `skip_llm` formula to TypeScript and Rust; verify threshold, API-2 no-credential/model resolution, and unsafe-path fixtures.

## 4. Native Extension Packaging and Compatibility

- [ ] 4.1 Add `foreman_extension.py` with a side-effect-free API-2 manifest, lazy optional imports, synchronous activation, asynchronous close, no sync/login/logout, genuine API-2 contribution types, and standard-library source-import fallbacks.
- [ ] 4.2 Define the complete `NativeSettings` table (`journal_enabled`, `journal_ttl_seconds`, `journal_max_records`, `steering_enabled`, `max_steers_per_worker`), pass the private host-owned capability, and apply the frozen object exactly once to responsibility and enricher; reject unknown keys.
- [ ] 4.3 Register `foreman.extensions`, validate `jev.triage` and `jev.observation` ownership/namespaces, and verify entry-point loading in source/test-double mode; verify genuine Foreman contribution types only in the U1 pinned-wheel task.

## 5. Fixtures, E2E, Rollback, and Documentation

- [ ] 5.0 **D0 — Pre-U1 documentation safety:** update EN/PT-BR docs, README, and the change status to mark native API-2 unavailable, distinguish `quality.jev-triage` from future `jev.triage`, and remove any claim that a native entry point ships or can be activated. This task runs before U1 and does not require an API-2 wheel.
- [ ] 5.1 Add evolution-specific fixtures without modifying frozen legacy fixtures: common hook/config cases for all runtimes, plus Python/upstream-only sanitized-state, provider, journal, and diagnostic cases; register explicit consumers and capability divergence.
- [ ] 5.2 Add the complete S01–S45 test registry with scenario ID, runtime/lane, test node, command, evidence URI, expected result, and explicit skip policy; reject missing, duplicate, orphan, or unexecuted required rows.
- [ ] 5.3 Run the pinned API-1 negative matrix and the API-2 positive matrix using the same explicit API-2 wheel pin; record package name, filename/version/tag/index/URL/Python/SHA, environment, import paths, and skip allowlist.
- [ ] 5.4 Add managed E2E against the API-2 wheel: sanitized provider payload, public-state callback, enrichment, diagnostic journal, no raw-state reachability, no native stop/retry, no network/worker backend, and policy ownership.
- [ ] 5.5 Add attached Codex E2E across separate processes: first steering, null/exhausted worker, changed/green/incomplete diagnostic cases, persisted-line diagnostic fallback, journal crash/timeout, work-unit reset, and actual hook JSON.
- [ ] 5.6 Add rollback E2E: remove `[extensions."jev"]`, delete extension-owned journal data, verify clean API-1/legacy behavior, no residual native contribution, and preserved sessions.
- [ ] 5.7 **D1 — Post-U1 documentation:** update native API-2 documentation only after U1 and E1 evidence exist; state exact artifact provenance, sanitized/non-atomic evidence, diagnostic-only journal, no lifecycle automation, and unmeasured performance. Run link tests.
- [ ] 5.8 Run strict OpenSpec, the S01–S45 registry check, full Python/TypeScript/Rust/replay suites, clean-room API-1/API-2 wheels, E2E, rollback, concurrency/adversarial tests, and a fresh SureForge review; do not mark native or release-ready until all applicable gates pass.

## Execution Lanes and Gates

Tasks are gated as follows: G0 (`0.1`) → D0 (`5.0`) → U0 (`1.1`–`1.8`) → L1/N1/P1 (`2.*`, `3.*`, `4.*`, allowed against the source/test-double) → U1 (`1.9`) → E1/rollback (`5.1`–`5.6`) → D1 (`5.7`) → final (`5.8`). Native activation, clean-room API-2 tests, real E2E, and release claims require U1.

- **G0 — Legacy freeze:** `0.1` completes before any adapter, fixture, or bundle change.
- **D0 — Pre-U1 docs:** `5.0` runs before U1 and removes any native-availability claim.
- **U0 — Upstream source/test-double:** `1.1`–`1.8` complete against the source contract; no published wheel is required.
- **L1/N1/P1 — Local source/test-double:** `2.*`, `3.*`, and `4.*` may start after U0, but no API-2 real activation is claimed.
- **U1 — API-2 wheel:** `1.9` completes and records the exact artifact before native activation, clean-room API-2 tests, or release claims.
- **L1 — Local diagnostics:** `2.1` → `2.2` → `2.3`; `2.4` precedes `2.5` and `2.6`.
- **N1 — Cross-runtime hooks/config:** `3.1` → `3.2` → `3.3`; `3.4` → `3.5`.
- **P1 — Packaging:** `4.1` → `4.2` → `4.3`.
- **E1 — E2E:** `5.3` precedes `5.4`, `5.5`, and `5.6`; all require U1 for native behavior.
- **D1 — Documentation:** `5.7` marks native unavailable until U1 and follows E1.
- **Final:** `5.8` requires G0, U0, U1, L1, N1, P1, E1, rollback, and D1.

## Traceability IDs

The current spec defines 45 scenarios S01–S45. A slash in a matrix lane (`U0/U1`, `L1/E1`) means both applicable lanes must be run: U0/test-double and U1/E1/pinned-wheel evidence are separate required checks. Every task and test must preserve these IDs; the registry checker rejects missing, duplicate, orphan, or unexecuted required rows.

| ID | Scenario | Test ID | Lane / gate |
|---|---|---|---|
| S01 | API-1 host rejects API-2 before activation | `test_s01_api1_rejects_api2_before_activation` | U0/U1 |
| S02 | API-2 host accepts API-1 | `test_s02_api2_accepts_api1` | U0/U1 |
| S03 | API-2 module construction is side-effect-free | `test_s03_api2_module_construction_is_side_effect_free` | U0 |
| S04 | unsupported schema fails before work | `test_s04_unsupported_schema_fails_before_work` | U0/U1 |
| S05 | public state excludes raw runtime data | `test_s05_public_state_excludes_raw_runtime_data` | U0 |
| S06 | API-2 provider receives sanitized observation | `test_s06_api2_provider_receives_sanitized_observation` | U0/E1 |
| S07 | sanitized observation enforces field limits | `test_s07_sanitized_observation_enforces_field_limits` | U0/E1 |
| S08 | invalid nested data is rejected | `test_s08_invalid_nested_data_is_rejected` | U0/E1 |
| S09 | current PostToolUse event is structured | `test_s09_current_posttooluse_event_is_structured` | U0 |
| S10 | oversized event is bounded | `test_s10_oversized_event_is_bounded` | U0 |
| S11 | event credentials are redacted | `test_s11_event_credentials_are_redacted` | U0/E1 |
| S12 | direct hook normalization is deterministic | `test_s12_direct_hook_normalization_is_deterministic` | N1 |
| S13 | conflicting fields are rejected | `test_s13_conflicting_fields_are_rejected` | N1 |
| S14 | invalid and successful exits are rejected | `test_s14_invalid_and_successful_exits_are_rejected` | N1 |
| S15 | clean worktree evidence | `test_s15_clean_worktree_evidence` | U0/E1 |
| S16 | staged changes are visible | `test_s16_staged_changes_are_visible` | U0/E1 |
| S17 | unstaged changes are visible | `test_s17_unstaged_changes_are_visible` | U0/E1 |
| S18 | untracked changes are explicit | `test_s18_untracked_changes_are_explicit` | U0/E1 |
| S19 | Git failure is distinct from clean state | `test_s19_git_failure_is_distinct_from_clean_state` | U0/E1 |
| S20 | non-atomic reads are conservative | `test_s20_non_atomic_reads_are_conservative` | U0/E1 |
| S21 | owned enricher runs | `test_s21_owned_enricher_runs` | U0/E1 |
| S22 | inactive enricher is skipped | `test_s22_inactive_enricher_is_skipped` | U0/E1 |
| S23 | enrichment limits and namespace are enforced | `test_s23_enrichment_limits_and_namespace_are_enforced` | U0/E1 |
| S24 | enrichment failure is safe | `test_s24_enrichment_failure_is_safe` | U0/E1 |
| S25 | journal stores metadata only | `test_s25_journal_stores_metadata_only` | L1/E1 |
| S26 | exact replay is idempotent | `test_s26_exact_replay_is_idempotent` | L1/E1 |
| S27 | journal failure never changes worker lifecycle | `test_s27_journal_failure_never_changes_worker_lifecycle` | L1/E1 |
| S28 | TTL removes only terminal diagnostics | `test_s28_ttl_removes_only_terminal_diagnostics` | L1/E1 |
| S29 | first deterministic attached failure steers | `test_s29_first_deterministic_attached_failure_steers` | L1/E1 |
| S30 | logic regression prevents steering | `test_s30_logic_regression_prevents_steering` | L1/E1 |
| S31 | null or exhausted worker cannot steer | `test_s31_null_or_exhausted_worker_cannot_steer` | L1/E1 |
| S32 | native responsibility never stops or retries | `test_s32_native_responsibility_never_stops_or_retries` | L1/E1 |
| S33 | directive reason is safe | `test_s33_directive_reason_is_safe` | L1/E1 |
| S34 | source import works without Foreman | `test_s34_source_import_works_without_foreman` | P1 |
| S35 | built distribution exposes the entry point | `test_s35_built_distribution_exposes_entry_point` | P1 |
| S36 | API-2 activation contributes owned IDs | `test_s36_api2_activation_contributes_owned_ids` | U1/P1 |
| S37 | settings are applied once | `test_s37_settings_are_applied_once` | P1 |
| S38 | explicit root overrides CWD | `test_s38_explicit_root_overrides_cwd` | N1 |
| S39 | missing explicit root uses safe defaults | `test_s39_missing_explicit_root_uses_safe_defaults` | N1 |
| S40 | symlink or unsafe candidate is rejected | `test_s40_symlink_or_unsafe_candidate_is_rejected` | N1 |
| S41 | API-2 recovery is not an execution or provider surface | `test_s41_api2_recovery_is_not_execution_or_provider_surface` | L1/P1 |
| S42 | native support is gated on API-2 wheel | `test_s42_native_support_is_gated_on_api2_wheel` | U1 |
| S43 | rollback restores legacy behavior | `test_s43_rollback_restores_legacy_behavior` | E1 |
| S44 | performance claims remain scoped | `test_s44_performance_claims_remain_scoped` | D1 |
| S45 | native path has no lifecycle automation | `test_s45_native_path_has_no_lifecycle_automation` | L1/E1 |

The registry checker must verify every S-ID has at least one executed test in its declared lane, that cross-runtime scenarios have the required Python/TypeScript/Rust instances, and that no test claims to substitute a test double for U1.
