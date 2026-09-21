# ⚡ Jev Harness: The Token Optimizer & Decision Gate for AI Coding Agents

<p align="center">
  <a href="https://github.com/ismaelsoilet/jev-harness"><img src="https://img.shields.io/badge/license-MIT-blue.svg" alt="License MIT"></a>
  <a href="https://pypi.org/project/jev-harness/"><img src="https://img.shields.io/pypi/v/jev-harness.svg?color=blue" alt="PyPI version"></a>
  <a href="https://pypi.org/project/jev-harness/"><img src="https://img.shields.io/badge/python-3.9%20%7C%203.10%20%7C%203.11%20%7C%203.12%20%7C%203.13-brightgreen.svg" alt="Python Versions"></a>
  <a href="https://typesafe.ai"><img src="https://img.shields.io/badge/powered%20by-TypeSafe%20Jev%20System%20One-orange.svg" alt="TypeSafe Jev"></a>
  <a href="https://modelcontextprotocol.io"><img src="https://img.shields.io/badge/MCP-Compatible-purple.svg" alt="MCP Compatible"></a>
  <a href="#"><img src="https://img.shields.io/badge/dependencies-0%20(pure%20stdlib)-success.svg" alt="Zero Dependencies"></a>
</p>

> **Stop burning 50,000 frontier tokens on missing packages, network flakiness, and circular doom loops.**
>
> `jev-harness` is a ultra-fast, zero-dependency token optimizer, test failure triage gate, and semantic guardrail for AI coding agents (OpenCode, Command Code, Claude Code, Cursor, Antigravity IDE, Windsurf, Zed, and Pi). Powered by **TypeSafe AI's Jev System One** non-autoregressive decision model.

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

### 1. Installation

```bash
# Via pip
pip install jev-harness

# Or via pipx (isolated global CLI)
pipx install jev-harness
```

### 2. Configuration (Optional)

Jev Harness automatically resolves credentials in the following priority:
1. Environment variables (`TYPESAFE_API_KEY`, `OPENCODE_API_KEY`, or `OPENROUTER_API_KEY`)
2. Local repository `.jev.json` or `.env`
3. Global configuration `~/.config/jev/credentials.env`
4. **Intelligent Offline Simulation Mode** (active by default if no key is supplied)

```bash
export TYPESAFE_API_KEY="your-typesafe-api-key"
# Check status anytime
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

---

## 🤖 Universal Agent & IDE Integrations

### 1. Cursor IDE (`.cursor/mcp.json`)
Add to `.cursor/mcp.json` (or run `jev-harness init --cursor` in your repo):

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

### 2. Claude Desktop (`claude_desktop_config.json`)
Add to your Claude Desktop configuration:

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

### 3. Antigravity IDE (`mcp_config.json` & `hooks.json`)
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

### 4. OpenCode & Command Code
In `.opencode/config.json` or agent instructions:
```markdown
When running tests or builds:
1. If a command fails, execute `jev-harness test-gate` on the traceback.
2. If `skip_llm=true`, execute the recommended deterministic action.
3. If an error persists across 2 consecutive attempts, run `jev-harness abort-check`.
```

### 5. Windsurf & Zed
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
```

---

## 🟦 TypeScript / JavaScript SDK & CLI

For Node.js, Bun, Deno, Vite, Tauri, and Next.js applications:

```bash
# Install via npm
npm install jev-harness

# Or via bun
bun add jev-harness
```

### Programmatic Usage

```typescript
import {
  triageTestFailure,
  shouldAbortTrajectory,
  routeModelTier,
  verifyStepCompletion,
  JevClient,
} from "jev-harness";

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

// 3. Select minimal sufficient model tier
const route = await routeModelTier("Fix typo in variable name");
console.log("Assigned Model Tier:", route.selectedTier); // deterministic
```

### TypeScript CLI

```bash
# Run test triage via npx
npx jev-harness triage "Cannot find module 'lodash'"

# Trajectory abort check
npx jev-harness abort-check --plan "Try identical prompt again"

# Model router
npx jev-harness route "Architect distributed consensus protocol"
```

---

## 📦 Git & CI/CD Guardrails

### Pre-commit Hook (`.pre-commit-config.yaml`)
```yaml
repos:
  - repo: https://github.com/ismaelsoilet/jev-harness
    rev: v0.1.0
    hooks:
      - id: jev-test-gate
```

### Husky Hook (`.husky/pre-commit`)
```bash
npm test 2>&1 | jev-harness test-gate || exit 1
```

---

## 📊 Economics & Benchmarks (September 2026 Frontier)

| Metric | 2026 Frontier Reasoning (GPT-6 Astra, Claude Fable 5.1) | Fast Agentic Tier (Gemini 3.8 Flash) | TypeSafe Jev System One (`jev-harness`) |
| :--- | :--- | :--- | :--- |
| **Input Pricing** | $10.00 / 1M tokens | $0.75 / 1M tokens | **$0.042 / 1M tokens (~238x cheaper)** |
| **Output Pricing** | $50.00 / 1M tokens | $3.75 / 1M tokens | **$0.00 (Free - Non-autoregressive)** |
| **Latency** | 10,000ms – 30,000ms | 1,500ms – 4,000ms | **70ms – 300ms (~100x faster)** |
| **Output Structure**| Free-form prose & streaming tokens | Structured JSON tool calls | **Strictly typed: Choice, Score, Noul** |
| **Determinism** | Stochastic reasoning | Stochastic generation | **Zero-hallucination calibrated bounds** |

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

## 📄 License

Distributed under the **MIT License**. See [`LICENSE`](LICENSE) for more information.
