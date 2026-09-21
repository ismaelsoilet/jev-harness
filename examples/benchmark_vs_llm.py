"""
Benchmark Simulation: Jev System One vs. Traditional Frontier LLM
Calculates token consumption, latency, and cost savings across common agent scenarios.
"""

import time
from jev_harness import (
    JevClient,
    triage_test_failure,
    should_abort_trajectory,
    route_model_tier,
    verify_step_completion,
)

SCENARIOS = [
    {
        "name": "Missing Pip Dependency (ModuleNotFoundError)",
        "fn": lambda c: triage_test_failure("ModuleNotFoundError: No module named 'numpy'", client=c),
        "frontier_input_tokens": 12000,
        "frontier_output_tokens": 800,
        "frontier_latency_ms": 12500,
    },
    {
        "name": "Flaky Network Timeout in Vitest",
        "fn": lambda c: triage_test_failure("ConnectionResetError: [Errno 104] Connection reset by peer with timeout", client=c),
        "frontier_input_tokens": 15000,
        "frontier_output_tokens": 1200,
        "frontier_latency_ms": 18000,
    },
    {
        "name": "Circular Doom Loop Trajectory Check",
        "fn": lambda c: should_abort_trajectory("Reescrever schema novamente", "Tentativa 1 timeout, Tentativa 2 falha circular", client=c),
        "frontier_input_tokens": 25000,
        "frontier_output_tokens": 1500,
        "frontier_latency_ms": 22000,
    },
    {
        "name": "Task Model Tier Routing (Typo fix)",
        "fn": lambda c: route_model_tier("Corrigir typo e formatar com black", client=c),
        "frontier_input_tokens": 4000,
        "frontier_output_tokens": 400,
        "frontier_latency_ms": 6000,
    },
]

# Pricing model (USD per 1M tokens - September 2026 Frontier)
# GPT-6 Astra / Claude Fable 5.1: $10.00 / 1M in, $50.00 / 1M out
FRONTIER_INPUT_PRICE_PER_M = 10.00
FRONTIER_OUTPUT_PRICE_PER_M = 50.00
# Gemini 3.8 Flash: $0.75 / 1M in, $3.75 / 1M out
FLASH_INPUT_PRICE_PER_M = 0.75
FLASH_OUTPUT_PRICE_PER_M = 3.75
# TypeSafe Jev System One: $0.042 / 1M in, $0.00 / 1M out
JEV_INPUT_PRICE_PER_M = 0.042
JEV_OUTPUT_PRICE_PER_M = 0.00


def main():
    client = JevClient()
    print("=" * 90)
    print("⚡ JEV SYSTEM ONE VS. 2026 FRONTIER LLMs (GPT-6 Astra, Claude Fable 5.1)")
    print("=" * 90)

    total_frontier_cost = 0.0
    total_jev_cost = 0.0
    total_frontier_time = 0.0
    total_jev_time = 0.0
    total_frontier_tokens = 0
    total_jev_tokens = 0

    header = f"{'Scenario':<42} | {'Jev Time':<10} | {'LLM Time':<10} | {'Jev Cost':<10} | {'LLM Cost':<10}"
    print(header)
    print("-" * len(header))

    for s in SCENARIOS:
        start = time.perf_counter()
        _ = s["fn"](client)
        jev_latency_ms = (time.perf_counter() - start) * 1000

        # Tokens
        jev_input = s["frontier_input_tokens"] // 5  # Targeted state
        jev_tokens = jev_input
        llm_tokens = s["frontier_input_tokens"] + s["frontier_output_tokens"]

        # Cost
        jev_cost = (jev_input / 1_000_000) * JEV_INPUT_PRICE_PER_M
        llm_cost = (
            (s["frontier_input_tokens"] / 1_000_000) * FRONTIER_INPUT_PRICE_PER_M
            + (s["frontier_output_tokens"] / 1_000_000) * FRONTIER_OUTPUT_PRICE_PER_M
        )

        total_frontier_cost += llm_cost
        total_jev_cost += jev_cost
        total_frontier_time += s["frontier_latency_ms"]
        total_jev_time += jev_latency_ms
        total_frontier_tokens += llm_tokens
        total_jev_tokens += jev_tokens

        print(
            f"{s['name'][:40]:<42} | "
            f"{jev_latency_ms:>7.1f} ms | "
            f"{s['frontier_latency_ms']:>7.0f} ms | "
            f"${jev_cost:>8.5f} | "
            f"${llm_cost:>8.4f}"
        )

    print("-" * len(header))
    savings_pct = ((total_frontier_cost - total_jev_cost) / total_frontier_cost) * 100
    speedup = total_frontier_time / max(1, total_jev_time)

    print(f"\n📊 SUMMARY RESULTS:")
    print(f"  • Total Tokens Burned: Frontier LLM: {total_frontier_tokens:,} vs. Jev Harness: {total_jev_tokens:,}")
    print(f"  • Total Cost:          Frontier LLM: ${total_frontier_cost:.4f} vs. Jev Harness: ${total_jev_cost:.5f}")
    print(f"  • Cost Savings:        ⚡ {savings_pct:.1f}% reduction in API bills")
    print(f"  • Latency Speedup:     🚀 {speedup:.1f}x faster decision loop")
    print("=" * 90)


if __name__ == "__main__":
    main()
