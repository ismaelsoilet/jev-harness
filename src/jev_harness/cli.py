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

try:
    from . import __version__
    from .client import JevClient
    from .gates import (
        modulate_reasoning_effort,
        route_model_tier,
        should_abort_trajectory,
        triage_test_failure,
        verify_step_completion,
    )
except (ImportError, ValueError):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from jev_harness import __version__
    from jev_harness.client import JevClient
    from jev_harness.gates import (
        modulate_reasoning_effort,
        route_model_tier,
        should_abort_trajectory,
        triage_test_failure,
        verify_step_completion,
    )


def _read_input(val_or_path: Optional[str], allow_stdin: bool = True) -> str:
    """Reads input from direct string, file path, or optionally stdin."""
    if val_or_path:
        p = Path(val_or_path)
        if p.is_file():
            return p.read_text(encoding="utf-8")
        return val_or_path
    if allow_stdin and not sys.stdin.isatty():
        return sys.stdin.read()
    return ""


def cmd_status(args: argparse.Namespace) -> int:
    client = JevClient(
        provider=getattr(args, "provider", None),
        force_mock=getattr(args, "mock", False),
    )
    key = client.api_key
    print("\n=== JEV HARNESS STATUS ===")
    if client.is_live:
        if client.provider == "opencode":
            print("Provider:    OPENCODE ZEN (Free Tier)")
            print(f"Endpoint:    {client.base_url}")
            print("Engine Mode: LIVE (OpenCode Zen Free Community Model)")
        else:
            masked = key[:6] + "..." + key[-4:] if key and len(key) > 10 else "***"
            print(f"API Key:     Configured ({masked})")
            print(f"Provider:    {client.provider.upper()}")
            print(f"Endpoint:    {client.base_url}")
            print("Engine Mode: LIVE")
    else:
        print("API Key:     NOT DETECTED")
        print("Engine Mode: SIMULATION / MOCK (Heuristic offline mode active)")
        print("\nPara ativar o modo LIVE com seu provedor escolhido:")
        print("  - OpenCode Zen Free: export OPENCODE_API_KEY=zen (ou jev-harness --provider opencode)")
        print("  - TypeSafe Oficial:  export TYPESAFE_API_KEY='sua_chave'")
        print("  - OpenRouter:        export OPENROUTER_API_KEY='sua_chave'")
        print("  (ou salve no .env do repo ou em ~/.config/jev/credentials.env)")
    print(f"Model:       {client.model}")
    print("==========================\n")
    return 0


def cmd_metrics(args: argparse.Namespace) -> int:
    from .session import load_session, reset_metrics
    if getattr(args, "reset", False):
        reset_metrics()
        print("\n[OK] Jev Harness metrics reset successfully.\n")
        return 0

    s = load_session()
    if getattr(args, "json", False):
        print(
            json.dumps(
                {
                    "total_triage_calls": s.total_triage_calls,
                    "skipped_llm_calls": s.skipped_llm_calls,
                    "abort_guards_triggered": s.abort_guards_triggered,
                    "deterministic_routes": s.deterministic_routes,
                    "effort_modulations": s.effort_modulations,
                    "estimated_tokens_saved": s.estimated_tokens_saved,
                    "estimated_cost_saved_usd": round(s.estimated_cost_saved_usd, 2),
                },
                indent=2,
            )
        )
    else:
        print("\n=== JEV HARNESS ROI & TOKEN METRICS ===")
        print(f"Total Test Triages:      {s.total_triage_calls}")
        print(f"LLM Calls Intercepted:   {s.skipped_llm_calls} (Fixed deterministically)")
        print(f"Doom Loops Aborted:      {s.abort_guards_triggered}")
        print(f"Deterministic Routes:    {s.deterministic_routes}")
        print(f"Effort Modulations:      {s.effort_modulations} (Astra-Jev per-generation)")
        print(f"Estimated Tokens Saved:  ⚡ {s.estimated_tokens_saved:,} tokens")
        print(f"Estimated API Cost Saved: 💸 ${s.estimated_cost_saved_usd:.2f} USD")
        print("=======================================\n")
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
- CLI command: `jev-harness [test-gate | abort-check | route | verify | status | metrics | mcp]`
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

    # 4. Create Cursor MCP snippet if .cursor exists or requested
    cursor_dir = cwd / ".cursor"
    if cursor_dir.exists() or getattr(args, "cursor", False) or getattr(args, "all", False):
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

    # 5. Configure Antigravity IDE if requested
    if getattr(args, "antigravity", False) or getattr(args, "all", False):
        antigravity_dir = Path.home() / ".gemini" / "config"
        try:
            antigravity_dir.mkdir(parents=True, exist_ok=True)
            hooks_file = antigravity_dir / "hooks.json"
            if not hooks_file.exists():
                hooks_file.write_text(
                    json.dumps(
                        {
                            "jev-token-guard": {
                                "PreInvocation": [
                                    {
                                        "type": "command",
                                        "command": "echo '{\"injectSteps\": [{\"ephemeralMessage\": \"[JEV ACTIVE] Jev System One está ativo no sistema. Ao lidar com testes com erro, utilize jev-harness test-gate. Se skip_llm=true, resolva o ambiente/dependência deterministicamente sem gastar tokens de LLM. Se houver falhas consecutivas, avalie com jev-harness abort-check.\"}]}'",
                                    }
                                ]
                            }
                        },
                        indent=2,
                    )
                    + "\n",
                    encoding="utf-8",
                )
                print(f"  [+] Configured Antigravity hook: {hooks_file}")
            mcp_file = antigravity_dir / "mcp_config.json"
            if not mcp_file.exists():
                mcp_file.write_text(
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
                print(f"  [+] Configured Antigravity MCP: {mcp_file}")
        except Exception as e:
            print(f"  [!] Antigravity configuration notice: {e}")

    # 6. Install Git pre-commit hook if requested
    if getattr(args, "git", False) or getattr(args, "all", False):
        git_hooks = cwd / ".git" / "hooks"
        if git_hooks.exists():
            pre_commit = git_hooks / "pre-commit"
            hook_script = "#!/bin/sh\n# Jev Harness Pre-commit Gate\npython -m unittest 2>&1 | jev-harness test-gate || exit 1\n"
            pre_commit.write_text(hook_script, encoding="utf-8")
            pre_commit.chmod(0o755)
            print(f"  [+] Installed Git pre-commit guardrail: {pre_commit.relative_to(cwd)}")

    print("\n[OK] Repository configured successfully! You can now run 'jev-harness status'.\n")
    return 0


def cmd_test_gate(args: argparse.Namespace) -> int:
    raw_input = getattr(args, "log", None) or getattr(args, "sample", None) or getattr(args, "log_pos", None)
    text = _read_input(raw_input).strip()
    if not text:
        print("Error: No test failure log provided. Pass --log <file_or_string> or as positional argument or pipe via stdin.", file=sys.stderr)
        return 2

    force_mock = getattr(args, "mock", False)
    provider = getattr(args, "provider", None)
    is_json = getattr(args, "json", False)
    client = JevClient(force_mock=force_mock, provider=provider)
    res = triage_test_failure(text, client=client, record_session=True)

    if is_json:
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
        print(f"Skip Prob:       {res.skip_llm_prob * 100:.1f}%")
        print(f"Severity Score:  {res.severity_score:.1f} / 4.0")
        print(f"Recommendation:  {res.action_recommendation}")
        if res.is_mock:
            print("Mode:            [SIMULATION/MOCK]")
        else:
            print(f"Mode:            [LIVE: {client.provider.upper()}]")
        print("--------------------------------\n")

    return 0 if res.skip_llm else 1


def cmd_abort_check(args: argparse.Namespace) -> int:
    raw_plan = getattr(args, "plan", None) or getattr(args, "plan_pos", None)
    plan = _read_input(raw_plan, allow_stdin=True).strip()
    history = _read_input(args.history, allow_stdin=False).strip()
    if not plan:
        print("Error: No plan provided. Pass --plan <text_or_path> or as positional argument.", file=sys.stderr)
        return 2

    force_mock = getattr(args, "mock", False)
    provider = getattr(args, "provider", None)
    is_json = getattr(args, "json", False)
    client = JevClient(force_mock=force_mock, provider=provider)
    res = should_abort_trajectory(plan, recent_attempts_summary=history, client=client, record_session=True)

    if is_json:
        print(
            json.dumps(
                {
                    "should_abort": res.should_abort,
                    "abort_probability": res.abort_probability,
                    "action": res.action,
                    "viability_score": res.viability_score,
                    "summary": res.reasoning_summary,
                    "is_mock": res.is_mock,
                },
                indent=2,
            )
        )
    else:
        print("\n--- JEV ABORT GATE VERDICT ---")
        print(f"Should Abort:     {'YES - STOP & RECONSIDER' if res.should_abort else 'NO - PROCEED'}")
        print(f"Abort Probability: {res.abort_probability * 100:.1f}%")
        print(f"Action:           {res.action.upper()}")
        print(f"Viability Score:  {res.viability_score:.1f} / 4.0")
        print(f"Summary:          {res.reasoning_summary}")
        if res.is_mock:
            print("Mode:             [SIMULATION/MOCK]")
        else:
            print(f"Mode:             [LIVE: {client.provider.upper()}]")
        print("------------------------------\n")

    return 1 if res.should_abort else 0


def cmd_route(args: argparse.Namespace) -> int:
    raw_task = getattr(args, "task", None) or getattr(args, "task_pos", None)
    task = _read_input(raw_task).strip()
    if not task:
        print("Error: No task provided. Pass --task <text_or_path> or as positional argument.", file=sys.stderr)
        return 2

    force_mock = getattr(args, "mock", False)
    provider = getattr(args, "provider", None)
    is_json = getattr(args, "json", False)
    client = JevClient(force_mock=force_mock, provider=provider)
    res = route_model_tier(task, client=client)

    if is_json:
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
        else:
            print(f"Mode:              [LIVE: {client.provider.upper()}]")
        print("-------------------------------\n")

    return 0


def cmd_verify(args: argparse.Namespace) -> int:
    criteria = _read_input(args.criteria, allow_stdin=False).strip()
    output = _read_input(args.output, allow_stdin=False).strip()
    if not criteria or not output:
        print("Error: Both --criteria and --output must be provided.", file=sys.stderr)
        return 2

    force_mock = getattr(args, "mock", False)
    provider = getattr(args, "provider", None)
    is_json = getattr(args, "json", False)
    client = JevClient(force_mock=force_mock, provider=provider)
    res = verify_step_completion(criteria, output, client=client)

    if is_json:
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
        print(f"Needs Rework:       {'YES' if res.needs_rework else 'NO'}")
        if res.is_mock:
            print("Mode:               [SIMULATION/MOCK]")
        else:
            print(f"Mode:               [LIVE: {client.provider.upper()}]")
        print("--------------------------------\n")

    return 0 if res.is_verified else 1


def cmd_reasoning_effort(args: argparse.Namespace) -> int:
    context_raw = getattr(args, "context_pos", None) or getattr(args, "context", None)
    context = _read_input(context_raw).strip()
    if not context:
        print("Error: Context/step description must be provided via argument or stdin.", file=sys.stderr)
        return 2

    provider = getattr(args, "target_provider", None) or getattr(args, "provider", "openai")
    model = getattr(args, "model", None)
    force_mock = getattr(args, "mock", False)
    is_json = getattr(args, "json", False)
    session_context_tokens = getattr(args, "session_context_tokens", 0) or 0

    client = JevClient(force_mock=force_mock)
    res = modulate_reasoning_effort(
        context,
        provider=provider,
        model=model,
        session_context_tokens=session_context_tokens,
        client=client,
        record_session=True,
    )

    if is_json:
        print(
            json.dumps(
                {
                    "effort": res.effort,
                    "confidence": res.confidence,
                    "complexity_score": res.complexity_score,
                    "rationale": res.rationale,
                    "provider": res.provider,
                    "provider_params": res.provider_params,
                    "is_reasoning_supported": res.is_reasoning_supported,
                    "cache_safe_recommendation": res.cache_safe_recommendation,
                    "is_mock": res.is_mock,
                },
                indent=2,
            )
        )
    else:
        print("\n=== JEV REASONING EFFORT GATE ===")
        print(f"Assigned Effort:   {res.effort.upper()}")
        print(f"Target Provider:   {res.provider.upper()}")
        print(f"Confidence:        {res.confidence * 100:.1f}%")
        print(f"Complexity Score:  {res.complexity_score:.1f} / 4.0")
        print(f"Rationale:         {res.rationale}")
        print(f"Provider Payload:  {json.dumps(res.provider_params)}")
        print(f"Cache Advisory:    {res.cache_safe_recommendation}")
        if not res.is_reasoning_supported:
            print("WARNING: Target model is direct single-pass; do NOT inject reasoning params!")
        if res.is_mock:
            print("Engine Mode:       [SIMULATION / MOCK]")
        else:
            print(f"Engine Mode:       [LIVE: {client.provider.upper()}]")
        print("=================================\n")

    return 0


def cmd_mcp(args: argparse.Namespace) -> int:
    force_mock = getattr(args, "mock", False)
    provider = getattr(args, "provider", None)
    client = JevClient(force_mock=force_mock, provider=provider)
    run_mcp_server(client=client)
    return 0


def main() -> None:
    # Common flags shared between root and all subparsers
    common_parser = argparse.ArgumentParser(add_help=False)
    common_parser.add_argument("--mock", action="store_true", default=argparse.SUPPRESS, help="Force local simulation mode even if key is present")
    common_parser.add_argument("--json", action="store_true", default=argparse.SUPPRESS, help="Output machine-readable JSON")
    common_parser.add_argument("--provider", choices=["typesafe", "opencode", "openrouter"], default=argparse.SUPPRESS, help="Override backend provider")

    parser = argparse.ArgumentParser(
        prog="jev-harness",
        description="TypeSafe Jev System One Decision Harness & Token Optimizer",
        parents=[common_parser],
    )
    parser.add_argument(
        "--version",
        "-V",
        action="version",
        version=f"%(prog)s {__version__}",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    # status
    p_status = subparsers.add_parser("status", parents=[common_parser], help="Show API configuration and engine status")
    p_status.set_defaults(func=cmd_status)

    # init
    p_init = subparsers.add_parser("init", parents=[common_parser], help="Initialize Jev adapter and configs in current repository")
    p_init.add_argument("--cursor", action="store_true", help="Also generate .cursor/mcp.json")
    p_init.add_argument("--antigravity", action="store_true", help="Configure Antigravity IDE hooks and MCP config")
    p_init.add_argument("--git", action="store_true", help="Install git pre-commit test-gate hook")
    p_init.add_argument("--all", action="store_true", help="Configure all integrations (Cursor, Antigravity, Git)")
    p_init.set_defaults(func=cmd_init)

    # metrics
    p_metrics = subparsers.add_parser("metrics", parents=[common_parser], help="Display token ROI, intercepted LLM calls, and cost savings")
    p_metrics.add_argument("--reset", action="store_true", help="Reset saved telemetry counters")
    p_metrics.set_defaults(func=cmd_metrics)

    # test-gate (alias: triage)
    p_test = subparsers.add_parser("test-gate", aliases=["triage"], parents=[common_parser], help="Triage test failures and avoid unnecessary LLM calls")
    p_test.add_argument("log_pos", nargs="?", default=None, help="Direct error string or path to error log file")
    p_test.add_argument("--log", "-l", help="Path to error log or raw log string")
    p_test.add_argument("--sample", help="Sample error string (alias for --log)")
    p_test.set_defaults(func=cmd_test_gate)

    # abort-check (alias: abort)
    p_abort = subparsers.add_parser("abort-check", aliases=["abort"], parents=[common_parser], help="Check if agent trajectory or plan leads to a dead end")
    p_abort.add_argument("plan_pos", nargs="?", default=None, help="Proposed plan or next step")
    p_abort.add_argument("--plan", "-p", default=None, help="Proposed plan or next step")
    p_abort.add_argument("--history", "-H", default="", help="Previous attempts summary or context")
    p_abort.set_defaults(func=cmd_abort_check)

    # route
    p_route = subparsers.add_parser("route", parents=[common_parser], help="Route task to minimal sufficient model tier")
    p_route.add_argument("task_pos", nargs="?", default=None, help="Task description or prompt")
    p_route.add_argument("--task", "-t", default=None, help="Task description or prompt")
    p_route.set_defaults(func=cmd_route)

    # reasoning-effort (alias: astra-jev)
    p_effort = subparsers.add_parser(
        "reasoning-effort",
        aliases=["astra-jev"],
        parents=[common_parser],
        help="Modulate reasoning effort dynamically before each generation (2026 Frontier Models)",
    )
    p_effort.add_argument("context_pos", nargs="?", default=None, help="Context or prompt of the immediate next step")
    p_effort.add_argument("--context", "-c", default=None, help="Context or prompt of the immediate next step")
    p_effort.add_argument(
        "--target-provider",
        "--provider-target",
        dest="target_provider",
        default="openai",
        help="Target model provider (openai, deepseek, qwen, anthropic, gemini, kimi, mimo)",
    )
    p_effort.add_argument("--model", "-m", default=None, help="Specific target model identifier")
    p_effort.add_argument(
        "--session-context-tokens",
        "--tokens",
        dest="session_context_tokens",
        type=int,
        default=0,
        help="Active prompt tokens in session context",
    )
    p_effort.set_defaults(func=cmd_reasoning_effort)

    # verify
    p_verify = subparsers.add_parser("verify", parents=[common_parser], help="Verify if produced evidence satisfies acceptance criteria")
    p_verify.add_argument("--criteria", "-c", required=True, help="Acceptance criteria")
    p_verify.add_argument("--output", "-o", required=True, help="Produced evidence / output")
    p_verify.set_defaults(func=cmd_verify)

    # mcp
    p_mcp = subparsers.add_parser("mcp", parents=[common_parser], help="Run stdio MCP server for Cursor, Claude, Antigravity, OpenCode")
    p_mcp.set_defaults(func=cmd_mcp)

    args = parser.parse_args()
    try:
        sys.exit(args.func(args))
    except BrokenPipeError:
        try:
            devnull = os.open(os.devnull, os.O_WRONLY)
            os.dup2(devnull, sys.stdout.fileno())
        except Exception:
            pass
        sys.exit(0)


if __name__ == "__main__":
    main()
