"""E3.9 — golden vectors for the offline mock, shared by the three runtimes.

Same fixture as `packages/ts/tests/mock_golden.test.ts` and
`packages/rust/tests/mock_golden_test.rs`: if the mock probabilities drift in one runtime, these
tests disagree and the divergence is caught instead of shipping a false parity claim.
"""
import json
import math
import unittest
from pathlib import Path

from jev_harness.client import (
    MOCK_CHOICE_BEST_CONFLICT,
    MOCK_CHOICE_BEST_PEAKED,
    MOCK_SCORE_BEST_PEAKED,
    ChoiceQuestion,
    JevClient,
    NoulQuestion,
    ScoreQuestion,
)

FIXTURE = Path(__file__).parent / "fixtures" / "mock_golden.json"


class TestMockGoldenVectors(unittest.TestCase):
    def setUp(self):
        self.client = JevClient(force_mock=True)
        self.fx = json.loads(FIXTURE.read_text(encoding="utf-8"))
        self.criteria = self.fx["choice_criteria"]

    def _choice(self, state):
        question = ChoiceQuestion(
            instructions="What is the root failure type in this error trace?", criteria=self.criteria
        )
        return self.client.system_one(state, {"category": question}).answers["category"]

    def test_constants_match_the_contract(self):
        self.assertAlmostEqual(MOCK_CHOICE_BEST_PEAKED, 0.85)
        self.assertAlmostEqual(MOCK_CHOICE_BEST_CONFLICT, 0.55)
        self.assertAlmostEqual(MOCK_SCORE_BEST_PEAKED, 0.80)

    def test_peaked_choice_distribution(self):
        expected = self.fx["peaked"]["expected"]
        answer = self._choice(self.fx["peaked"]["state"])
        self.assertEqual(answer.choice, expected["choice"])
        self.assertEqual(set(answer.probabilities), set(expected["probabilities"]))
        for key, value in expected["probabilities"].items():
            self.assertAlmostEqual(answer.probabilities[key], value, places=12)

    def test_conflicting_signals_lower_the_peak(self):
        expected = self.fx["conflict"]["expected"]
        answer = self._choice(self.fx["conflict"]["state"])
        self.assertEqual(answer.choice, expected["choice"])
        for key, value in expected["probabilities"].items():
            self.assertAlmostEqual(answer.probabilities[key], value, places=12)
        peak = answer.probabilities[answer.choice]
        self.assertAlmostEqual(peak, MOCK_CHOICE_BEST_CONFLICT, places=12)
        self.assertLess(peak, MOCK_CHOICE_BEST_PEAKED)

    def test_distributions_sum_to_one(self):
        for name in ("peaked", "conflict"):
            with self.subTest(name):
                answer = self._choice(self.fx[name]["state"])
                self.assertAlmostEqual(sum(answer.probabilities.values()), 1.0, places=9)

    def test_score_distribution_is_exposed(self):
        expected = self.fx["score"]["expected"]
        question = ScoreQuestion(instructions="How severe is this failure?", criteria=self.fx["score"]["levels"])
        answer = self.client.system_one(self.fx["score"]["state"], {"severity": question}).answers["severity"]
        self.assertAlmostEqual(answer.score, expected["score"], places=9)
        for key, value in expected["probabilities"].items():
            self.assertAlmostEqual(answer.probabilities[key], value, places=12)
        self.assertAlmostEqual(sum(answer.probabilities.values()), 1.0, places=9)

    def test_noul_stays_a_scalar(self):
        expected = self.fx["noul"]["expected"]
        question = NoulQuestion(self.fx["noul"]["instruction"])
        answer = self.client.system_one(self.fx["noul"]["state"], {"skip_llm": question}).answers["skip_llm"]
        self.assertAlmostEqual(answer.noul, expected["noul"], places=9)
        self.assertFalse(hasattr(answer, "probabilities"), "Noul has no distribution by contract")

    def test_conflict_peak_is_below_the_peaked_case(self):
        """A caller can therefore exercise escalation deterministically in CI."""
        peaked = self._choice(self.fx["peaked"]["state"]).probabilities
        conflict = self._choice(self.fx["conflict"]["state"]).probabilities
        n = len(peaked)
        peaked_margin = max(peaked.values()) - min(peaked.values())
        conflict_margin = max(conflict.values()) - min(conflict.values())
        self.assertAlmostEqual(peaked_margin, MOCK_CHOICE_BEST_PEAKED - (1 - MOCK_CHOICE_BEST_PEAKED) / (n - 1), places=9)
        self.assertAlmostEqual(
            conflict_margin, MOCK_CHOICE_BEST_CONFLICT - (1 - MOCK_CHOICE_BEST_CONFLICT) / (n - 1), places=9
        )
        self.assertLess(conflict_margin, peaked_margin)
        self.assertTrue(all(math.isfinite(v) for v in conflict.values()))


if __name__ == "__main__":
    unittest.main()
