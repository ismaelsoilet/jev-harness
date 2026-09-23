"""
E3.6 — structured recovery: turn "install the missing dependency" into *data*, never a shell string.

The design rules come straight from the audit that rejected the first draft:

* **no `shell_command`.** The output carries an `argv` list, so nothing can be re-parsed by a shell.
* **`is_safe_auto_run` defaults to `false`** and only becomes `true` when *both* hold: the package
  is already declared in a manifest/lockfile of this repository (the allowlist) **and** the caller
  passed `--allow-auto-recovery`.
* **validators per ecosystem** (PyPI PEP 503, npm `@scope/name`, crates) reject anything that is
  not a plain package name — `;`, backticks, `../`, leading `-` flags, spaces.
* **a decision derived from an untrusted log is never auto-executed.** The caller still owns the
  execution; the harness only says what would be safe.

Zero external dependencies: standard library only.
"""
from __future__ import annotations

import re
import shlex
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Ecosystem detectors, in the order they are tried against a failure log.
_PYPI_PATTERNS = (
    r"No module named ['\"]([A-Za-z0-9._+-]+)['\"]",
    r"ModuleNotFoundError:\s*No module named\s+([A-Za-z0-9._+-]+)",
    r"ImportError:\s*cannot import name\s+['\"]?([A-Za-z0-9._+-]+)['\"]?",
)
_NPM_PATTERNS = (
    r"Cannot find module ['\"]([@A-Za-z0-9._/-]+)['\"]",
    r"Module not found:\s*Error:\s*Can't resolve ['\"]([@A-Za-z0-9._/-]+)['\"]",
    r"error TS2307:\s*Cannot find module ['\"]([@A-Za-z0-9._/-]+)['\"]",
)
_CARGO_PATTERNS = (
    r"can't find crate for `([A-Za-z0-9_-]+)`",
    r"error\[E0463\]:\s*can't find crate for `([A-Za-z0-9_-]+)`",
    r"unresolved import `([A-Za-z0-9_]+)`",
)

# Where an already-declared dependency lives (the allowlist sources).
_MANIFEST_GLOBS = (
    "requirements*.txt",
    "*.lock",
    "uv.lock",
    "poetry.lock",
    "pyproject.toml",
    "Pipfile",
    "package.json",
    "package-lock.json",
    "yarn.lock",
    "pnpm-lock.yaml",
    "Cargo.toml",
    "Cargo.lock",
    "go.mod",
    "Gemfile",
    "Gemfile.lock",
)

# PEP 503 / npm / crates package-name shapes. Deliberately strict: anything else is refused.
_PYPI_NAME = re.compile(r"^[A-Za-z0-9]([A-Za-z0-9._-]*[A-Za-z0-9])?$")
_NPM_NAME = re.compile(r"^(?:@[a-z0-9][a-z0-9._-]*/)?[a-z0-9][a-z0-9._-]*$")
_CRATE_NAME = re.compile(r"^[A-Za-z][A-Za-z0-9_-]*$")

# A dependency that is only ever imported, never installed (stdlib / relative import).
_NOT_A_PACKAGE = {
    "os", "sys", "json", "re", "math", "time", "pathlib", "typing", "subprocess", "tempfile",
    "collections", "functools", "itertools", "dataclasses", "unittest", "logging", "hashlib",
    "asyncio", "concurrent", "socket", "threading", "traceback", "shutil", "glob", "io", "abc",
    "contextlib", "datetime", "importlib", "pkgutil", "signal", "stat", "string", "struct",
    "textwrap", "uuid", "warnings", "copy", "enum", "errno", "fnmatch", "inspect", "platform",
    "secrets", "sqlite3", "statistics", "csv", "base64", "binascii", "codecs", "decimal",
    "fractions", "heapq", "random", "selectors", "select", "ssl", "uuid", "zipfile", "gzip",
    "tarfile", "urllib", "http", "email", "html", "xml", "argparse", "configparser", "getpass",
    "shlex", "pprint", "queue", "weakref", "pickle", "shelve", "dbm", "zlib", "bz2", "lzma",
}

_INSTALL_COMMANDS: Dict[str, List[str]] = {
    "pypi": ["python", "-m", "pip", "install"],
    "npm": ["npm", "install"],
    "cargo": ["cargo", "add"],
}


def validate_package_name(name: str, manager: str) -> bool:
    """True only for a plain package name in the manager's own syntax."""
    if not name or len(name) > 200:
        return False
    if any(bad in name for bad in (";", "`", "$", "\\", "\n", " ", "\t", "\0", "..", "|", "&", ">", "<")):
        return False
    if name.startswith("-") or name.startswith("/") or name.startswith("."):
        return False
    if manager == "npm":
        return bool(_NPM_NAME.match(name))
    if manager == "cargo":
        return bool(_CRATE_NAME.match(name))
    return bool(_PYPI_NAME.match(name))


def detect_missing_package(log_text: str) -> Optional[Tuple[str, str]]:
    """Returns (package, manager) for a missing dependency, or None when there is no clear one.

    A name that is only a stdlib module is not a package: suggesting `pip install json` would be
    worse than saying nothing.
    """
    if not log_text:
        return None
    for patterns, manager in (
        (_PYPI_PATTERNS, "pypi"),
        (_NPM_PATTERNS, "npm"),
        (_CARGO_PATTERNS, "cargo"),
    ):
        for pattern in patterns:
            match = re.search(pattern, log_text)
            if not match:
                continue
            name = match.group(1).strip()
            if manager == "npm" and not name.startswith("@") and "/" in name:
                # A relative import (`./utils`, `../lib`) is a project path, not a package.
                continue
            if manager == "pypi" and name.split(".")[0] in _NOT_A_PACKAGE:
                continue
            if validate_package_name(name, manager):
                return name, manager
    return None


def declared_in_repository(name: str, manager: str, repo_root: Optional[Path] = None) -> bool:
    """The allowlist: is this dependency already declared in a manifest/lockfile of the repo?"""
    root = Path(repo_root or Path.cwd())
    if not root.is_dir():
        return False
    needle = name.lower().replace("_", "-") if manager == "pypi" else name.lower()
    # A declaration looks like a dependency line, not prose: `pkg`, `pkg==1`, `"pkg": "^1"`,
    # `pkg = "1"`, `@scope/pkg@1`. Matching only those keeps a package *mentioned* in a
    # description from counting as an installed dependency (the audit found that false positive).
    token = re.compile(rf"(?<![A-Za-z0-9._-]){re.escape(needle)}(?![A-Za-z0-9._-])")
    for glob in _MANIFEST_GLOBS:
        for candidate in sorted(root.glob(glob)):
            if not candidate.is_file() or candidate.stat().st_size > 2_000_000:
                continue
            try:
                content = candidate.read_text(encoding="utf-8", errors="replace").lower()
            except Exception:
                continue
            haystack = content.replace("_", "-") if manager == "pypi" else content
            for line in haystack.splitlines():
                stripped = line.strip()
                if not stripped or stripped.startswith(("#", "//", "description", "readme", "name =", "authors")):
                    continue
                if not token.search(stripped):
                    continue
                # Require a declaration shape next to the name.
                if re.search(
                    rf"(?<![A-Za-z0-9._-]){re.escape(needle)}\s*(?:[=<>!~^@:\"']|,|$)",
                    stripped,
                ) or f'"{needle}"' in stripped or f"'{needle}'" in stripped:
                    return True
    return False


def build_recovery(
    log_text: str,
    repo_root: Optional[Path] = None,
    allow_auto_recovery: bool = False,
) -> Optional[Dict[str, Any]]:
    """The `recovery` contract for one failure log, or None when there is nothing safe to say."""
    detected = detect_missing_package(log_text)
    if detected is None:
        return None
    name, manager = detected
    allowlisted = declared_in_repository(name, manager, repo_root)
    safe = bool(allowlisted and allow_auto_recovery)

    if allowlisted and not allow_auto_recovery:
        rationale = (
            f"'{name}' is declared in this repository's manifests, so installing it is consistent "
            "with the project — but automatic execution also requires --allow-auto-recovery."
        )
    elif allowlisted:
        rationale = f"'{name}' is declared in this repository's manifests and auto-recovery is enabled."
    else:
        rationale = (
            f"'{name}' is not declared in this repository's manifests/lockfiles: review it before "
            "installing anything (a missing dependency can also be a typosquatted name)."
        )

    return {
        "action_type": "install_dependency",
        "package_name": name,
        "package_manager": manager,
        "argv": [*_INSTALL_COMMANDS[manager], name],
        "is_safe_auto_run": safe,
        "rationale": rationale,
    }


def argv_is_shell_safe(argv: Any) -> bool:
    """A conservative guard used by the tests: the argv must survive re-serialisation unchanged."""
    if not isinstance(argv, list) or not argv or not all(isinstance(item, str) for item in argv):
        return False
    for item in argv:
        if shlex.quote(item) != item:
            return False
        if any(bad in item for bad in (";", "|", "&", "`", "$(", "\n", "\\")):
            return False
    return True
