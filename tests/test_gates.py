"""
Tests for semantic gates: test triage, abort check, model routing, verification.
"""

from pathlib import Path
import sys
import unittest

_PKG_ROOT = str(Path(__file__).resolve().parents[1] / "src")
if _PKG_ROOT not in sys.path:
    sys.path.insert(0, _PKG_ROOT)

from jev_harness.client import JevClient
from jev_harness.gates import (
    AbortGateResult,
    ModelRouteResult,
    TestTriageResult,
    VerificationResult,
    route_model_tier,
    should_abort_trajectory,
    triage_test_failure,
    verify_step_completion,
)


class TestSemanticGates(unittest.TestCase):
    def setUp(self):
        self.client = JevClient(force_mock=True)

    def test_triage_env_missing(self):
        err = "ModuleNotFoundError: No module named 'pytest'"
        res = triage_test_failure(err, client=self.client)
        self.assertIsInstance(res, TestTriageResult)
        self.assertEqual(res.category, "env_missing")
        self.assertTrue(res.skip_llm)
        self.assertIn("AUTO-ACTION", res.action_recommendation)

    def test_triage_transient_flaky(self):
        err = "ConnectionResetError: [Errno 104] Connection reset by peer with timeout"
        res = triage_test_failure(err, client=self.client)
        self.assertEqual(res.category, "flaky_transient")
        self.assertTrue(res.skip_llm)

    def test_abort_check_circular_loop(self):
        step = "Tentar pela 4a vez reescrever sem teste"
        hist = "Tentativa 1 falhou com timeout. Tentativa 2 falhou com erro fatal circular."
        res = should_abort_trajectory(step, recent_attempts_summary=hist, client=self.client)
        self.assertIsInstance(res, AbortGateResult)
        self.assertTrue(res.should_abort)
        self.assertGreaterEqual(res.abort_probability, 0.70)

    def test_abort_check_safe_plan(self):
        step = "Executar git status para verificar arquivos alterados"
        hist = "Compilacao passou perfeitamente."
        res = should_abort_trajectory(step, recent_attempts_summary=hist, client=self.client)
        self.assertFalse(res.should_abort)

    def test_route_model_tier_deterministic(self):
        task = "Corrigir typo e formatar codigo com black"
        res = route_model_tier(task, client=self.client)
        self.assertIsInstance(res, ModelRouteResult)
        self.assertEqual(res.selected_tier, "deterministic")
        self.assertIn("0 LLM Tokens", res.recommended_model)

    def test_verify_step_completion(self):
        criteria = "Deve passar todos os 10 testes unitarios sem warnings"
        output = "10 tests passed and completed successfully with 100% pass rate"
        res = verify_step_completion(criteria, output, client=self.client)
        self.assertIsInstance(res, VerificationResult)
        self.assertTrue(res.is_verified)
        self.assertFalse(res.needs_rework)


if __name__ == "__main__":
    unittest.main()
