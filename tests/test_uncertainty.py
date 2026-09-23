"""E3.1 — uncertainty with guards: the shape metrics and the escalation precedence.

The edge cases are the point: zeros in a live distribution, a uniform one, a bimodal one (two
equal peaks ⇒ zero margin), a single level (no shape at all) and an empty map. The escalation
rules are asserted separately, including the one that must never fire: a green run.
"""
import json
import math
import sys
import unittest
from pathlib import Path

_PKG_ROOT = str(Path(__file__).resolve().parents[1] / "src")
if _PKG_ROOT not in sys.path:
    sys.path.insert(0, _PKG_ROOT)

from jev_harness.client import ChoiceQuestion, JevClient, ScoreQuestion
from jev_harness.gates import triage_test_failure, verify_step_completion
from jev_harness.uncertainty import (
    LOW_CONFIDENCE_THRESHOLD,
    UNCERTAINTY_KEYS,
    build_uncertainty,
    distribution_shape,
    normalize_level_keys,
    uncertainty_from_answer,
    validate_question_options,
)

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "uncertainty_golden.json"


class TestGoldenVectors(unittest.TestCase):
    """The same fixture is read by `packages/ts/tests/uncertainty.test.ts` and the Rust test."""

    def setUp(self):
        self.fx = json.loads(FIXTURE.read_text(encoding="utf-8"))

    def test_shape_metrics_match_the_golden_vectors(self):
        for name, vector in self.fx["vectors"].items():
            with self.subTest(name):
                shape = distribution_shape(vector["probabilities"])
                self.assertEqual(shape["levels"], vector["shape"]["levels"])
                for key in ("margin", "normalized_entropy"):
                    if vector["shape"][key] is None:
                        self.assertIsNone(shape[key])
                    else:
                        self.assertAlmostEqual(shape[key], vector["shape"][key], places=8)

    def test_uniform_has_maximum_entropy_and_no_margin(self):
        shape = distribution_shape({"1": 0.25, "2": 0.25, "3": 0.25, "4": 0.25})
        self.assertEqual(shape["margin"], 0.0)
        self.assertAlmostEqual(shape["normalized_entropy"], 1.0, places=9)

    def test_bimodal_has_no_margin_but_less_entropy_than_uniform(self):
        shape = distribution_shape({"1": 0.45, "2": 0.45, "3": 0.05, "4": 0.05})
        self.assertEqual(shape["margin"], 0.0)
        self.assertLess(shape["normalized_entropy"], 1.0)

    def test_zeros_are_ignored_not_divided_by(self):
        shape = distribution_shape({"0": 0.7, "1": 0.3, "2": 0.0})
        self.assertEqual(shape["levels"], 2, "a zero-probability level is not a level")
        self.assertAlmostEqual(shape["margin"], 0.4, places=9)
        self.assertTrue(math.isfinite(shape["normalized_entropy"]))

    def test_single_level_and_empty_have_no_shape(self):
        self.assertIsNone(distribution_shape({"1": 1.0})["normalized_entropy"])
        self.assertIsNone(distribution_shape({})["margin"])
        self.assertIsNone(distribution_shape(None)["normalized_entropy"])

    def test_both_key_conventions_read_the_same(self):
        zero_based = normalize_level_keys({"0": 0.85, "1": 0.0375, "2": 0.0375, "3": 0.0375, "4": 0.0375})
        one_based = normalize_level_keys({"1": 0.85, "2": 0.0375, "3": 0.0375, "4": 0.0375, "5": 0.0375})
        self.assertEqual(sorted(zero_based), sorted(one_based))
        self.assertAlmostEqual(distribution_shape(zero_based)["margin"], distribution_shape(one_based)["margin"], places=12)

    def test_non_finite_and_text_values_are_dropped(self):
        shape = distribution_shape({"1": 0.5, "2": float("nan"), "3": "n/a", "4": 0.5})
        self.assertAlmostEqual(shape["margin"], 0.0, places=9)


class TestEscalationPrecedence(unittest.TestCase):
    def test_contract_keys(self):
        result = build_uncertainty({"1": 0.9, "2": 0.1}, 0.9, category="deep_logic")
        self.assertEqual(tuple(result.keys()), UNCERTAINTY_KEYS)

    def test_green_is_never_escalated(self):
        result = build_uncertainty({"1": 0.9, "2": 0.1}, 0.2, category="no_failure")
        self.assertFalse(result["escalate_to_system2"], "a passing run is never escalated")
        self.assertIn("passing run", result["escalation_reason"])

    def test_deep_logic_escalates_naturally(self):
        self.assertTrue(build_uncertainty({"1": 0.9, "2": 0.1}, 0.9, category="deep_logic")["escalate_to_system2"])

    def test_low_confidence_escalates_even_for_deterministic_categories(self):
        result = build_uncertainty({"1": 0.6, "2": 0.4}, 0.4, category="env_missing")
        self.assertTrue(result["escalate_to_system2"])
        self.assertIn("below", result["escalation_reason"])

    def test_a_confident_deterministic_decision_is_not_escalated(self):
        for category in ("env_missing", "flaky_transient", "syntax_trivial"):
            with self.subTest(category):
                result = build_uncertainty({"1": 0.9, "2": 0.1}, 0.9, category=category)
                self.assertFalse(result["escalate_to_system2"])

    def test_threshold_is_the_documented_line(self):
        self.assertEqual(LOW_CONFIDENCE_THRESHOLD, 0.65)
        self.assertTrue(build_uncertainty(None, 0.64, category="route")["escalate_to_system2"])
        self.assertFalse(build_uncertainty(None, 0.66, category="route")["escalate_to_system2"])

    def test_noul_answers_have_no_shape(self):
        class Noul:
            noul = 0.9

        result = uncertainty_from_answer(Noul(), category="deep_logic")
        self.assertIsNone(result["margin"])
        self.assertIsNone(result["normalized_entropy"])


class TestGatesEmitUncertainty(unittest.TestCase):
    def test_triage_exposes_the_envelope_without_changing_the_verdict(self):
        client = JevClient(force_mock=True)
        result = triage_test_failure("AssertionError: assert 4 == 5", client=client)
        self.assertEqual(result.category, "deep_logic")
        self.assertFalse(result.skip_llm, "the uncertainty envelope never changes skip_llm")
        self.assertEqual(tuple(result.uncertainty.keys()), UNCERTAINTY_KEYS)
        self.assertTrue(result.uncertainty["escalate_to_system2"])
        self.assertIsNotNone(result.uncertainty["margin"])

    def test_a_deterministic_triage_is_not_escalated(self):
        client = JevClient(force_mock=True)
        result = triage_test_failure("ModuleNotFoundError: No module named 'requests'", client=client)
        self.assertTrue(result.skip_llm)
        self.assertFalse(result.uncertainty["escalate_to_system2"])

    def test_verify_uses_its_score_answer_for_the_shape(self):
        client = JevClient(force_mock=True)
        result = verify_step_completion("tests pass", "Ran 24 tests ... OK", client=client)
        self.assertIsNotNone(result.uncertainty)
        self.assertEqual(set(result.uncertainty), set(UNCERTAINTY_KEYS))


class TestQuestionPreconditions(unittest.TestCase):
    def test_a_single_option_question_is_rejected_with_a_clear_error(self):
        with self.assertRaises(ValueError) as ctx:
            ChoiceQuestion(instructions="x", criteria={"only": "one"})
        self.assertIn("at least two options", str(ctx.exception))

        with self.assertRaises(ValueError):
            ScoreQuestion(instructions="x", criteria=["only"])

    def test_two_options_are_accepted(self):
        self.assertIsNotNone(ChoiceQuestion(instructions="x", criteria={"a": "b", "c": "d"}))
        self.assertIsNotNone(ScoreQuestion(instructions="x", criteria=["low", "high"]))

    def test_validator_is_reusable(self):
        with self.assertRaises(ValueError):
            validate_question_options(["single"])


if __name__ == "__main__":
    unittest.main()
