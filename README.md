# ⚡ Jev Harness: The Token Optimizer & Decision Gate for AI Coding Agents

<p align="center">
  <a href="https://github.com/ismaelsoilet/jev-harness/actions/workflows/ci.yml"><img src="https://github.com/ismaelsoilet/jev-harness/actions/workflows/ci.yml/badge.svg" alt="CI Status"></a>
  <a href="https://github.com/ismaelsoilet/jev-harness/actions/workflows/ci.yml"><img src="https://img.shields.io/badge/tests-626%20passed-brightgreen.svg?logo=githubactions&logoColor=white" alt="Tests Passed"></a>
  <a href="https://github.com/ismaelsoilet/jev-harness/releases"><img src="https://img.shields.io/github/v/release/ismaelsoilet/jev-harness?color=teal&logo=github&logoColor=white&cacheSeconds=0" alt="GitHub Release"></a>
  <a href="https://pypi.org/project/jev-harness/"><img src="https://img.shields.io/pypi/v/jev-harness.svg?color=blue&logo=pypi&logoColor=white&cacheSeconds=0" alt="PyPI version"></a>
  <a href="https://www.npmjs.com/package/@ismaelsoilet/jev-harness"><img src="https://img.shields.io/npm/v/@ismaelsoilet/jev-harness.svg?color=cb3837&logo=npm&logoColor=white&cacheSeconds=0" alt="npm version"></a>
  <a href="https://crates.io/crates/jev-harness"><img src="https://img.shields.io/crates/v/jev-harness.svg?color=dea584&logo=rust&logoColor=white&cacheSeconds=0" alt="crates.io version"></a>
  <a href="https://docs.rs/jev-harness"><img src="https://docs.rs/jev-harness/badge.svg" alt="docs.rs"></a>
  <a href="https://pypi.org/project/jev-harness/"><img src="https://img.shields.io/badge/python-3.9%20%7C%203.10%20%7C%203.11%20%7C%203.12%20%7C%203.13-3776ab.svg?logo=python&logoColor=white" alt="Python Versions"></a>
  <a href="https://search.sigstore.dev/?logIndex=2908239242"><img src="https://img.shields.io/badge/provenance-Sigstore-blue?logo=npm" alt="npm Provenance"></a>
  <a href="https://github.com/ismaelsoilet/jev-harness/blob/main/LICENSE"><img src="https://img.shields.io/badge/license-MIT-blue.svg" alt="License MIT"></a>
  <a href="https://typesafe.ai"><img src="https://img.shields.io/badge/powered%20by-TypeSafe%20Jev%20System%20One-orange.svg" alt="TypeSafe Jev"></a>
  <a href="https://modelcontextprotocol.io"><img src="https://img.shields.io/badge/MCP-Compatible-purple.svg" alt="MCP Compatible"></a>
  <a href="#"><img src="https://img.shields.io/badge/dependencies-0%20(pure%20stdlib)-success.svg" alt="Zero Dependencies"></a>
  <a href="docs/system_1_5/SYSTEM_1_5_IMPLEMENTATION.md"><img src="https://img.shields.io/badge/architecture-System%201.5%20Layer-8A2BE2.svg" alt="System 1.5 Architecture"></a>
</p>

<p align="center">
  <b><a href="README.md">🇬🇧 English</a> | <a href="README.pt-BR.md">🇧🇷 Português</a></b>
</p>

> **Stop burning 50,000 frontier tokens on missing packages, network flakiness, and circular doom loops.**
>
> `jev-harness` is an ultra-fast, zero-dependency token optimizer, test failure triage gate, and semantic guardrail for AI coding agents (OpenCode, Command Code, Claude Code, Cursor, Antigravity IDE, Windsurf, Zed, and Pi). Powered by **TypeSafe AI's Jev System One** non-autoregressive decision model.
>
> 🤖 **Operating as an AI Agent?** If you are **working on this repository**, read [`AGENTS.md`](AGENTS.md) ([Português](AGENTS.pt-BR.md)) first. If you are **integrating the tool into your own project**, you do not need it — use the [**Universal AI Agent Integration Guide**](docs/AGENT_INTEGRATION_GUIDE.md) (2-minute setup, no API key required to start).
>
> **What it is:** a deterministic-first **System 1.5 decision layer** for the code-quality loop — test-failure triage, doom-loop breaking, completion veto, reasoning-effort governance and model routing — callable as a CLI, MCP server, git/CI hook and typed SDKs across **three runtimes (Python, TypeScript, Rust)**.
> **What it is not:** a coding agent; a runtime supervisor (that is [Foreman](https://github.com/thruwire/foreman)); a tool-call guardrail ([jev-guard](https://github.com/leepokai/jev-guard)); a context sieve ([Winnow](https://github.com/GhalebDweikat/winnow)); or a capability router ([JevRouter](https://github.com/BillionsBobby/JevRouter)). See [Where it fits](#-where-it-fits-the-system-15-decision-layer).

<details>
<summary><b>📑 Table of contents</b></summary>

- [The Problem](#-the-problem) · [How It Works](#-how-it-works-system-1--system-15--system-2) · [Where It Fits](#-where-it-fits-the-system-15-decision-layer) · [Features](#-features) · [Quickstart](#-quickstart) · [CLI](#-cli-usage) · [Astra-Jev effort governance](#-astra-jev-dynamic-reasoning-effort-governance-2026-frontier-models) · [Integrations](#-universal-agent--ide-integrations) · [SDKs](#-python-sdk) ([TS](#-typescript--javascript-sdk--cli), [Rust](#-rust-crate--standalone-cli)) · [Git & CI guardrails](#-git--cicd-guardrails) · [Economics & benchmarks](#-economics--benchmarks-september-2026-frontier) · [Architecture & roadmap](#-architecture--roadmap) · [Contributing](#-contributing--submissions) · [Release](#-multi-registry-release--synchronization-pypi-npm-cratesio) · [Changelog](#-whats-new-in-v020)

</details>

---

## 🎯 The Problem

When an autonomous coding agent encounters a test failure or compiler error, the standard reaction is to dump 500 lines of raw traceback into an expensive frontier reasoning model (GPT-6 Astra, Claude Fable 5.1). 

| Failure Scenario | Without Jev Harness | With Jev Harness |
| :--- | :--- | :--- |
| **Missing dependency** (`ModuleNotFoundError`, `Cannot find module`, `TS2307`, `E0463`) | 💸 **~50,000 LLM tokens (estimate)** (~$0.50 - $2.50) + 15s delay to output `pip/npm install ...` | ⚡ **Jev triage** (measured: < 1 ms offline in-process, ~80–100 ms offline CLI, ~0.5–1 s live; ≈ **$0.00002/call** at ~470 input tokens) → Action: install package deterministically. **0 LLM tokens**. |
| **Flaky transient error** (network timeout, port busy, ECONNREFUSED) | 💸 LLM hallucinates architectural changes to "fix" an ephemeral glitch | ⚡ **Jev detects flaky transient** → Auto-retry worker once. **0 code changes**. |
| **Circular refactoring** (Doom Loop: attempting the same fix 3+ times) | 💸 **200,000+ tokens burned** in endless circular loops | 🛑 **Jev Abort Gate triggers** (`exit 1`) → Stops loop, alerts developer. |
| **Trivial typo / formatting** | 💸 Heavy reasoning frontier tier used for simple regex/typo | ⚡ **Jev Route** directs task to local script or Gemini 3.8 Flash. |

---

## 🏗️ How It Works: System 1 → System 1.5 → System 2

Daniel Kahneman's cognitive paradigm applied to agentic engineering, with this harness acting as the **System 1.5 executive governance layer** between System 1 perception and System 2 deliberation:
- **System 1 (Fast, Intuitive, Calibrated):** **TypeSafe Jev System One** provides non-autoregressive, parallel, typed micro-decisions. Latency: 70–300 ms (measured: **~80–100 ms** offline CLI, **~0.5–1.0 s** live on the free tier). Pricing: **$0.042 per 1M input tokens** ($0 output tokens). It answers specific closed-world questions (`triage_category`, `severity_score`, `should_abort`, `target_tier`, `completion_status`) without generative hallucinations.
- **System 1.5 (Deterministic Connective Tissue & Executive Gate):** **`jev-harness`** is the executive decision layer that coordinates System 1 and System 2 into a robust, bounded feedback loop (Josh Rosen's cognitive agent paradigm):
  - **Zero-trust state sanitization & focused perception:** Redacts sensitive credentials, masks prompt injections, and extracts targeted assertion slices (≤15 lines) instead of flooding models with 500-line terminal logs.
  - **Deterministic short-circuits & auto-recovery:** Instantly diagnoses missing dependencies (`pip`, `npm`, `cargo`) and transient network/port hiccups in < 500 µs locally without spending any LLM tokens.
  - **Uncertainty calibration & entropy envelopes:** Computes confidence margins and normalized entropy to guard against borderline calls, automatically escalating ambiguous cases to System 2.
  - **Reasoning-effort leasing & doom-loop breaking:** Regulates cognitive effort tiers (`low` to `extra_high`) for frontier models and trips an automatic circuit breaker (`exit 1`) when agents get stuck in repetitive repair loops.
  - **Cross-runtime parity:** Implemented natively in Python, TypeScript, and Rust with zero external runtime dependencies and full offline fallback.
- **System 2 (Slow, Deliberative, Generative):** Frontier reasoning models (**GPT-6 Astra**, **Claude Fable 5.1**, **Claude Opus 5**) write complex code, architect multi-file refactorings, and solve deep logic defects. System 1.5 ensures System 2 is **only invoked when strictly necessary**, cutting token spend by up to ~80–90%.

```
       ┌────────────────────────────────────────────────────────────────────────┐
       │                   AI Coding Agent Execution Loop                       │
       │     (OpenCode / Claude Code / Cursor / Windsurf / Antigravity IDE)     │
       └───────────────────────────────────┬────────────────────────────────────┘
                                           │
                                [Step / Test Execution]
                                           │
                                           ▼
                                 [Execution Output]
                                           │
                 ┌─────────────────────────┴─────────────────────────┐
                 ▼                                                   ▼
         [✅ PASS: Continue]                                  [❌ FAIL: Traceback]
                                                                     │
 ════════════════════════════════════════════════════════════════════╪══════════════════════════════════
 🧠 SYSTEM 1.5: EXECUTIVE DECISION & GOVERNANCE LAYER (jev-harness)  │
 ────────────────────────────────────────────────────────────────────┼──────────────────────────────────
                                                                     ▼
                                                     ┌───────────────────────────────┐
                                                     │ 1. Perception & Sanitization  │
                                                     │  • Credential Redaction       │
                                                     │  • Focused Traceback Slicing  │
                                                     │  • Injection Screening Guard  │
                                                     └───────────────┬───────────────┘
                                                                     │
                                                                     ▼
                                                     ┌───────────────────────────────┐
                                                     │ 2. Local Deterministic Fast   │
                                                     │    Heuristics (< 500 µs)      │
                                                     │  • Missing packages (regex)   │
                                                     │  • Transient network / ports  │
                                                     │  • Doom loop pattern match    │
                                                     └───────────────┬───────────────┘
                                                                     │
                                                 ┌───────────────────┴───────────────────┐
                                                 ▼ (Hit / Certain)                       ▼ (Ambiguous)
 ┌──────────────────────────────────────────────────────────────┐        ┌───────────────────────────────┐
 │ 3. Decision Cache & Receipts                                 │        │ ⚡ SYSTEM 1 (TypeSafe Jev)    │
 │  • Deduplication via .jev/cache.json                         │        │  • Non-autoregressive model   │
 │  • Append-only audit receipts (SHA-256)                      │        │  • Sub-second micro-decisions │
 │  • Reasoning effort lease management                         │        │  • Typed score & distribution │
 └──────────────────────────────┬───────────────────────────────┘        └───────────────┬───────────────┘
                                │                                                        │
                                └───────────────────────────┬────────────────────────────┘
                                                            │
                                                            ▼
                                             ┌───────────────────────────────┐
                                             │ 4. Uncertainty & Policy Gate  │
                                             │  • Margin & Normalized Entropy│
                                             │  • Dynamic effort modulation  │
                                             │  • Fail-open / fail-closed    │
                                             └──────────────┬────────────────┘
                                                            │
 ═══════════════════════════════════════════════════════════╪═══════════════════════════════════════════
                         ┌──────────────────────────────────┴──────────────────────────────────┐
                         ▼                                                                     ▼
         [skip_llm = True / Actionable]                                        [skip_llm = False / Escalated]
                         │                                                                     │
                         ▼                                                                     ▼
            Deterministic Shell Recovery                                         🧠 SYSTEM 2 (Frontier LLM)
          • pip/npm/cargo install package                                         (GPT-6 Astra / Claude Fable)
          • Exponential backoff retry                                             • Deep algorithmic debugging
          • Abort circuit breaker (exit 1)                                        • Multi-file architectural fix
                         │                                                        • Bounded reasoning effort
                         ▼                                                                     │
             ⚡ 0 Frontier Tokens Spent                                                💸 Cost cut by ~80%
```

---

## ✨ Features

- 🛡️ **Zero External Dependencies:** Built entirely with Python's standard library (`urllib.request`, `dataclasses`, `json`). No `pip` bloat; measured offline CLI cold start ~80–100 ms, in-process gates in tens of microseconds.
- 🔌 **Universal MCP Server:** Exposes Jev decision tools over stdio (`jev-mcp`) for Cursor, Claude Desktop, Antigravity, Windsurf, Zed, and OpenCode.
- 🚦 **UNIX Philosophy Compliant:** Standard exit codes (`0` for safe/skip_llm, `1` for abort/logic defect, `2` for syntax error) allow clean pipe composition: `pytest | jev-harness test-gate`.
- 🔄 **Resilient Provider Fallback:** retryable failures (`429`, `5xx`, timeouts, network errors) retry with capped exponential backoff and honor `Retry-After`; after the attempts, the default **fail-open** policy degrades to the deterministic engine and marks the answer (`is_mock=true` + `degraded_reason`: `auth_401`, `http_429`, `http_500`, `timeout`, `connection`, `invalid_response`). A `200` the runtime cannot interpret — a wrong field type (`score: "N/A"`), an unknown answer type, a missing required field or `answers: []` — takes the same path in all three runtimes: a marked degradation, never a crash, a silent `NaN` or a silently defaulted score. `--fail-closed` surfaces errors instead (exit `2`, no traceback), `--retries N` tunes attempts.
- 👻 **Shadow Mode:** `--shadow` (or `"shadow": true` in `.jev.json`) decides and reports `[SHADOW] would exit N` while always exiting `0`, so the pipeline keeps running while you measure the gates on real traffic. CLI misuse (a missing `--log` file, an invalid flag) still exits `2`.
- 🧾 **Audit trail & self-diagnosis:** `jev-harness doctor` checks config, credentials (fingerprint only), model origin, limits, state permissions, receipts/cache and the git hook — every problem comes with the fix command. `jev-harness receipts` reads the append-only decision trail (hashes + metadata, never raw logs; `0600`, TTL and size bounded, `--no-receipts` to disable).
- 🧪 **Calibration corpus & replay gate:** `jev-harness replay --corpus tests/corpus` runs 160 labelled cases through every gate, prints a confusion matrix, precision/recall/F1 and ECE per gate, and fails CI on a regression against `docs/REPLAY_REPORT.json` or when an adversarial log is classified deterministically.
- ⚡ **Decision cache & debounce:** identical live decisions are served from `.jev/cache.json` (`--no-cache` bypasses it), and repeated `nudge-gate`/`abort-check` evaluations inside the debounce window coalesce (`debounced: true`). Shadow runs and degraded answers are never cached; hit-rate shows up in `metrics`.
- 🤖 **CI triage Action:** a composite GitHub Action turns a failed step into a categorised annotation with the next deterministic action — offline by default (no key, no network), never blocks a green run, and blocking is opt-in via `fail-on`.
- 🎯 **Uncertainty envelope:** every gate result carries an additive `uncertainty` block (`margin`, `normalized_entropy`, `confidence`, `escalate_to_system2`, `escalation_reason`) derived from the provider's real distribution — zeros and single-option questions guarded, both key conventions accepted, and a green run is never escalated. It never changes `skip_llm` or an exit code.
- ✂️ **Focused perception & state redaction:** the triage gate sends the provider a `focused_slice` (the assertion line and its neighbours, ≤15 lines) plus a `causal_context` block instead of only the raw log, and **redacts credential-shaped material from the state itself** — in all three runtimes.
- 🧩 **Structured recovery, never auto-executed:** a missing dependency becomes data (`{action_type, package_name, package_manager, argv, is_safe_auto_run, rationale}`) — no shell string, per-ecosystem name validation, and `is_safe_auto_run` requires the package to be in your manifests **and** an explicit `--allow-auto-recovery`.
- 🧠 **Session memory & effort lease:** the gates reuse this repository's recent decisions (an explicit `--history` still wins), and a decision opens a bounded effort lease that answers in sub-milliseconds with `--use-lease` — invalidated immediately by `--tool-error` (break-glass).
- 🔌 **Host plugins & interop:** ready bundles for **Claude Code** (`plugins/claude-code`, manifest + skill + MCP registration) and **Codex/OpenCode** (`plugins/codex`), plus a documented interop section with the dated ecosystem table and an offline link checker in CI.
- 🌐 **Multi-Provider Support:** TypeSafe AI direct, OpenCode Zen, Command Code, Vercel AI Gateway, and OpenRouter (alpha access).

---

## 🧭 Where It Fits: The System 1.5 Decision Layer

`jev-harness` is one role in the emerging **System 1.5** category: connecting a fast System One decision model (**Jev**) to System 2 frontier models through deterministic software. The category already has specialised tools — use each where it belongs (stars/snapshot: 2026-09-23):

| Tool | Role | Works offline? |
| :--- | :--- | :--- |
| **jev-harness** (this repo) | Quality gates: test triage, doom-loop breaking, completion veto, effort governance, model routing | ✅ Deterministic engine, no key needed |
| [Foreman](https://github.com/thruwire/foreman) | Runs and supervises coding workers (steer / stop / retry / verify / finish) | ❌ Requires a key |
| [JevRouter](https://github.com/BillionsBobby/JevRouter) | Routes model / subagent / skill / MCP capabilities with policy and receipts | ❌ Requires a key |
| [Winnow](https://github.com/GhalebDweikat/winnow) | Filters what enters the agent's context window | ❌ Requires a key |
| [jev-guard](https://github.com/leepokai/jev-guard) | Guardrails for tool calls (deny / ask / allow) and prompt-injection screening | ❌ Requires a key |

**Our unique combination:** the only tool in this set that (1) works **fully offline** with a deterministic engine, (2) ships **three runtimes with semantic parity** for gate verdicts (Python / TypeScript / Rust — known mock-probability divergence is tracked as E3.9), and (3) owns the **test / commit / CI quality gate**.

📚 Architecture & roadmap: [System 1.5 plan](docs/system_1_5/SYSTEM_1_5_PLAN.md) · [Ecosystem & opportunities](docs/system_1_5/SYSTEM_1_5_OPPORTUNITIES.md) · [Implementation plan](docs/system_1_5/SYSTEM_1_5_IMPLEMENTATION.md) · [Documentation Hub](docs/README.md).

---

## 🚀 Quickstart

### 1. Installation Across Ecosystems
Available on all three major package registries with zero external runtime dependencies:

| Ecosystem | Registry | Package / Command | Status |
| :--- | :--- | :--- | :--- |
| **Python** | [PyPI](https://pypi.org/project/jev-harness/) | `pip install jev-harness` | [![PyPI](https://img.shields.io/pypi/v/jev-harness.svg?color=blue&logo=pypi&logoColor=white&cacheSeconds=0)](https://pypi.org/project/jev-harness/) |
| **TypeScript / Node** | [npm](https://www.npmjs.com/package/@ismaelsoilet/jev-harness) | `npm install @ismaelsoilet/jev-harness` | [![npm](https://img.shields.io/npm/v/@ismaelsoilet/jev-harness.svg?color=cb3837&logo=npm&logoColor=white&cacheSeconds=0)](https://www.npmjs.com/package/@ismaelsoilet/jev-harness) |
| **Rust** | [crates.io](https://crates.io/crates/jev-harness) | `cargo add jev-harness` | [![crates.io](https://img.shields.io/crates/v/jev-harness.svg?color=dea584&logo=rust&logoColor=white&cacheSeconds=0)](https://crates.io/crates/jev-harness) |
| **GitHub Releases** | [Releases](https://github.com/ismaelsoilet/jev-harness/releases) | Prebuilt binaries & assets | [![GitHub Release](https://img.shields.io/github/v/release/ismaelsoilet/jev-harness?color=teal&logo=github&logoColor=white&cacheSeconds=0)](https://github.com/ismaelsoilet/jev-harness/releases) |

```bash
# Python (CLI + SDK)
pip install jev-harness
# or isolated global CLI
pipx install jev-harness

# TypeScript / Node.js (CLI + SDK)
npm install @ismaelsoilet/jev-harness
# or run directly via npx
npx @ismaelsoilet/jev-harness --version

# Rust (Crate + Standalone CLI)
cargo add jev-harness
# or install standalone binary 'jev'
cargo install jev-harness
```

### 2. Configuration & Multi-Provider Support

Jev Harness supports multiple backend providers and auto-detects credentials:

| Provider | Endpoint | Cost | Configuration |
| :--- | :--- | :--- | :--- |
| **Command Code (Free Deal)** | `https://api.commandcode.ai/provider/v1/systemone` | **$0.00 / Free** | `export CMD_API_KEY=your-key` or `cmd login` (`~/.commandcode/auth.json`) |
| **OpenCode Zen (Free Tier)** | `https://opencode.ai/zen/v1/systemone` | **$0.00 / Free** | `export OPENCODE_API_KEY=zen` or auto-selected |
| **TypeSafe AI (Direct)** | `https://api.typesafe.ai/v1/systemone` | $0.042 / 1M | `export TYPESAFE_API_KEY=your-key` |
| **OpenRouter (Alpha)** ⚠️ | `https://openrouter.ai/api/alpha/decisions` | $0.042 / 1M | `export OPENROUTER_API_KEY=your-key` — requires approved alpha access; the endpoint and the `typesafe/jev-1.13` model are **not publicly listed yet** |
| **Vercel AI Gateway** | `https://ai-gateway.vercel.sh/v1/evaluate` | $0.042 / 1M | `export AI_GATEWAY_API_KEY=your-key` |
| **Autonomous Simulation** | Local Heuristics (< 500µs) | **$0.00** | Active by default if no key or offline |

> **📅 Provider verification date: 2026-09-22.** Model IDs, free tiers and prices change weekly — agents and engineers should re-verify them (and record their own date) if more than 30 days have passed. Step-by-step key acquisition for every provider: **[Universal AI Agent Integration Guide](docs/AGENT_INTEGRATION_GUIDE.md#-provider-access--api-keys)**.
>
> **🔒 Privacy:** offline mode (`--mock`, or no credentials) makes **zero network calls**. Live mode transmits the typed questions and the failure log (head 2,000 + tail 4,000 characters) to the provider endpoint. Since v0.2.0 the **state itself is redacted** in all three runtimes: credential-shaped material (API keys, JWTs, GitHub/AWS tokens, DB URLs, private keys) is masked before it leaves the process — in every gate and over MCP/SDK alike. That is shape-based hygiene, **not** a data-loss-prevention layer: structured customer data that does not look like a credential is still transmitted, so use `--mock` for repositories with regulated data.

Credential resolution priority:
1. Environment variables (`TYPESAFE_API_KEY`, `CMD_API_KEY`, `COMMAND_CODE_API_KEY`, `OPENCODE_API_KEY`, `OPENROUTER_API_KEY`, or `AI_GATEWAY_API_KEY`)
2. Local repository `.jev.json`, `.env`, or `~/.commandcode/auth.json`
3. Global configuration `~/.config/jev/credentials.env`
4. **Resilient Fallback**: active when no credentials are configured and on retryable provider failures (`429`/`5xx`/timeouts/network) or `401`/`403` from **any** provider. Retries use capped backoff + `Retry-After`; the engine prints `[JEV WARNING]` to stderr and every degraded result is flagged `is_mock=true` with a `degraded_reason`. Use `--fail-closed` to surface those errors instead (CLI exit `2`, no traceback).

```bash
# Check current connection & provider status anytime
jev-harness status
```

### Repository Configuration (`.jev.json`)

`jev-harness init` scaffolds a repository-local `.jev.json`. Honored keys:

| Key | Type | Default | Effect |
| :--- | :--- | :--- | :--- |
| `model` | string | provider default | Overrides the model sent to the provider. The scaffold placeholder `jev-latest` means "use the provider-optimized default", so it never clobbers provider model IDs. |
| `skip_llm_threshold` | float `0`-`1` | `0.65` | Minimum confidence for `test-gate` to set `skip_llm=true` (a `deep_logic` verdict is never bypassed). |
| `abort_threshold` | float `0`-`1` | `0.70` | Minimum dead-end probability for `abort-check` to abort a trajectory. |
| `shadow` | bool | `false` | Decide and report, but never change the exit code (see [Shadow Mode](#-features)). |
| `api_key` / `provider` | string | — | Optional credentials. Environment variables take precedence. |

Values are clamped to `[0, 1]`, and a corrupted file degrades to defaults instead of breaking CI. The same keys work identically in Python, TypeScript and Rust.

**Pinning the model.** The effective model resolves as explicit argument → `JEV_MODEL` env var → `model` in `.jev.json` → provider default (run `jev-harness status` to see both the model and where it came from). The alias `jev-latest` **moves**: the provider may change what it points to. Once your `skip_llm_threshold` is calibrated against a model version, pin it — for example `"model": "jev-1.13.0"` — so a provider release cannot silently change your decisions.

---

## 🛠️ CLI Usage

### 1. Test Failure Triage (`test-gate`)
Pipe error logs directly or pass a file:

```bash
# Pipe directly from your test runner
npm test | jev-harness test-gate
pytest | jev-harness test-gate

# Or analyze a saved log file
jev-harness test-gate --log error.log

# Or get machine-readable JSON
jev-harness test-gate --log error.log --json

# Observe decisions without blocking a pipeline (always exits 0)
jev-harness test-gate --shadow --log error.log

# Fail hard on provider outages instead of degrading to the offline engine
jev-harness test-gate --fail-closed --log error.log

# Bound how long retryable provider failures are retried (default: 3 attempts)
jev-harness test-gate --retries 1 --log error.log
```

**Output Example:**
```text
--- JEV TEST TRIAGE VERDICT ---
Category:        ENV_MISSING
Confidence:      92.0%
Skip LLM Call:   YES (Save Tokens!)
Skip Probability: 96.0%
Severity Score:  1.0 / 4.0
Recommendation:  AUTO-ACTION: Install missing dependency or check environment configuration (Do NOT call LLM).
--------------------------------
```

### 2. Guard Against Doom Loops & Dead-Ends (`abort-check`)
Verify that a proposed plan isn't repeating a failed path:

```bash
jev-harness abort-check \
  --plan "Retry rewriting the entire database schema without backup" \
  --history "Attempt 1 failed with timeout. Attempt 2 failed with circular foreign key error."
```
*Returns exit code `1` if abort is recommended, enabling automated CI stops.*

### 3. Model Tier Routing (`route`)
Pick the cheapest model capable of solving the task:

```bash
jev-harness route --task "Fix typo in docstring and reformat with black"
# -> TIER: DETERMINISTIC | Model: Direct Python/Bash Script (0 LLM Tokens)

jev-harness route --task "Refactor distributed actor supervision tree across 14 modules"
# -> TIER: HEAVY_SYSTEM2 | Model: Claude Fable 5.1 / GPT-6 Astra (~$10.00 in / $50.00 out)
```

### 4. Step Completion Verification (`verify`)
Verify evidence against criteria with calibrated confidence:

```bash
jev-harness verify \
  --criteria "Must export format_date function and pass all 10 unit tests" \
  --output "All 10 unit tests passed in 0.02s. format_date exported in index.ts."
```

### 5. Dynamic Reasoning Effort Governance (`reasoning-effort` / `astra-jev`)
Dynamically modulate reasoning effort per-generation (inspired by Vechen @miu21590) to eliminate latency and save thousands of tokens on mechanical tool steps:

```bash
# Evaluate immediate step for DeepSeek (e.g. DeepSeek V4.1-Flash / V4-Pro)
jev-harness reasoning-effort \
  --context "git status e verificar arquivos alterados no commit recente" \
  --target-provider deepseek

# Output:
# Effort: LOW | Dialect: {"extra_body": {"thinking": {"type": "enabled"}}, "reasoning_effort": "low"}
# Latency eliminated: ~200s internal CoT reduced to 1.5s!

# Evaluate architectural task for Anthropic (Claude Fable 5.1 / Claude Opus 5)
jev-harness reasoning-effort \
  --context "Architect distributed actor supervision tree with raft consensus" \
  --target-provider anthropic --json

# Safeguard check for direct models (returns empty params and warnings for non-reasoning models)
jev-harness reasoning-effort \
  --context "Run bash command" \
  --target-provider openai \
  --model gpt-5.6-luna
```

### 6. Continuation Nudge Gate (`nudge-gate` / `nudge`)
Inspired by [`CommandCodeAI/cmd-mod-jev-nudge`](https://github.com/CommandCodeAI/cmd-mod-jev-nudge), `nudge-gate` combines gated workflow phases (`research`, `ask`, `plan`, `execute`, `verify`, `complete`) with calibrated `Noul` probabilities (`nudge`, `waiting`, `progress`) to evaluate whether an autonomous agent paused prematurely with unfinished work or unverified changes (`should_nudge = true`, exit code `0`), while automatically vetoing nudges when waiting on user input (`waiting >= 0.5` or `phase == "ask"`), when the previous nudge produced no progress (`progress < 0.5`), or when all tests pass (`phase == "complete"`):

```bash
# Evaluate if an agent stopped after editing code without running tests
jev-harness nudge-gate \
  --transcript "Assistant: Edited src/auth.py. Now I need to run pytest to verify." \
  --json
# -> should_nudge: true | workflow_phase: "verify" | exit code 0

# Evaluate when waiting on user choice (vetoed automatically)
jev-harness nudge-gate \
  --transcript "Assistant: Which AWS region should I deploy to? Would you like me to proceed?"
# -> should_nudge: false | workflow_phase: "ask" | exit code 1
```

### 7. ROI & Token Savings Telemetry (`metrics`)
Inspect cumulative tokens saved, dollars saved, and doom loops intercepted:

```bash
# View active telemetry
jev-harness metrics

# Reset session telemetry counters
jev-harness metrics --reset
```

**Output Example:**
```text
============================================================
              JEV HARNESS TELEMETRY & ROI
============================================================
Total Triage Interceptions:      14 calls
LLM Frontier Calls Skipped:      11 calls (78.6%)
Abort Guard Stops Triggered:     2 doom loops killed
Deterministic Routes:            6 tasks
Reasoning Effort Modulations:    8 steps (6 low, 2 high)
Estimated Tokens Saved:          422,200 tokens (heuristic estimate)
Estimated Frontier Dollars Saved: $6.12 USD (heuristic estimate)
Assumption Model:                26,200 tokens/$0.31 per intercepted triage; 80,000 tokens/$1.20 per aborted doom loop
============================================================
```

> 📊 **These figures are a planning estimate, not metered usage.** The per-event assumptions are fixed constants (26,200 tokens/$0.31 per intercepted triage, 80,000 tokens/$1.20 per aborted loop). `--json` exposes `estimates_are_heuristic: true` so downstream tooling can label them correctly.

### 8. Self-diagnosis, audit trail and calibration (`doctor` / `receipts` / `replay`)

```bash
# Is my installation healthy? (never prints secrets; --live spends ONE request)
jev-harness doctor
jev-harness doctor --live --json

# What did this repository decide? (append-only, hashes + metadata only)
jev-harness receipts --tail 10
jev-harness receipts --json

# How accurate are the gates? (confusion matrix, P/R/F1, ECE per gate; fails on regression)
jev-harness replay --corpus tests/corpus
```

### 7. One-Command Agent Setup (`init`)
Automatically scaffold MCP configurations for your active agent or IDE:

```bash
# Setup for Cursor
jev-harness init --cursor

# Setup for Antigravity IDE
jev-harness init --antigravity

# Setup git pre-commit hook (detects npm/pytest/cargo; never overwrites an existing hook)
jev-harness init --git

# Setup all supported tools at once
jev-harness init --all
```

---

## ⚡ Astra-Jev: Dynamic Reasoning Effort Governance (2026 Frontier Models)

Inspired by Vechen's ([@miu21590](https://x.com/miu21590)) groundbreaking work on *Astra-Codex* and the **[Astra-Ares](https://github.com/miuuyy/Astra-Ares)** framework, **Astra-Jev** introduces autonomous, per-generation reasoning effort modulation governed by TypeSafe Jev System One.

Instead of locking an entire multi-turn coding session into heavy, slow reasoning (or risking bugs by running exclusively in low reasoning), Astra-Jev evaluates the cognitive demand of the immediate next generation in **< 500µs locally** (in-process; live latency depends on the provider — measured ~0.5–1.0 s on the free tier).

```
                  ┌────────────────────────────────────────────────────────┐
                  │                 Autonomous Agent Loop                  │
                  └──────────────────────────┬─────────────────────────────┘
                                             │
                                   Proposed Next Action
                     ("git status", "read file", or "architect kernel")
                                             │
                                             ▼
                             ┌───────────────────────────────┐
                             │       Astra-Jev Gate          │
                             │  (Jev System One Micro-Eval)  │
                             └───────────────┬───────────────┘
                                             │
            ┌────────────────────────────────┼────────────────────────────────┐
            ▼                                ▼                                ▼
    [Trivial / Mechanical]          [Standard Feature]             [Deep Architecture]
      Cognitive Depth: LOW           Cognitive Depth: MED          Cognitive Depth: HIGH
            │                                │                                │
            ▼                                ▼                                ▼
   Compile Provider Dialect       Compile Provider Dialect         Compile Provider Dialect
 (e.g. enable_thinking: false)     (e.g. reasoning_effort: med)    (e.g. thinking: adaptive max)
            │                                │                                │
            ▼                                ▼                                ▼
  ⚡ 1.5s response (~0 CoT)        🎯 Balanced ~4,000 CoT           🧠 Deep 32,000 CoT Analysis
   Western: Saves ~$0.80 USD       Western: Normal pricing          Western: Maximum reasoning
   Chinese: Saves ~240s wait       Chinese: Normal thinking         Chinese: Deep exploration
```

### Dual ROI: Why Modulate Reasoning Effort in 2026?

The value of dynamic reasoning modulation fundamentally depends on the provider architecture:

| Provider Ecosystem | Problem Solved | Without Astra-Jev | With Astra-Jev |
| :--- | :--- | :--- | :--- |
| **Western Frontier**<br>(*GPT-6 Astra*, *Claude Fable 5.1*) | **Dollar Cost**<br>($10/1M in, $50/1M out) | Agent burns ~8,000 reasoning tokens ($0.40 - $1.20) just to inspect `git status` or read a file | Injects `effort="low"`, burning only ~300 tokens. **Saves up to $1.15 per mechanical generation.** |
| **Chinese Frontier**<br>(*DeepSeek V4.1-Flash*, *Qwen 3.8 Max*, *Kimi-k3*, *MiMo*) | **Latency & GPU Starvation**<br>(Tokens are cheap, but internal CoT takes 3–5 minutes) | Agent enters 200–300 second internal thinking loop before running a trivial bash command | Disables thinking CoT or sets `effort="low"`. Response delivered in **1.5s instead of 240s**. |

### 🛡️ Critical Safeguards Built into Astra-Jev

1. **Direct Single-Pass Model Safeguard:** Models that do not support internal reasoning (e.g. `gpt-5.6-luna`, `gemini-3.8-live`, `claude-3.5-haiku`) will return fatal **HTTP 400 Bad Request** if reasoning parameters are injected. Astra-Jev automatically detects non-reasoning targets, sets `is_reasoning_supported = False`, and returns clean empty payloads `{}`.
2. **Preservation of `reasoning_content` (DeepSeek multi-turn):** In DeepSeek V4.1-Flash/Pro APIs, stripping `reasoning_content` across multi-turn tool calling can corrupt tool execution. Astra-Jev enforces dialect compliance to preserve thinking structures across turn transitions.
3. **Prompt Cache (KV Cache) Trade-off Advisory:** Toggling reasoning parameters back-and-forth mid-session can invalidate prefix cache on long contexts (>100k tokens). Astra-Jev provides `cache_safe_recommendation` advisories:
   - For pure mechanical actions, use Jev's `skip_llm=true` to execute directly without calling the LLM at all.
   - Keep reasoning effort stable across related sub-steps of a single complex implementation.

---

## 🤖 Universal Agent & IDE Integrations

> 📖 **Looking for a turnkey setup for any project?** Read the [**Universal AI Agent Integration Guide**](docs/AGENT_INTEGRATION_GUIDE.md) ([Português](docs/AGENT_INTEGRATION_GUIDE.pt-BR.md)) with copy-paste configs for Claude Code, Codex, Pi, Oh My Pi, CommandCode, Cursor, and CI/CD.
>
> 🏭 **Running a [`thruwire/foreman`](https://github.com/thruwire/foreman) factory?** This harness also ships a deterministic adapter surface, an operator bundle (`jev-harness export foreman`) and the verified upstream facts — see the [Foreman integration guide](docs/integrations/foreman.md).

### 1. Claude Code (`claude` CLI by Anthropic)
Connect Jev to Claude Code in 5 seconds via native MCP:
```bash
# Register Jev Harness MCP into Claude Code
claude mcp add jev-harness -- npx -y @ismaelsoilet/jev-harness mcp

# Or using Python:
claude mcp add jev-harness -- jev-mcp
```
Add to your project's `CLAUDE.md`:
```markdown
## Jev Harness Token Governance
- Before querying LLMs on test/build failures, call `jev_triage_test_failure`. If `skip_llm=true`, execute the deterministic fix directly.
- If a task retries twice without progress, call `jev_abort_check` to break doom loops.
- For mechanical bash commands or file lookups, call `jev_modulate_reasoning_effort` with effort="low".
```

### 2. OpenAI Codex / Astra-Codex
Dynamically modulate GPT-6 Astra reasoning effort per generation step inside Codex without invalidating prefix cache (as featured on X):
```bash
# In Codex automation scripts or step pre-hooks:
jev-harness reasoning-effort \
  --context "$TASK_STEP_DESCRIPTION" \
  --target-provider openai --json
```
Inject the resulting `reasoning_effort: "low" | "medium" | "high"` into the root API payload. The harness never rewrites your message history, so it does not invalidate the provider's prefix cache by design.

### 3. Pi & Oh My Pi (`pi` / `oh-my-pi`)
Equip Mario Zechner's minimalist terminal agent (`pi`) and `oh-my-pi` workflows:
```bash
# In your Pi task or terminal prompt:
npm test 2>&1 | npx @ismaelsoilet/jev-harness test-gate
pytest 2>&1 | jev-harness test-gate
```
If the exit code is `0` (`skip_llm=true`), Pi applies the deterministic package installation or retry command without querying expensive models.

### 4. CommandCode
In `.commandcode/config.json` or CLI pre-command triggers:
```json
{
  "mcpServers": {
    "jev-harness": {
      "command": "npx",
      "args": ["-y", "@ismaelsoilet/jev-harness", "mcp"]
    }
  }
}
```

### 5. Cursor IDE (`.cursor/mcp.json`)
Add to `.cursor/mcp.json` (or run `jev-harness init --cursor` in your repo):
```json
{
  "mcpServers": {
    "jev-harness": {
      "command": "npx",
      "args": ["-y", "@ismaelsoilet/jev-harness", "mcp"]
    }
  }
}
```

### 6. Claude Desktop (`claude_desktop_config.json`)
Add to `claude_desktop_config.json`:
```json
{
  "mcpServers": {
    "jev-harness": {
      "command": "npx",
      "args": ["-y", "@ismaelsoilet/jev-harness", "mcp"]
    }
  }
}
```

### 7. Google Antigravity IDE (`mcp_config.json` & `hooks.json`)
Connect as an MCP Server:
```json
{
  "mcpServers": {
    "jev-harness": {
      "command": "jev-mcp",
      "args": []
    }
  }
}
```
Or hook into the execution lifecycle in `~/.gemini/config/hooks.json`:
```json
{
  "jev-guard": {
    "PreInvocation": [
      {
        "type": "command",
        "command": "echo '{\"injectSteps\": [{\"ephemeralMessage\": \"[JEV ACTIVE] Triage test errors with jev-harness test-gate before calling LLMs. If skip_llm=true, fix deterministically.\"}]}'"
      }
    ]
  }
}
```

### 8. OpenCode, Windsurf & Zed
- **OpenCode:** Add Jev triage gate to `.opencode/config.json`.
- **Windsurf:** Add to `~/.codeium/windsurf/mcp_config.json`.
- **Zed:** Add to `~/.config/zed/settings.json` under `context_servers`.

---

## 🐍 Python SDK

You can also use `jev-harness` directly in Python scripts and agent orchestration frameworks (LangChain, LlamaIndex, CrewAI, AutoGen):

```python
from jev_harness import (
    JevClient,
    triage_test_failure,
    should_abort_trajectory,
    route_model_tier,
    verify_step_completion,
    modulate_reasoning_effort,
)

client = JevClient()

# 1. Triage test traceback
res = triage_test_failure("ModuleNotFoundError: No module named 'scipy'", client=client)
if res.skip_llm:
    print(f"Safe to fix deterministically: {res.action_recommendation}")

# 2. Check trajectory before spending tokens
abort_decision = should_abort_trajectory(
    proposed_step="Tentar novamente a mesma abordagem",
    recent_attempts_summary="Tentativa 1 falhou com timeout",
    client=client,
)
if abort_decision.should_abort:
    print("Trajectory aborted! Re-align with user.")

# 3. Dynamic Reasoning Effort Modulation (Astra-Jev)
effort_res = modulate_reasoning_effort(
    context="git status e inspecionar diff de arquivos alterados",
    provider="deepseek",
    model="deepseek-v4.1-flash",
    client=client,
)
print(f"Effort: {effort_res.effort}")  # low
print(f"Provider Params to inject: {effort_res.provider_params}")  # {'extra_body': {'thinking': {'type': 'enabled'}}, 'reasoning_effort': 'low'}
```

---

## 🟦 TypeScript / JavaScript SDK & CLI

For Node.js, Bun, Deno, Vite, Tauri, and Next.js applications:

```bash
# Install via npm
npm install @ismaelsoilet/jev-harness

# Or via bun
bun add @ismaelsoilet/jev-harness
```

### Programmatic Usage

```typescript
import {
  triageTestFailure,
  shouldAbortTrajectory,
  routeModelTier,
  verifyStepCompletion,
  modulateReasoningEffort,
  JevClient,
} from "@ismaelsoilet/jev-harness";

// 1. Triage test failure in < 2ms locally (or sub-second remote)
const triage = await triageTestFailure(rawErrorOutput);
if (triage.skipLlm) {
  console.log("Safe to fix deterministically! LLM call skipped.");
  console.log("Recommended Action:", triage.actionRecommendation);
}

// 2. Prevent circular doom loops before spending frontier tokens
const abortCheck = await shouldAbortTrajectory(
  "Repeat previous refactoring step",
  "Step failed with: TypeError: undefined is not a function"
);
if (abortCheck.shouldAbort) {
  console.error("Agent trapped in dead-end loop! Aborting.");
}

// 3. Dynamic Reasoning Effort Modulation (Astra-Jev)
const effortRes = await modulateReasoningEffort(
  "git status and check changed files",
  "anthropic"
);
console.log("Effort:", effortRes.effort); // low
console.log("Params:", effortRes.providerParams); // { thinking: { type: 'adaptive' }, output_config: { effort: 'low' } }
```

### TypeScript CLI

```bash
# Run test triage via npx
npx @ismaelsoilet/jev-harness triage "Cannot find module 'lodash'"

# Trajectory abort check
npx @ismaelsoilet/jev-harness abort-check --plan "Try identical prompt again"

# Model router
npx @ismaelsoilet/jev-harness route "Architect distributed consensus protocol"

# Dynamic reasoning effort modulation (Astra-Jev)
npx @ismaelsoilet/jev-harness reasoning-effort --context "git status" --target-provider deepseek --json
```

---

## 🦀 Rust Crate & Standalone CLI

Ultra-low latency (< 500µs local, zero-overhead) for systems programming, Tauri backends, and terminal tools without Python or Node.js dependencies:

```toml
[dependencies]
jev-harness = "0.2.0"
tokio = { version = "1", features = ["full"] }
```

### Programmatic Usage

```rust
use jev_harness::gates::{triage_test_failure, should_abort_trajectory, modulate_reasoning_effort};

#[tokio::main]
async fn main() {
    // 1. Triage test traceback in < 500µs
    let triage = triage_test_failure("error[E0463]: can't find crate for 'serde'", None).await.unwrap();
    if triage.skip_llm {
        println!("Safe to fix deterministically: {}", triage.action_recommendation);
    }

    // 2. Trajectory guard against dead ends
    let abort = should_abort_trajectory("Repeat same step", "Attempt 1 failed", None).await.unwrap();
    if abort.should_abort {
        eprintln!("Doomed loop detected: {}", abort.reasoning_summary);
    }

    // 3. Dynamic Reasoning Effort Modulation (Astra-Jev)
    let effort_res = modulate_reasoning_effort("git status", "openai", None, None).await.unwrap();
    println!("Effort: {}", effort_res.effort); // low
    println!("Params: {:?}", effort_res.provider_params); // {"reasoning_effort": "low"}
}
```

### Standalone CLI Binary (`jev` / `jev-harness`)

```bash
# Install via Cargo
cargo install jev-harness

# Or use directly in shell pipelines
cargo test 2>&1 | jev test-gate
jev route --task "Architect enterprise distributed consensus"
jev reasoning-effort --context "git status" --target-provider deepseek --json
```

---

## 📦 Git & CI/CD Guardrails

### Pre-commit Hook (`.pre-commit-config.yaml`)
The hook needs your test command as an argument (a hook repository cannot guess your runner):

```yaml
repos:
  - repo: https://github.com/ismaelsoilet/jev-harness
    rev: v0.2.0
    hooks:
      - id: jev-test-gate
        args: ["pytest -q"]     # or "npm test", "cargo test --quiet", ...
```

### Generated Git Hook (`jev-harness init --git`)
Detects your runner (`npm`/`pytest`/`cargo`), writes a failure-only hook and never overwrites an existing one (it saves `pre-commit.jev` instead). It is **virtualenv-aware**: when a `.venv`/`venv` exists the hook uses its binaries (e.g. `./.venv/bin/python`, `./.venv/bin/jev-harness`), so it works whether or not the environment is activated.

```bash
jev-harness init --git
jev-harness init --git --test-cmd "make test-fast"   # override the detected command
```

`init` also scaffolds `.jev.json`, `.env.jev.example` (all providers), `.agents/skills/jev-harness/SKILL.md` and, with `--cursor`, `.cursor/mcp.json`. It **never overwrites existing files or foreign hooks**; re-running regenerates only the hook it generated itself (recognised by its marker, including pre-v0.1.13 variants).

### Husky Hook (`.husky/pre-commit`)
Let the runner decide; ask Jev only for the triage of a failure:

```bash
if ! OUT=$(npm test 2>&1); then printf '%s\n' "$OUT" | jev-harness test-gate; exit 1; fi
```

> Green runs are detected deterministically (`category: "no_failure"`, exit `0`, zero API calls), so `npm test 2>&1 | jev-harness test-gate` is also safe — but the failure-only form above is the most explicit and never depends on run-summary parsing.
>
> ⚠️ **`.git/hooks/` is not version-controlled.** A generated hook lives only on your machine; for teams, commit a hook script (or use the `pre-commit` framework with `id: jev-test-gate`) so every developer gets the same gate.

---

## 📊 Economics & Benchmarks (September 2026 Frontier)

### Token & Cost Economics

| Metric | 2026 Frontier Reasoning (GPT-6 Astra, Claude Fable 5.1) | Fast Agentic Tier (Gemini 3.8 Flash) | TypeSafe Jev System One (`jev-harness`) |
| :--- | :--- | :--- | :--- |
| **Input Pricing** | $10.00 / 1M tokens | $0.75 / 1M tokens | **$0.042 / 1M tokens (~238x cheaper)** |
| **Output Pricing** | $50.00 / 1M tokens | $3.75 / 1M tokens | **$0.00 (Free - Non-autoregressive)** |
| **Latency** | 10,000ms – 30,000ms | 1,500ms – 4,000ms | **Provider claim: ~100 ms typical (70 ms floor). Measured harness E2E: ~0.5–1.0 s live (free tier), < 1 ms offline in-process** |
| **Output Structure**| Free-form prose & streaming tokens | Structured JSON tool calls | **Strictly typed: Choice, Score, Noul** |
| **Determinism** | Stochastic reasoning | Stochastic generation | **Calibrated probabilities — not infallible (see the model's documented [jaggedness](https://docs.typesafe.ai/model-jaggedness/jev-1.13))** |

### Tri-Runtime Offline Latency (measured 2026-09-23, in-process mock)

When `--mock` (or no credentials) is active, every gate runs locally with zero network. Budget: **p99 < 500µs** — asserted in CI for Rust, measured for all three runtimes on 2026-09-23 (`N = 1000` for triage, `N = 500` for abort/effort, standard Linux host):

| Runtime | Decision Gate | p50 | p95 | p99 | Mean |
| :--- | :--- | ---: | ---: | ---: | ---: |
| **Rust** (`packages/rust`) | `triage_test_failure` | 22.0 µs | 38.7 µs | 58.5 µs | 26.1 µs |
| | `should_abort_trajectory` | 14.6 µs | 30.3 µs | 43.1 µs | 16.8 µs |
| | `modulate_reasoning_effort` | 15.5 µs | 29.9 µs | 40.5 µs | 17.6 µs |
| | *pure `simulate_system_one`* | 1.9 µs | 1.9 µs | 2.8 µs | 1.9 µs |
| **TypeScript** (`packages/ts`) | `triageTestFailure` | 39.5 µs | 143.2 µs | 340.3 µs | 57.2 µs |
| | `shouldAbortTrajectory` | 37.1 µs | 106.0 µs | 234.4 µs | 47.3 µs |
| | `modulateReasoningEffort` | 21.9 µs | 77.2 µs | 338.4 µs | 34.1 µs |
| **Python** (`src/jev_harness`) | `triage_test_failure` | 124.9 µs | 208.1 µs | 295.5 µs | 140.4 µs |
| | `should_abort_trajectory` | 112.4 µs | 181.3 µs | 229.2 µs | 125.0 µs |
| | `modulate_reasoning_effort` | 78.1 µs | 131.3 µs | 162.0 µs | 86.8 µs |

> ⚡ **Reproduce / zero-overhead:** Rust asserts its budget in `packages/rust/tests/gates_test.rs` (`cargo test --test gates_test -- --nocapture`); Python and TypeScript values are a **point-in-time sample** (2026-09-23, this host, in-process forced-mock client), not a CI assertion. Re-measure on your hardware before citing; the **budget**, not the exact microsecond, is the contract. Piping test runners through the gates still adds overhead far below human perception.

---

## 🗺️ Architecture & Roadmap

| Document | What it answers |
| :--- | :--- |
| [Documentation Map & Catalog](docs/README.md) | Central documentation directory, audience navigation, and complete file index |
| [System 1.5 — Architecture & verified facts](docs/system_1_5/SYSTEM_1_5_PLAN.md) | Where the tool sits between System 1 (Jev) and System 2; what is verified today (v0.2.0) and what is missing |
| [System 1.5 — Ecosystem & opportunities](docs/system_1_5/SYSTEM_1_5_OPPORTUNITIES.md) | How we compare with Foreman, JevRouter, Winnow and jev-guard; 21 prioritised opportunities; the "can we be 1.5?" verdict |
| [System 1.5 — Implementation plan](docs/system_1_5/SYSTEM_1_5_IMPLEMENTATION.md) | Epics, acceptance criteria, tests and sequencing (H1–H3) |
| [Universal Agent Integration Guide](docs/AGENT_INTEGRATION_GUIDE.md) | Copy-paste setup for MCP, CLI, hooks and CI in any project |
| [Foreman integration](docs/integrations/foreman.md) | Adapter surface, operator bundle (`export foreman`) and the verified upstream facts for [thruwire/foreman](https://github.com/thruwire/foreman) factories |

---

## 🤝 Contributing & Submissions

Contributions are welcome!
- Submitting to **[awesome-jev](https://github.com/yibie/awesome-jev)** and **[awesome-jev-use-cases](https://github.com/whyashthakker/awesome-jev-use-cases)**.
- Open an Issue or Pull Request on GitHub.

```bash
# Development setup
git clone https://github.com/ismaelsoilet/jev-harness.git
cd jev-harness
python -m unittest discover -s tests
```

---

## 🚀 Multi-Registry Release & Synchronization (PyPI, npm, Crates.io)

### Do Registries Automatically Update on `git push`?
**No.** PyPI, npm, and Crates.io are immutable, independently versioned package registries. Pushing commits to GitHub updates only the Git repository, not the registry packages or their online documentation.

To update the packages and documentation across all 3 registries:

### 1. Unified Local Release Script (`scripts/release.sh`)
Use the automated multi-runtime script to check, bump versions, and publish:

```bash
# 1. Run full test battery (Python, TS, Rust - 626 tests)
./scripts/release.sh --check

# 2. Synchronously bump version in pyproject.toml, package.json, and Cargo.toml
./scripts/release.sh --bump 0.2.0

# 3. Publish to a specific registry or all at once:
./scripts/release.sh --publish rust    # Publishes to crates.io
./scripts/release.sh --publish npm     # Publishes to npm (@ismaelsoilet/jev-harness)
./scripts/release.sh --publish python  # Builds wheel/sdist for PyPI

# 4. Create git tag and push to GitHub
./scripts/release.sh --git-tag 0.2.0
```

### 2. Automated GitHub Actions CD (`.github/workflows/release.yml`)
You can also trigger releases via GitHub Actions:
- **Automatic:** Pushing any tag matching `v*.*.*` (e.g. `git push origin v0.1.6`) triggers the `release.yml` workflow, which tests all runtimes and automatically publishes to PyPI, npm, and Crates.io.
- **Manual:** Go to **GitHub Actions → Release & Publish → Run workflow**, specify the version, and click run.

*(Requires `PYPI_API_TOKEN` and `CARGO_REGISTRY_TOKEN` in GitHub Repository Secrets; npm uses OpenID Connect (OIDC) Trusted Publishing with cryptographic Sigstore provenance without static tokens).*

## 🌟 What's New in v0.2.0

- 🦀 **Rust live parity fixed (breaking for direct crate users)**: live `Score` answers were silently dropped because the parser expected an integer score and a list legend while the provider returns a float and a level map. `ScoreAnswer.score` is now `f64`, `legend` accepts a map or a list, and `probabilities` are parsed — `severity`, `viability`, `rigor` and `complexity` now match Python/TypeScript in live mode. Two other public signatures changed in 0.2.0: `JevClient::retry_delay_ms` now takes `Option<f64>` (fractional `Retry-After`) and `JevClient::parse_api_response` returns an error instead of silently dropping an unparseable answer. The crate is pre-1.0, so this ships as a minor release.
- 🔁 **Provider resilience**: retry with capped, jitter-free exponential backoff and `Retry-After` support (`429`/`5xx`/timeouts, fractional seconds included); after the attempts, the default **fail-open** policy degrades to the deterministic offline engine and marks the answer (`is_mock=true` + `degraded_reason`: `auth_401`, `http_429`, `http_500`, `timeout`, `connection`, `invalid_response`). `--fail-closed` surfaces the error instead (exit `2`, no traceback); `--retries N` tunes attempts.
- 🧩 **Malformed provider payloads are a first-class failure**: a `200` with type-mismatched fields (`score: "N/A"`, `answers: []`, `null` numerics), an unknown answer `type` or a missing required field used to crash Python with a raw traceback, produce a silent `NaN` in TypeScript and silently drop the answer in Rust — three different semantics for the same input, and a gate quietly falling back to its default score. All three now treat it as `invalid_response`, retry it like a bad status, degrade under fail-open and raise under fail-closed, and `degraded_reason` is finally **visible** in `--json`, in the MCP payloads and in the human `Mode:` line.
- 📦 **Payload guard**: `state` and questions are validated against the provider limits (128k state chars / 256k total, ~32k/64k tokens) before any network call, counting code points consistently across the three runtimes.
- 📌 **Model pinning and origin**: the effective model resolves as explicit argument → `JEV_MODEL` → `"model"` in `.jev.json` → provider default, and `status` now reports **where it came from** (`Model origin: repository .jev.json`), warning that `jev-latest` is a moving alias. Pin a version once your thresholds are calibrated.
- 🐛 **No more traceback on long literal input**: a task, state or `--log` value longer than the OS path limit used to crash `route`/`verify`/`effort` with `[Errno 36] File name too long` (exit `1` with a traceback); such a value is now treated as literal text (or reported as "log file not found"), and an oversized live payload exits `2` with a clear message.
- 👻 **Shadow mode**: `--shadow` (or `"shadow": true` in `.jev.json`) decides and reports `[SHADOW] would exit N` on stderr while always exiting `0` — in all three runtimes, including when the provider fails, where it reports `[SHADOW] would exit 2` instead of breaking the pipeline. CLI misuse still exits `2`; `test-gate --json` exposes `shadow` and `would_exit`.
- 🧪 **626-Test Battery**: 432 Python + 99 TypeScript + 95 Rust, including a shared live-payload fixture, real HTTP/TCP retry servers, malformed-payload probes, and shadow/payload-limit/model-pinning parity.
- 🧾 **Trust, audit and self-diagnosis**: `doctor` (OK/AVISO/FALHA + the fix command, `--json` for agents), `receipts` (append-only audit trail with a stable input hash, hashes only, `0600`, TTL/size bounded), `.jev/` git-ignored by the repo and by `init`, measured `usage`/`cost` split from the heuristic estimates in `metrics`, and a decision cache with a reported hit-rate (`--no-cache` to bypass).
- 🧪 **Measured calibration instead of assumed accuracy**: a 160-case labelled corpus (`tests/corpus`, 84 hand-labelled) plus `replay`, which prints the confusion matrix, precision/recall/F1 and ECE per gate and fails CI on a regression or on an adversarial log being classified deterministically. The first baseline and its open findings are published in `docs/REPLAY_REPORT.md`.
- 🛡️ **Untrusted logs are treated as untrusted**: a deterministic prompt-injection detector escalates (never skips the LLM) when the failure log addresses the judge, in all three runtimes — required by the adversarial corpus gate.
- 🤖 **CI triage Action** (`examples/github-action`): annotates a failed job with the category and the deterministic action, offline by default and never blocking a green run.
- 🎯 **Decision quality made explicit**: `uncertainty` per result (shape + escalation), `recovery` as structured data with an allowlist-backed safety flag, a focused slice instead of a raw log for the provider, state-level secret redaction, session memory in the gates and a bounded effort lease with a caller break-glass. All additive: no exit code or `skip_llm` changed.
- 🔀 **Tri-runtime parity is now enforced, not claimed**: `tests/fixtures/corpus_parity.json` locks 160 corpus cases × 6 gates across Python, TypeScript and Rust. Building it exposed and fixed real divergences, including a non-deterministic `HashMap` iteration order in the Rust mock.
- 📦 **Distribution**: host plugin bundles (Claude Code, Codex/OpenCode), an interop section with sourced dates, and an offline documentation link checker wired into CI.
- 🧭 **System 1.5 documentation**: architecture, ecosystem comparison and implementation plan are organized under `docs/system_1_5/` (`docs/system_1_5/SYSTEM_1_5_*.md`).
- 🔒 **Privacy/ops unchanged**: offline mode still makes zero network calls; degraded live answers are always labeled, never silent.

## 🌟 What's New in v0.1.14

- 🐛 **A mistyped `--log` path is no longer triaged as if it were the log text.** `jev-harness test-gate --log /missing/file` previously produced a fabricated `ENV_MISSING` / `skip_llm=true` verdict with exit `0`; it now exits `2` with a clear hint (use a positional argument, `--sample`, or stdin). Fixed in all three runtimes.
- 🪝 **No more false sense of protection after `init --git`.** When a foreign `pre-commit` hook is preserved, the CLI no longer prints a plain success message: it states that **the gate is not active until you merge `.git/hooks/pre-commit.jev`**.
- 📖 **Guide polish from a fresh-agent run**: the MCP smoke test shows the project-virtualenv absolute path, `init` documents exactly what it writes and that it must run inside a git repository, and exit code `2` now has a concrete example.
- 🧪 **211-Test Battery**: 100% pass rate across 211 tests (117 Python, 49 Rust, 45 TypeScript).

## 🌟 What's New in v0.1.13

- 🔌 **MCP integration actually works out of the box**: the guide now lists the **real** tool names and their arguments (`jev_triage_test_failure`, `jev_abort_check`, `jev_route_task`, `jev_verify_completion`, `jev_modulate_reasoning_effort`, `jev_should_nudge_continuation`), a 20-second smoke test, a valid `tools/call` example, a virtualenv note for client configs and an OpenCode snippet. The previous names (`jev_should_abort_trajectory`, `jev_route_model_tier`, `jev_verify_step_completion`, `jev_get_telemetry`) did not exist.
- 🪝 **`init --git` is virtualenv-aware**: the generated hook uses the project's environment binaries (`./.venv/bin/python`, `./.venv/bin/jev-harness`) when present, so a green suite is no longer blocked when the virtualenv is not activated, and `--test-cmd "<command>"` overrides the detected runner.
- 🛡️ **`init` never clobbers**: existing agent skills are preserved (like `.jev.json` and `.env.jev.example`), and only the hook it generated itself (marker, including pre-v0.1.13 variants) is regenerated.
- 📋 **MCP/CLI output parity**: the Python MCP server now returns `action_recommendation` alongside `recommendation` (and `summary` alongside `reasoning_summary`), matching the TypeScript runtime.
- 🧭 **Clearer onboarding**: the Quickstart states that **no API key is required** (offline mode is free and makes zero network calls), `status` guidance is fully in English, `.env.jev.example` lists every provider, and the README scopes `AGENTS.md` to people working on the repository itself.
- 🧪 **211-Test Battery**: 100% pass rate across 211 tests (117 Python, 49 Rust, 45 TypeScript). A fresh, context-free AI agent reproduced the full integration twice from the published docs; every gap it found is fixed here.

## 🌟 What's New in v0.1.12

- ✅ **Green runs never block or escalate**: a strict, deterministic success detector recognizes passing summaries from pytest, vitest, jest, cargo, go, mocha, rspec and unittest, returning `category: "no_failure"` with exit `0` and **zero API calls**. Real failures always veto the shortcut (`1 failed`, `FAILED`, tracebacks, panics, dependency/transient errors). This fixes false failures in pre-commit/husky recipes for JS and Rust projects.
- 🪝 **Working pre-commit integration**: `jev-test-gate` now takes your test command as `args` (the runner decides, Jev advises) through a console entry point that works from any consumer directory (a shell wrapper remains available for non-pre-commit users), and `jev-harness init --git` generates a runner-aware hook (npm/pytest/cargo) that uses `python3`, never overwrites an existing hook, and records the detected command.
- 🔐 **State files hardened**: `~/.config/jev` is created `0700` and `session.json` / the lock file are written `0600` (POSIX), so error snippets are no longer world-readable.
- 📖 **Documentation**: provider access and API-key acquisition for every backend (TypeSafe console, OpenCode Zen, Command Code, OpenRouter alpha, Vercel AI Gateway) with a **verification date** and re-check instructions for agents, plus an explicit privacy matrix (what leaves the machine in live vs offline mode).
- 🧪 **207-Test Battery**: 100% pass rate across 207 tests (113 Python, 49 Rust, 45 TypeScript).

## 🌟 What's New in v0.1.11

- 🐛 **Fixed a v0.1.10 classification regression**: a bare `RuntimeError:` / `ValueError:` / `TypeError:` line no longer masks a concrete dependency or transient root cause. Logs such as `RuntimeError: ... Caused by: ModuleNotFoundError` and `RuntimeError: ... Timeout` are triaged as `env_missing` / `flaky_transient` again (`skip_llm=true`), while real logic exceptions without an env/flaky root cause still escalate as `deep_logic`.
- 🌐 **Busy ports are flaky**: `Address already in use` / `EADDRINUSE` / `port already in use` (EN, PT-BR, ES) now classify as `flaky_transient`, matching the documented behaviour.
- ⚙️ **`.jev.json` is honored end-to-end**: `model`, `skip_llm_threshold` and `abort_threshold` take effect across Python, TypeScript and Rust (previously the file was scaffolded but silently ignored).
- 🔐 **No more auth CI crashes**: HTTP `401`/`403` from *any* provider degrades to offline simulation with a stderr warning and `is_mock=true`, instead of raising a traceback. Other failures (e.g. HTTP `500`) still surface as errors.
- 📊 **Honest ROI metrics**: the savings counters are labeled as heuristic estimates, the assumption model is printed, and `--json` exposes `estimates_are_heuristic`.
- 📖 **OpenRouter documented as alpha**: it requires approved alpha access; the endpoint and `typesafe/jev-1.13` model are not publicly listed, so it is no longer presented as a turnkey provider.
- 🧩 **Contract parity**: Standardized `workflow_phase` (`research`, `ask`, `plan`, `execute`, `verify`, `complete`) across CLI, SDK, and MCP outputs for `nudge-gate`.
- 🚦 **Release gate hardened**: `release.yml` now requires the full CI matrix (Linux/macOS/Windows, Python 3.9-3.13, Node 18-22, Rust) through a reusable workflow gate before publishing to PyPI, npm or crates.io — a red CI can no longer ship a release.
- 🧹 **Zero clippy warnings** across the Rust workspace.
- 🧩 **Tri-runtime heuristic parity**: the TypeScript engine now scores an explicit assertion exactly like Python and Rust, so the rules/04 precedence snippet (`FAIL` + cross-line `Expected:`/`Received:` containing a module name) is `deep_logic`/`skip_llm=false` on every runtime. Assertions spanning multiple lines are detected, and `Port 8080 is already in use`-style messages are `flaky_transient`.
- 🧪 **197-Test Battery**: 100% pass rate across 197 tests (107 Python, 47 Rust, 43 TypeScript) at v0.1.11; superseded by the 211-test battery in v0.1.12.

## 🌟 What's New in v0.1.10

- 🛡️ **Native Rust MCP Server (`packages/rust/src/mcp.rs`)**: High-performance JSON-RPC 2.0 stdio MCP server for the Rust runtime (`jev mcp` / `jev-harness mcp`), providing full feature parity with Python and TypeScript across all 6 decision gates.
- ⚡ **Atomic Concurrency File Locking (`fcntl.flock`)**: Robust transactional file locking in `session.py` guaranteeing zero metric corruption and 0.0% counter data loss under heavy concurrent agent executions.
- 🔄 **OpenCode Zen Live Auth Fallback**: Automatic graceful fallback to offline heuristic simulation on HTTP 401/403 when community dummy/zen keys are used, eliminating unhandled crashes in production.
- 🛠️ **CLI Subcommands Unification (`init` & `metrics`)**: Full cross-runtime availability of `init` (repo scaffolding & agent adapter generation) and `metrics` (session ROI and token telemetry) across Python, TS, and Rust.
- 📐 **Rigid JSON Schema & Contract Parity**: Ensured dual availability of `action_recommendation` + `recommendation` and `reasoning_summary` + `summary` across all CLI `--json` outputs and MCP tool invocations.
- 🧪 **149-Test Battery**: 100% test pass rate across 149 tests (86 Python, 34 Rust, 29 TypeScript) with sub-100µs latency in Rust.

---

## 🌟 What's New in v0.1.9

- 🆓 **Command Code Free Provider Integration**: Zero-cost live inference via Command Code ($0.00/M Deal - model `typesafe/jev`) with auto-auth detection from `~/.commandcode/auth.json` (`CMD_API_KEY`).
- 🚪 **6th Semantic Decision Gate (Continuation Nudge)**: Evaluates whether an autonomous agent paused prematurely with unfinished work or unverified changes, injecting targeted continuation nudges while vetoing nudges when waiting on user permission.
- 🔌 **CLI & MCP Support**: Subcommand `nudge-gate` (alias: `nudge`) and MCP tool `jev_should_nudge_continuation`.

---

## 🌟 What's New in v0.1.8

- 🏛️ **Astra-Ares v0.2.1 Protocol Parity**: Native endpoints for OpenRouter (`https://openrouter.ai/api/alpha/decisions`, model `typesafe/jev-1.13` with `provider: { only: ["typesafe"], allow_fallbacks: false }`), Vercel AI Gateway (`https://ai-gateway.vercel.sh/v1/evaluate`, model `typesafe-ai/jev` with `providerOptions: { gateway: { only: ["typesafe-ai"] } }` supporting `VERCEL_API_KEY`, `AI_GATEWAY_API_KEY`, `VERCEL_AI_GATEWAY_API_KEY`), TypeSafe AI direct (`https://api.typesafe.ai/v1/systemone`), and OpenCode Zen (`https://opencode.ai/zen/v1/systemone`).
- ⚡ **8-Level Reasoning Scale & Provider Dialects**: Support for `none`, `minimal`, `low`, `medium`, `high`, `xhigh`, `max`, `ultra` via `--supported-efforts` / `supportedEfforts`. Proper CoT disable mapping (`none` / `minimal`) across DeepSeek (`extra_body.thinking.type: disabled`), Qwen (`enable_thinking: false`), Anthropic (`thinking.type: disabled`), Kimi (`extra_body.thinking: false`), and MiMo (`thinking.type: disabled`).
- 🔄 **Multi-Generation Effort Leasing**: Multi-step stability leasing (`lease_steps` / `leaseSteps`: 1, 2, 5, 10 generations) with safe clamping (`max_lease_steps >= 1`), allocating 5 for mechanical tool calls, 1 for errors/tracebacks, and 2 for standard tasks.
- 🔒 **Zero-Trust Secret Redaction**: Automatic masking (`[REDACTED]`) of `Bearer ...`, `sk-...`, `vck_...`, and active API keys in all HTTP error messages and diagnostics across Python, TypeScript, and Rust.
- 🌐 **Polyglot & Multilingual Semantic Parity**: Uniform classification across 9 programming languages (Python, TypeScript/Node, Rust, Go, Java, C#, Ruby, C++) and 3 natural languages (EN, PT-BR, ES).
- 🛡️ **Red-Team Defense Hardening**: Collision resistance in `verify_step_completion` (never verifying real failures despite positive tokens) and `should_abort_trajectory` (never aborting forward progress), plus prompt injection mitigation in `modulate_reasoning_effort`.
- 🔌 **CLI & MCP Tooling Evolution**: `--supported-efforts` and `--max-lease-steps` supported across all 3 CLI binaries and native MCP server schemas with `lease_steps` in JSON responses.
- 🧪 **Expanded 138-Test Battery**: 100% test pass rate across 138 tests (79 Python, 31 Rust, 28 TypeScript) with latency p99 < 90µs in Rust.

---

## 🌟 What's New in v0.1.7

- 📊 **Empirical Tri-Runtime Latency Benchmarks & Verified < 500µs Guarantee**: Added comprehensive empirical latency benchmark tables ($p50$, $p95$, $p99 < 500\mu\text{s}$) across Python, TypeScript, and Rust, verified with 1,000-iteration automated test suites.
- ⚡ **Rust Engine Optimization**: Regex caching with `std::sync::LazyLock` and zero-allocation fallback client references in gates, dropping Rust triage $p99$ to **37.5µs** and pure System One simulation to **1.3µs**.
- 🛠️ **TypeScript CLI & Native MCP Full Parity**: Hardened Unix semantic exit code handling (code `2` on missing command or invalid arguments) and added dual camelCase + snake_case JSON field support across CLI commands and native MCP tools (`skip_llm`, `should_abort`, `provider_params`, `is_reasoning_supported`).
- 🚀 **In-Memory Heuristic Acceleration**: Added `record_session: bool = False` flag to decouple memory-only gate calls from filesystem I/O, achieving sub-150µs $p99$ latency in Python while preserving full telemetry on CLI executions.
- 🧪 **Complete 123-Test Battery**: 100% test pass rate across 123 tests (73 Python, 26 Rust, 24 TypeScript) with zero compiler warnings.

---

## 🌟 What's New in v0.1.6

- 🛡️ **Expanded Direct Model Safeguards**: Automatically identifies non-reasoning direct execution models (`gpt-4o`, `gpt-4o-mini`, `gemini-2.5-flash`, `gemini-2.0-flash`, `claude-3-5-haiku`, `qwen-2.5-coder`, `llama-3.3`, etc.), injecting `{}` to prevent fatal HTTP 400 Bad Request parameter rejections across all 3 runtimes.
- 🧠 **Active Session Context Tokens & Cache Risk Warning**: Added `--session-context-tokens` parameter to CLI and MCP tool. Emits proactive `HIGH CACHE RISK` advisory when session context exceeds 30,000 tokens to protect Prompt Cache (KV Cache) prefix hit rates.
- 💻 **TypeScript CLI `reasoning-effort` & Zero-Dependency Native MCP Server**: Added full native CLI command support (`npx @ismaelsoilet/jev-harness reasoning-effort`) and zero-dependency stdio MCP server (`npx @ismaelsoilet/jev-harness mcp`) matching Python and Rust.
- 🧪 **Hardened Adversarial Heuristics & 122-Test Battery**: Hardened regex matching for Jest and Pytest logs where `AssertionError` contains module names (guaranteeing `deep_logic` and `skip_llm=false`), preventing premature aborts on forward-progress implementation steps, and reaching 100% pass across 122 tests (73 Python, 25 Rust, 24 TypeScript).
- 🌐 **OpenRouter & Provider Enhancements**: Updated OpenRouter fallback model to `google/gemini-2.5-flash` with direct provider configuration options.

---

## 🌟 What's New in v0.1.5

- ⚡ **Astra-Jev Dynamic Reasoning Effort Governance**: Pioneered from Vechen (@miu21590) with native Jev System One semantic governance. Modulates per-generation reasoning effort in <500µs local (remote latency depends on the provider; provider-claimed 70ms floor).
- 🌐 **2026 Frontier Models & Dialect Compiling**: Full provider parameters dialect mapping across OpenAI (`reasoning_effort`), Anthropic (`thinking.type: adaptive`, `output_config.effort`), Gemini (`thinking_level`), DeepSeek (`extra_body.thinking: enabled`, preserving `reasoning_content`), Qwen (`enable_thinking`, `thinking_budget`), Kimi, and Xiaomi MiMo.
- 🛡️ **Zero-Failure Model Safeguards**: Automatically detects direct single-pass models (`gpt-5.6-luna`, `gemini-3.8-live`) to prevent fatal HTTP 400 Bad Request rejections.
- 🧠 **Prompt Cache (KV Cache) Advisories**: Includes cache-safety recommendations to prevent prefix cache invalidation across 100k+ token sessions.
- 🔌 **Universal MCP Tool & CLI Subcommand**: Added `jev_modulate_reasoning_effort` MCP tool and `jev-harness reasoning-effort` / `astra-jev` CLI command with telemetry tracking.
- 🧪 **Comprehensive 94-Test Battery**: 100% test pass rate across Python (62 tests), Rust (18 tests), and TypeScript (14 tests) with zero external runtime dependencies.

---

## 🌟 What's New in v0.1.4

- 🎨 **100% Visual & Badge Standardization**: Standardized all badges across PyPI, npm, and Crates.io with official logos, official colors, docs.rs and Sigstore provenance links.
- 🔐 **Zero-Token npm Trusted Publishing**: Fully migrated npm release workflow to OpenID Connect (OIDC) Trusted Publishing with Sigstore signed provenance statements. No expiring tokens required.
- ⚡ **Cross-Runtime CLI Unification**: Standardized subcommands (`test-gate`, `triage`, `abort-check`, `abort`, `route`, `verify`, `status`) and argument parsing (positional or flags) across Python, TypeScript (`@ismaelsoilet/jev-harness`), and Rust (`jev`).
- 🧪 **Comprehensive 82-Test Battery**: 100% test pass rate across Python (54), TypeScript (13), and Rust (15), covering adversarial inputs, Portuguese & English tracebacks, and UTF-8 truncations.
- 📦 **Tri-Registry Synchronization**: Crates.io, npm, and PyPI synchronized with automated GitHub Actions CD release.
- 🛡️ **Cross-Platform Test & Runtime Hardening**: Resilient HTTP/network handling across Python 3.9 through 3.13, Node 18 through 22, and Rust stable.

---

## 🙏 Acknowledgements

- **[Astra-Ares](https://github.com/miuuyy/Astra-Ares)** by Vechen ([@miu21590](https://x.com/miu21590)): Inspiration for per-generation reasoning effort modulation, multi-generation effort leasing (`lease_steps`), provider dialect mapping, and zero-trust secret redaction in error messages.
- **TypeSafe AI**: Creators of the Jev System One decision architecture.

---

## 📄 License

Distributed under the **MIT License**. See [`LICENSE`](LICENSE) for more information.
