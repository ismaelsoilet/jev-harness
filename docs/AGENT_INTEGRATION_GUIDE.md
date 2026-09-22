# 🤖 Jev Harness: Universal AI Agent Integration Guide

**[ 🇬🇧 English ](AGENT_INTEGRATION_GUIDE.md) | [ 🇧🇷 Português ](AGENT_INTEGRATION_GUIDE.pt-BR.md)**

> **Turnkey implementation playbook for autonomous AI coding agents (Cursor, Claude Code, Antigravity, OpenCode, Windsurf, Zed, Devin, Aider) and engineers equipping agentic workflows in ANY project.**

---

## 🧭 Overview: Why Integrate Jev Harness?

Autonomous AI coding agents burn **70% to 80% of their token budget and execution time** on mechanical, predictable failures:
1. **Missing packages & environment errors** (`ModuleNotFoundError`, `Cannot find module`, `E0463`). Agents routinely dump 500 lines of traceback into frontier models (GPT-6 Astra, Claude Fable 5.1), spending $0.50–$2.50 just to get `npm install` or `pip install`.
2. **Circular doom loops**: An agent retrying the same flawed refactoring 4 times, burning 200k+ tokens before failing.
3. **Internal reasoning latency**: Reasoning models (DeepSeek V4.1-Flash, Qwen 3.8 Max, o3-mini) entering 3-minute chain-of-thought loops just to run `git status` or read a 10-line file.

**`jev-harness` is the System 1 cognitive reflex for AI agents**:
- **70ms remote / <500µs local latency** (non-autoregressive typed decision engine).
- **$0.042 per 1M input tokens / $0.00 output tokens** (up to **238x cheaper** than frontier models).
- **Zero external runtime dependencies** across Python (pure stdlib), TypeScript (zero dependencies), and Rust (Tokio/Serde).
- **Instant offline simulation fallback**: runs locally even without an API key or internet connection.

---

## ⚡ Quickstart: 4 Universal Integration Modes

Choose the mode that fits your agent's execution environment:

```
                  ┌────────────────────────────────────────────────────────┐
                  │                 YOUR PROJECT REPOSITORY                │
                  └──────────────────────────┬─────────────────────────────┘
                                             │
             ┌───────────────────────────────┼───────────────────────────────┐
             ▼                               ▼                               ▼
    [Mode 1: MCP Server]           [Mode 2: Shell / CLI Pipe]       [Mode 3: Native SDK]
   Cursor, Claude Desktop,            pytest | jev-harness           Python / TS / Rust
    Antigravity, Windsurf            npm test | npx ...              Custom Agent Loops
```

---

### Mode 1: Universal MCP Server (Zero Code, Highest Capability)

If your agent runs inside an MCP-compatible environment (**Cursor, Claude Desktop, Antigravity IDE, Windsurf, Zed, OpenCode**), expose Jev tools over standard I/O in 30 seconds.

#### 1. Configuration Snippet

**For Cursor (`.cursor/mcp.json` in project root or `~/.cursor/mcp.json` globally):**
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
*(Or if Python is installed: `"command": "jev-mcp"`)*

**For Claude Desktop (`claude_desktop_config.json`):**
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

**For Google Antigravity IDE (`mcp_config.json`):**
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

#### 2. Tools Available to the Agent via MCP:
- `jev_triage_test_failure`: Analyzes raw error output. Returns whether to skip LLM and what deterministic shell action to execute.
- `jev_should_abort_trajectory`: Evaluates whether the agent's proposed plan is repeating previous failures (doom loop breaker).
- `jev_route_model_tier`: Suggests whether to use a local script, fast tier (Gemini 3.8 Flash), or frontier tier (Claude Fable 5.1 / GPT-6 Astra).
- `jev_verify_step_completion`: Deterministically evaluates whether step criteria were satisfied.
- `jev_modulate_reasoning_effort`: Dynamically configures per-generation reasoning effort (`low`, `medium`, `high`) and compiles provider-specific payloads for OpenAI, Anthropic, Gemini, DeepSeek, and Qwen.
- `jev_get_telemetry`: Reports session token savings, frontier dollars saved, and intercepted doom loops.

---

### Mode 2: Shell & CLI Pipelines (Language-Agnostic)

If your agent executes commands via a terminal tool (e.g. bash, zsh, pwsh), wrap your test commands using Unix pipes:

```bash
# Python / Pytest
pytest 2>&1 | jev-harness test-gate

# Node.js / Jest / Vitest / npm
npm test 2>&1 | npx @ismaelsoilet/jev-harness test-gate

# Rust / Cargo
cargo test 2>&1 | jev test-gate
```

#### Semantic Exit Codes:
- `0`: **Safe to proceed deterministically** (`skip_llm = true`). Jev outputs the exact fix (e.g. `pip install pytest-mock`).
- `1`: **Deep logic failure** (`skip_llm = false`) or **Trajectory Abort Recommended**. Only now should the agent invoke a frontier reasoning model.
- `2`: Syntax or invocation error.

#### Automated Trajectory Guard (Check before repeating steps):
```bash
jev-harness abort-check \
  --plan "Re-run database migration with forced schema reset" \
  --history "Attempt 1 timed out. Attempt 2 failed on foreign key constraint."
```
*If this returns exit code `1`, the agent MUST abort the path and re-align with the user.*

---

### Mode 3: Native SDK Integration (For Agent Frameworks)

If you are developing a custom agent loop (LangChain, LlamaIndex, CrewAI, AutoGen, or custom TypeScript/Python/Rust pipelines):

#### Python (`pip install jev-harness`)
```python
from jev_harness import JevClient, triage_test_failure, should_abort_trajectory, modulate_reasoning_effort

client = JevClient()

# 1. Triage test traceback before calling LLM
triage = triage_test_failure(raw_traceback, client=client)
if triage.skip_llm:
    # Execute deterministic fix without burning frontier tokens
    execute_shell_command(triage.action_recommendation)
else:
    # Only forward targeted failure to frontier model
    call_frontier_llm(triage.action_recommendation)

# 2. Check for doom loops before repeating steps
abort = should_abort_trajectory(proposed_step, history_summary, client=client)
if abort.should_abort:
    notify_user_dead_end(abort.reasoning_summary)

# 3. Modulate reasoning effort (Astra-Jev)
effort = modulate_reasoning_effort(
    context="git diff to check changed files",
    provider="deepseek",
    model="deepseek-v4.1-flash",
    client=client,
)
# Inject effort.provider_params into API payload
```

#### TypeScript / Node.js (`npm install @ismaelsoilet/jev-harness`)
```typescript
import { triageTestFailure, shouldAbortTrajectory, modulateReasoningEffort } from "@ismaelsoilet/jev-harness";

// 1. Triage
const triage = await triageTestFailure(errorOutput);
if (triage.skipLlm) {
  await runShell(triage.actionRecommendation);
}

// 2. Abort check
const abort = await shouldAbortTrajectory(nextAction, pastAttempts);
if (abort.shouldAbort) {
  throw new Error(`Trajectory stopped by Jev: ${abort.reasoningSummary}`);
}

// 3. Astra-Jev dynamic effort
const effort = await modulateReasoningEffort("Mechanical file rename", "anthropic");
// Pass effort.providerParams to Anthropic SDK
```

#### Rust (`cargo add jev-harness`)
```rust
use jev_harness::gates::{triage_test_failure, should_abort_trajectory, modulate_reasoning_effort};

let triage = triage_test_failure(error_log, None).await?;
if triage.skip_llm {
    apply_deterministic_fix(&triage.action_recommendation);
}
```

---

### Mode 4: Git & CI/CD Guardrails

Protect your repository automatically before commits or CI runs:

**In `.pre-commit-config.yaml`:**
```yaml
repos:
  - repo: https://github.com/ismaelsoilet/jev-harness
    rev: v0.1.6
    hooks:
      - id: jev-test-gate
```

**In GitHub Actions (`.github/workflows/ci.yml`):**
```yaml
- name: Run Tests with Jev Gate Guard
  run: |
    npm test 2>&1 | npx @ismaelsoilet/jev-harness test-gate
```

---

## 🧠 The Agent Decision Protocol (Operational Rules)

To make your agent completely autonomous and token-frugal, inject these 3 operational rules into your agent's system instructions:

```
                           [Agent Encounters Test/Build Failure]
                                             │
                                             ▼
                               ┌───────────────────────────┐
                               │   jev-harness test-gate   │
                               │  (System 1 Fast Decision) │
                               └─────────────┬─────────────┘
                                             │
                      ┌──────────────────────┴──────────────────────┐
                      ▼                                             ▼
             [skip_llm = true]                             [skip_llm = false]
       (Missing Package / Flaky / Trivial)                  (Deep Logic Bug)
                      │                                             │
                      ▼                                             ▼
         Execute Deterministic Action                 Send Filtered Error Log
          (e.g. npm install / retry)                   to Frontier Model (System 2)
       ⚡ 0 Tokens Burned / Instant Fix              💸 Tokens Saved by ~80%
```

### Rule 1: Zero-LLM Triage on Failures
- **NEVER** forward raw tracebacks (>20 lines) directly to a frontier reasoning model.
- Always run `jev-harness test-gate` (or the MCP tool `jev_triage_test_failure`) first.
- If `skip_llm == true`, execute the deterministic action provided in `action_recommendation`.

### Rule 2: Circuit Breaker on Repetitive Actions
- If an operation fails twice in a row, the agent **MUST** run `jev-harness abort-check` (or `jev_should_abort_trajectory`).
- If `should_abort == true`, the agent must **HALT**, explain the dead end to the user, and ask for directional guidance instead of burning further tokens in a loop.

### Rule 3: Per-Generation Reasoning Modulation (Astra-Jev)
- For mechanical operations (`git status`, reading files, formatting, simple edits), set reasoning effort to `low` or disable thinking to eliminate 3-minute latency and save up to $1.15 per call.
- Use `high` reasoning only when designing architecture, solving multi-file race conditions, or writing complex algorithms.

---

## 📋 Ready-to-Paste Agent Rules Snippets

Copy the appropriate snippet directly into your project's agent configuration file:

### For Cursor (`.cursorrules` or `.cursor/rules/jev.mdc`):
```markdown
# Jev Harness Token Optimization Protocol

Before spending tokens on test or compilation failures:
1. Always pipe the test output through `jev-harness test-gate` or invoke the MCP tool `jev_triage_test_failure`.
2. If `skip_llm` is true, immediately execute the recommended action without querying the model.
3. If a task fails across 2 consecutive attempts, invoke `jev_should_abort_trajectory` before proposing a third attempt.
4. If `should_abort` is true, halt execution and report the blocked trajectory to the user.
```

### For Claude Code / Claude Desktop (`CLAUDE.md`):
```markdown
# Agent Optimization & Safety Protocol
- Triage test errors using `jev-harness test-gate --log <file>` or MCP tool `jev_triage_test_failure`.
- When `skip_llm` is true, execute the deterministic command (e.g. missing package install). Do not deliberate.
- Prevent doom loops by checking proposed recovery steps with `jev-harness abort-check`.
```

### For Google Antigravity IDE (`GEMINI.md` or `.agents/rules/`):
```markdown
# Token Economy & Gate Safeguards
- Always triage compiler and test failures using `jev-harness test-gate`.
- Adhere strictly to `skip_llm` verdicts to preserve quota.
- Guard long-running trajectories against circular dead ends with `jev-harness abort-check`.
```

---

## 📊 Economics & Impact

| Action | Standard Agent Loop | Agent Loop with Jev Harness | Impact |
| :--- | :--- | :--- | :--- |
| **Missing Module Error** | Sends 300 lines to Claude Fable 5.1 (~50k tokens, ~$0.80) | Jev triages in 80ms (`$0.00004`). Installs package. | **99.9% cost reduction, 15s saved** |
| **Transient Network Flake** | Rewrites network config or hallucinating changes | Jev detects flake. Retries command once. | **Zero unnecessary code changes** |
| **3-Turn Circular Doom Loop**| Consumes 180k+ tokens, leaves repo in corrupted state | Jev aborts on turn 2 (`exit 1`). Trajectory halted. | **Saves ~$5.00, prevents repo damage** |
| **Tool Calling Reasoning Latency** | DeepSeek/Qwen waits 180s in internal CoT for `git status` | Astra-Jev sets `effort="low"`. Finishes in 1.5s. | **178s latency eliminated** |

---

## 🔗 Related Resources

- 🏛️ [System Blueprint & Architecture](../AGENTS.md)
- 🌐 [Frontier Model Governance (2026)](../.agents/rules/03_model_governance_and_frontier_registry.md)
- 📦 [GitHub Repository](https://github.com/ismaelsoilet/jev-harness)
- 🐍 [PyPI Package](https://pypi.org/project/jev-harness/)
- 🟦 [npm Package](https://www.npmjs.com/package/@ismaelsoilet/jev-harness)
- 🦀 [crates.io Package](https://crates.io/crates/jev-harness)
