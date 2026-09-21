"""
Example: Using Jev System One SDK directly in your Python applications.
"""

from jev_harness import (
    ChoiceQuestion,
    JevClient,
    NoulQuestion,
    ScoreQuestion,
    route_model_tier,
    should_abort_trajectory,
    triage_test_failure,
    verify_step_completion,
)


def main():
    # Initialize client (automatically cascades: env vars -> .jev.json -> credentials.env -> offline mock)
    client = JevClient()
    print(f"Jev Client active: Provider={client.provider}, Model={client.model}, Live={client.is_live}")

    # 1. Gate a test traceback
    sample_trace = """
    Traceback (most recent call last):
      File "test_runner.py", line 12, in <module>
        import redis
    ModuleNotFoundError: No module named 'redis'
    """
    print("\n--- 1. Triage Test Failure ---")
    triage = triage_test_failure(sample_trace, client=client)
    print(f"Category: {triage.category}")
    print(f"Skip expensive LLM?: {triage.skip_llm} (prob={triage.skip_llm_prob:.2f})")
    print(f"Action Recommendation: {triage.action_recommendation}")

    # 2. Guard against circular agent doom loops
    print("\n--- 2. Trajectory & Dead-End Check ---")
    abort_res = should_abort_trajectory(
        proposed_step="Tentar reescrever novamente sem rodar testes",
        recent_attempts_summary="Tentativa 1 falhou com timeout. Tentativa 2 falhou com erro circular.",
        client=client,
    )
    print(f"Should Abort?: {abort_res.should_abort}")
    print(f"Abort Probability: {abort_res.abort_probability:.2f}")
    print(f"Action: {abort_res.action}")

    # 3. Dynamic Model Routing
    print("\n--- 3. Task Route Tier ---")
    route_res = route_model_tier("Corrigir typo e formatar codigo com black", client=client)
    print(f"Selected Tier: {route_res.selected_tier}")
    print(f"Recommended Model: {route_res.recommended_model}")
    print(f"Rationale: {route_res.rationale}")

    # 4. Completion Verification Gate
    print("\n--- 4. Criteria Verification ---")
    verify_res = verify_step_completion(
        acceptance_criteria="Deve conter testes unitarios com 100% de aprovacao",
        produced_output="Todos os 22 testes unitarios passaram com sucesso em 0.017s.",
        client=client,
    )
    print(f"Verified: {verify_res.is_verified}")
    print(f"Satisfaction Probability: {verify_res.satisfaction_probability:.2f}")
    print(f"Rigor Score: {verify_res.rigor_score}/4.0")


if __name__ == "__main__":
    main()
