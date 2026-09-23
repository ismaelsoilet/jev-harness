"""E3.2 / E3.3 — the decision cache and the debounce window.

The cache exists to avoid paying twice for the same decision, and the failure mode to test is
exactly the opposite: serving a *stale* or *wrong-provenance* answer (an offline one to an online
caller, a shadow measurement, or a degraded fallback mistaken for a decision).
"""
import io
import json
import os
import pathlib
import sys
import tempfile
import threading
import time
import unittest
import urllib.error
from pathlib import Path
from unittest.mock import patch

_PKG_ROOT = str(Path(__file__).resolve().parents[1] / "src")
if _PKG_ROOT not in sys.path:
    sys.path.insert(0, _PKG_ROOT)

import jev_harness.cache as cache_mod
import jev_harness.client as client_mod
from jev_harness.cache import cache_key, clear, get, put, stats  # noqa: F401 (clear used in stats tests)
from jev_harness.client import JevClient, NoulQuestion

LIVE_PAYLOAD = {
    "model": "jev-1.13.0",
    "answers": {"q": {"type": "noul", "noul": 0.9}},
    "usage": {"input_tokens": 10, "output_tokens": 2},
    "cost": "0.0000004",
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


class CacheTestCase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)
        self._cwd = os.getcwd()
        os.chdir(self.root)
        self.addCleanup(os.chdir, self._cwd)
        self._env = patch.dict(
            os.environ,
            {"HOME": str(self.root), "USERPROFILE": str(self.root), "JEV_CACHE": ""},
        )
        self._env.start()
        self.addCleanup(self._env.stop)


class TestKeys(CacheTestCase):
    def test_key_covers_everything_that_can_change_the_answer(self):
        base = cache_key("triage", "log", "model-a", "typesafe", False)
        self.assertEqual(base, cache_key("triage", "log", "model-a", "typesafe", False))
        for variant in (
            cache_key("verify", "log", "model-a", "typesafe", False),
            cache_key("triage", "log2", "model-a", "typesafe", False),
            cache_key("triage", "log", "model-b", "typesafe", False),
            cache_key("triage", "log", "model-a", "opencode", False),
            cache_key("triage", "log", "model-a", "typesafe", True),
        ):
            with self.subTest(variant):
                self.assertNotEqual(base, variant)

    def test_offline_and_online_never_share_an_entry(self):
        self.assertNotEqual(
            cache_key("triage", "log", "m", "typesafe", True), cache_key("triage", "log", "m", "typesafe", False)
        )


class TestStoreAndFetch(CacheTestCase):
    def test_roundtrip(self):
        self.assertTrue(put("triage", "log", "m", "typesafe", False, {"model": "m", "answers": {}}))
        payload, debounced = get("triage", "log", "m", "typesafe", False)
        self.assertIsNotNone(payload)
        self.assertFalse(debounced)

    def test_ttl_expiry(self):
        now = time.time()
        put("triage", "log", "m", "typesafe", False, {"model": "m"}, now=now)
        fresh, _ = get("triage", "log", "m", "typesafe", False, now=now + 10)
        self.assertIsNotNone(fresh)
        expired, _ = get("triage", "log", "m", "typesafe", False, now=now + 4000)
        self.assertIsNone(expired)

    def test_configured_ttl_is_honored(self):
        (self.root / ".jev.json").write_text(json.dumps({"cache_ttl_seconds": 5}), encoding="utf-8")
        now = time.time()
        put("triage", "log", "m", "typesafe", False, {"model": "m"}, now=now)
        self.assertIsNotNone(get("triage", "log", "m", "typesafe", False, now=now + 4)[0])
        self.assertIsNone(get("triage", "log", "m", "typesafe", False, now=now + 6)[0])

    def test_disabled_by_config(self):
        (self.root / ".jev.json").write_text(json.dumps({"cache": False}), encoding="utf-8")
        self.assertFalse(put("triage", "log", "m", "typesafe", False, {"model": "m"}))
        self.assertIsNone(get("triage", "log", "m", "typesafe", False)[0])

    def test_disabled_by_env(self):
        with patch.dict(os.environ, {"JEV_CACHE": "0"}):
            self.assertFalse(put("triage", "log", "m", "typesafe", False, {"model": "m"}))
            self.assertIsNone(get("triage", "log", "m", "typesafe", False)[0])

    def test_clear_and_stats(self):
        put("triage", "a", "m", "typesafe", False, {"model": "m"})
        get("triage", "a", "m", "typesafe", False)  # hit
        get("triage", "b", "m", "typesafe", False)  # miss
        report = stats()
        self.assertEqual(report["entries"], 1)
        self.assertEqual(report["hits"], 1)
        self.assertEqual(report["misses"], 1)
        self.assertAlmostEqual(report["hit_rate"], 0.5)
        self.assertEqual(clear(), 1)
        self.assertEqual(stats()["entries"], 0)

    def test_prune_drops_expired_entries(self):
        now = time.time()
        put("triage", "old", "m", "typesafe", False, {"model": "m"}, now=now - 10_000)
        put("triage", "new", "m", "typesafe", False, {"model": "m"}, now=now)
        self.assertEqual(stats(now=now)["entries"], 2)
        self.assertEqual(stats(now=now, prune=True)["entries"], 1)

    def test_concurrent_writes_keep_the_file_valid(self):
        def writer(index):
            for step in range(4):
                put("triage", f"log-{index}-{step}", "m", "typesafe", False, {"model": "m"})

        threads = [threading.Thread(target=writer, args=(i,)) for i in range(6)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        payload = json.loads((self.root / ".config" / "jev" / "cache.json").read_text(encoding="utf-8"))
        self.assertEqual(len(payload["entries"]), 24)

    def test_file_permissions_are_hardened(self):
        if os.name == "nt":
            self.skipTest("POSIX permissions")
        import stat

        put("triage", "log", "m", "typesafe", False, {"model": "m"})
        path = self.root / ".config" / "jev" / "cache.json"
        self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)


class TestDebounce(CacheTestCase):
    def test_a_repeat_inside_the_window_is_coalesced(self):
        now = time.time()
        put("nudge", "transcript", "m", "typesafe", False, {"model": "m"}, now=now)
        payload, debounced = get(
            "nudge", "transcript", "m", "typesafe", False, window_seconds=5, now=now + 1
        )
        self.assertIsNotNone(payload)
        self.assertTrue(debounced)
        self.assertEqual(stats()["debounced"], 1)

    def test_a_repeat_outside_the_window_is_a_fresh_decision(self):
        now = time.time()
        put("nudge", "transcript", "m", "typesafe", False, {"model": "m"}, now=now)
        payload, debounced = get(
            "nudge", "transcript", "m", "typesafe", False, window_seconds=5, now=now + 30
        )
        self.assertIsNone(payload)
        self.assertFalse(debounced)

    def test_only_the_turn_gates_debounce(self):
        """The names must match the `gate=` the gate functions actually pass to system_one."""
        from jev_harness.cache import DEBOUNCE_GATES

        self.assertEqual(set(DEBOUNCE_GATES), {"nudge", "abort"})
        gates_source = pathlib.Path(__file__).resolve().parents[1] / "src" / "jev_harness" / "gates.py"
        source = gates_source.read_text(encoding="utf-8")
        for gate in DEBOUNCE_GATES:
            with self.subTest(gate):
                self.assertIn(f'gate="{gate}"', source, "a debounced gate must tag its own calls")

    def test_different_input_is_always_evaluated(self):
        now = time.time()
        put("nudge", "transcript A", "m", "typesafe", False, {"model": "m"}, now=now)
        payload, _ = get("nudge", "transcript B", "m", "typesafe", False, window_seconds=5, now=now + 1)
        self.assertIsNone(payload)


class TestClientIntegration(CacheTestCase):
    def _client(self, **kwargs):
        return JevClient(provider="typesafe", api_key="k", retry_base_delay=0.0, cache=True, **kwargs)

    def test_a_second_identical_live_call_does_not_hit_the_provider(self):
        calls = {"n": 0}

        def _open(req, timeout):
            calls["n"] += 1
            return _FakeResponse(LIVE_PAYLOAD)

        client = self._client()
        with patch.object(client_mod, "_urlopen_with_ipv4_fallback", _open):
            first = client.system_one("state", {"q": NoulQuestion("x")}, gate="triage")
            second = client.system_one("state", {"q": NoulQuestion("x")}, gate="triage")
        self.assertEqual(calls["n"], 1, "the second identical decision must be served locally")
        self.assertFalse(first.cached)
        self.assertTrue(second.cached)
        self.assertAlmostEqual(second.answers["q"].noul, first.answers["q"].noul)

    def test_cache_is_opt_in_for_library_callers(self):
        calls = {"n": 0}

        def _open(req, timeout):
            calls["n"] += 1
            return _FakeResponse(LIVE_PAYLOAD)

        client = JevClient(provider="typesafe", api_key="k", retry_base_delay=0.0)
        with patch.object(client_mod, "_urlopen_with_ipv4_fallback", _open):
            client.system_one("state", {"q": NoulQuestion("x")}, gate="triage")
            client.system_one("state", {"q": NoulQuestion("x")}, gate="triage")
        self.assertEqual(calls["n"], 2, "without cache=True every call is a real decision")

    def test_a_different_gate_never_shares_an_entry(self):
        calls = {"n": 0}

        def _open(req, timeout):
            calls["n"] += 1
            return _FakeResponse(LIVE_PAYLOAD)

        client = self._client()
        with patch.object(client_mod, "_urlopen_with_ipv4_fallback", _open):
            client.system_one("state", {"q": NoulQuestion("x")}, gate="triage")
            client.system_one("state", {"q": NoulQuestion("x")}, gate="verify")
        self.assertEqual(calls["n"], 2)

    def test_a_degraded_answer_is_never_cached(self):
        client = self._client()
        with patch.object(client_mod, "_urlopen_with_ipv4_fallback", side_effect=urllib.error.URLError("down")):
            degraded = client.system_one("state", {"q": NoulQuestion("x")}, gate="triage")
        self.assertTrue(degraded.is_mock)
        self.assertEqual(stats()["entries"], 0, "a fallback is a symptom, not a decision")

    def test_cache_does_not_leak_between_providers(self):
        calls = {"n": 0}

        def _open(req, timeout):
            calls["n"] += 1
            return _FakeResponse(LIVE_PAYLOAD)

        with patch.object(client_mod, "_urlopen_with_ipv4_fallback", _open):
            self._client().system_one("state", {"q": NoulQuestion("x")}, gate="triage")
            JevClient(
                provider="openrouter", api_key="k", retry_base_delay=0.0, cache=True
            ).system_one("state", {"q": NoulQuestion("x")}, gate="triage")
        self.assertEqual(calls["n"], 2)

    def test_the_replay_bypasses_the_cache(self):
        from jev_harness.replay import load_corpus, run_corpus

        client = JevClient(force_mock=True, cache=False)
        corpus = Path(__file__).resolve().parent / "corpus"
        first = run_corpus(load_corpus(corpus)[:5], client)
        self.assertEqual(stats()["entries"], 0)
        self.assertEqual(len(first.results), 5)


class TestCliCache(CacheTestCase):
    def _run(self, argv):
        import jev_harness.cli as cli

        out, err = io.StringIO(), io.StringIO()
        with patch.object(sys, "argv", ["jev-harness"] + argv):
            with patch("sys.stdout", out), patch("sys.stderr", err):
                with self.assertRaises(SystemExit) as cm:
                    cli.main()
        return cm.exception.code, out.getvalue(), err.getvalue()

    def test_cli_enables_the_cache_and_no_cache_bypasses_it(self):
        calls = {"n": 0}

        def _open(req, timeout):
            calls["n"] += 1
            return _FakeResponse(LIVE_PAYLOAD)

        with patch.dict(os.environ, {"TYPESAFE_API_KEY": "test-key"}):
            with patch.object(client_mod, "_urlopen_with_ipv4_fallback", _open):
                self._run(["test-gate", "--sample", "AssertionError: assert 1 == 2"])
                self._run(["test-gate", "--sample", "AssertionError: assert 1 == 2"])
                after_cache = calls["n"]
                self._run(["test-gate", "--no-cache", "--sample", "AssertionError: assert 1 == 2"])
        self.assertEqual(after_cache, 1, "the CLI shares the cache across invocations")
        self.assertEqual(calls["n"], 2, "--no-cache forces a real decision")

    def test_metrics_reports_the_hit_rate(self):
        put("triage", "log", "m", "typesafe", False, {"model": "m"})
        get("triage", "log", "m", "typesafe", False)
        code, out, _err = self._run(["metrics", "--json"])
        self.assertEqual(code, 0)
        payload = json.loads(out)
        self.assertIn("cache", payload)
        self.assertEqual(payload["cache"]["hits"], 1)
        self.assertIsNotNone(payload["cache"]["hit_rate"])

    def test_metrics_human_output_mentions_the_cache(self):
        code, out, _err = self._run(["metrics"])
        self.assertEqual(code, 0)
        self.assertIn("Decision Cache:", out)

    def test_shadow_runs_are_not_cached(self):
        calls = {"n": 0}

        def _open(req, timeout):
            calls["n"] += 1
            return _FakeResponse(LIVE_PAYLOAD)

        with patch.dict(os.environ, {"TYPESAFE_API_KEY": "test-key"}):
            with patch.object(client_mod, "_urlopen_with_ipv4_fallback", _open):
                for _ in range(2):
                    self._run(["test-gate", "--shadow", "--sample", "AssertionError: assert 1 == 2"])
        self.assertEqual(calls["n"], 2, "shadow always measures real decisions")
        self.assertEqual(stats()["entries"], 0, "a shadow measurement must never populate the cache")


if __name__ == "__main__":
    unittest.main()


class TestTurnGateDebounceEndToEnd(CacheTestCase):
    """The debounce must be observable through the gate that owns it, not just in the cache."""

    def _live_gate_client(self):
        return JevClient(provider="typesafe", api_key="k", retry_base_delay=0.0, cache=True)

    def test_repeated_nudge_evaluations_coalesce(self):
        from jev_harness.gates import should_nudge_continuation

        payload = {
            "model": "m",
            "answers": {
                "nudge": {"type": "noul", "noul": 0.9},
                "phase": {"type": "choice", "choice": "execute", "confidence": 0.9},
            },
            "usage": {"input_tokens": 1, "output_tokens": 1},
        }
        calls = {"n": 0}

        def _open(req, timeout):
            calls["n"] += 1
            return _FakeResponse(payload)

        client = self._live_gate_client()
        with patch.object(client_mod, "_urlopen_with_ipv4_fallback", _open):
            first = should_nudge_continuation("Assistant: finished the parser and stopped.", client=client)
            second = should_nudge_continuation("Assistant: finished the parser and stopped.", client=client)
        self.assertEqual(calls["n"], 1, "a repeat inside the debounce window must not hit the provider")
        self.assertFalse(first.debounced)
        self.assertTrue(second.cached)
        self.assertTrue(second.debounced)

    def test_repeated_abort_evaluations_coalesce(self):
        from jev_harness.gates import should_abort_trajectory

        payload = {
            "model": "m",
            "answers": {
                "dead_end": {"type": "noul", "noul": 0.9},
                "action": {"type": "choice", "choice": "abort_and_ask", "confidence": 0.9},
                "viability": {"type": "score", "score": 1.0, "confidence": 0.9},
            },
            "usage": {"input_tokens": 1, "output_tokens": 1},
        }
        calls = {"n": 0}

        def _open(req, timeout):
            calls["n"] += 1
            return _FakeResponse(payload)

        client = self._live_gate_client()
        with patch.object(client_mod, "_urlopen_with_ipv4_fallback", _open):
            first = should_abort_trajectory("Try the same fix again", "identical failure three times", client=client)
            second = should_abort_trajectory("Try the same fix again", "identical failure three times", client=client)
        self.assertEqual(calls["n"], 1)
        self.assertFalse(first.debounced)
        self.assertTrue(second.debounced)

    def test_other_gates_are_not_debounced(self):
        from jev_harness.gates import triage_test_failure

        payload = {
            "model": "m",
            "answers": {
                "category": {"type": "choice", "choice": "deep_logic", "confidence": 0.9},
                "skip_llm": {"type": "noul", "noul": 0.1},
                "severity": {"type": "score", "score": 2.0, "confidence": 0.9},
            },
            "usage": {"input_tokens": 1, "output_tokens": 1},
        }
        calls = {"n": 0}

        def _open(req, timeout):
            calls["n"] += 1
            return _FakeResponse(payload)

        client = self._live_gate_client()
        with patch.object(client_mod, "_urlopen_with_ipv4_fallback", _open):
            triage_test_failure("AssertionError: 1 != 2", client=client)
            triage_test_failure("AssertionError: 1 != 2", client=client)
        self.assertEqual(calls["n"], 1, "the TTL cache still serves it, but it is not a debounce")
        self.assertEqual(stats()["debounced"], 0)


class TestCorruptedStateIsSurvivable(CacheTestCase):
    """A damaged state file must never turn `metrics`/`doctor` into a traceback."""

    def _corrupt(self, payload):
        state_dir = self.root / ".config" / "jev"
        state_dir.mkdir(parents=True, exist_ok=True)
        (state_dir / "cache.json").write_text(json.dumps(payload), encoding="utf-8")

    def test_bogus_field_types_do_not_raise(self):
        self._corrupt(
            {
                "entries": {"k": {"stored_at": "boom", "ttl_seconds": None, "payload": {}}},
                "hits": "x",
                "misses": None,
                "debounced": [],
            }
        )
        report = stats(prune=True)
        self.assertEqual(report["entries"], 0)
        self.assertEqual(report["hits"], 0)
        self.assertIsNone(get("triage", "log", "m", "typesafe", False)[0])

    def test_garbage_file_is_ignored(self):
        state_dir = self.root / ".config" / "jev"
        state_dir.mkdir(parents=True, exist_ok=True)
        (state_dir / "cache.json").write_text("not json at all", encoding="utf-8")
        self.assertEqual(stats()["entries"], 0)

    def test_metrics_and_doctor_survive_a_corrupted_cache(self):
        self._corrupt({"entries": {"k": {"stored_at": {"nested": 1}}}, "hits": "x"})
        import jev_harness.cli as cli

        for argv in (["metrics", "--json"], ["doctor", "--json", "--no-git"]):
            with self.subTest(argv[0]):
                out, err = io.StringIO(), io.StringIO()
                with patch.object(sys, "argv", ["jev-harness"] + argv):
                    with patch("sys.stdout", out), patch("sys.stderr", err):
                        with self.assertRaises(SystemExit) as cm:
                            cli.main()
                self.assertNotIn("Traceback", err.getvalue())
                self.assertIn(cm.exception.code, (0, 1))
                json.loads(out.getvalue())
