# jev-harness (TypeScript)

> **Zero-dependency System One decision harness & token optimizer for AI coding agents (Node.js, Bun, Deno, Vite, Tauri, Next.js).**

<p align="center">
  <a href="https://github.com/ismaelsoilet/jev-harness/actions/workflows/ci.yml"><img src="https://github.com/ismaelsoilet/jev-harness/actions/workflows/ci.yml/badge.svg" alt="CI Status"></a>
  <a href="https://www.npmjs.com/package/@ismaelsoilet/jev-harness"><img src="https://img.shields.io/npm/v/@ismaelsoilet/jev-harness.svg?color=cb3837&logo=npm&logoColor=white" alt="npm version"></a>
  <a href="https://search.sigstore.dev/?logIndex=2907077153"><img src="https://img.shields.io/badge/provenance-Sigstore-blue?logo=npm" alt="npm Provenance"></a>
  <a href="https://www.typescriptlang.org/"><img src="https://img.shields.io/badge/TypeScript-5.x-blue.svg?logo=typescript&logoColor=white" alt="TypeScript"></a>
  <a href="https://github.com/ismaelsoilet/jev-harness/blob/main/LICENSE"><img src="https://img.shields.io/badge/license-MIT-blue.svg" alt="License MIT"></a>
  <a href="https://typesafe.ai"><img src="https://img.shields.io/badge/powered%20by-TypeSafe%20Jev%20System%20One-orange.svg" alt="TypeSafe Jev"></a>
  <a href="https://github.com/ismaelsoilet/jev-harness"><img src="https://img.shields.io/badge/dependencies-0-success.svg" alt="Zero Dependencies"></a>
</p>

`jev-harness` wraps [TypeSafe Jev System One](https://typesafe.ai) micro-decisions with local fast heuristics (1-5ms) and remote sub-second inference (70-300ms). It prevents catastrophic token waste ($10-$50/M frontier reasoning calls) by detecting dependency errors, circular failure loops, and deterministic routing locally.

---

## 🌐 Multi-Provider Support & OpenCode Zen (Free Tier)

Configure your preferred provider via environment variables or `.env`:

```bash
# Option A: OpenCode Zen Free Tier (No API key required!)
export JEV_PROVIDER="opencode"

# Option B: TypeSafe Direct API
export TYPESAFE_API_KEY="your-typesafe-api-key"

# Option C: OpenRouter
export OPENROUTER_API_KEY="your-openrouter-key"
```

---

## ⚡ Key Capabilities

1. **Test Triage (`triageTestFailure`)**:
   - Detects missing modules (`TS2307`, `Cannot find module`, `ModuleNotFoundError`), flaky network timeouts (`ETIMEDOUT`, `ECONNRESET`), and syntax errors in **< 2ms** locally.
   - Tells your agent runner to install dependencies or retry without invoking expensive frontier LLMs (`skipLlm: true`).

2. **Loop & Doom Prevention (`shouldAbortTrajectory`)**:
   - Evaluates consecutive identical test failures and repetition loops to kill runaway agentic runs before burning budget.

3. **Dynamic Model Routing (`routeModelTier`)**:
   - Routes simple tasks, typos, and lint errors to fast deterministic models, and reserves expensive 2026 reasoning models (**GPT-6 Astra**, **Claude Fable 5.1 / Claude Opus 5**) only for complex architectural asks.

4. **Step Completion Verification (`verifyStepCompletion`)**:
   - Confirms criteria satisfaction before concluding multi-step workflows.

---

## 📦 Installation

```bash
# npm
npm install @ismaelsoilet/jev-harness

# pnpm
pnpm add @ismaelsoilet/jev-harness

# yarn
yarn add @ismaelsoilet/jev-harness

# bun
bun add @ismaelsoilet/jev-harness
```

---

## 🚀 Usage

### 1. Test Failure Triage

```typescript
import { triageTestFailure } from '@ismaelsoilet/jev-harness';

const testOutput = `
src/app.ts:2:24 - error TS2307: Cannot find module '@tanstack/vue-query' or its corresponding type declarations.
`;

const decision = await triageTestFailure(testOutput);

if (decision.skipLlm) {
  console.log(`[ACTION] ${decision.actionRecommendation}`);
  console.log(`[CATEGORY] ${decision.category} (Confidence: ${(decision.confidence * 100).toFixed(1)}%)`);
} else {
  // Delegate to LLM with distilled traceback
  console.log(`[FORWARD] Deep bug detected. Route to frontier LLM.`);
}
```

### 2. Trajectory Loop Abort Guard

```typescript
import { shouldAbortTrajectory } from '@ismaelsoilet/jev-harness';

const plan = 'Repeat identical refactoring step without changes';
const failureHistory = 'Attempt 1 failed with TypeError\nAttempt 2 failed with TypeError';

const check = await shouldAbortTrajectory(plan, failureHistory);
if (check.shouldAbort) {
  console.error(`[KILL AGENT] ${check.reasoningSummary} (Action: ${check.action})`);
}
```

### 3. Smart Model Router

```typescript
import { routeModelTier } from '@ismaelsoilet/jev-harness';

const task = "Fix typo in variable name in src/utils/format.ts";
const routing = await routeModelTier(task);

console.log(`Recommended Tier: ${routing.selectedTier}`);   // 'deterministic'
console.log(`Model: ${routing.recommendedModel}`);          // 'Direct Python/Bash Script (0 LLM Tokens)'
```

### 4. Calibrated Criteria Verification

```typescript
import { verifyStepCompletion } from '@ismaelsoilet/jev-harness';

const criteria = "Must export format_date function and pass all unit tests";
const output = "All 10 unit tests passed in 0.02s. format_date exported in index.ts.";

const result = await verifyStepCompletion(criteria, output);
console.log(`Verified: ${result.isVerified ? 'PASS' : 'REWORK NEEDED'}`);
```

### 5. Dynamic Reasoning Effort Modulation (Astra-Jev)

```typescript
import { modulateReasoningEffort } from '@ismaelsoilet/jev-harness';

// Modulate mechanical step to low effort and compile target dialect
const effort = await modulateReasoningEffort("git status and check modified files", {
  provider: "deepseek",
  model: "deepseek-v4.1-flash",
  sessionContextTokens: 45000,
});
console.log("Effort:", effort.effort); // 'low'
console.log("Provider Params:", effort.providerParams); // { extra_body: { thinking: { type: 'enabled' } }, reasoning_effort: 'low' }
console.log("Cache Advisory:", effort.cacheSafeRecommendation);
```

### 6. CLI Usage

```bash
# Run triage on a test failure
npx @ismaelsoilet/jev-harness test-gate "Cannot find module 'lodash'"
# or alias
npx @ismaelsoilet/jev-harness triage "Cannot find module 'lodash'"

# Check trajectory loop abort
npx @ismaelsoilet/jev-harness abort-check --plan "Try identical prompt again" --history "Attempt 1 failed"

# Route a task to appropriate model tier
npx @ismaelsoilet/jev-harness route --task "Refactor full authentication kernel to WebCrypto"

# Dynamically modulate reasoning effort per-step (Astra-Jev)
npx @ismaelsoilet/jev-harness reasoning-effort --context "git status" --target-provider deepseek --json
# or alias
npx @ismaelsoilet/jev-harness astra-jev --context "Architect distributed consensus" --target-provider anthropic

# Evaluate prompt cache risk in long-context sessions
npx @ismaelsoilet/jev-harness reasoning-effort --context "git status" --session-context-tokens 45000

# System status & provider inspection
npx @ismaelsoilet/jev-harness status
```

---

## 🛡️ Zero Runtime Dependencies

This package has **zero external runtime dependencies**. It relies strictly on modern standard JavaScript/TypeScript primitives (`fetch`, regex engines) and works natively in Node.js 18+, Bun, Deno, Vite, Tauri, and Next.js.

---

## 📄 License

MIT © [Ismael Hosni Soilet de Lima](https://github.com/ismaelsoilet)
