"""E1.4 — measured cost/tokens per decision, kept apart from the heuristic savings model.

"Estimated" answers a planning question ("what would this have cost?"); "measured" answers an
accounting one ("what did the provider report for the decisions that actually used the network?").
Both are exposed, clearly labelled, and mock answers never touch the measured counters.
"""
import io
import json
import os
import sys
import tempfile
import unittest
import urllib.error
from pathlib import Path
from unittest.mock import patch

_PKG_ROOT = str(Path(__file__).resolve().parents[1] / "src")
if _PKG_ROOT not in sys.path:
    sys.path.insert(0, _PKG_ROOT)

import jev_harness.client as client_mod
from jev_harness.client import _parse_cost, JevClient, NoulQuestion
from jev_harness.session import load_session

LIVE_PAYLOAD = {
    "model": "jev-1.13.0",
    "answers": {"q": {"type": "noul", "noul": 0.9}},
    "usage": {"input_tokens": 518, "output_tokens": 69},
    "cost": "0.0000218",  # the provider sends cost as a string
}


class _FakeResponse:
    def __init__(self, payload):
        self._body = json.dumps(payload).encode("utf-8")

    def read(self):
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


class TestCostParsing(unittest.TestCase):
    def test_accepts_numbers_and_numeric_strings(self):
        self.assertAlmostEqual(_parse_cost("0.0000218"), 0.0000218)
        self.assertAlmostEqual(_parse_cost(0.5), 0.5)
        self.assertAlmostEqual(_parse_cost(0), 0.0)

    def test_rejects_nonsense_without_raising(self):
        for value in (None, "", "free", True, [], {"a": 1}, -1, float("nan"), float("inf")):
            with self.subTest(repr(value)):
                self.assertEqual(_parse_cost(value), 0.0)


class TestMeasuredUsage(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self._env = patch.dict(os.environ, {"HOME": self._tmp.name, "USERPROFILE": self._tmp.name})
        self._env.start()
        self.addCleanup(self._env.stop)

    def _live_client(self):
        return JevClient(provider="typesafe", api_key="test-key", retry_base_delay=0.0)

    def test_a_live_decision_records_what_the_provider_reported(self):
        client = self._live_client()
        with patch.object(client_mod, "_urlopen_with_ipv4_fallback", lambda req, timeout: _FakeResponse(LIVE_PAYLOAD)):
            resp = client.system_one("state", {"q": NoulQuestion("x")})
        self.assertFalse(resp.is_mock)
        self.assertAlmostEqual(resp.cost_usd, 0.0000218, places=12)

        session = load_session()
        self.assertEqual(session.measured_requests, 1)
        self.assertEqual(session.measured_input_tokens, 518)
        self.assertEqual(session.measured_output_tokens, 69)
        self.assertAlmostEqual(session.measured_cost_usd, 0.0000218, places=12)

    def test_several_decisions_accumulate(self):
        client = self._live_client()
        for _ in range(3):
            with patch.object(client_mod, "_urlopen_with_ipv4_fallback", lambda req, timeout: _FakeResponse(LIVE_PAYLOAD)):
                client.system_one("state", {"q": NoulQuestion("x")})
        session = load_session()
        self.assertEqual(session.measured_requests, 3)
        self.assertEqual(session.measured_input_tokens, 518 * 3)
        self.assertAlmostEqual(session.measured_cost_usd, 0.0000218 * 3, places=9)

    def test_mock_decisions_never_touch_the_measured_counters(self):
        client = JevClient(force_mock=True)
        client.system_one("ModuleNotFoundError: No module named 'x'", {"q": NoulQuestion("x")})
        session = load_session()
        self.assertEqual(session.measured_requests, 0)
        self.assertEqual(session.measured_cost_usd, 0.0)

    def test_a_degraded_fallback_is_not_a_measurement(self):
        client = self._live_client()
        with patch.object(client_mod, "_urlopen_with_ipv4_fallback", side_effect=urllib.error.URLError("down")):
            resp = client.system_one("state", {"q": NoulQuestion("x")})
        self.assertTrue(resp.is_mock)
        self.assertEqual(load_session().measured_requests, 0)

    def test_measurement_can_be_disabled(self):
        client = JevClient(provider="typesafe", api_key="k", retry_base_delay=0.0, measure_usage=False)
        with patch.object(client_mod, "_urlopen_with_ipv4_fallback", lambda req, timeout: _FakeResponse(LIVE_PAYLOAD)):
            client.system_one("state", {"q": NoulQuestion("x")})
        self.assertEqual(load_session().measured_requests, 0)

    def test_telemetry_failure_never_breaks_a_decision(self):
        client = self._live_client()
        with patch.object(client_mod, "_urlopen_with_ipv4_fallback", lambda req, timeout: _FakeResponse(LIVE_PAYLOAD)):
            with patch("jev_harness.session.record_measured_usage", side_effect=OSError("disk full")):
                resp = client.system_one("state", {"q": NoulQuestion("x")})
        self.assertFalse(resp.is_mock)  # the decision still came back

    def test_metrics_command_exposes_measured_and_estimated_separately(self):
        import jev_harness.cli as cli

        client = self._live_client()
        with patch.object(client_mod, "_urlopen_with_ipv4_fallback", lambda req, timeout: _FakeResponse(LIVE_PAYLOAD)):
            client.system_one("state", {"q": NoulQuestion("x")})

        out = io.StringIO()
        with patch.object(sys, "argv", ["jev-harness", "metrics", "--json"]):
            with patch("sys.stdout", out):
                with self.assertRaises(SystemExit) as cm:
                    cli.main()
        self.assertEqual(cm.exception.code, 0)
        payload = json.loads(out.getvalue())
        self.assertTrue(payload["estimates_are_heuristic"])
        self.assertEqual(payload["measured_input_tokens"], 518)
        self.assertAlmostEqual(payload["measured_cost_usd"], 0.0000218, places=9)
        self.assertIsNotNone(payload["measured_avg_duration_ms"])

    def test_reset_clears_measured_counters_too(self):
        import jev_harness.cli as cli

        client = self._live_client()
        with patch.object(client_mod, "_urlopen_with_ipv4_fallback", lambda req, timeout: _FakeResponse(LIVE_PAYLOAD)):
            client.system_one("state", {"q": NoulQuestion("x")})
        with patch.object(sys, "argv", ["jev-harness", "metrics", "--reset"]):
            with patch("sys.stdout", io.StringIO()):
                with self.assertRaises(SystemExit):
                    cli.main()
        session = load_session()
        self.assertEqual(session.measured_requests, 0)
        self.assertEqual(session.measured_cost_usd, 0.0)


if __name__ == "__main__":
    unittest.main()
