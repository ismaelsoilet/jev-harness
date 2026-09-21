"""
Tests for JevClient, questions serialization, and offline simulation engine.
"""

import json
from pathlib import Path
import sys
import unittest
from unittest.mock import MagicMock, patch

_PKG_ROOT = str(Path(__file__).resolve().parents[1] / "src")
if _PKG_ROOT not in sys.path:
    sys.path.insert(0, _PKG_ROOT)

from jev_harness.client import (
    ChoiceAnswer,
    ChoiceQuestion,
    JevClient,
    JevResponse,
    NoulAnswer,
    NoulQuestion,
    ScoreAnswer,
    ScoreQuestion,
)


class TestJevClient(unittest.TestCase):
    def test_choice_question_to_dict(self):
        q = ChoiceQuestion(
            instructions="Pick category",
            criteria={"bug": "code bug", "env": "environment issue"},
        )
        data = q.to_dict()
        self.assertEqual(data["type"], "choice")
        self.assertEqual(data["instructions"], "Pick category")
        self.assertIn("bug", data["criteria"])

    def test_score_question_validation(self):
        with self.assertRaises(ValueError):
            ScoreQuestion(instructions="Invalid", criteria=["only_one"])

        valid = ScoreQuestion(instructions="Valid", criteria=["low", "high"])
        self.assertEqual(valid.to_dict()["type"], "score")
        self.assertEqual(len(valid.to_dict()["criteria"]), 2)

    def test_noul_question_to_dict(self):
        q = NoulQuestion(instructions="Is this urgent?")
        self.assertEqual(q.to_dict()["type"], "noul")

    def test_offline_simulation_choice(self):
        client = JevClient(force_mock=True)
        resp = client.system_one(
            state="ModuleNotFoundError: No module named 'numpy'",
            questions={
                "category": ChoiceQuestion(
                    instructions="Category",
                    criteria={
                        "env_missing": "Missing module",
                        "deep_logic": "Logic bug",
                    },
                )
            },
        )
        self.assertTrue(resp.is_mock)
        ans = resp.answers["category"]
        self.assertIsInstance(ans, ChoiceAnswer)
        self.assertEqual(ans.choice, "env_missing")
        self.assertGreater(ans.confidence, 0.7)

    def test_offline_simulation_score(self):
        client = JevClient(force_mock=True)
        resp = client.system_one(
            state="All 10 tests passed and completed successfully with excellent output.",
            questions={
                "satisfaction": ScoreQuestion(
                    instructions="Rate satisfaction",
                    criteria=["poor", "acceptable", "good", "excellent"],
                )
            },
        )
        ans = resp.answers["satisfaction"]
        self.assertIsInstance(ans, ScoreAnswer)
        self.assertEqual(ans.score, 4.0)

    def test_offline_simulation_noul(self):
        client = JevClient(force_mock=True)
        resp = client.system_one(
            state="Fatal error: circular dependency deadlock impossible to resolve",
            questions={"abort": NoulQuestion(instructions="Should we abort?")},
        )
        ans = resp.answers["abort"]
        self.assertIsInstance(ans, NoulAnswer)
        self.assertGreater(ans.noul, 0.70)


if __name__ == "__main__":
    unittest.main()
