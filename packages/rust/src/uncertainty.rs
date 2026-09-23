//! E3.1 — uncertainty with guards, mirroring `src/jev_harness/uncertainty.py` and
//! `packages/ts/src/uncertainty.ts`.
//!
//! Zeros are ignored (never `0·ln 0`), both key conventions (`"0".."K−1"` and `"1".."K"`) read
//! the same, `K < 2` has no shape to report, and `confidence` stays the primary measure. Nothing
//! here changes a gate verdict: `skip_llm` and the exit codes are untouched.
use std::collections::HashMap;

pub const LOW_CONFIDENCE_THRESHOLD: f64 = 0.65;

#[derive(Debug, Clone, PartialEq)]
pub struct UncertaintyShape {
    pub margin: Option<f64>,
    pub normalized_entropy: Option<f64>,
    pub levels: Option<usize>,
}

#[derive(Debug, Clone, PartialEq)]
pub struct Uncertainty {
    pub margin: Option<f64>,
    pub normalized_entropy: Option<f64>,
    pub confidence: Option<f64>,
    pub escalate_to_system2: bool,
    pub escalation_reason: String,
}

/// Maps both key conventions to a 1-based level index.
pub fn normalize_level_keys(probabilities: &HashMap<String, f64>) -> HashMap<usize, f64> {
    let zero_based = probabilities
        .keys()
        .filter_map(|key| key.parse::<i64>().ok())
        .min()
        .map(|min| min == 0)
        .unwrap_or(false);
    let mut normalized = HashMap::new();
    // Non-numeric keys are appended after the numeric space, in the order they appear: the same
    // rule in Python, TypeScript and Rust, so the three runtimes agree on `levels`/`margin`.
    let mut next_free = match probabilities
        .keys()
        .filter_map(|key| key.parse::<i64>().ok())
        .max()
    {
        Some(maximum) => (maximum + if zero_based { 1 } else { 0 } + 1) as usize,
        None => 1,
    };
    for (key, value) in probabilities {
        if !value.is_finite() {
            continue;
        }
        let index = match key.parse::<i64>() {
            Ok(number) => (number + if zero_based { 1 } else { 0 }) as usize,
            Err(_) => {
                let index = next_free;
                next_free += 1;
                index
            }
        };
        normalized.entry(index).or_insert(*value);
    }
    normalized
}

pub fn distribution_shape(probabilities: Option<&HashMap<String, f64>>) -> UncertaintyShape {
    let probabilities = match probabilities {
        Some(map) if !map.is_empty() => map,
        _ => {
            return UncertaintyShape {
                margin: None,
                normalized_entropy: None,
                levels: None,
            }
        }
    };
    let normalized = normalize_level_keys(probabilities);
    let positive: Vec<f64> = normalized
        .values()
        .copied()
        .filter(|weight| *weight > 0.0)
        .collect();
    let k = positive.len();
    if k < 2 {
        return UncertaintyShape {
            margin: None,
            normalized_entropy: None,
            levels: if k == 0 { None } else { Some(k) },
        };
    }
    let total: f64 = positive.iter().sum();
    if total <= 0.0 {
        return UncertaintyShape {
            margin: None,
            normalized_entropy: None,
            levels: Some(k),
        };
    }
    let mut shares: Vec<f64> = positive.iter().map(|weight| weight / total).collect();
    shares.sort_by(|a, b| b.partial_cmp(a).unwrap_or(std::cmp::Ordering::Equal));
    let margin = shares[0] - shares[1];
    let entropy: f64 = shares
        .iter()
        .filter(|share| **share > 0.0)
        .map(|share| -share * share.ln())
        .sum();
    UncertaintyShape {
        margin: Some(round9(margin)),
        normalized_entropy: Some(round9(entropy / (k as f64).ln())),
        levels: Some(k),
    }
}

pub fn build_uncertainty(
    probabilities: Option<&HashMap<String, f64>>,
    confidence: Option<f64>,
    category: &str,
    threshold: f64,
) -> Uncertainty {
    let shape = distribution_shape(probabilities);
    let clean = confidence.filter(|value| value.is_finite()).map(round9);
    let mut escalate = false;
    let mut reason = String::new();
    if category == "no_failure" {
        reason = "a passing run is never escalated".to_string();
    } else if category == "deep_logic" {
        escalate = true;
        reason = "category is deep_logic: a reasoning model is the natural next step".to_string();
    } else if let Some(value) = clean {
        if value < threshold {
            escalate = true;
            reason = format!("confidence {value:.2} is below the {threshold:.2} threshold");
        }
    }
    Uncertainty {
        margin: shape.margin,
        normalized_entropy: shape.normalized_entropy,
        confidence: clean,
        escalate_to_system2: escalate,
        escalation_reason: reason,
    }
}

fn round9(value: f64) -> f64 {
    (value * 1e9).round() / 1e9
}

/// `K >= 2` is a precondition: a one-option question has no distribution to measure.
pub fn validate_question_options(count: usize) -> Result<(), String> {
    if count < 2 {
        return Err(
            "a Choice/Score question needs at least two options: with a single option there is no \
             distribution to measure (and the provider's own confidence is undefined)"
                .to_string(),
        );
    }
    Ok(())
}
