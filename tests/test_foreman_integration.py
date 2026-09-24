"""
Foreman integration tests (change `foreman-integration`).

Standard-library only: the suite must pass on a machine without `foreman`/`pydantic`, and the
optional Foreman-side validation reports `skipped` instead of failing. The golden values live in
`tests/fixtures/foreman_cases.json`, shared verbatim with the TypeScript and Rust suites.
"""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from jev_harness.integrations import foreman as F
from jev_harness.integrations import foreman_responsibility as R

REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURE = Path(__file__).parent / "fixtures" / "foreman_cases.json"
PRESET_FIXTURE = Path(__file__).parent / "fixtures" / "foreman_responsibility.toml"

try:
    import tomllib  # Python 3.11+
except ModuleNotFoundError:  # pragma: no cover - Python 3.9/3.10
    tomllib = None

try:  # the optional Foreman-side validation path
    import foreman as _foreman  # noqa: F401

    FOREMAN_AVAILABLE = True
except ImportError:
    FOREMAN_AVAILABLE = False

MISSING_DEPENDENCY_LOG = (
    "============================= test session starts ==============================\n"
    "platform linux -- Python 3.11.9, pytest-8.2.0\n"
    "collected 12 items\n\n"
    "tests/test_api.py::test_retry E\n"
    "==================================== ERRORS ====================================\n"
    "________________________ ERROR at setup of test_retry ________________________\n"
    "E   ModuleNotFoundError: No module named 'requests'\n"
    "=========================== short test summary info ============================\n"
    "ERROR tests/test_api.py::test_retry - ModuleNotFoundError: No module named 'requests'\n"
    "=============================== 1 error in 0.12s ==============================\n"
)


class _Worker(object):
    def __init__(self, stdout="", stderr="", worker_id="worker-1"):
        self.stdout = stdout
        self.stderr = stderr
        self.worker_id = worker_id


class _State(object):
    def __init__(self, iteration, workers, repository="/repo", run_id="run-1"):
        self.iteration = iteration
        self.workers = workers
        self.repository = repository
        self.run_id = run_id


class _Result(object):
    def __init__(self, recovery=0.9, assertion=0.05):
        self.checks = {
            R.RESPONSIBILITY_ID: {
                "deterministic_recovery_available": recovery,
                "assertion_failure_critical": assertion,
            }
        }


def _checks():
    return (
        R._Check(R.RESPONSIBILITY_ID, "deterministic_recovery_available", min_threshold=0.70),
        R._Check(R.RESPONSIBILITY_ID, "assertion_failure_critical", min_threshold=0.75),
    )


def _responsibility(diff_runner, window=5):
    return R.JevTriageResponsibility(checks=_checks(), diff_runner=diff_runner, window=window)


def _fixture():
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


class TestTriageExtraction(unittest.TestCase):
    def test_fixture_triage_cases(self):
        for case in _fixture()["triage_cases"]:
            with self.subTest(case["name"]):
                records = F.ForemanTriageObserver.extract_test_results(case["stdout"], case["stderr"])
                expect = case["expect"]
                self.assertEqual(len(records), expect["records"])
                if not records:
                    continue
                record = records[0]
                self.assertEqual(record["category"], expect["category"])
                self.assertEqual(record["skip_llm"], expect["skip_llm"])
                self.assertEqual(record["action_recommendation"], expect["action_recommendation"])
                self.assertEqual(record["assertion_slice"], expect["assertion_slice"])
                self.assertAlmostEqual(record["severity_score"], expect["severity_score"], places=9)
                self.assertAlmostEqual(record["confidence"], expect["confidence"], places=9)
                self.assertEqual(record["foreman_schema_version"], F.FOREMAN_SCHEMA_VERSION)
                if expect["recovery"] == "python-only":
                    self.assertIsInstance(record["recovery"], dict)
                    self.assertTrue(record["recovery"]["argv"])
                    self.assertFalse(record["recovery"]["is_safe_auto_run"])

    def test_missing_dependency_is_deterministic_and_safe(self):
        record = F.ForemanTriageObserver.extract_test_results(MISSING_DEPENDENCY_LOG)[0]
        self.assertEqual(record["category"], "env_missing")
        self.assertTrue(record["skip_llm"])
        self.assertEqual(record["recovery"]["package_name"], "requests")
        self.assertEqual(record["recovery"]["argv"], ["python", "-m", "pip", "install", "requests"])
        self.assertFalse(record["recovery"]["is_safe_auto_run"])

    def test_no_invented_classification_vocabulary(self):
        vocabulary = {
            "env_missing",
            "flaky_transient",
            "syntax_trivial",
            "test_redundant",
            "deep_logic",
            "no_failure",
        }
        for case in _fixture()["triage_cases"]:
            records = F.ForemanTriageObserver.extract_test_results(case["stdout"], case["stderr"])
            for record in records:
                self.assertIn(record["category"], vocabulary)

    def test_repo_root_changes_the_recovery_rationale(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "requirements.txt").write_text("requests==2.32.0\n", encoding="utf-8")
            scoped = F.ForemanTriageObserver.extract_test_results(
                MISSING_DEPENDENCY_LOG, repo_root=tmp
            )[0]
            unscoped = F.ForemanTriageObserver.extract_test_results(MISSING_DEPENDENCY_LOG)[0]
        self.assertIn("'requests' is declared in this repository's manifests", scoped["recovery"]["rationale"])
        self.assertIn("'requests' is not declared in this repository's manifests/lockfiles", unscoped["recovery"]["rationale"])

    def test_empty_output_returns_no_records(self):
        self.assertEqual(F.ForemanTriageObserver.extract_test_results("", ""), [])


class TestOutputConcatenation(unittest.TestCase):
    """Task 4.2: how stdout and stderr are joined must not change the classification."""

    def test_empty_stderr(self):
        self.assertEqual(F.ForemanTriageObserver.extract_test_results("12 passed in 0.31s", ""), [])

    def test_green_run_with_warning_on_stderr(self):
        records = F.ForemanTriageObserver.extract_test_results(
            "12 passed in 0.31s", "warning: failed to write coverage cache"
        )
        self.assertEqual(records, [])

    def test_traceback_split_across_streams(self):
        head = 'Traceback (most recent call last):\n  File "t.py", line 3, in <module>\n    assert 1 == 2'
        tail = "AssertionError: assert 1 == 2\n1 failed, 0 passed in 0.05s"
        records = F.ForemanTriageObserver.extract_test_results(head, tail)
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["category"], "deep_logic")
        self.assertIn("assert 1 == 2", records[0]["assertion_slice"])


class TestCircuitBreaker(unittest.TestCase):
    def test_fixture_health_cases(self):
        for case in _fixture()["health_cases"]:
            with self.subTest(case["name"]):
                verdict = F.ForemanCircuitBreaker.evaluate_worker_health(
                    case["snapshots"], window=case["window"]
                )
                expect = case["expect"]
                self.assertEqual(verdict["should_abort"], expect["should_abort"])
                self.assertEqual(verdict["reason"], expect["reason"])
                self.assertEqual(verdict["evidence"]["complete_signals"], expect["complete_signals"])
                self.assertEqual(
                    verdict["evidence"]["insufficient_history"], expect["insufficient_history"]
                )
                self.assertEqual(verdict["evidence"]["stagnant_output"], expect["stagnant_output"])
                self.assertEqual(verdict["evidence"]["stagnant_diff"], expect["stagnant_diff"])

    def test_legitimate_fix_and_retry_is_not_a_loop(self):
        same_output = "running pytest -q\ntests/test_api.py E"
        snapshots = [
            {"output": same_output, "diff": "diff --git a/app.py b/app.py\n+old"},
            {"output": same_output, "diff": "diff --git a/app.py b/app.py\n+fixed"},
        ] * 3
        verdict = F.ForemanCircuitBreaker.evaluate_worker_health(snapshots, window=5)
        self.assertFalse(verdict["should_abort"])


class TestResponsibilityPreset(unittest.TestCase):
    def test_fixture_is_the_canonical_preset(self):
        self.assertEqual(
            PRESET_FIXTURE.read_text(encoding="utf-8"), F.FOREMAN_RESPONSIBILITY_TOML
        )

    @unittest.skipIf(tomllib is None, "tomllib requires Python 3.11+")
    def test_preset_parses_with_only_accepted_keys(self):
        parsed = tomllib.loads(F.FOREMAN_RESPONSIBILITY_TOML)
        self.assertTrue(parsed["enabled"])
        self.assertFalse(parsed["always"])
        self.assertIn("routing_instructions", parsed)
        self.assertIn("routing_threshold", parsed)
        self.assertIn("deterministic_recovery_available", parsed["checks"])
        self.assertIn("assertion_failure_critical", parsed["checks"])
        for check in parsed["checks"].values():
            self.assertTrue(check["instructions"].strip())
            self.assertIsInstance(check["min_threshold"], float)
        self.assertEqual(parsed["settings"]["diff_timeout_seconds"], 5)
        self.assertEqual(
            set(parsed) - {"enabled", "always", "routing_instructions", "routing_threshold", "checks", "settings"},
            set(),
        )

    def test_header_states_the_pair_requirement(self):
        self.assertIn("SHIP THE PAIR TOGETHER", F.FOREMAN_RESPONSIBILITY_TOML)
        self.assertIn(
            "installed responsibility has no central configuration: quality.jev-triage",
            F.FOREMAN_RESPONSIBILITY_TOML,
        )
        self.assertIn(
            "configuration has no installed responsibility implementation: quality.jev-triage",
            F.FOREMAN_RESPONSIBILITY_TOML,
        )

    def test_operator_readme_names_both_failure_modes(self):
        self.assertIn("installed responsibility has no central configuration: quality.jev-triage", F.FOREMAN_OPERATOR_README)
        self.assertIn("configuration has no installed responsibility implementation: quality.jev-triage", F.FOREMAN_OPERATOR_README)
        self.assertIn("--responsibilities-dir", F.FOREMAN_OPERATOR_README)


class TestCompanionClass(unittest.TestCase):
    def test_abstains_without_evidence(self):
        responsibility = _responsibility(lambda repository, timeout: "diff")
        self.assertEqual(responsibility.directives(_State(1, []), _Result()), [])
        empty = _State(1, [_Worker(stdout="", stderr="")])
        self.assertEqual(responsibility.directives(empty, _Result()), [])

    def test_abstains_when_the_diff_runner_times_out(self):
        responsibility = _responsibility(lambda repository, timeout: None)
        for iteration in range(1, 7):
            state = _State(iteration, [_Worker(stdout="running tests")])
            self.assertEqual(responsibility.directives(state, _Result()), [])

    def test_proposes_retry_on_stagnation(self):
        responsibility = _responsibility(lambda repository, timeout: "same diff")
        proposals = []
        for iteration in range(1, 7):
            state = _State(iteration, [_Worker(stdout="running tests")])
            proposals = responsibility.directives(state, _Result())
        self.assertEqual(len(proposals), 1)
        proposal = proposals[0]
        self.assertEqual(proposal.action, R.InterventionType.RETRY_WORKER)
        self.assertEqual(proposal.responsibility_id, R.RESPONSIBILITY_ID)
        self.assertEqual(proposal.priority, R.RETRY_PRIORITY)
        self.assertIn(F.STAGNANT_EVIDENCE, proposal.reason)

    def test_same_iteration_is_idempotent(self):
        responsibility = _responsibility(lambda repository, timeout: "same diff")
        for iteration in range(1, 7):
            state = _State(iteration, [_Worker(stdout="running tests")])
            first = responsibility.directives(state, _Result())
        again = responsibility.directives(state, _Result())
        self.assertEqual(
            [(d.action, d.reason, d.priority) for d in first],
            [(d.action, d.reason, d.priority) for d in again],
        )

    @staticmethod
    def _changing_diff():
        calls = {"n": 0}

        def runner(repository, timeout):
            calls["n"] += 1
            return "diff-%d" % calls["n"]

        return runner

    def _fill_window(self, responsibility, stdout=MISSING_DEPENDENCY_LOG, calls=6):
        proposals = []
        for iteration in range(1, calls + 1):
            proposals = responsibility.directives(
                _State(iteration, [_Worker(stdout=stdout)]), _Result()
            )
        return proposals

    def test_environment_recovery_requires_a_complete_window(self):
        """Spec: an incomplete evidence window means no proposal, even for a clear env failure."""
        responsibility = _responsibility(self._changing_diff())
        single = _State(1, [_Worker(stdout=MISSING_DEPENDENCY_LOG)])
        self.assertEqual(responsibility.directives(single, _Result()), [])

    def test_proposes_retry_for_environment_recovery(self):
        responsibility = _responsibility(self._changing_diff())
        proposals = self._fill_window(responsibility)
        self.assertEqual(len(proposals), 1)
        self.assertEqual(proposals[0].action, R.InterventionType.RETRY_WORKER)
        self.assertIn("deterministic recovery available (env_missing)", proposals[0].reason)

    def test_logic_regression_vetoes_the_environment_recovery(self):
        responsibility = _responsibility(self._changing_diff())
        proposals = []
        for iteration in range(1, 7):
            proposals = responsibility.directives(
                _State(iteration, [_Worker(stdout=MISSING_DEPENDENCY_LOG)]), _Result(assertion=0.9)
            )
        self.assertEqual(proposals, [])

    def test_check_gate_blocks_the_proposal(self):
        responsibility = _responsibility(self._changing_diff())
        proposals = []
        for iteration in range(1, 7):
            proposals = responsibility.directives(
                _State(iteration, [_Worker(stdout=MISSING_DEPENDENCY_LOG)]), _Result(recovery=0.5)
            )
        self.assertEqual(proposals, [])

    def test_surface_matches_the_protocol(self):
        responsibility = _responsibility(lambda repository, timeout: "diff").configured_checks(_checks())
        self.assertEqual(responsibility.id, R.RESPONSIBILITY_ID)
        self.assertEqual(R.RESPONSIBILITY_ID, F.FOREMAN_PRESET_FILENAME[: -len(".toml")])
        self.assertTrue(responsibility.checks())
        route = responsibility.route()
        self.assertFalse(route.always)
        self.assertTrue(route.instructions)

    def test_configuration_validation(self):
        responsibility = _responsibility(lambda repository, timeout: "diff")
        configured = responsibility.configured({"diff_timeout_seconds": 2, "window": 4})
        self.assertEqual(configured._diff_timeout_seconds, 2.0)
        self.assertEqual(configured._window_size, 4)
        with self.assertRaises(ValueError):
            responsibility.configured({"not_a_setting": 1})
        with self.assertRaises(ValueError):
            responsibility.configured({"diff_timeout_seconds": 0})
        with self.assertRaises(ValueError):
            responsibility.configured({"window": "many"})


class TestZeroDependencyInvariant(unittest.TestCase):
    def _import_probe(self, module):
        script = (
            "import sys; sys.modules['pydantic'] = None; sys.modules['foreman'] = None;"
            f"import {module} as m; print('ok', getattr(m, 'FOREMAN_SCHEMA_VERSION', 'n/a'))"
        )
        env = {"PYTHONPATH": str(REPO_ROOT / "src"), "PATH": "/usr/bin:/bin"}
        return subprocess.run(
            [sys.executable, "-c", script], capture_output=True, text=True, env=env, cwd=str(REPO_ROOT)
        )

    def test_adapter_imports_without_foreman_or_pydantic(self):
        result = self._import_probe("jev_harness.integrations.foreman")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("ok 1", result.stdout)

    def test_companion_class_imports_without_foreman_or_pydantic(self):
        result = self._import_probe("jev_harness.integrations.foreman_responsibility")
        self.assertEqual(result.returncode, 0, result.stderr)

    @unittest.skipUnless(FOREMAN_AVAILABLE, "foreman is not installed (optional validation path)")
    def test_records_validate_against_foremans_pydantic_model(self):
        from foreman.observation import FactoryObservation  # pragma: no cover

        record = F.ForemanTriageObserver.extract_test_results(MISSING_DEPENDENCY_LOG)[0]
        observation = FactoryObservation(
            original_job="job",
            run_id="run",
            factory_status="running",
            iteration=0,
            active_workers=[],
            worker_history=[],
            latest_worker_output="",
            worker_exit_status={},
            worker_elapsed_seconds={},
            git_status="",
            git_diff="",
            changed_files=[],
            test_results=[record],
            verification_results=[],
            recent_events=[],
            previous_result=None,
            previous_intervention=None,
            attempts=0,
            failures=[],
            elapsed_factory_seconds=0.0,
        )
        self.assertEqual(observation.test_results[0]["category"], "env_missing")


class TestCapabilityMatrix(unittest.TestCase):
    def test_python_record_exposes_the_documented_keys(self):
        matrix = _fixture()["capability_matrix"]
        record = F.ForemanTriageObserver.extract_test_results(MISSING_DEPENDENCY_LOG)[0]
        for key in matrix["python"]:
            self.assertIn(key, record)
        for key in matrix["typescript"]:
            self.assertIn(key, record)

    def test_recovery_divergence_is_declared_not_accidental(self):
        matrix = _fixture()["capability_matrix"]
        self.assertIn("recovery", matrix["python"])
        self.assertNotIn("recovery", matrix["typescript"])
        self.assertNotIn("recovery", matrix["rust"])


class TestExportCommand(unittest.TestCase):
    def _run_export(self, out_dir=None, cwd=None):
        env = {"PYTHONPATH": str(REPO_ROOT / "src"), "PATH": "/usr/bin:/bin"}
        command = [sys.executable, "-m", "jev_harness.cli", "export", "foreman"]
        if out_dir is not None:
            command += ["--out-dir", str(out_dir)]
        return subprocess.run(command, capture_output=True, text=True, env=env, cwd=str(cwd or REPO_ROOT))

    def test_writes_the_three_expected_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = self._run_export(Path(tmp) / "bundle")
            self.assertEqual(result.returncode, 0, result.stderr)
            names = sorted(p.name for p in (Path(tmp) / "bundle").iterdir())
            self.assertEqual(
                names, sorted([F.FOREMAN_PRESET_FILENAME, F.FOREMAN_COMPANION_FILENAME, F.FOREMAN_README_FILENAME])
            )

    def test_re_export_is_byte_identical(self):
        with tempfile.TemporaryDirectory() as tmp:
            bundle = Path(tmp) / "bundle"
            self._run_export(bundle)
            first = {p.name: p.read_bytes() for p in bundle.iterdir()}
            self._run_export(bundle)
            second = {p.name: p.read_bytes() for p in bundle.iterdir()}
            self.assertEqual(first, second)

    def test_default_directory_is_never_run_state(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = self._run_export(cwd=tmp)
            self.assertEqual(result.returncode, 0, result.stderr)
            created = Path(tmp) / F.FOREMAN_DEFAULT_OUT_DIR
            self.assertTrue(created.is_dir())
            self.assertNotIn(".foreman", str(created))

    def test_refuses_to_write_into_run_state(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / ".foreman" / "responsibilities"
            result = self._run_export(target)
            self.assertEqual(result.returncode, 2)
            self.assertIn("refusing to write", result.stderr)
            self.assertFalse(target.exists())

    def test_exported_files_match_the_canonical_constants(self):
        with tempfile.TemporaryDirectory() as tmp:
            bundle = Path(tmp) / "bundle"
            self._run_export(bundle)
            self.assertEqual(
                (bundle / F.FOREMAN_PRESET_FILENAME).read_text(encoding="utf-8"),
                F.FOREMAN_RESPONSIBILITY_TOML,
            )
            self.assertEqual(
                (bundle / F.FOREMAN_README_FILENAME).read_text(encoding="utf-8"),
                F.FOREMAN_OPERATOR_README,
            )
            self.assertEqual(
                (bundle / F.FOREMAN_COMPANION_FILENAME).read_text(encoding="utf-8"),
                Path(R.__file__).read_text(encoding="utf-8"),
            )


@unittest.skipUnless(FOREMAN_AVAILABLE, "foreman is not installed (optional validation path)")
class TestForemanRegistryIntegration(unittest.TestCase):
    """Foreman-side validation against the real `ResponsibilityRegistry`.

    Reported as `skipped` where Foreman is absent (C1). Nothing here mirrors the registry locally:
    a local re-implementation would be a tautological test, which Rule 04 forbids.
    """

    @staticmethod
    def _real_checks():
        from foreman.responsibilities import Check  # pragma: no cover - guarded import

        return (
            Check(
                responsibility_id=R.RESPONSIBILITY_ID,
                check_id="deterministic_recovery_available",
                instructions="deterministic recovery available?",
                min_threshold=0.70,
            ),
            Check(
                responsibility_id=R.RESPONSIBILITY_ID,
                check_id="assertion_failure_critical",
                instructions="genuine logic regression?",
                min_threshold=0.75,
            ),
        )

    def test_registry_rejects_an_empty_checks_sequence(self):
        from foreman.responsibilities import ResponsibilityRegistry

        with self.assertRaises(ValueError) as caught:
            ResponsibilityRegistry([R.JevTriageResponsibility()])
        self.assertIn("has no checks", str(caught.exception))

    def test_registry_rejects_a_mismatched_responsibility_id(self):
        from foreman.models import Directive, InterventionType
        from foreman.responsibilities import ResponsibilityRegistry

        class _WrongId(R.JevTriageResponsibility):
            def directives(self, state, result):
                return [
                    Directive(
                        action=InterventionType.RETRY_WORKER,
                        reason="wrong owner",
                        assessment_iteration=1,
                        responsibility_id="someone-else",
                        priority=10,
                    )
                ]

        registry = ResponsibilityRegistry([_WrongId(checks=self._real_checks())])
        with self.assertRaises(ValueError) as caught:
            registry.directives(_State(1, []), _Result())
        self.assertIn("not 'quality.jev-triage'", str(caught.exception))

    def test_registry_accepts_and_forwards_the_exported_proposal(self):
        from foreman.models import InterventionType
        from foreman.responsibilities import ResponsibilityRegistry

        calls = {"n": 0}

        def runner(repository, timeout):
            calls["n"] += 1
            return "diff-%d" % calls["n"]

        registry = ResponsibilityRegistry(
            [R.JevTriageResponsibility(checks=self._real_checks(), diff_runner=runner)]
        )
        proposals = []
        for iteration in range(1, 7):
            proposals = registry.directives(
                _State(iteration, [_Worker(stdout=MISSING_DEPENDENCY_LOG)]), _Result()
            )
        self.assertEqual(len(proposals), 1)
        self.assertEqual(proposals[0].action, InterventionType.RETRY_WORKER)
        self.assertEqual(proposals[0].responsibility_id, R.RESPONSIBILITY_ID)


if __name__ == "__main__":
    unittest.main()
