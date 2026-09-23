"""E1.3 / E3.8 — decision receipts (audit trail) and the retention/privacy rules around them.

The trail must be useful for audit and useless for leaking: hashes and metadata only, 0600,
bounded in age and size, and never able to break a decision.
"""
import io
import json
import os
import stat
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import patch

_PKG_ROOT = str(Path(__file__).resolve().parents[1] / "src")
if _PKG_ROOT not in sys.path:
    sys.path.insert(0, _PKG_ROOT)

from jev_harness.receipts import (
    DEFAULT_MAX_ENTRIES,
    DEFAULT_TTL_DAYS,
    compute_input_hash,
    ensure_state_ignored,
    prune_receipts,
    read_receipts,
    receipts_enabled,
    receipts_path,
    receipts_summary,
    record_receipt,
)

SECRET_LOG = "ModuleNotFoundError: No module named 'requests'\nAPI_KEY=sk-supersecretvalue123"


class ReceiptsTestCase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)
        self._cwd = os.getcwd()
        os.chdir(self.root)
        self.addCleanup(os.chdir, self._cwd)
        self._env = patch.dict(os.environ, {"HOME": str(self.root), "USERPROFILE": str(self.root)})
        self._env.start()
        self.addCleanup(self._env.stop)


class TestInputHash(ReceiptsTestCase):
    def test_same_input_gives_the_same_hash(self):
        first = compute_input_hash("test-gate", SECRET_LOG)
        second = compute_input_hash("test-gate", SECRET_LOG)
        self.assertEqual(first, second)
        self.assertEqual(len(first), 32)

    def test_gate_and_input_both_matter(self):
        self.assertNotEqual(
            compute_input_hash("test-gate", SECRET_LOG), compute_input_hash("verify", SECRET_LOG)
        )
        self.assertNotEqual(
            compute_input_hash("test-gate", SECRET_LOG), compute_input_hash("test-gate", SECRET_LOG + " ")
        )

    def test_hash_never_contains_the_raw_input(self):
        digest = compute_input_hash("test-gate", SECRET_LOG)
        self.assertNotIn("requests", digest)
        self.assertNotIn("sk-supersecretvalue123", digest)


class TestRecording(ReceiptsTestCase):
    def test_a_receipt_carries_metadata_only(self):
        record = record_receipt(
            "test-gate",
            SECRET_LOG,
            "env_missing",
            confidence=0.88,
            model="jev-1.13.0",
            is_mock=True,
            degraded_reason="",
            shadow=False,
        )
        self.assertIsNotNone(record)
        raw = receipts_path().read_text(encoding="utf-8")
        self.assertNotIn("sk-supersecretvalue123", raw, "a receipt must never store raw log content")
        self.assertNotIn("ModuleNotFoundError", raw)
        line = json.loads(raw.strip().splitlines()[-1])
        self.assertEqual(line["gate"], "test-gate")
        self.assertEqual(line["decision"], "env_missing")
        self.assertAlmostEqual(line["confidence"], 0.88)
        self.assertEqual(line["input_hash"], compute_input_hash("test-gate", SECRET_LOG))
        self.assertEqual(set(["ts", "utc", "gate", "input_hash", "decision", "model", "is_mock"]) - set(line), set())

    def test_receipts_are_append_only(self):
        for index in range(3):
            record_receipt("route", f"task {index}", "deterministic")
        lines = [line for line in receipts_path().read_text(encoding="utf-8").splitlines() if line.strip()]
        self.assertEqual(len(lines), 3)
        self.assertEqual([json.loads(l)["decision"] for l in lines], ["deterministic"] * 3)

    def test_disabled_by_env_var(self):
        with patch.dict(os.environ, {"JEV_RECEIPTS": "0"}):
            self.assertFalse(receipts_enabled())
            self.assertIsNone(record_receipt("route", "task", "deterministic"))
        self.assertFalse(receipts_path().exists())

    def test_disabled_by_repo_config(self):
        (self.root / ".jev.json").write_text(json.dumps({"receipts": False}), encoding="utf-8")
        self.assertFalse(receipts_enabled())
        self.assertIsNone(record_receipt("route", "task", "deterministic"))

    def test_file_permissions_are_hardened(self):
        if os.name == "nt":
            self.skipTest("POSIX permissions")
        record_receipt("route", "task", "deterministic")
        mode = stat.S_IMODE(receipts_path().stat().st_mode)
        self.assertEqual(mode, 0o600)
        dir_mode = stat.S_IMODE(receipts_path().parent.stat().st_mode)
        self.assertEqual(dir_mode, 0o700)

    def test_concurrent_writers_do_not_corrupt_the_trail(self):
        def writer(index):
            for step in range(5):
                record_receipt("route", f"task {index}-{step}", "deterministic")

        threads = [threading.Thread(target=writer, args=(i,)) for i in range(6)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        lines = [l for l in receipts_path().read_text(encoding="utf-8").splitlines() if l.strip()]
        self.assertEqual(len(lines), 30)
        for line in lines:
            json.loads(line)  # every line must be intact JSON

    def test_a_failing_write_never_raises(self):
        with patch("pathlib.Path.open", side_effect=OSError("read-only fs")):
            record = record_receipt("route", "task", "deterministic")
        self.assertIsNotNone(record)  # returned, not raised


class TestRetention(ReceiptsTestCase):
    def _seed(self, count, age_days=0.0):
        now = time.time()
        for index in range(count):
            record_receipt("route", f"task {index}", "deterministic")
        path = receipts_path()
        lines = [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]
        for index, record in enumerate(lines):
            record["ts"] = now - age_days * 86400 - index  # all old when age_days > 0
        path.write_text("".join(json.dumps(r) + "\n" for r in lines), encoding="utf-8")
        return path

    def test_ttl_drops_old_receipts(self):
        path = self._seed(5, age_days=10)
        dropped = prune_receipts(ttl_days=1, path=path)
        self.assertEqual(dropped, 5)
        self.assertEqual(read_receipts(path=path), [])

    def test_ttl_keeps_fresh_receipts(self):
        path = self._seed(5, age_days=0)
        dropped = prune_receipts(ttl_days=30, path=path)
        self.assertEqual(dropped, 0)
        self.assertEqual(len(read_receipts(path=path)), 5)

    def test_size_cap_keeps_the_newest(self):
        path = self._seed(10)
        dropped = prune_receipts(ttl_days=0, max_entries=3, path=path)
        self.assertEqual(dropped, 7)
        kept = read_receipts(path=path)
        self.assertEqual(len(kept), 3)
        self.assertEqual(kept[-1]["decision"], "deterministic")

    def test_retention_limits_come_from_config(self):
        (self.root / ".jev.json").write_text(
            json.dumps({"receipts_ttl_days": 5, "receipts_max_entries": 42}), encoding="utf-8"
        )
        summary = receipts_summary()
        self.assertEqual(summary["retention_ttl_days"], 5)
        self.assertEqual(summary["retention_max_entries"], 42)

    def test_defaults_are_documented_values(self):
        summary = receipts_summary()
        self.assertEqual(summary["retention_ttl_days"], DEFAULT_TTL_DAYS)
        self.assertEqual(summary["retention_max_entries"], DEFAULT_MAX_ENTRIES)

    def test_recording_prunes_automatically(self):
        (self.root / ".jev.json").write_text(json.dumps({"receipts_max_entries": 2}), encoding="utf-8")
        for index in range(5):
            record_receipt("route", f"task {index}", "deterministic")
        self.assertEqual(len(read_receipts(path=receipts_path())), 2)


class TestReceiptsCommand(ReceiptsTestCase):
    def _run(self, argv):
        import jev_harness.cli as cli

        out, err = io.StringIO(), io.StringIO()
        with patch.object(sys, "argv", ["jev-harness"] + argv):
            with patch("sys.stdout", out), patch("sys.stderr", err):
                with self.assertRaises(SystemExit) as cm:
                    cli.main()
        return cm.exception.code, out.getvalue(), err.getvalue()

    def test_gates_record_and_the_command_shows_them(self):
        self._run(["test-gate", "--mock", "--sample", SECRET_LOG])
        code, out, _err = self._run(["receipts"])
        self.assertEqual(code, 0)
        self.assertIn("test-gate", out)
        self.assertIn("env_missing", out)
        self.assertNotIn("supersecretvalue", out)

    def test_no_receipts_flag_suppresses_the_trail(self):
        self._run(["test-gate", "--mock", "--no-receipts", "--sample", SECRET_LOG])
        self.assertFalse(receipts_path().exists() and receipts_path().read_text(encoding="utf-8").strip())

    def test_json_output_is_machine_readable(self):
        self._run(["route", "--mock", "--task", "Fix a typo in a docstring"])
        code, out, _err = self._run(["receipts", "--json"])
        self.assertEqual(code, 0)
        payload = json.loads(out)
        self.assertEqual(payload["summary"]["total"], 1)
        self.assertEqual(payload["receipts"][0]["gate"], "route")

    def test_shadow_decisions_are_flagged_in_the_receipt(self):
        self._run(["test-gate", "--mock", "--shadow", "--sample", "AssertionError: assert 1 == 2"])
        code, out, _err = self._run(["receipts", "--json"])
        self.assertEqual(code, 0)
        record = json.loads(out)["receipts"][0]
        self.assertTrue(record["shadow"])
        self.assertEqual(record["decision"], "deep_logic")

    def test_empty_trail_is_a_clean_exit(self):
        code, out, _err = self._run(["receipts"])
        self.assertEqual(code, 0)
        self.assertIn("No receipts recorded yet", out)


class TestGitignoreHygiene(ReceiptsTestCase):
    def test_creates_gitignore_when_absent(self):
        self.assertEqual(ensure_state_ignored(self.root), ".jev/")
        self.assertIn(".jev/", (self.root / ".gitignore").read_text(encoding="utf-8"))

    def test_appends_without_clobbering_existing_rules(self):
        (self.root / ".gitignore").write_text("node_modules/\n*.log\n", encoding="utf-8")
        self.assertEqual(ensure_state_ignored(self.root), ".jev/")
        content = (self.root / ".gitignore").read_text(encoding="utf-8")
        self.assertIn("node_modules/", content)
        self.assertIn("*.log", content)
        self.assertIn(".jev/", content)

    def test_is_idempotent_and_accepts_existing_variants(self):
        for existing in (".jev/\n", ".jev\n", "/.jev/\n", "node_modules/\n/ .jev/\n".replace("/ ", "/")):
            with self.subTest(existing):
                (self.root / ".gitignore").write_text(existing, encoding="utf-8")
                self.assertIsNone(ensure_state_ignored(self.root))

    def test_missing_trailing_newline_is_handled(self):
        (self.root / ".gitignore").write_text("node_modules/", encoding="utf-8")
        self.assertEqual(ensure_state_ignored(self.root), ".jev/")
        content = (self.root / ".gitignore").read_text(encoding="utf-8")
        self.assertIn("node_modules/\n", content)
        self.assertTrue(content.endswith(".jev/\n"))


if __name__ == "__main__":
    unittest.main()
