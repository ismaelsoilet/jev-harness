"""Fixes verified after the adversarial review of the last epic wave.

Every test here corresponds to a finding: a leak path, a documented flag that did not exist, a
memory that was computed and discarded, an allowlist that read prose, and a break-glass that
never released. They are regression guards, not restatements of the implementation.
"""
import io
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

_PKG_ROOT = str(Path(__file__).resolve().parents[1] / "src")
if _PKG_ROOT not in sys.path:
    sys.path.insert(0, _PKG_ROOT)

import jev_harness.cli as cli
from jev_harness.client import ChoiceQuestion, JevClient, NoulQuestion
from jev_harness.gates import (
    modulate_reasoning_effort,
    route_model_tier,
    should_abort_trajectory,
    should_nudge_continuation,
    triage_test_failure,
    verify_step_completion,
)
from jev_harness.recovery import build_recovery, declared_in_repository
from jev_harness.session import gate_history, get_lease, record_gate_decision, record_tool_error, set_lease

SECRET = "vck_live_9f8a7b6c5d4e3f2a1b0c"
SECRET_LOG = f"AssertionError: assert 4 == 5\napi_key = \"{SECRET}\"\n"


class CapturingClient(JevClient):
    """Captures every payload the client would transmit, without any network."""

    def __init__(self, **kwargs):
        super().__init__(force_mock=True, **kwargs)
        self.payloads = []

    def _build_and_send(self, payload):  # pragma: no cover - not used
        raise AssertionError

    def system_one(self, state, questions, model=None, gate="system_one"):  # type: ignore[override]
        import jev_harness.client as client_module

        original = client_module._urlopen_with_ipv4_fallback
        captured = {}

        def fake_urlopen(req, timeout):
            captured["body"] = req.data.decode("utf-8") if req.data else ""
            raise AssertionError("network disabled in this test")

        client_module._urlopen_with_ipv4_fallback = fake_urlopen
        try:
            live = JevClient(force_mock=False, api_key="test-key", provider="typesafe")
            live.retries = 0
            try:
                live.system_one(state, questions, model, gate)
            except Exception:
                pass
            self.payloads.append(captured.get("body", ""))
        finally:
            client_module._urlopen_with_ipv4_fallback = original
        return super().system_one(state, questions, model, gate)


class TestRedactionReachesEveryGate(unittest.TestCase):
    """The review found redaction only in the triage gate; the client must cover all of them."""

    def setUp(self):
        self.client = CapturingClient()

    def _assert_no_secret(self, label):
        self.assertTrue(self.client.payloads, f"{label}: no payload captured")
        for body in self.client.payloads:
            self.assertNotIn(SECRET, body, f"{label} leaked the secret in the request body")
            self.assertIn("[REDACTED", body, f"{label} did not redact")

    def test_every_gate_redacts_the_state_it_transmits(self):
        self.client.payloads.clear()
        triage_test_failure(SECRET_LOG, client=self.client)
        route_model_tier(f"Review the config with {SECRET}", client=self.client)
        verify_step_completion("tests pass", f"output with password: {SECRET}", client=self.client)
        should_abort_trajectory(f"Rerun with api_key={SECRET}", "attempt 1 failed", client=self.client)
        modulate_reasoning_effort(f"tool: curl -H 'Authorization: {SECRET}'", client=self.client)
        should_nudge_continuation(f"Assistant: set api_key = {SECRET}", client=self.client)
        self.assertEqual(len(self.client.payloads), 6)
        self._assert_no_secret("gates")

    def test_the_payload_guard_measures_the_redacted_string(self):
        long_log = "AssertionError: assert 1 == 2\n" + ("padding " * 40) + f"api_key={SECRET}"
        self.client.payloads.clear()
        triage_test_failure(long_log, client=self.client)
        self._assert_no_secret("payload guard")


class TestStateJsonFlag(unittest.TestCase):
    """`--state-json` was documented while missing; it must work and must fail loudly."""

    def _run(self, argv, cwd=None):
        out, err = io.StringIO(), io.StringIO()
        with patch.object(sys, "argv", ["jev-harness"] + argv):
            with patch("sys.stdout", out), patch("sys.stderr", err):
                with self.assertRaises(SystemExit) as cm:
                    cli.main()
        return cm.exception.code, out.getvalue(), err.getvalue()

    def test_inline_object_is_accepted(self):
        code, out, _err = self._run(
            ["route", "--mock", "--json", "--task", "Fix a typo",
             "--state-json", '{"repo": "acme", "referenced_files": ["src/app.py"]}']
        )
        self.assertEqual(code, 0)
        self.assertIn("selected_tier", json.loads(out))

    def test_a_green_sample_exits_zero_with_extra_context(self):
        code, out, _err = self._run(
            ["test-gate", "--mock", "--json", "--sample", "ModuleNotFoundError: No module named 'requests'",
             "--state-json", '{"test_command": "pytest -q"}']
        )
        self.assertEqual(code, 0, "--state-json must not change the deterministic exit code")
        self.assertEqual(json.loads(out)["category"], "env_missing")

    def test_file_object_is_accepted(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "state.json"
            path.write_text(json.dumps({"test_command": "pytest -q"}), encoding="utf-8")
            code, _out, _err = self._run(
                ["test-gate", "--mock", "--sample", "ModuleNotFoundError: No module named 'requests'",
                 "--state-json", str(path)]
            )
        self.assertEqual(code, 0, "a declared dependency is still a deterministic decision")

    def test_invalid_value_exits_two_with_a_clear_message(self):
        code, _out, err = self._run(
            ["test-gate", "--mock", "--sample", "AssertionError: 1 != 2", "--state-json", "not json"]
        )
        self.assertEqual(code, 2)
        self.assertIn("--state-json", err)

    def test_non_object_json_is_rejected(self):
        code, _out, err = self._run(["test-gate", "--mock", "--sample", "AssertionError: 1 != 2", "--state-json", "[1, 2]"])
        self.assertEqual(code, 2)
        self.assertIn("must be a JSON object", err)

    def test_the_extra_context_reaches_the_gate_state(self):
        captured = {}

        class Spy(JevClient):
            def system_one(self, state, questions, model=None, gate="system_one"):  # type: ignore[override]
                captured["state"] = state
                return super().system_one(state, questions, model, gate)

        triage_test_failure(
            "AssertionError: 1 != 2", client=Spy(force_mock=True), extra_state={"repo": "acme"}
        )
        self.assertIn("acme", json.dumps(captured["state"]))


class MemoryClient(JevClient):
    def __init__(self, **kwargs):
        super().__init__(force_mock=True, **kwargs)
        self.states = []

    def system_one(self, state, questions, model=None, gate="system_one"):  # type: ignore[override]
        self.states.append(state)
        return super().system_one(state, questions, model, gate)


class TestGateMemoryActuallyReachesTheState(unittest.TestCase):
    """The review found the enriched history computed and then discarded."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self._cwd = os.getcwd()
        os.chdir(self._tmp.name)
        self.addCleanup(os.chdir, self._cwd)
        self._env = patch.dict(os.environ, {"HOME": self._tmp.name, "USERPROFILE": self._tmp.name})
        self._env.start()
        self.addCleanup(self._env.stop)

    def test_remembered_decisions_travel_in_the_abort_state(self):
        for _ in range(3):
            triage_test_failure("AssertionError: assert 4 == 5", client=JevClient(force_mock=True), record_session=True)
        record_gate_decision("abort", "abort", action="abort_and_ask")
        client = MemoryClient()
        result = should_abort_trajectory("Retry the same fix again", client=client, record_session=True)
        rendered = json.dumps(client.states[-1])
        self.assertIn("Recent abort decisions", rendered, "the remembered decisions must be sent")
        self.assertIn("Recent triage outcomes", rendered, "the remembered triage must be sent too")
        self.assertTrue(result.should_abort, "the repeated step must still abort")

    def test_an_explicit_history_replaces_the_memory(self):
        record_gate_decision("abort", "proceed", action="proceed")
        client = MemoryClient()
        should_abort_trajectory("Add the missing fixture", "Attempt 1: fixture missing.", client=client)
        rendered = json.dumps(client.states[-1])
        self.assertIn("Attempt 1: fixture missing.", rendered)
        self.assertNotIn("Recent abort decisions", rendered)


class TestRecoveryAllowlistReadsDeclarations(unittest.TestCase):
    """Prose must not make a package look installed, and lockfiles must still be read."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)

    def test_a_package_mentioned_in_prose_is_not_declared(self):
        (self.root / "Cargo.toml").write_text(
            '[package]\nname = "app"\ndescription = "a prose-lib compatible client, see also uvicorn"\n',
            encoding="utf-8",
        )
        self.assertFalse(declared_in_repository("prose-lib", "pypi", self.root))
        self.assertFalse(declared_in_repository("uvicorn", "pypi", self.root))
        recovery = build_recovery(
            "ModuleNotFoundError: No module named 'uvicorn'", repo_root=self.root, allow_auto_recovery=True
        )
        self.assertFalse(recovery["is_safe_auto_run"])

    def test_real_declarations_are_still_recognized(self):
        (self.root / "requirements.txt").write_text("requests==2.32.0\n", encoding="utf-8")
        (self.root / "package.json").write_text(json.dumps({"dependencies": {"@scope/pkg": "^1"}}), encoding="utf-8")
        (self.root / "package-lock.json").write_text(
            json.dumps({"packages": {"node_modules/@other/pkg": {"version": "1.0.0"}}}), encoding="utf-8"
        )
        (self.root / "Cargo.toml").write_text('[dependencies]\nserde = "1.0"\n', encoding="utf-8")
        self.assertTrue(declared_in_repository("requests", "pypi", self.root))
        self.assertTrue(declared_in_repository("@scope/pkg", "npm", self.root))
        self.assertTrue(declared_in_repository("@other/pkg", "npm", self.root), "lockfile formats count")
        self.assertTrue(declared_in_repository("serde", "cargo", self.root))


class TestBreakGlassAndLeaseReport(unittest.TestCase):
    """A reported tool error must not leave the lease permanently inert, and the count must be real."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self._cwd = os.getcwd()
        os.chdir(self._tmp.name)
        self.addCleanup(os.chdir, self._cwd)
        self._env = patch.dict(os.environ, {"HOME": self._tmp.name, "USERPROFILE": self._tmp.name})
        self._env.start()
        self.addCleanup(self._env.stop)

    def test_a_new_decision_clears_the_previous_tool_error(self):
        set_lease("low", {}, 3)
        record_tool_error("npm test failed")
        self.assertIsNone(get_lease(), "the break-glass must invalidate the lease")

        set_lease("medium", {"reasoning_effort": "medium"}, 2)
        lease = get_lease()
        self.assertIsNotNone(lease, "a fresh decision is a fresh start after a reported error")
        self.assertEqual(lease["effort"], "medium")

    def test_the_leased_result_reports_the_steps_left_after_this_one(self):
        set_lease("low", {"reasoning_effort": "low"}, 3)
        result = modulate_reasoning_effort("git status", client=JevClient(force_mock=True), use_lease=True)
        self.assertEqual(result.lease_steps, 2, "the reported count is what remains after this step")
        self.assertEqual(get_lease()["steps_remaining"], 2)

    def test_the_lease_still_answers_without_a_provider_call(self):
        set_lease("low", {}, 2)

        class Poisoned(JevClient):
            def system_one(self, *args, **kwargs):  # type: ignore[override]
                raise AssertionError("a leased step must not reach the provider")

        result = modulate_reasoning_effort("git status", client=Poisoned(force_mock=True), use_lease=True)
        self.assertEqual(result.effort, "low")


class TestQuestionPreconditionsAtSendTime(unittest.TestCase):
    def test_a_single_option_question_is_refused_when_sent(self):
        client = JevClient(force_mock=True)
        with self.assertRaises(ValueError):
            client.system_one("state", {"q": ChoiceQuestion(instructions="x", criteria={"only": "one"})})

    def test_a_valid_batch_is_sent(self):
        client = JevClient(force_mock=True)
        response = client.system_one("state", {"q": NoulQuestion(instructions="done?")})
        self.assertTrue(response.answers)


if __name__ == "__main__":
    unittest.main()
