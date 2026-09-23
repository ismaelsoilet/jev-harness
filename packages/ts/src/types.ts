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
  legend?: string[] | Record<string, string>;
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
  /** Set when the answer came from a fallback (auth_401, http_500, timeout, connection). */
  degradedReason?: string;
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
  /** Set when a provider failure caused the offline fallback (E0.2). */
  degradedReason: string;
}

export interface AbortGateResult {
  shouldAbort: boolean;
  abortProbability: number;
  action: "proceed" | "replan" | "abort_and_ask" | string;
  viabilityScore: number;
  reasoningSummary: string;
  isMock: boolean;
  /** Set when a provider failure caused the offline fallback (E0.2). */
  degradedReason: string;
}

export interface ModelRouteResult {
  selectedTier: "deterministic" | "lightweight_system2" | "heavy_system2" | string;
  confidence: number;
  complexityScore: number;
  recommendedModel: string;
  rationale: string;
  isMock: boolean;
  /** Set when a provider failure caused the offline fallback (E0.2). */
  degradedReason: string;
}

export interface VerificationResult {
  isVerified: boolean;
  satisfactionProbability: number;
  rigorScore: number;
  confidence: number;
  needsRework: boolean;
  isMock: boolean;
  /** Set when a provider failure caused the offline fallback (E0.2). */
  degradedReason: string;
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
  /** Set when a provider failure caused the offline fallback (E0.2). */
  degradedReason: string;
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
  /** Set when a provider failure caused the offline fallback (E0.2). */
  degradedReason: string;
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
  /** Maximum provider attempts for retryable failures (429/5xx/timeout/network). Default 3. */
  maxRetries?: number;
  /** Base delay for exponential backoff in ms. Default 500. */
  retryBaseDelayMs?: number;
  /** Fail-open (default): degrade to the offline engine and mark the response. */
  failOpen?: boolean;
}
