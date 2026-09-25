# Proposal: Safe Native Foreman Evidence Integration

## Why

The current `foreman-integration` adapter can classify worker output and detect repeated raw evidence, but the published Foreman responsibility protocol exposes only `FactoryState` and bounded cumulative output. It cannot prove which tool payload or repository snapshot belonged to each historical assessment, so reconstructing attached-session stagnation from `worker.stdout` would be unsound.

Foreman's extension and attached-worker foundations now make a concrete integration possible, but a third-party responsibility needs a backward-compatible API that supplies bounded, redacted evidence without breaking existing extensions or giving `jev-harness` control of worker lifecycle. The first native API-2 release is deliberately conservative: structured evidence, observation enrichment, diagnostics, and optional steering only.

## What Changes

- Define an upstream Foreman extension API version 2 that preserves API-1 behavior, adds a public sanitized state/context, a sanitized provider seam, and namespaced observation-enricher transport.
- Add a gated, backward-compatible negotiation path. An API-1 host may inspect an API-2 entry point for its manifest but rejects it before activation, contribution registration, or worker start; the JEV module itself is required to be side-effect-free at import and singleton construction.
- Capture repository evidence once per assessment with explicit `HEAD`, index/worktree diff, status, untracked detection, neutral Git configuration, bounded output, and an explicitly non-atomic stability marker. Repository evidence is diagnostic only and has no lifecycle authority.
- Provide attached assessments with bounded, redacted structured event data. API-2 callbacks receive a public state and never receive raw `FactoryState`, raw worker output, raw paths, credentials, or raw Git/tool payloads.
- Persist only extension-owned metadata and domain-separated digests in a diagnostic journal. Journal failures, cancellations, cleanup errors, and `close()` errors are fail-open diagnostics and cannot stop, restart, retry, or terminate a worker.
- Add a namespace-safe `jev` extension with manifest API version `2`, responsibility `jev.triage`, and observation enricher `jev.observation`; it performs no network or command execution during activation and never executes recovery commands automatically.
- Limit native API-2 v1 actions to an optional first deterministic `STEER_WORKER` proposal when the host's real steering budget, grace period, and policy allow it. It never proposes `STOP_WORKER` or `RETRY_WORKER`; existing Foreman worker-health and legacy operator behavior remain authoritative.
- Add tri-runtime hook normalization for direct `PostToolUse` payloads and the real persisted `after_tool: {...}` compatibility format. Persisted text is diagnostic-only and can never justify a steering or automatic lifecycle action.
- Add repository-scoped `.jev.json` resolution with canonical paths, bounded ancestor search, explicit trust rules, and the existing capability matrix. The API-2 path reads only behavioral threshold fields; it never resolves provider credentials or model names from repository-owned configuration. Structured `argv` recovery remains legacy-only.
- Separate source/test-double development from native activation: G0, D0, and U0 may begin immediately; local implementation lanes may use the API-2 source/test-double after U0, but native activation, real E2E, and release claims remain blocked until an API-2 `foreman-factory` wheel is published and pinned.
- Correct claims: isolated offline heuristics may be provider-free and sub-millisecond in tested gates, but the complete Foreman loop still uses TypeSafe, Git capture is bounded/non-atomic, and token savings remain unmeasured.
- Preserve the existing `jev-harness export foreman` command and the `quality.jev-triage` operator path, identity, and byte-identical legacy artifacts.

## Capabilities

### New Capabilities

- `foreman-evolution`: Safe native Foreman extension activation, structured evidence, bounded observation enrichment, diagnostic journal, attached-session triage, repository-scoped configuration, optional steering, and verified cross-runtime normalization.

### Modified Capabilities

<!-- None: this repository currently has no archived main specs. -->

## Impact

- **Foreman upstream contract, required before native activation:**
  - extension API version 2 with API-1 compatibility;
  - explicit API-2 provider dispatch and sanitized observation path;
  - public sanitized state and optional contextual responsibility protocol;
  - namespaced observation-enricher contributions and one-time settings/configuration;
  - explicit work-unit/submission identity and per-assessment repository evidence;
  - API-2 tests for redaction, transport, routing, hooks, policy, and migration.
- **`jev-harness` Python:** new `foreman_evidence.py` and `foreman_extension.py`; evolution of `foreman.py`, `config.py`, `gates.py`, package exports, `pyproject.toml`, fixtures, and tests. The legacy `foreman_responsibility.py` source remains unchanged.
- **TypeScript and Rust:** hook normalization, repository-scoped threshold resolution, shared fixtures, and the declared `recovery: null` capability boundary.
- **Compatibility:** existing two-argument responsibilities, API-1 extensions, older attached sessions, and the manual operator bundle remain valid; missing or legacy evidence causes abstention or the unchanged legacy path.
- **Dependencies:** no new `jev-harness` runtime dependency. Python remains standard-library-only at runtime; TypeScript adds no runtime package; Rust adds no crate. Foreman keeps its existing dependency set.
- **Claims:** no end-to-end zero-token, sub-millisecond, measured token-savings, automatic-stop, retry, termination, or exactly-once lifecycle-action claim is introduced.
