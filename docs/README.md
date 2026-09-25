# 📚 Jev Harness Documentation Hub

**[ 🇬🇧 English ](README.md) | [ 🇧🇷 Português ](README.pt-BR.md)**

> **Welcome to the documentation catalog for `jev-harness`** — the deterministic System 1.5 decision layer, token optimizer, and semantic guardrail for AI coding agents.

---

## 🧭 Navigation by Role & Objective

Find exactly what you need based on what you are building:

| I want to... | Recommended Document | Language | Description |
| :--- | :--- | :--- | :--- |
| **Plug Jev into my IDE / agent** | [Universal Agent Integration Guide](AGENT_INTEGRATION_GUIDE.md) | [🇬🇧](AGENT_INTEGRATION_GUIDE.md) · [🇧🇷](AGENT_INTEGRATION_GUIDE.pt-BR.md) | 2-minute turnkey setup for Cursor, Claude Code, Antigravity, OpenCode, Zed, Windsurf via MCP or CLI. |
| **Understand System 1.5 architecture** | [System 1.5 Architecture Plan](system_1_5/SYSTEM_1_5_PLAN.md) | 🇧🇷 (with EN summary) | Grounded facts, cognitive model (Kahneman System 1 → 1.5 → 2), and primary sources. |
| **Compare ecosystem tools** | [Ecosystem & Opportunities](system_1_5/SYSTEM_1_5_OPPORTUNITIES.md) | 🇧🇷 (with EN summary) | Direct comparison with Foreman, JevRouter, Winnow, and jev-guard. 21 prioritized opportunities. |
| **Inspect implementation roadmap** | [System 1.5 Implementation Plan](system_1_5/SYSTEM_1_5_IMPLEMENTATION.md) | 🇧🇷 (with EN summary) | Phased horizons (H1 delivered in v0.2.0, H2, H3), acceptance criteria, and test contracts. |
| **Supervise agents with Foreman** | [Foreman Integration Guide](integrations/foreman.md) | [🇬🇧](integrations/foreman.md) · [🇧🇷](integrations/foreman.pt-BR.md) | Dual-loop supervision, extension entrypoint, stagnation breaker, and operator bundle. |
| **Verify benchmarks & calibration** | [Replay & Benchmark Report](REPLAY_REPORT.md) | 🇬🇧 | 160-case labelled corpus, confusion matrix, precision/recall/F1, and ECE calibration. |
| **Check release history** | [Release Notes v0.2.0](RELEASE_NOTES_v0.2.0.md) | 🇬🇧 | Changes delivered in v0.2.0 across all 4 registries. |
| **Operate as an agent on this repo** | [AI Agent Constitution](../AGENTS.md) | [🇬🇧](../AGENTS.md) · [🇧🇷](../AGENTS.pt-BR.md) | Mandatory protocol, testing posture, frontier registry, and Quad-Sync release rules. |

---

## 📂 Repository Documentation Structure

```
jev-harness/
├── README.md                          # 🏠 Flagship English overview & quickstart
├── README.pt-BR.md                    # 🇧🇷 Flagship Portuguese overview & quickstart
├── AGENTS.md                          # 🤖 Operational manual & constitution for AI agents
├── AGENTS.pt-BR.md                    # 🇧🇷 Portuguese AI agent constitution
│
├── docs/                              # 📚 This Documentation Hub
│   ├── README.md                      # 🇬🇧 Documentation map & role-based index (this file)
│   ├── README.pt-BR.md                # 🇧🇷 Portuguese documentation map & index
│   ├── AGENT_INTEGRATION_GUIDE.md     # 🤖 Turnkey setup for any external project
│   ├── AGENT_INTEGRATION_GUIDE.pt-BR.md
│   ├── RELEASE_NOTES_v0.2.0.md        # 🚀 Release notes & delivered deliverables
│   ├── NOTORIETY_PR_STRATEGY.md       # 📢 Community & ecosystem engagement strategy
│   ├── REPLAY_REPORT.md               # 📊 Calibration benchmarks & confusion matrix
│   ├── REPLAY_REPORT.json             # 🔢 Raw replay dataset
│   │
│   ├── system_1_5/                    # 🧠 System 1.5 Architecture Trilogy
│   │   ├── README.md                  # 🧭 Trilogy overview & cognitive model
│   │   ├── SYSTEM_1_5_PLAN.md         # 🏛️ Architecture, target state & verified facts
│   │   ├── SYSTEM_1_5_OPPORTUNITIES.md # 🔭 Ecosystem landscape & 21 opportunities
│   │   └── SYSTEM_1_5_IMPLEMENTATION.md # 🛠️ Phased implementation plan (H1–H3)
│   │
│   └── integrations/                  # 🔌 Host & Runtime Integrations
│       ├── foreman.md                 # 🏭 Foreman autonomous supervisor integration
│       └── foreman.pt-BR.md           # 🇧🇷 Portuguese Foreman integration guide
│
└── .agents/rules/                     # 🛡️ Modular Engineering Standards
    ├── 01_project_blueprint.md        # System layout & monorepo tree
    ├── 02_software_engineering_principles.md # Karpathy, Fable, Unix philosophy
    ├── 03_model_governance_and_frontier_registry.md # 2026 models & safeguards
    ├── 04_testing_and_truthfulness.md # Zero-trust & 626-test battery
    ├── 05_release_and_quad_sync_protocol.md # Quad-Sync pipeline across 4 registries
    ├── 06_code_style_and_conventions.md # Python, TypeScript & Rust standards
    └── 07_mcp_quality_and_tdqs_standards.md # Glama TDQS A+ (5.0) MCP guidelines
```

---

## 🏛️ The System 1.5 Paradigm at a Glance

The repository operationalizes Daniel Kahneman's cognitive paradigm for autonomous agentic software engineering:

```
┌────────────────────────────────────────────────────────────────────────┐
│                   AI Coding Agent Execution Loop                       │
│     (OpenCode / Claude Code / Cursor / Windsurf / Antigravity IDE)     │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
                                 Execute
                                    │
                                    ▼
                         [Step / Test Execution]
                                    │
        ┌───────────────────────────┴───────────────────────────┐
        ▼                                                       ▼
  [✅ Pass: Continue]                                    [❌ Fail: Log]
                                                                │
  ══════════════════════════════════════════════════════════════╪════════════════════════
  🧠 SYSTEM 1.5: CONNECTIVE TISSUE & EXECUTIVE GOVERNANCE       │ (jev-harness)
  ──────────────────────────────────────────────────────────────┼────────────────────────
                                                                ▼
                                                ┌───────────────────────────────┐
                                                │ 1. Perception & Sanitization  │
                                                │  • Secret / Credential Masking│
                                                │  • Traceback Slicing (≤15 l)  │
                                                │  • Prompt-Injection Screener  │
                                                └───────────────┬───────────────┘
                                                                │
                                                                ▼
                                                ┌───────────────────────────────┐
                                                │ 2. Local Fast Heuristics      │
                                                │    (< 500 µs, Zero Cost)      │
                                                │  • Missing dependencies       │
                                                │  • Transient network / ports  │
                                                │  • Doom loop loop-breaker     │
                                                └───────────────┬───────────────┘
                                                                │
                                ┌───────────────────────────────┴───────────────────────────────┐
                                ▼                                                               ▼
                     [Deterministic Match]                                             [Uncertain / Ambiguous]
                                │                                                               │
                                ▼                                                               ▼
                 ┌─────────────────────────────┐                                ┌───────────────────────────────┐
                 │ 3. Instant Shell Action     │                                │ 4. TypeSafe Jev System One    │
                 │    (skip_llm = True)        │                                │    (70–150ms, $0.042/M tokens)│
                 │  • pip / npm / cargo install│                                └───────────────┬───────────────┘
                 │  • Single retry on flaky    │                                                │
                 │ ⚡ 0 LLM Tokens Spent       │                                                ▼
                 └─────────────────────────────┘                                ┌───────────────────────────────┐
                                                                                │ 5. Calibration & Entropy Gate │
                                                                                │  • Margins & Entropy Filter   │
                                                                                └───────────────┬───────────────┘
                                                                                                │
                                ┌───────────────────────────────────────────────────────────────┴───────────────────────────┐
                                ▼                                                                                           ▼
                      [Calibrated Skip]                                                                           [Deep Logic Defect]
                                │                                                                                           │
                                ▼                                                                                           ▼
                 ┌─────────────────────────────┐                                                             ┌─────────────────────────────┐
                 │ 0 Frontier Tokens           │                                                             │ 🧠 System 2: Frontier LLM   │
                 │ Instant Terminal Resolution │                                                             │ (GPT-6 Astra, Claude Fable) │
                 └─────────────────────────────┘                                                             │ Targeted trace / Full CoT   │
                                                                                                             └─────────────────────────────┘
```

---

## 🛠️ Semantic Decision Gates Reference

`jev-harness` exposes 6 semantic decision gates across Python, TypeScript, Rust, CLI, and MCP:

| Gate Name | CLI Command | MCP Tool Name | Primary Purpose |
| :--- | :--- | :--- | :--- |
| **`triage_test_failure`** | `test-gate` | `jev_triage_test_failure` | Evaluates terminal/test failures. Recommends deterministic fix (`skip_llm = true`) or escalates targeted slice to frontier LLM. |
| **`should_abort_trajectory`** | `abort-check` | `jev_check_abort` | Detects circular doom loops and repetitive failure patterns. Exits with code `1` to stop token drain. |
| **`route_model_tier`** | `route` | `jev_route_task` | Matches task complexity to the most economical capable model tier (local script → flash model → frontier model). |
| **`verify_step_completion`** | `verify` | `jev_verify_completion` | Evaluates evidence and test outputs against acceptance criteria to prevent false completion claims. |
| **`modulate_reasoning_effort`** | `reasoning-effort` | `jev_modulate_reasoning_effort` | Dynamically modulates thinking budget (`low` to `high`) per generation based on step complexity and multi-turn leases. |
| **`should_nudge_continuation`** | `nudge` | `jev_evaluate_nudge` | Evaluates whether a multi-step agent should be nudged to continue or allowed to terminate cleanly. |

---

## 📜 Maintenance and Freshness Policy

Per repository governance ([`AGENTS.md`](../AGENTS.md)):
1. **Freshness Guarantee**: All comparative facts, provider endpoints, and ecosystem numbers are audited at minimum every 30 days. Current verification date: **2026-09-23**.
2. **Automated Link Verification**: The repository runs an offline deterministic link checker (`python3 scripts/check_links.py --root .`) wired into CI to guarantee zero broken documentation links.
3. **Tri-Runtime Parity**: Any documentation mentioning API surfaces or CLI behavior applies identically across Python, TypeScript, and Rust runtimes.
