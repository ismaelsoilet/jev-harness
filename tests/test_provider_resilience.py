"""E0.2 - provider resilience: retry with backoff, Retry-After, fail-open/fail-closed.

The default is fail-open for gates: a transient provider outage degrades to the
deterministic offline engine and the response is marked (`is_mock=true` +
`degraded_reason`). `--fail-closed` surfaces the error instead (exit 2 in the CLI).
"""
import http.server
import io
import json
import math
import os
import sys
import tempfile
import threading
import time
import unittest
import urllib.error
from unittest.mock import patch

import jev_harness.client as client_mod
from jev_harness.client import MAX_STATE_CHARS, JevClient


SUCCESS_PAYLOAD = {
    "model": "jev-test",
    "answers": {
        "category": {"type": "choice", "choice": "env_missing", "confidence": 0.9},
        "skip_llm": {"type": "noul", "noul": 0.9},
        "severity": {"type": "score", "score": 1.0, "confidence": 0.8},
    },
    "usage": {"input_tokens": 10, "output_tokens": 5},
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


def _http_error(code, retry_after=None):
    headers = {"Retry-After": retry_after} if retry_after is not None else {}
    return urllib.error.HTTPError("http://x", code, "err", headers, None)


def _opener(sequence):
    """Returns an opener that yields `sequence` (exception or payload) per call and a counter."""
    calls = {"n": 0}

    def _open(req, timeout):
        i = calls["n"]
        calls["n"] += 1
        item = sequence[min(i, len(sequence) - 1)]
        if isinstance(item, Exception):
            raise item
        return _FakeResponse(item)

    return _open, calls


def _client(**kwargs):
    kwargs.setdefault("retry_base_delay", 0.0)
    kwargs.setdefault("max_retries", 3)
    return JevClient(provider="typesafe", api_key="test-key", **kwargs)


class TestProviderResilience(unittest.TestCase):
    def setUp(self):
        # State (session/receipts/cache) must never leak into the developer's real HOME.
        self._state = tempfile.TemporaryDirectory()
        self.addCleanup(self._state.cleanup)
        self._env = patch.dict(
            os.environ, {"HOME": self._state.name, "USERPROFILE": self._state.name}
        )
        self._env.start()
        self.addCleanup(self._env.stop)

    def _run(self, sequence, client=None, questions=None):
        client = client or _client()
        opener, calls = _opener(sequence)
        questions = questions or {
            "category": client_mod.ChoiceQuestion(instructions="c", criteria={"env_missing": "x", "deep_logic": "y"})
        }
        with patch.object(client_mod, "_urlopen_with_ipv4_fallback", opener):
            resp = client.system_one("state", questions)
        return resp, calls["n"]

    def test_429_then_success_retries_and_stays_live(self):
        resp, attempts = self._run([_http_error(429), SUCCESS_PAYLOAD])
        self.assertEqual(attempts, 2)
        self.assertFalse(resp.is_mock)
        self.assertEqual(resp.degraded_reason, "")

    def test_retry_after_header_is_honored_via_delay_helper(self):
        client = _client()
        self.assertEqual(client._retry_delay(1, "2"), 2.0)
        self.assertEqual(client._retry_delay(1, "not-a-number"), 0.0)
        self.assertEqual(client._retry_delay(3), 0.0)  # base delay 0 in tests

    def test_repeated_429_falls_back_and_is_marked(self):
        resp, attempts = self._run([_http_error(429)])
        self.assertEqual(attempts, 3)
        self.assertTrue(resp.is_mock)
        self.assertEqual(resp.degraded_reason, "http_429")

    def test_5xx_falls_back_by_default(self):
        resp, attempts = self._run([_http_error(503)])
        self.assertEqual(attempts, 3)
        self.assertTrue(resp.is_mock)
        self.assertEqual(resp.degraded_reason, "http_503")

    def test_timeout_falls_back_and_is_marked(self):
        resp, attempts = self._run([TimeoutError("timed out")])
        self.assertEqual(attempts, 3)
        self.assertTrue(resp.is_mock)
        self.assertEqual(resp.degraded_reason, "timeout")

    def test_connection_error_falls_back_and_is_marked(self):
        err = urllib.error.URLError("refused")
        resp, attempts = self._run([err])
        self.assertEqual(attempts, 3)
        self.assertTrue(resp.is_mock)
        self.assertEqual(resp.degraded_reason, "connection")

    def test_401_falls_back_immediately_without_retry(self):
        resp, attempts = self._run([_http_error(401)])
        self.assertEqual(attempts, 1)
        self.assertTrue(resp.is_mock)
        self.assertEqual(resp.degraded_reason, "auth_401")

    def test_fail_closed_raises_on_exhausted_retries(self):
        client = _client(fail_open=False)
        with self.assertRaises(RuntimeError):
            self._run([_http_error(500)], client=client)

    def test_fail_closed_raises_on_timeout(self):
        client = _client(fail_open=False)
        with self.assertRaises(RuntimeError):
            self._run([TimeoutError("timed out")], client=client)

    def test_cli_fail_open_returns_gate_exit_without_traceback(self):
        import jev_harness.cli as cli
        opener, _calls = _opener([_http_error(429)])
        with patch.dict(os.environ, {"TYPESAFE_API_KEY": "test-key"}):
            with patch.object(client_mod, "_urlopen_with_ipv4_fallback", opener):
                with patch.object(sys, "argv", ["jev-harness", "test-gate", "--sample", "ModuleNotFoundError: No module named x"]):
                    with patch("sys.stdout", new_callable=io.StringIO):
                        with self.assertRaises(SystemExit) as cm:
                            cli.main()
        self.assertEqual(cm.exception.code, 0)  # env_missing is deterministic even offline

    def test_cli_fail_closed_exits_two_without_traceback(self):
        import jev_harness.cli as cli
        opener, _calls = _opener([_http_error(500)])
        stderr = io.StringIO()
        with patch.dict(os.environ, {"TYPESAFE_API_KEY": "test-key"}):
            with patch.object(client_mod, "_urlopen_with_ipv4_fallback", opener):
                with patch.object(
                    sys,
                    "argv",
                    ["jev-harness", "test-gate", "--fail-closed", "--sample", "ModuleNotFoundError: No module named x"],
                ):
                    with patch("sys.stdout", new_callable=io.StringIO):
                        with patch("sys.stderr", stderr):
                            with self.assertRaises(SystemExit) as cm:
                                cli.main()
        self.assertEqual(cm.exception.code, 2)
        self.assertIn("Error:", stderr.getvalue())


class TestMalformedProviderResponses(unittest.TestCase):
    """E0.2: a 200 carrying type-mismatched fields is a parse failure, never a traceback."""

    def setUp(self):
        self._state = tempfile.TemporaryDirectory()
        self.addCleanup(self._state.cleanup)
        self._env = patch.dict(
            os.environ, {"HOME": self._state.name, "USERPROFILE": self._state.name}
        )
        self._env.start()
        self.addCleanup(self._env.stop)

    def _payload(self, **answers):
        return {
            "model": "jev-test",
            "answers": answers,
            "usage": {"input_tokens": 1, "output_tokens": 1},
        }

    def _run(self, payload, client=None):
        client = client or _client(max_retries=1)
        opener, calls = _opener([payload])
        with patch.object(client_mod, "_urlopen_with_ipv4_fallback", opener):
            resp = client.system_one(
                "state",
                {"q": client_mod.NoulQuestion("x")},
            )
        return resp, calls["n"]

    def test_non_numeric_score_degrades_and_is_marked(self):
        resp, attempts = self._run(self._payload(severity={"type": "score", "score": "N/A", "confidence": 0.5}))
        self.assertEqual(attempts, 1)
        self.assertTrue(resp.is_mock)
        self.assertEqual(resp.degraded_reason, "invalid_response")

    def test_type_mismatches_never_crash(self):
        cases = {
            "score null": self._payload(severity={"type": "score", "score": None, "confidence": 0.5}),
            "confidence list": self._payload(severity={"type": "score", "score": 1.0, "confidence": []}),
            "answers not an object": {"model": "x", "answers": [{"type": "score"}], "usage": {}},
            "usage not an object": {"model": "x", "answers": {}, "usage": "n/a"},
            "noul string": self._payload(skip_llm={"type": "noul", "noul": "high"}),
        }
        for label, payload in cases.items():
            with self.subTest(label):
                resp, _attempts = self._run(payload)
                self.assertTrue(resp.is_mock, label)

    def test_retry_after_supports_fractional_seconds_in_all_runtimes(self):
        # Rust previously parsed only integers; the three runtimes must agree.
        client = _client()
        self.assertEqual(client._retry_delay(1, "1.5"), 1.5)
        self.assertEqual(client._retry_delay(1, "0.25"), 0.25)
        self.assertEqual(client._retry_delay(1, "999"), 30.0)  # capped
        self.assertEqual(client._retry_delay(1, "-1"), 0.0)  # meaningless: falls back to backoff
        self.assertEqual(client._retry_delay(1, "nonsense"), 0.0)
        slow = JevClient(provider="typesafe", api_key="k", retry_base_delay=0.5)
        self.assertEqual(slow._retry_delay(1, "-1"), 0.5)  # base delay * 2^0

    def test_openrouter_chat_path_respects_the_failure_policy(self):
        def chat_client(fail_open=True):
            client = JevClient(
                provider="openrouter",
                api_key="k",
                base_url="https://openrouter.ai/api/v1/chat/completions",
                fail_open=fail_open,
            )
            return client

        with patch.object(client_mod, "_urlopen_with_ipv4_fallback", side_effect=urllib.error.URLError("down")):
            resp = chat_client().system_one("state", {"q": client_mod.NoulQuestion("x")})
        self.assertTrue(resp.is_mock)
        self.assertEqual(resp.degraded_reason, "invalid_response")

        with patch.object(client_mod, "_urlopen_with_ipv4_fallback", side_effect=urllib.error.URLError("down")):
            with self.assertRaises(RuntimeError):
                chat_client(fail_open=False).system_one("state", {"q": client_mod.NoulQuestion("x")})

    def test_fail_closed_raises_on_malformed_payload(self):
        client = _client(fail_open=False, max_retries=1)
        with self.assertRaises(RuntimeError) as ctx:
            self._run(self._payload(severity={"type": "score", "score": "N/A", "confidence": 0.5}), client=client)
        self.assertIn("malformed", str(ctx.exception))

    def test_malformed_response_is_retried_before_degrading(self):
        payload = self._payload(severity={"type": "score", "score": "N/A", "confidence": 0.5})
        opener, calls = _opener([payload])
        client = _client(max_retries=3)
        with patch.object(client_mod, "_urlopen_with_ipv4_fallback", opener):
            resp = client.system_one("state", {"q": client_mod.NoulQuestion("x")})
        self.assertEqual(calls["n"], 3)
        self.assertEqual(resp.degraded_reason, "invalid_response")

    def test_unknown_answer_type_is_malformed_not_dropped(self):
        # A valid answer next to an uninterpretable one must not hide the bad one: the gate
        # would silently use its default score instead of the provider's judgement.
        payload = self._payload(
            category={"type": "choice", "choice": "env_missing", "confidence": 0.98},
            skip_llm={"type": "noul", "noul": 0.9},
            severity={"type": "score_v2", "value": 3},
        )
        resp, _attempts = self._run(payload)
        self.assertTrue(resp.is_mock)
        self.assertEqual(resp.degraded_reason, "invalid_response")

    def test_missing_or_mistyped_required_fields_are_malformed(self):
        cases = {
            "score without score": {"type": "score"},
            "score without confidence": {"type": "score", "score": 1.0},
            "choice without confidence": {"type": "choice", "choice": "x"},
            "choice as a number": {"type": "choice", "choice": 3, "confidence": 0.9},
            "noul without noul": {"type": "noul"},
            "numeric string": {"type": "score", "score": "1.0", "confidence": 0.9},
            "boolean score": {"type": "score", "score": True, "confidence": 0.9},
            "no type": {"score": 1.0, "confidence": 0.5},
            "answer is a string": "boom",
        }
        for label, answer in cases.items():
            with self.subTest(label):
                resp, _attempts = self._run(self._payload(**{"q": answer}))
                self.assertTrue(resp.is_mock, label)
                self.assertEqual(resp.degraded_reason, "invalid_response", label)

    def test_dropped_connection_classes_follow_the_policy(self):
        """RemoteDisconnected/ConnectionResetError are OSErrors and BadStatusLine is an
        HTTPException: all are transport failures, never a traceback."""
        import http.client

        cases = {
            "remote disconnected": http.client.RemoteDisconnected("remote closed"),
            "connection reset": ConnectionResetError("reset by peer"),
            "bad status line": http.client.BadStatusLine("garbage"),
        }
        for label, error in cases.items():
            with self.subTest(label):
                client = _client(retry_base_delay=0.0)
                with patch.object(client_mod, "_urlopen_with_ipv4_fallback", side_effect=error):
                    resp = client.system_one("state", {"q": client_mod.NoulQuestion("x")})
                self.assertTrue(resp.is_mock, label)
                self.assertIn(resp.degraded_reason, ("connection", "timeout", "invalid_response"), label)

                strict = _client(fail_open=False, retry_base_delay=0.0)
                with patch.object(client_mod, "_urlopen_with_ipv4_fallback", side_effect=error):
                    with self.assertRaises(RuntimeError):
                        strict.system_one("state", {"q": client_mod.NoulQuestion("x")})

    def test_non_finite_numbers_are_rejected(self):
        """`json.loads` accepts the non-standard NaN/Infinity literals; TS and Rust do not."""
        for literal in ("NaN", "Infinity", "-Infinity"):
            with self.subTest(literal):
                payload = json.loads(
                    '{"model": "x", "answers": {"q": {"type": "score", "score": %s, "confidence": 0.5}}, "usage": {}}'
                    % literal
                )
                resp, _attempts = self._run(payload)
                self.assertTrue(resp.is_mock, literal)
                self.assertEqual(resp.degraded_reason, "invalid_response", literal)
                for answer in resp.answers.values():
                    value = getattr(answer, "score", getattr(answer, "noul", 0.0))
                    self.assertTrue(math.isfinite(value), f"{literal} leaked a non-finite value")

    def test_cli_never_emits_non_standard_json(self):
        """A NaN score must never reach `--json`: the output has to stay parseable JSON."""
        payload = json.loads(
            '{"model": "x", "answers": {"q": {"type": "score", "score": NaN, "confidence": 0.5}}, "usage": {}}'
        )
        opener, _calls = _opener([payload])
        out = io.StringIO()
        with patch.dict(os.environ, {"TYPESAFE_API_KEY": "test-key"}):
            with patch.object(client_mod, "_urlopen_with_ipv4_fallback", opener):
                with patch.object(
                    sys, "argv", ["jev-harness", "test-gate", "--json", "--sample", "AssertionError: assert 1 == 2"]
                ):
                    with patch("sys.stdout", out), patch("sys.stderr", io.StringIO()):
                        with self.assertRaises(SystemExit):
                            cli_main = __import__("jev_harness.cli", fromlist=["main"]).main
                            cli_main()
        parsed = json.loads(out.getvalue())  # strict JSON: NaN would make this raise
        self.assertEqual(parsed["degraded_reason"], "invalid_response")

    def test_openrouter_chat_path_retries_before_degrading(self):
        client = JevClient(
            provider="openrouter",
            api_key="k",
            base_url="https://openrouter.ai/api/v1/chat/completions",
            retry_base_delay=0.0,
        )
        opener, calls = _opener([urllib.error.URLError("down")])
        with patch.object(client_mod, "_urlopen_with_ipv4_fallback", opener):
            resp = client.system_one("state", {"q": client_mod.NoulQuestion("x")})
        self.assertEqual(calls["n"], 3)  # same attempt budget as the native endpoint
        self.assertEqual(resp.degraded_reason, "invalid_response")

    def test_cli_reports_the_degradation_in_json_and_human_output(self):
        import jev_harness.cli as cli

        payload = self._payload(severity={"type": "score", "score": "N/A", "confidence": 0.5})
        opener, _calls = _opener([payload])
        for extra, expect_json in ((["--json"], True), ([], False)):
            out, err = io.StringIO(), io.StringIO()
            with patch.dict(os.environ, {"TYPESAFE_API_KEY": "test-key"}):
                with patch.object(client_mod, "_urlopen_with_ipv4_fallback", opener):
                    with patch.object(
                        sys,
                        "argv",
                        ["jev-harness", "test-gate", "--sample", "AssertionError: assert 1 == 2"] + extra,
                    ):
                        with patch("sys.stdout", out), patch("sys.stderr", err):
                            with self.assertRaises(SystemExit):
                                cli.main()
            if expect_json:
                self.assertEqual(json.loads(out.getvalue())["degraded_reason"], "invalid_response")
            else:
                self.assertIn("degraded: invalid_response", out.getvalue())
            self.assertNotIn("Traceback", err.getvalue())


class _Handler(http.server.BaseHTTPRequestHandler):
    """Returns the scripted responses, one per request (500/429/200/invalid)."""

    script = []
    seen = []

    def do_POST(self):  # noqa: N802
        length = int(self.headers.get("Content-Length", "0"))
        self.rfile.read(length)
        _Handler.seen.append(self.path)
        code, body, headers = _Handler.script[min(len(_Handler.seen) - 1, len(_Handler.script) - 1)]
        self.send_response(code)
        for key, value in (headers or {}).items():
            self.send_header(key, value)
        payload = body.encode("utf-8")
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, *args):  # silence
        pass


class TestProviderResilienceAgainstRealServer(unittest.TestCase):
    """The IPv4 helper must not double-send requests or bypass Retry-After."""

    def _serve(self, script):
        _Handler.script = script
        _Handler.seen = []
        server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        return server, f"http://127.0.0.1:{server.server_address[1]}/v1/systemone"

    def _client(self, base_url, **kwargs):
        client = JevClient(provider="typesafe", api_key="test-key", **kwargs)
        client.base_url = base_url
        client.retry_base_delay = float(kwargs.get("retry_base_delay", 0.0))
        return client

    def _questions(self, client):
        return {"q": client_mod.NoulQuestion("is valid?")}

    def test_retry_count_is_exact_and_retry_after_is_honored(self):
        server, url = self._serve([(500, "boom", None), (500, "boom", None), (200, json.dumps(SUCCESS_PAYLOAD), None)])
        try:
            client = self._client(url, retry_base_delay=0.0)
            resp = client.system_one("state", self._questions(client))
            self.assertFalse(resp.is_mock)
            self.assertEqual(len(_Handler.seen), 3)  # exactly max_retries, no hidden double-send
        finally:
            server.shutdown()

    def test_retry_after_seconds_are_honored(self):
        server, url = self._serve([(429, "slow down", {"Retry-After": "1"}), (200, json.dumps(SUCCESS_PAYLOAD), None)])
        try:
            client = self._client(url, retry_base_delay=0.0)
            started = time.monotonic()
            resp = client.system_one("state", self._questions(client))
            elapsed = time.monotonic() - started
            self.assertFalse(resp.is_mock)
            self.assertEqual(len(_Handler.seen), 2)
            self.assertGreaterEqual(elapsed, 0.9)  # Retry-After: 1 honored
        finally:
            server.shutdown()

    def test_invalid_json_body_degrades_marked(self):
        server, url = self._serve([(200, "<html>gateway</html>", None)])
        try:
            client = self._client(url, retry_base_delay=0.0, max_retries=1)
            resp = client.system_one("state", self._questions(client))
            self.assertTrue(resp.is_mock)
            self.assertEqual(resp.degraded_reason, "invalid_response")
        finally:
            server.shutdown()

    def test_fail_closed_raises_on_401(self):
        server, url = self._serve([(401, "unauthorized", None)])
        try:
            client = self._client(url, retry_base_delay=0.0, fail_open=False)
            with self.assertRaises(RuntimeError):
                client.system_one("state", self._questions(client))
            self.assertEqual(len(_Handler.seen), 1)  # auth is never retried
        finally:
            server.shutdown()

    def test_unicode_state_counts_code_points_not_bytes(self):
        # 127_999 code points of "é" is 255_998 UTF-8 bytes: must still be accepted (< 128k code points).
        client = JevClient(provider="typesafe", api_key="k")
        client.base_url = "http://127.0.0.1:9/v1/systemone"
        client.retry_base_delay = 0.0
        client.max_retries = 1
        resp = client.system_one("é" * (MAX_STATE_CHARS - 1), {"q": client_mod.NoulQuestion("x")})
        self.assertTrue(resp.is_mock)  # accepted by the guard, degraded by the dead endpoint


if __name__ == "__main__":
    unittest.main()
