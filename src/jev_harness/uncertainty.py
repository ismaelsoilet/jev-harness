"""
E3.1 — uncertainty with guards, derived from the provider's real distributions.

The provider returns a full distribution for `Choice` and `Score` answers and derives its
`confidence` from it. Two mistakes are easy to make and are prevented here:

* **using a broken distribution.** Live payloads contain zeros (so `0·ln 0` must be skipped),
  may arrive with either key convention (`"0".."K−1"` or `"1".."K"`), and a single-option question
  has no meaningful entropy at all (`K < 2` is rejected when the question is created).
* **treating three derived signals as independent.** `confidence` is derived from the same
  distribution, so it is the **primary** measure; `margin` and `normalized_entropy` are secondary
  shape measures. `Noul` answers carry no distribution and therefore no shape measure.

Nothing here changes a gate's verdict: `skip_llm` and the exit codes stay exactly as they were.
"""
from __future__ import annotations

import math
from typing import Any, Dict, Mapping, Optional, Sequence

# Below this confidence (the same line the triage gate uses to decide alone) the decision is not
# trustworthy enough to act on without a reasoning model.
LOW_CONFIDENCE_THRESHOLD = 0.65

UNCERTAINTY_KEYS = ("margin", "normalized_entropy", "confidence", "escalate_to_system2", "escalation_reason")


def normalize_level_keys(probabilities: Mapping[Any, float]) -> Dict[int, float]:
    """Maps both key conventions to a 1-based level index.

    `Score` answers in the wild use `"1".."K"` (the mock and the recorded fixture) while some
    `Choice` payloads use `"0".."K−1"`; the same distribution must read the same way in both.
    """
    keys = list(probabilities.keys())
    numeric = [int(key) for key in keys if str(key).lstrip("-").isdigit()]
    zero_based = bool(numeric) and min(numeric) == 0
    # Non-numeric keys are appended after the numeric space, in the order they appear: the same
    # rule in Python, TypeScript and Rust, so the three runtimes agree on `levels`/`margin`.
    next_free = (max(numeric) + (1 if zero_based else 0) + 1) if numeric else 1
    normalized: Dict[int, float] = {}
    for key, value in probabilities.items():
        try:
            weight = float(value)
        except (TypeError, ValueError):
            continue
        if not math.isfinite(weight):
            continue
        if str(key).lstrip("-").isdigit():
            index = int(key) + (1 if zero_based else 0)
        else:
            index = next_free
            next_free += 1
        if index in normalized:
            continue
        normalized[index] = weight
    return normalized


def distribution_shape(probabilities: Optional[Mapping[Any, float]]) -> Dict[str, Optional[float]]:
    """`margin` (peak minus runner-up) and `normalized_entropy` (H / ln K), or Nones.

    Guards: values that are not finite are dropped; non-positive probabilities are ignored by the
    entropy (a zero probability contributes nothing but `ln 0` would blow up); `K < 2` has no
    shape to report; if the remaining mass is degenerate the result is reported as 0.0 rather than
    silently invented.
    """
    if not probabilities:
        return {"margin": None, "normalized_entropy": None, "levels": None}
    normalized = normalize_level_keys(probabilities)
    positive = {index: weight for index, weight in normalized.items() if weight > 0}
    k = len(positive)
    if k < 2:
        return {"margin": None, "normalized_entropy": None, "levels": k or None}

    total = sum(positive.values())
    if total <= 0:
        return {"margin": None, "normalized_entropy": None, "levels": k}
    shares = sorted((weight / total for weight in positive.values()), reverse=True)
    margin = shares[0] - shares[1]
    entropy = -sum(share * math.log(share) for share in shares if share > 0)
    normalized_entropy = entropy / math.log(k) if k > 1 else 0.0
    return {
        "margin": round(margin, 9),
        "normalized_entropy": round(normalized_entropy, 9),
        "levels": k,
    }


def build_uncertainty(
    probabilities: Optional[Mapping[Any, float]] = None,
    confidence: Optional[float] = None,
    category: str = "",
    threshold: float = LOW_CONFIDENCE_THRESHOLD,
) -> Dict[str, Any]:
    """The additive `uncertainty` contract for one answer.

    Precedence (documented, and never overriding the gate's own verdict):
    * `no_failure` is neutral: a green run is never escalated;
    * `env_missing` / `flaky_transient` keep their deterministic path (`skip_llm=true`) and are
      escalated only when the confidence itself is low;
    * `deep_logic` escalates naturally (it is already an escalation);
    * a low confidence escalates regardless of the category, except for `no_failure`.
    """
    shape = distribution_shape(probabilities)
    clean_confidence = None
    if isinstance(confidence, (int, float)) and math.isfinite(float(confidence)):
        clean_confidence = round(float(confidence), 9)

    escalate = False
    reason = ""
    if category != "no_failure":
        if category == "deep_logic":
            escalate = True
            reason = "category is deep_logic: a reasoning model is the natural next step"
        elif clean_confidence is not None and clean_confidence < threshold:
            escalate = True
            reason = f"confidence {clean_confidence:.2f} is below the {threshold:.2f} threshold"
    if category == "no_failure":
        reason = "a passing run is never escalated"

    return {
        "margin": shape["margin"],
        "normalized_entropy": shape["normalized_entropy"],
        "confidence": clean_confidence,
        "escalate_to_system2": escalate,
        "escalation_reason": reason,
    }


def uncertainty_from_answer(
    answer: Any,
    category: str = "",
    threshold: float = LOW_CONFIDENCE_THRESHOLD,
) -> Dict[str, Any]:
    """Convenience wrapper for a `Choice`/`Score`/`Noul` answer object from the client."""
    probabilities = getattr(answer, "probabilities", None)
    confidence = getattr(answer, "confidence", None)
    if isinstance(answer, dict):  # serialized answers
        probabilities = answer.get("probabilities")
        confidence = answer.get("confidence")
    return build_uncertainty(probabilities, confidence, category=category, threshold=threshold)


def validate_question_options(options: Sequence[Any]) -> None:
    """`K >= 2` is a precondition: a one-option question has no distribution to measure.

    Raises ValueError with an actionable message (the caller built an unusable question).
    """
    if len(list(options)) < 2:
        raise ValueError(
            "a Choice/Score question needs at least two options: with a single option there is no "
            "distribution to measure (and the provider's own confidence is undefined)"
        )
