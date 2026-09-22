/**
 * Type definitions for Jev System One Decision Harness.
 */

export interface ChoiceQuestion {
  type: "choice";
  instructions: string;
  criteria: Record<string, string>;
}

export interface ScoreQuestion {
  type: "score";
  instructions: string;
  criteria: string[];
}

export interface NoulQuestion {
  type: "noul";
  instructions: string;
}

export type Question = ChoiceQuestion | ScoreQuestion | NoulQuestion;

export interface ChoiceAnswer {
  type: "choice";
  choice: string;
  confidence: number;
  probabilities?: Record<string, number>;
}

export interface ScoreAnswer {
  type: "score";
  score: number;
  confidence: number;
  probabilities?: Record<string, number>;
  legend?: string[];
}

export interface NoulAnswer {
  type: "noul";
  noul: number; // Probability between 0.0 and 1.0 that answer is yes
}

export type Answer = ChoiceAnswer | ScoreAnswer | NoulAnswer;

export interface JevResponse {
  model: string;
  answers: Record<string, Answer>;
  usage: {
    input_tokens: number;
    output_tokens: number;
  };
  isMock: boolean;
  rawResponse?: any;
}

export interface TestTriageResult {
  category: "env_missing" | "flaky_transient" | "syntax_trivial" | "deep_logic" | "test_redundant" | string;
  confidence: number;
  skipLlm: boolean;
  skipLlmProb: number;
  severityScore: number;
  actionRecommendation: string;
  isMock: boolean;
}

export interface AbortGateResult {
  shouldAbort: boolean;
  abortProbability: number;
  action: "proceed" | "replan" | "abort_and_ask" | string;
  viabilityScore: number;
  reasoningSummary: string;
  isMock: boolean;
}

export interface ModelRouteResult {
  selectedTier: "deterministic" | "lightweight_system2" | "heavy_system2" | string;
  confidence: number;
  complexityScore: number;
  recommendedModel: string;
  rationale: string;
  isMock: boolean;
}

export interface VerificationResult {
  isVerified: boolean;
  satisfactionProbability: number;
  rigorScore: number;
  confidence: number;
  needsRework: boolean;
  isMock: boolean;
}

export type EffortLevel = "none" | "minimal" | "low" | "medium" | "high" | "xhigh" | "max" | "ultra" | string;

export interface ReasoningEffortResult {
  effort: EffortLevel;
  confidence: number;
  complexityScore: number;
  rationale: string;
  provider: string;
  providerParams: Record<string, any>;
  isReasoningSupported: boolean;
  cacheSafeRecommendation: string;
  leaseSteps: number;
  isMock: boolean;
}

export type WorkflowPhase = "research" | "ask" | "plan" | "execute" | "verify" | "complete" | string;

export interface NudgeGateResult {
  shouldNudge: boolean;
  nudgeProbability: number;
  waitingProbability: number;
  progressProbability: number;
  workflowPhase: WorkflowPhase;
  suggestedNudgePrompt: string;
  rationale: string;
  isMock: boolean;
}

export type AbortCheckResult = AbortGateResult;
export type StepVerificationResult = VerificationResult;

export interface JevClientOptions {
  apiKey?: string;
  provider?: string;
  baseUrl?: string;
  model?: string;
  timeoutMs?: number;
  forceMock?: boolean;
}
