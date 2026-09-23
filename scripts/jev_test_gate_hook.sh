#!/bin/sh
# ==============================================================================
# Jev Harness pre-commit gate wrapper for the `pre-commit` framework.
#
# The test command is supplied as hook arguments, because a hook repository cannot
# know your project's test runner. Example `.pre-commit-config.yaml`:
#
#   repos:
#     - repo: https://github.com/ismaelsoilet/jev-harness
#       rev: v0.1.12
#       hooks:
#         - id: jev-test-gate
#           args: ["pytest -q"]        # or "npm test", "cargo test", ...
#
# Semantics: the test runner decides whether the commit is blocked; Jev Harness only
# triages the failing output so the agent can fix it deterministically whenever
# possible (install a dependency, retry a transient failure, or escalate to an LLM).
# ==============================================================================
set -u

if [ "$#" -eq 0 ] || [ -z "${1:-}" ]; then
    echo "[jev] No test command configured for the jev-test-gate hook." >&2
    echo '[jev] Add it in .pre-commit-config.yaml, e.g.:  args: ["pytest -q"]' >&2
    echo "[jev] Skipping the gate (nothing was blocked)." >&2
    exit 0
fi

TEST_CMD="$*"

echo "[jev] Running: ${TEST_CMD}"
if ! TEST_OUTPUT=$(sh -c "${TEST_CMD}" 2>&1); then
    printf '%s\n' "${TEST_OUTPUT}" | jev-harness test-gate || true
    echo "[jev] Tests failed: commit blocked. If the triage above says skip_llm=YES,"
    echo "[jev] apply the deterministic fix (install/retry) instead of calling an LLM."
    exit 1
fi

exit 0
