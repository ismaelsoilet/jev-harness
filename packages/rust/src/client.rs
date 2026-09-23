//! HTTP client and offline deterministic simulation engine for TypeSafe Jev System One.

use crate::config::load_repo_config;
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

/// E3.5 — masks credential-shaped material before a log is sent to a provider.
/// Mirrors `redact_secrets` in Python/TypeScript: all three runtimes can transmit a failure log,
/// so all three must mask the same shapes.
static SECRET_PATTERNS: LazyLock<Vec<(&'static str, regex::Regex)>> = LazyLock::new(|| {
    [
        (
            "group",
            r#"(?i)\b(?:api[_-]?key|apikey|access[_-]?token|auth[_-]?token|secret|password|passwd|pwd|client[_-]?secret|private[_-]?key|bearer)\b\s*[:=]\s*["']?([A-Za-z0-9._\-/+]{6,})["']?"#,
        ),
        ("plain", r"(?i)\b(?:sk|pk|rk|vck|xox[baprs])[-_][A-Za-z0-9._\-]{12,}"),
        ("plain", r"(?i)\bgh[pousr]_[A-Za-z0-9]{20,}"),
        ("plain", r"\bAKIA[0-9A-Z]{16}\b"),
        ("key", r"(?s)-----BEGIN [A-Z ]*PRIVATE KEY-----.*?-----END [A-Z ]*PRIVATE KEY-----"),
        ("plain", r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}"),
        ("url", r"(?i)((?:postgres|mysql|mongodb|redis)(?:\+\w+)?)://[^\s:@/]+:[^\s@/]+@"),
    ]
    .iter()
    .map(|(kind, pattern)| (*kind, regex::Regex::new(pattern).expect("secret pattern")))
    .collect()
});

pub fn redact_secrets(text: &str) -> String {
    if text.is_empty() {
        return String::new();
    }
    let mut redacted = text.to_string();
    for (kind, pattern) in SECRET_PATTERNS.iter() {
        redacted = match *kind {
            "group" => pattern
                .replace_all(&redacted, |caps: &regex::Captures<'_>| match caps.get(1) {
                    Some(value) => caps[0].replace(value.as_str(), "[REDACTED]"),
                    None => "[REDACTED]".to_string(),
                })
                .to_string(),
            "key" => pattern
                .replace_all(&redacted, "[REDACTED PRIVATE KEY]")
                .to_string(),
            "url" => pattern
                .replace_all(&redacted, "${1}://[REDACTED]@")
                .to_string(),
            _ => pattern.replace_all(&redacted, "[REDACTED]").to_string(),
        };
    }
    redacted
}

/// Renders a structured state (E0.4) as labelled text with **real newlines**.
///
/// The wire keeps the JSON form (structure + path references), but the offline engine is
/// line-oriented: JSON escapes every newline, which would collapse a multi-line log into a single
/// line and silently change every line-anchored pattern. Mirrors `render_state_text` in
/// Python/TypeScript so the three runtimes score the same text.
pub fn render_state_text(state: &str) -> String {
    let trimmed = state.trim_start();
    if !trimmed.starts_with('{') {
        return state.to_string();
    }
    let parsed: serde_json::Value = match serde_json::from_str(trimmed) {
        Ok(value) => value,
        Err(_) => return state.to_string(),
    };
    let object = match parsed.as_object() {
        Some(map) => map,
        None => return state.to_string(),
    };
    let mut parts: Vec<String> = Vec::new();
    for (key, value) in object {
        // Perception fields are provider-facing metadata (E3.5): the offline engine keeps scoring
        // the full log, so its verdicts stay comparable across runtimes.
        if matches!(
            key.as_str(),
            "focused_slice" | "causal_context" | "raw_log_ref"
        ) {
            continue;
        }
        let rendered = match value {
            serde_json::Value::String(text) => text.clone(),
            other => other.to_string(),
        };
        parts.push(format!("{key}:\n{rendered}"));
    }
    parts.join("\n\n")
}

/// Builds the structured state for one gate, dropping empty fields (parity with Python/TS).
pub fn build_state(fields: serde_json::Map<String, serde_json::Value>) -> String {
    let mut state = serde_json::Map::new();
    for (key, value) in fields {
        let empty = match &value {
            serde_json::Value::Null => true,
            serde_json::Value::String(text) => text.is_empty(),
            serde_json::Value::Array(items) => items.is_empty(),
            serde_json::Value::Object(map) => map.is_empty(),
            _ => false,
        };
        if !empty {
            state.insert(key, value);
        }
    }
    serde_json::Value::Object(state).to_string()
}

/// Mock distribution contract (E3.9). Mirrored in `src/jev_harness/client.py` and
/// `packages/ts/src/client.ts`, and asserted against `tests/fixtures/mock_golden.json`.
/// A signal *conflict* (explicit assertion next to an environment/transient signal) lowers the
/// peak on purpose so a caller can exercise `escalate_to_system2` deterministically.
pub const MOCK_CHOICE_BEST_PEAKED: f64 = 0.85;
pub const MOCK_CHOICE_BEST_CONFLICT: f64 = 0.55;
pub const MOCK_SCORE_BEST_PEAKED: f64 = 0.80;

/// Abort action derived from the dead-end signals (parity with Python/TypeScript).
pub fn mock_abort_action_choice(criteria: &HashMap<String, String>, state_lower: &str) -> String {
    let mut step = state_lower.to_string();
    for marker in ["proposed next step:", "proposed_next_step:"] {
        if let Some((_, tail)) = step.split_once(marker) {
            step = tail.to_string();
        }
    }
    let forward = [
        "implement",
        "fix",
        "resolve",
        "correct",
        "update",
        "create",
        "write",
        "add",
        "install",
        "apply",
        "corrigir",
        "implementar",
        "executar",
        "validar",
        "corregir",
    ]
    .iter()
    .any(|w| step.contains(w));
    let repetitive = [
        "same",
        "repetir",
        "tentar novamente",
        "intentar de nuevo",
        "4a vez",
        "again",
        "identical",
    ]
    .iter()
    .any(|w| step.contains(w));
    let fatal = [
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
    if repetitive || fatal {
        return if criteria.contains_key("abort_and_ask") {
            "abort_and_ask".to_string()
        } else {
            criteria.keys().next().cloned().unwrap_or_default()
        };
    }
    if forward && criteria.contains_key("proceed") {
        return "proceed".to_string();
    }
    String::new()
}

/// Peaked distribution over `options` summing to 1.0 (1.0 when there is a single option).
pub fn mock_distribution(options: &[String], best: &str, peak: f64) -> HashMap<String, f64> {
    let mut out = HashMap::new();
    if options.len() <= 1 {
        for option in options {
            out.insert(option.clone(), 1.0);
        }
        return out;
    }
    let rest = (1.0 - peak) / (options.len() - 1) as f64;
    for option in options {
        out.insert(option.clone(), if option == best { peak } else { rest });
    }
    out
}

static ASSERTION_REGEX: LazyLock<regex::Regex> = LazyLock::new(|| {
    regex::Regex::new(r"(?i)(?:assertionerror|assertionfailed|assertionfailederror|assert\b|assert_eq!|assertthat|expect\(.*?\)\.to|expected:.*received:|failures?:|fail(?:ed)?\s+test|falha de asserção|fallo de aserción|opentest4j)").expect("Invalid assertion regex")
});

// Success summaries emitted by common runners when a suite is green, plus the failure
// signals that veto the `no_failure` short-circuit ("0 failed" is not a veto).
static SUCCESS_PATTERNS: LazyLock<Vec<regex::Regex>> = LazyLock::new(|| {
    [
        r"test result:\s*ok",
        r"[1-9][\d,]*\s+passed\b",
        r"[1-9]\d*\s+passing\b",
        r"test suites?:\s*[1-9]\d*\s+passed",
        r"[1-9]\d*\s+examples?,\s*0\s+failures",
        r"all tests? passed",
        r"\bbuild success(?:ful)?\b",
        r"(?m)^\s*ok\s+\S+",
    ]
    .iter()
    .map(|p| regex::Regex::new(p).expect("Invalid success pattern"))
    .collect()
});

static FAILURE_COUNT_REGEX: LazyLock<regex::Regex> = LazyLock::new(|| {
    regex::Regex::new(r"[1-9\x{FF11}-\x{FF19}\x{0661}-\x{0669}\x{06F1}-\x{06F9}][\d,._\x{00A0} \x{FF10}-\x{FF19}\x{0660}-\x{0669}\x{06F0}-\x{06F9}]*\s*(?:failures|failure|failed|failing|errors?)\b")
        .expect("count")
});
static FAILURE_NOUN_REGEX: LazyLock<regex::Regex> = LazyLock::new(|| {
    regex::Regex::new(
        r"\b[1-9\x{FF11}-\x{FF19}\x{0661}-\x{0669}\x{06F1}-\x{06F9}][\d,._\x{00A0} \x{FF10}-\x{FF19}\x{0660}-\x{0669}\x{06F0}-\x{06F9}]*\s+tests?\s+failed\b",
    )
    .expect("noun")
});

static FAILURE_ASSIGN_REGEX: LazyLock<regex::Regex> = LazyLock::new(|| {
    regex::Regex::new(r"(?:failures?|errors?|failed|failing)\s*[:=]\s*[1-9]").expect("assign")
});
static FAILURE_MARKER_REGEX: LazyLock<regex::Regex> = LazyLock::new(|| {
    // NOTE: `error:` must not be followed by \b — a colon before a space has no word boundary.
    regex::Regex::new(
        r"\b(?:traceback|panic|panicked|assertionerror|assertion failed|not ok)\b|error\s*:",
    )
    .expect("marker")
});
static UPPER_FAILED_REGEX: LazyLock<regex::Regex> =
    LazyLock::new(|| regex::Regex::new(r"\bFAILED\b").expect("FAILED"));
static UPPER_FAIL_LINE_REGEX: LazyLock<regex::Regex> =
    LazyLock::new(|| regex::Regex::new(r"(?m)^\s*FAIL\b|(?m)---\s*FAIL\b").expect("FAIL"));
static RAN_TESTS_REGEX: LazyLock<regex::Regex> =
    LazyLock::new(|| regex::Regex::new(r"ran\s+[1-9]\d*\s+tests?").expect("ran tests"));
static BARE_OK_LINE_REGEX: LazyLock<regex::Regex> =
    LazyLock::new(|| regex::Regex::new(r"(?m)^\s*ok\s*$").expect("ok line"));

/// A failure log is *untrusted input*: the model-jaggedness docs show that adversarial content
/// in the state can steer a decision. These markers mean "this text is addressing the judge",
/// so the log is escalated instead of classified. Kept identical to the Python and TS lists.
static INJECTION_PATTERNS: LazyLock<Vec<regex::Regex>> = LazyLock::new(|| {
    [
        r"(?i)ignore\s+(?:all\s+|any\s+|the\s+)?(?:previous|prior|above|earlier|foregoing)\s+(?:instruction|prompt|rule|direction|message)s?",
        r"(?i)disregard\s+(?:all\s+|any\s+|the\s+)?(?:above|previous|prior|earlier|system)",
        r"(?i)\b(?:ignore|bypass|override)\s+(?:the\s+)?(?:gate|harness|instructions?|safety|polic(?:y|ies))\b",
        r"(?i)<\|(?:im_start|im_end|system|assistant|user)\|>",
        r"\[/?(?:INST|SYS)\]",
        r"(?im)###\s*(?:system|instruction|assistant)\b",
        r#"(?i)"role"\s*:\s*"(?:system|assistant)"\s*,\s*"content""#,
        r"(?i)\bskip_llm\s*[:=]\s*(?:true|false)\b",
        r"(?i)\b(?:classif|labell?|mark|report|record|return|output|respond|answer)\w*\b[^.\n]{0,60}\b(?:as\s+)?(?:env_missing|flaky_transient|syntax_trivial|no_failure)\b",
        r"(?i)\b(?:do\s+not|don't|never)\s+(?:call|invoke|use|escalate\s+to)\s+(?:the\s+)?(?:llm|model|api|system\s*2|frontier)\b",
    ]
    .iter()
    .map(|p| regex::Regex::new(p).expect("injection pattern"))
    .collect()
});

/// True when the log is trying to address the judge instead of describing a failure.
pub fn looks_like_prompt_injection(log: &str) -> bool {
    if log.is_empty() {
        return false;
    }
    INJECTION_PATTERNS
        .iter()
        .any(|pattern| pattern.is_match(log))
}

/// Returns true only when a log is unequivocally a *successful* run summary.
///
/// Strict by design: a positive success summary is required AND every failure signal
/// (non-zero counts, FAIL/FAILED markers, tracebacks, panics, dependency or transient
/// errors) must be absent, so a real failure can never be short-circuited.
pub fn looks_like_test_success(log: &str) -> bool {
    if log.trim().is_empty() {
        return false;
    }
    let text = log.to_lowercase();

    if FAILURE_COUNT_REGEX.is_match(&text)
        || FAILURE_NOUN_REGEX.is_match(&text)
        || FAILURE_ASSIGN_REGEX.is_match(&text)
        || FAILURE_MARKER_REGEX.is_match(&text)
        || UPPER_FAILED_REGEX.is_match(log)
        || UPPER_FAIL_LINE_REGEX.is_match(log)
    {
        return false;
    }
    if ["✗", "❌", "✘", "✕", "×", "‼"]
        .iter()
        .any(|m| log.contains(m))
    {
        return false;
    }
    let unclean = [
        "module not found",
        "no module named",
        "cannot find module",
        "cannot find crate",
        "command not found",
        "connection refused",
        "connection reset",
        "econnrefused",
        "econnreset",
        "etimedout",
        "socket hang up",
        "address already in use",
        "timed out",
        "timeout",
    ];
    if unclean.iter().any(|s| text.contains(s)) {
        return false;
    }

    if SUCCESS_PATTERNS.iter().any(|p| p.is_match(&text)) {
        return true;
    }
    RAN_TESTS_REGEX.is_match(&text) && BARE_OK_LINE_REGEX.is_match(&text)
}

static FAIL_LINE_REGEX: LazyLock<regex::Regex> =
    LazyLock::new(|| regex::Regex::new(r"(?i)^fail(?:ed)?\b").expect("Invalid fail line regex"));

static FAIL_TO_REGEX: LazyLock<regex::Regex> =
    LazyLock::new(|| regex::Regex::new(r"(?i)^fail(?:ed)?\s+to\b").expect("Invalid fail-to regex"));

static EXPECTED_RECEIVED_REGEX: LazyLock<regex::Regex> = LazyLock::new(|| {
    regex::Regex::new(r"(?is)expected:.{0,300}?received:").expect("Invalid expected/received regex")
});

static BARE_EXCEPTION_REGEX: LazyLock<regex::Regex> = LazyLock::new(|| {
    regex::Regex::new(r"(?i)^(?:valueerror|runtimeerror|typeerror|keyerror|indexerror|zerodivisionerror|attributeerror|overflowerror|arithmeticerror|illegalargumentexception|illegalstateexception):").expect("Invalid bare exception regex")
});

static FAILURE_REGEX: LazyLock<regex::Regex> = LazyLock::new(|| {
    regex::Regex::new(r"(?i)(?:assertionerror|assertionfailed|assertionfailederror|failures?:\s*[1-9]|failed\b|falhou\b|\d+\s+failed\b|not\s+ok\b|segmentation\s+fault|sigsegv|panic\b|core\s+dumped)").expect("Invalid failure regex")
});

static NEGATION_REGEX: LazyLock<regex::Regex> = LazyLock::new(|| {
    regex::Regex::new(r"(?i)\b(not|do\s+not|don't|não|nao|no|never|sem|evitar|avoid)\s+(\w+\s+){0,3}(abort|abortar|stop|parar|detener|falhar|fail|deadlock|circular|dead\s*end)").expect("Invalid negation regex")
});

// Provider payload limits (jev-1.13: 64k tokens total; 32k for state + longest question).
// Characters are a conservative proxy (~4 chars/token) with no external tokenizer.
pub const MAX_STATE_CHARS: usize = 128_000;
pub const MAX_TOTAL_CHARS: usize = 256_000;

#[derive(Debug, Clone)]
pub struct JevClient {
    pub api_key: Option<String>,
    pub base_url: String,
    pub model: String,
    /// Where the effective model came from: "argument" | "env" | ".jev.json" | "provider_default".
    pub model_source: String,
    pub provider: String,
    pub timeout_ms: u64,
    pub force_mock: bool,
    /// Fail-open (default): degrade to the offline engine and mark the response.
    pub fail_open: bool,
    /// Maximum provider attempts for retryable failures (429/5xx/timeout/network).
    pub max_retries: u32,
    /// Base delay for exponential backoff in ms.
    pub retry_base_delay_ms: u64,
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
        let (final_model, model_source) = Self::resolve_model(model, &resolved_provider);
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
            model_source: model_source.to_string(),
            provider: resolved_provider,
            timeout_ms: final_timeout,
            force_mock,
            fail_open: true,
            max_retries: 3,
            retry_base_delay_ms: 500,
            http_client,
        }
    }

    /// Resolution order: explicit argument > `JEV_MODEL` env var > repository `.jev.json`
    /// override > provider default. The generic placeholder (`jev-latest`, what
    /// `jev-harness init` scaffolds) is treated as "no override" so scaffolded configs never
    /// clobber provider model IDs.
    pub fn resolve_model(model: Option<String>, provider: &str) -> (String, &'static str) {
        if let Some(explicit) = model {
            return (explicit, "argument");
        }
        if let Ok(from_env) = std::env::var("JEV_MODEL") {
            let trimmed = from_env.trim();
            if !trimmed.is_empty() {
                return (trimmed.to_string(), "env");
            }
        }
        if let Some(repo_model) = load_repo_config()
            .model
            .as_ref()
            .filter(|m| m.as_str() != DEFAULT_MODEL)
        {
            return (repo_model.clone(), ".jev.json");
        }
        let provider_default = match provider {
            "commandcode" => "typesafe/jev",
            "opencode" => "jev-1.13-free",
            "openrouter" => "typesafe/jev-1.13",
            "vercel" => "typesafe-ai/jev",
            _ => DEFAULT_MODEL,
        };
        (provider_default.to_string(), "provider_default")
    }

    pub fn with_mock() -> Self {
        Self {
            api_key: None,
            base_url: TYPESAFE_API_URL.to_string(),
            model: DEFAULT_MODEL.to_string(),
            model_source: "provider_default".to_string(),
            provider: "mock".to_string(),
            timeout_ms: DEFAULT_TIMEOUT_MS,
            force_mock: true,
            fail_open: true,
            max_retries: 3,
            retry_base_delay_ms: 500,
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
        let repo_config = load_repo_config();
        let model = if let Some(repo_model) = repo_config
            .model
            .as_ref()
            .filter(|m| m.as_str() != DEFAULT_MODEL)
        {
            repo_model.clone()
        } else {
            match prov.as_str() {
                "commandcode" => "typesafe/jev".to_string(),
                "opencode" => "jev-1.13-free".to_string(),
                "openrouter" => "typesafe/jev-1.13".to_string(),
                "vercel" => "typesafe-ai/jev".to_string(),
                _ => DEFAULT_MODEL.to_string(),
            }
        };
        let model_source = Self::resolve_model(None, &prov).1;
        Self {
            api_key,
            base_url,
            model,
            model_source: model_source.to_string(),
            provider: prov,
            timeout_ms: DEFAULT_TIMEOUT_MS,
            force_mock: false,
            fail_open: true,
            max_retries: 3,
            retry_base_delay_ms: 500,
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
                return (Some(key), "vercel".to_string(), VERCEL_API_URL.to_string());
            }
        }

        if let Ok(key) = env::var("VERCEL_API_KEY") {
            if !key.trim().is_empty() {
                return (Some(key), "vercel".to_string(), VERCEL_API_URL.to_string());
            }
        }

        if let Ok(key) = env::var("AI_GATEWAY_API_KEY") {
            if !key.trim().is_empty() {
                return (Some(key), "vercel".to_string(), VERCEL_API_URL.to_string());
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
                        return (Some(k.to_string()), prov.to_string(), url.to_string());
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
                    if trimmed.starts_with("CMD_API_KEY=")
                        || trimmed.starts_with("COMMAND_CODE_API_KEY=")
                    {
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
                    if trimmed.starts_with("VERCEL_AI_GATEWAY_API_KEY=")
                        || trimmed.starts_with("VERCEL_API_KEY=")
                        || trimmed.starts_with("AI_GATEWAY_API_KEY=")
                    {
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
                    let key_opt = val
                        .get("apiKey")
                        .or_else(|| val.get("api_key"))
                        .and_then(|v| v.as_str());
                    if let Some(k) = key_opt {
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

    /// Builder for the failure policy used by every command:
    /// fail-open is the default for gates; fail-closed surfaces errors instead.
    pub fn with_failure_policy(
        mut self,
        fail_open: bool,
        max_retries: u32,
        retry_base_delay_ms: u64,
    ) -> Self {
        self.fail_open = fail_open;
        self.max_retries = max_retries.max(1);
        self.retry_base_delay_ms = retry_base_delay_ms;
        self
    }

    /// Exponential backoff honoring a provider `Retry-After`. Fractional seconds are accepted so
    /// the three runtimes agree on the delay; the value is capped for fast CI.
    pub fn retry_delay_ms(&self, attempt: u32, retry_after: Option<f64>) -> u64 {
        if let Some(seconds) = retry_after {
            if seconds.is_finite() && seconds >= 0.0 {
                return ((seconds * 1000.0) as u64).min(30_000);
            }
        }
        let factor = 1u64 << attempt.saturating_sub(1).min(6);
        self.retry_base_delay_ms.saturating_mul(factor).min(5_000)
    }

    pub async fn system_one(
        &self,
        state: &str,
        questions: HashMap<String, Question>,
    ) -> Result<JevResponse, JevError> {
        // E3.1: a question with a single option has no distribution to measure.
        for question in questions.values() {
            match question {
                Question::Choice(choice) => {
                    crate::uncertainty::validate_question_options(choice.criteria.len())
                        .map_err(JevError::Config)?
                }
                Question::Score(score) => {
                    crate::uncertainty::validate_question_options(score.criteria.len())
                        .map_err(JevError::Config)?
                }
                Question::Noul(_) => {}
            }
        }
        let redacted_state = redact_secrets(state);
        let state = redacted_state.as_str();
        let is_live = !self.force_mock && (self.provider == "opencode" || self.api_key.is_some());
        if !is_live {
            return Ok(self.simulate_system_one(state, &questions, &self.model));
        }

        // Count code points (not UTF-8 bytes) so the three runtimes agree on the limit.
        let state_chars = state.chars().count();
        let questions_chars = serde_json::to_string(&questions)
            .map(|s| s.chars().count())
            .unwrap_or(0);
        if state_chars > MAX_STATE_CHARS || state_chars + questions_chars > MAX_TOTAL_CHARS {
            return Err(JevError::Config(format!(
                "Payload exceeds the provider limit: {} state chars + {} question chars (limit: {} state / {} total, ~32k/64k tokens). Trim the state or split the questions.",
                state_chars,
                questions_chars,
                MAX_STATE_CHARS,
                MAX_TOTAL_CHARS
            )));
        }

        let mut payload = serde_json::json!({
            "model": self.model,
            "state": state,
            "questions": questions
        });
        if self.provider == "openrouter" {
            payload["provider"] =
                serde_json::json!({ "only": ["typesafe"], "allow_fallbacks": false });
        } else if self.provider == "vercel" {
            payload["providerOptions"] =
                serde_json::json!({ "gateway": { "only": ["typesafe-ai"] } });
        }

        let mut attempt: u32 = 0;
        loop {
            attempt += 1;
            let attempt_started = std::time::Instant::now();
            let mut req = self
                .http_client
                .post(&self.base_url)
                .header("Content-Type", "application/json");

            if let Some(ref key) = self.api_key {
                if key != "zen" {
                    req = req.header("Authorization", format!("Bearer {}", key));
                }
            }
            if self.provider == "openrouter" {
                req = req
                    .header(
                        "HTTP-Referer",
                        "https://github.com/ismaelsoilet/jev-harness",
                    )
                    .header("X-Title", "Jev Harness");
            }

            let resp_result = req.json(&payload).send().await;

            match resp_result {
                Ok(resp) => {
                    let status = resp.status().as_u16();
                    if !resp.status().is_success() {
                        let retry_after = resp
                            .headers()
                            .get("retry-after")
                            .and_then(|v| v.to_str().ok())
                            .and_then(|s| s.trim().parse::<f64>().ok());
                        let raw_text = resp.text().await.unwrap_or_default();
                        let text = Self::redact_secrets(&raw_text, self.api_key.as_deref());
                        if status == 401 || status == 403 {
                            if !self.fail_open {
                                return Err(JevError::Api {
                                    status,
                                    message: text,
                                });
                            }
                            eprintln!("[JEV WARNING] {} auth failed (HTTP {}); falling back to offline simulation.", self.provider, status);
                            let mut sim = self.simulate_system_one(state, &questions, &self.model);
                            sim.degraded_reason = format!("auth_{}", status);
                            return Ok(sim);
                        }
                        let retryable = status == 429 || status >= 500;
                        if retryable && attempt < self.max_retries {
                            let delay = self.retry_delay_ms(attempt, retry_after);
                            if delay > 0 {
                                tokio::time::sleep(Duration::from_millis(delay)).await;
                            }
                            continue;
                        }
                        if self.fail_open {
                            eprintln!(
                                "[JEV WARNING] {} API HTTP {}; falling back to offline simulation.",
                                self.provider, status
                            );
                            let mut sim = self.simulate_system_one(state, &questions, &self.model);
                            sim.degraded_reason = format!("http_{}", status);
                            return Ok(sim);
                        }
                        return Err(JevError::Api {
                            status,
                            message: text,
                        });
                    }

                    match resp.json::<serde_json::Value>().await {
                        Ok(parsed) => match self.parse_api_response(&parsed) {
                            Ok(response) => return Ok(response),
                            Err(e) => {
                                if attempt < self.max_retries {
                                    let delay = self.retry_delay_ms(attempt, None);
                                    if delay > 0 {
                                        tokio::time::sleep(Duration::from_millis(delay)).await;
                                    }
                                    continue;
                                }
                                if self.fail_open {
                                    eprintln!(
                                        "[JEV WARNING] {} returned a malformed response: {}; falling back to offline simulation.",
                                        self.provider, e
                                    );
                                    let mut sim =
                                        self.simulate_system_one(state, &questions, &self.model);
                                    sim.degraded_reason = "invalid_response".to_string();
                                    return Ok(sim);
                                }
                                return Err(e);
                            }
                        },
                        Err(_) => {
                            if attempt < self.max_retries {
                                let delay = self.retry_delay_ms(attempt, None);
                                if delay > 0 {
                                    tokio::time::sleep(Duration::from_millis(delay)).await;
                                }
                                continue;
                            }
                            if self.fail_open {
                                eprintln!("[JEV WARNING] {} returned a non-JSON response; falling back to offline simulation.", self.provider);
                                let mut sim =
                                    self.simulate_system_one(state, &questions, &self.model);
                                sim.degraded_reason = "invalid_response".to_string();
                                return Ok(sim);
                            }
                            return Err(JevError::Config(
                                "Provider returned a non-JSON response".to_string(),
                            ));
                        }
                    }
                }
                Err(e) => {
                    let retryable = e.is_timeout() || e.is_connect() || e.is_request();
                    if retryable && attempt < self.max_retries {
                        let delay = self.retry_delay_ms(attempt, None);
                        if delay > 0 {
                            tokio::time::sleep(Duration::from_millis(delay)).await;
                        }
                        continue;
                    }
                    if self.fail_open {
                        // A read timeout surfaces as a generic request error: classify by
                        // elapsed time so the marker matches Python and TypeScript.
                        let elapsed_ratio = attempt_started.elapsed().as_millis() as u64;
                        let timed_out = e.is_timeout()
                            || (!e.is_connect()
                                && elapsed_ratio >= self.timeout_ms.saturating_mul(9) / 10);
                        eprintln!("[JEV WARNING] {} transport error ({}); falling back to offline simulation.", self.provider, e);
                        let mut sim = self.simulate_system_one(state, &questions, &self.model);
                        sim.degraded_reason = if timed_out {
                            "timeout".to_string()
                        } else {
                            "connection".to_string()
                        };
                        return Ok(sim);
                    }
                    return Err(JevError::Http(e));
                }
            }
        }
    }

    /// Strictly parses a provider payload. A 200 whose fields have the wrong types is an error
    /// (handled by the failure policy), never a silently dropped answer or a defaulted score.
    pub fn parse_api_response(&self, val: &serde_json::Value) -> Result<JevResponse, JevError> {
        let model = val
            .get("model")
            .and_then(|v| v.as_str())
            .unwrap_or(&self.model)
            .to_string();

        let mut answers = HashMap::new();

        let raw_answers = val.get("answers").filter(|v| !v.is_null());
        if let Some(raw) = raw_answers {
            let ans_obj = raw.as_object().ok_or_else(|| {
                JevError::Config("malformed response: 'answers' must be a JSON object".to_string())
            })?;
            for (k, v) in ans_obj {
                let parsed = serde_json::from_value::<Answer>(v.clone()).map_err(|e| {
                    JevError::Config(format!(
                        "malformed response: answer '{}' could not be parsed: {}",
                        k, e
                    ))
                })?;
                answers.insert(k.clone(), parsed);
            }
        }

        if answers.is_empty() {
            // A live response with nothing usable would silently make every gate fall back to
            // its defaults; that must be a visible degradation instead.
            return Err(JevError::Config(
                "malformed response: no answers could be parsed".to_string(),
            ));
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
            degraded_reason: String::new(),
        })
    }

    /// Fast regex-based deterministic decision simulation (< 500µs).
    pub fn simulate_system_one(
        &self,
        state: &str,
        questions: &HashMap<String, Question>,
        model_name: &str,
    ) -> JevResponse {
        let rendered_state = render_state_text(state);
        let state = rendered_state.as_str();
        let state_lower = state.to_lowercase();
        let state_tokens: HashSet<String> = state_lower
            .split(|c: char| !c.is_alphanumeric() && c != '_')
            .filter(|s| !s.is_empty())
            .map(|s| s.to_string())
            .collect();

        let real_assertion = state_lower.lines().any(|line| {
            let t = line.trim();
            t.starts_with("panicked at")
                || t.starts_with("panic:")
                || ASSERTION_REGEX.is_match(t)
                // Bare pytest/Jest `FAIL`/`FAILED` lines are assertions, but prose such as
                // "Failed to start the server" is a transient/environment report. Two regexes
                // mirror Python/TS `^fail(?:ed)?(?!\s+to\b)\b` exactly (the regex crate has no
                // lookahead), so `failing tests:` / `failsafe mode` are not treated as assertions.
                || (FAIL_LINE_REGEX.is_match(t) && !FAIL_TO_REGEX.is_match(t))
        }) || EXPECTED_RECEIVED_REGEX.is_match(&state_lower);
        let bare_exception = state_lower
            .lines()
            .any(|line| BARE_EXCEPTION_REGEX.is_match(line.trim()));
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
            "importerror",
            "cannot find module",
            "err_module_not_found",
            "ts2307",
            "cannot find crate",
            "can't find crate",
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
            "already in use",
            "address already in use",
            "eaddrinuse",
            "port already in use",
            "port is already in use",
            "porta já está em uso",
            "puerto ya está en uso",
        ];

        // Precedence rule (.agents/rules/04): an explicit assertion/expectation mismatch always
        // outranks dependency or transient words in the same log. A bare exception name is logic
        // evidence only when no concrete env/flaky root cause is present.
        let has_env_signal = env_missing_triggers.iter().any(|k| state_lower.contains(k));
        let has_flaky_signal = flaky_triggers.iter().any(|k| state_lower.contains(k));
        let is_explicit_assertion =
            real_assertion || (bare_exception && !(has_env_signal || has_flaky_signal));
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
            "git", "diff", "typo", "flake8", "eslint", "prettier", "linter", "echo", "pwd",
            "format", "black", "lint", "cat", "ls",
        ];
        let multi_word_mech = [
            "git status",
            "git diff",
            "git log",
            "view file",
            "read file",
            "cat file",
            "check status",
            "run linter",
            "fix typo",
            "ler arquivo",
            "verificar arquivo",
            "formatar código",
            "leer archivo",
            "corregir errata",
            "listar arquivos",
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
                    // The abort gate's action is derived from the same signals as its dead-end
                    // question: letting token overlap pick "abort_and_ask" beside a low dead-end
                    // probability made the gate contradict its own evidence (parity with Python/TS).
                    let derived_abort_action = if cq.criteria.contains_key("abort_and_ask")
                        && cq.criteria.contains_key("proceed")
                    {
                        mock_abort_action_choice(&cq.criteria, &state_lower)
                    } else {
                        String::new()
                    };
                    if !derived_abort_action.is_empty() {
                        best_choice = derived_abort_action.clone();
                    }
                    let mut best_score: i32 = 0;

                    // Canonical (sorted) order so ties break identically in every runtime.
                    let mut ordered_keys: Vec<&String> = cq.criteria.keys().collect();
                    ordered_keys.sort();
                    for opt in ordered_keys {
                        let desc = &cq.criteria[opt];
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

                        if !derived_abort_action.is_empty() {
                            continue; // derived from the dead-end signal, not overlap
                        }
                        if score > best_score {
                            best_score = score;
                            best_choice = opt.clone();
                        }
                    }

                    let is_effort_q = qid == "effort"
                        || [
                            "none", "minimal", "low", "medium", "high", "xhigh", "max", "ultra",
                        ]
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
                    } else if qid == "workflow_phase"
                        || (cq.criteria.contains_key("execute")
                            && cq.criteria.contains_key("complete"))
                    {
                        // Canonical phase contract (parity with Python/TypeScript).
                        let is_waiting_q = state_lower.contains('?')
                            || [
                                "waiting for your",
                                "waiting on user",
                                "wait for my go-ahead",
                                "please confirm",
                                "which option",
                                "do you approve",
                                "would you like me to",
                                "do you want me to",
                                "need your api key",
                                "aguardando sua aprovação",
                                "aguardando usuário",
                                "qual opção você prefere",
                                "qual opção",
                                "preciso que você confirme",
                                "preciso de permissão",
                                "need clarification",
                                "please clarify",
                                "need permission",
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
                            "updated file",
                            "edited file",
                            "finished editing",
                            "modified file",
                            "wrote code",
                            "atualizei o arquivo",
                            "alterei o arquivo",
                            "terminei de editar",
                            "arquivo alterado",
                        ]
                        .iter()
                        .any(|w| state_lower.contains(w));
                        let is_unfinished = [
                            "next i'll",
                            "next i will",
                            "now i will",
                            "continuarei",
                            "a seguir vou",
                            "próximo passo farei",
                            "1 of 5",
                            "2 of 5",
                            "3 of 5",
                            "4 of 5",
                            "step 1 of",
                            "step 1 done",
                            "unfinished",
                            "remaining",
                            "todo:",
                            "pendente",
                            "partial",
                            "parcial",
                            "in progress",
                            "falta implementar",
                            "falta rodar os testes",
                            "sem testar",
                            "without running tests",
                            "tests not run",
                            "haven't run pytest",
                            "need to run",
                            "need to verify",
                            "to verify",
                            "unverified",
                            "run pytest",
                            "run cargo test",
                            "run npm test",
                            "updated file",
                            "edited file",
                            "finished editing",
                            "modified file",
                            "wrote code",
                            "atualizei o arquivo",
                            "alterei o arquivo",
                            "terminei de editar",
                            "arquivo alterado",
                            "next step",
                        ]
                        .iter()
                        .any(|w| state_lower.contains(w));
                        let is_complete = [
                            "all done",
                            "100% passing",
                            "all criteria satisfied",
                            "tudo concluído",
                            "todas as etapas concluídas",
                            "task complete",
                            "konnichiwa! all done",
                            "all tests passed",
                            "tests passed (0 failed)",
                            "completed and verified",
                            "completed all",
                            "concluído com sucesso",
                            "todos os testes passaram",
                        ]
                        .iter()
                        .any(|w| state_lower.contains(w));

                        if is_waiting_q && cq.criteria.contains_key("ask") {
                            best_choice = "ask".to_string();
                        } else if is_complete && cq.criteria.contains_key("complete") {
                            best_choice = "complete".to_string();
                        } else if is_unverified && cq.criteria.contains_key("verify") {
                            best_choice = "verify".to_string();
                        } else if is_unfinished && cq.criteria.contains_key("execute") {
                            best_choice = "execute".to_string();
                        }
                        // No explicit fallback: an undecided phase keeps the generic scoring
                        // result, matching Python and TypeScript.
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
                    ]
                    .iter()
                    .any(|k| state_lower.contains(k));
                    let has_signal_conflict = (is_explicit_assertion || has_deadlock_or_loop)
                        && (has_env_signal || has_flaky_signal);
                    let options: Vec<String> = cq.criteria.keys().cloned().collect();
                    let probs = mock_distribution(
                        &options,
                        &best_choice,
                        if has_signal_conflict {
                            MOCK_CHOICE_BEST_CONFLICT
                        } else {
                            MOCK_CHOICE_BEST_PEAKED
                        },
                    );
                    answers.insert(
                        qid.clone(),
                        Answer::Choice(ChoiceAnswer {
                            choice: best_choice,
                            confidence: 0.88,
                            probabilities: Some(probs),
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
                        "pass",
                        "sucesso",
                        "éxito",
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

                    let is_satisfaction_failure =
                        has_explicit_failure && (qid == "satisfaction" || qid == "rigor");
                    let is_unviable_step = qid == "viability"
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
                            || has_deadlock_or_loop);

                    if is_satisfaction_failure || is_unviable_step {
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

                    let levels: Vec<String> = (1..=n_levels).map(|i| i.to_string()).collect();
                    let probs = mock_distribution(
                        &levels,
                        &matched_idx.to_string(),
                        MOCK_SCORE_BEST_PEAKED,
                    );
                    answers.insert(
                        qid.clone(),
                        Answer::Score(ScoreAnswer {
                            score: matched_idx as f64,
                            confidence: 0.85,
                            legend: Some(serde_json::json!(sq.criteria)),
                            probabilities: Some(probs),
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
                    // Structured state (E0.4) or legacy concatenated text — accept both markers.
                    let mut proposed_part: &str = &state_lower;
                    for marker in ["proposed next step:", "proposed_next_step:"] {
                        if let Some((_, tail)) = proposed_part.split_once(marker) {
                            proposed_part = tail;
                        }
                    }
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
                        && (inst.contains("deterministically") || inst.contains("skip"))
                    {
                        prob = 0.95;
                    }

                    // CommandCode Jev Nudge continuation heuristics
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
                    let is_done = [
                        "all done",
                        "100% passing",
                        "all criteria satisfied",
                        "tudo concluído",
                        "todas as etapas concluídas",
                        "task complete",
                        "konnichiwa! all done",
                        "all tests passed",
                        "tests passed (0 failed)",
                        "completed and verified",
                    ]
                    .iter()
                    .any(|w| state_lower.contains(w));
                    let has_unfinished_work = [
                        "next i'll",
                        "next i will",
                        "now i will",
                        "continuarei",
                        "a seguir vou",
                        "próximo passo farei",
                        "1 of 5",
                        "2 of 5",
                        "3 of 5",
                        "4 of 5",
                        "step 1 of",
                        "step 1 done",
                        "unfinished",
                        "remaining",
                        "todo:",
                        "pendente",
                        "partial",
                        "parcial",
                        "in progress",
                        "falta implementar",
                        "falta rodar os testes",
                        "sem testar",
                        "without running tests",
                        "tests not run",
                        "haven't run pytest",
                        "need to run",
                        "need to verify",
                        "to verify",
                        "unverified",
                        "run pytest",
                        "run cargo test",
                        "run npm test",
                        "updated file",
                        "edited file",
                        "finished editing",
                        "modified file",
                        "wrote code",
                        "atualizei o arquivo",
                        "alterei o arquivo",
                        "terminei de editar",
                        "arquivo alterado",
                        "next step",
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
                        prob = if has_no_progress { 0.12 } else { 0.85 };
                    } else if qid == "nudge" || inst.contains("gentle nudge") {
                        if is_waiting_on_user || has_no_progress || is_done {
                            prob = 0.06;
                        } else if has_unfinished_work {
                            prob = 0.82;
                        } else {
                            prob = 0.20;
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
            degraded_reason: String::new(),
        }
    }
}
