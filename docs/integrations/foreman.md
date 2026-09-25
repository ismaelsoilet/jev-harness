# Foreman integration (thruwire/foreman)

**[ 🇬🇧 English ](foreman.md) | [ 🇧🇷 Português ](foreman.pt-BR.md)**

`jev-harness` ships a deterministic adapter surface and operator bundle for
[thruwire/foreman](https://github.com/thruwire/foreman) factories, plus a companion responsibility class
for the existing API-1 path. A native API-2 extension is not yet available: it requires a reviewed,
published, and pinned `foreman-factory` API-2 wheel. This document is the operator and architecture guide;
the change artifacts under `openspec/changes/foreman-integration/` and `openspec/changes/foreman-evolution/`
are the designs of record.

---

## 🏛️ Architecture: The Dual-Loop Paradigm

As Foreman creator Josh Rosen noted, agent loops naturally pair with a fast decision model like Jev:
the agent is given freedom to work while an independent model continuously evaluates what is happening.
Foreman and `jev-harness` play two distinct, complementary roles in this ecosystem:

```
                      ┌──────────────────────────────────────────────┐
                      │          thruwire/foreman (Runtime)          │
                      │  • Supervises workers (Codex/OpenCode)       │
                      │  • Decides: CONTINUE, STEER, RETRY, STOP     │
                      │  • Owns execution loop & interactive hooks   │
                      └──────────────────────┬───────────────────────┘
                                             │
                               Planned API-2│ [foreman.extensions] (PR #24)
                               path only     │ or Hook Adapter (PR #23)
                                             ▼
                      ┌──────────────────────────────────────────────┐
                      │          jev-harness (Adapter Layer)         │
                      └──────┬───────────────────────┬───────────────┘
                             │                       │
         1. Test Failure     │                       │ 2. Deterministic
            Triage           │                       │    Circuit Breaker
            (test_results)   │                       │    (worker_stuck)
                             ▼                       ▼
          ┌────────────────────────────┐   ┌───────────────────────────┐
          │ extract_test_results       │   │ evaluate_worker_health    │
          │ • env_missing (skip_llm)   │   │ • Noise-filtered output   │
          │ • flaky_transient          │   │ • Git diff fingerprint   │
          │ • deep_logic               │   │ • Dual-signal stagnation  │
          │ • root-cause assertion     │   │   (STAGNANT_EVIDENCE)     │
          │ • safe recovery argv list  │   └───────────────────────────┘
          └────────────────────────────┘
```

### How `jev-harness` Adds Value to Foreman

| Problem in Agent Supervision | How Foreman Operates Alone | How `jev-harness` Augments Foreman |
| :--- | :--- | :--- |
| **Unstructured Test Failures** | Verifier and worker outputs are stored as raw tails (12,000 chars in `latest_worker_output`); `test_results` is empty (`[]`). | Populates `test_results` with structured failure records (`category`, `skip_llm`, `recovery` argv) and an isolated 500-char `assertion_slice`. |
| **False-Positive Worker Aborts** | `worker_stuck` is evaluated via semantic Jev questions (`min_threshold = 0.80`), which can suffer from uncalibrated false positives. | Supplies deterministic, noise-normalized output + git diff fingerprinting across a 5-step window. Declines if code is changing. |
| **Trivial Environment Doom Loops** | Workers may burn 50,000+ frontier tokens repeatedly debugging a missing package (`ModuleNotFoundError`) or busy port. | Returns `skip_llm: true` with a deterministic repair command (`recovery.argv: ["pip", "install", "..."]`), bypassing LLM calls entirely. |
| **Interactive Assistant Sessions** | Workers started in interactive tools (Codex, Claude) produce test failures inside terminal tool calls (`PostToolUse`). | Provides hook-aware parsing to triage tool execution errors in real-time before the assistant burns reasoning tokens on the next turn. |
| **Zero-Overhead Integration** | Requires no heavy dependencies (`pydantic`, `httpx`, `requests`) in runtime. | Pure standard library implementation in Python (< 500µs offline heuristics or live Jev System One). |

---

## 1. What ships, and where it lives

| Piece | Python | TypeScript | Rust |
| :--- | :--- | :--- | :--- |
| `ForemanTriageObserver.extract_test_results` (`extractTestResults`) | ✅ | ✅ | ✅ |
| `ForemanCircuitBreaker.evaluate_worker_health` (`evaluateWorkerHealth`) | ✅ | ✅ | ✅ |
| `FOREMAN_RESPONSIBILITY_TOML` preset | ✅ | ✅ | ✅ |
| `recovery` inside the triage record (E3.6) | ✅ (safe argv list) | declared `null` | declared `None` |
| `jev-harness export foreman` | ✅ | ✅ | ✅ |
| Native Foreman Extension (`foreman.extensions` entry point) | ⛔ Unavailable until a pinned API-2 wheel is released | N/A (Python-specific) | N/A |

| Field | Python | TypeScript | Rust |
| :--- | :--- | :--- | :--- |
| `category`, `severity_score`, `confidence`, `skip_llm`, `action_recommendation` | ✅ | ✅ | ✅ |
| `assertion_slice` | ✅ | ✅ | ✅ |
| `recovery` | ✅ (argv list, never a shell string) | declared `null` | declared `None` |

The capability matrix is **tested, never accidental**: the shared fixture
`tests/fixtures/foreman_cases.json` drives the three suites and the declared divergence fails a
test if it changes silently.

---

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
  itself (`src/foreman/foreman/jev.py` sends `state=observation.model_dump(...)`). The current
  records take effect through the **existing API-1 companion class** and operator bundle, not through
  a native API-2 extension or the supervisor's prompt.

---

## 3. Activation Paths

### Path A — Native Foreman Extension (API-2; Not Yet Available)

The current `foreman-factory` release supports extension API 1 only. The planned API-2 integration is
blocked until a reviewed, published, and pinned API-2 wheel is available. Do not add a
`foreman.extensions` entry point or expect automatic `activate()` behavior from the current package.

### Path B — Existing API-1 Companion Class

Make the companion class importable and pass it explicitly:

```python
from jev_harness.integrations.foreman_responsibility import JevTriageResponsibility

responsibilities = configured_registry(
    config,
    config_dir="/etc/foreman/responsibilities",
    additional=[JevTriageResponsibility()],
)
```

```bash
pip install jev-harness
foreman run --repo ./my-project --job "..." --responsibilities-dir /etc/foreman/responsibilities
```

### Path C — Operator Bundle Export (Air-gapped or Standalone)

```bash
jev-harness export foreman [--out-dir ./foreman-responsibilities]
```

Three files are written — in every runtime, byte-identical:

| File | Purpose |
| :--- | :--- |
| `quality.jev-triage.toml` | Central responsibility configuration (routing + checks + `[settings]`). |
| `quality_jev_triage.py` | The companion class (`JevTriageResponsibility`). |
| `README.md` | Activation steps next to the files. |

> **Never place these files inside a managed repository's `.foreman/` directory.** That directory is
> run state. Foreman reads responsibility configuration from the *installation*:
> `--responsibilities-dir <dir>` or `FOREMAN_RESPONSIBILITIES_DIR`.

#### The pair ships together (both failures exit code 2)
A TOML only *configures* an **installed** implementation:
* class installed without central TOML → `ResponsibilityConfigError: installed responsibility has no central configuration: quality.jev-triage`
* TOML present without class → `ResponsibilityConfigError: configuration has no installed responsibility implementation: quality.jev-triage`

---

## 4. What the class proposes

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

---

## 5. Determinism caveats (read before relying on thresholds)

- **Process CWD affects `skip_llm`.** `load_repo_config()` walks up 4 levels from the *process*
  working directory looking for `.jev.json`, so `skip_llm_threshold` can differ between machines.
  Pass `repo_root=<target repository>` to decouple configuration discovery from the supervisor process CWD.
- **`repo_root` scopes the recovery rationale.** Pass `repo_root=<target repository>` so
  `is_safe_auto_run` and the rationale are evaluated against *that* repository's manifests instead
  of the process CWD.
- **The diff read is bounded and non-blocking.** The companion class calls
  `git -C <repo> diff --no-ext-diff` through an injectable runner with a hard timeout
  (`[settings] diff_timeout_seconds = 5`). In async event loops, subprocess execution is offloaded
  to avoid thread stalls; on timeout it fails open (diff `null` → decline → abstain).
- **Offline by default.** The adapter uses the deterministic offline engine
  (`is_mock: true` in the record). Inject a live client if you want Jev judgements — that costs one
  provider call per assessment (the debounce floor is 5s, the periodic assessment 30s).

---

## 6. Verified upstream facts (inspected 2026-09-25 · re-verify by 2026-10-25)

| Fact | Primary source |
| :--- | :--- |
| `thruwire/foreman` repository: 552★ (verified 2026-09-25) | `github.com/thruwire/foreman` |
| `test_results: list[dict[str, Any]]` exists and `build()` hardcodes `test_results=[]` | `src/foreman/observation.py` |
| Verifier summary is a raw tail: `summary=(record.stdout or record.stderr)[-output_limit:]` | `src/foreman/runtime.py` |
| `worker_stuck` / `work_off_track` are Noul questions at `min_threshold = 0.80`; `meaningful_progress` declares none | `src/foreman/responsibilities/definitions/core.worker-health.toml` |
| Responsibility configuration is central; target repositories never supply it; `.foreman/` is run state | `docs/routing.md`, `README.md` |
| A TOML configures an installed class; both half-missing cases exit 2 with the messages quoted above | `src/foreman/responsibilities/configuration.py` |
| Third-party extensions are accepted via `[project.entry-points."foreman.extensions"]` and enabled in `config.toml` | `docs/extensions.md`, `src/foreman/extensions.py` (PR #24) |
| Interactive assistant hooks (`foreman hook --client <adapter>`) evaluate on `PreToolUse`, `PostToolUse`, `Stop` | `docs/hooks.md`, `src/foreman/hooks.py` (PR #23) |
| Linked worktree state is excluded from `.foreman/` tracking | `src/foreman/persistence.py` (PR #26) |
| The only state channel into the Jev prompt is the observation (`state=observation.model_dump(mode="json")`); steering text comes from check probabilities, never from a directive reason | `src/foreman/foreman/jev.py`, `src/foreman/steering.py` |
| Directives are ranked by `(priority, confidence)` with retry/worker guardrails (`max_retries=1`, `max_workers=3`) | `src/foreman/policy.py` |
| Foreman v0.3.0 dependencies: `pydantic`, `python-dotenv`, `rich`, `typer`, `typesafe-sdk` | `pyproject.toml` |

---

## 7. Deep Technical FAQ / Architecture Notes

### Q: Why package this as an external extension rather than putting it in Foreman core?
Foreman is an agnostic, extensible supervisor runtime. Keeping language-specific test parsing and regex perception heuristics outside the Foreman core prevents dependency bloat and keeps Foreman focused on lifecycle, live steering, and checkpoint delegation (ThruWire). Foreman's extension foundation (PR #24) is the architecturally intended mechanism for domain-specific responsibilities.

### Q: How does the circuit breaker prevent false aborts?
A single metric (like repeating a test command or a semantic stuckness score) often flags false positives during legitimate fix-and-retry loops. The `ForemanCircuitBreaker` requires **both** normalized output (stripped of volatile timestamps and run durations) and git diff fingerprints to be identical across a complete 5-step window. If the worker edits code, the diff changes and the breaker declines to abort.

### Q: Does git diff execution stall Foreman's asyncio event loop?
No. The diff runner has a hard 5-second timeout and fails open (returning `null`, which causes the breaker to decline). In async execution contexts, the subprocess call is offloaded to prevent event loop stuttering.

### Q: Is a TypeSafe API key mandatory?
No. `jev-harness` is offline-first by default. It runs local deterministic heuristics in < 500µs with zero credentials. If a live `JevClient` is injected, it queries the live neural System One model for ambiguous cases.

---

## 8. Follow-ups recorded by this integration

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

---

## 9. Verification

```bash
python -m unittest tests.test_foreman_integration      # 37 tests (4 skipped without Foreman)
cd packages/ts  && npm test                            # includes 10 Foreman tests
cd packages/rust && cargo test                         # includes 8 Foreman tests
python scripts/check_links.py --root .                 # link check (part of the battery)
```

The three runtimes export byte-identical bundles (verified: TOML 1,952 B, companion
class 11,598 B, README 2,813 B).
