# 🚀 PR & Visibility Strategy: Elevating `jev-harness` Across the Ecosystem

Este documento contém os **Pull Requests estratégicos**, **textos persuasivos**, **diffs exatos** e **materiais de divulgação** prontos para posicionar o `jev-harness` como a ferramenta de referência para **Token Optimization, Test Failure Triage e Governança System 1.5** no ecossistema global de Agentes de IA e MCP.

---

## 🎯 Mapa de Alvos de Notoriedade

| Alvo | Relevância | O que vamos submeter | Impacto Esperado |
| :--- | :--- | :--- | :--- |
| **1. `punkpeye/awesome-mcp-servers`** | O maior diretório MCP do mundo (>10k★). Referência obrigatória para Claude Desktop, Cursor, Antigravity e OpenCode. | PR na seção `Coding Agents` com tag de fast-track `🤖🤖🤖`. | Descoberta direta por dezenas de milhares de desenvolvedores de agentes. |
| **2. `thruwire/foreman` (535★)** | O projeto líder em supervisão semântica com Jev. | PR/Issue propondo seção de Ecossistema Complementar System 1.5 e guia de interoperação. | Posicionamento conjunto como pilares do movimento **System 1.5**. |
| **3. `e2b-dev/awesome-ai-agents`** | Diretório referência de infraestrutura para ambientes e ferramentas de agentes autônomos. | PR na categoria `Developer Tools & Frameworks`. | Validação técnica perante mantenedores de sandboxes de código. |
| **4. Comunidades Técnicas (Show HN, Reddit r/mcp, r/LocalLLaMA, Discord)** | Comunidades ativas onde desenvolvedores de agentes sofrem diariamente com custo e doom loops. | Post/Showcase técnico focado em benchmarks e economia real de tokens. | Adoção imediata e feedback de usuários reais. |

---

## 📦 PR 1: `punkpeye/awesome-mcp-servers`

* **Repositório:** [`https://github.com/punkpeye/awesome-mcp-servers`](https://github.com/punkpeye/awesome-mcp-servers)
* **Seção:** `### 🤖 <a name="coding-agents"></a>Coding Agents`
* **Posição Alfabética:** Entre `danieldoderlein/llm-bus` e `lawrencehui/Citio` (`i` de `ismaelsoilet`).
* **Título do PR:** `Add Jev Harness: Token optimizer & System 1.5 triage gate for coding agents 🤖🤖🤖` *(a flag `🤖🤖🤖` ativa o fast-track de merge automático para agentes)*

### Texto do Pull Request (Inglês)

```markdown
### Summary

This PR adds **Jev Harness** to the **Coding Agents** category.

**Repository:** https://github.com/ismaelsoilet/jev-harness

### What is Jev Harness?

`jev-harness` is a zero-dependency token optimizer, test-failure triage gate, and System 1.5 semantic guardrail for AI coding agents (OpenCode, Claude Code, Cursor, Antigravity IDE, Windsurf, Zed).

When autonomous coding agents hit test failures or compiler errors, the default behavior is dumping 500+ lines of raw traceback into expensive frontier models (GPT-6 Astra, Claude Fable), burning ~50,000 tokens just to hallucinate an answer or realize a package is missing (`pip/npm/cargo install`).

`jev-harness` acts as the deterministic-first **System 1.5 executive decision layer**:
- ⚡ **Local deterministic triage (< 500µs):** Catches missing dependencies (`TS2307`, `ModuleNotFoundError`, `E0463`) and transient network/port hiccups offline with zero LLM tokens.
- 🎯 **TypeSafe Jev System One micro-decisions (70-300ms, $0.042/1M tokens):** Non-autoregressive classification of bug severity, completion verification, and model routing.
- 🛑 **Doom Loop Circuit Breaker:** Detects circular refactoring attempts and kills runaway agent loops (`exit 1`) before burning the budget.
- 🛡️ **Cross-Runtime Parity:** Fully implemented across **Python, TypeScript, and Rust** with zero external runtime dependencies and full offline fallback.
- 🔌 **Universal MCP Server:** Ships out-of-the-box as `jev-mcp` (Python) and `npx @ismaelsoilet/jev-harness mcp` (TypeScript).

### Entry added to README.md

```markdown
- [ismaelsoilet/jev-harness](https://github.com/ismaelsoilet/jev-harness) 🐍 📇 🦀 🏠 🍎 🪟 🐧 - Zero-dependency token optimizer, test-failure triage gate, and System 1.5 semantic guardrail for AI coding agents. Intercepts compiler errors, missing packages, and transient network glitches in < 500µs locally (or 70-300ms via TypeSafe Jev System One non-autoregressive decisions), eliminating 50k-token LLM doom loops with zero-token shell recoveries. Native tri-runtime (Python, TypeScript, Rust) with full offline fallback. Ships as `jev-mcp` or `npx @ismaelsoilet/jev-harness mcp`. MIT.
```

### Checklist
- [x] Follows existing format and alphabetical order in `Coding Agents`.
- [x] Includes language badges (`🐍 📇 🦀`), local scope (`🏠`), and OS support (`🍎 🪟 🐧`).
- [x] Public repository with OSI-approved license (MIT).
- [x] Includes `🤖🤖🤖` tag for agent merge workflow.
```

### Diff Exato para o `README.md` do `awesome-mcp-servers`

```diff
 - [danieldoderlein/llm-bus](https://github.com/danieldoderlein/llm-bus) [![danieldoderlein/llm-bus MCP server](https://glama.ai/mcp/servers/danieldoderlein/llm-bus/badges/score.svg)](https://glama.ai/mcp/servers/danieldoderlein/llm-bus) 📇 ☁️ 🏠 - Multi-agent coordination bus over MCP: atomic gap-free claims, advisory file leases, a shared event ledger, presence, prose handoffs, and a task graph, so multiple coding agents (Claude Code, Cursor, Codex) stop colliding and re-deriving each other's work. Remote Streamable HTTP; self-hostable (AGPL-3.0) or hosted at llm-bus.com.
+- [ismaelsoilet/jev-harness](https://github.com/ismaelsoilet/jev-harness) 🐍 📇 🦀 🏠 🍎 🪟 🐧 - Zero-dependency token optimizer, test-failure triage gate, and System 1.5 semantic guardrail for AI coding agents. Intercepts compiler errors, missing packages, and transient network glitches in < 500µs locally (or 70-300ms via TypeSafe Jev System One non-autoregressive decisions), eliminating 50k-token LLM doom loops with zero-token shell recoveries. Native tri-runtime (Python, TypeScript, Rust) with full offline fallback. Ships as `jev-mcp` or `npx @ismaelsoilet/jev-harness mcp`. MIT.
 - [lawrencehui/Citio](https://github.com/lawrencehui/Citio) [![lawrencehui/Citio MCP server](https://glama.ai/mcp/servers/lawrencehui/Citio/badges/score.svg)](https://glama.ai/mcp/servers/lawrencehui/Citio) 📇 ☁️ - Self-hosted AI teammate in Slack: @mention it and Claude Code or Codex investigates CloudWatch logs, runs tests, and opens pull requests. The bundled MCP server holds all credentials (GitHub, AWS, Slack) so the agent never sees keys. One-command deploy to your own AWS. MIT.
```

---

## 🤝 PR 2: `thruwire/foreman` (535★)

* **Repositório:** [`https://github.com/thruwire/foreman`](https://github.com/thruwire/foreman)
* **Objetivo:** Adicionar seção ou guia sobre a composição de papéis no ecossistema System 1.5. Enquanto o Foreman é o supervisor de runtime de workers de código, o `jev-harness` é a camada de qualidade/testes chamável offline.
* **Título do PR / Issue:** `docs: add System 1.5 ecosystem interop reference (Foreman + Jev Harness)`

### Texto da Proposta (Inglês)

```markdown
### Motivation & Context

In recent weeks, the application of TypeSafe AI's Jev System One paradigm has evolved into clear, specialized roles across the emerging **System 1.5 architecture** (as conceptualized in Josh Rosen's framework).

While **Foreman** is the definitive supervisor for coding workers (`Codex`/`OpenCode`), other non-competing, complementary tools have matured to solve adjacent bottlenecks in the agentic workflow:

| Role in the Agent Loop | Primary Tool | Specialty |
| :--- | :--- | :--- |
| **Worker Runtime Supervision** | **Foreman** (this repository) | End-to-end execution, worker steering (`steer`/`stop`/`retry`/`finish`), turn supervision. |
| **Code Quality & Test Gate** | [**jev-harness**](https://github.com/ismaelsoilet/jev-harness) | Test failure triage, deterministic shell recovery (`pip`/`npm`/`cargo`), doom-loop abort circuit breaker, zero-dependency offline fallback. |
| **Tool-Call Guardrail** | [**jev-guard**](https://github.com/leepokai/jev-guard) | Policy-based tool interceptor (`deny`/`ask`/`allow`). |
| **Capability Routing** | [**JevRouter**](https://github.com/BillionsBobby/JevRouter) | Routing model and capability tiers. |

### How Foreman and Jev Harness Compose Naturally

1. **Foreman Directs, Jev Harness Triages:**
   When a worker executes tests, `jev-harness test-gate` can classify raw failure output locally (< 500µs) or via Jev (70-300ms). If `skip_llm = true` (e.g. missing dependency or transient port bind), the factory can execute an automated recovery step without burning supervisor or worker LLM iterations.
2. **Double-Veto Safety:**
   Foreman's worker-health assessment (`worker_stuck`, `work_off_track`) can be informed by `jev-harness abort-check` receipts without relinquishing Foreman's authority over the execution loop.
3. **Zero-Dependency Tri-Runtime Parity:**
   `jev-harness` provides native typed libraries across Python, TypeScript, and Rust, making it straightforward to invoke within Python-based Foreman or TypeScript-based pipelines.

### Proposed Documentation Addition

Adding a brief "Ecosystem & Complementary Tools" subsection in Foreman's documentation pointing to these complementary roles reinforces the credibility of the entire System 1.5 cognitive hierarchy.
```

---

## 🌐 Material para Lançamento & Redes Técnicas

### 1. Show Hacker News / Reddit (`r/LocalLLaMA`, `r/mcp`, `r/artificial`)

**Title:**
> *Show HN: Jev Harness – Stop burning 50,000 frontier tokens on missing dependencies and doom loops (Python/TS/Rust)*

**Post Body:**
```markdown
Hey HN / Reddit,

If you've built autonomous coding agents or used tools like Claude Code, Cursor, or OpenCode, you've probably watched this happen:

1. A test fails with `error TS2307: Cannot find module '@tanstack/vue-query'` or `ModuleNotFoundError: No module named 'requests'`.
2. The agent dumps 500 lines of traceback into GPT-6 Astra or Claude Fable 5.1 (~$0.50 to $2.50).
3. The frontier model "thinks" for 20 seconds, only to output: `npm install @tanstack/vue-query`.
4. Worse: on flaky network blips or circular bugs, agents enter doom loops, easily burning 200,000+ tokens refactoring random code to "fix" an ephemeral glitch.

To solve this, we built **Jev Harness** (https://github.com/ismaelsoilet/jev-harness) — an open-source, zero-dependency token optimizer, test-failure triage gate, and semantic circuit breaker.

### How it works: System 1 → System 1.5 → System 2
We treat the code-quality loop through Daniel Kahneman's cognitive paradigm:
- **System 1 (Fast Perception):** TypeSafe Jev System One non-autoregressive micro-decisions (70-300ms, $0.042/1M tokens, $0 output tokens).
- **System 1.5 (Deterministic Executive Layer - `jev-harness`):**
  - Extracts focused assertion slices (≤15 lines) and redacts API keys/credentials before external dispatch.
  - Runs local fast heuristics in < 500µs: diagnoses missing modules and auto-generates structured shell recovery commands (`pip/npm/cargo install`).
  - Evaluates uncertainty envelopes (margins + normalized entropy) to detect ambiguous signals.
  - Abort circuit breaker (`exit 1`) stops circular doom loops instantly.
- **System 2 (Generative Deliberation):** Frontier LLMs (GPT-6 Astra, Claude Fable) are ONLY engaged when deep logic bugs are genuinely present.

### Key highlights:
- 🛡️ **Zero external runtime dependencies:** Python stdlib (`urllib.request`), pure TypeScript/JavaScript, and pure Rust.
- ⚡ **True offline mode:** Runs full deterministic triage offline (< 500µs in Rust, < 2ms in TS/Python) with no API key needed.
- 🧪 **626 unit tests & replay calibration gate:** Includes 160 labeled corpus test cases with ECE calibration tracking.
- 🔌 **Universal MCP Server:** Exposes decision gates over stdio (`jev-mcp` ou `npx @ismaelsoilet/jev-harness mcp`).
- 📦 **Quad-channel release:** Published on PyPI, npm, Crates.io, and GitHub Releases (`v0.2.0`).

GitHub: https://github.com/ismaelsoilet/jev-harness
Documentation & System 1.5 Plan: https://github.com/ismaelsoilet/jev-harness/blob/main/SYSTEM_1_5_PLAN.md

We’d love feedback, issues, or ideas on where you're seeing agent token waste!
```

---

### 2. Tweet / Thread no X (Twitter) & LinkedIn

```
Autonomous coding agents love burning 50,000 frontier tokens on:
❌ "Cannot find module 'lodash'"
❌ Network timeouts
❌ Circular doom loops refactoring working code

We built @ismaelsoilet/jev-harness to fix this: a zero-dependency System 1.5 decision layer. 🧵👇

1/ The Problem:
When pytest or vitest fails, agents dump 500 lines of traceback into Claude Fable or GPT-6 Astra.
Cost: ~$1.50 and 20s of latency just to run `npm install`.

2/ The System 1.5 Fix:
`jev-harness` intercepts errors in < 500µs locally:
⚡ Categorizes missing deps & flaky network hiccups
⚡ Synthesizes structured recovery commands
⚡ Trips a circuit breaker on repetitive doom loops
⚡ Cost: 0 frontier tokens.

3/ Under the Hood:
- Powered by TypeSafe AI's Jev System One non-autoregressive micro-decisions (70-300ms, $0.042/1M tokens).
- Bounded uncertainty envelope (normalized entropy).
- Cryptographic SHA-256 receipts & audit trail.

4/ Tri-Runtime Parity:
Built 100% with standard libraries:
🐍 Python: `pip install jev-harness`
📇 TypeScript: `npm install @ismaelsoilet/jev-harness`
🦀 Rust: `cargo add jev-harness`
🔌 MCP Server: `npx @ismaelsoilet/jev-harness mcp`

Check it out (v0.2.0 is live!):
🔗 https://github.com/ismaelsoilet/jev-harness
```
