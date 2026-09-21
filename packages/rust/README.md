# jev-harness (Rust)

> **Zero-overhead System One decision harness & token optimizer for AI coding agents and Tauri applications.**

<p align="center">
  <a href="https://github.com/ismaelsoilet/jev-harness/actions/workflows/ci.yml"><img src="https://github.com/ismaelsoilet/jev-harness/actions/workflows/ci.yml/badge.svg" alt="CI Status"></a>
  <a href="https://crates.io/crates/jev-harness"><img src="https://img.shields.io/crates/v/jev-harness.svg" alt="Crates.io"></a>
  <a href="https://opensource.org/licenses/MIT"><img src="https://img.shields.io/badge/License-MIT-yellow.svg" alt="License MIT"></a>
  <a href="https://www.rust-lang.org/"><img src="https://img.shields.io/badge/rust-2021%20edition-orange.svg" alt="Rust"></a>
</p>

`jev-harness` wraps [TypeSafe Jev System One](https://typesafe.ai) micro-decisions with local fast heuristics (< 500µs) and remote sub-second inference (70-300ms). It prevents catastrophic token waste ($10-$50/M frontier reasoning calls) by detecting dependency errors, circular failure loops, and deterministic routing locally.

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

1. **Test & Process Failure Triage (`triage_test_failure`)**:
   - Detects missing modules (`TS2307`, `Cannot find module`, `ModuleNotFoundError`, `E0463`), flaky network timeouts (`ETIMEDOUT`, `ECONNRESET`), and syntax errors in **< 500µs** locally.
   - Tells your agent or process runner to install dependencies or retry without invoking expensive frontier LLMs (`skip_llm: true`).

2. **Loop & Doom Prevention (`should_abort_trajectory`)**:
   - Evaluates consecutive identical test failures and repetition loops to kill runaway agentic runs before burning budget.

3. **Dynamic Model Routing (`route_model_tier`)**:
   - Routes simple tasks, typos, and lint errors to fast deterministic models, and reserves expensive 2026 reasoning models (**GPT-6 Astra**, **Claude Fable 5.1 / Mythos 5.1**) only for complex architectural asks.

4. **Step Completion Verification (`verify_step_completion`)**:
   - Confirms criteria satisfaction before concluding multi-step workflows.

---

## 📦 Installation

Add to your `Cargo.toml`:

```toml
[dependencies]
jev-harness = "0.1.3"
tokio = { version = "1", features = ["full"] }
```

Or install the standalone CLI:

```bash
cargo install jev-harness
```

---

## 🚀 Usage

### 1. Test Failure Triage

```rust
use jev_harness::gates::triage_test_failure;

#[tokio::main]
async fn main() {
    let error_log = "error[E0463]: can't find crate for 'serde'";
    let decision = triage_test_failure(error_log, None).await.unwrap();

    if decision.skip_llm {
        println!("[ACTION] {}", decision.action_recommendation);
    } else {
        println!("[FORWARD] Deep bug detected. Route to frontier LLM.");
    }
}
```

### 2. Trajectory Loop Abort Guard

```rust
use jev_harness::gates::should_abort_trajectory;

#[tokio::main]
async fn main() {
    let history = "Attempt 1 failed with connection timeout\nAttempt 2 failed with connection timeout";
    let step = "Repeat identical prompt with no code changes";

    let check = should_abort_trajectory(step, history, None).await.unwrap();
    if check.should_abort {
        eprintln!("[KILL AGENT] {}", check.reasoning_summary);
    }
}
```

### 3. Model Tier Routing

```rust
use jev_harness::gates::route_model_tier;

#[tokio::main]
async fn main() {
    let routing = route_model_tier("Refactor auth system architecture", None).await.unwrap();
    println!("Selected Tier: {}", routing.selected_tier);
    println!("Recommended Model: {}", routing.recommended_model);
}
```

### 4. CLI Usage

```bash
# Run triage on a traceback
jev triage "Cannot find module 'lodash'"

# Trajectory abort check
jev abort-check --plan "Try identical prompt again"

# Route model tier
jev route --task "Fix typo in variable name"

# Check system status
jev status
```

---

## 📄 License

MIT © [Ismael Hosni Soilet de Lima](https://github.com/ismaelsoilet)
