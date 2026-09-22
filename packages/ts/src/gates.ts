import { JevClient } from "./client.js";
import type {
  AbortGateResult,
  ChoiceAnswer,
  ModelRouteResult,
  NoulAnswer,
  ReasoningEffortResult,
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
    cleanLog = cleanLog.slice(0, 2500) + "\n...[truncated]...\n" + cleanLog.slice(-5000);
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

export function buildProviderParams(
  provider: string = "openai",
  effort: "low" | "medium" | "high",
  model?: string
): { providerParams: Record<string, any>; isSupported: boolean; rationale: string; cacheSafeRecommendation: string } {
  const normProvider = provider.trim().toLowerCase();
  const normModel = (model || "").trim().toLowerCase();

  const directModels = ["gpt-5.6-luna", "gpt-5.5", "gemini-3.8-live", "gemini-1.5-flash", "qwen-3.8-flash-standard"];
  if (directModels.some((dm) => normModel.includes(dm))) {
    return {
      providerParams: {},
      isSupported: false,
      rationale: `Model '${model}' is a direct single-pass model without internal reasoning CoT. Do NOT inject reasoning parameters.`,
      cacheSafeRecommendation: "Cache unaffected. Model runs in direct generation mode.",
    };
  }

  const cacheRec =
    effort !== "low"
      ? "Keep reasoning effort stable across related sub-steps to preserve Prompt Cache (KV Cache)."
      : "Low reasoning effort saves ~7,000 reasoning tokens. Safe to use for mechanical tool calls.";

  if (normProvider === "openai" || normProvider === "codex") {
    return {
      providerParams: { reasoning_effort: effort },
      isSupported: true,
      rationale: `Configured OpenAI reasoning_effort='${effort}' for target model.`,
      cacheSafeRecommendation: cacheRec,
    };
  } else if (normProvider === "deepseek" || normProvider === "deepseek-ai") {
    const effortVal = effort === "low" ? "low" : "high";
    return {
      providerParams: {
        extra_body: { thinking: { type: "enabled" } },
        reasoning_effort: effortVal,
      },
      isSupported: true,
      rationale: `DeepSeek Thinking mode configured with effort='${effortVal}'. Preserves reasoning_content in multi-turn tool calling.`,
      cacheSafeRecommendation: effort === "low" ? "Cuts latency by ~200s in mechanical steps when set to low." : cacheRec,
    };
  } else if (normProvider === "qwen" || normProvider === "alibaba") {
    if (effort === "low") {
      return {
        providerParams: { enable_thinking: false },
        isSupported: true,
        rationale: "Disabled Qwen thinking CoT for mechanical/terminal step to minimize latency.",
        cacheSafeRecommendation: "Zero tokens spent on reasoning trace.",
      };
    } else {
      const budget = effort === "medium" ? 4096 : 16384;
      return {
        providerParams: { enable_thinking: true, thinking_budget: budget },
        isSupported: true,
        rationale: `Enabled Qwen thinking budget (${budget} tokens).`,
        cacheSafeRecommendation: cacheRec,
      };
    }
  } else if (normProvider === "anthropic" || normProvider === "claude") {
    const effortMap: Record<string, string> = { low: "low", medium: "medium", high: "max" };
    const chosen = effortMap[effort] || "medium";
    return {
      providerParams: {
        thinking: { type: "adaptive" },
        output_config: { effort: chosen },
      },
      isSupported: true,
      rationale: `Configured Anthropic Adaptive Thinking with effort='${chosen}'.`,
      cacheSafeRecommendation: cacheRec,
    };
  } else if (normProvider === "gemini" || normProvider === "google") {
    const geminiMap: Record<string, string> = { low: "minimal", medium: "medium", high: "high" };
    const chosen = geminiMap[effort] || "medium";
    return {
      providerParams: {
        thinking_config: { thinking_level: chosen },
      },
      isSupported: true,
      rationale: `Configured Gemini thinking_level='${chosen}'.`,
      cacheSafeRecommendation: cacheRec,
    };
  } else if (normProvider === "kimi" || normProvider === "moonshot") {
    if (effort === "low") {
      return {
        providerParams: { extra_body: { thinking: false } },
        isSupported: true,
        rationale: "Enabled Kimi Instant Mode (thinking disabled) for zero-latency execution.",
        cacheSafeRecommendation: "Eliminates internal CoT overhead.",
      };
    } else {
      const kEffort = effort === "high" ? "high" : "low";
      return {
        providerParams: { reasoning_effort: kEffort },
        isSupported: true,
        rationale: `Configured Kimi reasoning_effort='${kEffort}'.`,
        cacheSafeRecommendation: cacheRec,
      };
    }
  } else if (normProvider === "mimo" || normProvider === "xiaomi") {
    if (effort === "low") {
      return {
        providerParams: { thinking: { type: "disabled" } },
        isSupported: true,
        rationale: "Disabled MiMo CoT for terminal command to free GPU inference.",
        cacheSafeRecommendation: "Immediate generation without scratchpad.",
      };
    } else {
      return {
        providerParams: { thinking: { type: "enabled" }, reasoning: { effort } },
        isSupported: true,
        rationale: `Enabled MiMo deep reasoning with effort='${effort}'.`,
        cacheSafeRecommendation: cacheRec,
      };
    }
  } else {
    return {
      providerParams: { reasoning_effort: effort },
      isSupported: true,
      rationale: `Generic reasoning effort='${effort}'.`,
      cacheSafeRecommendation: cacheRec,
    };
  }
}

export async function modulateReasoningEffort(
  context: string,
  options: { provider?: string; model?: string; client?: JevClient } = {}
): Promise<ReasoningEffortResult> {
  const activeClient = options.client || new JevClient();
  const provider = options.provider || "openai";
  const model = options.model;

  const questions = {
    effort: {
      type: "choice" as const,
      instructions: "Select the minimal sufficient reasoning effort needed for this immediate agent step",
      criteria: {
        low: "Mechanical action: run bash command, check git status, view file, format code, linter check, simple import, or trivial syntax edit",
        medium: "Standard code modification: implement bounded function, write standard unit test, add parameter, or localized refactoring",
        high: "Deep cognitive task: architectural design, race condition, distributed deadlock, concurrency kernel bug, or complex multi-file debugging",
      },
    },
    complexity: {
      type: "score" as const,
      instructions: "Rate the cognitive depth required for this next step",
      criteria: ["trivial_mechanical", "standard_implementation", "complex_logic", "exceptional_architecture"],
    },
  };

  const cleanContext = context.trim().slice(0, 4000);
  const resp = await activeClient.systemOne(cleanContext, questions);

  const effortAns = resp.answers.effort as ChoiceAnswer | undefined;
  const compAns = resp.answers.complexity as ScoreAnswer | undefined;

  let effort = (effortAns?.choice as "low" | "medium" | "high") || "medium";
  if (!["low", "medium", "high"].includes(effort)) {
    effort = "medium";
  }
  const confidence = effortAns?.confidence ?? 0.85;
  const complexityScore = compAns?.score ?? 2.0;

  const { providerParams, isSupported, rationale, cacheSafeRecommendation } = buildProviderParams(
    provider,
    effort,
    model
  );

  return {
    effort,
    confidence,
    complexityScore,
    rationale,
    provider,
    providerParams,
    isReasoningSupported: isSupported,
    cacheSafeRecommendation,
    isMock: resp.isMock,
  };
}
