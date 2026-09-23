#!/usr/bin/env python3
"""
E2.1 — CI triage entry point for the composite GitHub Action.

Reads a failure log, asks a gate what it is, and publishes the answer as a GitHub annotation
(plus an optional PR comment and a job summary). Design rules from the plan:

* **a green run is never blocked** — the action reports, it does not decide the job's fate;
* **offline by default** — no key, no network, fully deterministic; live only when a provider key
  is present and `engine: live` is requested;
* **opt-in blocking** — `fail-on` turns a specific category into a non-zero exit;
* **untrusted input** — the log is a CI artifact, so it is treated as data (the triage gate
  escalates on prompt-injection markers).

Zero external dependencies: standard library only, like the rest of the core.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

try:  # installed package (the Action installs jev-harness before running this)
    from jev_harness.client import JevClient
    from jev_harness.gates import triage_test_failure
except ImportError:  # running straight from a source checkout
    sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "src"))
    from jev_harness.client import JevClient
    from jev_harness.gates import triage_test_failure

# What the agent should do next, per category (kept short: it is an annotation, not a report).
ACTIONS = {
    "env_missing": "Install the missing dependency deterministically (no LLM needed).",
    "flaky_transient": "Retry once: the failure looks transient (network/port/timing).",
    "syntax_trivial": "Fix the syntax error flagged by the runner.",
    "test_redundant": "Remove or un-deprecate the redundant test.",
    "deep_logic": "Escalate to a reasoning model with the focused failure context.",
    "no_failure": "Nothing to triage: the log shows a successful run.",
}


def _escape_workflow_command(text: str) -> str:
    """GitHub workflow commands need %, \\r and \\n escaped, and the message may be long."""
    escaped = text.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")
    return escaped[:4000]


def _read_log(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return ""


def triage(log_text: str, engine: str, provider: str | None = None) -> dict:
    """Runs the triage gate and returns a JSON-ready verdict."""
    if engine == "live":
        client = JevClient(provider=provider, fail_open=True)
    else:
        client = JevClient(force_mock=True)
    result = triage_test_failure(log_text, client=client, record_session=False)
    return {
        "category": result.category,
        "skip_llm": result.skip_llm,
        "confidence": result.confidence,
        "severity_score": result.severity_score,
        "action_recommendation": result.action_recommendation,
        "is_mock": result.is_mock,
        "degraded_reason": result.degraded_reason,
        "engine": engine,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Triage a CI failure log and annotate the job.")
    parser.add_argument("--log", default="jevtriage.log", help="Path to the captured failure log")
    parser.add_argument(
        "--engine",
        choices=["mock", "live"],
        default=os.getenv("JEV_ENGINE", "mock"),
        help="Decision engine (default: mock / $JEV_ENGINE)",
    )
    parser.add_argument("--provider", default=os.getenv("JEV_PROVIDER") or None, help="Provider for the live engine")
    parser.add_argument("--json", action="store_true", help="Print the verdict as JSON")
    parser.add_argument("--summary", default=None, help="Append a Markdown summary to this file ($GITHUB_STEP_SUMMARY)")
    parser.add_argument(
        "--fail-on",
        default=os.getenv("JEV_FAIL_ON", ""),
        help="Comma-separated categories that should exit 1 (empty = never block; default: empty)",
    )
    parser.add_argument(
        "--github-output",
        default=os.getenv("GITHUB_OUTPUT", ""),
        help="Write `category` and `action` step outputs to this file (defaults to $GITHUB_OUTPUT)",
    )
    args = parser.parse_args(argv)

    log_text = _read_log(Path(args.log))
    if not log_text.strip():
        # No log is not a failure of the pipeline: say so and stay green.
        print(f"::notice::jev-harness found no failure log at {args.log} (nothing to triage).")
        return 0

    verdict = triage(log_text, args.engine, args.provider)
    category = verdict["category"]
    action = ACTIONS.get(category, "Review the failure manually.")

    # A green run is never annotated and never blocked.
    if category == "no_failure":
        print("::notice::jev-harness: the captured log shows a passing run; no triage needed.")
        if args.json:
            print(json.dumps(verdict, indent=2))
        return 0

    level = "error" if category == "deep_logic" else "warning"
    degraded = f" (degraded: {verdict['degraded_reason']})" if verdict["degraded_reason"] else ""
    mode = "live" if args.engine == "live" and not verdict["is_mock"] else "offline"
    print(
        f"::{level} title=jev-harness [{category}]{degraded}::"
        f"{_escape_workflow_command(action)} "
        f"(confidence {verdict['confidence']:.2f}, severity {verdict['severity_score']:.1f}/4.0, engine {mode})"
    )

    if args.summary:
        try:
            with open(args.summary, "a", encoding="utf-8") as handle:
                handle.write(
                    f"### jev-harness triage\n\n"
                    f"| Category | Action | Confidence | Severity | Engine |\n"
                    f"| :--- | :--- | ---: | ---: | :--- |\n"
                    f"| `{category}` | {action} | {verdict['confidence']:.2f} | "
                    f"{verdict['severity_score']:.1f}/4.0 | {mode} |\n\n"
                    f"> {verdict['action_recommendation']}\n\n"
                )
        except Exception:
            pass

    if args.github_output:
        try:
            with open(args.github_output, "a", encoding="utf-8") as handle:
                handle.write(f"category={category}\n")
                handle.write(f"action={action}\n")
                handle.write(f"skip_llm={'true' if verdict['skip_llm'] else 'false'}\n")
        except Exception:
            pass

    if args.json:
        print(json.dumps(verdict, indent=2))

    fail_on = {item.strip() for item in args.fail_on.split(",") if item.strip()}
    return 1 if category in fail_on else 0


if __name__ == "__main__":
    sys.exit(main())
