"""E0.1 - recorded live System One payload parity (Score answers must parse).

Regression for v0.1.14: the Rust runtime dropped Score answers in live mode
(float score / map legend). Python and TypeScript already handled them; this
test pins the shared fixture used by all three runtimes.
"""
import json
import unittest
from pathlib import Path

from jev_harness.client import JevClient


FIXTURE = Path(__file__).parent / "fixtures" / "systemone_live_score.json"


class TestLivePayloadParity(unittest.TestCase):
    def test_score_payload_parses_score_probabilities_and_map_legend(self):
        data = json.loads(FIXTURE.read_text(encoding="utf-8"))
        resp = JevClient(force_mock=True)._parse_response(data, "jev-test", is_mock=False)
        severity = resp.answers["severity"]
        self.assertAlmostEqual(severity.score, 1.76, places=9)
        self.assertAlmostEqual(severity.probabilities["1"], 0.44, places=9)
        self.assertIsInstance(severity.legend, dict)
        viability = resp.answers["viability"]
        self.assertAlmostEqual(viability.score, 2.11, places=9)
        category = resp.answers["category"]
        self.assertEqual(category.choice, "env_missing")
        self.assertAlmostEqual(category.confidence, 0.98, places=9)

    def test_integer_scores_and_list_legends_still_parse(self):
        data = {
            "model": "x",
            "answers": {"severity": {"type": "score", "score": 2, "confidence": 0.9, "legend": ["a", "b"]}},
        }
        resp = JevClient(force_mock=True)._parse_response(data, "x", is_mock=False)
        self.assertAlmostEqual(resp.answers["severity"].score, 2.0, places=9)
        self.assertIsInstance(resp.answers["severity"].legend, list)


if __name__ == "__main__":
    unittest.main()
