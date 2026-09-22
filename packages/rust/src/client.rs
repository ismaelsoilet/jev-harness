//! HTTP client and offline deterministic simulation engine for TypeSafe Jev System One.

use crate::types::*;
use std::collections::{HashMap, HashSet};
use std::env;
use std::fs;
use std::path::PathBuf;
use std::sync::LazyLock;
use std::time::Duration;

pub const DEFAULT_MODEL: &str = "jev-latest";
pub const DEFAULT_TIMEOUT_MS: u64 = 10000;
pub const TYPESAFE_API_URL: &str = "https://api.typesafe.ai/v1/systemone";
pub const OPENCODE_API_URL: &str = "https://opencode.ai/zen/v1/systemone";
pub const OPENROUTER_API_URL: &str = "https://openrouter.ai/api/v1/chat/completions";
pub const DEFAULT_USER_AGENT: &str = concat!(
    "Mozilla/5.0 (compatible; JevHarness/",
    env!("CARGO_PKG_VERSION"),
    "; +https://github.com/ismaelsoilet/jev-harness)"
);

static ASSERTION_REGEX: LazyLock<regex::Regex> = LazyLock::new(|| {
    regex::Regex::new(r"(?i)(?:assertionerror|assert\b|expect\(.*?\)\.to|assert_eq!|failures?:|expected:.*received:|^fail\s+|^failed\s+test)").expect("Invalid assertion regex")
});

static NEGATION_REGEX: LazyLock<regex::Regex> = LazyLock::new(|| {
    regex::Regex::new(r"(?i)\b(not|do\s+not|don't|não|nao|never|sem|evitar|avoid)\s+(\w+\s+){0,3}(abort|abortar|stop|parar|falhar|fail|deadlock|circular|dead\s*end)").expect("Invalid negation regex")
});

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
        let final_model = model.unwrap_or_else(|| {
            if resolved_provider == "opencode" {
                "jev-1.13-free".to_string()
            } else {
                DEFAULT_MODEL.to_string()
            }
        });
        let final_timeout = timeout_ms.unwrap_or(DEFAULT_TIMEOUT_MS);

        let http_client = reqwest::Client::builder()
            .timeout(Duration::from_millis(final_timeout))
            .user_agent(DEFAULT_USER_AGENT)
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
        Self {
            api_key: None,
            base_url: TYPESAFE_API_URL.to_string(),
            model: DEFAULT_MODEL.to_string(),
            provider: "mock".to_string(),
            timeout_ms: DEFAULT_TIMEOUT_MS,
            force_mock: true,
            http_client: reqwest::Client::new(),
        }
    }

    fn resolve_credentials(explicit_key: Option<String>) -> (Option<String>, String, String) {
        if let Some(key) = explicit_key {
            if !key.trim().is_empty() {
                return (
                    Some(key),
                    "typesafe".to_string(),
                    TYPESAFE_API_URL.to_string(),
                );
            }
        }

        // 1. Check environment variables
        if let Ok(p) = env::var("JEV_PROVIDER") {
            if p.trim() == "opencode" {
                let key = env::var("OPENCODE_API_KEY").ok();
                return (key, "opencode".to_string(), OPENCODE_API_URL.to_string());
            }
        }

        if let Ok(key) = env::var("TYPESAFE_API_KEY") {
            if !key.trim().is_empty() {
                return (
                    Some(key),
                    "typesafe".to_string(),
                    TYPESAFE_API_URL.to_string(),
                );
            }
        }

        if let Ok(key) = env::var("OPENCODE_API_KEY") {
            if !key.trim().is_empty() {
                return (
                    Some(key),
                    "opencode".to_string(),
                    OPENCODE_API_URL.to_string(),
                );
            }
        }

        if let Ok(key) = env::var("OPENROUTER_API_KEY") {
            if !key.trim().is_empty() {
                return (
                    Some(key),
                    "openrouter".to_string(),
                    OPENROUTER_API_URL.to_string(),
                );
            }
        }

        // 2. Check local repository .jev.json
        if let Ok(content) = fs::read_to_string(".jev.json") {
            if let Ok(val) = serde_json::from_str::<serde_json::Value>(&content) {
                let prov = val
                    .get("provider")
                    .and_then(|v| v.as_str())
                    .unwrap_or("typesafe");
                if prov == "opencode" {
                    let k = val
                        .get("api_key")
                        .and_then(|v| v.as_str())
                        .map(|s| s.to_string());
                    return (k, "opencode".to_string(), OPENCODE_API_URL.to_string());
                }
                if let Some(k) = val.get("api_key").and_then(|v| v.as_str()) {
                    if !k.trim().is_empty() {
                        return (
                            Some(k.to_string()),
                            "typesafe".to_string(),
                            TYPESAFE_API_URL.to_string(),
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
                    if trimmed.starts_with("JEV_PROVIDER=") && trimmed.contains("opencode") {
                        return (None, "opencode".to_string(), OPENCODE_API_URL.to_string());
                    }
                    if trimmed.starts_with("OPENCODE_API_KEY=") {
                        let k = trimmed
                            .trim_start_matches("OPENCODE_API_KEY=")
                            .trim_matches('"');
                        if !k.is_empty() {
                            return (
                                Some(k.to_string()),
                                "opencode".to_string(),
                                OPENCODE_API_URL.to_string(),
                            );
                        }
                    }
                    if trimmed.starts_with("TYPESAFE_API_KEY=") {
                        let k = trimmed
                            .trim_start_matches("TYPESAFE_API_KEY=")
                            .trim_matches('"');
                        if !k.is_empty() {
                            return (
                                Some(k.to_string()),
                                "typesafe".to_string(),
                                TYPESAFE_API_URL.to_string(),
                            );
                        }
                    }
                }
            }
        }

        (None, "mock".to_string(), TYPESAFE_API_URL.to_string())
    }

    pub async fn system_one(
        &self,
        state: &str,
        questions: HashMap<String, Question>,
    ) -> Result<JevResponse, JevError> {
        let is_live = !self.force_mock && (self.provider == "opencode" || self.api_key.is_some());
        if !is_live {
            return Ok(self.simulate_system_one(state, &questions, &self.model));
        }

        let payload = serde_json::json!({
            "model": self.model,
            "state": state,
            "questions": questions
        });

        let mut req = self
            .http_client
            .post(&self.base_url)
            .header("Content-Type", "application/json");

        if let Some(ref key) = self.api_key {
            req = req.header("Authorization", format!("Bearer {}", key));
        }

        let resp_result = req.json(&payload).send().await;

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
            Err(e) => Err(JevError::Http(e)),
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

        let is_explicit_assertion = state_lower.lines().any(|line| {
            let t = line.trim();
            t.starts_with("panicked at")
                || t.starts_with("panic:")
                || ASSERTION_REGEX.is_match(t)
        });

        let heavy_kw = [
            "kernel",
            "distributed",
            "architecture",
            "refactor",
            "concurrency",
            "deadlock",
            "multi-file",
            "consensus",
            "supervision tree",
        ];
        let has_heavy_keywords = heavy_kw.iter().any(|k| state_lower.contains(k));

        let is_negated_abort = NEGATION_REGEX.is_match(state);

        let mut answers = HashMap::new();

        for (qid, q) in questions {
            match q {
                Question::Choice(cq) => {
                    let mut best_choice = if cq.criteria.contains_key("deep_logic") {
                        "deep_logic".to_string()
                    } else if cq.criteria.contains_key("lightweight_system2") {
                        "lightweight_system2".to_string()
                    } else if cq.criteria.contains_key("proceed") {
                        "proceed".to_string()
                    } else {
                        cq.criteria.keys().next().cloned().unwrap_or_default()
                    };
                    let mut best_score: i32 = 0;

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

                        let has_deadlock_or_loop = [
                            "infinite loop",
                            "loop infinito",
                            "deadlock",
                            "deadlock!",
                            "goroutines are asleep",
                            "mutex",
                            "thread hung",
                        ]
                        .iter()
                        .any(|k| state_lower.contains(k));

                        // Domain heuristics
                        if opt == "deep_logic" {
                            let triggers = [
                                "assertionerror",
                                "assert ",
                                "panicked at",
                                "panic:",
                                "panic",
                                "deadlock",
                                "goroutines are asleep",
                                "infinite loop",
                                "loop infinito",
                                "mutex",
                                "segmentation fault",
                                "nullpointerexception",
                                "nil pointer dereference",
                                "index out of bounds",
                                "falha de asserção",
                                "asserção",
                                "erro de lógica",
                                "expect(",
                            ];
                            if triggers.iter().any(|t| state_lower.contains(t)) {
                                score += 8;
                            }
                            if is_explicit_assertion || has_deadlock_or_loop {
                                score += 18;
                            }
                        } else if opt == "env_missing" {
                            let triggers = [
                                "modulenotfounderror",
                                "no module named",
                                "not found",
                                "importerror",
                                "cannot find module",
                                "err_module_not_found",
                                "ts2307",
                                "cannot find crate",
                                "can't find crate",
                                "find crate",
                                "e0463",
                                "cannot find package",
                                "no required module provides package",
                                "módulo não encontrado",
                                "nenhum módulo chamado",
                                "pacote não encontrado",
                            ];
                            if triggers.iter().any(|t| state_lower.contains(t)) {
                                score += if is_explicit_assertion { 0 } else { 7 };
                            }
                        } else if opt == "flaky_transient" && !has_deadlock_or_loop {
                            let triggers = [
                                "connectionreset",
                                "timeout",
                                "timed out",
                                "econnreset",
                                "econnrefused",
                                "etimedout",
                                "socket hang up",
                                "gateway timeout",
                                "503 service unavailable",
                                "tempo limite",
                                "tempo limite esgotado",
                                "conexão recusada",
                            ];
                            if triggers.iter().any(|t| state_lower.contains(t)) {
                                score += if is_explicit_assertion { 0 } else { 7 };
                            }
                        } else if opt == "syntax_trivial" {
                            let triggers = [
                                "syntaxerror",
                                "indentationerror",
                                "expected ';'",
                                "ts1005",
                                "missing bracket",
                                "erro de sintaxe",
                                "sintaxe inválida",
                                "indentação inesperada",
                            ];
                            if triggers.iter().any(|t| state_lower.contains(t)) {
                                score += 6;
                            }
                        } else if opt == "deterministic" {
                            let triggers = [
                                "typo", "format", "black", "prettier", "eslint", "lint", "bash",
                                "regex", "script", "renomear",
                            ];
                            if triggers.iter().any(|t| state_lower.contains(t)) {
                                score += if has_heavy_keywords { 2 } else { 7 };
                            }
                        } else if opt == "heavy_system2" {
                            if has_heavy_keywords {
                                score += 15;
                            } else {
                                let triggers = [
                                    "refactor",
                                    "kernel",
                                    "distributed",
                                    "architecture",
                                    "concurrency",
                                    "deadlock",
                                    "multi-file",
                                ];
                                if triggers.iter().any(|t| state_lower.contains(t)) {
                                    score += 7;
                                }
                            }
                        } else if opt == "abort_and_ask" {
                            if !is_negated_abort {
                                let triggers = [
                                    "repeat",
                                    "circular",
                                    "deadlock",
                                    "same",
                                    "tentar novamente",
                                    "mesma",
                                    "abort",
                                ];
                                if triggers.iter().any(|t| state_lower.contains(t)) {
                                    score += 8;
                                }
                            }
                        } else if opt == "proceed" {
                            let triggers = [
                                "proceed",
                                "unit test",
                                "test",
                                "verify",
                                "verifying",
                                "incremental",
                                "progress",
                                "implement",
                                "add",
                                "adicionar",
                                "migration",
                            ];
                            if is_negated_abort || triggers.iter().any(|t| state_lower.contains(t))
                            {
                                score += 8;
                            }
                        }

                        if score > best_score {
                            best_score = score;
                            best_choice = opt.clone();
                        }
                    }

                    let criteria = &cq.criteria;
                    if criteria.contains_key("low") && criteria.contains_key("high") {
                        if has_heavy_keywords
                            || [
                                "deadlock",
                                "race condition",
                                "distributed",
                                "concurrency",
                                "kernel",
                                "supervision",
                                "architectural",
                                "complex",
                                "algorithmic",
                            ]
                            .iter()
                            .any(|k| state_lower.contains(k))
                        {
                            best_choice = "high".to_string();
                        } else if [
                            "git", "status", "diff", "ls", "cat", "view", "read", "typo", "format",
                            "black", "lint", "flake8", "eslint", "prettier", "import", "version",
                            "trivial",
                        ]
                        .iter()
                        .any(|k| state_lower.contains(k))
                            && !has_heavy_keywords
                        {
                            best_choice = "low".to_string();
                        } else {
                            best_choice = "medium".to_string();
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

                    let positive_words = [
                        "satisfy",
                        "satisfaz",
                        "atende",
                        "passed",
                        "passou",
                        "sucesso",
                        "pass",
                        "success",
                        "excellent",
                        "exhaustively",
                        "complete",
                        "concluido",
                        "proceed",
                    ];
                    let trivial_words = ["trivial", "minor", "typo", "pequeno"];
                    let critical_words = [
                        "critical",
                        "critico",
                        "fatal",
                        "disaster",
                        "destrutivo",
                        "complex",
                    ];

                    if is_negated_abort || positive_words.iter().any(|w| state_lower.contains(w)) {
                        matched_idx = n_levels;
                    } else if trivial_words.iter().any(|w| state_lower.contains(w))
                        && !has_heavy_keywords
                    {
                        matched_idx = 1;
                    } else if has_heavy_keywords
                        || critical_words.iter().any(|w| state_lower.contains(w))
                    {
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

                    let negative_signals = [
                        "abort",
                        "abortar",
                        "fail",
                        "falha",
                        "error",
                        "erro",
                        "impossible",
                        "impossivel",
                        "fatal",
                        "circular",
                        "deadlock",
                        "dead end",
                        "broken",
                        "quebrado",
                        "unviable",
                        "inviavel",
                        "deletar",
                        "apagar",
                        "destrutivo",
                    ];
                    let positive_signals = [
                        "pass",
                        "passed",
                        "passou",
                        "success",
                        "sucesso",
                        "resolved",
                        "resolvido",
                        "good",
                        "bom",
                        "valid",
                        "valido",
                        "satisfy",
                        "satisfaz",
                        "atende",
                        "all criteria",
                        "todos os criterios",
                        "concluido",
                        "complete",
                        "proceed",
                        "linear",
                    ];

                    let proposed_part = if state_lower.contains("proposed next step:") {
                        state_lower
                            .split("proposed next step:")
                            .nth(1)
                            .unwrap_or(&state_lower)
                    } else {
                        &state_lower
                    };
                    let is_forward_progress = [
                        "implement",
                        "fix",
                        "resolve",
                        "correct",
                        "update",
                        "create",
                        "write",
                        "corrigir",
                        "implementar",
                        "executar",
                        "validar",
                    ]
                    .iter()
                    .any(|w| proposed_part.contains(w));
                    let is_repetitive_loop = [
                        "same",
                        "repetir",
                        "tentar novamente",
                        "4a vez",
                        "again",
                        "identical",
                    ]
                    .iter()
                    .any(|w| proposed_part.contains(w));
                    let is_fatal_deadlock = [
                        "impossible",
                        "impossivel",
                        "circular",
                        "deadlock",
                        "dead end",
                        "inviavel",
                        "hopeless",
                        "fatal",
                    ]
                    .iter()
                    .any(|w| state_lower.contains(w));

                    if is_negated_abort
                        && ["abort", "dead", "unviable", "destructive"]
                            .iter()
                            .any(|w| inst.contains(w))
                    {
                        prob = 0.08;
                    } else if is_fatal_deadlock
                        && [
                            "abort",
                            "dead",
                            "fail",
                            "urgent",
                            "invalid",
                            "unviable",
                            "destructive",
                            "dead end",
                        ]
                        .iter()
                        .any(|w| inst.contains(w))
                    {
                        prob = 0.88;
                    } else if [
                        "abort",
                        "dead",
                        "unviable",
                        "destructive",
                        "dead end",
                        "circular",
                    ]
                    .iter()
                    .any(|w| inst.contains(w))
                    {
                        if is_repetitive_loop {
                            prob = 0.88;
                        } else if is_forward_progress {
                            prob = 0.12;
                        } else if negative_signals.iter().any(|s| state_lower.contains(s)) {
                            prob = 0.85;
                        } else {
                            prob = 0.15;
                        }
                    } else if inst.contains("deterministically") || inst.contains("skip") {
                        let has_deadlock_or_loop = [
                            "infinite loop",
                            "loop infinito",
                            "deadlock",
                            "deadlock!",
                            "goroutines are asleep",
                            "mutex",
                        ]
                        .iter()
                        .any(|k| state_lower.contains(k));

                        if is_explicit_assertion || has_deadlock_or_loop {
                            prob = 0.05;
                        } else if [
                            "modulenotfounderror",
                            "no module named",
                            "pip install",
                            "npm install",
                            "ts2307",
                            "cannot find crate",
                        ]
                        .iter()
                        .any(|w| state_lower.contains(w))
                        {
                            prob = 0.95;
                        } else if state_lower.contains("assertionerror")
                            || state_lower.contains("panicked")
                        {
                            prob = 0.05;
                        } else {
                            prob = 0.20;
                        }
                    }

                    if positive_signals.iter().any(|s| state_lower.contains(s)) {
                        if ["pass", "valid", "satisfy", "complete", "verif"]
                            .iter()
                            .any(|w| inst.contains(w))
                        {
                            prob = 0.92;
                        } else if ["abort", "dead", "unviable"]
                            .iter()
                            .any(|w| inst.contains(w))
                        {
                            prob = 0.08;
                        }
                    }

                    answers.insert(qid.clone(), Answer::Noul(NoulAnswer { noul: prob }));
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
