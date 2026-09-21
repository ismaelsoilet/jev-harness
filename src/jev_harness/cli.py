"""
Jev System One CLI Harness.
Provides fast semantic decisions, test gating, and token optimization from the shell.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys
from typing import Optional

from .client import JevClient
from .gates import (
    route_model_tier,
    should_abort_trajectory,
    triage_test_failure,
    verify_step_completion,
)


def _read_input(val_or_path: Optional[str]) -> str:
    """Reads input from direct string, file path, or stdin."""
    if val_or_path:
        p = Path(val_or_path)
        if p.is_file():
            return p.read_text(encoding="utf-8")
        return val_or_path
    if not sys.stdin.isatty():
        return sys.stdin.read()
    return ""


def cmd_status(args: argparse.Namespace) -> int:
    client = JevClient()
    key = client.api_key
    print("\n=== JEV HARNESS STATUS ===")
    if key:
        masked = key[:6] + "..." + key[-4:] if len(key) > 10 else "***"
        print(f"API Key:     Configured ({masked})")
        print(f"Provider:    {client.provider.upper()}")
        print(f"Endpoint:    {client.base_url}")
        print(f"Engine Mode: LIVE")
    else:
        print("API Key:     NOT DETECTED")
        print("Engine Mode: SIMULATION / MOCK (Heuristic offline mode active)")
        print("\nPara ativar o modo LIVE com seu provedor escolhido:")
        print("  - TypeSafe Oficial:  export TYPESAFE_API_KEY='sua_chave'")
        print("  - OpenCode Zen Free: export OPENCODE_API_KEY='sua_chave'")
        print("  - OpenRouter:        export OPENROUTER_API_KEY='sua_chave'")
        print("  (ou salve no .env do repo ou em ~/.config/jev/credentials.env)")
    print(f"Model:       {client.model}")
    print("==========================\n")
    return 0


def cmd_init(args: argparse.Namespace) -> int:
    cwd = Path.cwd()
    print(f"Initializing Jev Harness integration in: {cwd}")

    # 1. Ensure .agents/skills/jev-harness exists
    skills_dir = cwd / ".agents" / "skills" / "jev-harness"
    skills_dir.mkdir(parents=True, exist_ok=True)

    local_skill_file = skills_dir / "SKILL.md"
    skill_content = """---
name: jev-harness
description: Repository adapter for Jev System One. Uses fast semantic decisions (70-300ms) to gate tests, prevent token waste, and route models.
license: MIT
---

# Local Jev Harness Adapter

This repository is connected to the global **Jev System One Harness**.

## Usage in this repo:
- CLI command: `jev-harness [test-gate | abort-check | route | verify | status | mcp]`
- Local configuration: `.jev.json` or `.env`
- Global engine: `jev-harness`

## Rules for AI Coding Agents:
1. When a test fails, run `jev-harness test-gate` before spending 50k tokens prompting an LLM.
2. If `skip_llm=true`, solve the dependency or syntax issue deterministically.
3. Use `jev-harness abort-check` before attempting risky refactors or after 2 consecutive errors.
4. Run `jev-harness verify` before marking tasks as completed.
"""
    local_skill_file.write_text(skill_content, encoding="utf-8")
    print(f"  [+] Created agent skill: {local_skill_file.relative_to(cwd)}")

    # 2. Create .jev.json template
    jev_json = cwd / ".jev.json"
    if not jev_json.exists():
        jev_json.write_text(
            json.dumps(
                {
                    "api_key": "",
                    "model": "jev-latest",
                    "skip_llm_threshold": 0.65,
                    "abort_threshold": 0.70,
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        print(f"  [+] Created repo config: {jev_json.relative_to(cwd)}")
    else:
        print(f"  [*] Kept existing: {jev_json.relative_to(cwd)}")

    # 3. Create .env.jev.example
    env_example = cwd / ".env.jev.example"
    if not env_example.exists():
        env_example.write_text(
            "# Jev / TypeSafe API Key\nTYPESAFE_API_KEY=\"your_key_here\"\n# Or OpenRouter fallback:\n# OPENROUTER_API_KEY=\"your_key_here\"\n",
            encoding="utf-8",
        )
        print(f"  [+] Created env template: {env_example.relative_to(cwd)}")

    # 4. Create Cursor MCP snippet if .cursor exists
    cursor_dir = cwd / ".cursor"
    if cursor_dir.exists() or args.cursor:
        cursor_dir.mkdir(exist_ok=True)
        cursor_mcp = cursor_dir / "mcp.json"
        if not cursor_mcp.exists():
            cursor_mcp.write_text(
                json.dumps(
                    {
                        "mcpServers": {
                            "jev-harness": {
                                "command": "jev-mcp",
                                "args": [],
                            }
                        }
                    },
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )
            print(f"  [+] Created Cursor MCP config: {cursor_mcp.relative_to(cwd)}")

    print("\n[OK] Repository configured successfully! You can now run 'jev-harness status'.\n")
    return 0


def cmd_test_gate(args: argparse.Namespace) -> int:
    text = _read_input(args.log or args.sample)
    if not text:
        print("Error: No test failure log provided. Pass --log <file_or_string> or pipe via stdin.", file=sys.stderr)
        return 2

    client = JevClient(force_mock=args.mock)
    res = triage_test_failure(text, client=client)

    if args.json:
        print(
            json.dumps(
                {
                    "category": res.category,
                    "confidence": res.confidence,
                    "skip_llm": res.skip_llm,
                    "skip_llm_prob": res.skip_llm_prob,
                    "severity_score": res.severity_score,
                    "recommendation": res.action_recommendation,
                    "is_mock": res.is_mock,
                },
                indent=2,
            )
        )
    else:
        print("\n--- JEV TEST TRIAGE VERDICT ---")
        print(f"Category:        {res.category.upper()}")
        print(f"Confidence:      {res.confidence * 100:.1f}%")
        print(f"Skip LLM Call:   {'YES (Save Tokens!)' if res.skip_llm else 'NO (Dispatch to System 2)'}")
        print(f"Skip Probability: {res.skip_llm_prob * 100:.1f}%")
        print(f"Severity Score:  {res.severity_score:.1f} / 4.0")
        print(f"Recommendation:  {res.action_recommendation}")
        if res.is_mock:
            print("Mode:            [SIMULATION/MOCK]")
        print("--------------------------------\n")

    return 0 if res.skip_llm else 1


def cmd_abort_check(args: argparse.Namespace) -> int:
    plan = _read_input(args.plan)
    history = _read_input(args.history)
    if not plan:
        print("Error: No plan provided. Pass --plan <text_or_path>.", file=sys.stderr)
        return 2

    client = JevClient(force_mock=args.mock)
    res = should_abort_trajectory(plan, recent_attempts_summary=history, client=client)

    if args.json:
        print(
            json.dumps(
                {
                    "should_abort": res.should_abort,
                    "abort_probability": res.abort_probability,
                    "action": res.action,
                    "viability_score": res.viability_score,
                    "reasoning_summary": res.reasoning_summary,
                    "is_mock": res.is_mock,
                },
                indent=2,
            )
        )
    else:
        print("\n--- JEV ABORT GATE VERDICT ---")
        print(f"Should Abort:     {'YES - STOP & RECONSIDER' if res.should_abort else 'NO - PROCEED'}")
        print(f"Abort Probability: {res.abort_probability * 100:.1f}%")
        print(f"Recommended Action: {res.action}")
        print(f"Viability Score:   {res.viability_score:.1f} / 4.0")
        print(f"Summary:           {res.reasoning_summary}")
        if res.is_mock:
            print("Mode:              [SIMULATION/MOCK]")
        print("------------------------------\n")

    return 1 if res.should_abort else 0


def cmd_route(args: argparse.Namespace) -> int:
    task = _read_input(args.task)
    if not task:
        print("Error: No task description provided. Pass --task <text_or_path>.", file=sys.stderr)
        return 2

    client = JevClient(force_mock=args.mock)
    res = route_model_tier(task, client=client)

    if args.json:
        print(
            json.dumps(
                {
                    "selected_tier": res.selected_tier,
                    "confidence": res.confidence,
                    "complexity_score": res.complexity_score,
                    "recommended_model": res.recommended_model,
                    "rationale": res.rationale,
                    "is_mock": res.is_mock,
                },
                indent=2,
            )
        )
    else:
        print("\n--- JEV MODEL ROUTE VERDICT ---")
        print(f"Selected Tier:     {res.selected_tier.upper()}")
        print(f"Confidence:        {res.confidence * 100:.1f}%")
        print(f"Complexity Score:  {res.complexity_score:.1f} / 4.0")
        print(f"Recommended Model: {res.recommended_model}")
        print(f"Rationale:         {res.rationale}")
        if res.is_mock:
            print("Mode:              [SIMULATION/MOCK]")
        print("-------------------------------\n")

    return 0


def cmd_verify(args: argparse.Namespace) -> int:
    criteria = _read_input(args.criteria)
    output = _read_input(args.output)
    if not criteria or not output:
        print("Error: Both --criteria and --output must be provided.", file=sys.stderr)
        return 2

    client = JevClient(force_mock=args.mock)
    res = verify_step_completion(criteria, output, client=client)

    if args.json:
        print(
            json.dumps(
                {
                    "is_verified": res.is_verified,
                    "satisfaction_probability": res.satisfaction_probability,
                    "rigor_score": res.rigor_score,
                    "confidence": res.confidence,
                    "needs_rework": res.needs_rework,
                    "is_mock": res.is_mock,
                },
                indent=2,
            )
        )
    else:
        print("\n--- JEV VERIFICATION VERDICT ---")
        print(f"Verified:           {'PASS' if res.is_verified else 'REWORK NEEDED'}")
        print(f"Satisfaction Prob:  {res.satisfaction_probability * 100:.1f}%")
        print(f"Rigor Score:        {res.rigor_score:.1f} / 4.0")
        print(f"Confidence:         {res.confidence * 100:.1f}%")
        if res.is_mock:
            print("Mode:               [SIMULATION/MOCK]")
        print("--------------------------------\n")

    return 0 if res.is_verified else 1


def cmd_mcp(args: argparse.Namespace) -> int:
    from .mcp_server import run_mcp_server
    client = JevClient(force_mock=args.mock)
    run_mcp_server(client=client)
    return 0


def main() -> None:
    # Common flags shared between root and all subparsers
    common_parser = argparse.ArgumentParser(add_help=False)
    common_parser.add_argument("--mock", action="store_true", help="Force local simulation mode even if key is present")
    common_parser.add_argument("--json", action="store_true", help="Output machine-readable JSON")

    parser = argparse.ArgumentParser(
        prog="jev-harness",
        description="TypeSafe Jev System One Decision Harness & Token Optimizer",
        parents=[common_parser],
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    # status
    p_status = subparsers.add_parser("status", parents=[common_parser], help="Show API configuration and engine status")
    p_status.set_defaults(func=cmd_status)

    # init
    p_init = subparsers.add_parser("init", parents=[common_parser], help="Initialize Jev adapter and configs in current repository")
    p_init.add_argument("--cursor", action="store_true", help="Also generate .cursor/mcp.json")
    p_init.set_defaults(func=cmd_init)

    # test-gate
    p_test = subparsers.add_parser("test-gate", parents=[common_parser], help="Triage test failures and avoid unnecessary LLM calls")
    p_test.add_argument("--log", "-l", help="Path to error log or raw log string")
    p_test.add_argument("--sample", help="Sample error string (alias for --log)")
    p_test.set_defaults(func=cmd_test_gate)

    # abort-check
    p_abort = subparsers.add_parser("abort-check", parents=[common_parser], help="Check if agent trajectory or plan leads to a dead end")
    p_abort.add_argument("--plan", "-p", required=True, help="Proposed plan or next step")
    p_abort.add_argument("--history", "-H", default="", help="Previous attempts summary or context")
    p_abort.set_defaults(func=cmd_abort_check)

    # route
    p_route = subparsers.add_parser("route", parents=[common_parser], help="Route task to minimal sufficient model tier")
    p_route.add_argument("--task", "-t", required=True, help="Task description or prompt")
    p_route.set_defaults(func=cmd_route)

    # verify
    p_verify = subparsers.add_parser("verify", parents=[common_parser], help="Verify if produced evidence satisfies acceptance criteria")
    p_verify.add_argument("--criteria", "-c", required=True, help="Acceptance criteria")
    p_verify.add_argument("--output", "-o", required=True, help="Produced evidence / output")
    p_verify.set_defaults(func=cmd_verify)

    # mcp
    p_mcp = subparsers.add_parser("mcp", parents=[common_parser], help="Run stdio MCP server for Cursor, Claude, Antigravity, OpenCode")
    p_mcp.set_defaults(func=cmd_mcp)

    args = parser.parse_args()
    sys.exit(args.func(args))


if __name__ == "__main__":
    main()
