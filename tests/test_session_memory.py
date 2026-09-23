"""E3.4 / E3.7 — session memory in the gates, and the persistent effort lease.

The two properties that matter: a gate must use *real* history when the caller sends none (while
an explicit history always wins), and the lease must be cheap, bounded, and breakable — without
ever losing data written by another version of the tool.
"""
import json
import os
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

_PKG_ROOT = str(Path(__file__).resolve().parents[1] / "src")
if _PKG_ROOT not in sys.path:
    sys.path.insert(0, _PKG_ROOT)

from jev_harness.client import JevClient
from jev_harness.gates import (
    modulate_reasoning_effort,
    should_abort_trajectory,
    should_nudge_continuation,
    triage_test_failure,
)
from jev_harness.session import (
    SESSION_SCHEMA_VERSION,
    consume_lease,
    gate_history,
    get_lease,
    load_session,
    record_gate_decision,
    record_tool_error,
    save_session,
    set_lease,
)


class SessionTestCase(unittest.TestCase):
    def setUp(self):
        self._cwd = os.getcwd()
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        os.chdir(self.root)
        self.addCleanup(self._cleanup_dirs)
        self._env = patch.dict(os.environ, {"HOME": str(self.root), "USERPROFILE": str(self.root)})
        self._env.start()
        self.addCleanup(self._env.stop)
        self.client = JevClient(force_mock=True)

    def _cleanup_dirs(self):
        os.chdir(self._cwd)
        self._tmp.cleanup()


class TestGateMemory(SessionTestCase):
    """E3.4 — the gates use the repository's own recent decisions."""

    def test_triage_records_its_decision(self):
        triage_test_failure("ModuleNotFoundError: No module named 'x'", client=self.client, record_session=True)
        history = gate_history("triage")
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0]["decision"], "env_missing")
        self.assertFalse(history[0]["action"] == "", "the recommended action is remembered")

    def test_abort_detects_repetition_from_the_session(self):
        for _ in range(3):
            triage_test_failure("AssertionError: assert 4 == 5", client=self.client, record_session=True)
        # No --history is provided: the gate must fall back to what this repository decided.
        result = should_abort_trajectory(
            "Retry the same fix again", client=self.client, record_session=True
        )
        self.assertTrue(result.should_abort)
        captured = gate_history("abort")
        self.assertEqual(captured[-1]["decision"], "abort")

    def test_an_explicit_history_still_wins(self):
        record_gate_decision("abort", "proceed", action="proceed")
        captured = {}

        class Spy(JevClient):
            def system_one(self, state, questions, model=None, gate="system_one"):  # type: ignore[override]
                captured["state"] = state
                return super().system_one(state, questions, model, gate)

        should_abort_trajectory(
            "Add the missing fixture", "Attempt 1: fixture missing; added it.", client=Spy(force_mock=True)
        )
        rendered = json.dumps(captured["state"])
        self.assertIn("Attempt 1: fixture missing", rendered)
        self.assertNotIn("Recent abort decisions", rendered)

    def test_nudge_reuses_the_last_real_nudge(self):
        """With a remembered nudge the gate treats the call as a *repeat* (it can judge progress)."""
        transcript = "Assistant: finished the parser. Next I will wire it into the CLI."
        first = should_nudge_continuation(transcript, client=self.client)
        self.assertEqual(first.progress_probability, 1.0, "no previous nudge means progress is assumed")

        record_gate_decision("nudge-gate", "execute", action="nudge")
        second = should_nudge_continuation(transcript, client=self.client)
        self.assertLess(second.progress_probability, 1.0, "the remembered nudge is now the reference")
        self.assertTrue(second.should_nudge)

    def test_memory_is_isolated_per_repository(self):
        triage_test_failure("AssertionError: 1 != 2", client=self.client, record_session=True)
        other = tempfile.TemporaryDirectory()
        try:
            os.chdir(other.name)
            (Path(other.name) / ".jev").mkdir()
            self.assertEqual(gate_history("triage"), [], "another repository must not see this history")
        finally:
            os.chdir(self.root)
            other.cleanup()

    def test_history_is_bounded(self):
        for index in range(40):
            record_gate_decision("triage", f"category-{index}")
        history = gate_history("triage")
        self.assertLessEqual(len(history), 20)
        self.assertEqual(history[-1]["decision"], "category-39")


class TestPersistentLease(SessionTestCase):
    """E3.7 — cheap reuse, a caller contract, and a break-glass."""

    def test_a_leased_decision_does_not_call_the_provider(self):
        calls = {"n": 0}

        class Counting(JevClient):
            def system_one(self, *args, **kwargs):  # type: ignore[override]
                calls["n"] += 1
                return super().system_one(*args, **kwargs)

        set_lease("low", {"reasoning_effort": "low"}, 2)
        started = time.perf_counter()
        result = modulate_reasoning_effort("git status", client=Counting(force_mock=True), use_lease=True)
        elapsed_ms = (time.perf_counter() - started) * 1000
        self.assertEqual(calls["n"], 0, "a leased step must not spend a call")
        self.assertEqual(result.effort, "low")
        self.assertLess(elapsed_ms, 250, f"lease should answer in sub-milliseconds (took {elapsed_ms:.2f} ms)")
        self.assertEqual(get_lease()["steps_remaining"], 1)

    def test_a_tool_error_zeroes_the_lease(self):
        set_lease("high", {}, 5)
        self.assertIsNotNone(get_lease())
        record_tool_error("package manager failed")
        self.assertIsNone(get_lease(), "the break-glass must invalidate the lease immediately")

    def test_lease_without_opt_in_is_ignored(self):
        set_lease("low", {}, 2)
        result = modulate_reasoning_effort("design a distributed consensus layer", client=self.client)
        self.assertNotEqual(result.effort, "low", "an unrelated task must be re-decided")
        self.assertEqual(get_lease()["steps_remaining"], 2, "the lease is untouched when not used")

    def test_lease_expires_with_its_ttl(self):
        set_lease("low", {}, 3)
        lease = get_lease()
        self.assertIsNotNone(lease)
        self.assertIsNone(get_lease(now=time.time() + lease["ttl_seconds"] + 1))

    def test_exhausted_lease_is_not_returned(self):
        set_lease("low", {}, 1)
        self.assertIsNotNone(consume_lease())
        self.assertIsNone(get_lease())

    def test_lease_carries_its_schema_version_and_contract(self):
        set_lease("medium", {"reasoning_effort": "medium"}, 5)
        lease = get_lease()
        self.assertEqual(
            set(lease),
            {"effort", "provider_params", "steps_remaining", "issued_at", "ttl_seconds", "schema_version"},
        )
        self.assertEqual(lease["schema_version"], SESSION_SCHEMA_VERSION)

    def test_an_effort_decision_opens_the_lease_for_the_next_steps(self):
        result = modulate_reasoning_effort("git status", client=self.client, record_session=True)
        lease = get_lease()
        self.assertIsNotNone(lease, "a decision with lease steps must open a lease")
        self.assertEqual(lease["effort"], result.effort)
        self.assertGreater(lease["steps_remaining"], 0)


class TestSchemaTolerance(SessionTestCase):
    """An older (or newer) writer must never lose data through this version."""

    def _session_path(self) -> Path:
        from jev_harness.session import _get_storage_path

        return _get_storage_path()

    def test_unknown_fields_survive_a_load_and_save_round_trip(self):
        path = self._session_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(
                {
                    "total_triage_calls": 3,
                    "future_field": {"from": "a newer writer"},
                    "another_future": [1, 2, 3],
                }
            ),
            encoding="utf-8",
        )
        session = load_session()
        self.assertEqual(session.total_triage_calls, 3)
        self.assertEqual(session.schema_version, 1, "the stored version is reported honestly")
        save_session(session)
        written = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(written["future_field"], {"from": "a newer writer"})
        self.assertEqual(written["another_future"], [1, 2, 3])
        self.assertEqual(written["schema_version"], SESSION_SCHEMA_VERSION)
        self.assertEqual(written["total_triage_calls"], 3)

    def test_a_corrupted_session_file_does_not_break_anything(self):
        path = self._session_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("{ not json", encoding="utf-8")
        session = load_session()
        self.assertEqual(session.total_triage_calls, 0)
        self.assertIsNone(get_lease())

    def test_gate_decisions_and_lease_survive_a_round_trip(self):
        record_gate_decision("abort", "proceed", action="proceed")
        set_lease("low", {"reasoning_effort": "low"}, 2)
        reloaded = load_session()
        self.assertEqual(reloaded.gate_decisions[-1]["decision"], "proceed")
        self.assertEqual(reloaded.lease["effort"], "low")


if __name__ == "__main__":
    unittest.main()
