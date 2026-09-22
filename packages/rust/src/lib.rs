//! # Jev Harness (Rust)
//!
//! Zero-overhead System One decision harness and token optimizer for AI coding agents.
//! Powered by [TypeSafe AI's Jev System One](https://typesafe.ai).
//!
//! Provides ultra-fast micro-decisions (<500µs local, 70-300ms remote) to optimize model routing,
//! triage test and execution failures, and protect against doomed repetitive loops.

pub mod cli;
pub mod client;
pub mod gates;
pub mod mcp;
pub mod types;

pub use client::{JevClient, COMMANDCODE_API_URL};
pub use gates::{
    build_provider_params, modulate_reasoning_effort, route_model_tier, should_abort_trajectory,
    should_nudge_continuation, triage_test_failure, verify_step_completion,
};
pub use mcp::run_mcp_server;
pub use types::*;
