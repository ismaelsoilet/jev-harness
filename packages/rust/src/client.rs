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
pub const COMMANDCODE_API_URL: &str = "https://api.commandcode.ai/provider/v1/systemone";
pub const OPENCODE_API_URL: &str = "https://opencode.ai/zen/v1/systemone";
pub const OPENROUTER_API_URL: &str = "https://openrouter.ai/api/alpha/decisions";
pub const VERCEL_API_URL: &str = "https://ai-gateway.vercel.sh/v1/evaluate";
pub const DEFAULT_USER_AGENT: &str = concat!(
    "Mozilla/5.0 (compatible; JevHarness/",
    env!("CARGO_PKG_VERSION"),
    "; +https://github.com/ismaelsoilet/jev-harness)"
);

static ASSERTION_REGEX: LazyLock<regex::Regex> = LazyLock::new(|| {
    regex::Regex::new(r"(?i)(?:assertionerror|assertionfailed|assertionfailederror|assert\b|assert_eq!|assertthat|expect\(.*?\)\.to|expected:.*received:|failures?:|fail(?:ed)?\s+test|^fail(?:ed)?\b|falha de asserção|fallo de aserción|opentest4j)").expect("Invalid assertion regex")
});

static FAILURE_REGEX: LazyLock<regex::Regex> = LazyLock::new(|| {
    regex::Regex::new(r"(?i)(?:assertionerror|assertionfailed|assertionfailederror|failures?:\s*[1-9]|failed\b|falhou\b|\d+\s+failed\b|not\s+ok\b|segmentation\s+fault|sigsegv|panic\b|core\s+dumped)").expect("Invalid failure regex")
});

static NEGATION_REGEX: LazyLock<regex::Regex> = LazyLock::new(|| {
    regex::Regex::new(r"(?i)\b(not|do\s+not|don't|não|nao|no|never|sem|evitar|avoid)\s+(\w+\s+){0,3}(abort|abortar|stop|parar|detener|falhar|fail|deadlock|circular|dead\s*end)").expect("Invalid negation regex")
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
            if resolved_provider == "commandcode" {
                "typesafe/jev".to_string()
            } else if resolved_provider == "opencode" {
                "jev-1.13-free".to_string()
            } else if resolved_provider == "openrouter" {
                "typesafe/jev-1.13".to_string()
            } else if resolved_provider == "vercel" {
                "typesafe-ai/jev".to_string()
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

    pub fn with_provider(provider: &str, api_key: Option<String>) -> Self {
        let prov = provider.trim().to_lowercase();
        let base_url = match prov.as_str() {
            "commandcode" => COMMANDCODE_API_URL.to_string(),
            "opencode" => OPENCODE_API_URL.to_string(),
            "openrouter" => OPENROUTER_API_URL.to_string(),
            "vercel" => VERCEL_API_URL.to_string(),
            _ => TYPESAFE_API_URL.to_string(),
        };
        let model = match prov.as_str() {
            "commandcode" => "typesafe/jev".to_string(),
            "opencode" => "jev-1.13-free".to_string(),
            "openrouter" => "typesafe/jev-1.13".to_string(),
            "vercel" => "typesafe-ai/jev".to_string(),
            _ => DEFAULT_MODEL.to_string(),
        };
        Self {
            api_key,
            base_url,
            model,
            provider: prov,
            timeout_ms: DEFAULT_TIMEOUT_MS,
            force_mock: false,
            http_client: reqwest::Client::new(),
        }
    }

    pub fn redact_secrets(text: &str, secret: Option<&str>) -> String {
        if text.is_empty() {
            return String::new();
        }
        let mut cleaned = text.to_string();
        if let Some(sec) = secret {
            if sec.len() >= 4 {
                cleaned = cleaned.replace(sec, "[REDACTED]");
            }
        }
        for prefix in ["Bearer ", "bearer ", "sk-", "vck_"] {
            while let Some(idx) = cleaned.find(prefix) {
                let end = cleaned[idx + prefix.len()..]
                    .find(|c: char| !c.is_ascii_alphanumeric() && c != '.' && c != '_' && c != '-')
                    .map(|offset| idx + prefix.len() + offset)
                    .unwrap_or(cleaned.len());
                if end > idx + prefix.len() {
                    cleaned.replace_range(idx..end, "[REDACTED]");
                } else {
                    break;
                }
            }
        }
        cleaned.chars().take(400).collect()
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
            let pt = p.trim();
            if pt == "commandcode" {
                let key = env::var("CMD_API_KEY")
                    .or_else(|_| env::var("COMMAND_CODE_API_KEY"))
                    .ok();
                if let Some(k) = key {
                    if !k.trim().is_empty() {
                        return (
                            Some(k),
                            "commandcode".to_string(),
                            COMMANDCODE_API_URL.to_string(),
                        );
                    }
                }
            } else if pt == "opencode" {
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

        for env_name in ["CMD_API_KEY", "COMMAND_CODE_API_KEY"] {
            if let Ok(key) = env::var(env_name) {
                if !key.trim().is_empty() {
                    return (
                        Some(key),
                        "commandcode".to_string(),
                        COMMANDCODE_API_URL.to_string(),
                    );
                }
            }
        }

        if let Ok(key) = env::var("VERCEL_AI_GATEWAY_API_KEY") {
            if !key.trim().is_empty() {
                return (
                    Some(key),
                    "vercel".to_string(),
                    VERCEL_API_URL.to_string(),
                );
            }
        }

        if let Ok(key) = env::var("VERCEL_API_KEY") {
            if !key.trim().is_empty() {
                return (
                    Some(key),
                    "vercel".to_string(),
                    VERCEL_API_URL.to_string(),
                );
            }
        }

        if let Ok(key) = env::var("AI_GATEWAY_API_KEY") {
            if !key.trim().is_empty() {
                return (
                    Some(key),
                    "vercel".to_string(),
                    VERCEL_API_URL.to_string(),
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
                        let url = match prov {
                            "commandcode" => COMMANDCODE_API_URL,
                            "openrouter" => OPENROUTER_API_URL,
                            "vercel" => VERCEL_API_URL,
                            _ => TYPESAFE_API_URL,
                        };
                        return (
                            Some(k.to_string()),
                            prov.to_string(),
                            url.to_string(),
                        );
                    }
                }
            }
        }

        // 3. Check ~/.config/jev/credentials.env and ~/.commandcode/auth.json
        if let Ok(home) = env::var("HOME").or_else(|_| env::var("USERPROFILE")) {
            let p = PathBuf::from(&home).join(".config/jev/credentials.env");
            if let Ok(content) = fs::read_to_string(p) {
                for line in content.lines() {
                    let trimmed = line.trim();
                    if trimmed.starts_with("JEV_PROVIDER=") && trimmed.contains("opencode") {
                        return (None, "opencode".to_string(), OPENCODE_API_URL.to_string());
                    }
                    if trimmed.starts_with("CMD_API_KEY=") || trimmed.starts_with("COMMAND_CODE_API_KEY=") {
                        let k = trimmed
                            .split('=')
                            .nth(1)
                            .unwrap_or("")
                            .trim_matches('"')
                            .trim();
                        if !k.is_empty() {
                            return (
                                Some(k.to_string()),
                                "commandcode".to_string(),
                                COMMANDCODE_API_URL.to_string(),
                            );
                        }
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
                    if trimmed.starts_with("VERCEL_AI_GATEWAY_API_KEY=") || trimmed.starts_with("VERCEL_API_KEY=") || trimmed.starts_with("AI_GATEWAY_API_KEY=") {
                        let k = trimmed
                            .split('=')
                            .nth(1)
                            .unwrap_or("")
                            .trim_matches('"')
                            .trim();
                        if !k.is_empty() {
                            return (
                                Some(k.to_string()),
                                "vercel".to_string(),
                                VERCEL_API_URL.to_string(),
                            );
                        }
                    }
                }
            }

            let cmd_auth = PathBuf::from(&home).join(".commandcode/auth.json");
            if let Ok(content) = fs::read_to_string(cmd_auth) {
                if let Ok(val) = serde_json::from_str::<serde_json::Value>(&content) {
                    if let Some(k) = val.get("apiKey").and_then(|v| v.as_str()) {
                        let kt = k.trim();
                        if !kt.is_empty() {
                            return (
                                Some(kt.to_string()),
                                "commandcode".to_string(),
                                COMMANDCODE_API_URL.to_string(),
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

        let mut payload = serde_json::json!({
            "model": self.model,
            "state": state,
            "questions": questions
        });
        if self.provider == "openrouter" {
            payload["provider"] = serde_json::json!({ "only": ["typesafe"], "allow_fallbacks": false });
        } else if self.provider == "vercel" {
            payload["providerOptions"] = serde_json::json!({ "gateway": { "only": ["typesafe-ai"] } });
        }

        let mut req = self
            .http_client
            .post(&self.base_url)
            .header("Content-Type", "application/json");

        if let Some(ref key) = self.api_key {
            req = req.header("Authorization", format!("Bearer {}", key));
        }
        if self.provider == "openrouter" {
            req = req
                .header("HTTP-Referer", "https://github.com/ismaelsoilet/jev-harness")
                .header("X-Title", "Jev Harness");
        }

        let resp_result = req.json(&payload).send().await;

        match resp_result {
            Ok(resp) => {
                if !resp.status().is_success() {
                    let status = resp.status().as_u16();
                    let raw_text = resp.text().await.unwrap_or_default();
                    let text = Self::redact_secrets(&raw_text, self.api_key.as_deref());
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
        let has_explicit_failure = FAILURE_REGEX.is_match(&state_lower);

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
            "arquitetura",
            "distribuído",
            "distribuída",
            "distribuido",
            "refatorar",
            "refatoração",
            "concorrência",
            "concorrencia",
            "consenso",
            "múltiplos arquivos",
            "condição de corrida",
            "arquitectura",
            "concurrencia",
            "condición de carrera",
            "múltiples archivos",
        ];
        let has_heavy_keywords = heavy_kw.iter().any(|k| state_lower.contains(k));

        let env_missing_triggers = [
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
            "classnotfoundexception",
            "noclassdeffounderror",
            "package does not exist",
            "no such file or directory",
            "command not found",
            "module not found",
            "package not found",
            "crate not found",
            "cs0246",
            "type or namespace name",
            "cannot load such file",
            "loaderror",
            "módulo não encontrado",
            "modulo nao encontrado",
            "nenhum módulo chamado",
            "pacote não encontrado",
            "módulo no encontrado",
            "modulo no encontrado",
            "no se encontró el módulo",
            "paquete no encontrado",
        ];
        let flaky_triggers = [
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
            "conexao recusada",
            "tiempo de espera agotado",
            "conexión rechazada",
            "conexion rechazada",
        ];
        let syntax_triggers = [
            "syntaxerror",
            "indentationerror",
            "expected ';'",
            "ts1005",
            "missing bracket",
            "erro de sintaxe",
            "sintaxe inválida",
            "indentação inesperada",
            "error de sintaxis",
            "sintaxis inválida",
        ];
        let deep_logic_triggers = [
            "assertionerror",
            "assertionfailed",
            "assertionfailederror",
            "assert ",
            "panicked at",
            "panic:",
            "panic",
            "deadlock",
            "goroutines are asleep",
            "infinite loop",
            "loop infinito",
            "bucle infinito",
            "bloqueo mutuo",
            "mutex",
            "segmentation fault",
            "sigsegv",
            "addresssanitizer",
            "core dumped",
            "nullpointerexception",
            "nullreferenceexception",
            "arrayindexoutofboundsexception",
            "nil pointer dereference",
            "index out of bounds",
            "falha de asserção",
            "asserção",
            "erro de lógica",
            "fallo de aserción",
            "error de lógica",
            "expect(",
        ];
        let single_word_mech = [
            "git", "diff", "typo", "flake8", "eslint", "prettier", "linter",
            "echo", "pwd", "format", "black", "lint", "cat", "ls",
        ];
        let multi_word_mech = [
            "git status", "git diff", "git log", "view file", "read file", "cat file",
            "check status", "run linter", "fix typo", "ler arquivo", "verificar arquivo",
            "formatar código", "leer archivo", "corregir errata", "listar arquivos",
            "listar diretório",
        ];
        let has_mech_trigger = single_word_mech.iter().any(|w| state_tokens.contains(*w))
            || multi_word_mech.iter().any(|p| state_lower.contains(p));

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
                            "bucle infinito",
                            "deadlock",
                            "deadlock!",
                            "bloqueo mutuo",
                            "goroutines are asleep",
                            "mutex",
                            "thread hung",
                        ]
                        .iter()
                        .any(|k| state_lower.contains(k));

                        // Domain heuristics
                        if opt == "deep_logic" {
                            if deep_logic_triggers.iter().any(|t| state_lower.contains(t)) {
                                score += 8;
                            }
                            if is_explicit_assertion || has_deadlock_or_loop {
                                score += 18;
                            }
                        } else if opt == "env_missing" {
                            if env_missing_triggers.iter().any(|t| state_lower.contains(t)) {
                                score += if is_explicit_assertion { 0 } else { 7 };
                            }
                        } else if opt == "flaky_transient" && !has_deadlock_or_loop {
                            if flaky_triggers.iter().any(|t| state_lower.contains(t)) {
                                score += if is_explicit_assertion { 0 } else { 7 };
                            }
                        } else if opt == "syntax_trivial" {
                            if syntax_triggers.iter().any(|t| state_lower.contains(t)) {
                                score += 6;
                            }
                        } else if opt == "deterministic" {
                            if has_mech_trigger
                                || ["bash", "regex", "script"]
                                    .iter()
                                    .any(|k| state_tokens.contains(*k))
                            {
                                score += if has_heavy_keywords { 2 } else { 7 };
                            }
                        } else if opt == "heavy_system2" {
                            if has_heavy_keywords {
                                score += 15;
                            }
                        } else if opt == "abort_and_ask" {
                            if !is_negated_abort {
                                let triggers = [
                                    "repeat",
                                    "circular",
                                    "deadlock",
                                    "same",
                                    "tentar novamente",
                                    "intentar de nuevo",
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

                    let is_effort_q = qid == "effort"
                        || ["none", "minimal", "low", "medium", "high", "xhigh", "max", "ultra"]
                            .iter()
                            .any(|eff| cq.criteria.contains_key(*eff));

                    if is_effort_q {
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
                                "deadlocks",
                                "concorrência",
                                "arquitetura",
                                "condição de corrida",
                                "arquitectura",
                                "concurrencia",
                            ]
                            .iter()
                            .any(|k| state_lower.contains(k))
                        {
                            best_choice = if cq.criteria.contains_key("ultra")
                                && state_lower.contains("beyond max")
                            {
                                "ultra".to_string()
                            } else if cq.criteria.contains_key("max")
                                && (state_lower.contains("first principles")
                                    || state_lower.contains("proof"))
                            {
                                "max".to_string()
                            } else if cq.criteria.contains_key("xhigh")
                                && (state_lower.contains("first principles")
                                    || state_lower.contains("subsystems"))
                            {
                                "xhigh".to_string()
                            } else if cq.criteria.contains_key("high") {
                                "high".to_string()
                            } else if cq.criteria.contains_key("xhigh") {
                                "xhigh".to_string()
                            } else if cq.criteria.contains_key("max") {
                                "max".to_string()
                            } else if cq.criteria.contains_key("medium") {
                                "medium".to_string()
                            } else {
                                cq.criteria.keys().last().cloned().unwrap_or_default()
                            };
                        } else if has_mech_trigger && !has_heavy_keywords {
                            best_choice = if cq.criteria.contains_key("none")
                                && ["git status", "pwd", "echo", "version"]
                                    .iter()
                                    .any(|m| state_lower.contains(m))
                            {
                                "none".to_string()
                            } else if cq.criteria.contains_key("minimal")
                                && ["git status", "pwd", "echo", "version"]
                                    .iter()
                                    .any(|m| state_lower.contains(m))
                            {
                                "minimal".to_string()
                            } else if cq.criteria.contains_key("low") {
                                "low".to_string()
                            } else if cq.criteria.contains_key("minimal") {
                                "minimal".to_string()
                            } else if cq.criteria.contains_key("none") {
                                "none".to_string()
                            } else if cq.criteria.contains_key("medium") {
                                "medium".to_string()
                            } else {
                                cq.criteria.keys().next().cloned().unwrap_or_default()
                            };
                        } else {
                            best_choice = if cq.criteria.contains_key("medium") {
                                "medium".to_string()
                            } else if cq.criteria.contains_key("high") {
                                "high".to_string()
                            } else if cq.criteria.contains_key("low") {
                                "low".to_string()
                            } else {
                                cq.criteria.keys().next().cloned().unwrap_or_default()
                            };
                        }
                    } else if qid == "lease"
                        || (cq.criteria.contains_key("1")
                            && ["2", "5", "10"]
                                .iter()
                                .any(|x| cq.criteria.contains_key(*x)))
                    {
                        // Astra-Ares multi-generation lease question
                        if [
                            "error",
                            "fail",
                            "erro",
                            "falha",
                            "deadlock",
                            "panic",
                            "exception",
                        ]
                        .iter()
                        .any(|k| state_lower.contains(k))
                        {
                            best_choice = "1".to_string();
                        } else if has_mech_trigger && !has_heavy_keywords {
                            best_choice = if cq.criteria.contains_key("5") {
                                "5".to_string()
                            } else if cq.criteria.contains_key("2") {
                                "2".to_string()
                            } else {
                                "1".to_string()
                            };
                        } else {
                            best_choice = if cq.criteria.contains_key("2") {
                                "2".to_string()
                            } else if cq.criteria.contains_key("5") {
                                "5".to_string()
                            } else {
                                "1".to_string()
                            };
                        }
                        if !cq.criteria.contains_key(&best_choice) {
                            best_choice = cq.criteria.keys().next().cloned().unwrap_or_default();
                        }
                    } else if qid == "sureforge_phase"
                        || (cq.criteria.contains_key("execute")
                            && cq.criteria.contains_key("verify"))
                    {
                        let is_waiting_q = state_lower.contains('?')
                            || [
                                "waiting on user",
                                "need permission",
                                "please clarify",
                                "which option",
                                "would you like me to",
                                "do you want me to",
                                "aguardando usuário",
                                "preciso de permissão",
                                "qual opção",
                            ]
                            .iter()
                            .any(|w| state_lower.contains(w));
                        let is_unverified = [
                            "without running tests",
                            "tests not run",
                            "unverified",
                            "haven't run pytest",
                            "todo: run tests",
                            "falta rodar os testes",
                            "sem testar",
                            "need to verify",
                            "to verify",
                            "run pytest",
                            "run cargo test",
                            "run npm test",
                            "need to run",
                        ]
                        .iter()
                        .any(|w| state_lower.contains(w));
                        let is_unfinished = [
                            "todo",
                            "remaining",
                            "next step",
                            "unfinished",
                            "partial",
                            "in progress",
                            "falta implementar",
                            "pendente",
                            "continuarei",
                            "step 1 of",
                        ]
                        .iter()
                        .any(|w| state_lower.contains(w));
                        let is_complete = [
                            "all tests passed",
                            "tests passed (0 failed)",
                            "completed and verified",
                            "100% passing",
                            "completed all",
                            "task complete",
                            "concluído com sucesso",
                            "todos os testes passaram",
                        ]
                        .iter()
                        .any(|w| state_lower.contains(w));

                        if is_waiting_q && cq.criteria.contains_key("ask") {
                            best_choice = "ask".to_string();
                        } else if is_unverified && cq.criteria.contains_key("verify") {
                            best_choice = "verify".to_string();
                        } else if is_unfinished && cq.criteria.contains_key("execute") {
                            best_choice = "execute".to_string();
                        } else if is_complete && cq.criteria.contains_key("complete") {
                            best_choice = "complete".to_string();
                        } else if ["plan", "architecture", "design", "planejamento"]
                            .iter()
                            .any(|w| state_lower.contains(w))
                            && cq.criteria.contains_key("plan")
                        {
                            best_choice = "plan".to_string();
                        } else if ["research", "investigat", "search", "pesquisando"]
                            .iter()
                            .any(|w| state_lower.contains(w))
                            && cq.criteria.contains_key("research")
                        {
                            best_choice = "research".to_string();
                        } else {
                            best_choice = if cq.criteria.contains_key("complete") {
                                "complete".to_string()
                            } else {
                                cq.criteria.keys().next().cloned().unwrap_or_default()
                            };
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
                    let mut matched_idx = if qid == "viability" { 3 } else { 2 };

                    let positive_words = [
                        "satisfy",
                        "satisfaz",
                        "satisface",
                        "atende",
                        "passed",
                        "passou",
                        "pasó",
                        "sucesso",
                        "éxito",
                        "pass",
                        "success",
                        "excellent",
                        "exhaustively",
                        "complete",
                        "concluido",
                        "completado",
                        "proceed",
                    ];
                    let trivial_words = ["trivial", "minor", "pequeno", "menor"];
                    let critical_words = [
                        "critical",
                        "critico",
                        "crítico",
                        "fatal",
                        "disaster",
                        "destrutivo",
                        "complex",
                        "complexo",
                        "complejo",
                    ];
                    let has_deadlock_or_loop = [
                        "infinite loop",
                        "loop infinito",
                        "bucle infinito",
                        "deadlock",
                        "deadlock!",
                        "bloqueo mutuo",
                        "goroutines are asleep",
                        "mutex",
                    ]
                    .iter()
                    .any(|k| state_lower.contains(k));

                    let neg_signals = ["not ok", "failed", "falhou"];

                    if has_explicit_failure && (qid == "satisfaction" || qid == "rigor") {
                        matched_idx = 1;
                    } else if qid == "viability"
                        && ([
                            "deadlock",
                            "circular",
                            "impossible",
                            "impossivel",
                            "imposible",
                            "doomed",
                            "inviavel",
                            "inviable",
                        ]
                        .iter()
                        .any(|w| state_lower.contains(w))
                            || has_deadlock_or_loop)
                    {
                        matched_idx = 1;
                    } else if !has_explicit_failure
                        && positive_words.iter().any(|w| state_lower.contains(w))
                        && !neg_signals.iter().any(|neg| state_lower.contains(neg))
                    {
                        matched_idx = n_levels;
                    } else if qid != "viability"
                        && trivial_words.iter().any(|w| state_lower.contains(w))
                        && !has_heavy_keywords
                    {
                        matched_idx = 1;
                    } else if qid != "viability"
                        && (has_heavy_keywords
                            || critical_words.iter().any(|w| state_lower.contains(w)))
                    {
                        matched_idx = n_levels;
                    }

                    for (idx, level_label) in sq.criteria.iter().enumerate() {
                        let lvl_lower = level_label.to_lowercase();
                        let lvl_tokens: Vec<&str> = lvl_lower
                            .split(|c: char| !c.is_alphanumeric() && c != '_')
                            .filter(|s| !s.is_empty())
                            .collect();
                        if lvl_tokens.iter().any(|t| state_tokens.contains(*t))
                            && !(has_explicit_failure
                                && idx > 0
                                && (qid == "satisfaction" || qid == "rigor"))
                        {
                            matched_idx = (idx + 1) as i32;
                        }
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
                        "fallo",
                        "error",
                        "erro",
                        "impossible",
                        "impossivel",
                        "imposible",
                        "fatal",
                        "circular",
                        "deadlock",
                        "dead end",
                        "broken",
                        "quebrado",
                        "unviable",
                        "inviavel",
                        "inviable",
                        "deletar",
                        "apagar",
                        "destrutivo",
                    ];
                    let positive_signals = [
                        "pass",
                        "passed",
                        "passou",
                        "pasó",
                        "success",
                        "sucesso",
                        "éxito",
                        "resolved",
                        "resolvido",
                        "resuelto",
                        "good",
                        "bom",
                        "valid",
                        "valido",
                        "válido",
                        "satisfy",
                        "satisfaz",
                        "satisface",
                        "atende",
                        "all criteria",
                        "todos os criterios",
                        "concluido",
                        "completado",
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
                        "corregir",
                    ]
                    .iter()
                    .any(|w| proposed_part.contains(w));
                    let is_repetitive_loop = [
                        "same",
                        "repetir",
                        "tentar novamente",
                        "intentar de nuevo",
                        "4a vez",
                        "again",
                        "identical",
                    ]
                    .iter()
                    .any(|w| proposed_part.contains(w));
                    let is_fatal_deadlock = [
                        "impossible",
                        "impossivel",
                        "imposible",
                        "circular",
                        "deadlock",
                        "dead end",
                        "inviavel",
                        "inviable",
                        "hopeless",
                        "fatal",
                    ]
                    .iter()
                    .any(|w| state_lower.contains(w));
                    let has_deadlock_or_loop = [
                        "infinite loop",
                        "loop infinito",
                        "bucle infinito",
                        "deadlock",
                        "deadlock!",
                        "bloqueo mutuo",
                        "goroutines are asleep",
                        "mutex",
                    ]
                    .iter()
                    .any(|k| state_lower.contains(k));

                    if has_explicit_failure
                        && ["pass", "valid", "satisfy", "complete", "verif"]
                            .iter()
                            .any(|w| inst.contains(w))
                    {
                        prob = 0.05;
                    } else if is_negated_abort
                        && ["abort", "dead", "unviable", "destructive"]
                            .iter()
                            .any(|w| inst.contains(w))
                    {
                        prob = 0.08;
                    } else if (is_fatal_deadlock || has_deadlock_or_loop)
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
                        if is_repetitive_loop {
                            prob = 0.88;
                        } else if is_forward_progress {
                            prob = 0.12;
                        } else if negative_signals.iter().any(|s| state_lower.contains(s)) {
                            prob = 0.85;
                        } else {
                            prob = 0.15;
                        }
                    }

                    if !has_explicit_failure
                        && positive_signals.iter().any(|s| state_lower.contains(s))
                        && !["not ok", "failed", "falhou"]
                            .iter()
                            .any(|neg| state_lower.contains(neg))
                    {
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

                    if (is_explicit_assertion || has_deadlock_or_loop)
                        && (inst.contains("deterministically") || inst.contains("skip"))
                    {
                        prob = 0.05;
                    } else if env_missing_triggers
                        .iter()
                        .chain(flaky_triggers.iter())
                        .chain(["pip install", "npm install", "cargo add"].iter())
                        .any(|w| state_lower.contains(w))
                        && !(is_explicit_assertion || has_deadlock_or_loop)
                    {
                        if inst.contains("deterministically") || inst.contains("skip") {
                            prob = 0.95;
                        }
                    }

                    // CommandCode Jev Nudge + SureForge continuation heuristics
                    let is_waiting_on_user = state_lower.contains('?')
                        || [
                            "waiting on user",
                            "need permission",
                            "please clarify",
                            "which option",
                            "would you like me to",
                            "do you want me to",
                            "aguardando usuário",
                            "preciso de permissão",
                            "qual opção",
                        ]
                        .iter()
                        .any(|w| state_lower.contains(w));
                    let has_unfinished_work = [
                        "todo",
                        "remaining",
                        "next step",
                        "unfinished",
                        "partial",
                        "in progress",
                        "without running tests",
                        "tests not run",
                        "unverified",
                        "haven't run pytest",
                        "falta implementar",
                        "pendente",
                        "falta rodar os testes",
                        "sem testar",
                        "need to verify",
                        "step 1 of",
                        "to verify",
                        "run pytest",
                        "run cargo test",
                        "run npm test",
                        "need to run",
                    ]
                    .iter()
                    .any(|w| state_lower.contains(w));
                    let has_no_progress = [
                        "no progress",
                        "stuck",
                        "same output",
                        "unchanged",
                        "repeated without change",
                        "sem progresso",
                        "mesma saída",
                    ]
                    .iter()
                    .any(|w| state_lower.contains(w));

                    if qid == "waiting" || inst.contains("waiting on the user") {
                        prob = if is_waiting_on_user { 0.88 } else { 0.08 };
                    } else if qid == "progress" || inst.contains("last nudge produce real progress")
                    {
                        prob = if has_no_progress { 0.12 } else { 0.86 };
                    } else if qid == "nudge" || inst.contains("gentle nudge") {
                        if is_waiting_on_user || has_no_progress {
                            prob = 0.10;
                        } else if has_unfinished_work {
                            prob = 0.89;
                        } else {
                            prob = 0.14;
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
