# Spec Delta

## Purpose

Defines a safe first native Foreman API-2 integration for `jev-harness`: backward-compatible negotiation, a public sanitized state and observation, structured hook evidence, diagnostic repository metadata, bounded enrichment, a metadata-only diagnostic journal, optional first-turn steering, and honest release/performance gates.

## ADDED Requirements

### Requirement: Backward-compatible API-2 negotiation

The Foreman runtime SHALL support extension API versions 1 and 2. API 2 SHALL preserve the existing extension lifecycle and API-1 responsibility behavior. An API-1 host SHALL reject an API-2 manifest before calling `activate()`, registering contributions, or starting a worker. An API-2 host SHALL accept API-1 extensions unchanged. API-2 modules and singleton construction SHALL be side-effect-free.

#### Scenario: S01 — API-1 host rejects API-2 before activation
- **WHEN** an API-2 extension is discovered by an API-1 host
- **THEN** the host reports an explicit compatibility error, never calls `activate()`, registers no contribution, and starts no worker

#### Scenario: S02 — API-2 host accepts API-1
- **WHEN** an API-2 host loads an API-1 extension without context or enricher support
- **THEN** the existing lifecycle and responsibility behavior remain available

#### Scenario: S03 — API-2 module construction is side-effect-free
- **WHEN** an API-2 entry point is imported and its singleton is constructed before activation
- **THEN** no network call, subprocess, filesystem mutation, log emission, or worker lifecycle action occurs

#### Scenario: S04 — unsupported schema fails before work
- **WHEN** a context or contribution schema version is not supported
- **THEN** Foreman returns a compatibility error before assessment, policy evaluation, or worker start

### Requirement: Public API-2 state and sanitized observation

API 2 SHALL pass responsibilities and enrichers a closed `PublicSupervisionState` rather than raw `FactoryState`. The state SHALL contain deterministic assessment/work-unit/submission/repository references, bounded status/count/elapsed data, optional worker identity, effective host steering state, and bounded error codes. It SHALL contain no raw repository path, data-directory path, digest key, credential, or raw tool/Git payload. The API-2 provider SHALL receive a closed `Api2AssessmentEnvelope` containing the sanitized observation, and the existing `FactoryPolicy` SHALL consume the adapted public result without a second policy path. Private capabilities SHALL be non-serializable and unavailable through the public context.

#### Scenario: S05 — public state excludes raw runtime data
- **WHEN** an API-2 responsibility receives public state
- **THEN** it contains only opaque references, status, counts, bounded elapsed time, optional worker ID/steering budget, and no raw path, worker output, event payload, or credential

#### Scenario: S06 — API-2 provider receives sanitized observation
- **WHEN** semantic assessment runs through API 2
- **THEN** the provider receives only the validated `Api2AssessmentEnvelope` containing `SanitizedObservation`, never raw `FactoryObservation` or raw `FactoryState`; the existing `FactoryPolicy` consumes the adapted public result without a second policy path

#### Scenario: S07 — sanitized observation enforces field limits
- **WHEN** an API-2 observation is constructed
- **THEN** job/output are at most 8,000 UTF-8 bytes each, worker summaries are at most ten items of 2,000 bytes, event summaries are at most thirty items of 2,000 bytes, and test records are at most four items of 4,000 bytes with a 16,000-byte aggregate

#### Scenario: S08 — invalid nested data is rejected
- **WHEN** an observation contains unknown fields, non-JSON values, forbidden raw fields, excessive nesting, or oversized values
- **THEN** the record is rejected or redacted before it reaches a provider, responsibility, event, log, or journal

### Requirement: Structured and redacted hook evidence

Attached API-2 responsibilities SHALL receive a bounded `EventEvidence` object for the current normalized event rather than cumulative `worker.stdout`. The event model SHALL include normalized kind/source, optional client/tool identifiers, redacted bounded tool response, and a truncation flag. This guarantee applies to the API-2 callback/provider boundary; it does not retroactively sanitize API-1 persistence. The persisted `after_tool` compatibility form is an untrusted diagnostic only and carries no current-turn, repository, steering, or lifecycle authority.

#### Scenario: S09 — current PostToolUse event is structured
- **WHEN** a Codex `PostToolUse` event is assessed
- **THEN** the responsibility receives the current event kind, source, tool identifiers, and bounded redacted tool response

#### Scenario: S10 — oversized event is bounded
- **WHEN** serialized event data exceeds 8,000 UTF-8 bytes
- **THEN** the event evidence is bounded and marked truncated before callback delivery

#### Scenario: S11 — event credentials are redacted
- **WHEN** event evidence contains recognized credentials, authorization headers, cookies, private keys, JWTs, URL userinfo, or secret-like key/value fields
- **THEN** every API-2 callback, event diagnostic, provider field, and journal record contains only redacted placeholders or digests

#### Scenario: S12 — direct hook normalization is deterministic
- **WHEN** Python, TypeScript, or Rust receives a supported direct `PostToolUse` payload
- **THEN** all runtimes normalize identical event, output/stderr, exit-code, and repository-binding semantics

#### Scenario: S13 — conflicting fields are rejected
- **WHEN** lifecycle fields conflict or outer/inner integer exit codes disagree
- **THEN** all runtimes return no triage input

#### Scenario: S14 — invalid and successful exits are rejected
- **WHEN** an exit code is boolean, fractional, textual, or zero
- **THEN** all runtimes return no triage input

### Requirement: Diagnostic repository evidence

Foreman SHALL collect repository evidence once per assessment and expose only digest-based metadata. Evidence SHALL distinguish complete, incomplete, stable, unstable, truncated, and untracked states. The collector SHALL use the resolved `HEAD`, status, index diff, worktree diff, and untracked detection with a bounded deadline and neutral Git configuration. Repository evidence is diagnostic only and SHALL never select `STOP_WORKER`, `RETRY_WORKER`, or termination.

#### Scenario: S15 — clean worktree evidence
- **WHEN** all Git reads succeed and no tracked or untracked changes exist
- **THEN** evidence is complete, stable, untracked-free, and has stable digests

#### Scenario: S16 — staged changes are visible
- **WHEN** an index-only tracked change exists
- **THEN** the index diff is represented and the evidence is eligible for diagnostics

#### Scenario: S17 — unstaged changes are visible
- **WHEN** a worktree-only tracked change exists
- **THEN** the worktree diff is represented and the evidence is eligible for diagnostics

#### Scenario: S18 — untracked changes are explicit
- **WHEN** status or untracked detection finds an untracked path
- **THEN** evidence is marked untracked and may be incomplete

#### Scenario: S19 — Git failure is distinct from clean state
- **WHEN** a Git command times out, fails, exceeds its byte limit, or returns invalid output
- **THEN** evidence is incomplete and carries no lifecycle authority

#### Scenario: S20 — non-atomic reads are conservative
- **WHEN** repository state changes between Git reads
- **THEN** evidence is marked unstable or incomplete and is never described as an atomic snapshot

### Requirement: Bounded observation enrichment

API-2 extensions SHALL contribute an `ObservationEnricher` owned by an active responsibility. The CLI and both runtimes SHALL transport configured enrichers. Enrichment SHALL occur before semantic assessment, return only closed records and namespaced data, preserve Foreman-owned evidence, and fail safely.

#### Scenario: S21 — owned enricher runs
- **WHEN** an active responsibility owns a valid enricher
- **THEN** the enricher runs before assessment and its valid record appears in `SanitizedObservation.test_results`

#### Scenario: S22 — inactive enricher is skipped
- **WHEN** the owner responsibility is not active
- **THEN** the enricher is not called and contributes no record or data

#### Scenario: S23 — enrichment limits and namespace are enforced
- **WHEN** enrichers return results
- **THEN** at most two run in contribution order, records and extension data obey their documented bounds, each record source ID equals its registered enricher ID, and unknown/duplicate source IDs are rejected

#### Scenario: S24 — enrichment failure is safe
- **WHEN** an enricher raises, times out, is cancelled, or returns invalid data
- **THEN** existing observation evidence remains, a sanitized degradation diagnostic is emitted, and worker lifecycle continues

### Requirement: Metadata-only diagnostic journal

The native extension SHALL persist best-effort diagnostic records by work unit. Records SHALL contain only opaque identity, sequence, event kind, classification, output/repository digests, normalizer version, generation, and TTL metadata. Journal I/O SHALL be asynchronous, bounded, atomic per record, idempotent on exact replay, and fail open without lifecycle authority.

#### Scenario: S25 — journal stores metadata only
- **WHEN** a diagnostic record is written
- **THEN** no raw output, command, tool response, path, stack trace, credential, or recovery argv is persisted

#### Scenario: S26 — exact replay is idempotent
- **WHEN** the same assessment and semantic record are written again
- **THEN** the journal performs no duplicate append

#### Scenario: S27 — journal failure never changes worker lifecycle
- **WHEN** journal I/O, permissions, locking, validation, timeout, or crash handling fails, including `close()`
- **THEN** the extension emits a sanitized diagnostic, proposes no stop/retry, does not terminate or restart a worker, and does not prevent the host from rendering the normal assessment outcome

#### Scenario: S28 — TTL removes only terminal diagnostics
- **WHEN** an expired work-unit diagnostic directory is cleaned
- **THEN** cleanup removes only validated terminal records, preserves unresolved markers, enforces owner/mode rules, and does not block the event loop

### Requirement: Conservative native directive semantics

`JevTriageResponsibilityV2` SHALL be fixed to `jev.triage` and SHALL return a sequence on every path, with `[]` for abstention. It MAY propose only `STEER_WORKER`. It SHALL never propose `STOP_WORKER` or `RETRY_WORKER`. Foreman's existing policy, worker-health responsibility, and lifecycle controls remain authoritative.

#### Scenario: S29 — first deterministic attached failure steers
- **WHEN** a first direct `after_tool` failure is `env_missing` or `flaky_transient`, `skip_llm` is true, `assertion_failure_critical` is present and false, the public worker is active, `steering_allowed` is true, the effective budget is exactly one, `steer_count=0`, `steering_emitted=false`, and the grace period is not active
- **THEN** the native responsibility proposes `STEER_WORKER` and Foreman renders safe additional context

#### Scenario: S30 — logic regression prevents steering
- **WHEN** `assertion_failure_critical` clears
- **THEN** the native responsibility abstains

#### Scenario: S31 — null or exhausted worker cannot steer
- **WHEN** the public worker ID is null, the worker does not support steering, `steer_count` is nonzero, or `steering_emitted` is true
- **THEN** the native responsibility abstains and no lifecycle target is invented

#### Scenario: S32 — native responsibility never stops or retries
- **WHEN** managed or attached evidence appears stagnant
- **THEN** the native responsibility may record a diagnostic but never proposes `STOP_WORKER`, `RETRY_WORKER`, or termination

#### Scenario: S33 — directive reason is safe
- **WHEN** the native responsibility proposes steering
- **THEN** its reason is bounded and contains no raw output, secret, command, stack trace, or shell string

### Requirement: Native extension packaging and settings

The package SHALL register a `jev` `foreman.extensions` entry point with API version `2`, contribute `jev.triage` and `jev.observation`, import without `foreman` or `pydantic`, and apply a closed validated `NativeSettings` object exactly once. The extension SHALL not add runtime dependencies or execute recovery commands.

#### Scenario: S34 — source import works without Foreman
- **WHEN** the native extension module is imported without Foreman or Pydantic
- **THEN** standard-library fallback types permit source import without I/O

#### Scenario: S35 — built distribution exposes the entry point
- **WHEN** a built wheel is installed in a clean environment
- **THEN** its metadata contains the `jev` entry point and resolves the singleton

#### Scenario: S36 — API-2 activation contributes owned IDs
- **WHEN** a pinned API-2 Foreman host activates the extension
- **THEN** it receives a genuine contribution with `jev.triage`, `jev.observation`, and a real responsibility definition

#### Scenario: S37 — settings are applied once
- **WHEN** valid `NativeSettings` are supplied
- **THEN** the frozen object is applied exactly once to the responsibility and owned enricher, arbitrary keys are rejected, and no second settings source is consulted; steering remains disabled when `steering_enabled` is false or the budget is zero

### Requirement: Repository-scoped configuration and legacy recovery boundary

Python, TypeScript, and Rust SHALL accept an explicit repository root for `.jev.json` discovery and use the same effective `skip_llm` formula. Explicit roots SHALL be canonicalized, existing file paths shall resolve to parents, search shall be limited to four directory levels, and unsafe candidates shall be rejected. `.jev.json` is not a credential boundary. Structured recovery remains legacy-only and is never placed in API-2 provider or journal state.

#### Scenario: S38 — explicit root overrides CWD
- **WHEN** an explicit trusted root contains a different threshold than the process CWD
- **THEN** all runtimes evaluate `skip_llm` with the explicit root threshold

#### Scenario: S39 — missing explicit root uses safe defaults
- **WHEN** an explicit root does not exist or is not a file/directory
- **THEN** triage uses safe defaults and does not fall back to CWD

#### Scenario: S40 — symlink or unsafe candidate is rejected
- **WHEN** a candidate config is a symlink, outside the allowed chain, unsafe owner/mode, non-regular, or oversized
- **THEN** the candidate is ignored without a crash or unsafe read

#### Scenario: S41 — API-2 recovery is not an execution or provider surface
- **WHEN** the native enricher classifies a recoverable failure
- **THEN** it may emit bounded guidance text but no `argv`, shell command, credential, or automatic execution capability enters API-2 provider, event, or journal state

### Requirement: Honest release, rollback, and performance gates

Native support SHALL not be advertised or enabled until a reviewed `foreman-factory` API-2 wheel is published and pinned with exact filename, version, tag, Python version, index/URL, and SHA-256. Rollback SHALL remove the extension configuration and extension-owned journal data while preserving the legacy path. Documentation SHALL distinguish isolated offline heuristics from full Foreman supervision and SHALL not claim end-to-end zero-token, sub-millisecond, measured savings, or automatic lifecycle control.

#### Scenario: S42 — native support is gated on API-2 wheel
- **WHEN** local code runs while Foreman still supports only API 1
- **THEN** the extension is not activated as native and the legacy path remains available

#### Scenario: S43 — rollback restores legacy behavior
- **WHEN** the extension configuration is removed and extension-owned journal data is deleted
- **THEN** Foreman returns to the unchanged legacy path with no broken sessions or residual native contribution

#### Scenario: S44 — performance claims remain scoped
- **WHEN** integration documentation is built
- **THEN** it states that isolated offline heuristics can be provider-free, full Foreman routing/assessment still uses TypeSafe, Git capture is bounded/non-atomic, journal failures are diagnostic, and token savings are unmeasured

#### Scenario: S45 — native path has no lifecycle automation
- **WHEN** any API-2 diagnostic indicates stagnation, incomplete evidence, failed enrichment, or journal failure
- **THEN** the native extension cannot automatically stop, retry, restart, or terminate a worker
