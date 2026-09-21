"""
Tests for CLI interface and exit code conventions.
"""

from io import StringIO
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

_PKG_ROOT = str(Path(__file__).resolve().parents[1] / "src")
if _PKG_ROOT not in sys.path:
    sys.path.insert(0, _PKG_ROOT)

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


if __name__ == "__main__":
    unittest.main()
