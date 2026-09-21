# jev-harness (TypeScript)

> **Zero-dependency System One decision harness & token optimizer for AI coding agents (Node.js, Bun, Deno, Vite, Tauri, Next.js).**

[![npm version](https://img.shields.io/npm/v/@ismaelsoilet/jev-harness.svg?color=red&logo=npm)](https://www.npmjs.com/package/@ismaelsoilet/jev-harness)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.x-blue.svg)](https://www.typescriptlang.org/)
[![Zero Dependencies](https://img.shields.io/badge/dependencies-0-success.svg)](https://github.com/ismaelsoilet/jev-harness)

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
   - Routes simple tasks, typos, and lint errors to fast deterministic models, and reserves expensive 2026 reasoning models (**GPT-6 Astra**, **Claude Fable 5.1 / Mythos 5.1**) only for complex architectural asks.

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

const decision = triageTestFailure(testOutput);

if (decision.skipLlm) {
  console.log(`[ACTION] ${decision.action}`);
  console.log(`[RESOLVE] Run: npm install ${decision.suggestedFix}`);
} else {
  // Delegate to LLM with distilled traceback
  console.log(`[FORWARD] Deep bug detected. Route to model:`, decision.action);
}
```

### 2. Trajectory Loop Abort Guard

```typescript
import { shouldAbortTrajectory } from '@ismaelsoilet/jev-harness';

const failureHistory = [
  'TypeError: Cannot read properties of undefined (reading "id")',
  'TypeError: Cannot read properties of undefined (reading "id")',
  'TypeError: Cannot read properties of undefined (reading "id")',
];

const check = shouldAbortTrajectory(failureHistory);
if (check.abort) {
  console.error(`[KILL AGENT] ${check.reason}`);
}
```

### 3. Smart Model Router

```typescript
import { routeModelTier } from '@ismaelsoilet/jev-harness';

const task = "Fix typo in variable name in src/utils/format.ts";
const routing = routeModelTier(task);

console.log(`Recommended Tier: ${routing.tier}`); // 'deterministic'
console.log(`Model: ${routing.model}`);           // 'gemini-3.8-flash' or local
```

### 4. CLI Usage

```bash
# Run triage on a test failure
npx @ismaelsoilet/jev-harness triage "Cannot find module 'lodash'"

# Check loop abort
npx @ismaelsoilet/jev-harness abort-check "fail 1" "fail 1" "fail 1"

# Route a task
npx @ismaelsoilet/jev-harness route "Refactor full authentication kernel to WebCrypto"
```

---

## 🛡️ Zero Runtime Dependencies

This package has **zero external runtime dependencies**. It relies strictly on modern standard JavaScript/TypeScript primitives (`fetch`, regex engines) and works natively in Node.js 18+, Bun, Deno, Vite, Tauri, and Next.js.

---

## 📄 License

MIT © [Ismael Hosni Soilet de Lima](https://github.com/ismaelsoilet)
