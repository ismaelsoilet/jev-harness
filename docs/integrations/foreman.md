# Foreman integration (thruwire/foreman)

`jev-harness` ships a deterministic adapter surface for
[thruwire/foreman](https://github.com/thruwire/foreman) factories, plus an operator bundle that
installs the companion responsibility class. This document is the operator guide; the change
artifacts under `openspec/changes/foreman-integration/` are the design of record.

*This guide is in English; the [Universal AI Agent Integration Guide](AGENT_INTEGRATION_GUIDE.pt-BR.md)
has a Portuguese version for the general harness setup.*

## 1. What ships, and where it lives

| Piece | Python | TypeScript | Rust |
| :--- | :--- | :--- | :--- |
| `ForemanTriageObserver.extract_test_results` (`extractTestResults`) | ✅ | ✅ | ✅ |
| `ForemanCircuitBreaker.evaluate_worker_health` (`evaluateWorkerHealth`) | ✅ | ✅ | ✅ |
| `FOREMAN_RESPONSIBILITY_TOML` preset | ✅ | ✅ | ✅ |
| `recovery` inside the triage record (E3.6) | ✅ | `null` | `None` |
| `jev-harness export foreman` | ✅ | ✅ | ✅ |

| Field | Python | TypeScript | Rust |
| :--- | :--- | :--- | :--- |
| `category`, `severity_score`, `confidence`, `skip_llm`, `action_recommendation` | ✅ | ✅ | ✅ |
| `assertion_slice` | ✅ | ✅ | ✅ |
| `recovery` | ✅ (argv list, never a shell string) | declared `null` | declared `None` |

The capability matrix is **tested, never accidental**: the shared fixture
`tests/fixtures/foreman_cases.json` drives the three suites and the declared divergence fails a
test if it changes silently.

## 2. What it does (and what it cannot do yet)

- **Triage records.** One record per worker/verifier log, shaped for
  `FactoryObservation.test_results: list[dict[str, Any]]`: the failure category, the root-cause
  assertion line, a deterministic `skip_llm` verdict, and (in Python) the structured recovery
  object (`argv`, `is_safe_auto_run`, rationale).
- **Stagnation evidence.** `evaluate_worker_health` compares a normalized-output fingerprint and a
  diff fingerprint; it recommends abort **only when both are unchanged** across the window
  (`STAGNANT_EVIDENCE`) and **declines** (`complete_signals: false`) when no diff is available.
  It is advisory evidence for Foreman's own policy — jev-harness never decides to stop a worker.
- **Token effect: additive.** `test_results` is an additional field; Foreman keeps
  `latest_worker_output` (its 12,000-char tail) and the bounded `git_diff` (20,000 chars). The
  record adds roughly 250 tokens per failure while preserving the assertion line and making the
  failure machine-actionable. A tail-*replacement* change would be a separate upstream discussion.
- **Inert until the upstream seam lands.** Foreman hardcodes `test_results=[]`
  (`src/foreman/observation.py`) and its only state channel into the Jev prompt is the observation
  itself (`src/foreman/foreman/jev.py` sends `state=observation.model_dump(...)`). Today the
  records therefore take effect through the **companion class** (directive proposals), not through
  the supervisor's prompt.

## 3. Install the operator bundle

```bash
jev-harness export foreman [--out-dir ./foreman-responsibilities]
```

Three files are written — in every runtime, byte-identical:

| File | Purpose |
| :--- | :--- |
| `quality.jev-triage.toml` | Central responsibility configuration (routing + checks + `[settings]`). |
| `quality_jev_triage.py` | The companion class (`JevTriageResponsibility`). |
| `README.md` | The same activation steps, next to the files. |

> **Never place these files inside a managed repository's `.foreman/` directory.** That directory is
> run state. Foreman reads responsibility configuration from the *installation*:
> `--responsibilities-dir <dir>` or `FOREMAN_RESPONSIBILITIES_DIR`.

### The pair ships together (both failures exit code 2)

A TOML only *configures* an **installed** implementation:

* class installed without the central TOML →
  `ResponsibilityConfigError: installed responsibility has no central configuration: quality.jev-triage`
* TOML present without the class →
  `ResponsibilityConfigError: configuration has no installed responsibility implementation: quality.jev-triage`

### Activation

**Path A — patched launcher (works today).** Make the class importable in the Foreman environment
and pass it explicitly, or register it in Foreman's `builtin_registry`:

```python
from jev_harness.integrations.foreman_responsibility import JevTriageResponsibility

responsibilities = configured_registry(
    config,
    config_dir="/etc/foreman/responsibilities",      # the exported bundle directory
    additional=[JevTriageResponsibility()],
)
```

```bash
pip install jev-harness            # inside the Foreman environment
foreman run --repo ./my-project --job "..." --responsibilities-dir /etc/foreman/responsibilities
```

**Path B — upstream registration.** The integration PR (see the change design, Decision 5) adds a
registration path so stock `foreman run` loads the class without a patch. Until it lands, Path A is
the way.

### What the class proposes

- `RETRY_WORKER` (priority 700, below the safety-critical runtime directives; the runtime
  iteration-limit is 950 and neutral `CONTINUE` is 0) when, **and only when the evidence window
  holds `window` assessments**:
  * the breaker returns `should_abort` (stagnation), or
  * triage classifies the failure as `env_missing` / `flaky_transient` with `skip_llm: true`;
- gated by its own Jev checks from the preset: `deterministic_recovery_available` must clear its
  `min_threshold`, and `assertion_failure_critical` **vetoes the environment-recovery retry** when a
  genuine logic regression is likely (a provably stagnant worker is retried regardless — the
  stagnation verdict is already the evidence);
- nothing otherwise (fail-open): no evidence, an incomplete window, a diff timeout or a missing
  `git` all mean "abstain", never a guess.

The directive `reason` is **audit evidence** (visible in `foreman inspect` and `FOREMAN_INTERVENED`
events). Foreman builds the worker steering text from check probabilities, so the reason does not
instruct the worker.

## 4. Determinism caveats (read before relying on thresholds)

- **Process CWD affects `skip_llm`.** `load_repo_config()` walks up 4 levels from the *process*
  working directory looking for `.jev.json`, so `skip_llm_threshold` can differ between machines.
  Run Foreman from a directory whose ancestry has no `.jev.json`, or pin one deliberately.
- **`repo_root` scopes the recovery rationale.** Pass `repo_root=<target repository>` so
  `is_safe_auto_run` and the rationale are evaluated against *that* repository's manifests instead
  of the process CWD. The TypeScript and Rust signatures accept the parameter for parity and
  document that it has no effect there (no recovery object in those runtimes).
- **The diff read is bounded, not non-blocking.** The companion class calls
  `git -C <repo> diff --no-ext-diff` through an injectable runner with a hard timeout
  (`[settings] diff_timeout_seconds = 5`). `directives()` is synchronous on Foreman's event loop, so
  the call may block up to that timeout plus the child's teardown; on timeout it fails open
  (diff `null` → decline → abstain).
- **Offline by default.** The adapter uses the deterministic offline engine
  (`is_mock: true` in the record). Inject a live client if you want Jev judgements — that costs one
  provider call per assessment (the debounce floor is 5s, the periodic assessment 30s).

## 5. Verified upstream facts (inspected 2026-09-23 · re-verify by 2026-10-23)

| Fact | Primary source |
| :--- | :--- |
| `test_results: list[dict[str, Any]]` exists and `build()` hardcodes `test_results=[]` | `src/foreman/observation.py` |
| Verifier summary is a raw tail: `summary=(record.stdout or record.stderr)[-output_limit:]` | `src/foreman/runtime.py` |
| `worker_stuck` / `work_off_track` are Noul questions at `min_threshold = 0.80`; `meaningful_progress` declares none | `src/foreman/responsibilities/definitions/core.worker-health.toml` |
| Responsibility configuration is central; target repositories never supply it; `.foreman/` is run state | `docs/routing.md`, `README.md` |
| A TOML configures an installed class; both half-missing cases exit 2 with the messages quoted above | `src/foreman/responsibilities/configuration.py` |
| Third-party classes are accepted via `configured_registry(additional=[...])`, and must implement `configured`/`configured_checks` | `src/foreman/responsibilities/configuration.py` |
| Stock `foreman run` passes no `additional=` today | `src/foreman/cli.py` |
| The only state channel into the Jev prompt is the observation (`state=observation.model_dump(mode="json")`); steering text comes from check probabilities, never from a directive reason | `src/foreman/foreman/jev.py`, `src/foreman/steering.py` |
| Directives are ranked by `(priority, confidence)` with retry/worker guardrails (`max_retries=1`, `max_workers=3`) | `src/foreman/policy.py` |
| Foreman v0.3.0 dependencies: `pydantic`, `python-dotenv`, `rich`, `typer`, `typesafe-sdk` | `pyproject.toml` |

## 6. Follow-ups recorded by this integration

- **The breaker is deliberately not a core gate** (no CLI verdict, no MCP tool, no corpus entry).
  Promotion path when the corpus proves no accuracy regression: label cases in `tests/corpus/`,
  add a CLI verdict, then an MCP tool named with the canonical `verb_noun` pattern required by
  `.agents/rules/07_mcp_quality_and_tdqs_standards.md` (e.g. `jev_evaluate_worker_health`, never a
  noun-verb or `should_` form), and finally a **tri-runtime parity review** — a promoted gate must
  ship the same semantics in Python, TypeScript and Rust, with the capability matrix updated and
  the shared fixture extended (the same discipline this adapter already follows).
- **E3.6 `recovery` is Python-only.** Porting it to TypeScript/Rust is deferred; the trigger is a
  non-Python consumer that needs deterministic recovery. The capability matrix and the shared
  fixture make the divergence explicit until then.
- **Boundary with the user's "no token savings" expectation:** the additive effect is documented in
  §2; do not quote savings this integration does not deliver.

## 7. Verification

```bash
python -m unittest tests.test_foreman_integration      # 32 tests (1 skipped without Foreman)
cd packages/ts  && npm test                            # includes 9 Foreman tests
cd packages/rust && cargo test                         # includes 7 Foreman tests
python scripts/check_links.py --root .                 # link check (also part of the battery)
```

The three runtimes export byte-identical bundles (verified on 2026-09-23: TOML 1952 B, companion
class 11,259 B, README 2,687 B).
