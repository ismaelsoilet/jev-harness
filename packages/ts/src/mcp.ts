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
const SERVER_VERSION = "0.1.9";

export const TOOLS_MANIFEST = [
  {
    name: "jev_triage_test_failure",
    description:
      "Triages test traceback, compile error, or runtime failure using Jev System One (70-300ms, zero-generation). Returns root cause category, skip_llm flag (true if resolvable deterministically without frontier LLM), and immediate action recommendation.",
    inputSchema: {
      type: "object",
      properties: {
        failure_log: {
          type: "string",
          description: "Raw test failure output, stack trace, or compiler error log.",
        },
      },
      required: ["failure_log"],
    },
  },
  {
    name: "jev_abort_check",
    description:
      "Guards against doom loops, dead-ends, circular retries, and destructive refactors. Evaluates proposed plan against recent attempt history before burning tokens.",
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
    description:
      "Routes programming task to the minimal sufficient model tier (deterministic script, lightweight fast flash model, or heavy frontier reasoning model) to optimize cost and latency.",
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
    description:
      "Calibrates step completion against acceptance criteria using typed rubric scoring. Checks if evidence is sufficient to declare done without launching expensive extra review loops.",
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
    description:
      "Dynamically modulates reasoning effort (low, medium, high) for the immediate generation step. Maps exact parameters for OpenAI (GPT-6 Astra/o3), DeepSeek (V4.1-Flash/R1), Qwen (3.8 Max), Anthropic (Claude Fable 5.1), and Gemini (3.8 Thinking). Eliminates reasoning token waste and cuts multi-minute delays on mechanical tool calls.",
    inputSchema: {
      type: "object",
      properties: {
        context: {
          type: "string",
          description: "The command, prompt, or next step to evaluate.",
        },
        provider: {
          type: "string",
          description: "Target provider (openai, deepseek, qwen, anthropic, gemini, kimi, mimo). Default: openai.",
        },
        model: {
          type: "string",
          description: "Optional model identifier to check for direct non-reasoning compatibility.",
        },
        session_context_tokens: {
          type: "integer",
          description: "Optional active prompt tokens in session context to evaluate prompt cache risk.",
        },
        supported_efforts: {
          type: "array",
          items: { type: "string" },
          description: "Optional list of supported effort levels (e.g. ['none', 'minimal', 'low', 'medium', 'high', 'xhigh', 'max', 'ultra']).",
        },
        max_lease_steps: {
          type: "integer",
          description: "Optional upper bound for generation stability lease steps (default: 10).",
        },
      },
      required: ["context"],
    },
  },
  {
    name: "jev_should_nudge_continuation",
    description:
      "Evaluates whether an autonomous agent paused prematurely with unfinished work or unverified changes (SureForge phases: research, ask, plan, execute, verify, complete + CommandCode Jev Nudge protocol). Vetoes nudges when waiting on user permission/input or when the previous nudge produced no progress.",
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
          isMock: res.isMock,
        };
      } else if (toolName === "jev_abort_check") {
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
          isMock: res.isMock,
        };
      } else if (toolName === "jev_should_nudge_continuation") {
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
          sureforge_phase: res.sureforgePhase,
          sureforgePhase: res.sureforgePhase,
          suggested_nudge_prompt: res.suggestedNudgePrompt,
          suggestedNudgePrompt: res.suggestedNudgePrompt,
          rationale: res.rationale,
          is_mock: res.isMock,
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
