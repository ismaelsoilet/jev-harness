//! Repository-local configuration loader for `.jev.json`.
//!
//! Walks up from the current working directory (max 4 levels), merges the file over
//! safe defaults, and caches the parsed result by file fingerprint so the semantic
//! gates keep their sub-millisecond latency contract.
//!
//! Honored keys:
//!   - `model`              -> overrides the provider default model
//!   - `skip_llm_threshold` -> triage gate confidence threshold
//!   - `abort_threshold`    -> trajectory abort gate threshold
//!   - `shadow`             -> decide and report, but never change the exit code
//!
//! Credential keys (`api_key`, `provider`) are resolved by `JevClient::resolve_credentials`.

use serde_json::Value;
use std::fs;
use std::path::{Path, PathBuf};
use std::sync::{Mutex, OnceLock};

pub const DEFAULT_SKIP_LLM_THRESHOLD: f64 = 0.65;
pub const DEFAULT_ABORT_THRESHOLD: f64 = 0.70;

/// Repository configuration merged over safe defaults.
#[derive(Debug, Clone, PartialEq)]
pub struct RepoConfig {
    pub model: Option<String>,
    pub skip_llm_threshold: f64,
    pub abort_threshold: f64,
    /// Decide and report, but never change the exit code.
    pub shadow: bool,
}

impl Default for RepoConfig {
    fn default() -> Self {
        Self {
            model: None,
            skip_llm_threshold: DEFAULT_SKIP_LLM_THRESHOLD,
            abort_threshold: DEFAULT_ABORT_THRESHOLD,
            shadow: false,
        }
    }
}

fn find_repo_config_path(start_dir: &Path) -> Option<PathBuf> {
    let mut current = start_dir.to_path_buf();
    for _ in 0..4 {
        let candidate = current.join(".jev.json");
        if candidate.is_file() {
            return Some(candidate);
        }
        if !current.pop() {
            break;
        }
    }
    None
}

fn clamp_probability(value: f64) -> f64 {
    value.clamp(0.0, 1.0)
}

fn fingerprint(path: &Path) -> Option<String> {
    let metadata = fs::metadata(path).ok()?;
    let modified = metadata
        .modified()
        .ok()
        .and_then(|t| t.duration_since(std::time::UNIX_EPOCH).ok())
        .map(|d| d.as_nanos())
        .unwrap_or(0);
    Some(format!(
        "{}:{}:{}",
        path.display(),
        modified,
        metadata.len()
    ))
}

/// Parses a `.jev.json` file, never panicking: corrupted content degrades to defaults.
fn parse_config_file(path: &Path) -> RepoConfig {
    let mut config = RepoConfig::default();
    if let Ok(content) = fs::read_to_string(path) {
        if let Ok(data) = serde_json::from_str::<Value>(&content) {
            if let Some(model) = data.get("model").and_then(|v| v.as_str()) {
                let trimmed = model.trim();
                if !trimmed.is_empty() {
                    config.model = Some(trimmed.to_string());
                }
            }
            if let Some(value) = data.get("skip_llm_threshold").and_then(|v| v.as_f64()) {
                config.skip_llm_threshold = clamp_probability(value);
            }
            if let Some(value) = data.get("abort_threshold").and_then(|v| v.as_f64()) {
                config.abort_threshold = clamp_probability(value);
            }
            if let Some(value) = data.get("shadow").and_then(|v| v.as_bool()) {
                config.shadow = value;
            }
        }
    }
    config
}

/// Loads `.jev.json` starting the search at an explicit directory, without caching.
/// Useful for tests and tooling that must not depend on the process working directory.
pub fn load_repo_config_from(start_dir: &Path) -> RepoConfig {
    match find_repo_config_path(start_dir) {
        Some(path) => parse_config_file(&path),
        None => RepoConfig::default(),
    }
}

/// Loads `.jev.json` from the current working directory, cached by path + mtime + size.
pub fn load_repo_config() -> RepoConfig {
    static CACHE: OnceLock<Mutex<Option<(String, RepoConfig)>>> = OnceLock::new();
    let cache = CACHE.get_or_init(|| Mutex::new(None));

    let Ok(start_dir) = std::env::current_dir() else {
        return RepoConfig::default();
    };
    let Some(path) = find_repo_config_path(&start_dir) else {
        return RepoConfig::default();
    };

    let current_fingerprint = fingerprint(&path);
    if let Some(fp) = current_fingerprint.as_ref() {
        if let Ok(guard) = cache.lock() {
            if let Some((cached_fp, cached_config)) = guard.as_ref() {
                if cached_fp == fp {
                    return cached_config.clone();
                }
            }
        }
    }

    let config = parse_config_file(&path);

    if let Some(fp) = current_fingerprint {
        if let Ok(mut guard) = cache.lock() {
            *guard = Some((fp, config.clone()));
        }
    }
    config
}
