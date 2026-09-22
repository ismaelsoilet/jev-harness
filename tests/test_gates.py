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
    ReasoningEffortResult,
    TestTriageResult,
    VerificationResult,
    modulate_reasoning_effort,
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

    def test_route_model_tier_heavy_reasoning(self):
        task = "Refactor distributed actor supervision kernel and solve multi-file deadlock architecture"
        res = route_model_tier(task, client=self.client)
        self.assertIsInstance(res, ModelRouteResult)
        self.assertEqual(res.selected_tier, "heavy_system2")
        self.assertIn("Claude Fable 5.1 / GPT-6 Astra", res.recommended_model)

    def test_verify_step_completion(self):
        criteria = "Deve passar todos os 10 testes unitarios sem warnings"
        output = "10 tests passed and completed successfully with 100% pass rate"
        res = verify_step_completion(criteria, output, client=self.client)
        self.assertIsInstance(res, VerificationResult)
        self.assertTrue(res.is_verified)
        self.assertFalse(res.needs_rework)

    def test_modulate_reasoning_effort_mechanical(self):
        ctx = "git status e verificar arquivos modificados"
        res = modulate_reasoning_effort(ctx, provider="openai", client=self.client)
        self.assertIsInstance(res, ReasoningEffortResult)
        self.assertEqual(res.effort, "low")
        self.assertTrue(res.is_reasoning_supported)
        self.assertEqual(res.provider_params, {"reasoning_effort": "low"})

    def test_modulate_reasoning_effort_heavy(self):
        ctx = "Diagnosticar deadlock distribuído e race conditions entre threads no kernel"
        res = modulate_reasoning_effort(ctx, provider="openai", client=self.client)
        self.assertIsInstance(res, ReasoningEffortResult)
        self.assertEqual(res.effort, "high")
        self.assertEqual(res.provider_params, {"reasoning_effort": "high"})

    def test_modulate_reasoning_effort_deepseek_dialects(self):
        ctx_low = "executar flake8 e linter no codigo"
        res_low = modulate_reasoning_effort(ctx_low, provider="deepseek", client=self.client)
        self.assertEqual(res_low.effort, "low")
        self.assertEqual(res_low.provider_params["reasoning_effort"], "low")
        self.assertIn("extra_body", res_low.provider_params)

        ctx_high = "Refactor distributed consensus supervision tree architecture"
        res_high = modulate_reasoning_effort(ctx_high, provider="deepseek", client=self.client)
        self.assertEqual(res_high.effort, "high")
        self.assertEqual(res_high.provider_params["reasoning_effort"], "high")

    def test_modulate_reasoning_effort_qwen_dialects(self):
        ctx_low = "cat package.json"
        res_low = modulate_reasoning_effort(ctx_low, provider="qwen", client=self.client)
        self.assertEqual(res_low.effort, "low")
        self.assertEqual(res_low.provider_params, {"enable_thinking": False})

    def test_direct_model_safeguard(self):
        ctx = "cat package.json"
        res = modulate_reasoning_effort(ctx, provider="openai", model="gpt-5.6-luna", client=self.client)
        self.assertFalse(res.is_reasoning_supported)
        self.assertEqual(res.provider_params, {})
        self.assertIn("direct single-pass model", res.rationale)


if __name__ == "__main__":
    unittest.main()
