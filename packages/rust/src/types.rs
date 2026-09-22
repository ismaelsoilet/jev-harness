//! Strongly typed data contracts for TypeSafe Jev System One.

use serde::{Deserialize, Serialize};
use std::collections::HashMap;

/// Choice question: selects one key from a map of criteria.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct ChoiceQuestion {
    pub instructions: String,
    pub criteria: HashMap<String, String>,
}

/// Score question: rates state against an ordered rubric array.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct ScoreQuestion {
    pub instructions: String,
    pub criteria: Vec<String>,
}

/// Noul question: asks for probability (0.0 to 1.0) that answer is affirmative.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct NoulQuestion {
    pub instructions: String,
}

/// Question enum tagged by "type".
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
#[serde(tag = "type")]
pub enum Question {
    #[serde(rename = "choice")]
    Choice(ChoiceQuestion),
    #[serde(rename = "score")]
    Score(ScoreQuestion),
    #[serde(rename = "noul")]
    Noul(NoulQuestion),
}

/// Choice answer with chosen key and calibrated confidence.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct ChoiceAnswer {
    pub choice: String,
    pub confidence: f64,
    #[serde(default)]
    pub probabilities: Option<HashMap<String, f64>>,
}

/// Score answer with integer rating (1-indexed) and confidence.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct ScoreAnswer {
    pub score: i32,
    pub confidence: f64,
    #[serde(default)]
    pub legend: Option<Vec<String>>,
}

/// Noul answer with calibrated probability between 0.0 and 1.0.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct NoulAnswer {
    pub noul: f64,
}

/// Answer enum tagged by "type".
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
#[serde(tag = "type")]
pub enum Answer {
    #[serde(rename = "choice")]
    Choice(ChoiceAnswer),
    #[serde(rename = "score")]
    Score(ScoreAnswer),
    #[serde(rename = "noul")]
    Noul(NoulAnswer),
}

impl Answer {
    pub fn as_choice(&self) -> Option<&ChoiceAnswer> {
        match self {
            Answer::Choice(a) => Some(a),
            _ => None,
        }
    }

    pub fn as_score(&self) -> Option<&ScoreAnswer> {
        match self {
            Answer::Score(a) => Some(a),
            _ => None,
        }
    }

    pub fn as_noul(&self) -> Option<&NoulAnswer> {
        match self {
            Answer::Noul(a) => Some(a),
            _ => None,
        }
    }
}

/// Token usage reported by API.
#[derive(Debug, Clone, Serialize, Deserialize, Default, PartialEq)]
pub struct JevUsage {
    #[serde(default)]
    pub input_tokens: u32,
    #[serde(default)]
    pub output_tokens: u32,
}

/// Complete response from Jev System One.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct JevResponse {
    pub model: String,
    pub answers: HashMap<String, Answer>,
    #[serde(default)]
    pub usage: JevUsage,
    #[serde(default)]
    pub is_mock: bool,
}

/// Triage result for test or execution failure.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct TestTriageResult {
    pub category: String,
    pub confidence: f64,
    pub skip_llm: bool,
    pub skip_llm_prob: f64,
    pub severity_score: f64,
    pub action_recommendation: String,
    pub is_mock: bool,
}

/// Result of loop abort and dead-end check.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct AbortGateResult {
    pub should_abort: bool,
    pub abort_probability: f64,
    pub action: String,
    pub viability_score: f64,
    pub reasoning_summary: String,
    pub is_mock: bool,
}

/// Model tier routing decision.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct ModelRouteResult {
    pub selected_tier: String,
    pub confidence: f64,
    pub complexity_score: f64,
    pub recommended_model: String,
    pub rationale: String,
    pub is_mock: bool,
}

/// Step completion verification result.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct VerificationResult {
    pub is_verified: bool,
    pub satisfaction_probability: f64,
    pub rigor_score: f64,
    pub confidence: f64,
    pub needs_rework: bool,
    pub is_mock: bool,
}

/// Dynamic reasoning effort modulation result (Astra-Jev).
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct ReasoningEffortResult {
    pub effort: String,
    pub confidence: f64,
    pub complexity_score: f64,
    pub rationale: String,
    pub provider: String,
    pub provider_params: serde_json::Value,
    pub is_reasoning_supported: bool,
    pub cache_safe_recommendation: String,
    pub lease_steps: u32,
    pub is_mock: bool,
}

/// Continuation nudge decision result (SureForge + CommandCode Jev Nudge).
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct NudgeGateResult {
    pub should_nudge: bool,
    pub nudge_probability: f64,
    pub waiting_probability: f64,
    pub progress_probability: f64,
    pub sureforge_phase: String,
    pub suggested_nudge_prompt: String,
    pub rationale: String,
    pub is_mock: bool,
}

/// Error type for Jev operations.
#[derive(Debug)]
pub enum JevError {
    Http(reqwest::Error),
    Json(serde_json::Error),
    Config(String),
    Api { status: u16, message: String },
}

impl std::fmt::Display for JevError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            JevError::Http(e) => write!(f, "HTTP error: {}", e),
            JevError::Json(e) => write!(f, "JSON serialization error: {}", e),
            JevError::Config(m) => write!(f, "Configuration error: {}", m),
            JevError::Api { status, message } => {
                write!(f, "API error (HTTP {}): {}", status, message)
            }
        }
    }
}

impl std::error::Error for JevError {}

impl From<reqwest::Error> for JevError {
    fn from(e: reqwest::Error) -> Self {
        JevError::Http(e)
    }
}

impl From<serde_json::Error> for JevError {
    fn from(e: serde_json::Error) -> Self {
        JevError::Json(e)
    }
}
