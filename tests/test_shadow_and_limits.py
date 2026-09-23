"""E0.3/E1.1 - payload limits, model pinning and shadow mode (decide without acting)."""
import io
import json
import os
import sys
import tempfile
import unittest
import urllib.error
from pathlib import Path
from unittest.mock import patch

from jev_harness.client import MAX_STATE_CHARS, JevClient, NoulQuestion


SUCCESS_PAYLOAD = {
    "model": "jev-test",
    "answers": {"q": {"type": "noul", "noul": 0.9}},
    "usage": {"input_tokens": 1, "output_tokens": 1},
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


class TestPayloadLimits(unittest.TestCase):
    def _client(self):
        client = JevClient(provider="typesafe", api_key="k", retry_base_delay=0.0, max_retries=1)
        client.base_url = "http://127.0.0.1:9/v1/systemone"
        return client

    def test_limit_plus_one_is_rejected_before_network(self):
        client = JevClient(provider="typesafe", api_key="k")
        with self.assertRaises(RuntimeError) as ctx:
            client.system_one("x" * (MAX_STATE_CHARS + 1), {"q": NoulQuestion("x")})
        self.assertIn("exceeds", str(ctx.exception))

    def test_limit_minus_one_is_accepted(self):
        resp = self._client().system_one("x" * (MAX_STATE_CHARS - 1), {"q": NoulQuestion("x")})
        self.assertTrue(resp.is_mock)  # accepted by the guard, degraded by the dead endpoint

    def test_exact_limit_is_accepted(self):
        resp = self._client().system_one("x" * MAX_STATE_CHARS, {"q": NoulQuestion("x")})
        self.assertTrue(resp.is_mock)  # boundary is inclusive of the limit itself

    def test_normal_payload_is_not_rejected(self):
        client = JevClient(provider="typesafe", api_key="k", retry_base_delay=0.0)
        with patch("jev_harness.client._urlopen_with_ipv4_fallback", side_effect=urllib.error.URLError("refused")):
            resp = client.system_one("small state", {"q": NoulQuestion("x")})
        self.assertTrue(resp.is_mock)  # degraded, but not a limit error


class TestModelPinning(unittest.TestCase):
    """E0.3: the request must carry the pinned model, and `status` must name its origin."""

    def _capture(self, client, state="state"):
        sent = {}

        def _open(req, timeout):
            sent["body"] = json.loads(req.data.decode("utf-8"))
            return _FakeResponse(SUCCESS_PAYLOAD)

        with patch("jev_harness.client._urlopen_with_ipv4_fallback", _open):
            client.system_one(state, {"q": NoulQuestion("x")})
        return sent["body"]

    def _in_repo_config(self, config):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        (Path(tmp.name) / ".jev.json").write_text(json.dumps(config), encoding="utf-8")
        return tmp

    def test_pinned_model_is_sent_in_the_request_payload(self):
        tmp = self._in_repo_config({"model": "jev-1.13.0"})
        old = os.getcwd()
        try:
            os.chdir(tmp.name)
            client = JevClient(provider="typesafe", api_key="k", retry_base_delay=0.0)
            self.assertEqual(client.model_source, ".jev.json")
            self.assertEqual(client.model, "jev-1.13.0")
            body = self._capture(client)
        finally:
            os.chdir(old)
        self.assertEqual(body["model"], "jev-1.13.0")

    def test_environment_variable_pins_the_model_over_repo_config(self):
        tmp = self._in_repo_config({"model": "from-repo"})
        old = os.getcwd()
        try:
            os.chdir(tmp.name)
            with patch.dict(os.environ, {"JEV_MODEL": "jev-1.13.0"}):
                client = JevClient(provider="typesafe", api_key="k")
        finally:
            os.chdir(old)
        self.assertEqual(client.model, "jev-1.13.0")
        self.assertEqual(client.model_source, "env")

    def test_explicit_argument_wins_and_is_labelled(self):
        client = JevClient(provider="typesafe", api_key="k", model="from-argument")
        self.assertEqual(client.model, "from-argument")
        self.assertEqual(client.model_source, "argument")

    def test_provider_default_is_labelled_as_such(self):
        client = JevClient(provider="opencode", api_key="k")
        self.assertEqual(client.model, "jev-1.13-free")
        self.assertEqual(client.model_source, "provider_default")

    def test_status_prints_the_model_and_its_origin(self):
        import jev_harness.cli as cli

        out = io.StringIO()
        with patch.object(sys, "argv", ["jev-harness", "status", "--mock"]):
            with patch("sys.stdout", out):
                with self.assertRaises(SystemExit) as cm:
                    cli.main()
        self.assertEqual(cm.exception.code, 0)
        self.assertIn("Model:", out.getvalue())
        self.assertIn("Model origin:", out.getvalue())


def _run_cli(argv, env=None):
    """Runs the real CLI entry point, capturing exit code, stdout and stderr.

    HOME is redirected so a test run can never inflate the developer's real telemetry or
    decision cache (state lives in `.jev/` or `~/.config/jev`).
    """
    import jev_harness.cli as cli

    out, err = io.StringIO(), io.StringIO()
    code = None
    with tempfile.TemporaryDirectory() as state_dir:
        isolated = {"HOME": state_dir, "USERPROFILE": state_dir}
        isolated.update(env or {})
        with patch.dict(os.environ, isolated):
            with patch.object(sys, "argv", ["jev-harness"] + argv):
                with patch("sys.stdout", out), patch("sys.stderr", err):
                    try:
                        cli.main()
                    except SystemExit as exc:
                        code = exc.code
    return code, out.getvalue(), err.getvalue()


class TestCliPayloadGuard(unittest.TestCase):
    """E0.3 acceptance: an oversized payload must fail with a clear message and exit 2."""

    def test_oversized_payload_exits_two_without_a_traceback(self):
        code, _out, err = _run_cli(
            ["route", "--task", "x" * (MAX_STATE_CHARS + 1)],
            env={"TYPESAFE_API_KEY": "test-key"},
        )
        self.assertEqual(code, 2)
        self.assertIn("exceeds", err)
        self.assertNotIn("Traceback", err)

    def test_over_long_literal_input_is_text_not_a_path(self):
        # Regression: a value longer than the OS path limit raised OSError (traceback, exit 1).
        code, out, err = _run_cli(["route", "--task", "y" * (MAX_STATE_CHARS + 1), "--mock"])
        self.assertEqual(code, 0)
        self.assertIn("MODEL ROUTE VERDICT", out)
        self.assertNotIn("Traceback", err)

    def test_over_long_log_path_reports_not_found_instead_of_crashing(self):
        # Same class as above, on the strict `--log` path check.
        code, _out, err = _run_cli(["test-gate", "--log", "z" * 5000, "--mock"])
        self.assertEqual(code, 2)
        self.assertIn("log file not found", err)
        self.assertNotIn("Traceback", err)


class TestShadowMode(unittest.TestCase):
    def _run(self, argv):
        return _run_cli(argv)

    def test_shadow_never_blocks_a_real_defect(self):
        # A genuine logic defect normally exits 1 (escalate); shadow must exit 0.
        code, _out, _err = self._run(["test-gate", "--mock", "--sample", "AssertionError: assert 4 == 5"])
        self.assertEqual(code, 1)
        code_shadow, _out, err_shadow = self._run(
            ["test-gate", "--mock", "--shadow", "--sample", "AssertionError: assert 4 == 5"]
        )
        self.assertEqual(code_shadow, 0)
        self.assertIn("[SHADOW] would exit 1", err_shadow)

    def test_jev_json_shadow_key_is_honored(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / ".jev.json").write_text(json.dumps({"shadow": True}), encoding="utf-8")
            old = os.getcwd()
            try:
                os.chdir(tmp)
                code, _out, err = self._run(
                    ["test-gate", "--mock", "--sample", "AssertionError: assert 4 == 5"]
                )
            finally:
                os.chdir(old)
        self.assertEqual(code, 0)
        self.assertIn("[SHADOW]", err)


    def test_shadow_json_exposes_envelope(self):
        code, out, _err = self._run(["test-gate", "--mock", "--shadow", "--json", "--sample", "AssertionError: assert 4 == 5"])
        self.assertEqual(code, 0)
        payload = json.loads(out)
        self.assertTrue(payload["shadow"])
        self.assertEqual(payload["would_exit"], 1)

    def test_non_shadow_json_has_no_shadow_keys(self):
        code, out, _err = self._run(["test-gate", "--mock", "--json", "--sample", "AssertionError: assert 4 == 5"])
        self.assertEqual(code, 1)
        payload = json.loads(out)
        self.assertNotIn("shadow", payload)
        self.assertNotIn("would_exit", payload)

    def test_shadow_wins_over_fail_closed_for_gate_failures(self):
        """E1.1 accepts 'shadow always exits 0': a provider/limit failure must not break the pipeline."""
        code, _out, err = _run_cli(
            ["route", "--shadow", "--task", "x" * (MAX_STATE_CHARS + 1)],
            env={"TYPESAFE_API_KEY": "test-key"},
        )
        self.assertEqual(code, 0)
        self.assertIn("exceeds", err)
        self.assertIn("[SHADOW] would exit 2", err)
        self.assertNotIn("Traceback", err)

    def test_invocation_errors_still_exit_two_under_shadow(self):
        """Shadow masks gate/provider outcomes, not CLI misuse."""
        code, _out, err = _run_cli(["test-gate", "--shadow", "--log", "/nao/existe.log", "--mock"])
        self.assertEqual(code, 2)
        self.assertIn("log file not found", err)


if __name__ == "__main__":
    unittest.main()
