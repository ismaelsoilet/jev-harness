import * as fs from "node:fs";
import * as path from "node:path";
import * as os from "node:os";
import type {
  Answer,
  ChoiceAnswer,
  ChoiceQuestion,
  JevClientOptions,
  JevResponse,
  NoulAnswer,
  NoulQuestion,
  Question,
  ScoreAnswer,
  ScoreQuestion,
} from "./types.js";
import { loadRepoConfig } from "./config.js";
import { validateQuestionOptions } from "./uncertainty.js";

export const TYPESAFE_API_URL = "https://api.typesafe.ai/v1/systemone";
export const COMMANDCODE_API_URL = "https://api.commandcode.ai/provider/v1/systemone";
export const OPENCODE_API_URL = "https://opencode.ai/zen/v1/systemone";
export const OPENROUTER_API_URL = "https://openrouter.ai/api/alpha/decisions";
export const VERCEL_API_URL = "https://ai-gateway.vercel.sh/v1/evaluate";
export const DEFAULT_MODEL = "jev-latest";
// Provider payload limits (jev-1.13: 64k tokens total; 32k for state + longest question).
// Characters are a conservative proxy (~4 chars/token) with no external tokenizer.
export const MAX_STATE_CHARS = 128000;
export const MAX_TOTAL_CHARS = 256000;

export const DEFAULT_USER_AGENT = "Mozilla/5.0 (compatible; JevHarness/0.2.0; +https://github.com/ismaelsoilet/jev-harness)";

/**
 * Mock distribution contract (E3.9). Mirrored in `src/jev_harness/client.py` and
 * `packages/rust/src/client.rs`, and asserted against `tests/fixtures/mock_golden.json`.
 * A signal *conflict* (explicit assertion next to an environment/transient signal) lowers the
 * peak on purpose so a caller can exercise `escalate_to_system2` deterministically.
 */
export const MOCK_CHOICE_BEST_PEAKED = 0.85;
export const MOCK_CHOICE_BEST_CONFLICT = 0.55;
export const MOCK_SCORE_BEST_PEAKED = 0.8;

/** Peaked distribution over `options` summing to 1.0 (1.0 when there is a single option). */
export function mockDistribution(options: string[], best: string, peak: number): Record<string, number> {
  const out: Record<string, number> = {};
  if (options.length <= 1) {
    for (const option of options) out[option] = 1.0;
    return out;
  }
  const rest = (1.0 - peak) / (options.length - 1);
  for (const option of options) out[option] = option === best ? peak : rest;
  return out;
}

/** Thrown when a 200 payload cannot be interpreted; the failure policy decides what happens. */
export class MalformedResponseError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "MalformedResponseError";
  }
}

/**
 * Requires a JSON number, exactly as the Rust runtime's serde does: a numeric string, a boolean,
 * `null` or a missing field is a malformed answer, never a silent `NaN` or a silent default.
 */
function finiteNumber(value: unknown, field: string, qid: string): number {
  if (typeof value !== "number" || !Number.isFinite(value)) {
    throw new MalformedResponseError(
      `malformed response: answer '${qid}' is missing a numeric ${JSON.stringify(field)}`
    );
  }
  return value;
}

/** Requires a JSON string field, mirroring the Rust runtime's serde semantics. */
function requiredText(answer: Record<string, any>, field: string, qid: string): string {
  if (typeof answer[field] !== "string") {
    throw new MalformedResponseError(
      `malformed response: answer '${qid}' is missing a textual ${JSON.stringify(field)}`
    );
  }
  return answer[field];
}

/**
 * Renders a structured state (E0.4) as labelled text with real newlines.
 *
 * The wire keeps the JSON form (structure + path references), but the offline engine is
 * line-oriented: `JSON.stringify` escapes every newline, which would collapse a multi-line log
 * into one line and silently change every line-anchored pattern. Mirrors `render_state_text` in
 * Python and Rust so the three runtimes score the same text.
 */
export function renderStateText(state: string | Record<string, unknown>): string {
  let parsed: unknown = state;
  if (typeof state === "string") {
    const trimmed = state.trim();
    if (!trimmed.startsWith("{")) return state;
    try {
      parsed = JSON.parse(trimmed);
    } catch {
      return state;
    }
  }
  if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) return String(state);
  const parts: string[] = [];
  // Perception fields are provider-facing metadata (E3.5): the offline engine keeps scoring the
  // full log, so its deterministic verdicts stay comparable across runtimes.
  const ignored = new Set(["focused_slice", "causal_context", "raw_log_ref"]);
  for (const [key, value] of Object.entries(parsed as Record<string, unknown>)) {
    if (ignored.has(key)) continue;
    const rendered =
      value && typeof value === "object" ? JSON.stringify(value) : String(value);
    parts.push(`${key}:\n${rendered}`);
  }
  return parts.join("\n\n");
}

/** Structured state builder: drops empty fields, keeps the caller's extras (E0.4). */
export function buildState(fields: Record<string, unknown>): Record<string, unknown> {
  const state: Record<string, unknown> = {};
  for (const [key, value] of Object.entries(fields)) {
    if (value === null || value === undefined || value === "" || (Array.isArray(value) && value.length === 0)) {
      continue;
    }
    state[key] = value;
  }
  return state;
}

/**
 * E3.5 — masks credential-shaped material before a log is sent to a provider.
 * Mirrors `redact_secrets` in Python (and Rust): the same shapes must be masked in all three
 * runtimes, because all three can transmit a failure log.
 */
export const SECRET_PATTERNS: RegExp[] = [
  /\b(?:api[_-]?key|apikey|access[_-]?token|auth[_-]?token|secret|password|passwd|pwd|client[_-]?secret|private[_-]?key|bearer)\b\s*[:=]\s*["']?([A-Za-z0-9._\-/+]{6,})["']?/gi,
  /\b(?:sk|pk|rk|vck|xox[baprs])[-_][A-Za-z0-9._\-]{12,}/gi,
  /\bgh[pousr]_[A-Za-z0-9]{20,}/gi,
  /\bAKIA[0-9A-Z]{16}\b/g,
  /-----BEGIN [A-Z ]*PRIVATE KEY-----[\s\S]*?-----END [A-Z ]*PRIVATE KEY-----/g,
  /\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}/g,
  /(?:postgres|mysql|mongodb|redis)(?:\+\w+)?:\/\/[^\s:@/]+:[^\s@/]+@/gi,
];

export function redactSecrets(text: string): string {
  if (!text) return text;
  let redacted = text;
  for (const pattern of SECRET_PATTERNS) {
    redacted = redacted.replace(pattern, (match: string, group: unknown) => {
      // Without a capture group the second argument is the match offset (a number), so the
      // group must be type-checked before it is used for substitution.
      if (typeof group === "string" && group) return match.replace(group, "[REDACTED]");
      if (match.toLowerCase().startsWith("-----begin")) return "[REDACTED PRIVATE KEY]";
      if (match.includes("://")) return `${match.split("://")[0]}://[REDACTED]@`;
      return "[REDACTED]";
    });
  }
  return redacted;
}

/** Abort action derived from the dead-end signals (parity with Python/Rust). */
export function mockAbortActionChoice(criteria: Record<string, string>, stateLower: string): string {
  let step = stateLower;
  for (const marker of ["proposed next step:", "proposed_next_step:"]) {
    if (step.includes(marker)) step = step.split(marker).pop() as string;
  }
  const forward = [
    "implement", "fix", "resolve", "correct", "update", "create", "write", "add", "install",
    "apply", "corrigir", "implementar", "executar", "validar", "corregir",
  ].some((w) => step.includes(w));
  const repetitive = ["same", "repetir", "tentar novamente", "intentar de nuevo", "4a vez", "again", "identical"].some(
    (w) => step.includes(w)
  );
  const fatal = [
    "impossible", "impossivel", "imposible", "circular", "deadlock", "dead end", "inviavel",
    "inviable", "hopeless", "fatal",
  ].some((w) => stateLower.includes(w));
  if (repetitive || fatal) return "abort_and_ask" in criteria ? "abort_and_ask" : Object.keys(criteria)[0];
  if (forward && "proceed" in criteria) return "proceed";
  return "";
}

/**
 * A failure log is *untrusted input*: the model-jaggedness docs show that adversarial content
 * in the state can steer a decision. These markers mean "this text is addressing the judge",
 * so the log is escalated instead of classified. Kept identical to the Python and Rust lists.
 */
export const INJECTION_PATTERNS: RegExp[] = [
  /ignore\s+(?:all\s+|any\s+|the\s+)?(?:previous|prior|above|earlier|foregoing)\s+(?:instruction|prompt|rule|direction|message)s?/i,
  /disregard\s+(?:all\s+|any\s+|the\s+)?(?:above|previous|prior|earlier|system)/i,
  /\b(?:ignore|bypass|override)\s+(?:the\s+)?(?:gate|harness|instructions?|safety|polic(?:y|ies))\b/i,
  /<\|(?:im_start|im_end|system|assistant|user)\|>/i,
  /\[\/?(?:INST|SYS)\]/,
  /###\s*(?:system|instruction|assistant)\b/im,
  /"role"\s*:\s*"(?:system|assistant)"\s*,\s*"content"/i,
  /\bskip_llm\s*[:=]\s*(?:true|false)\b/i,
  /\b(?:classif|labell?|mark|report|record|return|output|respond|answer)\w*\b[^.\n]{0,60}\b(?:as\s+)?(?:env_missing|flaky_transient|syntax_trivial|no_failure)\b/i,
  /\b(?:do\s+not|don't|never)\s+(?:call|invoke|use|escalate\s+to)\s+(?:the\s+)?(?:llm|model|api|system\s*2|frontier)\b/i,
];

/** True when the log is trying to address the judge instead of describing a failure. */
export function looksLikePromptInjection(log: string): boolean {
  if (!log) return false;
  return INJECTION_PATTERNS.some((pattern) => pattern.test(log));
}

/**
 * Returns true only when a log is unequivocally a *successful* run summary.
 *
 * Strict by design: a positive success summary is required AND every failure signal
 * (non-zero counts, FAIL/FAILED markers, tracebacks, panics, dependency or transient
 * errors) must be absent, so a real failure can never be short-circuited.
 */
export function looksLikeTestSuccess(log: string): boolean {
  if (!log || !log.trim()) return false;

  const text = log.toLowerCase();

  // 1. Failure vetoes.
  if (/[1-9\uff11-\uff19\u0661-\u0669\u06f1-\u06f9][\d,._\u00a0 \uff10-\uff19\u0660-\u0669\u06f0-\u06f9]*\s*(?:failures|failure|failed|failing|errors?)\b/.test(text))
    return false;
  if (/\b[1-9\uff11-\uff19\u0661-\u0669\u06f1-\u06f9][\d,._\u00a0 \uff10-\uff19\u0660-\u0669\u06f0-\u06f9]*\s+tests?\s+failed\b/.test(text))
    return false;
  if (/(?:failures?|errors?|failed|failing)\s*[:=]\s*[1-9]/.test(text)) return false;
  // NOTE: `error:` must not be followed by \b — a colon before a space has no word boundary.
  if (/\b(?:traceback|panic|panicked|assertionerror|assertion failed|not ok)\b|error\s*:/.test(text)) return false;
  if (/\bFAILED\b/.test(log) || /(?:^|\n)\s*FAIL\b/.test(log) || /---\s*FAIL\b/.test(log)) return false;
  if (/[✗❌✘✕×‼]/.test(log)) return false;
  const unclean = [
    "module not found",
    "no module named",
    "cannot find module",
    "cannot find crate",
    "command not found",
    "connection refused",
    "connection reset",
    "econnrefused",
    "econnreset",
    "etimedout",
    "socket hang up",
    "address already in use",
    "timed out",
    "timeout",
  ];
  if (unclean.some((signal) => text.includes(signal))) return false;

  // 2. Positive success summaries (non-zero pass counts required).
  const successPatterns = [
    /test result:\s*ok/,
    /[1-9][\d,]*\s+passed\b/,
    /[1-9]\d*\s+passing\b/,
    /test suites?:\s*[1-9]\d*\s+passed/,
    /[1-9]\d*\s+examples?,\s*0\s+failures/,
    /all tests? passed/,
    /\bbuild success(?:ful)?\b/,
    /^\s*ok\s+\S+/m,
  ];
  if (successPatterns.some((pattern) => pattern.test(text))) return true;

  if (/ran\s+[1-9]\d*\s+tests?/.test(text) && /^\s*ok\s*$/m.test(text)) return true;
  return false;
}

export class JevClient {
  public apiKey?: string;
  public provider: string;
  public baseUrl: string;
  public model: string;
  /** Where the effective model came from: "argument" | "env" | ".jev.json" | "provider_default". */
  public modelSource: string;
  public timeoutMs: number;
  public forceMock: boolean;
  public maxRetries: number;
  public retryBaseDelayMs: number;
  public failOpen: boolean;

  constructor(options: JevClientOptions = {}) {
    this.timeoutMs = options.timeoutMs ?? 15000;
    this.forceMock = options.forceMock ?? false;
    this.maxRetries = Math.max(1, options.maxRetries ?? 3);
    this.retryBaseDelayMs = Math.max(0, options.retryBaseDelayMs ?? 500);
    this.failOpen = options.failOpen ?? true;

    const { key, provider } = this.resolveCredentials(options.apiKey);
    this.apiKey = key;
    this.provider = options.provider || provider;

    if (options.baseUrl) {
      this.baseUrl = options.baseUrl;
    } else if (this.provider === "commandcode") {
      this.baseUrl = COMMANDCODE_API_URL;
    } else if (this.provider === "opencode") {
      this.baseUrl = OPENCODE_API_URL;
    } else if (this.provider === "openrouter") {
      this.baseUrl = OPENROUTER_API_URL;
    } else if (this.provider === "vercel") {
      this.baseUrl = VERCEL_API_URL;
    } else {
      this.baseUrl = TYPESAFE_API_URL;
    }

    // Resolution order: explicit option > `JEV_MODEL` env var > repository `.jev.json`
    // override > provider default. The generic placeholder (`jev-latest`, what `jev init`
    // scaffolds) is treated as "no override" so scaffolded configs never clobber provider
    // model IDs.
    const repoConfig = loadRepoConfig();
    const envModel = process.env.JEV_MODEL;
    if (options.model) {
      this.model = options.model;
      this.modelSource = "argument";
    } else if (envModel && envModel.trim()) {
      this.model = envModel.trim();
      this.modelSource = "env";
    } else if (repoConfig.model && repoConfig.model !== DEFAULT_MODEL) {
      this.model = repoConfig.model;
      this.modelSource = ".jev.json";
    } else if (this.provider === "commandcode") {
      this.model = "typesafe/jev";
      this.modelSource = "provider_default";
    } else if (this.provider === "opencode") {
      this.model = "jev-1.13-free";
      this.modelSource = "provider_default";
    } else if (this.provider === "openrouter") {
      this.model = "typesafe/jev-1.13";
      this.modelSource = "provider_default";
    } else if (this.provider === "vercel") {
      this.model = "typesafe-ai/jev";
      this.modelSource = "provider_default";
    } else {
      this.model = DEFAULT_MODEL;
      this.modelSource = "provider_default";
    }
  }

  public get isLive(): boolean {
    if (this.forceMock) return false;
    if (this.provider === "opencode") return true;
    return Boolean(this.apiKey);
  }

  private resolveCredentials(explicitKey?: string): { key?: string; provider: string } {
    if (explicitKey) return { key: explicitKey, provider: "typesafe" };

    // 1. Environment variables
    if (typeof process !== "undefined" && process.env) {
      if (process.env.JEV_PROVIDER === "commandcode") {
        const cmdKey = process.env.CMD_API_KEY || process.env.COMMAND_CODE_API_KEY;
        if (cmdKey) return { key: cmdKey, provider: "commandcode" };
      }
      if (process.env.JEV_PROVIDER === "opencode") return { key: process.env.OPENCODE_API_KEY, provider: "opencode" };
      if (process.env.TYPESAFE_API_KEY) return { key: process.env.TYPESAFE_API_KEY, provider: "typesafe" };
      if (process.env.CMD_API_KEY) return { key: process.env.CMD_API_KEY, provider: "commandcode" };
      if (process.env.COMMAND_CODE_API_KEY) return { key: process.env.COMMAND_CODE_API_KEY, provider: "commandcode" };
      if (process.env.VERCEL_AI_GATEWAY_API_KEY) return { key: process.env.VERCEL_AI_GATEWAY_API_KEY, provider: "vercel" };
      if (process.env.VERCEL_API_KEY) return { key: process.env.VERCEL_API_KEY, provider: "vercel" };
      if (process.env.AI_GATEWAY_API_KEY) return { key: process.env.AI_GATEWAY_API_KEY, provider: "vercel" };
      if (process.env.OPENCODE_API_KEY) return { key: process.env.OPENCODE_API_KEY, provider: "opencode" };
      if (process.env.OPENROUTER_API_KEY) return { key: process.env.OPENROUTER_API_KEY, provider: "openrouter" };

      // 2. Local repository files (.jev.json or .env)
      try {
        let current = process.cwd();
        for (let i = 0; i < 4; i++) {
          const jevJson = path.join(current, ".jev.json");
          if (fs.existsSync(jevJson)) {
            const data = JSON.parse(fs.readFileSync(jevJson, "utf-8"));
            if (data.api_key || data.provider === "opencode") return { key: data.api_key, provider: data.provider || "typesafe" };
          }

          const dotenv = path.join(current, ".env");
          if (fs.existsSync(dotenv)) {
            const lines = fs.readFileSync(dotenv, "utf-8").split("\n");
            for (const raw of lines) {
              const line = raw.trim();
              if (line.startsWith("JEV_PROVIDER=") && line.split("=", 2)[1].replace(/['"]/g, "").trim() === "opencode") return { key: undefined, provider: "opencode" };
              if (line.startsWith("TYPESAFE_API_KEY=")) return { key: line.split("=", 2)[1].replace(/['"]/g, "").trim(), provider: "typesafe" };
              if (line.startsWith("CMD_API_KEY=")) return { key: line.split("=", 2)[1].replace(/['"]/g, "").trim(), provider: "commandcode" };
              if (line.startsWith("COMMAND_CODE_API_KEY=")) return { key: line.split("=", 2)[1].replace(/['"]/g, "").trim(), provider: "commandcode" };
              if (line.startsWith("VERCEL_AI_GATEWAY_API_KEY=")) return { key: line.split("=", 2)[1].replace(/['"]/g, "").trim(), provider: "vercel" };
              if (line.startsWith("VERCEL_API_KEY=")) return { key: line.split("=", 2)[1].replace(/['"]/g, "").trim(), provider: "vercel" };
              if (line.startsWith("AI_GATEWAY_API_KEY=")) return { key: line.split("=", 2)[1].replace(/['"]/g, "").trim(), provider: "vercel" };
              if (line.startsWith("OPENCODE_API_KEY=")) return { key: line.split("=", 2)[1].replace(/['"]/g, "").trim(), provider: "opencode" };
              if (line.startsWith("OPENROUTER_API_KEY=")) return { key: line.split("=", 2)[1].replace(/['"]/g, "").trim(), provider: "openrouter" };
            }
          }
          const parent = path.dirname(current);
          if (parent === current) break;
          current = parent;
        }
      } catch {
        // Fallback gracefully
      }

      // 3. User global config (~/.config/jev/credentials.env and ~/.commandcode/auth.json)
      try {
        const home = os.homedir();
        const globalCreds = path.join(home, ".config", "jev", "credentials.env");
        if (fs.existsSync(globalCreds)) {
          const lines = fs.readFileSync(globalCreds, "utf-8").split("\n");
          for (const raw of lines) {
            const line = raw.trim();
            if (line.startsWith("JEV_PROVIDER=") && line.split("=", 2)[1].replace(/['"]/g, "").trim() === "opencode") return { key: undefined, provider: "opencode" };
            if (line.startsWith("TYPESAFE_API_KEY=")) return { key: line.split("=", 2)[1].replace(/['"]/g, "").trim(), provider: "typesafe" };
            if (line.startsWith("CMD_API_KEY=")) return { key: line.split("=", 2)[1].replace(/['"]/g, "").trim(), provider: "commandcode" };
            if (line.startsWith("COMMAND_CODE_API_KEY=")) return { key: line.split("=", 2)[1].replace(/['"]/g, "").trim(), provider: "commandcode" };
            if (line.startsWith("VERCEL_AI_GATEWAY_API_KEY=")) return { key: line.split("=", 2)[1].replace(/['"]/g, "").trim(), provider: "vercel" };
            if (line.startsWith("VERCEL_API_KEY=")) return { key: line.split("=", 2)[1].replace(/['"]/g, "").trim(), provider: "vercel" };
            if (line.startsWith("AI_GATEWAY_API_KEY=")) return { key: line.split("=", 2)[1].replace(/['"]/g, "").trim(), provider: "vercel" };
            if (line.startsWith("OPENCODE_API_KEY=")) return { key: line.split("=", 2)[1].replace(/['"]/g, "").trim(), provider: "opencode" };
            if (line.startsWith("OPENROUTER_API_KEY=")) return { key: line.split("=", 2)[1].replace(/['"]/g, "").trim(), provider: "openrouter" };
          }
        }
        const cmdAuth = path.join(home, ".commandcode", "auth.json");
        if (fs.existsSync(cmdAuth)) {
          const authData = JSON.parse(fs.readFileSync(cmdAuth, "utf-8"));
          const cmdKey = authData?.apiKey || authData?.api_key;
          if (cmdKey && typeof cmdKey === "string" && cmdKey.trim()) {
            return { key: cmdKey.trim(), provider: "commandcode" };
          }
        }
      } catch {
        // Ignore
      }
    }

    return { key: undefined, provider: "mock" };
  }

  public async systemOne(
    state: string | Record<string, any> | any[],
    questions: Record<string, Question>,
    overrideModel?: string
  ): Promise<JevResponse> {
    const rawState = typeof state === "string" ? state : JSON.stringify(state);
    const stateStr = redactSecrets(rawState);
    const chosenModel = overrideModel || this.model;

    if (!this.isLive) {
      return this.simulateSystemOne(stateStr, questions, chosenModel);
    }

    // Count code points (not UTF-16 units) so the three runtimes agree on the limit.
    const stateChars = [...stateStr].length;
    const questionsChars = [...JSON.stringify(questions)].length;
    if (stateChars > MAX_STATE_CHARS || stateChars + questionsChars > MAX_TOTAL_CHARS) {
      throw new Error(
        `Payload exceeds the provider limit: ${stateChars} state chars + ${questionsChars} question chars ` +
          `(limit: ${MAX_STATE_CHARS} state / ${MAX_TOTAL_CHARS} total, ~32k/64k tokens). Trim the state or split the questions.`
      );
    }

    // E3.1: a question with a single option has no distribution to measure.
    for (const question of Object.values(questions)) {
      if (question.type === "choice") validateQuestionOptions(Object.keys(question.criteria));
      if (question.type === "score") validateQuestionOptions(question.criteria);
    }

    const payload: Record<string, any> = {
      model: chosenModel,
      state: stateStr,
      questions,
    };
    if (this.provider === "openrouter") {
      payload.provider = { only: ["typesafe"], allow_fallbacks: false };
    } else if (this.provider === "vercel") {
      payload.providerOptions = { gateway: { only: ["typesafe-ai"] } };
    }

    const providerMap: Record<string, string> = {
      commandcode: "Command Code",
      opencode: "OpenCode Zen",
      openrouter: "OpenRouter",
      vercel: "Vercel AI Gateway",
    };
    const providerName = providerMap[this.provider] || "TypeSafe";

    for (let attempt = 1; ; attempt++) {
      const attemptStarted = Date.now();
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), this.timeoutMs);
      try {
        const headers: Record<string, string> = {
          "Content-Type": "application/json",
          "User-Agent": DEFAULT_USER_AGENT,
        };
        if (this.apiKey && this.apiKey !== "zen") {
          headers["Authorization"] = `Bearer ${this.apiKey}`;
        }
        if (this.provider === "openrouter") {
          headers["HTTP-Referer"] = "https://github.com/ismaelsoilet/jev-harness";
          headers["X-Title"] = "Jev Harness";
        }

        const resp = await fetch(this.baseUrl, {
          method: "POST",
          headers,
          body: JSON.stringify(payload),
          signal: controller.signal,
        });

        if (!resp.ok) {
          const errText = JevClient.redactSecrets(await resp.text(), this.apiKey);
          if (resp.status === 401 || resp.status === 403) {
            const authMessage = `${providerName} auth failed (HTTP ${resp.status})`;
            if (!this.failOpen) throw new Error(authMessage);
            process.stderr.write(`[JEV WARNING] ${authMessage}; falling back to offline simulation.\n`);
            return this.markDegraded(this.simulateSystemOne(stateStr, questions, chosenModel), `auth_${resp.status}`);
          }
          const retryable = resp.status === 429 || resp.status >= 500;
          if (retryable && attempt < this.maxRetries) {
            await this.sleep(this.retryDelayMs(attempt, resp.headers?.get("retry-after") ?? undefined));
            continue;
          }
          const message = `${providerName} API HTTP ${resp.status}: ${errText}`;
          if (this.failOpen) {
            process.stderr.write(`[JEV WARNING] ${message}; falling back to offline simulation.\n`);
            return this.markDegraded(this.simulateSystemOne(stateStr, questions, chosenModel), `http_${resp.status}`);
          }
          throw new Error(message);
        }

        const data = await resp.json();
        return this.parseResponse(data, chosenModel, false);
      } catch (err: any) {
        const elapsed = Date.now() - attemptStarted;
        const malformed = err?.name === "MalformedResponseError";
        const retryableTransport =
          err?.name === "AbortError" || err?.name === "TypeError" || err?.name === "SyntaxError" || malformed;
        if (retryableTransport) {
          if (attempt < this.maxRetries) {
            await this.sleep(this.retryDelayMs(attempt));
            continue;
          }
          const invalidResponse = err?.name === "SyntaxError" || malformed;
          // A read timeout can surface as a generic TypeError: classify by elapsed time
          // so the marker matches Python and Rust.
          const isTimeout =
            err?.name === "AbortError" || (!invalidResponse && elapsed >= this.timeoutMs * 0.9);
          const message = malformed
            ? `${providerName} returned a malformed response: ${err?.message ?? err}`
            : invalidResponse
              ? `${providerName} returned a non-JSON response`
              : isTimeout
                ? `${providerName} API request timed out after ${this.timeoutMs}ms`
                : `Failed to connect to ${providerName} API (${this.baseUrl}): ${err?.message ?? err}`;
          if (this.failOpen) {
            process.stderr.write(`[JEV WARNING] ${message}; falling back to offline simulation.\n`);
            return this.markDegraded(
              this.simulateSystemOne(stateStr, questions, chosenModel),
              invalidResponse ? "invalid_response" : isTimeout ? "timeout" : "connection"
            );
          }
          throw new Error(message);
        }
        throw err;
      } finally {
        clearTimeout(timeoutId);
      }
    }
  }

  /** Exponential backoff honoring a provider Retry-After (seconds), capped for fast CI. */
  public retryDelayMs(attempt: number, retryAfter?: string): number {
    if (retryAfter) {
      const parsed = Number(String(retryAfter).trim());
      if (Number.isFinite(parsed) && parsed >= 0) return Math.min(30000, parsed * 1000);
    }
    return Math.max(0, Math.min(5000, this.retryBaseDelayMs * Math.pow(2, Math.max(0, attempt - 1))));
  }

  private sleep(ms: number): Promise<void> {
    return new Promise((resolve) => setTimeout(resolve, ms));
  }

  private markDegraded(resp: JevResponse, reason: string): JevResponse {
    return { ...resp, degradedReason: reason };
  }

  public static redactSecrets(text: string, secret?: string): string {
    if (!text) return "";
    let cleaned = text;
    if (secret && secret.length >= 4) {
      cleaned = cleaned.split(secret).join("[REDACTED]");
    }
    return cleaned
      .replace(/(?:Bearer\s+|(?:vck_|sk-))[A-Za-z0-9._-]+/gi, "[REDACTED]")
      .slice(0, 400);
  }

  /**
   * A live payload with type-mismatched fields (`score: "N/A"`, `answers: [...]`) is a parse
   * failure handled by the failure policy — never a silent `NaN` or a dropped answer.
   */
  private parseResponse(data: any, model: string, isMock: boolean): JevResponse {
    const answers: Record<string, Answer> = {};
    if (data && typeof data === "object" && data.answers !== undefined && data.answers !== null) {
      if (typeof data.answers !== "object" || Array.isArray(data.answers)) {
        throw new MalformedResponseError("malformed response: 'answers' must be a JSON object");
      }
    }
    const rawAnswers = (data && typeof data === "object" && data.answers && typeof data.answers === "object")
      ? data.answers
      : {};

    for (const [qid, ans] of Object.entries<any>(rawAnswers)) {
      if (!ans || typeof ans !== "object" || Array.isArray(ans)) {
        throw new MalformedResponseError(`malformed response: answer '${qid}' must be a JSON object`);
      }
      if (ans.type === "choice") {
        answers[qid] = {
          type: "choice",
          choice: requiredText(ans, "choice", qid),
          confidence: finiteNumber(ans.confidence, "confidence", qid),
          probabilities: ans.probabilities,
        };
      } else if (ans.type === "score") {
        answers[qid] = {
          type: "score",
          score: finiteNumber(ans.score, "score", qid),
          confidence: finiteNumber(ans.confidence, "confidence", qid),
          probabilities: ans.probabilities,
          legend: ans.legend,
        };
      } else if (ans.type === "noul") {
        answers[qid] = {
          type: "noul",
          noul: finiteNumber(ans.noul, "noul", qid),
        };
      } else {
        // An answer the runtime cannot interpret must never be dropped: the gate would
        // silently use its default score instead of the provider's judgement.
        throw new MalformedResponseError(
          `malformed response: answer '${qid}' has an unsupported type ${JSON.stringify(ans.type)}`
        );
      }
    }

    if (Object.keys(answers).length === 0 && !isMock) {
      // Nothing usable would silently make every gate fall back to its defaults.
      throw new MalformedResponseError("malformed response: no answers could be parsed");
    }

    const usage = (data && typeof data === "object" && data.usage && typeof data.usage === "object")
      ? data.usage
      : {
          input_tokens: Math.max(10, Math.floor(String((data && data.state) || "").length / 4)),
          output_tokens: 0,
        };

    return {
      model: (data && data.model) || model,
      answers,
      usage,
      isMock,
      rawResponse: data,
    };
  }

  public simulateSystemOne(
    state: string | Record<string, unknown>,
    questions: Record<string, Question>,
    model: string
  ): JevResponse {
    const rendered = renderStateText(state);
    const stateLower = rendered.toLowerCase();
    const stateTokens = new Set(stateLower.match(/[\p{L}\p{N}_]+/gu) || []);
    const answers: Record<string, Answer> = {};

    // Mirrors Python exactly: the `^fail...` alternative is line-anchored, so it must be tested
    // per stripped line (a bare `/^/` without `m` would only match the start of the whole state,
    // which silently changed the verdict in one runtime).
    const assertionLine =
      /(?:assertionerror|assertionfailed|assertionfailederror|assert\b|assert_eq!|assertthat|expect\(.*?\)\.to|expected:.*received:|failures?:|fail(?:ed)?\s+test|^fail(?:ed)?(?!\s+to\b)\b|falha de asserção|fallo de aserción|opentest4j)/i;
    const realAssertion =
      stateLower.split(/\r?\n/).some((line) => assertionLine.test(line.trim())) ||
      // Cross-line Expectation/Reality pairs (rules/04 precedence) remain explicit assertions.
      /expected:[\s\S]{0,300}?received:/i.test(stateLower);
    const bareException = /(?:^|\n)\s*(?:valueerror|runtimeerror|typeerror|keyerror|indexerror|zerodivisionerror|attributeerror|overflowerror|arithmeticerror|illegalargumentexception|illegalstateexception):/i.test(stateLower);
    const hasExplicitFailure = /(?:assertionerror|assertionfailed|assertionfailederror|failures?:\s*[1-9]|failed\b|falhou\b|\d+\s+failed\b|not\s+ok\b|segmentation\s+fault|sigsegv|panic\b|core\s+dumped)/i.test(stateLower);
    const hasHeavyKeywords = /(?:kernel|distributed|architecture|refactor|concurrency|deadlock|multi-file|consensus|supervision tree|arquitetura|distribuído|distribuída|distribuido|refatorar|refatoração|concorrência|concorrencia|consenso|múltiplos arquivos|condição de corrida|arquitectura|concurrencia|condición de carrera|múltiples archivos)/i.test(stateLower);
    const hasDeadlockOrLoop = /(?:infinite\s+loop|loop\s+infinito|bucle\s+infinito|deadlock|dead\s+lock|bloqueo\s+mutuo|livelock|hung|mutex|spin\s*lock|goroutines\s+are\s+asleep)/i.test(stateLower);
    const isNegatedAbort = /\b(?:not|do\s+not|don't|não|nao|no|never|sem|evitar|avoid)\s+(?:\w+\s+){0,3}(?:abort|abortar|stop|parar|detener|falhar|fail|deadlock|circular|dead\s*end)/i.test(stateLower);

    const envMissingTriggers = [
      "modulenotfounderror", "no module named", "importerror",
      "cannot find module", "err_module_not_found", "ts2307", "cannot find crate",
      "can't find crate", "e0463",
      "cannot find package", "no required module provides package",
      "classnotfoundexception", "noclassdeffounderror", "package does not exist",
      "no such file or directory", "command not found", "module not found", "package not found", "crate not found",
      "cs0246", "type or namespace name", "cannot load such file", "loaderror",
      "módulo não encontrado", "modulo nao encontrado", "nenhum módulo chamado", "pacote não encontrado",
      "módulo no encontrado", "modulo no encontrado", "no se encontró el módulo", "paquete no encontrado"
    ];
    const flakyTriggers = [
      "connectionreset", "timeout", "timed out", "econnreset", "econnrefused",
      "etimedout", "socket hang up", "gateway timeout", "503 service unavailable",
      "tempo limite", "tempo limite esgotado", "conexão recusada", "conexao recusada",
      "tiempo de espera agotado", "conexión rechazada", "conexion rechazada",
      "already in use", "address already in use", "eaddrinuse", "port already in use", "port is already in use",
      "porta já está em uso", "puerto ya está en uso"
    ];

    // Precedence rule (.agents/rules/04): an explicit assertion/expectation mismatch always
    // outranks dependency or transient words in the same log. A bare exception name is logic
    // evidence only when no concrete env/flaky root cause is present.
    const hasEnvSignal = envMissingTriggers.some((k) => stateLower.includes(k));
    const hasFlakySignal = flakyTriggers.some((k) => stateLower.includes(k));
    const isExplicitAssertion = realAssertion || (bareException && !(hasEnvSignal || hasFlakySignal));
    const syntaxTriggers = [
      "syntaxerror", "indentationerror", "expected ';'", "ts1005", "missing bracket",
      "erro de sintaxe", "sintaxe inválida", "indentação inesperada",
      "error de sintaxis", "sintaxis inválida"
    ];
    const deepLogicTriggers = [
      "assertionerror", "assertionfailed", "assertionfailederror", "assert ", "panicked at", "panic:", "panic",
      "deadlock", "goroutines are asleep", "infinite loop", "loop infinito", "bucle infinito", "bloqueo mutuo",
      "mutex", "segmentation fault", "sigsegv", "addresssanitizer", "core dumped",
      "nullpointerexception", "nullreferenceexception", "arrayindexoutofboundsexception",
      "nil pointer dereference", "index out of bounds",
      "falha de asserção", "asserção", "erro de lógica", "fallo de aserción", "error de lógica", "expect("
    ];
    const singleWordMech = new Set([
      "git", "diff", "typo", "flake8", "eslint", "prettier", "linter",
      "echo", "pwd", "format", "black", "lint", "cat", "ls"
    ]);
    const multiWordMech = [
      "git status", "git diff", "git log", "view file", "read file", "cat file",
      "check status", "run linter", "fix typo", "ler arquivo", "verificar arquivo",
      "formatar código", "leer archivo", "corregir errata", "listar arquivos",
      "listar diretório"
    ];
    const hasMechTrigger = Array.from(singleWordMech).some((w) => stateTokens.has(w)) || multiWordMech.some((p) => stateLower.includes(p));

    for (const [qid, q] of Object.entries(questions)) {
      if (q.type === "choice") {
        let bestChoice = "deep_logic" in q.criteria
          ? "deep_logic"
          : "lightweight_system2" in q.criteria
          ? "lightweight_system2"
          : "proceed" in q.criteria
          ? "proceed"
          : Object.keys(q.criteria)[0];
        // The abort gate's action is derived from the same signals as its dead-end question:
        // letting token overlap pick "abort_and_ask" beside a low dead-end probability made the
        // gate contradict its own evidence (parity with Python/Rust).
        const derivedAbortAction =
          "abort_and_ask" in q.criteria && "proceed" in q.criteria
            ? mockAbortActionChoice(q.criteria, stateLower)
            : "";
        if (derivedAbortAction) bestChoice = derivedAbortAction;
        let bestScore = 0;

        // Canonical (sorted) order so ties break identically in every runtime.
        for (const opt of Object.keys(q.criteria).sort()) {
          const desc = q.criteria[opt];
          const optTokens = (opt + " " + desc).toLowerCase().match(/[\p{L}\p{N}_]+/gu) || [];
          let matchScore = optTokens.filter((t) => stateTokens.has(t)).length;

          if (stateLower.includes(opt.toLowerCase())) matchScore += 3;

          if (opt === "deep_logic") {
            if (deepLogicTriggers.some((k) => stateLower.includes(k))) matchScore += 8;
            if (isExplicitAssertion || hasDeadlockOrLoop) matchScore += 18;
          } else if (
            opt === "env_missing" &&
            envMissingTriggers.some((k) => stateLower.includes(k))
          ) {
            matchScore += isExplicitAssertion ? 0 : 7;
          } else if (
            opt === "flaky_transient" &&
            flakyTriggers.some((k) => stateLower.includes(k))
          ) {
            matchScore += (isExplicitAssertion || hasDeadlockOrLoop) ? 0 : 7;
          } else if (
            opt === "syntax_trivial" &&
            syntaxTriggers.some((k) => stateLower.includes(k))
          ) {
            matchScore += 6;
          } else if (
            opt === "deterministic" &&
            (hasMechTrigger || ["bash", "regex", "script"].some((k) => stateTokens.has(k)))
          ) {
            matchScore += hasHeavyKeywords ? 2 : 7;
          } else if (opt === "heavy_system2" && hasHeavyKeywords) {
            matchScore += 16;
          } else if (opt === "abort_and_ask") {
            if (!isNegatedAbort && ["repeat", "circular", "deadlock", "same", "tentar novamente", "intentar de nuevo", "mesma", "abort"].some((k) => stateLower.includes(k))) {
              matchScore += 8;
            }
          } else if (opt === "proceed") {
            if (isNegatedAbort || ["proceed", "unit test", "test", "verify", "verifying", "incremental", "progress", "implement", "add", "adicionar", "migration"].some((k) => stateLower.includes(k))) {
              matchScore += 8;
            }
          }

          if (derivedAbortAction) continue; // derived from the dead-end signal, not overlap
          if (matchScore > bestScore) {
            bestScore = matchScore;
            bestChoice = opt;
          }
        }

        const isEffortQ = qid === "effort" || ["none", "minimal", "low", "medium", "high", "xhigh", "max", "ultra"].some((eff) => eff in q.criteria);

        if (isEffortQ) {
          if (
            hasHeavyKeywords ||
            [
              "deadlock", "race condition", "distributed", "concurrency", "kernel",
              "supervision", "architectural", "complex", "algorithmic", "deadlocks", "concorrência", "arquitetura",
              "condição de corrida", "arquitectura", "concurrencia"
            ].some((k) => stateLower.includes(k))
          ) {
            if ("ultra" in q.criteria && stateLower.includes("beyond max")) {
              bestChoice = "ultra";
            } else if ("max" in q.criteria && (stateLower.includes("first principles") || stateLower.includes("proof"))) {
              bestChoice = "max";
            } else if ("xhigh" in q.criteria && (stateLower.includes("first principles") || stateLower.includes("subsystems"))) {
              bestChoice = "xhigh";
            } else if ("high" in q.criteria) {
              bestChoice = "high";
            } else if ("xhigh" in q.criteria) {
              bestChoice = "xhigh";
            } else if ("max" in q.criteria) {
              bestChoice = "max";
            } else if ("medium" in q.criteria) {
              bestChoice = "medium";
            } else {
              bestChoice = Object.keys(q.criteria).pop()!;
            }
          } else if (hasMechTrigger && !hasHeavyKeywords) {
            if ("none" in q.criteria && ["git status", "pwd", "echo", "version"].some((m) => stateLower.includes(m))) {
              bestChoice = "none";
            } else if ("minimal" in q.criteria && ["git status", "pwd", "echo", "version"].some((m) => stateLower.includes(m))) {
              bestChoice = "minimal";
            } else if ("low" in q.criteria) {
              bestChoice = "low";
            } else if ("minimal" in q.criteria) {
              bestChoice = "minimal";
            } else if ("none" in q.criteria) {
              bestChoice = "none";
            } else if ("medium" in q.criteria) {
              bestChoice = "medium";
            } else {
              bestChoice = Object.keys(q.criteria)[0];
            }
          } else {
            if ("medium" in q.criteria) {
              bestChoice = "medium";
            } else if ("high" in q.criteria) {
              bestChoice = "high";
            } else if ("low" in q.criteria) {
              bestChoice = "low";
            } else {
              bestChoice = Object.keys(q.criteria)[0];
            }
          }
        } else if (qid === "workflow_phase" || ("execute" in q.criteria && "complete" in q.criteria)) {
          // Canonical phase contract (parity with Python/Rust): same lists, same precedence.
          const isWaitingQ = stateLower.includes("?") || [
            "waiting for your",
            "waiting on user",
            "wait for my go-ahead",
            "please confirm",
            "which option",
            "do you approve",
            "would you like me to",
            "do you want me to",
            "need your api key",
            "aguardando sua aprovação",
            "aguardando usuário",
            "qual opção você prefere",
            "qual opção",
            "preciso que você confirme",
            "preciso de permissão",
            "need clarification",
            "please clarify",
            "need permission",
          ].some((w) => stateLower.includes(w));
          const isUnverified = [
            "without running tests",
            "tests not run",
            "unverified",
            "haven't run pytest",
            "todo: run tests",
            "falta rodar os testes",
            "sem testar",
            "need to verify",
            "to verify",
            "run pytest",
            "run cargo test",
            "run npm test",
            "need to run",
            "updated file",
            "edited file",
            "finished editing",
            "modified file",
            "wrote code",
            "atualizei o arquivo",
            "alterei o arquivo",
            "terminei de editar",
            "arquivo alterado",
          ].some((w) => stateLower.includes(w));
          const isUnfinished = [
            "next i'll",
            "next i will",
            "now i will",
            "continuarei",
            "a seguir vou",
            "próximo passo farei",
            "1 of 5",
            "2 of 5",
            "3 of 5",
            "4 of 5",
            "step 1 of",
            "step 1 done",
            "unfinished",
            "remaining",
            "todo:",
            "pendente",
            "partial",
            "parcial",
            "in progress",
            "falta implementar",
            "falta rodar os testes",
            "sem testar",
            "without running tests",
            "tests not run",
            "haven't run pytest",
            "need to run",
            "need to verify",
            "to verify",
            "unverified",
            "run pytest",
            "run cargo test",
            "run npm test",
            "updated file",
            "edited file",
            "finished editing",
            "modified file",
            "wrote code",
            "atualizei o arquivo",
            "alterei o arquivo",
            "terminei de editar",
            "arquivo alterado",
            "next step",
          ].some((w) => stateLower.includes(w));
          const isComplete = [
            "all done",
            "100% passing",
            "all criteria satisfied",
            "tudo concluído",
            "todas as etapas concluídas",
            "task complete",
            "konnichiwa! all done",
            "all tests passed",
            "tests passed (0 failed)",
            "completed and verified",
            "completed all",
            "concluído com sucesso",
            "todos os testes passaram",
          ].some((w) => stateLower.includes(w));

          if (isWaitingQ && "ask" in q.criteria) {
            bestChoice = "ask";
          } else if (isComplete && "complete" in q.criteria) {
            bestChoice = "complete";
          } else if (isUnverified && "verify" in q.criteria) {
            bestChoice = "verify";
          } else if (isUnfinished && "execute" in q.criteria) {
            bestChoice = "execute";
          }
          // Beyond the four signals above the phase is decided by the generic scoring, which is
          // what the other runtimes do — the calibration corpus measures it as the better rule
          // (bare keywords like "test" pointed at `verify` for a transcript that was `execute`).
        } else if (qid === "lease" || ("1" in q.criteria && ["2", "5", "10"].some((x) => x in q.criteria))) {
          // Astra-Ares multi-generation lease question
          if (["error", "fail", "erro", "falha", "deadlock", "panic", "exception"].some((k) => stateLower.includes(k))) {
            bestChoice = "1";
          } else if (hasMechTrigger && !hasHeavyKeywords) {
            bestChoice = "5" in q.criteria ? "5" : ("2" in q.criteria ? "2" : "1");
          } else {
            bestChoice = "2" in q.criteria ? "2" : ("5" in q.criteria ? "5" : "1");
          }
          if (!(bestChoice in q.criteria)) {
            bestChoice = Object.keys(q.criteria)[0];
          }
        }

        const hasSignalConflict =
          (isExplicitAssertion || hasDeadlockOrLoop) && (hasEnvSignal || hasFlakySignal);
        const probs = mockDistribution(
          Object.keys(q.criteria),
          bestChoice,
          hasSignalConflict ? MOCK_CHOICE_BEST_CONFLICT : MOCK_CHOICE_BEST_PEAKED
        );

        answers[qid] = {
          type: "choice",
          choice: bestChoice,
          confidence: 0.88,
          probabilities: probs,
        };
      } else if (q.type === "score") {
        const nLevels = q.criteria.length;
        let matchedIdx = qid === "viability" ? 3 : 2;

        if (hasExplicitFailure && ["satisfaction", "rigor"].includes(qid)) {
          matchedIdx = 1;
        } else if (
          qid === "viability" &&
          (["deadlock", "circular", "impossible", "impossivel", "imposible", "doomed", "inviavel", "inviable"].some((w) => stateLower.includes(w)) || hasDeadlockOrLoop)
        ) {
          matchedIdx = 1;
        } else if (
          !hasExplicitFailure &&
          ["satisfy", "satisfaz", "satisface", "atende", "passed", "passou", "pasó", "pass", "sucesso", "éxito", "success", "excellent", "exhaustively", "complete", "concluido", "completado", "proceed"].some((w) => stateLower.includes(w)) &&
          !["not ok", "failed", "falhou"].some((neg) => stateLower.includes(neg))
        ) {
          matchedIdx = nLevels;
        } else if (qid !== "viability" && ["trivial", "minor", "pequeno", "menor"].some((w) => stateLower.includes(w)) && !hasHeavyKeywords) {
          matchedIdx = 1;
        } else if (qid !== "viability" && (hasHeavyKeywords || ["critical", "critico", "crítico", "fatal", "disaster", "destrutivo", "complex", "complexo", "complejo"].some((w) => stateLower.includes(w)))) {
          matchedIdx = nLevels;
        }

        for (let idx = 0; idx < q.criteria.length; idx++) {
          const levelTokens = (q.criteria[idx] || "").toLowerCase().match(/[\p{L}\p{N}_]+/gu) || [];
          if (levelTokens.some((t) => stateTokens.has(t)) && !(hasExplicitFailure && idx > 0 && ["satisfaction", "rigor"].includes(qid))) {
            matchedIdx = idx + 1;
          }
        }

        answers[qid] = {
          type: "score",
          score: matchedIdx,
          confidence: 0.85,
          probabilities: mockDistribution(
            q.criteria.map((_: string, i: number) => String(i + 1)),
            String(matchedIdx),
            MOCK_SCORE_BEST_PEAKED
          ),
          legend: q.criteria,
        };
      } else if (q.type === "noul") {
        const inst = q.instructions.toLowerCase();
        let prob = 0.15;

        const negativeSignals = ["abort", "abortar", "fail", "falha", "fallo", "error", "erro", "impossible", "impossivel", "imposible", "fatal", "circular", "deadlock", "broken", "unviable", "inviavel", "inviable", "destrutivo"];
        const positiveSignals = ["pass", "passed", "passou", "pasó", "success", "sucesso", "éxito", "resolved", "resuelto", "valid", "válido", "satisfy", "satisfaz", "satisface", "complete", "completado", "proceed", "linear"];

        // Structured state (E0.4) or legacy concatenated text — accept both markers.
        let proposedPart = stateLower;
        for (const marker of ["proposed next step:", "proposed_next_step:"]) {
          if (proposedPart.includes(marker)) proposedPart = proposedPart.split(marker).pop() as string;
        }
        const isForwardProgress = ["implement", "fix", "resolve", "correct", "update", "create", "write", "corrigir", "implementar", "executar", "validar", "corregir"].some((w) => proposedPart.includes(w));
        const isRepetitiveLoop = ["same", "repetir", "tentar novamente", "intentar de nuevo", "4a vez", "again", "identical"].some((w) => proposedPart.includes(w));
        const isFatalDeadlock = ["impossible", "impossivel", "imposible", "circular", "deadlock", "dead end", "inviavel", "inviable", "hopeless", "fatal"].some((w) => stateLower.includes(w));

        if (hasExplicitFailure && ["pass", "valid", "satisfy", "complete", "verif"].some((w) => inst.includes(w))) {
          prob = 0.05;
        } else if (isNegatedAbort && ["abort", "dead", "unviable", "destructive"].some((w) => inst.includes(w))) {
          prob = 0.08;
        } else if ((isFatalDeadlock || hasDeadlockOrLoop) && ["abort", "dead", "fail", "urgent", "invalid", "unviable", "destructive", "dead end"].some((w) => inst.includes(w))) {
          prob = 0.88;
        } else if (["abort", "dead", "fail", "urgent", "invalid", "unviable", "destructive", "dead end"].some((w) => inst.includes(w))) {
          if (isRepetitiveLoop) {
            prob = 0.88;
          } else if (isForwardProgress) {
            prob = 0.12;
          } else if (negativeSignals.some((w) => stateLower.includes(w))) {
            prob = 0.85;
          } else {
            prob = 0.15;
          }
        }

        if (!hasExplicitFailure && positiveSignals.some((w) => stateLower.includes(w)) && !["not ok", "failed", "falhou"].some((neg) => stateLower.includes(neg))) {
          if (["pass", "valid", "satisfy", "complete", "verif"].some((w) => inst.includes(w))) {
            prob = 0.92;
          } else if (["abort", "dead", "unviable"].some((w) => inst.includes(w))) {
            prob = 0.08;
          }
        }

        if ((isExplicitAssertion || hasDeadlockOrLoop) && (inst.includes("deterministically") || inst.includes("skip"))) {
          prob = 0.05;
        } else if (
          [...envMissingTriggers, ...flakyTriggers, "pip install", "npm install", "cargo add"].some((w) => stateLower.includes(w)) &&
          !(isExplicitAssertion || hasDeadlockOrLoop)
        ) {
          if (inst.includes("deterministically") || inst.includes("skip")) {
            prob = 0.95;
          }
        }

        // CommandCode Jev Nudge continuation heuristics
        const isWaitingOnUser = stateLower.includes("?") || [
          "waiting on user", "need permission", "please clarify", "which option",
          "would you like me to", "do you want me to", "aguardando usuário",
          "preciso de permissão", "qual opção"
        ].some((w) => stateLower.includes(w));
        const isDone = [
          "all done", "100% passing", "all criteria satisfied", "tudo concluído",
          "todas as etapas concluídas", "task complete", "konnichiwa! all done",
          "all tests passed", "tests passed (0 failed)", "completed and verified"
        ].some((w) => stateLower.includes(w));
        const hasUnfinishedWork = [
          "next i'll",
          "next i will",
          "now i will",
          "continuarei",
          "a seguir vou",
          "próximo passo farei",
          "1 of 5",
          "2 of 5",
          "3 of 5",
          "4 of 5",
          "step 1 of",
          "step 1 done",
          "unfinished",
          "remaining",
          "todo:",
          "pendente",
          "partial",
          "parcial",
          "in progress",
          "falta implementar",
          "falta rodar os testes",
          "sem testar",
          "without running tests",
          "tests not run",
          "haven't run pytest",
          "need to run",
          "need to verify",
          "to verify",
          "unverified",
          "run pytest",
          "run cargo test",
          "run npm test",
          "updated file",
          "edited file",
          "finished editing",
          "modified file",
          "wrote code",
          "atualizei o arquivo",
          "alterei o arquivo",
          "terminei de editar",
          "arquivo alterado",
          "next step",
        ].some((w) => stateLower.includes(w));
        const hasNoProgress = [
          "no progress", "stuck", "same output", "unchanged", "repeated without change",
          "sem progresso", "mesma saída"
        ].some((w) => stateLower.includes(w));

        if (qid === "waiting" || inst.includes("waiting on the user")) {
          prob = isWaitingOnUser ? 0.88 : 0.08;
        } else if (qid === "progress" || inst.includes("last nudge produce real progress")) {
          prob = hasNoProgress ? 0.12 : 0.85;
        } else if (qid === "nudge" || inst.includes("gentle nudge")) {
          if (isWaitingOnUser || hasNoProgress || isDone) {
            prob = 0.06;
          } else if (hasUnfinishedWork) {
            prob = 0.82;
          } else {
            prob = 0.2;
          }
        }

        answers[qid] = {
          type: "noul",
          noul: prob,
        };
      }
    }

    return {
      model: `${model}-simulation`,
      answers,
      usage: {
        input_tokens: Math.max(10, Math.floor(rendered.length / 4)),
        output_tokens: 0,
      },
      isMock: true,
      rawResponse: { simulated: true },
    };
  }
}
