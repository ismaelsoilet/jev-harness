# Design: Safe Native Foreman Evidence Integration

## Context

The current `foreman-integration` adapter can classify worker output and detect repeated raw evidence, but the published Foreman responsibility protocol exposes only `FactoryState` and bounded cumulative output. It cannot prove which tool payload or repository snapshot belonged to each historical assessment, so reconstructing attached-session stagnation from `worker.stdout` would be unsound.

The inspected upstream baseline is `thruwire/foreman@ba91849e7088f072db491c739e4c81fd9a4c8154` (`foreman-factory` 0.3.0, inspected 2026-09-25). It supports extension API 1 only. The API-2 contract below is an upstream change. G0/D0/U0 and local source/test-double work may begin without an API-2 wheel; native activation, real E2E, and release claims remain blocked until a reviewed API-2 wheel is published and pinned.

The legacy `quality.jev-triage` implementation and exported bundle remain untouched.

## Goals / Non-Goals

**Goals:**

- Preserve API-1 extensions, API-1 responsibilities, attached sessions, and the legacy operator bundle.
- Give API-2 extensions a closed public state, sanitized observation, namespaced enrichment, and explicit identity.
- Keep Foreman's existing `FactoryPolicy` as the sole directive selector.
- Persist best-effort diagnostic metadata without lifecycle authority.
- Make repository evidence bounded and explicitly non-atomic.
- Permit at most one native steering proposal per attached work unit.

**Non-Goals:**

- Native automatic `STOP_WORKER`, `RETRY_WORKER`, restart, or termination.
- A native lifecycle ledger or exactly-once action guarantee.
- Reconstructing Git history from `worker.stdout`.
- Sanitizing all API-1 Foreman persistence.
- Executing recovery `argv` or putting recovery commands in API-2 provider state.
- Claiming end-to-end zero-token, sub-millisecond, or measured savings.

## Decisions

### Decision 1: Gated API-2 contract

API 2 extends the current lifecycle. An API-2 host accepts API-1 extensions unchanged. An API-1 host may load an API-2 entry point for manifest discovery, but rejects it before `activate()`, contribution registration, or worker start. The JEV module separately requires side-effect-free import and singleton construction; this is a JEV conformance test, not a sandbox guarantee for arbitrary extensions.

The execution lanes are explicit:

- G0: freeze the committed legacy baseline.
- D0: correct public documentation so native API-2 is described as unavailable.
- U0: define and test the upstream source contract with a test double.
- L1/N1/P1: implement local evidence, hooks/config, and packaging against U0.
- U1: publish and pin a real API-2 wheel.
- E1/D1/Final: real-wheel E2E, final documentation, and release verification.

### Decision 2: Closed identity, public state, envelope, and result models

API 2 defines closed models with `extra="forbid"`. Raw `FactoryState`, `WorkerRecord`, raw stdout/stderr, raw paths, raw Git output, and raw tool payloads are never passed to API-2 callbacks.

`PublicSupervisionState` contains only:

- opaque `run_ref`, `work_unit_id`, `submission_id`, `assessment_id`, `assessment_sequence`, `repository_id`, and `repository_binding_digest`;
- mode, iteration, bounded status/count/elapsed values;
- optional bounded `worker_id`;
- effective host steering state: active worker, `supports_steering`, `steering_allowed`, `max_steers_per_worker`, `steer_count`, `steering_emitted`, grace-period state;
- bounded error codes.

`Api2AssessmentEnvelope` contains the public state, current `EventEvidence`, `RepositoryEvidence`, `SanitizedObservation`, typed enrichment records, and scalar namespaced extension data. `PublicAssessmentResult` contains `source = "api2"`, bounded category/confidence/`skip_llm`/recommendation, and typed `CheckOutcome` values carrying `check_id`, probability, threshold, and `cleared`; it contains no raw history or internal `ForemanResult`.

Identity rules:

- `work_unit_id = secrets.token_bytes(32)` encoded as lowercase hexadecimal and persisted in managed state or attached session schema 3.
- `repository_id` is host-generated and bound to the trusted repository. `trusted_root_digest = sha256(length_prefixed(canonical_trusted_root))`; `repository_binding_digest = sha256("jev-repository-binding-v1" || length_prefixed(repository_id) || length_prefixed(trusted_root_digest))`.
The host mints `submission_id` from trusted `client`, `session_id`, a host-derived `turn_index`, and a host-derived `event_id`; it never trusts a payload-supplied identity. `turn_index` comes from a non-empty `turn_id` or a persisted host counter, and `event_id` is a host-generated event sequence when the adapter has no stable native ID. API 2 rejects an event when neither identity can be derived.
- `assessment_id = sha256("jev-assessment-v1" || length_prefixed(work_unit_id) || length_prefixed(mode) || length_prefixed(repository_binding_digest) || uint64_be(assessment_sequence))`.
- `assessment_sequence` is persisted per work unit, starts at 1, and increments once per assessment. Missing sequence identity is rejected before assessment. Gaps become diagnostic barriers.

`PrivateExtensionCapabilities` is a host-owned, non-serializable protocol. It exposes only `evidence_store()`, `trusted_repository()`, `journal()`, and `native_settings()` operations; each operation returns an opaque handle or bounded typed value. It is passed to the native enricher constructor, never through the public context, and never exposes a path, key, credential, or raw payload. `JevDiagnosticJournal` receives only the private journal handle.

### Decision 3: Sanitized API-2 boundary

`SanitizedObservation` is a closed provider payload with explicit UTF-8 byte limits:

- `job_summary`: 8,000 bytes;
- latest diagnostic projection: 8,000 bytes;
- at most ten worker diagnostic summaries, 2,000 bytes each;
- at most thirty event diagnostic summaries, 2,000 bytes each;
- at most four typed enrichment records, 4,000 bytes each and 16,000 aggregate;
- status, iteration, counts, and elapsed time.

Worker/event summaries are generated by closed `SafeDiagnosticSummary` projections from typed fields and digests; raw worker/event strings are never copied directly. Each summary contains only a safe kind/code, digest, and redacted stack-free snippet.

`RedactionProfile(redaction-v1)` runs before every API-2 DTO and provider call. It replaces credential material with a redacted placeholder or digest; it replaces typed path fields with an opaque digest plus an allowlisted basename; and it drops free-form path/shell fragments without rejecting the surrounding record. It also rejects non-JSON/binary values and enforces depth 16, 10,000 nodes, and 8,000 UTF-8 bytes per free-form string. This profile covers API-2 callback/provider/journal sinks; API-1 persistence is explicitly outside its guarantee.

API 2 dispatch is explicit: the host builds and validates `Api2AssessmentEnvelope`, calls `ForemanModel.assess_api2(envelope, checks)`, and validates the returned `PublicAssessmentResult`. A provider/result from the wrong path is rejected. Native steering is evaluated only after this result exists; a deterministic fast-path result without a public `assertion_failure_critical` outcome abstains and does not force an LLM call.

### Decision 4: One Foreman policy path

The host adapts `PublicAssessmentResult` into the existing internal `ForemanResult` using the same check IDs, probabilities, thresholds, and guardrails as API 1. `FactoryPolicy.evaluate_with_context(state, public_result, context)` is a new additive method on the existing class; existing API-1 `evaluate()` and `decide()` remain unchanged. A single host-owned `check_id → responsibility_id` table and threshold table are used by both paths. Foreman remains the sole owner of directive selection, worker-health behavior, stop, retry, and termination. API-2 native `jev.triage` may propose only `STEER_WORKER`; every other sealed action remains outside its proposal set.

### Decision 5: Bounded, explicitly non-atomic repository evidence

`RepositoryEvidence` exposes only:

- `complete`, `stable_reads`, `untracked`, and `truncated`;
- domain-separated `head_oid_digest`, `tracked_diff_digest`, `status_digest`, and `worktree_digest`;
- generation ID and a bounded allowlisted `evidence_codes` list.

Digests use `sha256-v1` with length-prefixed UTF-8 framing and NFC normalization. They are not claimed to be secret or resistant to dictionary attacks. The private host capability computes them; no key enters extension records.

The collector uses argv, no shell, a shared deadline, resolved `HEAD`, status, index diff, worktree diff, untracked detection, `--no-ext-diff`, `--no-textconv`, neutral Git configuration, `core.fsmonitor=false`, and process-group cleanup. Any timeout, failure, invalid bytes, changed OID, ignored-path ambiguity, submodule ambiguity, or truncation marks evidence incomplete. A consistency pass is heuristic, not an atomic worktree transaction. Repository evidence is diagnostic only.

### Decision 6: Enricher transport, settings, and namespace

API 2 adds `ObservationEnricherRegistration`, `ObservationEnrichment`, and an async enricher protocol. The CLI, managed runtime, and attached runtime transport configured enrichers alongside responsibilities.

An `EnrichmentRecord.source_id` is a validated non-empty namespaced identifier that must equal the registered enricher ID. `jev.observation` is the native value; a second extension can contribute a different unique ID. Duplicate or unknown source IDs are rejected.

`NativeSettings` is the sole frozen activation-settings object:

| key | type | default | range |
|---|---:|---:|---|
| `journal_enabled` | boolean | true | true/false |
| `journal_ttl_seconds` | integer | 604800 | 60–2592000 |
| `journal_max_records` | integer | 32 | 5–128 |
| `steering_enabled` | boolean | true | true/false |
| `max_steers_per_worker` | integer | 1 | 0–1 |

The host computes effective steering state as the native upper bound AND its own policy, budget, active-worker, and grace-period state. `PublicSupervisionState` is the only input the synchronous responsibility uses; it does not read settings or environment. The API-2 configuration step applies the frozen settings exactly once to responsibility and enricher.

At most two enrichers run sequentially in contribution order with a 500 ms per-call and 750 ms total budget. A second enricher starts only when the remaining total budget is positive. Records and scalar namespaced data obey the envelope bounds. Invalid, oversized, conflicting, or late results are rejected; failures emit sanitized diagnostics and do not affect lifecycle. Enrichment records carry the registered namespaced `source_id`; the host rejects unknown, duplicate, or non-matching source IDs before merging data into the envelope.

### Decision 7: Best-effort diagnostic journal

`JevDiagnosticJournal` receives a private journal handle, not a path. It stores only the public assessment identity, sequence, repository binding, event kind, classification, digests, normalizer version, generation, and TTL metadata.

Exact replay is a no-op. A conflicting replay produces a typed `JournalConflict`; the journal attempts to write only a sanitized conflict code, catches every I/O error, returns fail-open, and never retries or changes lifecycle. Terminal cleanup and `close()` are best-effort. Before the commit gate, cancellation aborts. Once commit begins, the result is `unknown_after_crash` and is never retried blindly. Any journal failure, permission error, lock timeout, cleanup error, or close error cannot stop, restart, retry, or terminate a worker.

Journal I/O uses a dedicated bounded executor. The journal is diagnostic history only and has no lifecycle authority.

### Decision 8: Hook parsing and native steering

Every runtime exposes one canonical direct-hook normalizer. It validates lifecycle fields before unwrapping `tool_response`, resolves integer exit aliases, rejects conflicting/invalid values, treats zero as success, and accepts a host-minted `TrustedRepository` capability. Repository binding comes from the host's already-resolved session/worktree identity before hook assessment; payload `cwd` is provenance only. A direct event without a host binding remains diagnostic-only and cannot steer.

The persisted `after_tool: {...}` compatibility parser returns an `UntrustedPersistedDiagnostic`. It has no current-turn identity, repository binding, steering authority, or lifecycle authority. It may be classified for diagnostics only; it is never fed to the native responsibility for steering.

The native responsibility proposes `STEER_WORKER` only for a direct API-2 `after_tool` event when:

- category is `env_missing` or `flaky_transient` and `skip_llm=true`;
- `assertion_failure_critical` is present and not cleared;
- the public worker is active, steering is allowed, the effective budget is one, `steer_count=0`, and `steering_emitted=false`.

The host serializes the work unit and atomically reserves one steering opportunity with the same work-unit commit that records the diagnostic. `steering_emitted` is a one-bit host state, not a lifecycle ledger. If a process crashes after reservation and before rendering, the opportunity may be lost; no second native steering is allowed. A conflicting journal replay never consumes a steering reservation.

### Decision 9: Repository configuration and legacy recovery boundary

Python, TypeScript, and Rust accept optional repository-root input for behavioral thresholds. Explicit roots are canonicalized, existing files resolve to their parent, missing non-directories return defaults, and search is limited to four levels. Unsafe ownership/modes, symlinks, outside targets, non-regular files, and oversized configs are rejected.

The common `skip_llm` formula is:

```text
category != deep_logic
AND (category in {env_missing, flaky_transient}
     OR skip_llm_probability >= effective_skip_llm_threshold)
```

The API-2 path never resolves provider credentials, API keys, or model names from repository-owned `.jev.json`; existing credential/model behavior is preserved only in the legacy/API-1 path. Structured Python `recovery.argv` remains legacy-only and never enters API-2 test records, provider state, journal, or directive reasons.

## Risks / Trade-offs

- Upstream API-2 must be published before native activation.
- Git evidence is non-atomic and conservative.
- Redaction protects API-2 sinks, not all historical API-1 persistence.
- Diagnostic journal failures are accepted because they have no lifecycle authority.
- At-most-one steering may lose an opportunity after a crash but cannot produce multiple native steering actions in one work unit.
- API-2 public models may need a future additive schema version for new bounded fields.

## Migration Plan

1. Complete G0 legacy freeze and D0 documentation safety.
2. Implement U0 API-2 source contract and test-double tests.
3. Implement L1/N1/P1 local lanes against U0.
4. Publish and pin the API-2 wheel as U1.
5. Run managed/attached E2E with the same wheel hash.
6. Publish native documentation only after U1/E1 evidence.
7. Roll back by removing `[extensions."jev"]` and extension-owned journal data.

## Validation Matrix

- strict OpenSpec and complete S01–S45 traceability;
- G0 manifest and D0 documentation safety;
- API-1/API-2 negotiation, public models, redaction, provider bridge, and policy ownership;
- identity replay, repository change, missing event identity, and sequence gaps;
- Git clean/staged/unstaged/untracked/ignored/submodule/failure/non-atomic matrix;
- enrichment namespace, bounds, settings-once, and cancellation;
- diagnostic journal crash/timeout/replay/TTL/close-failure matrix;
- direct steering budget, no-worker, logic-veto, at-most-one, and no native stop/retry;
- clean-room API-1/API-2 wheel matrix, rollback, and documentation;
- legacy byte identity and full project suites.
