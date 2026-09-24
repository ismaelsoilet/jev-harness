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

if __package__ is None or __package__ == "":
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    __package__ = "jev_harness"

from . import __version__
from .client import JevClient
from .config import load_repo_config
from .integrations.foreman import FOREMAN_DEFAULT_OUT_DIR
from .session import (
    ASSUMED_COST_PER_ABORT_USD,
    ASSUMED_COST_PER_TRIAGE_SKIP_USD,
    ASSUMED_TOKENS_PER_ABORT,
    ASSUMED_TOKENS_PER_TRIAGE_SKIP,
)
from .gates import (
    modulate_reasoning_effort,
    route_model_tier,
    should_abort_trajectory,
    should_nudge_continuation,
    triage_test_failure,
    verify_step_completion,
)


def _path_is_file(value: str) -> bool:
    """True when `value` names an existing file. An unusable path (longer than the OS limit)
    is not a file: the caller must treat it as literal text, never as a crash."""
    try:
        return Path(value).is_file()
    except OSError:
        return False


def _read_input(val_or_path: Optional[str], allow_stdin: bool = True) -> str:
    """Reads input from direct string, file path, or optionally stdin."""
    if val_or_path:
        if _path_is_file(val_or_path):
            return Path(val_or_path).read_text(encoding="utf-8")
        return val_or_path
    if allow_stdin and not sys.stdin.isatty():
        return sys.stdin.read()
    return ""


def _extra_state(args: argparse.Namespace) -> Dict[str, Any]:
    """Parses `--state-json` (inline object or file) so every gate can merge structured context."""
    from .state import parse_state_json

    raw = getattr(args, "state_json", None)
    if not raw:
        return {}
    try:
        return parse_state_json(raw)
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        raise SystemExit(2)


def _build_client(args: argparse.Namespace) -> JevClient:
    """Builds the client honoring the shared mock/provider/retry/failure flags of every command."""
    kwargs: Dict[str, Any] = {
        "force_mock": getattr(args, "mock", False),
        "provider": getattr(args, "provider", None),
        "fail_open": not getattr(args, "fail_closed", False),
        # The CLI is the cost-conscious surface, but a shadow measurement must always see real
        # decisions (and --no-cache always wins).
        "cache": not getattr(args, "no_cache", False) and not _shadow_enabled(args),
    }
    retries = getattr(args, "retries", None)
    if retries is not None:
        kwargs["max_retries"] = max(1, int(retries))
    return JevClient(**kwargs)


def _shadow_enabled(args: argparse.Namespace) -> bool:
    """Shadow mode: decide and report, but never change the caller's exit code."""
    return bool(getattr(args, "shadow", False)) or bool(load_repo_config().get("shadow", False))


def _shadow_wrap(args: argparse.Namespace, exit_code: int) -> int:
    if _shadow_enabled(args):
        print(f"[SHADOW] would exit {exit_code} - no action taken.", file=sys.stderr)
        return 0
    return exit_code


def _receipt(args: argparse.Namespace, gate: str, input_text: str, res: Any, client: JevClient, decision: str) -> None:
    """E1.3: appends one audit receipt (never raw log content, only a stable input hash)."""
    if getattr(args, "no_receipts", False):
        return
    from .receipts import record_receipt

    record_receipt(
        gate=gate,
        input_text=input_text,
        decision=decision,
        confidence=getattr(res, "confidence", None),
        model=client.model,
        is_mock=bool(getattr(res, "is_mock", False)),
        degraded_reason=getattr(res, "degraded_reason", ""),
        shadow=_shadow_enabled(args),
    )


def _mock_mode_label(result: Any) -> str:
    """`[SIMULATION/MOCK]`, naming the degradation when a provider failure caused it (E0.2)."""
    reason = getattr(result, "degraded_reason", "")
    return f"[SIMULATION/MOCK - degraded: {reason}]" if reason else "[SIMULATION/MOCK]"


def _model_origin_label(client: JevClient) -> str:
    """Human label for where the effective model came from (E0.3)."""
    labels = {
        "argument": "explicit argument",
        "env": "JEV_MODEL environment variable",
        ".jev.json": "repository .jev.json",
        "provider_default": "provider default",
    }
    source = getattr(client, "model_source", "provider_default")
    return labels.get(source, source)


def cmd_status(args: argparse.Namespace) -> int:
    client = _build_client(args)
    key = client.api_key
    print("\n=== JEV HARNESS STATUS ===")
    if client.is_live:
        if client.provider == "opencode":
            print("Provider:    OPENCODE ZEN (Free Tier)")
            print(f"Endpoint:    {client.base_url}")
            print("Engine Mode: LIVE (OpenCode Zen Free Community Model)")
        elif client.provider == "commandcode":
            masked = key[:6] + "..." + key[-4:] if key and len(key) > 10 else "***"
            print(f"API Key:     Configured ({masked})")
            print("Provider:    COMMAND CODE (Free $0.00/M Deal - typesafe/jev)")
            print(f"Endpoint:    {client.base_url}")
            print("Engine Mode: LIVE")
        else:
            masked = key[:6] + "..." + key[-4:] if key and len(key) > 10 else "***"
            print(f"API Key:     Configured ({masked})")
            print(f"Provider:    {client.provider.upper()}")
            print(f"Endpoint:    {client.base_url}")
            print("Engine Mode: LIVE")
    else:
        print("API Key:     NOT DETECTED")
        print("Engine Mode: SIMULATION / MOCK (fully offline deterministic engine)")
        print("\nNo key is required: offline mode is free and makes zero network calls.")
        print("To enable LIVE mode, pick one provider:")
        print("  - OpenCode Zen (free tier): export JEV_PROVIDER=opencode OPENCODE_API_KEY=<key>  # https://opencode.ai/auth")
        print("  - TypeSafe AI (direct):     export TYPESAFE_API_KEY=<key>                       # https://console.typesafe.ai")
        print("  - Command Code:             export CMD_API_KEY=<key>                            # https://commandcode.ai/signup")
        print("  - OpenRouter (alpha only):  export OPENROUTER_API_KEY=<key>")
        print("  - Vercel AI Gateway:        export AI_GATEWAY_API_KEY=<key>")
        print("  (or save it in the repo .env / .jev.json, or ~/.config/jev/credentials.env)")
    print(f"Model:       {client.model}")
    print(f"Model origin: {_model_origin_label(client)}")
    if client.model == "jev-latest":
        print("Note:        'jev-latest' is a moving alias - pin a version (e.g. \"model\": \"jev-1.13.0\") when your thresholds are calibrated.")
    print("==========================\n")
    return 0


def cmd_replay(args: argparse.Namespace) -> int:
    """Runs the labelled corpus, reports calibration and enforces the regression gate (E1.2)."""
    from pathlib import Path as _Path

    from .replay import find_baseline_path, render_console, render_json, replay

    corpus_dir = _Path(getattr(args, "corpus", "tests/corpus"))
    engine = "mock" if getattr(args, "mock", False) or getattr(args, "engine", "mock") == "mock" else "live"
    client = JevClient(force_mock=engine == "mock", provider=getattr(args, "provider", None))

    baseline_arg = getattr(args, "baseline", None)
    baseline_path = _Path(baseline_arg) if baseline_arg else find_baseline_path(corpus_dir)
    try:
        outcome, findings, _payload = replay(
            corpus_dir,
            client,
            engine,
            baseline_path=baseline_path,
            update_baseline=bool(getattr(args, "update_baseline", False)),
            allow_regression=bool(getattr(args, "allow_regression", False)),
            write_report=not getattr(args, "no_report", False),
        )
    except (FileNotFoundError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2

    if getattr(args, "json", False):
        print(render_json(outcome, findings, engine, client.model))
    else:
        print(render_console(outcome, findings, engine, client.model))
        if getattr(args, "no_report", False):
            print("(report not rewritten: --no-report)")
        else:
            print(f"Report written to: {corpus_dir.resolve().parent.parent / 'docs' / 'REPLAY_REPORT.md'}")
    return 1 if findings and not getattr(args, "allow_regression", False) else 0


def cmd_doctor(args: argparse.Namespace) -> int:
    """E2.4: self-diagnosis with a fix command per problem (never prints secrets)."""
    from .doctor import render_console, run_doctor

    report = run_doctor(live=bool(getattr(args, "live", False)), check_git_hook=not getattr(args, "no_git", False))
    if getattr(args, "json", False):
        print(json.dumps(report.as_dict(), indent=2))
    else:
        print(render_console(report))
    return 1 if report.failed else 0


def cmd_receipts(args: argparse.Namespace) -> int:
    """Shows the local decision receipts (E1.3): audit trail, hashes only, no raw logs."""
    from .receipts import read_receipts, receipts_path, receipts_summary

    tail = int(getattr(args, "tail", 20) or 20)
    records = read_receipts(tail=tail)
    if getattr(args, "json", False):
        print(json.dumps({"path": str(receipts_path()), "summary": receipts_summary(), "receipts": records}, indent=2))
        return 0
    if not records:
        print(f"No receipts recorded yet ({receipts_path()}).")
        print("Receipts are Python-side, 0600, and disabled with --no-receipts or \"receipts\": false.")
        return 0
    print("\n=== JEV DECISION RECEIPTS (newest last) ===")
    for record in records:
        print(
            f"{record.get('utc', '')}  {str(record.get('gate', '?')):<17} "
            f"{str(record.get('decision', '')):<16} conf={record.get('confidence')} "
            f"hash={record.get('input_hash')} mock={record.get('is_mock')}"
            + (f" degraded={record.get('degraded_reason')}" if record.get("degraded_reason") else "")
            + (" [SHADOW]" if record.get("shadow") else "")
        )
    summary = receipts_summary()
    print("-------------------------------------------")
    print(
        f"{summary['total']} receipt(s); retention: ttl={summary['retention_ttl_days']}d, "
        f"max={summary['retention_max_entries']}; file: {receipts_path()}"
    )
    print("===========================================\n")
    return 0


def cmd_metrics(args: argparse.Namespace) -> int:
    from .session import load_session, reset_metrics
    if getattr(args, "reset", False):
        reset_metrics()
        print("\n[OK] Jev Harness metrics reset successfully.\n")
        return 0

    s = load_session()
    from .cache import stats as cache_stats
    cache_stats = cache_stats(prune=True)
    if getattr(args, "json", False):
        print(
            json.dumps(
                {
                    "total_triage_calls": s.total_triage_calls,
                    "skipped_llm_calls": s.skipped_llm_calls,
                    "abort_guards_triggered": s.abort_guards_triggered,
                    "deterministic_routes": s.deterministic_routes,
                    "effort_modulations": s.effort_modulations,
                    "nudge_continuations": s.nudge_continuations,
                    "estimated_tokens_saved": s.estimated_tokens_saved,
                    "estimated_cost_saved_usd": round(s.estimated_cost_saved_usd, 2),
                    "estimates_are_heuristic": True,
                    "measured_requests": s.measured_requests,
                    "measured_input_tokens": s.measured_input_tokens,
                    "measured_output_tokens": s.measured_output_tokens,
                    "measured_cost_usd": round(s.measured_cost_usd, 9),
                    "cache": cache_stats,
                    "measured_avg_duration_ms": (
                        round(s.measured_duration_ms / s.measured_requests, 1) if s.measured_requests else None
                    ),
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
        print(f"Continuation Nudges:     {s.nudge_continuations} (Jev Nudge Gate)")
        print(f"Estimated Tokens Saved:  ⚡ {s.estimated_tokens_saved:,} tokens (heuristic estimate)")
        print(f"Estimated API Cost Saved: 💸 ${s.estimated_cost_saved_usd:.2f} USD (heuristic estimate)")
        if s.measured_requests:
            print(
                f"Measured (live):         {s.measured_requests} request(s), "
                f"{s.measured_input_tokens:,} in / {s.measured_output_tokens:,} out tokens, "
                f"${s.measured_cost_usd:.4f} provider cost, "
                f"{s.measured_duration_ms / s.measured_requests:.0f} ms avg"
            )
        else:
            print("Measured (live):         none yet (offline decisions are not network measurements)")
        hit_rate = cache_stats.get("hit_rate")
        print(
            f"Decision Cache:          {cache_stats['entries']} entr(ies), "
            f"{cache_stats['hits']} hit(s) / {cache_stats['misses']} miss(es), "
            f"hit-rate {'n/a' if hit_rate is None else f'{hit_rate * 100:.1f}%'}, "
            f"{cache_stats['debounced']} coalesced (debounce), ttl={cache_stats['ttl_seconds']}s"
        )
        print(
            "Assumption Model:        "
            f"{ASSUMED_TOKENS_PER_TRIAGE_SKIP:,} tokens/${ASSUMED_COST_PER_TRIAGE_SKIP_USD:.2f} per intercepted triage; "
            f"{ASSUMED_TOKENS_PER_ABORT:,} tokens/${ASSUMED_COST_PER_ABORT_USD:.2f} per aborted doom loop"
        )
        print("=======================================\n")
    return 0


def project_bin(cwd: Path, name: str, default: str = "") -> str:
    """Returns the project venv binary (e.g. ./.venv/bin/python) when present, else `default`
    or the bare command name. Hook-safe: paths are relative to the repository root, which is
    the working directory Git uses to run hooks."""
    candidates = (
        Path(".venv") / "bin" / name,
        Path("venv") / "bin" / name,
        Path(".venv") / "Scripts" / f"{name}.exe",
        Path("venv") / "Scripts" / f"{name}.exe",
    )
    for rel in candidates:
        try:
            if (cwd / rel).exists():
                return f"./{rel.as_posix()}"
        except Exception:
            continue
    return default or name


def detect_test_command(cwd: Path, override: str = "") -> str:
    """Best-effort detection of the repository test command for the generated git hook.
    Honours an explicit override and prefers the project virtualenv interpreter."""
    if override and override.strip():
        return override.strip()
    python_bin = project_bin(cwd, "python", "python3")
    package_json = cwd / "package.json"
    if package_json.is_file():
        try:
            scripts = json.loads(package_json.read_text(encoding="utf-8")).get("scripts", {})
            if isinstance(scripts, dict) and scripts.get("test"):
                return "npm test --silent"
        except Exception:
            pass
    if (cwd / "Cargo.toml").is_file():
        return "cargo test --quiet"
    python_markers = (
        (cwd / "pytest.ini").is_file()
        or (cwd / "tox.ini").is_file()
        or (cwd / "pyproject.toml").is_file()
        and "[tool.pytest" in (cwd / "pyproject.toml").read_text(encoding="utf-8", errors="ignore")
    )
    if python_markers:
        return f"{python_bin} -m pytest -q"
    if (cwd / "pyproject.toml").is_file() or (cwd / "setup.py").is_file() or (cwd / "tests").is_dir():
        return f"{python_bin} -m unittest"
    return ""


def build_git_hook(test_cmd: str, jev_bin: str = "jev-harness") -> str:
    """Returns the generated pre-commit hook: the runner decides, Jev only advises.
    `jev_bin` may be an absolute or repo-relative path to the CLI (project virtualenv)."""
    command = test_cmd or ""
    return (
        "#!/bin/sh\n"
        "# Jev Harness pre-commit gate (generated by `jev-harness init --git`).\n"
        "# The test runner decides whether the commit is blocked; Jev only triages a failing\n"
        "# run so it can be fixed deterministically when possible.\n"
        "# Regenerate with: jev-harness init --git [--test-cmd \"<your test command>\"]\n"
        "\n"
        f'TEST_CMD="{command}"\n'
        f'JEV_BIN="{jev_bin}"\n'
        "\n"
        'if [ -z "$TEST_CMD" ]; then\n'
        '  echo "[jev] No test command detected. Edit this hook and set TEST_CMD (e.g. npm test)." >&2\n'
        "  exit 0\n"
        "fi\n"
        "\n"
        'if ! TEST_OUTPUT=$(sh -c "$TEST_CMD" 2>&1); then\n'
        "  printf '%s\\n' \"$TEST_OUTPUT\" | \"$JEV_BIN\" test-gate\n"
        "  exit 1\n"
        "fi\n"
        "exit 0\n"
    )


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
    if local_skill_file.exists():
        print(f"  [=] Existing agent skill preserved: {local_skill_file.relative_to(cwd)}")
    else:
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
            '# Jev Harness provider credentials. Offline mode needs NO key (zero network calls).\n# Docs: https://github.com/ismaelsoilet/jev-harness/blob/main/docs/AGENT_INTEGRATION_GUIDE.md\n#\n# OpenCode Zen (free tier) - https://opencode.ai/auth\n# JEV_PROVIDER=opencode\n# OPENCODE_API_KEY="your_key_here"\n#\n# TypeSafe AI (direct) - https://console.typesafe.ai\n# TYPESAFE_API_KEY="your_key_here"\n#\n# Command Code - https://commandcode.ai/signup  (or run: cmd login)\n# CMD_API_KEY="your_key_here"\n#\n# OpenRouter (alpha access only)\n# OPENROUTER_API_KEY="your_key_here"\n#\n# Vercel AI Gateway\n# AI_GATEWAY_API_KEY="your_key_here"\n',
            encoding="utf-8",
        )
        print(f"  [+] Created env template: {env_example.relative_to(cwd)}")

    # 3b. Keep local decision state out of version control (E3.8)
    from .receipts import ensure_state_ignored

    if ensure_state_ignored(cwd):
        print("  [+] Added '.jev/' to .gitignore (local sessions, receipts and cache)")

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
                                "command": str((cwd / project_bin(cwd, "jev-mcp", "jev-mcp").lstrip("./")).resolve())
                    if project_bin(cwd, "jev-mcp", "") else "jev-mcp",
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
    git_gate_active = True
    if getattr(args, "git", False) or getattr(args, "all", False):
        git_hooks = cwd / ".git" / "hooks"
        if git_hooks.exists():
            pre_commit = git_hooks / "pre-commit"
            marker = "Jev Harness pre-commit gate"
            test_cmd = detect_test_command(cwd, getattr(args, "test_cmd", "") or "")
            jev_bin = project_bin(cwd, "jev-harness", "jev-harness")
            hook_script = build_git_hook(test_cmd, jev_bin)
            existing = ""
            if pre_commit.exists():
                try:
                    existing = pre_commit.read_text(encoding="utf-8", errors="ignore")
                except Exception:
                    existing = ""
            if existing and marker.lower() not in existing.lower():
                sample = git_hooks / "pre-commit.jev"
                sample.write_text(hook_script, encoding="utf-8")
                sample.chmod(0o755)
                git_gate_active = False
                print(
                    "  [!] An existing pre-commit hook was preserved; the Jev gate is NOT active yet. "
                    f"Merge {sample.relative_to(cwd)} into it (or use the pre-commit framework) to enable it."
                )
            else:
                pre_commit.write_text(hook_script, encoding="utf-8")
                pre_commit.chmod(0o755)
                detected = detect_test_command(cwd, getattr(args, "test_cmd", "") or "")
                detail = f" (test command: {detected})" if detected else " (no test command detected yet)"
                print(f"  [+] Installed Git pre-commit guardrail: {pre_commit.relative_to(cwd)}{detail}")

    if git_gate_active:
        print("\n[OK] Repository configured successfully! You can now run 'jev-harness status'.\n")
    else:
        print(
            "\n[!] Repository configured, but the Jev commit gate is NOT active "
            "(an existing hook was preserved). Merge .git/hooks/pre-commit.jev to enable it.\n"
        )
    return 0


def cmd_export(args: argparse.Namespace) -> int:
    """`export foreman`: writes the operator bundle (preset TOML + companion class + README)."""
    from .integrations import foreman as foreman_integration
    from .integrations import foreman_responsibility

    out_dir = Path(getattr(args, "out_dir", None) or foreman_integration.FOREMAN_DEFAULT_OUT_DIR)
    if ".foreman" in out_dir.resolve().parts:
        print(
            "Error: refusing to write into a '.foreman/' directory - that path is Foreman run "
            "state, not configuration. Point --out-dir at the Foreman installation's "
            "responsibilities directory instead.",
            file=sys.stderr,
        )
        return 2
    out_dir.mkdir(parents=True, exist_ok=True)

    preset = out_dir / foreman_integration.FOREMAN_PRESET_FILENAME
    preset.write_text(foreman_integration.FOREMAN_RESPONSIBILITY_TOML, encoding="utf-8")
    companion = out_dir / foreman_integration.FOREMAN_COMPANION_FILENAME
    companion.write_text(
        Path(foreman_responsibility.__file__).read_text(encoding="utf-8"), encoding="utf-8"
    )
    readme = out_dir / foreman_integration.FOREMAN_README_FILENAME
    readme.write_text(foreman_integration.FOREMAN_OPERATOR_README, encoding="utf-8")

    if getattr(args, "json", False):
        print(
            json.dumps(
                {
                    "out_dir": str(out_dir),
                    "files": [preset.name, companion.name, readme.name],
                    "activation": f"foreman run --responsibilities-dir {out_dir}",
                },
                indent=2,
            )
        )
        return 0
    print(f"\n[OK] Foreman operator bundle written to: {out_dir}")
    print(f"  [+] {preset.name}")
    print(f"  [+] {companion.name}")
    print(f"  [+] {readme.name}")
    print("\nNext steps (the pair ships together; Foreman exits 2 when either half is missing):")
    print("  1. Install the class in the Foreman environment (pip install jev-harness,")
    print("     then pass JevTriageResponsibility() via configured_registry(additional=[...])")
    print("     or register it in Foreman's builtin_registry).")
    print(f"  2. Run: foreman run --repo <repo> --job \"<job>\" --responsibilities-dir {out_dir}")
    print("     (or export FOREMAN_RESPONSIBILITIES_DIR=<that directory>).")
    print("  Never place these files in a managed repository's .foreman/ directory.\n")
    return 0


def cmd_test_gate(args: argparse.Namespace) -> int:
    log_path = getattr(args, "log", None)
    raw_input = log_path or getattr(args, "sample", None) or getattr(args, "log_pos", None)
    if log_path and not _path_is_file(log_path):
        # `--log` is documented as a file: a typo must not be triaged as if it were the log text.
        print(f"Error: log file not found: {log_path}", file=sys.stderr)
        print(
            "Hint: pass the log text as a positional argument, use --sample for a literal string, "
            "or pipe it via stdin.",
            file=sys.stderr,
        )
        return 2
    text = _read_input(raw_input).strip()
    if not text:
        print("Error: No test failure log provided. Pass --log <file_or_string> or as positional argument or pipe via stdin.", file=sys.stderr)
        return 2

    force_mock = getattr(args, "mock", False)
    provider = getattr(args, "provider", None)
    is_json = getattr(args, "json", False)
    client = _build_client(args)
    res = triage_test_failure(
        text,
        client=client,
        record_session=True,
        extra_state=_extra_state(args),
        allow_auto_recovery=bool(getattr(args, "allow_auto_recovery", False)),
    )
    _receipt(args, "test-gate", text, res, client, res.category)

    exit_code = 0 if res.skip_llm else 1
    shadow_payload = {"shadow": True, "would_exit": exit_code} if _shadow_enabled(args) else {}
    if is_json:
        print(
            json.dumps(
                {
                    "category": res.category,
                    "uncertainty": getattr(res, "uncertainty", None),
                    "confidence": res.confidence,
                    "skip_llm": res.skip_llm,
                    "skip_llm_prob": res.skip_llm_prob,
                    "severity_score": res.severity_score,
                    "action_recommendation": res.action_recommendation,
                    "recommendation": res.action_recommendation,
                    "is_mock": res.is_mock,
                    "degraded_reason": getattr(res, "degraded_reason", ""),
                    "recovery": getattr(res, "recovery", None),
                    **shadow_payload,
                },
                indent=2,
            )
        )
    else:
        print("\n--- JEV TEST TRIAGE VERDICT ---")
        print(f"Category:        {res.category.upper()}")
        if res.category == "no_failure":
            print("No failure detected: the test run appears successful. Nothing to triage.")
            print("Mode:            [DETERMINISTIC]")
            print("--------------------------------\n")
            return 0
        print(f"Confidence:      {res.confidence * 100:.1f}%")
        print(f"Skip LLM Call:   {'YES (Save Tokens!)' if res.skip_llm else 'NO (Dispatch to System 2)'}")
        print(f"Skip Prob:       {res.skip_llm_prob * 100:.1f}%")
        print(f"Severity Score:  {res.severity_score:.1f} / 4.0")
        print(f"Recommendation:  {res.action_recommendation}")
        recovery = getattr(res, "recovery", None)
        if recovery:
            safe = "yes" if recovery["is_safe_auto_run"] else "no"
            print(f"Recovery:        {recovery['package_manager']} install {recovery['package_name']} "
                  f"(argv: {' '.join(recovery['argv'])}; safe to auto-run: {safe})")
            print(f"                 {recovery['rationale']}")
        if res.is_mock:
            print(f"Mode:            {_mock_mode_label(res)}")
        else:
            print(f"Mode:            [LIVE: {client.provider.upper()}]")
        print("--------------------------------\n")

    return _shadow_wrap(args, exit_code)


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
    client = _build_client(args)
    res = should_abort_trajectory(
        plan, recent_attempts_summary=history, client=client, record_session=True, extra_state=_extra_state(args)
    )
    _receipt(args, "abort-check", f"{plan}\n{history}", res, client, "abort" if res.should_abort else "proceed")

    if is_json:
        print(
            json.dumps(
                {
                    "should_abort": res.should_abort,
                    "uncertainty": getattr(res, "uncertainty", None),
                    "cached": getattr(res, "cached", False),
                    "debounced": getattr(res, "debounced", False),
                    "abort_probability": res.abort_probability,
                    "action": res.action,
                    "viability_score": res.viability_score,
                    "reasoning_summary": res.reasoning_summary,
                    "summary": res.reasoning_summary,
                    "is_mock": res.is_mock,
                    "degraded_reason": getattr(res, "degraded_reason", ""),
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
            print(f"Mode:             {_mock_mode_label(res)}")
        else:
            print(f"Mode:             [LIVE: {client.provider.upper()}]")
        print("------------------------------\n")

    return _shadow_wrap(args, 1 if res.should_abort else 0)


def cmd_route(args: argparse.Namespace) -> int:
    raw_task = getattr(args, "task", None) or getattr(args, "task_pos", None)
    task = _read_input(raw_task).strip()
    if not task:
        print("Error: No task provided. Pass --task <text_or_path> or as positional argument.", file=sys.stderr)
        return 2

    force_mock = getattr(args, "mock", False)
    provider = getattr(args, "provider", None)
    is_json = getattr(args, "json", False)
    client = _build_client(args)
    res = route_model_tier(task, client=client, record_session=True, extra_state=_extra_state(args))
    _receipt(args, "route", task, res, client, res.selected_tier)

    if is_json:
        print(
            json.dumps(
                {
                    "selected_tier": res.selected_tier,
                    "uncertainty": getattr(res, "uncertainty", None),
                    "confidence": res.confidence,
                    "complexity_score": res.complexity_score,
                    "recommended_model": res.recommended_model,
                    "rationale": res.rationale,
                    "is_mock": res.is_mock,
                    "degraded_reason": getattr(res, "degraded_reason", ""),
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
            print(f"Mode:              {_mock_mode_label(res)}")
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
    client = _build_client(args)
    res = verify_step_completion(criteria, output, client=client, extra_state=_extra_state(args))
    _receipt(args, "verify", f"{criteria}\n{output}", res, client, "verified" if res.is_verified else "not_verified")

    if is_json:
        print(
            json.dumps(
                {
                    "is_verified": res.is_verified,
                    "uncertainty": getattr(res, "uncertainty", None),
                    "satisfaction_probability": res.satisfaction_probability,
                    "rigor_score": res.rigor_score,
                    "confidence": res.confidence,
                    "needs_rework": res.needs_rework,
                    "is_mock": res.is_mock,
                    "degraded_reason": getattr(res, "degraded_reason", ""),
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
            print(f"Mode:               {_mock_mode_label(res)}")
        else:
            print(f"Mode:               [LIVE: {client.provider.upper()}]")
        print("--------------------------------\n")

    return _shadow_wrap(args, 0 if res.is_verified else 1)


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
    supported_raw = getattr(args, "supported_efforts", None)
    supported_efforts = [s.strip() for s in supported_raw.split(",")] if supported_raw else None
    max_lease_steps = getattr(args, "max_lease_steps", 10) or 10

    client = _build_client(args)
    res = modulate_reasoning_effort(
        context,
        extra_state=_extra_state(args),
        provider=provider,
        model=model,
        session_context_tokens=session_context_tokens,
        supported_efforts=supported_efforts,
        max_lease_steps=max_lease_steps,
        client=client,
        record_session=True,
        use_lease=bool(getattr(args, "use_lease", False)),
    )
    _receipt(args, "reasoning-effort", context, res, client, res.effort)

    if is_json:
        print(
            json.dumps(
                {
                    "effort": res.effort,
                    "uncertainty": getattr(res, "uncertainty", None),
                    "confidence": res.confidence,
                    "complexity_score": res.complexity_score,
                    "rationale": res.rationale,
                    "provider": res.provider,
                    "provider_params": res.provider_params,
                    "is_reasoning_supported": res.is_reasoning_supported,
                    "cache_safe_recommendation": res.cache_safe_recommendation,
                    "lease_steps": res.lease_steps,
                    "is_mock": res.is_mock,
                    "degraded_reason": getattr(res, "degraded_reason", ""),
                },
                indent=2,
            )
        )
    else:
        print("\n=== JEV REASONING EFFORT GATE ===")
        print(f"Assigned Effort:   {res.effort.upper()}")
        print(f"Stability Lease:   {res.lease_steps} generation(s)")
        print(f"Target Provider:   {res.provider.upper()}")
        print(f"Confidence:        {res.confidence * 100:.1f}%")
        print(f"Complexity Score:  {res.complexity_score:.1f} / 4.0")
        print(f"Rationale:         {res.rationale}")
        print(f"Provider Payload:  {json.dumps(res.provider_params)}")
        print(f"Cache Advisory:    {res.cache_safe_recommendation}")
        if not res.is_reasoning_supported:
            print("WARNING: Target model is direct single-pass; do NOT inject reasoning params!")
        if res.is_mock:
            print(f"Engine Mode:       {_mock_mode_label(res)}")
        else:
            print(f"Engine Mode:       [LIVE: {client.provider.upper()}]")
        print("=================================\n")

    return 0


def cmd_nudge_gate(args: argparse.Namespace) -> int:
    raw_transcript = getattr(args, "transcript_pos", None) or getattr(args, "transcript", None)
    transcript = _read_input(raw_transcript, allow_stdin=True).strip()
    if not transcript:
        print(
            "Error: No transcript tail provided. Pass --transcript <text_or_path>, positional arg, or pipe via stdin.",
            file=sys.stderr,
        )
        return 2

    prev_nudge = _read_input(getattr(args, "previous_nudge", ""), allow_stdin=False).strip()
    threshold = float(getattr(args, "threshold", 0.5))
    force_mock = getattr(args, "mock", False)
    provider = getattr(args, "provider", None)
    is_json = getattr(args, "json", False)

    client = _build_client(args)
    res = should_nudge_continuation(
        extra_state=_extra_state(args),
        transcript_tail=transcript,
        previous_nudge_summary=prev_nudge,
        threshold=threshold,
        client=client,
        record_session=True,
    )
    _receipt(
        args,
        "nudge-gate",
        transcript,
        res,
        client,
        "nudge" if res.should_nudge else f"hold:{res.workflow_phase}",
    )

    if is_json:
        print(
            json.dumps(
                {
                    "should_nudge": res.should_nudge,
                    "uncertainty": getattr(res, "uncertainty", None),
                    "cached": getattr(res, "cached", False),
                    "debounced": getattr(res, "debounced", False),
                    "nudge_probability": res.nudge_probability,
                    "waiting_probability": res.waiting_probability,
                    "progress_probability": res.progress_probability,
                    "workflow_phase": res.workflow_phase,
                    "suggested_nudge_prompt": res.suggested_nudge_prompt,
                    "rationale": res.rationale,
                    "is_mock": res.is_mock,
                    "degraded_reason": getattr(res, "degraded_reason", ""),
                },
                indent=2,
            )
        )
    else:
        print("\n=== JEV CONTINUATION NUDGE GATE ===")
        print(f"Should Nudge:      {'YES (Inject Continuation)' if res.should_nudge else 'NO (Stop & Yield to User)'}")
        print(f"Workflow Phase:    {res.workflow_phase.upper()}")
        print(f"Nudge Prob:        {res.nudge_probability * 100:.1f}%")
        print(f"Waiting Prob:      {res.waiting_probability * 100:.1f}%")
        print(f"Progress Prob:     {res.progress_probability * 100:.1f}%")
        print(f"Rationale:         {res.rationale}")
        if res.suggested_nudge_prompt:
            print(f"Suggested Prompt:  {res.suggested_nudge_prompt}")
        if res.is_mock:
            print(f"Engine Mode:       {_mock_mode_label(res)}")
        else:
            print(f"Engine Mode:       [LIVE: {client.provider.upper()}]")
        print("===============================================\n")

    return _shadow_wrap(args, 0 if res.should_nudge else 1)


def cmd_mcp(args: argparse.Namespace) -> int:
    from .mcp_server import run_mcp_server
    force_mock = getattr(args, "mock", False)
    provider = getattr(args, "provider", None)
    client = _build_client(args)
    run_mcp_server(client=client)
    return 0


def main() -> None:
    # Common flags shared between root and all subparsers
    common_parser = argparse.ArgumentParser(add_help=False)
    common_parser.add_argument("--mock", action="store_true", default=argparse.SUPPRESS, help="Force local simulation mode even if key is present")
    common_parser.add_argument("--json", action="store_true", default=argparse.SUPPRESS, help="Output machine-readable JSON")
    common_parser.add_argument(
        "--shadow",
        action="store_true",
        default=argparse.SUPPRESS,
        help="Decide and report, but never change the exit code (also via .jev.json)",
    )
    common_parser.add_argument(
        "--fail-closed",
        action="store_true",
        default=argparse.SUPPRESS,
        help="Surface provider errors instead of falling back to the offline engine (default: fail-open)",
    )
    common_parser.add_argument(
        "--state-json",
        default=None,
        help="Extra structured context for the gate state: inline JSON object or a path to a JSON file (E0.4)",
    )
    common_parser.add_argument(
        "--use-lease",
        action="store_true",
        default=argparse.SUPPRESS,
        help="Effort gate: reuse an active lease (opened by a previous decision) instead of calling",
    )
    common_parser.add_argument(
        "--tool-error",
        default=argparse.SUPPRESS,
        help="Report a tool failure: invalidates the effort lease (E3.7 break-glass) before deciding",
    )
    common_parser.add_argument(
        "--allow-auto-recovery",
        action="store_true",
        default=argparse.SUPPRESS,
        help="Allow is_safe_auto_run=true when the package is also declared in repo manifests (E3.6)",
    )
    common_parser.add_argument(
        "--no-cache",
        action="store_true",
        default=argparse.SUPPRESS,
        help="Bypass the local decision cache (.jev/cache.json) for this run",
    )
    common_parser.add_argument(
        "--no-receipts",
        action="store_true",
        default=argparse.SUPPRESS,
        help="Do not append this decision to .jev/receipts.jsonl",
    )
    common_parser.add_argument(
        "--retries",
        type=int,
        default=argparse.SUPPRESS,
        help="Maximum provider attempts for retryable failures (default: 3)",
    )
    common_parser.add_argument(
        "--provider",
        choices=["typesafe", "commandcode", "opencode", "openrouter", "vercel"],
        default=argparse.SUPPRESS,
        help="Override backend provider",
    )

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
    p_init.add_argument("--test-cmd", default="", help="Override the detected test command for the generated git hook")
    p_init.add_argument("--all", action="store_true", help="Configure all integrations (Cursor, Antigravity, Git)")
    p_init.set_defaults(func=cmd_init)

    # export (nested: `export foreman`)
    p_export = subparsers.add_parser(
        "export",
        parents=[common_parser],
        help="Write integration bundles for other tools (currently: foreman)",
    )
    export_targets = p_export.add_subparsers(dest="export_target", required=True)
    p_export_foreman = export_targets.add_parser(
        "foreman",
        parents=[common_parser],
        help="Write the Foreman operator bundle (preset TOML + companion class + README)",
    )
    p_export_foreman.add_argument(
        "--out-dir",
        default=None,
        help=f"Target directory (default: ./{FOREMAN_DEFAULT_OUT_DIR}/)",
    )
    p_export_foreman.set_defaults(func=cmd_export)

    # doctor
    p_doctor = subparsers.add_parser(
        "doctor",
        parents=[common_parser],
        help="Diagnose configuration, credentials, model, state and git hook (never prints secrets)",
    )
    p_doctor.add_argument("--live", action="store_true", help="Also spend ONE request to check the provider")
    p_doctor.add_argument("--no-git", action="store_true", help="Skip the git hook check")
    p_doctor.set_defaults(func=cmd_doctor)

    # receipts
    p_receipts = subparsers.add_parser(
        "receipts",
        parents=[common_parser],
        help="Show the local append-only decision receipts (audit trail)",
    )
    p_receipts.add_argument("--tail", type=int, default=20, help="Show only the newest N receipts (default: 20)")
    p_receipts.set_defaults(func=cmd_receipts)

    # metrics
    p_metrics = subparsers.add_parser("metrics", parents=[common_parser], help="Display token ROI, intercepted LLM calls, and cost savings")
    p_metrics.add_argument("--reset", action="store_true", help="Reset saved telemetry counters")
    p_metrics.set_defaults(func=cmd_metrics)

    # replay
    p_replay = subparsers.add_parser(
        "replay",
        parents=[common_parser],
        help="Replay the labelled corpus, print calibration metrics and enforce the regression gate",
    )
    p_replay.add_argument("--corpus", default="tests/corpus", help="Corpus directory of *.jsonl cases (default: tests/corpus)")
    p_replay.add_argument("--engine", choices=["mock", "live"], default="mock", help="Decision engine for the replay (default: mock)")
    p_replay.add_argument("--baseline", default=None, help="Baseline JSON to compare against (default: docs/REPLAY_REPORT.json)")
    p_replay.add_argument("--update-baseline", action="store_true", help="Record the current run as the new baseline (review before committing)")
    p_replay.add_argument("--allow-regression", action="store_true", help="Report findings but always exit 0")
    p_replay.add_argument("--no-report", action="store_true", help="Do not rewrite docs/REPLAY_REPORT.md")
    p_replay.set_defaults(func=cmd_replay)

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

    # reasoning-effort (alias: astra-jev, effort)
    p_effort = subparsers.add_parser(
        "reasoning-effort",
        aliases=["astra-jev", "effort"],
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
    p_effort.add_argument(
        "--supported-efforts",
        dest="supported_efforts",
        help="Comma-separated allowed effort levels (e.g. low,medium,high,xhigh)",
    )
    p_effort.add_argument(
        "--max-lease-steps",
        dest="max_lease_steps",
        type=int,
        default=10,
        help="Maximum generation stability lease steps (default: 10)",
    )
    p_effort.set_defaults(func=cmd_reasoning_effort)

    # verify
    p_verify = subparsers.add_parser("verify", parents=[common_parser], help="Verify if produced evidence satisfies acceptance criteria")
    p_verify.add_argument("--criteria", "-c", required=True, help="Acceptance criteria")
    p_verify.add_argument("--output", "-o", required=True, help="Produced evidence / output")
    p_verify.set_defaults(func=cmd_verify)

    # nudge-gate
    p_nudge = subparsers.add_parser(
        "nudge-gate",
        aliases=["nudge"],
        parents=[common_parser],
        help="Evaluate if agent stopped prematurely with unfinished work or unverified changes (Jev Nudge Gate)",
    )
    p_nudge.add_argument("transcript_pos", nargs="?", default=None, help="Recent agent transcript tail or path to transcript file")
    p_nudge.add_argument("--transcript", "-t", default=None, help="Recent agent transcript tail or path to transcript file")
    p_nudge.add_argument("--previous-nudge", "-P", default="", help="Summary of the previous nudge to verify progress")
    p_nudge.add_argument("--threshold", type=float, default=0.5, help="Probability threshold for nudge/waiting/progress (default: 0.5)")
    p_nudge.set_defaults(func=cmd_nudge_gate)

    # mcp
    p_mcp = subparsers.add_parser("mcp", parents=[common_parser], help="Run stdio MCP server for Cursor, Claude, Antigravity, OpenCode")
    p_mcp.set_defaults(func=cmd_mcp)

    args = parser.parse_args()
    tool_error = getattr(args, "tool_error", None)
    if tool_error:
        try:
            from .session import record_tool_error

            record_tool_error(str(tool_error))
            print(f"[JEV] Tool error recorded; the effort lease was invalidated: {tool_error}", file=sys.stderr)
        except Exception:
            pass
    try:
        sys.exit(args.func(args))
    except RuntimeError as e:
        # Shadow mode never breaks the caller's pipeline: report what would have happened.
        print(f"Error: {e}", file=sys.stderr)
        if _shadow_enabled(args):
            print("[SHADOW] would exit 2 - no action taken.", file=sys.stderr)
            sys.exit(0)
        sys.exit(2)
    except BrokenPipeError:
        try:
            devnull = os.open(os.devnull, os.O_WRONLY)
            os.dup2(devnull, sys.stdout.fileno())
        except Exception:
            pass
        sys.exit(0)


if __name__ == "__main__":
    main()
