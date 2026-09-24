import * as readline from "node:readline";
import { JevClient } from "./client.js";
import {
  modulateReasoningEffort,
  routeModelTier,
  shouldAbortTrajectory,
  shouldNudgeContinuation,
  triageTestFailure,
  verifyStepCompletion,
} from "./gates.js";

const PROTOCOL_VERSION = "2024-11-05";
const SERVER_NAME = "jev-harness";
const SERVER_VERSION = "0.2.0";

export const MCP_TOOL_ANNOTATIONS = {
  readOnlyHint: true,
  destructiveHint: false,
  idempotentHint: true,
  openWorldHint: false,
};

export const TOOLS_MANIFEST = [
  {
    name: "jev_triage_test_failure",
    title: "Triage Test Failure",
    description:
      "Triages test failure traceback, compilation error, or runtime exception using Jev System One non-autoregressive decision classification (70-300ms, zero LLM generation). Detects missing environment packages, flaky transient glitches, or deep logic defects.\n\nUse when: An agent encounters a test failure, traceback, compiler error (e.g. TS2307, ModuleNotFoundError, E0463), or needs to decide whether to invoke a frontier LLM.\nDo NOT use when: Tests pass, or for general code review or feature generation.\n\nReturns: JSON object with 'category' (env_missing, flaky_transient, deep_logic, no_failure), 'skip_llm' (boolean: true if resolvable deterministically without frontier LLM), and 'action_recommendation' (string with concrete recovery action).",
    annotations: MCP_TOOL_ANNOTATIONS,
    inputSchema: {
      type: "object",
      properties: {
        failure_log: {
          type: "string",
          description: "Raw test failure output, stack trace, or compiler error log.",
        },
        test_command: {
          type: "string",
          description: "Optional test command that was executed (e.g. 'pytest tests/', 'npm test').",
        },
      },
      required: ["failure_log"],
    },
  },
  {
    name: "jev_check_abort",
    title: "Check Trajectory Abort",
    description:
      "Guards against doom loops, repetitive circular retries, dead-ends, and destructive refactoring before burning frontier reasoning tokens. Evaluates the agent's proposed plan against recent attempt history.\n\nUse when: An agent is about to retry a failed step, execute a code edit after previous failed attempts, or before embarking on a potentially circular fix.\nDo NOT use when: Making the first attempt on a fresh task with no prior failure history.\n\nReturns: JSON object with 'should_abort' (boolean: true if the trajectory is stuck in a circular loop), 'abort_probability' (number: 0.0 to 1.0), 'action' (string: PROCEED, HALT, PIVOT), and 'reasoning_summary' (string explaining the decision).",
    annotations: MCP_TOOL_ANNOTATIONS,
    inputSchema: {
      type: "object",
      properties: {
        proposed_step: {
          type: "string",
          description: "The next proposed plan, code modification, or architectural direction.",
        },
        recent_attempts_summary: {
          type: "string",
          description: "Summary of previous failed attempts, errors encountered, or circular patterns.",
        },
      },
      required: ["proposed_step"],
    },
  },
  {
    name: "jev_route_task",
    title: "Route Task Model Tier",
    description:
      "Routes a programming task to the minimal sufficient model tier (deterministic script, lightweight flash model, or heavy frontier reasoning model) to minimize latency and token expenditure.\n\nUse when: Starting a new task, refactoring step, or bug fix to choose between lightweight models and expensive reasoning frontier models.\nDo NOT use when: Diagnosing test execution tracebacks (use jev_triage_test_failure instead).\n\nReturns: JSON object with 'selected_tier' (string: deterministic, lightweight, heavy), 'complexity_score' (number: 1.0 to 5.0), 'recommended_model' (string), and 'rationale' (string).",
    annotations: MCP_TOOL_ANNOTATIONS,
    inputSchema: {
      type: "object",
      properties: {
        task_description: {
          type: "string",
          description: "Clear description of the task, bug to fix, or feature to implement.",
        },
      },
      required: ["task_description"],
    },
  },
  {
    name: "jev_verify_completion",
    title: "Verify Step Completion",
    description:
      "Calibrates step completion against acceptance criteria using typed rubric scoring. Evaluates whether produced evidence proves the task is finished without running redundant review loops.\n\nUse when: An agent believes a task or milestone is complete and wants to verify acceptance criteria before concluding.\nDo NOT use when: Work is still underway or tests are actively failing.\n\nReturns: JSON object with 'is_verified' (boolean: true if acceptance criteria are satisfied with proof), 'satisfaction_probability' (number: 0.0 to 1.0), 'rigor_score' (number: 1.0 to 4.0), 'needs_rework' (boolean), and 'confidence' (number: 0.0 to 1.0).",
    annotations: MCP_TOOL_ANNOTATIONS,
    inputSchema: {
      type: "object",
      properties: {
        acceptance_criteria: {
          type: "string",
          description: "Explicit requirements, constraints, or definition of done.",
        },
        produced_output: {
          type: "string",
          description: "The evidence, test results, code diff, or output produced.",
        },
      },
      required: ["acceptance_criteria", "produced_output"],
    },
  },
  {
    name: "jev_modulate_reasoning_effort",
    title: "Modulate Reasoning Effort",
    description:
      "Dynamically modulates reasoning effort (low, medium, high, etc.) and generation stability lease steps for the immediate LLM call. Maps provider-specific parameters for OpenAI (GPT-6 Astra/o3), DeepSeek (V4.1-Flash/R1), Qwen (3.8 Max), Anthropic (Claude Fable 5.1), and Gemini (3.8 Thinking) to prevent reasoning token waste.\n\nUse when: Preparing a prompt or tool call for a reasoning-capable LLM to calibrate thinking effort according to task complexity.\nDo NOT use when: Calling standard non-reasoning models or local deterministic scripts.\n\nReturns: JSON object with 'effort' (string), 'provider' (string), 'provider_params' (object with provider-native kwargs), 'is_reasoning_supported' (boolean), 'cache_safe_recommendation' (string), and 'lease_steps' (integer).",
    annotations: MCP_TOOL_ANNOTATIONS,
    inputSchema: {
      type: "object",
      properties: {
        context: {
          type: "string",
          description: "The command, prompt, or next step to evaluate.",
        },
        provider: {
          type: "string",
          enum: ["openai", "deepseek", "qwen", "anthropic", "gemini", "kimi", "mimo"],
          default: "openai",
          description: "Target provider dialect (openai, deepseek, qwen, anthropic, gemini, kimi, mimo). Default: openai.",
        },
        model: {
          type: "string",
          description: "Optional model identifier to check for direct non-reasoning compatibility.",
        },
        session_context_tokens: {
          type: "integer",
          minimum: 0,
          default: 0,
          description: "Optional active prompt tokens in session context to evaluate prompt cache risk.",
        },
        supported_efforts: {
          type: "array",
          items: { type: "string" },
          description: "Optional list of supported effort levels (e.g. ['none', 'minimal', 'low', 'medium', 'high', 'xhigh', 'max', 'ultra']).",
        },
        max_lease_steps: {
          type: "integer",
          minimum: 1,
          maximum: 50,
          default: 10,
          description: "Optional upper bound for generation stability lease steps (default: 10).",
        },
      },
      required: ["context"],
    },
  },
  {
    name: "jev_evaluate_nudge",
    title: "Evaluate Continuation Nudge",
    description:
      "Evaluates whether an autonomous agent paused prematurely with unfinished work or unverified changes (covering workflow phases: research, ask, plan, execute, verify, complete). Vetoes nudges when waiting on user input or when repeated nudges make no progress.\n\nUse when: A background worker or agent loop stops and you need to determine if it should be nudged to continue autonomously.\nDo NOT use when: The agent explicitly requested user confirmation or required credentials.\n\nReturns: JSON object with 'should_nudge' (boolean), 'workflow_phase' (string: research, ask, plan, execute, verify, complete), 'action' (string: NUDGE, WAIT, STOP), and 'confidence' (number: 0.0 to 1.0).",
    annotations: MCP_TOOL_ANNOTATIONS,
    inputSchema: {
      type: "object",
      properties: {
        transcript_tail: {
          type: "string",
          description: "Recent agent transcript tail or turn output.",
        },
        previous_nudge_summary: {
          type: "string",
          description: "Optional summary of the previous nudge to check if real progress was made.",
        },
        threshold: {
          type: "number",
          minimum: 0.0,
          maximum: 1.0,
          default: 0.5,
          description: "Optional probability threshold for nudge/waiting/progress (default: 0.5).",
        },
      },
      required: ["transcript_tail"],
    },
  },
];

export async function processMessage(line: string, client: JevClient): Promise<Record<string, any> | null> {
  const trimmed = line.trim();
  if (!trimmed) return null;

  let msg: any;
  try {
    msg = JSON.parse(trimmed);
  } catch {
    return {
      jsonrpc: "2.0",
      id: null,
      error: { code: -32700, message: "Parse error" },
    };
  }

  const method = msg.method;
  const reqId = msg.id;
  const params = msg.params || {};

  if (method === "notifications/initialized") return null;
  if (method === "ping") return { jsonrpc: "2.0", id: reqId, result: {} };

  if (method === "initialize") {
    return {
      jsonrpc: "2.0",
      id: reqId,
      result: {
        protocolVersion: PROTOCOL_VERSION,
        serverInfo: { name: SERVER_NAME, version: SERVER_VERSION },
        capabilities: { tools: {} },
      },
    };
  }

  if (method === "tools/list") {
    return {
      jsonrpc: "2.0",
      id: reqId,
      result: { tools: TOOLS_MANIFEST },
    };
  }

  if (method === "tools/call") {
    const toolName = params.name;
    const args = params.arguments || {};

    try {
      let result: any;
      if (toolName === "jev_triage_test_failure") {
        if (!args.failure_log) {
          return {
            jsonrpc: "2.0",
            id: reqId,
            error: { code: -32602, message: "Missing required argument 'failure_log'" },
          };
        }
        const res = await triageTestFailure(args.failure_log, client);
        result = {
          category: res.category,
          confidence: res.confidence,
          skip_llm: res.skipLlm,
          skipLlm: res.skipLlm,
          skip_llm_prob: res.skipLlmProb,
          skipLlmProb: res.skipLlmProb,
          severity_score: res.severityScore,
          severityScore: res.severityScore,
          recommendation: res.actionRecommendation,
          actionRecommendation: res.actionRecommendation,
          is_mock: res.isMock,
          degraded_reason: res.degradedReason ?? "",
          isMock: res.isMock,
        };
      } else if (toolName === "jev_check_abort" || toolName === "jev_abort_check") {
        if (!args.proposed_step) {
          return {
            jsonrpc: "2.0",
            id: reqId,
            error: { code: -32602, message: "Missing required argument 'proposed_step'" },
          };
        }
        const res = await shouldAbortTrajectory(args.proposed_step, args.recent_attempts_summary || "", client);
        result = {
          should_abort: res.shouldAbort,
          shouldAbort: res.shouldAbort,
          abort_probability: res.abortProbability,
          abortProbability: res.abortProbability,
          action: res.action,
          viability_score: res.viabilityScore,
          viabilityScore: res.viabilityScore,
          reasoning_summary: res.reasoningSummary,
          reasoningSummary: res.reasoningSummary,
          is_mock: res.isMock,
          degraded_reason: res.degradedReason ?? "",
          isMock: res.isMock,
        };
      } else if (toolName === "jev_route_task") {
        if (!args.task_description) {
          return {
            jsonrpc: "2.0",
            id: reqId,
            error: { code: -32602, message: "Missing required argument 'task_description'" },
          };
        }
        const res = await routeModelTier(args.task_description, client);
        result = {
          selected_tier: res.selectedTier,
          selectedTier: res.selectedTier,
          confidence: res.confidence,
          complexity_score: res.complexityScore,
          complexityScore: res.complexityScore,
          recommended_model: res.recommendedModel,
          recommendedModel: res.recommendedModel,
          rationale: res.rationale,
          is_mock: res.isMock,
          degraded_reason: res.degradedReason ?? "",
          isMock: res.isMock,
        };
      } else if (toolName === "jev_verify_completion") {
        if (!args.acceptance_criteria || !args.produced_output) {
          return {
            jsonrpc: "2.0",
            id: reqId,
            error: { code: -32602, message: "Missing required arguments 'acceptance_criteria' or 'produced_output'" },
          };
        }
        const res = await verifyStepCompletion(args.acceptance_criteria, args.produced_output, client);
        result = {
          is_verified: res.isVerified,
          isVerified: res.isVerified,
          satisfaction_probability: res.satisfactionProbability,
          satisfactionProbability: res.satisfactionProbability,
          rigor_score: res.rigorScore,
          rigorScore: res.rigorScore,
          confidence: res.confidence,
          needs_rework: res.needsRework,
          needsRework: res.needsRework,
          is_mock: res.isMock,
          degraded_reason: res.degradedReason ?? "",
          isMock: res.isMock,
        };
      } else if (toolName === "jev_modulate_reasoning_effort") {
        if (!args.context) {
          return {
            jsonrpc: "2.0",
            id: reqId,
            error: { code: -32602, message: "Missing required argument 'context'" },
          };
        }
        const res = await modulateReasoningEffort(args.context, {
          provider: args.provider,
          model: args.model,
          sessionContextTokens: args.session_context_tokens,
          supportedEfforts: args.supported_efforts,
          maxLeaseSteps: args.max_lease_steps,
          client,
        });
        result = {
          effort: res.effort,
          confidence: res.confidence,
          complexity_score: res.complexityScore,
          complexityScore: res.complexityScore,
          rationale: res.rationale,
          provider: res.provider,
          provider_params: res.providerParams,
          providerParams: res.providerParams,
          is_reasoning_supported: res.isReasoningSupported,
          isReasoningSupported: res.isReasoningSupported,
          cache_safe_recommendation: res.cacheSafeRecommendation,
          cacheSafeRecommendation: res.cacheSafeRecommendation,
          lease_steps: res.leaseSteps,
          leaseSteps: res.leaseSteps,
          is_mock: res.isMock,
          degraded_reason: res.degradedReason ?? "",
          isMock: res.isMock,
        };
      } else if (toolName === "jev_evaluate_nudge" || toolName === "jev_should_nudge_continuation") {
        if (!args.transcript_tail) {
          return {
            jsonrpc: "2.0",
            id: reqId,
            error: { code: -32602, message: "Missing required argument 'transcript_tail'" },
          };
        }
        const res = await shouldNudgeContinuation(String(args.transcript_tail), {
          previousNudgeSummary: args.previous_nudge_summary ? String(args.previous_nudge_summary) : "",
          threshold: typeof args.threshold === "number" ? args.threshold : 0.5,
          client,
        });
        result = {
          should_nudge: res.shouldNudge,
          shouldNudge: res.shouldNudge,
          nudge_probability: res.nudgeProbability,
          nudgeProbability: res.nudgeProbability,
          waiting_probability: res.waitingProbability,
          waitingProbability: res.waitingProbability,
          progress_probability: res.progressProbability,
          progressProbability: res.progressProbability,
          workflow_phase: res.workflowPhase,
          workflowPhase: res.workflowPhase,
          suggested_nudge_prompt: res.suggestedNudgePrompt,
          suggestedNudgePrompt: res.suggestedNudgePrompt,
          rationale: res.rationale,
          is_mock: res.isMock,
          degraded_reason: res.degradedReason ?? "",
          isMock: res.isMock,
        };
      } else {
        return {
          jsonrpc: "2.0",
          id: reqId,
          error: { code: -32601, message: `Method not found: ${toolName}` },
        };
      }

      return {
        jsonrpc: "2.0",
        id: reqId,
        result: {
          content: [{ type: "text", text: JSON.stringify(result) }],
          isError: false,
        },
      };
    } catch (exc: any) {
      return {
        jsonrpc: "2.0",
        id: reqId,
        result: {
          content: [{ type: "text", text: `Error executing ${toolName}: ${exc?.message || exc}` }],
          isError: true,
        },
      };
    }
  }

  if (reqId !== undefined) {
    return {
      jsonrpc: "2.0",
      id: reqId,
      error: { code: -32601, message: `Method not found: ${method}` },
    };
  }

  return null;
}

export async function runMcpServer(client?: JevClient): Promise<void> {
  const activeClient = client || new JevClient();
  const rl = readline.createInterface({
    input: process.stdin,
    terminal: false,
  });

  return new Promise<void>((resolve) => {
    let pending = Promise.resolve();

    rl.on("line", (line) => {
      pending = pending.then(async () => {
        try {
          const resp = await processMessage(line, activeClient);
          if (resp !== null) {
            process.stdout.write(JSON.stringify(resp) + "\n");
          }
        } catch (err) {
          // Prevent unhandled rejection
        }
      });
    });

    rl.on("close", async () => {
      await pending;
      resolve();
    });
  });
}
