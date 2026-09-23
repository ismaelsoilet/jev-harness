# Triaging CI failures with the Jev Harness Action (E2.1)

A composite action that turns a failed CI step into a **categorised annotation** with the next
deterministic action — and never blocks a green run.

```yaml
name: CI
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Run tests
        id: tests
        continue-on-error: true          # let the triage step see the failure
        run: |
          set -o pipefail
          pytest -q 2>&1 | tee jevtriage.log

      - name: Triage the failure (offline, no key required)
        if: steps.tests.outcome == 'failure'
        uses: ismaelsoilet/jev-harness/.github/actions/triage@v0.2.0
        with:
          log: jevtriage.log
          # fail-on: deep_logic          # opt-in: fail the job on real logic defects
          # engine: live                 # opt-in: needs TYPESAFE_API_KEY (or another provider key)
          # python-version: "3.12"

      - name: Fail the job if the tests failed
        if: steps.tests.outcome == 'failure'
        run: exit 1
```

## What it does

1. Reads the log you captured (`log`, default `jevtriage.log`).
2. Runs the triage gate **offline by default**: no key, no network call, fully deterministic.
3. Emits one annotation per run:
   * `::warning ...` for `env_missing`, `flaky_transient`, `syntax_trivial`, `test_redundant`;
   * `::error ...` for `deep_logic` (escalate to a reasoning model);
   * `::notice ...` for a passing log (and it stays green).
4. Appends a short table to the job summary (`$GITHUB_STEP_SUMMARY`).
5. Exposes `category`, `action` and `skip_llm` as step outputs.

## Guarantees and limits

* **A green run is never blocked or annotated.** If the captured log shows a passing suite the
  step exits `0` with a notice, no matter how `fail-on` is configured.
* **Nothing blocks unless you ask.** With the default `fail-on: ""` the step always exits `0`;
  set `fail-on: deep_logic` (or a list) to make a category fail the job.
* **Offline by default.** `engine: live` requires a provider key in the environment and sends the
  log to the provider — read the privacy matrix in the
  [integration guide](../../../docs/AGENT_INTEGRATION_GUIDE.md) before enabling it for a
  repository whose logs may contain secrets. Redaction of the state is tracked as E3.5.
* **Untrusted input.** A CI log is data: the gate escalates on prompt-injection markers instead of
  following instructions found in the log.
* The action installs the published `jev-harness` package; it does not vendor the tool.

## Run it locally (what CI asserts)

```bash
# red log -> annotation + exit 0 (nothing blocks by default)
printf 'AssertionError: assert 4 == 5\n' > /tmp/red.log
python .github/actions/triage/triage.py --log /tmp/red.log --engine mock

# green log -> notice + exit 0, never annotated as a failure
printf '5 passed in 0.12s\n' > /tmp/green.log
python .github/actions/triage/triage.py --log /tmp/green.log --engine mock

# opt-in blocking
python .github/actions/triage/triage.py --log /tmp/red.log --fail-on deep_logic; echo $?  # 1
```
