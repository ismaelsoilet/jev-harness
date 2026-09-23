//! # Jev Harness (Rust)
//!
//! Zero-overhead System One decision harness and token optimizer for AI coding agents.
//! Powered by [TypeSafe AI's Jev System One](https://typesafe.ai).
//!
//! Provides ultra-fast micro-decisions (<500µs local, 70-300ms remote) to optimize model routing,
//! triage test and execution failures, and protect against doomed repetitive loops.

pub mod cli;
pub mod client;
pub mod config;
pub mod gates;
pub mod mcp;
pub mod types;

pub use client::{looks_like_test_success, JevClient, COMMANDCODE_API_URL};
pub use config::{
    load_repo_config, load_repo_config_from, RepoConfig, DEFAULT_ABORT_THRESHOLD,
    DEFAULT_SKIP_LLM_THRESHOLD,
};
pub use gates::{
    build_provider_params, modulate_reasoning_effort, route_model_tier, should_abort_trajectory,
    should_nudge_continuation, triage_test_failure, verify_step_completion,
};
pub use mcp::run_mcp_server;
pub use types::*;
