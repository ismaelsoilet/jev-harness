/**
 * E3.1 — uncertainty with guards, mirroring `src/jev_harness/uncertainty.py` and
 * `packages/rust/src/uncertainty.rs`.
 *
 * Zeros are ignored (never `0·ln 0`), both key conventions (`"0".."K−1"` and `"1".."K"`) read the
 * same, `K < 2` has no shape to report, and `confidence` stays the primary measure. Nothing here
 * changes a gate verdict: `skipLLM` and the exit codes are untouched.
 */
export const LOW_CONFIDENCE_THRESHOLD = 0.65;

export const UNCERTAINTY_KEYS = [
  "margin",
  "normalized_entropy",
  "confidence",
  "escalate_to_system2",
  "escalation_reason",
] as const;

export interface UncertaintyShape {
  margin: number | null;
  normalized_entropy: number | null;
  levels: number | null;
}

export function normalizeLevelKeys(probabilities: Record<string, unknown>): Map<number, number> {
  const keys = Object.keys(probabilities);
  const numeric = keys.map((key) => Number(key)).filter((value) => Number.isInteger(value));
  const zeroBased = numeric.length > 0 && Math.min(...numeric) === 0;
  const normalized = new Map<number, number>();
  // Non-numeric keys are appended after the numeric space, in the order they appear: the same rule
  // in Python, TypeScript and Rust, so the three runtimes agree on `levels` and `margin`.
  let nextFree = numeric.length > 0 ? Math.max(...numeric) + (zeroBased ? 1 : 0) + 1 : 1;
  for (const key of keys) {
    const value = Number(probabilities[key]);
    if (!Number.isFinite(value)) continue;
    const numericKey = Number.isInteger(Number(key));
    const index = numericKey ? Number(key) + (zeroBased ? 1 : 0) : nextFree++;
    if (!normalized.has(index)) normalized.set(index, value);
  }
  return normalized;
}

export function distributionShape(probabilities?: Record<string, number> | null): UncertaintyShape {
  if (!probabilities || Object.keys(probabilities).length === 0) {
    return { margin: null, normalized_entropy: null, levels: null };
  }
  const normalized = normalizeLevelKeys(probabilities);
  const positive = [...normalized.values()].filter((weight) => weight > 0);
  const k = positive.length;
  if (k < 2) return { margin: null, normalized_entropy: null, levels: k || null };
  const total = positive.reduce((sum, weight) => sum + weight, 0);
  if (total <= 0) return { margin: null, normalized_entropy: null, levels: k };
  const shares = positive.map((weight) => weight / total).sort((a, b) => b - a);
  const margin = shares[0] - shares[1];
  const entropy = -shares.filter((share) => share > 0).reduce((sum, share) => sum + share * Math.log(share), 0);
  return {
    margin: Number(margin.toFixed(9)),
    normalized_entropy: Number((entropy / Math.log(k)).toFixed(9)),
    levels: k,
  };
}

export interface Uncertainty {
  margin: number | null;
  normalized_entropy: number | null;
  confidence: number | null;
  escalate_to_system2: boolean;
  escalation_reason: string;
}

export function buildUncertainty(
  probabilities?: Record<string, number> | null,
  confidence?: number | null,
  category = "",
  threshold = LOW_CONFIDENCE_THRESHOLD
): Uncertainty {
  const shape = distributionShape(probabilities);
  const clean = typeof confidence === "number" && Number.isFinite(confidence) ? Number(confidence.toFixed(9)) : null;
  let escalate = false;
  let reason = "";
  if (category === "no_failure") {
    reason = "a passing run is never escalated";
  } else if (category === "deep_logic") {
    escalate = true;
    reason = "category is deep_logic: a reasoning model is the natural next step";
  } else if (clean !== null && clean < threshold) {
    escalate = true;
    reason = `confidence ${clean.toFixed(2)} is below the ${threshold.toFixed(2)} threshold`;
  }
  return {
    margin: shape.margin,
    normalized_entropy: shape.normalized_entropy,
    confidence: clean,
    escalate_to_system2: escalate,
    escalation_reason: reason,
  };
}

export function validateQuestionOptions(options: unknown[]): void {
  if (options.length < 2) {
    throw new Error(
      "a Choice/Score question needs at least two options: with a single option there is no " +
        "distribution to measure (and the provider's own confidence is undefined)"
    );
  }
}
