# jev-harness (Rust)

> **Zero-overhead System One decision harness & token optimizer for AI coding agents and Tauri applications.**

[![Crates.io](https://img.shields.io/crates/v/jev-harness.svg)](https://crates.io/crates/jev-harness)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Rust](https://img.shields.io/badge/rust-2021%20edition-orange.svg)](https://www.rust-lang.org/)

`jev-harness` wraps [TypeSafe Jev System One](https://typesafe.ai) micro-decisions with local fast heuristics (< 500µs) and remote sub-second inference (70-300ms). It prevents catastrophic token waste ($10-$50/M frontier reasoning calls) by detecting dependency errors, circular failure loops, and deterministic routing locally.

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
jev-harness = "0.1"
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
