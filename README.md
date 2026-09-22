# ⚡ Jev Harness: The Token Optimizer & Decision Gate for AI Coding Agents

<p align="center">
  <a href="https://github.com/ismaelsoilet/jev-harness/actions/workflows/ci.yml"><img src="https://github.com/ismaelsoilet/jev-harness/actions/workflows/ci.yml/badge.svg" alt="CI Status"></a>
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
</p>

<p align="center">
  <b><a href="README.md">🇬🇧 English</a> | <a href="README.pt-BR.md">🇧🇷 Português</a></b>
</p>

> **Stop burning 50,000 frontier tokens on missing packages, network flakiness, and circular doom loops.**
>
> `jev-harness` is an ultra-fast, zero-dependency token optimizer, test failure triage gate, and semantic guardrail for AI coding agents (OpenCode, Command Code, Claude Code, Cursor, Antigravity IDE, Windsurf, Zed, and Pi). Powered by **TypeSafe AI's Jev System One** non-autoregressive decision model.
>
> 🤖 **Operating as an AI Agent?** You **MUST** read [`AGENTS.md`](AGENTS.md) ([Português](AGENTS.pt-BR.md)) before executing tasks, and refer to our [**Universal AI Agent Integration Guide**](docs/AGENT_INTEGRATION_GUIDE.md) to plug the harness into any project in 2 minutes.

---

## 🎯 The Problem

When an autonomous coding agent encounters a test failure or compiler error, the standard reaction is to dump 500 lines of raw traceback into an expensive frontier reasoning model (GPT-6 Astra, Claude Fable 5.1). 

| Failure Scenario | Without Jev Harness | With Jev Harness |
| :--- | :--- | :--- |
| **Missing dependency** (`ModuleNotFoundError`, `Cannot find module`, `TS2307`, `E0463`) | 💸 **50,000 LLM tokens burned** (~$0.50 - $2.50) + 15s delay to output `pip/npm install ...` | ⚡ **Jev triage in 90ms ($0.00004)** → Action: install package deterministically. **0 LLM tokens**. |
| **Flaky transient error** (network timeout, port busy, ECONNREFUSED) | 💸 LLM hallucinates architectural changes to "fix" an ephemeral glitch | ⚡ **Jev detects flaky transient** → Auto-retry worker once. **0 code changes**. |
| **Circular refactoring** (Doom Loop: attempting the same fix 3+ times) | 💸 **200,000+ tokens burned** in endless circular loops | 🛑 **Jev Abort Gate triggers** (`exit 1`) → Stops loop, alerts developer. |
| **Trivial typo / formatting** | 💸 Heavy reasoning frontier tier used for simple regex/typo | ⚡ **Jev Route** directs task to local script or Gemini 3.8 Flash. |

---

## 🏗️ How It Works: System One vs. System Two

Daniel Kahneman's cognitive paradigm applied to agentic engineering:
- **System 1 (Fast, Intuitive, Calibrated):** **Jev** makes non-autoregressive, parallel, typed decisions in **70ms to 300ms** at **$0.042 per 1M tokens** ($0 output tokens).
- **System 2 (Slow, Deliberative, Generative):** Frontier LLMs (GPT-6 Astra, Claude Fable 5.1) write code and solve deep algorithmic logic.

```
       ┌────────────────────────────────────────────────────────┐
       │                 AI Coding Agent Loop                   │
       └──────────────────────────┬─────────────────────────────┘
                                  │
                       Command/Test Execution
                                  │
                                  ▼
                         [Test / Step Output]
                                  │
         ┌────────────────────────┴────────────────────────┐
         ▼                                                 ▼
   [PASS: Continue]                                 [FAIL: Error Log]
                                                           │
                                                           ▼
                                               ┌───────────────────────┐
                                               │   jev-harness gate    │
                                               │ (Jev System One 70ms) │
                                               └───────────┬───────────┘
                                                           │
                        ┌──────────────────────────────────┴──────────────────────────────────┐
                        ▼                                                                     ▼
             [skip_llm = True]                                                         [skip_llm = False]
      (Env missing / Flaky / Trivial)                                                    (Deep Logic Bug)
                        │                                                                     │
                        ▼                                                                     ▼
           Deterministic Shell Action                                                 Dispatch Targeted
        (pip/npm install or fast retry)                                            Trace to Frontier LLM
     ⚡ 0 Frontier Tokens / Instant Fix                                          💸 Cost Reduced by ~80%
```

---

## ✨ Features

- 🛡️ **Zero External Dependencies:** Built entirely with Python's standard library (`urllib.request`, `dataclasses`, `json`). No `pip` bloat, instant startup (< 50ms).
- 🔌 **Universal MCP Server:** Exposes Jev decision tools over stdio (`jev-mcp`) for Cursor, Claude Desktop, Antigravity, Windsurf, Zed, and OpenCode.
- 🚦 **UNIX Philosophy Compliant:** Standard exit codes (`0` for safe/skip_llm, `1` for abort/logic defect, `2` for syntax error) allow clean pipe composition: `pytest | jev-harness test-gate`.
- 🔄 **Autonomous Simulation Fallback:** If offline or without an API key, an intelligent heuristic engine runs locally so your CI and scripts never crash.
- 🌐 **Multi-Provider Support:** Seamlessly connects to TypeSafe AI direct, OpenCode Zen, or OpenRouter.

---

## 🚀 Quickstart

### 1. Installation Across Ecosystems
Available on all three major package registries with zero external runtime dependencies:

| Ecosystem | Registry | Package / Command | Status |
| :--- | :--- | :--- | :--- |
| **Python** | [PyPI](https://pypi.org/project/jev-harness/) | `pip install jev-harness` | [![PyPI](https://img.shields.io/pypi/v/jev-harness.svg?color=blue&logo=pypi&logoColor=white&cacheSeconds=300)](https://pypi.org/project/jev-harness/) |
| **TypeScript / Node** | [npm](https://www.npmjs.com/package/@ismaelsoilet/jev-harness) | `npm install @ismaelsoilet/jev-harness` | [![npm](https://img.shields.io/npm/v/@ismaelsoilet/jev-harness.svg?color=cb3837&logo=npm&logoColor=white)](https://www.npmjs.com/package/@ismaelsoilet/jev-harness) |
| **Rust** | [crates.io](https://crates.io/crates/jev-harness) | `cargo add jev-harness` | [![crates.io](https://img.shields.io/crates/v/jev-harness.svg?color=dea584&logo=rust&logoColor=white)](https://crates.io/crates/jev-harness) |

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
| **OpenCode Zen (Free Tier)** | `https://opencode.ai/zen/v1/systemone` | **$0.00 / Free** | `export OPENCODE_API_KEY=zen` or auto-selected |
| **TypeSafe AI (Direct)** | `https://api.typesafe.ai/v1/systemone` | $0.042 / 1M | `export TYPESAFE_API_KEY=your-key` |
| **OpenRouter Adapter** | `https://openrouter.ai/api/v1/chat/completions` | By Model | `export OPENROUTER_API_KEY=your-key` |
| **Autonomous Simulation** | Local Heuristics (< 500µs) | **$0.00** | Active by default if no key or offline |

Credential resolution priority:
1. Environment variables (`TYPESAFE_API_KEY`, `OPENCODE_API_KEY`, or `OPENROUTER_API_KEY`)
2. Local repository `.jev.json` or `.env`
3. Global configuration `~/.config/jev/credentials.env`
4. **Autonomous Simulation Fallback** (ensures your CI, agents, and scripts never crash)

```bash
# Check current connection & provider status anytime
jev-harness status
```

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

### 6. ROI & Token Savings Telemetry (`metrics`)
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
Estimated Tokens Saved:          422,200 tokens
Estimated Frontier Dollars Saved: $6.12 USD
============================================================
```

### 7. One-Command Agent Setup (`init`)
Automatically scaffold MCP configurations for your active agent or IDE:

```bash
# Setup for Cursor
jev-harness init --cursor

# Setup for Antigravity IDE
jev-harness init --antigravity

# Setup git pre-commit hook
jev-harness init --git

# Setup all supported tools at once
jev-harness init --all
```

---

## ⚡ Astra-Jev: Dynamic Reasoning Effort Governance (2026 Frontier Models)

Inspired by Vechen's ([@miu21590](https://x.com/miu21590)) groundbreaking work on *Astra-Codex*, **Astra-Jev** introduces autonomous, per-generation reasoning effort modulation governed by TypeSafe Jev System One.

Instead of locking an entire multi-turn coding session into heavy, slow reasoning (or risking bugs by running exclusively in low reasoning), Astra-Jev evaluates the cognitive demand of the immediate next generation in **< 500µs locally (70ms remote)**.

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
- If a task retries twice without progress, call `jev_should_abort_trajectory` to break doom loops.
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
Inject the resulting `reasoning_effort: "low" | "medium" | "high"` into the root API payload. Zero message mutation = 100% prompt cache preserved across 50+ turns.

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
jev-harness = "0.1.7"
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
```yaml
repos:
  - repo: https://github.com/ismaelsoilet/jev-harness
    rev: v0.1.7
    hooks:
      - id: jev-test-gate
```

### Husky Hook (`.husky/pre-commit`)
```bash
npm test 2>&1 | jev-harness test-gate || exit 1
```

---

## 📊 Economics & Benchmarks (September 2026 Frontier)

### Token & Cost Economics

| Metric | 2026 Frontier Reasoning (GPT-6 Astra, Claude Fable 5.1) | Fast Agentic Tier (Gemini 3.8 Flash) | TypeSafe Jev System One (`jev-harness`) |
| :--- | :--- | :--- | :--- |
| **Input Pricing** | $10.00 / 1M tokens | $0.75 / 1M tokens | **$0.042 / 1M tokens (~238x cheaper)** |
| **Output Pricing** | $50.00 / 1M tokens | $3.75 / 1M tokens | **$0.00 (Free - Non-autoregressive)** |
| **Latency** | 10,000ms – 30,000ms | 1,500ms – 4,000ms | **70ms – 300ms (~100x faster)** |
| **Output Structure**| Free-form prose & streaming tokens | Structured JSON tool calls | **Strictly typed: Choice, Score, Noul** |
| **Determinism** | Stochastic reasoning | Stochastic generation | **Zero-hallucination calibrated bounds** |

### Tri-Runtime Offline Heuristic Latency Benchmarks (< 500µs Local Guarantee)

When operating in offline simulation mode (`--mock` or during network partitions), `jev-harness` executes local System One decision gates with zero external network overhead. All gates strictly satisfy the **$p99 < 500\mu\text{s}$** contract across all three runtimes ($N = 1,000$ iterations empirically measured):

| Runtime | Decision Gate | $p50$ | $p95$ | $p99$ | Mean | Spec Compliance |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: |
| **Rust** (`packages/rust`) | `triage_test_failure` | **10.3 µs** | **22.0 µs** | **37.5 µs** | 13.5 µs | ✅ **PASS** (< 38 µs) |
| | `should_abort_trajectory` | **6.2 µs** | **10.0 µs** | **22.9 µs** | 7.0 µs | ✅ **PASS** (< 23 µs) |
| | `modulate_reasoning_effort` | **5.1 µs** | **7.1 µs** | **15.3 µs** | 5.6 µs | ✅ **PASS** (< 16 µs) |
| | *pure `simulate_system_one`* | **0.7 µs** | **0.9 µs** | **1.3 µs** | 1.0 µs | ✅ **PASS** (< 2 µs) |
| **TypeScript** (`packages/ts`) | `triageTestFailure` | **13.6 µs** | **37.5 µs** | **213.9 µs** | 26.9 µs | ✅ **PASS** (< 214 µs) |
| | `shouldAbortTrajectory` | **7.8 µs** | **21.6 µs** | **93.7 µs** | 10.5 µs | ✅ **PASS** (< 94 µs) |
| | `modulateReasoningEffort` | **6.3 µs** | **17.1 µs** | **89.4 µs** | 9.0 µs | ✅ **PASS** (< 90 µs) |
| **Python** (`src/jev_harness`) | `triage_test_failure` | **53.5 µs** | **95.0 µs** | **135.6 µs** | 63.1 µs | ✅ **PASS** (< 136 µs) |
| | `should_abort_trajectory` | **37.0 µs** | **67.1 µs** | **88.8 µs** | 42.3 µs | ✅ **PASS** (< 89 µs) |
| | `modulate_reasoning_effort` | **33.7 µs** | **62.6 µs** | **103.7 µs** | 41.0 µs | ✅ **PASS** (< 104 µs) |

> ⚡ **Zero-Overhead Guarantee:** Because heuristic checks execute in tens of microseconds, piping test runners or pre-execution hooks through `jev-harness` introduces undetectable overhead into agent loops while preventing runaway token costs and circular doom loops.

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
# 1. Run full test battery (Python, TS, Rust - 122 tests)
./scripts/release.sh --check

# 2. Synchronously bump version in pyproject.toml, package.json, and Cargo.toml
./scripts/release.sh --bump 0.1.6

# 3. Publish to a specific registry or all at once:
./scripts/release.sh --publish rust    # Publishes to crates.io
./scripts/release.sh --publish npm     # Publishes to npm (@ismaelsoilet/jev-harness)
./scripts/release.sh --publish python  # Builds wheel/sdist for PyPI

# 4. Create git tag and push to GitHub
./scripts/release.sh --git-tag 0.1.6
```

### 2. Automated GitHub Actions CD (`.github/workflows/release.yml`)
You can also trigger releases via GitHub Actions:
- **Automatic:** Pushing any tag matching `v*.*.*` (e.g. `git push origin v0.1.6`) triggers the `release.yml` workflow, which tests all runtimes and automatically publishes to PyPI, npm, and Crates.io.
- **Manual:** Go to **GitHub Actions → Release & Publish → Run workflow**, specify the version, and click run.

*(Requires `PYPI_API_TOKEN` and `CARGO_REGISTRY_TOKEN` in GitHub Repository Secrets; npm uses OpenID Connect (OIDC) Trusted Publishing with cryptographic Sigstore provenance without static tokens).*

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

- ⚡ **Astra-Jev Dynamic Reasoning Effort Governance**: Pioneered from Vechen (@miu21590) with native Jev System One semantic governance. Modulates per-generation reasoning effort in <500µs local / 70ms remote.
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

## 📄 License

Distributed under the **MIT License**. See [`LICENSE`](LICENSE) for more information.
