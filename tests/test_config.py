"""
Tests for the repository `.jev.json` configuration loader (v0.1.11).

These tests are hermetic: they run inside a temporary working directory so a
developer's `~/.jev.json` can never influence the assertions.
"""

import json
import os
from pathlib import Path
import sys
import tempfile
import unittest

_PKG_ROOT = str(Path(__file__).resolve().parents[1] / "src")
if _PKG_ROOT not in sys.path:
    sys.path.insert(0, _PKG_ROOT)

from jev_harness import JevClient, should_abort_trajectory, triage_test_failure
from jev_harness.config import (
    DEFAULT_ABORT_THRESHOLD,
    DEFAULT_SKIP_LLM_THRESHOLD,
    load_repo_config,
)


class TestRepoConfig(unittest.TestCase):
    def setUp(self):
        self._original_cwd = os.getcwd()
        self._tmp = tempfile.TemporaryDirectory()
        os.chdir(self._tmp.name)
        self.addCleanup(self._restore_cwd)

    def _restore_cwd(self):
        os.chdir(self._original_cwd)
        self._tmp.cleanup()

    def _write_config(self, payload):
        Path(".jev.json").write_text(json.dumps(payload), encoding="utf-8")

    def test_defaults_without_config_file(self):
        cfg = load_repo_config()
        self.assertIsNone(cfg["model"])
        self.assertEqual(cfg["skip_llm_threshold"], DEFAULT_SKIP_LLM_THRESHOLD)
        self.assertEqual(cfg["abort_threshold"], DEFAULT_ABORT_THRESHOLD)

    def test_model_override_is_honored(self):
        self._write_config({"model": "custom-model-7b"})
        self.assertEqual(JevClient(force_mock=True).model, "custom-model-7b")

    def test_scaffold_placeholder_does_not_clobber_provider_defaults(self):
        # `jev-harness init` scaffolds "jev-latest"; provider-mandated IDs must survive it.
        self._write_config({"model": "jev-latest"})
        self.assertEqual(JevClient(force_mock=True).model, "jev-latest")
        self.assertEqual(
            JevClient(force_mock=True, provider="opencode").model, "jev-1.13-free"
        )
        self.assertEqual(
            JevClient(force_mock=True, provider="commandcode").model, "typesafe/jev"
        )

    def test_explicit_argument_beats_repo_config(self):
        self._write_config({"model": "from-config"})
        self.assertEqual(
            JevClient(model="from-argument", force_mock=True).model, "from-argument"
        )

    def test_skip_llm_threshold_is_honored_by_triage_gate(self):
        log = "SyntaxError: expected ';'\nHint: run pip install fast-json"
        default_res = triage_test_failure(log, client=JevClient(force_mock=True))
        self.assertEqual(default_res.category, "syntax_trivial")
        self.assertTrue(default_res.skip_llm, "Default threshold must allow skip_llm")

        self._write_config({"skip_llm_threshold": 0.99})
        strict_res = triage_test_failure(log, client=JevClient(force_mock=True))
        self.assertEqual(strict_res.category, "syntax_trivial")
        self.assertFalse(
            strict_res.skip_llm,
            "A 0.99 threshold must block skip_llm for a 0.95 probability",
        )

    def test_abort_threshold_is_honored_by_abort_gate(self):
        default_res = should_abort_trajectory(
            "Implement the login endpoint",
            "No prior attempts",
            client=JevClient(force_mock=True),
        )
        self.assertFalse(default_res.should_abort)

        self._write_config({"abort_threshold": 0.10})
        strict_res = should_abort_trajectory(
            "Implement the login endpoint",
            "No prior attempts",
            client=JevClient(force_mock=True),
        )
        self.assertTrue(
            strict_res.should_abort,
            "A 0.10 threshold must abort a step scored above it",
        )

    def test_corrupted_config_degrades_to_defaults(self):
        Path(".jev.json").write_text("{ this is not valid json", encoding="utf-8")
        cfg = load_repo_config()
        self.assertIsNone(cfg["model"])
        self.assertEqual(cfg["skip_llm_threshold"], DEFAULT_SKIP_LLM_THRESHOLD)
        self.assertEqual(cfg["abort_threshold"], DEFAULT_ABORT_THRESHOLD)

    def test_thresholds_are_clamped_to_unit_interval(self):
        self._write_config({"skip_llm_threshold": 7.5, "abort_threshold": -3})
        cfg = load_repo_config()
        self.assertEqual(cfg["skip_llm_threshold"], 1.0)
        self.assertEqual(cfg["abort_threshold"], 0.0)

    def test_non_numeric_and_boolean_thresholds_are_ignored(self):
        self._write_config({"skip_llm_threshold": True, "abort_threshold": "high"})
        cfg = load_repo_config()
        self.assertEqual(cfg["skip_llm_threshold"], DEFAULT_SKIP_LLM_THRESHOLD)
        self.assertEqual(cfg["abort_threshold"], DEFAULT_ABORT_THRESHOLD)


if __name__ == "__main__":
    unittest.main()
