import os
import unittest
import tempfile
import shutil
from pathlib import Path
from jev_harness.client import JevClient
from jev_harness.gates import (
    triage_test_failure,
    should_abort_trajectory,
    route_model_tier,
    verify_step_completion,
)
from jev_harness.session import (
    SessionState,
    load_session,
    save_session,
    record_triage_event,
    record_abort_event,
    record_route_event,
    detect_repeated_failure,
    record_step_attempt,
    reset_metrics,
)


class TestAdversarialAndTelemetry(unittest.TestCase):
    def setUp(self):
        self.client = JevClient(force_mock=True)
        self.temp_dir = tempfile.mkdtemp()
        self.orig_home = os.environ.get("HOME")
        os.environ["HOME"] = self.temp_dir

    def tearDown(self):
        if self.orig_home:
            os.environ["HOME"] = self.orig_home
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_adversarial_negated_abort_english(self):
        res = should_abort_trajectory(
            proposed_step="Do NOT abort, proceed with database migration steps",
            recent_attempts_summary="Previous step completed successfully",
            client=self.client,
        )
        self.assertFalse(res.should_abort, "Negated abort intent must NOT trigger abort")
        self.assertEqual(res.action, "proceed")
        self.assertLess(res.abort_probability, 0.50)

    def test_adversarial_negated_abort_portuguese(self):
        res = should_abort_trajectory(
            proposed_step="Não aborte, execute a validação linear dos critérios",
            recent_attempts_summary="Etapa 1 executada com sucesso",
            client=self.client,
        )
        self.assertFalse(res.should_abort, "Negated abort in Portuguese must NOT trigger abort")
        self.assertEqual(res.action, "proceed")

    def test_adversarial_assertion_testing_module_name(self):
        res = triage_test_failure(
            failure_log="FAILED tests/test_mod.py::test_loader - AssertionError: assert 'No module named torch' in resp.text",
            client=self.client,
        )
        self.assertEqual(res.category, "deep_logic", "AssertionError must take precedence over substring module names")
        self.assertFalse(res.skip_llm, "Deep logic assertion test must NOT skip LLM")

    def test_adversarial_heavy_keyword_dominance(self):
        res = route_model_tier(
            task_description="Architect enterprise distributed kernel consensus engine and fix typo in comments",
            client=self.client,
        )
        self.assertEqual(res.selected_tier, "heavy_system2", "Kernel / distributed consensus must dominate minor typo")
        self.assertIn("Claude Fable 5.1", res.recommended_model)

    def test_telemetry_event_recording(self):
        reset_metrics()
        
        # Record triage with skip_llm=True
        record_triage_event(skip_llm=True, category="env_missing")
        # Record triage with skip_llm=False
        record_triage_event(skip_llm=False, category="deep_logic")
        # Record abort guard triggered
        record_abort_event(triggered=True)
        # Record deterministic route
        record_route_event(selected_tier="deterministic")

        session = load_session()
        self.assertEqual(session.total_triage_calls, 2)
        self.assertEqual(session.skipped_llm_calls, 1)
        self.assertEqual(session.abort_guards_triggered, 1)
        self.assertEqual(session.deterministic_routes, 1)
        self.assertGreater(session.estimated_tokens_saved, 100000)
        self.assertGreater(session.estimated_cost_saved_usd, 1.50)

    def test_telemetry_doom_loop_repeated_failure(self):
        reset_metrics()
        err = "TypeError: cannot unpack non-iterable NoneType object in process_batch"
        
        # 1st attempt: not yet repeated
        record_step_attempt("Attempt 1", error_snippet=err)
        self.assertFalse(detect_repeated_failure(err, max_repeats=2))

        # 2nd attempt with same error: repeated failure detected!
        record_step_attempt("Attempt 2", error_snippet=err)
        self.assertTrue(detect_repeated_failure(err, max_repeats=2))

    def test_opencode_zen_live_property(self):
        opencode_client = JevClient(provider="opencode")
        self.assertTrue(opencode_client.is_live, "OpenCode Zen provider must be live without API key")
        self.assertIn("zen/v1/systemone", opencode_client.base_url)

    def test_adversarial_utf8_truncation_emojis(self):
        # Build 8000-char string packed with UTF-8 accents and 4-byte emojis
        chunk = "⚡ Erro de compilação em módulo de produção: 'não foi possível carregar' 🦀 🔥\n"
        log = chunk * 100
        res = triage_test_failure(failure_log=log, client=self.client)
        self.assertIsNotNone(res.category)
        self.assertTrue(res.is_mock)

    def test_opencode_zen_no_silent_fallback_on_network_error(self):
        from unittest.mock import patch
        import urllib.error
        from jev_harness.client import NoulQuestion

        client = JevClient(provider="opencode")
        http_err = urllib.error.HTTPError(
            url="https://opencode.ai/zen/v1/systemone",
            code=500,
            msg="Internal Server Error",
            hdrs={},
            fp=None,
        )
        with patch("jev_harness.client._urlopen_with_ipv4_fallback", side_effect=http_err):
            with self.assertRaises(RuntimeError) as ctx:
                client.system_one("test state", {"q": NoulQuestion("is valid?")})
            self.assertIn("OpenCode Zen API returned HTTP 500", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
