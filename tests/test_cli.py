"""
Tests for CLI interface and exit code conventions.
"""

import io
from io import StringIO
import json
import os
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

_PKG_ROOT = str(Path(__file__).resolve().parents[1] / "src")
if _PKG_ROOT not in sys.path:
    sys.path.insert(0, _PKG_ROOT)

from jev_harness import __version__
from jev_harness.cli import main


class TestCLI(unittest.TestCase):
    def test_cli_status(self):
        with patch.object(sys, "argv", ["jev-harness", "status"]):
            with patch("sys.stdout", new_callable=StringIO) as out:
                with self.assertRaises(SystemExit) as cm:
                    main()
                self.assertEqual(cm.exception.code, 0)
                self.assertIn("JEV HARNESS STATUS", out.getvalue())

    def test_cli_route_json(self):
        with patch.object(sys, "argv", ["jev-harness", "route", "--task", "Fix typo", "--json", "--mock"]):
            with patch("sys.stdout", new_callable=StringIO) as out:
                with self.assertRaises(SystemExit) as cm:
                    main()
                self.assertEqual(cm.exception.code, 0)
                data = json.loads(out.getvalue())
                self.assertIn("selected_tier", data)
                self.assertEqual(data["selected_tier"], "deterministic")

    def test_cli_test_gate_skip_exit_code(self):
        # env_missing should return 0 (safe to solve deterministically / skip LLM)
        err = "ModuleNotFoundError: No module named 'numpy'"
        with patch.object(sys, "argv", ["jev-harness", "test-gate", "--sample", err, "--mock"]):
            with patch("sys.stdout", new_callable=StringIO):
                with self.assertRaises(SystemExit) as cm:
                    main()
                self.assertEqual(cm.exception.code, 0)

    def test_cli_abort_check_trigger_exit_code(self):
        # circular loop should return 1 (abort recommended)
        with patch.object(
            sys,
            "argv",
            [
                "jev-harness",
                "abort-check",
                "--plan",
                "Tentar pela 4a vez reescrever",
                "--history",
                "Falhou 3 vezes com erro fatal circular",
                "--mock",
            ],
        ):
            with patch("sys.stdout", new_callable=StringIO):
                with self.assertRaises(SystemExit) as cm:
                    main()
                self.assertEqual(cm.exception.code, 1)

    def test_cli_global_flags_before_and_after(self):
        # Flags before subcommand
        with patch.object(sys, "argv", ["jev-harness", "--provider", "opencode", "status"]):
            with patch("sys.stdout", new_callable=StringIO) as out:
                with self.assertRaises(SystemExit) as cm:
                    main()
                self.assertEqual(cm.exception.code, 0)
                self.assertIn("OPENCODE ZEN", out.getvalue())

        # Flags after subcommand
        with patch.object(sys, "argv", ["jev-harness", "status", "--provider", "opencode"]):
            with patch("sys.stdout", new_callable=StringIO) as out:
                with self.assertRaises(SystemExit) as cm:
                    main()
                self.assertEqual(cm.exception.code, 0)
                self.assertIn("OPENCODE ZEN", out.getvalue())

    def test_cli_missing_args(self):
        with patch.object(sys, "argv", ["jev-harness", "test-gate"]):
            with patch("sys.stdin", new=StringIO("")):
                with patch("sys.stderr", new_callable=StringIO):
                    with self.assertRaises(SystemExit) as cm:
                        main()
                    self.assertEqual(cm.exception.code, 2)

    def test_cli_version(self):
        with patch.object(sys, "argv", ["jev-harness", "--version"]):
            with patch("sys.stdout", new_callable=StringIO) as out:
                with self.assertRaises(SystemExit) as cm:
                    main()
                self.assertEqual(cm.exception.code, 0)
                self.assertIn(__version__, out.getvalue())

    def test_cli_reasoning_effort_json(self):
        with patch.object(
            sys,
            "argv",
            [
                "jev-harness",
                "reasoning-effort",
                "--context",
                "git status e diff",
                "--target-provider",
                "deepseek",
                "--json",
                "--mock",
            ],
        ):
            with patch("sys.stdout", new_callable=StringIO) as out:
                with self.assertRaises(SystemExit) as cm:
                    main()
                self.assertEqual(cm.exception.code, 0)
                data = json.loads(out.getvalue())
                self.assertEqual(data["effort"], "low")
                self.assertEqual(data["provider"], "deepseek")
                self.assertIn("extra_body", data["provider_params"])

    def test_cli_reasoning_effort_text(self):
        with patch.object(
            sys,
            "argv",
            [
                "jev-harness",
                "reasoning-effort",
                "--context",
                "Refactor kernel deadlock concurrency",
                "--target-provider",
                "openai",
                "--mock",
            ],
        ):
            with patch("sys.stdout", new_callable=StringIO) as out:
                with self.assertRaises(SystemExit) as cm:
                    main()
                self.assertEqual(cm.exception.code, 0)
                output = out.getvalue()
                self.assertIn("JEV REASONING EFFORT GATE", output)
                self.assertIn("Assigned Effort:   HIGH", output)

    def test_cli_nudge_gate_json(self):
        with patch.object(
            sys,
            "argv",
            [
                "jev-harness",
                "nudge-gate",
                "--transcript",
                "Assistant: Edited src/auth.py. Now I need to run pytest to verify.",
                "--json",
                "--mock",
            ],
        ):
            with patch("sys.stdout", new_callable=StringIO) as out:
                with self.assertRaises(SystemExit) as cm:
                    main()
                self.assertEqual(cm.exception.code, 0)
                data = json.loads(out.getvalue())
                self.assertTrue(data["should_nudge"])
                self.assertEqual(
                    data["workflow_phase"],
                    "verify",
                    "workflow_phase is the canonical documented field name",
                )

    def test_cli_nudge_alias_works(self):
        with patch.object(
            sys,
            "argv",
            [
                "jev-harness",
                "nudge",
                "--transcript",
                "Assistant: Edited src/auth.py. Now I need to run pytest to verify.",
                "--json",
                "--mock",
            ],
        ):
            with patch("sys.stdout", new_callable=StringIO) as out:
                with self.assertRaises(SystemExit) as cm:
                    main()
                self.assertEqual(cm.exception.code, 0)
                data = json.loads(out.getvalue())
                self.assertEqual(data["workflow_phase"], "verify")

    def test_cli_test_gate_green_run_exits_zero_with_no_failure(self):
        with patch.object(sys, "argv", ["jev-harness", "test-gate", "--json", "--mock"]):
            with patch("sys.stdin", io.StringIO("Tests: 12 passed, 12 total\n")):
                with patch("sys.stdout", new_callable=StringIO) as out:
                    with self.assertRaises(SystemExit) as cm:
                        main()
                    self.assertEqual(cm.exception.code, 0)
                    data = json.loads(out.getvalue())
                    self.assertEqual(data["category"], "no_failure")
                    self.assertTrue(data["skip_llm"])

    def test_cli_init_git_generates_runner_aware_hook(self):
        import tempfile
        from pathlib import Path as _Path

        with tempfile.TemporaryDirectory() as tmp:
            cwd = _Path(tmp)
            (cwd / ".git" / "hooks").mkdir(parents=True)
            (cwd / "pyproject.toml").write_text("[tool.pytest.ini_options]\n", encoding="utf-8")
            original = os.getcwd()
            try:
                os.chdir(cwd)
                with patch.object(sys, "argv", ["jev-harness", "init", "--git"]):
                    with patch("sys.stdout", new_callable=StringIO):
                        with self.assertRaises(SystemExit) as cm:
                            main()
                        self.assertEqual(cm.exception.code, 0)
                hook = cwd / ".git" / "hooks" / "pre-commit"
                content = hook.read_text(encoding="utf-8")
                self.assertIn("Jev Harness pre-commit gate", content)
                self.assertIn('TEST_CMD="python3 -m pytest -q"', content)
                self.assertIn("jev-harness test-gate", content)
                self.assertNotIn("python -m unittest 2>&1", content)
                self.assertTrue(os.access(hook, os.X_OK))
            finally:
                os.chdir(original)

    def test_cli_init_git_preserves_existing_hook(self):
        import tempfile
        from pathlib import Path as _Path

        with tempfile.TemporaryDirectory() as tmp:
            cwd = _Path(tmp)
            hooks = cwd / ".git" / "hooks"
            hooks.mkdir(parents=True)
            (hooks / "pre-commit").write_text("#!/bin/sh\necho custom\n", encoding="utf-8")
            original = os.getcwd()
            try:
                os.chdir(cwd)
                with patch.object(sys, "argv", ["jev-harness", "init", "--git"]):
                    with patch("sys.stdout", new_callable=StringIO):
                        with self.assertRaises(SystemExit):
                            main()
                self.assertEqual((hooks / "pre-commit").read_text(encoding="utf-8"), "#!/bin/sh\necho custom\n")
                sample = hooks / "pre-commit.jev"
                self.assertTrue(sample.exists())
                self.assertIn("Jev Harness pre-commit gate", sample.read_text(encoding="utf-8"))
            finally:
                os.chdir(original)

    def test_cli_provider_commandcode_status(self):
        with patch.dict("os.environ", {"CMD_API_KEY": "cmd-test-key"}):
            with patch.object(sys, "argv", ["jev-harness", "--provider", "commandcode", "status"]):
                with patch("sys.stdout", new_callable=StringIO) as out:
                    with self.assertRaises(SystemExit) as cm:
                        main()
                    self.assertEqual(cm.exception.code, 0)
                    self.assertIn("COMMAND CODE", out.getvalue())


if __name__ == "__main__":
    unittest.main()

