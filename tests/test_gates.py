"""
Tests for semantic gates: test triage, abort check, model routing, verification.
"""

from pathlib import Path
import sys
import unittest

_PKG_ROOT = str(Path(__file__).resolve().parents[1] / "src")
if _PKG_ROOT not in sys.path:
    sys.path.insert(0, _PKG_ROOT)

from jev_harness.client import COMMANDCODE_API_URL, JevClient
from jev_harness.gates import (
    AbortGateResult,
    ModelRouteResult,
    NudgeGateResult,
    ReasoningEffortResult,
    TestTriageResult,
    VerificationResult,
    modulate_reasoning_effort,
    route_model_tier,
    should_abort_trajectory,
    should_nudge_continuation,
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

    def test_astra_ares_lease_steps_and_supported_efforts(self):
        res_mech = modulate_reasoning_effort(
            "git status e listar diretório",
            provider="openai",
            supported_efforts=["low", "medium", "high", "xhigh"],
            client=self.client,
        )
        self.assertEqual(res_mech.effort, "low")
        self.assertEqual(res_mech.lease_steps, 5)

        res_err = modulate_reasoning_effort(
            "Traceback (most recent call last): AssertionError: expected 200 got 500",
            provider="openai",
            client=self.client,
        )
        self.assertEqual(res_err.lease_steps, 1)

    def test_openrouter_and_vercel_native_endpoints(self):
        or_client = JevClient(provider="openrouter", api_key="test-key")
        self.assertEqual(or_client.base_url, "https://openrouter.ai/api/alpha/decisions")
        self.assertEqual(or_client.model, "typesafe/jev-1.13")

        vc_client = JevClient(provider="vercel", api_key="test-key")
        self.assertEqual(vc_client.base_url, "https://ai-gateway.vercel.sh/v1/evaluate")
        self.assertEqual(vc_client.model, "typesafe-ai/jev")

    def test_multilingual_natural_language_pt_es(self):
        # Portuguese (PT-BR)
        res_pt_low = modulate_reasoning_effort(
            "Ler arquivo de configuração e formatar código",
            provider="openai",
            client=self.client,
        )
        self.assertEqual(res_pt_low.effort, "low")

        res_pt_high = modulate_reasoning_effort(
            "Refatorar arquitetura distribuída com concorrência e bloqueio mútuo",
            provider="openai",
            client=self.client,
        )
        self.assertEqual(res_pt_high.effort, "high")

        # Spanish (ES)
        res_es_low = modulate_reasoning_effort(
            "Leer archivo de configuración y ejecutar linter",
            provider="openai",
            client=self.client,
        )
        self.assertEqual(res_es_low.effort, "low")

        res_es_high = modulate_reasoning_effort(
            "Refactorizar arquitectura distribuida con concurrencia y interbloqueo",
            provider="openai",
            client=self.client,
        )
        self.assertEqual(res_es_high.effort, "high")

    def test_polyglot_error_tracebacks(self):
        # Java ClassNotFoundException -> env_missing + skip_llm=True
        res_java = triage_test_failure(
            "Exception in thread 'main' java.lang.ClassNotFoundException: org.postgresql.Driver",
            client=self.client,
        )
        self.assertEqual(res_java.category, "env_missing")
        self.assertTrue(res_java.skip_llm)

        # C# CS0246 missing assembly -> env_missing + skip_llm=True
        res_cs = triage_test_failure(
            "Program.cs(12,7): error CS0246: The type or namespace name 'Newtonsoft' could not be found",
            client=self.client,
        )
        self.assertEqual(res_cs.category, "env_missing")
        self.assertTrue(res_cs.skip_llm)

        # C++ AddressSanitizer -> deep_logic + skip_llm=False
        res_cpp = triage_test_failure(
            "==12345==ERROR: AddressSanitizer: heap-use-after-free on address 0x602000000010",
            client=self.client,
        )
        self.assertEqual(res_cpp.category, "deep_logic")
        self.assertFalse(res_cpp.skip_llm)

    def test_commandcode_provider_endpoint_and_model(self):
        cmd_client = JevClient(provider="commandcode", api_key="cmd_test_123")
        self.assertEqual(cmd_client.base_url, COMMANDCODE_API_URL)
        self.assertEqual(cmd_client.model, "typesafe/jev")
        self.assertTrue(cmd_client.is_live)

    def test_sureforge_nudge_gate_execute_and_verify_vs_vetoes(self):
        # 1. Unfinished implementation ('execute' phase) -> should_nudge = True
        res_exec = should_nudge_continuation(
            "Implemented step 1 of 3. Remaining TODO: update CLI parser and run tests.",
            client=self.client,
        )
        self.assertIsInstance(res_exec, NudgeGateResult)
        self.assertTrue(res_exec.should_nudge)
        self.assertEqual(res_exec.sureforge_phase, "execute")
        self.assertGreaterEqual(res_exec.nudge_probability, 0.5)

        # 2. Unverified changes ('verify' phase) -> should_nudge = True with Verify prompt
        res_ver = should_nudge_continuation(
            "Assistant: I edited src/auth.py and added the validation logic. I haven't run pytest yet to verify.",
            client=self.client,
        )
        self.assertTrue(res_ver.should_nudge)
        self.assertEqual(res_ver.sureforge_phase, "verify")
        self.assertIn("Verify phase", res_ver.suggested_nudge_prompt)

        # 3. Waiting on user ('ask' phase / question mark) -> vetoed (should_nudge = False)
        res_wait = should_nudge_continuation(
            "Would you like me to target PostgreSQL 16 or SQLite for the migration? Waiting on user choice.",
            client=self.client,
        )
        self.assertFalse(res_wait.should_nudge)
        self.assertEqual(res_wait.sureforge_phase, "ask")
        self.assertGreaterEqual(res_wait.waiting_probability, 0.5)

        # 4. Previous nudge made no progress -> vetoed (should_nudge = False)
        res_no_prog = should_nudge_continuation(
            "Still in progress with remaining todo items.",
            previous_nudge_summary="Previous nudge produced no progress and stuck on same output.",
            client=self.client,
        )
        self.assertFalse(res_no_prog.should_nudge)
        self.assertLess(res_no_prog.progress_probability, 0.5)

        # 5. Complete workflow ('complete' phase) -> should_nudge = False
        res_done = should_nudge_continuation(
            "All tests passed (100% passing) and task complete.",
            client=self.client,
        )
        self.assertFalse(res_done.should_nudge)
        self.assertEqual(res_done.sureforge_phase, "complete")


if __name__ == "__main__":
    unittest.main()

