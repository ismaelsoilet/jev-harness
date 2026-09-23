"""
Console entry point for the `pre-commit` framework hook (`jev-test-gate`).

The `pre-commit` framework installs this package into an isolated environment and
invokes the console script with the test command supplied by the consumer's
`.pre-commit-config.yaml` (`args:`). Semantics: the test runner decides whether the
commit is blocked; Jev Harness only triages the failing output so the agent can fix
it deterministically whenever possible (install a dependency, retry a transient
failure, or escalate to an LLM).

Usage in `.pre-commit-config.yaml`:

    repos:
      - repo: https://github.com/ismaelsoilet/jev-harness
        rev: v0.1.12
        hooks:
          - id: jev-test-gate
            args: ["pytest -q"]     # or "npm test", "cargo test --quiet", ...
"""

from __future__ import annotations

import subprocess
import sys
from typing import List, Optional


def main(argv: Optional[List[str]] = None) -> int:
    """Runs the configured test command and triages a failure. Returns the exit code."""
    args = list(sys.argv[1:] if argv is None else argv)

    if not args or not " ".join(args).strip():
        sys.stderr.write(
            "[jev] No test command configured for the jev-test-gate hook.\n"
            '[jev] Add it in .pre-commit-config.yaml, e.g.:  args: ["pytest -q"]\n'
            "[jev] Skipping the gate (nothing was blocked).\n"
        )
        return 0

    command = " ".join(args)
    sys.stderr.write(f"[jev] Running: {command}\n")

    try:
        completed = subprocess.run(
            command, shell=True, capture_output=True, text=True, errors="replace"
        )
    except Exception as exc:  # pragma: no cover - defensive: never hide a failure
        sys.stderr.write(f"[jev] Could not run the test command: {exc}\n")
        return 1

    if completed.returncode == 0:
        return 0

    output = f"{completed.stdout or ''}{completed.stderr or ''}"

    try:
        from .gates import triage_test_failure

        result = triage_test_failure(output)
        print("--- JEV TEST TRIAGE VERDICT ---")
        print(f"Category:        {result.category.upper()}")
        print(f"Recommendation:  {result.action_recommendation}")
        if result.skip_llm:
            print("[jev] Deterministic fix available (see recommendation above) - no LLM needed.")
        else:
            print("[jev] Real logic defect: dispatch the filtered log to a reasoning model.")
    except Exception as exc:  # pragma: no cover - triage must never hide the failure
        sys.stderr.write(f"[jev] Triage unavailable: {exc}\n")

    sys.stderr.write("[jev] Tests failed: commit blocked.\n")
    return 1


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
