import { JevClient } from "./client.js";
import type {
  AbortGateResult,
  ChoiceAnswer,
  ModelRouteResult,
  NoulAnswer,
  ScoreAnswer,
  TestTriageResult,
  VerificationResult,
} from "./types.js";

export async function triageTestFailure(
  failureLog: string,
  client?: JevClient
): Promise<TestTriageResult> {
  const activeClient = client || new JevClient();

  let cleanLog = failureLog.trim();
  if (cleanLog.length > 8000) {
    cleanLog = "...[truncated]...\n" + cleanLog.slice(-7500);
  }

  const questions = {
    category: {
      type: "choice" as const,
      instructions: "What is the root failure type in this error trace?",
      criteria: {
        env_missing: "Missing module, package not installed, environment variable missing, or runtime command not found",
        flaky_transient: "Network timeout, port already in use, race condition, or transient socket hangup",
        syntax_trivial: "Small typo, missing bracket, indentation error, or simple import name mismatch",
        test_redundant: "Deprecated test, duplicate assertion, or obsolete fixture",
        deep_logic: "Complex algorithmic bug, business logic defect, or architectural regression",
      },
    },
    skip_llm: {
      type: "noul" as const,
      instructions: "Can this error be handled deterministically (e.g. running pip/npm install, retrying, or fixing a simple typo) without calling an expensive System 2 generative LLM?",
    },
    severity: {
      type: "score" as const,
      instructions: "Rate the architectural severity of this test failure",
      criteria: ["trivial_env", "minor_syntax", "moderate_bug", "critical_systemic"],
    },
  };

  const resp = await activeClient.systemOne(cleanLog, questions);

  const catAns = resp.answers.category as ChoiceAnswer | undefined;
  const skipAns = resp.answers.skip_llm as NoulAnswer | undefined;
  const sevAns = resp.answers.severity as ScoreAnswer | undefined;

  const category = catAns?.choice || "deep_logic";
  const confidence = catAns?.confidence ?? 0.5;
  const skipProb = skipAns?.noul ?? 0.0;
  const sevScore = sevAns?.score ?? 3.0;

  const skipLlm = skipProb >= 0.65 || category === "env_missing" || category === "flaky_transient";

  let rec: string;
  if (category === "env_missing") {
    rec = "AUTO-ACTION: Install missing dependency or check environment configuration (Do NOT call LLM).";
  } else if (category === "flaky_transient") {
    rec = "AUTO-ACTION: Retry test once with fresh worker; do not generate code changes.";
  } else if (category === "syntax_trivial") {
    rec = "LOW-COST: Fix typo locally or route to fastest lightweight tier.";
  } else if (category === "test_redundant") {
    rec = "PRUNE: Test is redundant or obsolete; prune from test harness.";
  } else {
    rec = "ESCALATE: Real logic defect; dispatch to System 2 LLM with targeted context.";
  }

  return {
    category,
    confidence,
    skipLlm,
    skipLlmProb: skipProb,
    severityScore: sevScore,
    actionRecommendation: rec,
    isMock: resp.isMock,
  };
}

export async function shouldAbortTrajectory(
  proposedStep: string,
  recentAttemptsSummary: string = "",
  client?: JevClient
): Promise<AbortGateResult> {
  const activeClient = client || new JevClient();
  const state = `RECENT ATTEMPTS & CONTEXT:\n${recentAttemptsSummary}\n\nPROPOSED NEXT STEP:\n${proposedStep}`;

  const questions = {
    dead_end: {
      type: "noul" as const,
      instructions: "Does this proposed step indicate a dead end, repeating a previously failed approach, or proposing an unviable/destructive path?",
    },
    action: {
      type: "choice" as const,
      instructions: "What should the orchestrator do with this proposed trajectory?",
      criteria: {
        proceed: "The step is logical, progress-oriented, and grounded in evidence",
        replan: "The step is doubtful or weak; reconsider alternatives",
        abort_and_ask: "The trajectory is circular or contradictory; stop and ask user for clarification",
      },
    },
    viability: {
      type: "score" as const,
      instructions: "Evaluate the technical viability of this step",
      criteria: ["hopeless_circular", "doubtful", "plausible", "highly_viable"],
    },
  };

  const resp = await activeClient.systemOne(state, questions);

  const deadEndAns = resp.answers.dead_end as NoulAnswer | undefined;
  const actionAns = resp.answers.action as ChoiceAnswer | undefined;
  const viabilityAns = resp.answers.viability as ScoreAnswer | undefined;

  const deadEndProb = deadEndAns?.noul ?? 0.0;
  const action = actionAns?.choice || "proceed";
  const viability = viabilityAns?.score ?? 3.0;

  const shouldAbort = deadEndProb >= 0.70 || action === "abort_and_ask" || viability <= 1.5;
  const effectiveAction = shouldAbort && action === "proceed" ? "abort_and_ask" : action;

  const summary = shouldAbort
    ? `Abort recommended (prob=${deadEndProb.toFixed(2)})`
    : `Safe to proceed (viability=${viability.toFixed(1)}, action=${action})`;

  return {
    shouldAbort,
    abortProbability: deadEndProb,
    action: effectiveAction,
    viabilityScore: viability,
    reasoningSummary: summary,
    isMock: resp.isMock,
  };
}

export async function routeModelTier(
  taskDescription: string,
  client?: JevClient
): Promise<ModelRouteResult> {
  const activeClient = client || new JevClient();

  const questions = {
    tier: {
      type: "choice" as const,
      instructions: "Select the minimal sufficient model tier to solve this programming task",
      criteria: {
        deterministic: "Can be solved with bash, regex, deterministic script, or pure Jev classification",
        lightweight_system2: "Simple coding edit, formatting, documentation, or trivial unit test (e.g. Gemini 3.8 Flash)",
        heavy_system2: "Complex architecture, deep reasoning, multi-file refactoring, or difficult debugging (e.g. GPT-6 Astra, Claude Fable 5.1)",
      },
    },
    complexity: {
      type: "score" as const,
      instructions: "Rate the cognitive complexity of this task",
      criteria: ["trivial", "straightforward", "moderate", "highly_complex"],
    },
  };

  const resp = await activeClient.systemOne(taskDescription, questions);

  const tierAns = resp.answers.tier as ChoiceAnswer | undefined;
  const compAns = resp.answers.complexity as ScoreAnswer | undefined;

  const tier = tierAns?.choice || "lightweight_system2";
  const conf = tierAns?.confidence ?? 0.8;
  const comp = compAns?.score ?? 2.0;

  let modelRec: string;
  let rationale: string;

  if (tier === "deterministic") {
    modelRec = "Direct Python/Bash Script (0 LLM Tokens)";
    rationale = "Task does not require generative reasoning; execute mechanically.";
  } else if (tier === "lightweight_system2") {
    modelRec = "Gemini 3.8 Flash (~$0.75 in / $3.75 out per 1M tokens)";
    rationale = "Task is bounded and straightforward; save frontier tokens.";
  } else {
    modelRec = "Claude Fable 5.1 / GPT-6 Astra (~$10.00 in / $50.00 out per 1M tokens)";
    rationale = "Task requires deep architectural synthesis or multi-file reasoning.";
  }

  return {
    selectedTier: tier,
    confidence: conf,
    complexityScore: comp,
    recommendedModel: modelRec,
    rationale,
    isMock: resp.isMock,
  };
}

export async function verifyStepCompletion(
  acceptanceCriteria: string,
  producedOutput: string,
  client?: JevClient
): Promise<VerificationResult> {
  const activeClient = client || new JevClient();
  const state = `ACCEPTANCE CRITERIA:\n${acceptanceCriteria}\n\nPRODUCED EVIDENCE / OUTPUT:\n${producedOutput}`;

  const questions = {
    satisfaction: {
      type: "noul" as const,
      instructions: "Does the produced output satisfy the acceptance criteria with concrete verifiable evidence?",
    },
    rigor: {
      type: "score" as const,
      instructions: "Rate how rigorously the criteria are verified by the evidence",
      criteria: ["unverified", "partially_verified", "well_verified", "exhaustively_proven"],
    },
  };

  const resp = await activeClient.systemOne(state, questions);

  const satAns = resp.answers.satisfaction as NoulAnswer | undefined;
  const rigorAns = resp.answers.rigor as ScoreAnswer | undefined;

  const satProb = satAns?.noul ?? 0.0;
  const rigorScore = rigorAns?.score ?? 2.0;
  const conf = rigorAns?.confidence ?? 0.8;

  const isVerified = satProb >= 0.80 && rigorScore >= 2.5;

  return {
    isVerified,
    satisfactionProbability: satProb,
    rigorScore,
    confidence: conf,
    needsRework: !isVerified,
    isMock: resp.isMock,
  };
}
