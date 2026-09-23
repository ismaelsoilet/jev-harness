"""
E2.4 — `jev-harness doctor`: a self-diagnosis an agent (or a human) can act on.

Every check reports OK / AVISO / FALHA and, when something is wrong, the command that fixes it.
Secrets are never printed: credentials are reported by *source* and fingerprint only.

The doctor is deliberately cheap: it never touches the network unless `--live` is passed, in
which case it spends exactly one trivial request and reports the measured latency.
"""
from __future__ import annotations

import json
import os
import stat
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from . import __version__
from .client import MAX_STATE_CHARS, MAX_TOTAL_CHARS, JevClient, NoulQuestion
from .config import DEFAULT_ABORT_THRESHOLD, DEFAULT_SKIP_LLM_THRESHOLD, find_repo_config_path, load_repo_config

OK = "OK"
WARN = "AVISO"
FAIL = "FALHA"


@dataclass
class Check:
    name: str
    status: str
    detail: str
    fix: str = ""

    def as_dict(self) -> Dict[str, str]:
        return {"check": self.name, "status": self.status, "detail": self.detail, "fix": self.fix}


@dataclass
class DoctorReport:
    checks: List[Check] = field(default_factory=list)
    version: str = __version__
    runtime: str = "python"
    live: bool = False
    live_latency_ms: Optional[int] = None

    def add(self, name: str, status: str, detail: str, fix: str = "") -> None:
        self.checks.append(Check(name, status, detail, fix))

    @property
    def failed(self) -> List[Check]:
        return [c for c in self.checks if c.status == FAIL]

    @property
    def warnings(self) -> List[Check]:
        return [c for c in self.checks if c.status == WARN]

    def as_dict(self) -> Dict[str, Any]:
        return {
            "version": self.version,
            "runtime": self.runtime,
            "live": self.live,
            "live_latency_ms": self.live_latency_ms,
            "status": FAIL if self.failed else (WARN if self.warnings else OK),
            "checks": [c.as_dict() for c in self.checks],
        }


def _fingerprint(secret: Optional[str]) -> str:
    """A short, non-reversible hint so a user can tell *which* key is loaded."""
    if not secret:
        return "none"
    import hashlib

    return hashlib.sha256(secret.encode("utf-8")).hexdigest()[:8]


def _credential_source(client: JevClient) -> str:
    if os.getenv("JEV_PROVIDER") or any(
        os.getenv(name)
        for name in (
            "TYPESAFE_API_KEY",
            "CMD_API_KEY",
            "COMMAND_CODE_API_KEY",
            "OPENCODE_API_KEY",
            "OPENROUTER_API_KEY",
            "AI_GATEWAY_API_KEY",
            "VERCEL_API_KEY",
            "VERCEL_AI_GATEWAY_API_KEY",
        )
    ):
        return "environment variable"
    if find_repo_config_path() is not None or Path.cwd().joinpath(".env").is_file():
        return "repository .jev.json/.env"
    for candidate in (
        Path.home() / ".commandcode" / "auth.json",
        Path.home() / ".config" / "jev" / "credentials.env",
    ):
        if candidate.is_file():
            return str(candidate)
    return "none"


def run_doctor(  # noqa: C901 - a diagnostic is naturally a list of independent probes
    cwd: Optional[Path] = None,
    live: bool = False,
    check_git_hook: bool = True,
) -> DoctorReport:
    cwd = Path(cwd or Path.cwd())
    report = DoctorReport(live=live)

    # 1. Version / runtime
    report.add("version", OK, f"jev-harness {__version__} (python runtime)")

    # 2. Repository configuration
    config_path = find_repo_config_path()
    if config_path is None:
        report.add(
            "config",
            WARN,
            "no .jev.json found (defaults are in use)",
            "run: jev-harness init",
        )
    else:
        try:
            raw = json.loads(config_path.read_text(encoding="utf-8"))
            if not isinstance(raw, dict):
                raise ValueError("the file does not contain a JSON object")
            config = load_repo_config()
            report.add(
                "config",
                OK,
                f"{config_path} parsed (skip_llm_threshold={config['skip_llm_threshold']}, "
                f"abort_threshold={config['abort_threshold']}, shadow={bool(config.get('shadow', False))}, "
                f"receipts={bool(config.get('receipts', True))}, cache={bool(config.get('cache', True))})",
            )
        except Exception as exc:
            report.add(
                "config",
                FAIL,
                f"{config_path} is not usable ({type(exc).__name__}: {exc})",
                f"fix the JSON in {config_path} or delete it to fall back to defaults",
            )

    # 3. Credentials (never printing the secret itself)
    client = JevClient()
    if client.api_key:
        report.add(
            "credentials",
            OK,
            f"provider={client.provider} key detected (fingerprint sha256[:8]={_fingerprint(client.api_key)}, "
            f"source: {_credential_source(client)}) — the key itself is never printed",
        )
    else:
        report.add(
            "credentials",
            WARN,
            "no credentials found: offline (deterministic) mode is active and makes zero network calls",
            "optional: export TYPESAFE_API_KEY=... (or OPENCODE_API_KEY / CMD_API_KEY) for live decisions",
        )

    # 4. Effective model and where it came from
    report.add(
        "model",
        OK if client.model else FAIL,
        f"{client.model} (origin: {getattr(client, 'model_source', 'provider_default')})",
        "" if client.model else "set \"model\" in .jev.json or JEV_MODEL",
    )
    if client.model == "jev-latest":
        report.add(
            "model_pin",
            WARN,
            "'jev-latest' is a moving alias: a provider release can change your decisions",
            "pin a version once your thresholds are calibrated, e.g. \"model\": \"jev-1.13.0\"",
        )
    else:
        report.add("model_pin", OK, f"model is pinned to a version ({client.model})")

    # 5. Payload limits
    report.add(
        "payload_limits",
        OK,
        f"state <= {MAX_STATE_CHARS:,} code points, total <= {MAX_TOTAL_CHARS:,} ("
        "~32k/64k tokens); exceeding them exits 2 before any network call",
    )

    # 6. Local state: location, permissions, contents
    from .receipts import receipts_path, receipts_summary
    from .cache import stats as cache_stats

    state_file = receipts_path()
    state_dir = state_file.parent
    # The doctor reports state, it never mutates it: silently chmod-ing the user's files would
    # hide exactly the problem this check exists to surface.
    detail = f"state directory: {state_dir}"
    status = OK
    if not state_dir.exists():
        detail += " (not created yet; it appears after the first recorded decision)"
    elif os.name != "nt":
        mode = stat.S_IMODE(state_dir.stat().st_mode)
        if mode & 0o077:
            status = WARN
            detail += f" (permissions {oct(mode)}: other users can read your state)"
        else:
            detail += f" (permissions {oct(mode)})"
    report.add(
        "state_dir",
        status,
        detail,
        "chmod 700 the state directory shown above" if status == WARN else "",
    )

    receipts = receipts_summary()
    report.add(
        "receipts",
        OK,
        f"{receipts['total']} receipt(s); retention ttl={receipts['retention_ttl_days']}d, "
        f"max={receipts['retention_max_entries']}",
        "disable with \"receipts\": false or --no-receipts",
    )
    cache = cache_stats(prune=True)
    hit_rate = cache["hit_rate"]
    report.add(
        "cache",
        OK,
        f"{cache['entries']} entr(ies), hit-rate {'n/a' if hit_rate is None else f'{hit_rate * 100:.1f}%'}, "
        f"ttl={cache['ttl_seconds']}s, debounce={cache['debounce_seconds']}s",
        "bypass with --no-cache",
    )

    # 7. Git pre-commit hook
    if check_git_hook:
        hooks_dir = _git_hooks_dir(cwd)
        if hooks_dir is None:
            report.add("git_hook", OK, "not a git repository: no hook expected")
        else:
            hook = hooks_dir / "pre-commit"
            jev_hook = hooks_dir / "pre-commit.jev"
            if hook.is_file():
                content = _safe_read(hook)
                if "jev" in content.lower():
                    report.add("git_hook", OK, f"{hook} is active and references jev-harness")
                elif jev_hook.is_file():
                    report.add(
                        "git_hook",
                        WARN,
                        f"a foreign pre-commit hook is installed; the Jev gate lives in {jev_hook} but is NOT active",
                        f"merge {jev_hook} into {hook}, or set core.hooksPath to a directory that chains both",
                    )
                else:
                    report.add(
                        "git_hook",
                        WARN,
                        f"{hook} exists but does not reference jev-harness",
                        "run: jev-harness init --git",
                    )
            elif jev_hook.is_file():
                report.add(
                    "git_hook",
                    WARN,
                    f"{jev_hook} exists but no pre-commit hook is installed",
                    f"merge {jev_hook} into {hooks_dir / 'pre-commit'}",
                )
            else:
                report.add(
                    "git_hook",
                    WARN,
                    "no pre-commit hook: failing tests are not blocked before commit",
                    "run: jev-harness init --git",
                )

    # 8. Optional live probe (exactly one trivial request)
    if live:
        if not client.is_live:
            report.add(
                "provider_live",
                FAIL,
                "--live was requested but no credentials are configured",
                "export a provider key, then re-run: jev-harness doctor --live",
            )
        else:
            started = time.monotonic()
            try:
                response = client.system_one(
                    "doctor connectivity probe",
                    {"probe": NoulQuestion("Is this request answered?")},
                    gate="doctor",
                )
                elapsed = int((time.monotonic() - started) * 1000)
                report.live_latency_ms = elapsed
                if response.is_mock:
                    report.add(
                        "provider_live",
                        WARN,
                        f"{client.provider} did not answer live: degraded "
                        f"(degraded_reason={response.degraded_reason or 'unknown'}) in {elapsed} ms",
                        "check the key/network, or keep using the offline engine",
                    )
                else:
                    report.add(
                        "provider_live",
                        OK,
                        f"{client.provider} answered in {elapsed} ms (model={response.model}, "
                        f"usage={response.usage.get('input_tokens', 0)} in tokens, cost=${response.cost_usd:.8f})",
                    )
            except Exception as exc:
                report.add(
                    "provider_live",
                    FAIL,
                    f"live probe failed: {type(exc).__name__}: {exc}",
                    "verify the key and network, or use the offline engine (no key required)",
                )

    return report


def _safe_read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return ""


def _git_hooks_dir(cwd: Path) -> Optional[Path]:
    """Repo hooks dir taking `core.hooksPath` into account, or None outside a repository."""
    git_dir = cwd / ".git"
    if git_dir.is_file():  # worktree / submodule pointer
        content = _safe_read(git_dir).strip()
        if content.startswith("gitdir:"):
            git_dir = Path(content.split(":", 1)[1].strip())
            if not git_dir.is_absolute():
                git_dir = (cwd / git_dir).resolve()
    if not git_dir.is_dir():
        return None
    config_file = git_dir / "config"
    text = _safe_read(config_file)
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.lower().startswith("hookspath"):
            _, _, value = stripped.partition("=")
            value = value.strip().strip('"')
            if value:
                candidate = Path(os.path.expanduser(value))
                return candidate if candidate.is_absolute() else (git_dir.parent / candidate)
    return git_dir / "hooks"


def render_console(report: DoctorReport) -> str:
    lines = ["", "=== JEV HARNESS DOCTOR ===", f"Version: {report.version}  Runtime: {report.runtime}"]
    lines.append("")
    for check in report.checks:
        lines.append(f"[{check.status:<5}] {check.name:<15} {check.detail}")
        if check.fix:
            lines.append(f"        ↳ {check.fix}")
    lines.append("")
    if report.failed:
        lines.append(f"RESULT: {len(report.failed)} failure(s) — see the fixes above.")
    elif report.warnings:
        lines.append(f"RESULT: healthy with {len(report.warnings)} warning(s).")
    else:
        lines.append("RESULT: everything checks out.")
    lines.append("===========================\n")
    return "\n".join(lines)
