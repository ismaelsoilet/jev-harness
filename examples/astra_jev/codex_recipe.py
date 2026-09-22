"""
⚡ Astra-Jev Codex Recipe
Demonstrates how to configure dynamic per-generation reasoning effort
for OpenAI Codex CLI using Jev System One as demonstrated by Vechen (@miu21590).

Codex Profile Configuration (~/.codex/config.toml or local repo .codex.toml):
--------------------------------------------------------------------------------
[models.astra-jev]
model = "gpt-6-astra"
default_effort = "medium"
pre_generation_hook = "jev-harness reasoning-effort --context \"$PROMPT_CONTEXT\" --target-provider openai --json"

Usage in terminal:
  codex -m astra-jev "Refactor authentication middleware and test with pytest"
--------------------------------------------------------------------------------
"""

import json
import os
import subprocess
from typing import Any, Dict


def get_dynamic_reasoning_effort(step_context: str, provider: str = "openai") -> Dict[str, Any]:
    """
    Evaluates the immediate step context with Jev System One in ~70ms (or <1ms locally)
    and returns the safe parameter payload.
    """
    cmd = [
        "jev-harness",
        "reasoning-effort",
        "--context",
        step_context,
        "--target-provider",
        provider,
        "--json",
    ]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return json.loads(proc.stdout)
    except Exception as exc:
        # Fallback to balanced default if CLI is unavailable
        return {"effort": "medium", "provider_params": {"reasoning_effort": "medium"}}


def main() -> None:
    print("=== Astra-Jev Codex Integration Demo ===\n")

    steps = [
        "git status e inspecionar arquivos modificados",
        "cat package.json e checar versao de dependencias",
        "Diagnosticar race condition e deadlocks de thread pool no kernel distribuido",
    ]

    for step in steps:
        print(f"Step Context: '{step}'")
        decision = get_dynamic_reasoning_effort(step)
        print(f"  -> Decision: {decision['effort'].upper()}")
        print(f"  -> API Payload injected: {decision['provider_params']}")
        print(f"  -> Cache Advisory: {decision.get('cache_safe_recommendation', '')}\n")


if __name__ == "__main__":
    main()
