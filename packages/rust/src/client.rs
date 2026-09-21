//! HTTP client and offline deterministic simulation engine for TypeSafe Jev System One.

use crate::types::*;
use std::collections::{HashMap, HashSet};
use std::env;
use std::fs;
use std::path::PathBuf;
use std::time::Duration;

pub const DEFAULT_MODEL: &str = "jev-latest";
pub const DEFAULT_TIMEOUT_MS: u64 = 10000;

#[derive(Debug, Clone)]
pub struct JevClient {
    pub api_key: Option<String>,
    pub base_url: String,
    pub model: String,
    pub provider: String,
    pub timeout_ms: u64,
    pub force_mock: bool,
    http_client: reqwest::Client,
}

impl Default for JevClient {
    fn default() -> Self {
        Self::new(None, None, None, None, false)
    }
}

impl JevClient {
    pub fn new(
        api_key: Option<String>,
        base_url: Option<String>,
        model: Option<String>,
        timeout_ms: Option<u64>,
        force_mock: bool,
    ) -> Self {
        let (resolved_key, resolved_provider, resolved_url) = Self::resolve_credentials(api_key);
        let final_url = base_url.unwrap_or(resolved_url);
        let final_model = model.unwrap_or_else(|| DEFAULT_MODEL.to_string());
        let final_timeout = timeout_ms.unwrap_or(DEFAULT_TIMEOUT_MS);

        let http_client = reqwest::Client::builder()
            .timeout(Duration::from_millis(final_timeout))
            .build()
            .unwrap_or_else(|_| reqwest::Client::new());

        Self {
            api_key: resolved_key,
            base_url: final_url,
            model: final_model,
            provider: resolved_provider,
            timeout_ms: final_timeout,
            force_mock,
            http_client,
        }
    }

    pub fn with_mock() -> Self {
        Self::new(None, None, None, None, true)
    }

    fn resolve_credentials(
        explicit_key: Option<String>,
    ) -> (Option<String>, String, String) {
        if let Some(key) = explicit_key {
            if !key.trim().is_empty() {
                return (
                    Some(key),
                    "typesafe".to_string(),
                    "https://api.typesafe.ai/v1/system-one".to_string(),
                );
            }
        }

        // 1. Check environment variables
        if let Ok(key) = env::var("TYPESAFE_API_KEY") {
            if !key.trim().is_empty() {
                return (
                    Some(key),
                    "typesafe".to_string(),
                    "https://api.typesafe.ai/v1/system-one".to_string(),
                );
            }
        }

        if let Ok(key) = env::var("OPENCODE_API_KEY") {
            if !key.trim().is_empty() {
                return (
                    Some(key),
                    "opencode".to_string(),
                    "https://api.opencode.ai/v1/system-one".to_string(),
                );
            }
        }

        if let Ok(key) = env::var("OPENROUTER_API_KEY") {
            if !key.trim().is_empty() {
                return (
                    Some(key),
                    "openrouter".to_string(),
                    "https://openrouter.ai/api/v1/chat/completions".to_string(),
                );
            }
        }

        // 2. Check local repository .jev.json
        if let Ok(content) = fs::read_to_string(".jev.json") {
            if let Ok(val) = serde_json::from_str::<serde_json::Value>(&content) {
                if let Some(k) = val.get("api_key").and_then(|v| v.as_str()) {
                    if !k.trim().is_empty() {
                        return (
                            Some(k.to_string()),
                            "typesafe".to_string(),
                            "https://api.typesafe.ai/v1/system-one".to_string(),
                        );
                    }
                }
            }
        }

        // 3. Check ~/.config/jev/credentials.env
        if let Ok(home) = env::var("HOME") {
            let p = PathBuf::from(home).join(".config/jev/credentials.env");
            if let Ok(content) = fs::read_to_string(p) {
                for line in content.lines() {
                    let trimmed = line.trim();
                    if trimmed.starts_with("TYPESAFE_API_KEY=") {
                        let k = trimmed.trim_start_matches("TYPESAFE_API_KEY=").trim_matches('"');
                        if !k.is_empty() {
                            return (
                                Some(k.to_string()),
                                "typesafe".to_string(),
                                "https://api.typesafe.ai/v1/system-one".to_string(),
                            );
                        }
                    }
                }
            }
        }

        (
            None,
            "mock".to_string(),
            "https://api.typesafe.ai/v1/system-one".to_string(),
        )
    }

    pub async fn system_one(
        &self,
        state: &str,
        questions: HashMap<String, Question>,
    ) -> Result<JevResponse, JevError> {
        if self.force_mock || self.api_key.is_none() {
            return Ok(self.simulate_system_one(state, &questions, &self.model));
        }

        let key = self.api_key.as_ref().unwrap();

        let payload = serde_json::json!({
            "model": self.model,
            "state": state,
            "questions": questions
        });

        let resp_result = self
            .http_client
            .post(&self.base_url)
            .header("Authorization", format!("Bearer {}", key))
            .header("Content-Type", "application/json")
            .json(&payload)
            .send()
            .await;

        match resp_result {
            Ok(resp) => {
                if !resp.status().is_success() {
                    let status = resp.status().as_u16();
                    let text = resp.text().await.unwrap_or_default();
                    return Err(JevError::Api {
                        status,
                        message: text,
                    });
                }

                let parsed: serde_json::Value = resp.json().await?;
                self.parse_api_response(&parsed)
            }
            Err(_e) => {
                // If network failure occurs in agentic run, fall back gracefully to simulation
                Ok(self.simulate_system_one(state, &questions, &format!("{}-offline-fallback", self.model)))
            }
        }
    }

    fn parse_api_response(&self, val: &serde_json::Value) -> Result<JevResponse, JevError> {
        let model = val
            .get("model")
            .and_then(|v| v.as_str())
            .unwrap_or(&self.model)
            .to_string();

        let mut answers = HashMap::new();

        if let Some(ans_obj) = val.get("answers").and_then(|v| v.as_object()) {
            for (k, v) in ans_obj {
                if let Ok(a) = serde_json::from_value::<Answer>(v.clone()) {
                    answers.insert(k.clone(), a);
                }
            }
        }

        let usage = val
            .get("usage")
            .and_then(|v| serde_json::from_value::<JevUsage>(v.clone()).ok())
            .unwrap_or_default();

        Ok(JevResponse {
            model,
            answers,
            usage,
            is_mock: false,
        })
    }

    /// Fast regex-based deterministic decision simulation (< 500µs).
    pub fn simulate_system_one(
        &self,
        state: &str,
        questions: &HashMap<String, Question>,
        model_name: &str,
    ) -> JevResponse {
        let state_lower = state.to_lowercase();
        let state_tokens: HashSet<String> = state_lower
            .split(|c: char| !c.is_alphanumeric() && c != '_')
            .filter(|s| !s.is_empty())
            .map(|s| s.to_string())
            .collect();

        let mut answers = HashMap::new();

        for (qid, q) in questions {
            match q {
                Question::Choice(cq) => {
                    let mut best_choice = cq.criteria.keys().next().cloned().unwrap_or_default();
                    let mut best_score: i32 = -1;

                    for (opt, desc) in &cq.criteria {
                        let opt_text = format!("{} {}", opt, desc).to_lowercase();
                        let opt_tokens: Vec<&str> = opt_text
                            .split(|c: char| !c.is_alphanumeric() && c != '_')
                            .filter(|s| !s.is_empty())
                            .collect();

                        let mut score = opt_tokens
                            .iter()
                            .filter(|t| state_tokens.contains(**t))
                            .count() as i32;

                        if state_lower.contains(&opt.to_lowercase()) {
                            score += 3;
                        }

                        // Domain heuristics
                        if opt == "deep_logic" {
                            let triggers = [
                                "assertionerror", "assert ", "panicked at", "panic:", "panic",
                                "deadlock", "goroutines are asleep", "segmentation fault",
                                "nullpointerexception", "nil pointer dereference", "index out of bounds"
                            ];
                            if triggers.iter().any(|t| state_lower.contains(t)) {
                                score += 8;
                            }
                        } else if opt == "env_missing" {
                            let triggers = [
                                "modulenotfounderror", "no module named", "not found", "importerror",
                                "cannot find module", "err_module_not_found", "ts2307", "cannot find crate",
                                "can't find crate", "find crate", "e0463", "cannot find package", "no required module provides package"
                            ];
                            if triggers.iter().any(|t| state_lower.contains(t)) {
                                score += 7;
                            }
                        } else if opt == "flaky_transient" {
                            let triggers = [
                                "connectionreset", "timeout", "timed out", "econnreset", "econnrefused",
                                "etimedout", "socket hang up", "gateway timeout", "503 service unavailable"
                            ];
                            if triggers.iter().any(|t| state_lower.contains(t)) {
                                score += 7;
                            }
                        } else if opt == "syntax_trivial" {
                            let triggers = ["syntaxerror", "indentationerror", "expected ';'", "ts1005", "missing bracket"];
                            if triggers.iter().any(|t| state_lower.contains(t)) {
                                score += 6;
                            }
                        } else if opt == "deterministic" {
                            let triggers = ["typo", "format", "black", "prettier", "eslint", "lint", "bash", "regex", "script", "renomear"];
                            if triggers.iter().any(|t| state_lower.contains(t)) {
                                score += 7;
                            }
                        } else if opt == "heavy_system2" {
                            let triggers = ["refactor", "kernel", "distributed", "architecture", "concurrency", "deadlock", "multi-file"];
                            if triggers.iter().any(|t| state_lower.contains(t)) {
                                score += 7;
                            }
                        } else if opt == "abort_and_ask" {
                            let triggers = ["repeat", "circular", "deadlock", "same", "tentar novamente", "mesma", "abort"];
                            if triggers.iter().any(|t| state_lower.contains(t)) {
                                score += 8;
                            }
                        } else if opt == "proceed" {
                            let triggers = ["unit test", "test", "verify", "verifying", "incremental", "progress", "implement", "add", "adicionar"];
                            if triggers.iter().any(|t| state_lower.contains(t)) {
                                score += 6;
                            }
                        }

                        if score > best_score {
                            best_score = score;
                            best_choice = opt.clone();
                        }
                    }

                    answers.insert(
                        qid.clone(),
                        Answer::Choice(ChoiceAnswer {
                            choice: best_choice,
                            confidence: 0.88,
                            probabilities: None,
                        }),
                    );
                }
                Question::Score(sq) => {
                    let n_levels = sq.criteria.len() as i32;
                    let mut matched_idx = 2;

                    let positive_words = ["satisfy", "satisfaz", "atende", "passed", "passou", "sucesso", "pass", "success", "excellent", "exhaustively", "complete", "concluido"];
                    let trivial_words = ["trivial", "minor", "typo", "pequeno"];
                    let critical_words = ["critical", "critico", "fatal", "disaster", "destrutivo"];

                    if positive_words.iter().any(|w| state_lower.contains(w)) {
                        matched_idx = n_levels;
                    } else if trivial_words.iter().any(|w| state_lower.contains(w)) {
                        matched_idx = 1;
                    } else if critical_words.iter().any(|w| state_lower.contains(w)) {
                        matched_idx = n_levels;
                    }

                    answers.insert(
                        qid.clone(),
                        Answer::Score(ScoreAnswer {
                            score: matched_idx,
                            confidence: 0.85,
                            legend: Some(sq.criteria.clone()),
                        }),
                    );
                }
                Question::Noul(nq) => {
                    let inst = nq.instructions.to_lowercase();
                    let mut prob = 0.15;

                    let negative_signals = ["abort", "abortar", "fail", "falha", "error", "erro", "impossible", "impossivel", "fatal", "circular", "deadlock", "broken", "unviable", "destrutivo"];
                    let positive_signals = ["pass", "passed", "passou", "success", "sucesso", "resolved", "valid", "satisfy", "complete"];

                    if inst.contains("dead end") || inst.contains("abort") || inst.contains("repetit") || inst.contains("circular") {
                        if state_lower.contains("repeat") || state_lower.contains("same") || state_lower.contains("novamente") || state_lower.contains("mesma") || state_lower.contains("tentar novamente") {
                            prob = 0.85;
                        } else if negative_signals.iter().any(|s| state_lower.contains(s)) {
                            prob = 0.72;
                        } else {
                            prob = 0.10;
                        }
                    } else if inst.contains("skip") || inst.contains("ignorar") {
                        if ["modulenotfounderror", "cannot find module", "ts2307", "not found", "timeout", "timed out", "econnreset"].iter().any(|k| state_lower.contains(k)) {
                            prob = 0.95;
                        } else if state_lower.contains("assertionerror") || state_lower.contains("panicked") {
                            prob = 0.05;
                        }
                    } else if positive_signals.iter().any(|s| state_lower.contains(s)) {
                        prob = 0.88;
                    }

                    answers.insert(
                        qid.clone(),
                        Answer::Noul(NoulAnswer { noul: prob }),
                    );
                }
            }
        }

        JevResponse {
            model: model_name.to_string(),
            answers,
            usage: JevUsage {
                input_tokens: std::cmp::max(10, (state.len() / 4) as u32),
                output_tokens: 0,
            },
            is_mock: true,
        }
    }
}
