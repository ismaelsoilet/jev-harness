"""
Comprehensive real-world traceback test suite for Jev System One.
Tests multi-language tracebacks from production environments:
Python, Node/TypeScript, Rust/Cargo, and Go.
"""

from pathlib import Path
import sys
import unittest

_PKG_ROOT = str(Path(__file__).resolve().parents[1] / "src")
if _PKG_ROOT not in sys.path:
    sys.path.insert(0, _PKG_ROOT)

from jev_harness.client import JevClient
from jev_harness.gates import triage_test_failure


class TestRealTracebacks(unittest.TestCase):
    def setUp(self):
        self.client = JevClient(force_mock=True)

    # --- PYTHON TRACEBACKS ---
    def test_python_missing_module(self):
        trace = """
        Traceback (most recent call last):
          File "/app/server.py", line 4, in <module>
            import pydantic
        ModuleNotFoundError: No module named 'pydantic'
        """
        res = triage_test_failure(trace, client=self.client)
        self.assertEqual(res.category, "env_missing")
        self.assertTrue(res.skip_llm)
        self.assertIn("AUTO-ACTION", res.action_recommendation)

    def test_python_flaky_timeout(self):
        trace = """
        Traceback (most recent call last):
          File "/app/test_api.py", line 45, in test_remote_fetch
            urllib.request.urlopen("https://api.internal:8443/health", timeout=2)
        TimeoutError: [Errno 110] Connection timed out
        """
        res = triage_test_failure(trace, client=self.client)
        self.assertEqual(res.category, "flaky_transient")
        self.assertTrue(res.skip_llm)

    def test_python_logic_assertion(self):
        trace = """
        FAILED tests/test_auth.py::test_login_flow - AssertionError: assert user.is_active is True
        where False = user.is_active
        > assert user.is_active is True
        E AssertionError: assert False is True
        """
        res = triage_test_failure(trace, client=self.client)
        self.assertEqual(res.category, "deep_logic")
        self.assertFalse(res.skip_llm)
        self.assertIn("ESCALATE", res.action_recommendation)

    # --- NODE & TYPESCRIPT TRACEBACKS ---
    def test_nodejs_missing_module(self):
        trace = """
        node:internal/modules/cjs/loader:1147
          throw err;
          ^
        Error: Cannot find module 'express'
        Require stack:
        - /var/www/app/index.js
            at Module._resolveFilename (node:internal/modules/cjs/loader:1144:15)
        code: 'MODULE_NOT_FOUND'
        """
        res = triage_test_failure(trace, client=self.client)
        self.assertEqual(res.category, "env_missing")
        self.assertTrue(res.skip_llm)

    def test_typescript_ts2307(self):
        trace = """
        src/components/AiView.vue:3:26 - error TS2307: Cannot find module '@types/node' or its corresponding type declarations.
        3 import { Buffer } from 'buffer';
                                 ~~~~~~~~
        Found 1 error in src/components/AiView.vue:3
        """
        res = triage_test_failure(trace, client=self.client)
        self.assertEqual(res.category, "env_missing")
        self.assertTrue(res.skip_llm)

    def test_nodejs_econnreset(self):
        trace = """
        FetchError: request to http://localhost:5173 failed, reason: connect ECONNREFUSED 127.0.0.1:5173
            at ClientRequest.<anonymous> (/var/app/node_modules/node-fetch/lib/index.js:1491:11)
            at ClientRequest.emit (node:events:517:28)
            at Socket.socketErrorListener (node:_http_client:501:9)
        errno: 'ECONNREFUSED',
        code: 'ECONNREFUSED'
        """
        res = triage_test_failure(trace, client=self.client)
        self.assertEqual(res.category, "flaky_transient")
        self.assertTrue(res.skip_llm)

    # --- RUST & CARGO TRACEBACKS ---
    def test_rust_cant_find_crate(self):
        trace = """
        error[E0463]: can't find crate for 'tokio'
         --> src/main.rs:1:1
          |
        1 | extern crate tokio;
          | ^^^^^^^^^^^^^^^^^^^ can't find crate
        error: aborting due to 1 previous error
        """
        res = triage_test_failure(trace, client=self.client)
        self.assertEqual(res.category, "env_missing")
        self.assertTrue(res.skip_llm)

    def test_rust_panic(self):
        trace = """
        running 1 test
        test tests::test_bounds ... FAILED
        failures:
        ---- tests::test_bounds stdout ----
        thread 'tests::test_bounds' panicked at 'index out of bounds: the len is 3 but the index is 4', src/lib.rs:22:9
        note: run with `RUST_BACKTRACE=1` environment variable to display a backtrace
        """
        res = triage_test_failure(trace, client=self.client)
        self.assertEqual(res.category, "deep_logic")
        self.assertFalse(res.skip_llm)

    # --- GO TRACEBACKS ---
    def test_go_package_not_found(self):
        trace = """
        main.go:4:8: cannot find package "github.com/gin-gonic/gin" in any of:
            /usr/local/go/src/github.com/gin-gonic/gin (from $GOROOT)
            /home/dev/go/src/github.com/gin-gonic/gin (from $GOPATH)
        """
        res = triage_test_failure(trace, client=self.client)
        self.assertEqual(res.category, "env_missing")
        self.assertTrue(res.skip_llm)

    def test_go_deadlock(self):
        trace = """
        fatal error: all goroutines are asleep - deadlock!
        goroutine 1 [chan receive]:
        main.main()
            /app/concurrency.go:19 +0x65
        exit status 2
        """
        res = triage_test_failure(trace, client=self.client)
        self.assertEqual(res.category, "deep_logic")
        self.assertFalse(res.skip_llm)

    # --- LARGE PAYLOAD EDGE CASE ---
    def test_large_traceback_truncation(self):
        # 30,000 characters of repeating noise with a critical error at the tail
        huge_trace = ("Noise log line: process memory 42MB OK\n" * 600) + "ModuleNotFoundError: No module named 'scipy'\n"
        self.assertGreater(len(huge_trace), 20000)
        res = triage_test_failure(huge_trace, client=self.client)
        self.assertEqual(res.category, "env_missing")
        self.assertTrue(res.skip_llm)


if __name__ == "__main__":
    unittest.main()
