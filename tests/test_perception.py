"""E3.5 / E3.8 — perception: the judge gets the precise signal, and never a secret.

Two obligations are tested here: the focused slice must carry the failure line (measured over the
shared corpus, ≥90%), and no credential-shaped string may leave the process in the state.
"""
import json
import sys
import unittest
from pathlib import Path

_PKG_ROOT = str(Path(__file__).resolve().parents[1] / "src")
if _PKG_ROOT not in sys.path:
    sys.path.insert(0, _PKG_ROOT)

from jev_harness.gates import triage_test_failure
from jev_harness.client import JevClient
from jev_harness.perception import (
    PERCEPTION_FIELDS,
    find_assertion_line,
    perception_fields,
    redact_secrets,
    slice_contains_assertion,
    slice_failure,
)
from jev_harness.state import build_state, render_state_text

CORPUS = Path(__file__).resolve().parent / "corpus" / "triage.jsonl"

SECRETS = {
    "api_key_pair": 'api_key = "vck_live_9f8a7b6c5d4e3f2a1b0c"',
    "env_style": "TYPESAFE_API_KEY=sk-abcdefghijklmnopqrstuvwxyz012345",
    "bearer": 'Authorization: Bearer eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxIn0.abcdefghijklmnop',
    "github": "token ghp_" + "A" * 24,
    "aws": "AKIAIOSFODNN7EXAMPLE",
    "db_url": "postgres://admin:hunter2@db.internal:5432/app",
    "private_key": "-----BEGIN RSA PRIVATE KEY-----\nMIIEowIBAAKCAQEA\n-----END RSA PRIVATE KEY-----",
    "password_pair": "password: hunter2secret",
}


class TestRedaction(unittest.TestCase):
    def test_every_secret_shape_is_masked(self):
        for name, text in SECRETS.items():
            with self.subTest(name):
                cleaned = redact_secrets(text)
                self.assertIn("[REDACTED", cleaned, name)
                for fragment in ("vck_live_9f8a7b6c5d4e3f2a1b0c", "abcdefghijklmnopqrstuvwxyz012345",
                                 "ghp_" + "A" * 24, "AKIAIOSFODNN7EXAMPLE", "hunter2", "MIIEowIBAAKCAQEA"):
                    self.assertNotIn(fragment, cleaned, name)

    def test_ordinary_log_text_is_untouched(self):
        log = "AssertionError: assert 4 == 5\nFAILED tests/test_math.py::test_add"
        self.assertEqual(redact_secrets(log), log)

    def test_a_log_with_a_secret_still_triages(self):
        result = triage_test_failure(
            "AssertionError: assert 4 == 5\napi_key = vck_live_9f8a7b6c5d4e3f2a1b0c",
            client=JevClient(force_mock=True),
        )
        self.assertEqual(result.category, "deep_logic")

    def test_the_state_sent_never_contains_the_secret(self):
        """The epic's guarantee: redaction covers the payload, not only error messages."""
        captured = {}

        class Spy(JevClient):
            def system_one(self, state, questions, model=None, gate="system_one"):  # type: ignore[override]
                captured["state"] = json.dumps(state) if not isinstance(state, str) else state
                return super().system_one(state, questions, model, gate)

        triage_test_failure(
            "AssertionError: assert 1 == 2\npassword: hunter2secret\nvck_live_9f8a7b6c5d4e3f2a1b0c",
            client=Spy(force_mock=True),
        )
        self.assertIn("AssertionError", captured["state"])
        self.assertNotIn("hunter2secret", captured["state"])
        self.assertNotIn("vck_live", captured["state"])


class TestFocusedSlice(unittest.TestCase):
    def test_slice_centers_on_the_assertion(self):
        log = "\n".join(
            ["collecting tests..."] + [f"noise line {i}" for i in range(40)]
            + ["AssertionError: assert 42 == 41", "FAILED tests/test_cart.py::test_total"]
            + [f"trailing {i}" for i in range(40)]
        )
        fields = slice_failure(log)
        self.assertIn("AssertionError: assert 42 == 41", fields["focused_slice"])
        self.assertLessEqual(len(fields["focused_slice"].splitlines()), 15)
        # The causal context is what came *before* the slice: the setup that produced the failure.
        self.assertIn("noise line 32", fields["causal_context"])
        self.assertTrue(fields["raw_log_ref"])

    def test_no_anchor_means_no_slice(self):
        self.assertEqual(slice_failure("collecting...\nall good\n"), {})
        self.assertEqual(slice_failure(""), {})

    def test_provider_fields_do_not_change_the_offline_verdict(self):
        """The offline engine must keep scoring the log, not the perception metadata."""
        fields = perception_fields("AssertionError: assert 4 == 5\nFAILED tests/x.py::test_y")
        state_with = build_state(failure_log="AssertionError: 4 != 5", **fields)
        state_without = build_state(failure_log="AssertionError: 4 != 5")
        self.assertNotEqual(state_with, state_without)
        self.assertEqual(render_state_text(state_with), render_state_text(state_without))

    def test_perception_field_names_are_the_documented_contract(self):
        self.assertEqual(set(PERCEPTION_FIELDS), {"focused_slice", "causal_context", "raw_log_ref"})


class TestSliceCorpusCoverage(unittest.TestCase):
    """The E1.2 measurement: the slice must carry the failure line in ≥90% of the corpus."""

    def test_slice_carries_the_assertion_across_the_corpus(self):
        cases = [
            json.loads(line)
            for line in CORPUS.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        with_anchor = 0
        carried = 0
        for case in cases:
            log = case["input"]["log"]
            if not find_assertion_line(log):
                continue
            with_anchor += 1
            if slice_contains_assertion(slice_failure(log).get("focused_slice", "")):
                carried += 1
        self.assertGreaterEqual(with_anchor, 40, "the corpus must exercise the slicer")
        self.assertGreaterEqual(
            carried / with_anchor, 0.90, f"slice kept the assertion in {carried}/{with_anchor} cases"
        )


if __name__ == "__main__":
    unittest.main()
