# 🤖 AGENTS.md: AI Agent Constitution and Operational Manual

**[ 🇬🇧 English ](AGENTS.md) | [ 🇧🇷 Português ](AGENTS.pt-BR.md)**

> **ATTENTION:** ANY autonomous artificial intelligence agent (Claude Code, OpenAI Codex / Astra-Codex, Pi, Oh My Pi, CommandCode, Cursor, Antigravity IDE, OpenCode, Windsurf, Zed, Devin, Aider) opening this repository **MUST READ THIS DOCUMENT** before planning, modifying code, or executing changes.
> 
> *Project Version: v0.1.8 — Synchronized across all 4 official registries.*

---

## 🧭 Quick Index of Modular Conventions and Rules

This document serves as the primary entry portal. The repository organizes its specialized and self-contained rules under [`.agents/rules/`](.agents/rules/):

1. 🏛️ **[System Architecture Blueprint](.agents/rules/01_project_blueprint.md)**: Directory mapping, tri-runtime layout (Python, TS, Rust), data pipelines, and zero-dependency contracts.
2. 🧠 **[Core Software Engineering Principles](.agents/rules/02_software_engineering_principles.md)**: Karpathy principles, Fable loop, Kahneman System 1 vs 2, Unix philosophy, and anti-Frankenstein architecture.
3. 🌐 **[Model Governance & 2026 Frontier Registry](.agents/rules/03_model_governance_and_frontier_registry.md)**: Golden rule against obsolete models, mandatory daily web research, provider dialects, and direct model safeguards.
4. 🛡️ **[Exhaustive Testing & Absolute Truthfulness](.agents/rules/04_testing_and_truthfulness.md)**: Zero-trust posture, prohibition of tautological tests, 122-test battery.
5. 🚀 **[Release Protocol & Quad-Sync Synchronization](.agents/rules/05_release_and_quad_sync_protocol.md)**: Synchronous pipeline across 4 registries (GitHub, PyPI, npm, Crates.io).
6. 📝 **[Code Style and Language Conventions](.agents/rules/06_code_style_and_conventions.md)**: Strict standards for Python (pure stdlib), TypeScript (native ESM), and Rust (Tokio 2021).
7. 🤖 **[Universal Agent Implementation Guide](docs/AGENT_INTEGRATION_GUIDE.md)** ([Português](docs/AGENT_INTEGRATION_GUIDE.pt-BR.md)): Step-by-step playbook to plug Jev Harness via MCP, CLI, or native SDK into any project in 2 minutes.

---

## 🏛️ 1. Project Blueprint (System Blueprint)

`jev-harness` solves the most expensive problem in agentic computing: **wasting frontier tokens on trivial mechanical failures and circular doom loops**.

### Tri-Runtime Architecture with Strict Semantic Parity:
* **Python Core (`src/jev_harness/`)**:
  - `client.py`: Ultra-resilient HTTP client using pure standard library (`urllib.request`), dynamic timeout, and offline heuristic simulation in **< 500µs**.
  - `gates.py`: Implementation of the 5 semantic decision gates (`triage_test_failure`, `should_abort_trajectory`, `route_model_tier`, `verify_step_completion`, `modulate_reasoning_effort`).
  - `mcp_server.py`: Universal stdio MCP server for direct integration with Cursor, Claude Desktop, and Antigravity IDE.
  - `cli.py`: Command-line interface (`jev-harness`) in strict compliance with Unix pipes.
  - `session.py`: Session telemetry, ROI calculation, and cache protection.
* **Rust Crate (`packages/rust/`)**:
  - High-performance implementation in stable Rust (Tokio + Serde), providing the `jev_harness` crate and standalone CLI binaries `jev` and `jev-harness`.
* **TypeScript Package (`packages/ts/`)**:
  - Native npm package `@ismaelsoilet/jev-harness` supporting Node.js, Bun, and Deno, exporting a typed SDK and CLI executable via `npx`.

---

## 🧠 2. Core Software Engineering Principles

Every agent operating in this repository must guide its decisions by five non-negotiable pillars:

### 1. Karpathy Principles for LLM Coding
* **Think Before Coding**: Do not assume. Do not conceal confusion. State assumptions and trade-offs explicitly before applying edits.
* **Simplicity First**: Deliver the minimum code that solves the current problem with excellence. Zero speculative code. No complex design patterns (Factory, Strategy) for a single use-case.
* **Surgical Changes**: Touch strictly what was requested. Never refactor, reformat, or change quotes in adjacent code outside the requested scope.
* **Goal-Driven Execution**: Turn tasks into verifiable success criteria. When fixing a bug, reproduce it with an automated test before implementing the patch.

### 2. Absolute Truthfulness and Zero-Trust Posture
* **NEVER TRUST BLINDLY, ALWAYS TEST AND VERIFY.**
* **IF SOMETHING SEEMS UNUSUAL, INVESTIGATE DOWN TO THE ROOT CAUSE.**
* Zero False Completion Claims. Report actual command output and observed test results before claiming any task is done.

### 3. Unix Philosophy and Tool Composition
* Semantic exit codes:
  - `0`: Success / Deterministic action identified (`skip_llm = true`).
  - `1`: Deep logic defect (`skip_llm = false`) or Trajectory abort recommended (`should_abort = true`).
  - `2`: Syntax error or invalid CLI arguments.

### 4. Zero External Runtime Dependencies in Core (Anti-Frankenstein Principle)
* The `jev-harness` core must **NEVER** introduce heavy runtime dependencies in Python (`requests`, `pydantic`, and `httpx` are prohibited) or in TypeScript (zero runtime `dependencies`).
* **No reverse HTTP proxy** should ever be bundled into the core. Astra-Jev provider parameter compilation is clean, typed, and static via `build_provider_params`.

---

## 🌐 3. Mandatory AI Model Governance: Prohibition of Outdated Data

> [!CAUTION]
> **MANDATORY FRONTIER RULE:** It is strictly prohibited to cite or use obsolete models (GPT-3.5, GPT-4, Gemini 1.0/1.5, Claude 2/3.0) as frontier model references.

1. **Active Web Research Required with Date Logged**: AI models and their parameters evolve weekly. Always search the web (`search_web`) before citing any model and explicitly record the **search date** in documentation. Unverified information or projections of unreleased future models (such as rumored Opus 5.2 or 5.5 versions) are **strictly forbidden** from being listed as active.
2. **Official Frontier Catalog (Verified via Web Research on September 22, 2026)**:
   * **OpenAI / Codex**: `gpt-6-astra`, `o3-mini`, `codex` (`reasoning_effort: "low" | "medium" | "high"`).
   * **Anthropic**: `claude-fable-5.1` (released 2026-09-01), `claude-opus-5` (released 2026-07-24) (`thinking: { type: "adaptive" }`). *(Governance note: Claude Opus 5 is the latest released model in the Opus family; versions 5.2 and 5.5 have not been released and must not be listed as available)*.
   * **DeepSeek**: `deepseek-v4.1-flash`, `deepseek-v4-pro`, `r1` (`extra_body.thinking: enabled`, preserving `reasoning_content`).
   * **Alibaba DashScope**: `qwen-3.8-max` (2.4T MoE), `qwen-3.8-omni-flash` (`enable_thinking: false` vs `true`).
   * **Google Gemini**: `gemini-3.8-flash-thinking`, `gemini-3.5-pro` (`thinking_config.thinking_level`).
   * **Moonshot**: `kimi-k3` (`extra_body: { thinking: false }` instant mode).
   * **Xiaomi**: `mimo-v2.6-pro`, `mimo-v2-flash` (`thinking: { type: "disabled" | "enabled" }`).
3. **Safeguard for Direct Models**: Single-pass models (`gpt-4o`, `gpt-4o-mini`, `gemini-2.5-flash`, `claude-3-5-haiku`, `llama-3.3`, etc.) that reject reasoning parameters with HTTP 400 are automatically detected, generating `{}` and setting `is_reasoning_supported = false`.
4. **Prompt Cache (KV Cache) Governance**: Do not mutate message history to inject reasoning metadata. Inject strictly at the root level of the API payload to preserve GPU prefix cache.

---

## 🚀 4. Strict Release Protocol and Pre-Push Verification (Quad-Sync)

> [!CAUTION]
> **INVIOLABLE PRE-PUSH GOLDEN RULE:** It is strictly prohibited for any agent or developer to run `git push` (commits or tags) without first executing the mandatory version parity verification:
> ```bash
> ./scripts/release.sh --verify-sync
> ```
> If any divergence exists between `pyproject.toml`, `packages/ts/package.json`, `packages/rust/Cargo.toml`, or `src/jev_harness/__init__.py`, the push is **immediately aborted**.

### Complete 6-Step Release Workflow:

```
[Code or Docs Modification]
        │
        ▼
[1. Run 122 Tests: ./scripts/release.sh --check]
        │ (If 100% Passing)
        ▼
[2. Synchronous Version Bump: ./scripts/release.sh --bump <version>]
        │
        ▼
[3. Rebuild Artifacts: npm run build (TS) & cargo build --release (Rust)]
        │
        ▼
[4. Rigid Parity Check: ./scripts/release.sh --verify-sync]
        │ (If 100% Synchronized)
        ▼
[5. Detailed Commit + Git Tag + Git Push origin main --tags]
        │
        ▼
[6. GitHub Release Polish + Active CD Monitoring]:
    - Create Release via `gh release create v<version>` with clean, professional notes
    - Strictly eliminate markdown spacing errors or careless typos
    - Monitor GitHub Actions (`gh run list --workflow=release.yml`) until all green
    - Validate availability across all 4 channels:
        1. GitHub: https://github.com/ismaelsoilet/jev-harness/releases
        2. PyPI: https://pypi.org/project/jev-harness/
        3. npm: https://www.npmjs.com/package/@ismaelsoilet/jev-harness
        4. Crates.io: https://crates.io/crates/jev-harness
```

> [!IMPORTANT]
> **PROHIBITION OF ORPHAN BUMPS AND MISALIGNED BADGES:**
> 1. Never alter versions in manifest files without creating the corresponding Git tag (`vX.Y.Z`) and GitHub Release. The repository must never have commits with bumped versions while the previous release is marked as "Latest".
> 2. Top-level badges in `README.md` must accurately reflect the published state across all 4 registries. Never tolerate broken badges, outdated cached versions, or broken hyperlinks.

---

## 🧹 5. Repository Maintenance and Hygiene

The repository must remain impeccably clean at all times:
* **Zero temporary files**: Never commit `*.log`, `*.tmp`, cache directories, or scratch files.
* **Updated examples**: Keep recipes under `examples/` synchronized with current API versions.
* **Living Documentation**: When altering any function signature in semantic gates, update all READMEs and rules in `.agents/rules/` immediately.

---

## 🤖 7. Implementing Jev Harness in Any Project (Agent Quickstart)

To implement `jev-harness` in **any external project** and prevent AI agents from burning 50,000+ tokens on trivial errors or getting trapped in circular doom loops:

Refer to our turnkey, copy-paste ready guide:
* 📖 **[Universal AI Agent Integration Guide (English)](docs/AGENT_INTEGRATION_GUIDE.md)**
* 📖 **[Guia Universal de Integração para Agentes (Português)](docs/AGENT_INTEGRATION_GUIDE.pt-BR.md)**

### 3-Step Summary for Any Project:
1. **Configure the MCP Server**: Add `"jev-harness": { "command": "npx", "args": ["-y", "@ismaelsoilet/jev-harness", "mcp"] }` to `.cursor/mcp.json` or `claude_desktop_config.json`.
2. **Pipe Test Runners**: Run `pytest 2>&1 | jev-harness test-gate` or `npm test 2>&1 | npx @ismaelsoilet/jev-harness test-gate`. If exit code is `0` (`skip_llm = true`), apply the deterministic fix without querying an LLM.
3. **Inject Agent Rules**: Paste the `.cursorrules`, `CLAUDE.md`, or `AGENTS.md` instructions from the guide to enforce token economy automatically.
