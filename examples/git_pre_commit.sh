#!/usr/bin/env bash
# Git pre-commit / pre-push hook using Jev System One
# Save to .husky/pre-commit or .git/hooks/pre-commit and chmod +x

set -e

echo "[Jev] Running test suite with token guard..."

# Run your test suite and capture output
TEST_OUTPUT=$(npm test 2>&1) || TEST_EXIT=$?

if [ "${TEST_EXIT:-0}" -ne 0 ]; then
    echo "Tests failed. Invoking Jev System One triage..."
    echo "$TEST_OUTPUT" | jev-harness test-gate
    TRIAGE_EXIT=$?

    if [ $TRIAGE_EXIT -eq 0 ]; then
        echo -e "\n[Jev Notice] Failure appears to be environment, syntax, or flaky network."
        echo "Follow Jev's deterministic recommendation above before prompting an LLM."
    else
        echo -e "\n[Jev Notice] Genuine logic defect detected."
    fi
    exit 1
fi

echo "[Jev] All tests passed! Ready to commit."
exit 0
