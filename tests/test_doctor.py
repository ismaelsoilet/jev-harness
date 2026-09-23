"""E2.4 — `doctor`: a healthy machine reports OK, a broken one reports FALHA plus the fix.

The two properties that matter most: it must never print a secret, and it must never be the
reason a pipeline is red when the tool itself is fine (a missing key is a WARNING, not a failure).
"""
import io
import json
import os
import stat
import subprocess
import sys
import tempfile
import unittest
import urllib.error
from pathlib import Path
from unittest.mock import patch

_PKG_ROOT = str(Path(__file__).resolve().parents[1] / "src")
if _PKG_ROOT not in sys.path:
    sys.path.insert(0, _PKG_ROOT)

import jev_harness.client as client_mod
from jev_harness.doctor import FAIL, OK, WARN, render_console, run_doctor

LIVE_PAYLOAD = {
    "model": "jev-1.13.0",
    "answers": {"probe": {"type": "noul", "noul": 0.9}},
    "usage": {"input_tokens": 12, "output_tokens": 1},
    "cost": "0.0000005",
}

SECRET = "sk-doctor-secret-value-123456"


class _FakeResponse:
    def __init__(self, payload):
        self._body = json.dumps(payload).encode("utf-8")

    def read(self):
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


class DoctorTestCase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)
        self._cwd = os.getcwd()
        os.chdir(self.root)
        self.addCleanup(os.chdir, self._cwd)
        # A clean HOME and no provider env: the doctor must see exactly what we configure.
        self._env = patch.dict(
            os.environ,
            {
                "HOME": str(self.root),
                "USERPROFILE": str(self.root),
                "TYPESAFE_API_KEY": "",
                "CMD_API_KEY": "",
                "COMMAND_CODE_API_KEY": "",
                "OPENCODE_API_KEY": "",
                "OPENROUTER_API_KEY": "",
                "AI_GATEWAY_API_KEY": "",
                "JEV_PROVIDER": "",
            },
        )
        self._env.start()
        self.addCleanup(self._env.stop)

    def _status(self, report, name):
        for check in report.checks:
            if check.name == name:
                return check.status, check.detail, check.fix
        raise AssertionError(f"no check named {name}: {[c.name for c in report.checks]}")

    def _run_cli(self, argv):
        import jev_harness.cli as cli

        out, err = io.StringIO(), io.StringIO()
        with patch.object(sys, "argv", ["jev-harness"] + argv):
            with patch("sys.stdout", out), patch("sys.stderr", err):
                with self.assertRaises(SystemExit) as cm:
                    cli.main()
        return cm.exception.code, out.getvalue(), err.getvalue()


class TestHealthyAndDegraded(DoctorTestCase):
    def test_offline_machine_is_healthy_with_a_warning(self):
        report = run_doctor(cwd=self.root, check_git_hook=False)
        status, detail, _fix = self._status(report, "credentials")
        self.assertEqual(status, WARN)
        self.assertIn("offline", detail)
        self.assertFalse(report.failed, "a missing key must never be a failure")
        self.assertEqual(self._status(report, "version")[0], OK)

    def test_credentials_are_reported_without_the_secret(self):
        with patch.dict(os.environ, {"TYPESAFE_API_KEY": SECRET}):
            report = run_doctor(cwd=self.root, check_git_hook=False)
        rendered = render_console(report) + json.dumps(report.as_dict())
        self.assertNotIn(SECRET, rendered, "doctor must never print a secret")
        status, detail, _fix = self._status(report, "credentials")
        self.assertEqual(status, OK)
        self.assertIn("fingerprint", detail)
        self.assertIn("environment variable", detail)

    def test_corrupted_config_is_a_failure_with_a_fix(self):
        (self.root / ".jev.json").write_text("{ not json", encoding="utf-8")
        report = run_doctor(cwd=self.root, check_git_hook=False)
        status, detail, fix = self._status(report, "config")
        self.assertEqual(status, FAIL)
        self.assertIn("not usable", detail)
        self.assertIn("fix the JSON", fix)
        self.assertTrue(report.failed)

    def test_valid_config_is_reported_with_its_effective_values(self):
        (self.root / ".jev.json").write_text(
            json.dumps({"skip_llm_threshold": 0.5, "shadow": True, "receipts": False}), encoding="utf-8"
        )
        report = run_doctor(cwd=self.root, check_git_hook=False)
        status, detail, _fix = self._status(report, "config")
        self.assertEqual(status, OK)
        self.assertIn("skip_llm_threshold=0.5", detail)
        self.assertIn("shadow=True", detail)
        self.assertIn("receipts=False", detail)

    def test_moving_alias_is_flagged(self):
        with patch.dict(os.environ, {"TYPESAFE_API_KEY": "k"}):
            report = run_doctor(cwd=self.root, check_git_hook=False)
        status, detail, fix = self._status(report, "model_pin")
        self.assertEqual(status, WARN)
        self.assertIn("moving alias", detail)
        self.assertIn("pin a version", fix)

    def test_loose_state_permissions_are_flagged(self):
        if os.name == "nt":
            self.skipTest("POSIX permissions")
        # The repository-local state directory is preferred by the resolver and is never
        # auto-hardened, so it is the one the doctor can actually observe.
        state_dir = self.root / ".jev"
        state_dir.mkdir(parents=True)
        os.chmod(state_dir, 0o755)
        report = run_doctor(cwd=self.root, check_git_hook=False)
        status, detail, fix = self._status(report, "state_dir")
        self.assertEqual(status, WARN)
        self.assertIn("other users can read", detail)
        self.assertIn("chmod 700", fix)

    def test_the_global_state_directory_is_auto_hardened(self):
        if os.name == "nt":
            self.skipTest("POSIX permissions")
        global_dir = self.root / ".config" / "jev"
        global_dir.mkdir(parents=True)
        os.chmod(global_dir, 0o755)
        report = run_doctor(cwd=self.root, check_git_hook=False)
        status, detail, _fix = self._status(report, "state_dir")
        self.assertEqual(status, OK, "the resolver hardens the global state dir on use")
        self.assertIn("0o700", detail)


class TestGitHook(DoctorTestCase):
    def _git_repo(self, hook_content=None):
        subprocess.run(["git", "init", "-q"], cwd=self.root, check=True, capture_output=True)
        hooks = self.root / ".git" / "hooks"
        hooks.mkdir(parents=True, exist_ok=True)
        if hook_content is not None:
            (hooks / "pre-commit").write_text(hook_content, encoding="utf-8")
        return hooks

    def test_outside_a_repository_it_is_not_reported_as_a_problem(self):
        report = run_doctor(cwd=self.root)
        status, detail, _fix = self._status(report, "git_hook")
        self.assertEqual(status, OK)
        self.assertIn("not a git repository", detail)

    def test_missing_hook_warns_with_the_init_command(self):
        self._git_repo()
        report = run_doctor(cwd=self.root)
        status, _detail, fix = self._status(report, "git_hook")
        self.assertEqual(status, WARN)
        self.assertIn("init --git", fix)

    def test_active_hook_is_ok(self):
        hooks = self._git_repo("#!/bin/sh\nev-harness test-gate  # jev-harness gate\n".replace("ev-", "jev-"))
        self.assertTrue((hooks / "pre-commit").is_file())
        report = run_doctor(cwd=self.root)
        self.assertEqual(self._status(report, "git_hook")[0], OK)

    def test_a_preserved_foreign_hook_is_flagged_as_inactive(self):
        hooks = self._git_repo("#!/bin/sh\necho foreign hook\n")
        (hooks / "pre-commit.jev").write_text("#!/bin/sh\njev-harness test-gate\n", encoding="utf-8")
        report = run_doctor(cwd=self.root)
        status, detail, fix = self._status(report, "git_hook")
        self.assertEqual(status, WARN)
        self.assertIn("NOT active", detail)
        self.assertIn("merge", fix)


class TestLiveProbe(DoctorTestCase):
    def test_live_without_credentials_is_a_failure_with_the_fix(self):
        report = run_doctor(cwd=self.root, live=True, check_git_hook=False)
        status, detail, fix = self._status(report, "provider_live")
        self.assertEqual(status, FAIL)
        self.assertIn("--live was requested", detail)
        self.assertIn("export a provider key", fix)

    def test_live_success_reports_latency_and_usage(self):
        with patch.dict(os.environ, {"TYPESAFE_API_KEY": "test-key"}):
            with patch.object(client_mod, "_urlopen_with_ipv4_fallback", lambda req, timeout: _FakeResponse(LIVE_PAYLOAD)):
                report = run_doctor(cwd=self.root, live=True, check_git_hook=False)
        status, detail, _fix = self._status(report, "provider_live")
        self.assertEqual(status, OK)
        self.assertIn("answered in", detail)
        self.assertIn("cost=", detail)
        self.assertIsNotNone(report.live_latency_ms)
        self.assertFalse(report.failed)

    def test_live_degradation_is_a_warning_not_a_failure(self):
        with patch.dict(os.environ, {"TYPESAFE_API_KEY": "test-key"}):
            with patch.object(client_mod, "_urlopen_with_ipv4_fallback", side_effect=urllib.error.URLError("down")):
                report = run_doctor(cwd=self.root, live=True, check_git_hook=False)
        status, detail, _fix = self._status(report, "provider_live")
        self.assertEqual(status, WARN)
        self.assertIn("degraded", detail)
        self.assertFalse(report.failed, "a degraded provider is not a broken installation")


class TestDoctorCli(DoctorTestCase):
    def test_cli_reports_json_and_exit_codes(self):
        code, out, _err = self._run_cli(["doctor", "--json", "--no-git"])
        self.assertEqual(code, 0)
        payload = json.loads(out)
        self.assertIn(payload["status"], (OK, WARN))
        self.assertTrue(any(c["check"] == "config" for c in payload["checks"]))

    def test_cli_exits_one_when_something_is_broken(self):
        (self.root / ".jev.json").write_text("{ broken", encoding="utf-8")
        code, out, _err = self._run_cli(["doctor", "--no-git"])
        self.assertEqual(code, 1)
        self.assertIn("FALHA", out)

    def test_human_output_lists_status_and_fixes(self):
        code, out, _err = self._run_cli(["doctor", "--no-git"])
        self.assertEqual(code, 0)
        self.assertIn("=== JEV HARNESS DOCTOR ===", out)
        self.assertIn("[", out)
        self.assertIn("RESULT:", out)


if __name__ == "__main__":
    unittest.main()
