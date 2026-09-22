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

export const TYPESAFE_API_URL = "https://api.typesafe.ai/v1/systemone";
export const COMMANDCODE_API_URL = "https://api.commandcode.ai/provider/v1/systemone";
export const OPENCODE_API_URL = "https://opencode.ai/zen/v1/systemone";
export const OPENROUTER_API_URL = "https://openrouter.ai/api/alpha/decisions";
export const VERCEL_API_URL = "https://ai-gateway.vercel.sh/v1/evaluate";
export const DEFAULT_MODEL = "jev-latest";
export const DEFAULT_USER_AGENT = "Mozilla/5.0 (compatible; JevHarness/0.1.11; +https://github.com/ismaelsoilet/jev-harness)";

export class JevClient {
  public apiKey?: string;
  public provider: string;
  public baseUrl: string;
  public model: string;
  public timeoutMs: number;
  public forceMock: boolean;

  constructor(options: JevClientOptions = {}) {
    this.timeoutMs = options.timeoutMs ?? 15000;
    this.forceMock = options.forceMock ?? false;

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

    // Resolution order: explicit option > repository `.jev.json` override > provider
    // default. The generic placeholder (`jev-latest`, what `jev init` scaffolds) is treated
    // as "no override" so scaffolded configs never clobber provider model IDs.
    const repoConfig = loadRepoConfig();
    if (options.model) {
      this.model = options.model;
    } else if (repoConfig.model && repoConfig.model !== DEFAULT_MODEL) {
      this.model = repoConfig.model;
    } else if (this.provider === "commandcode") {
      this.model = "typesafe/jev";
    } else if (this.provider === "opencode") {
      this.model = "jev-1.13-free";
    } else if (this.provider === "openrouter") {
      this.model = "typesafe/jev-1.13";
    } else if (this.provider === "vercel") {
      this.model = "typesafe-ai/jev";
    } else {
      this.model = DEFAULT_MODEL;
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
    const stateStr = typeof state === "string" ? state : JSON.stringify(state);
    const chosenModel = overrideModel || this.model;

    if (!this.isLive) {
      return this.simulateSystemOne(stateStr, questions, chosenModel);
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
        const providerMap: Record<string, string> = {
          commandcode: "Command Code",
          opencode: "OpenCode Zen",
          openrouter: "OpenRouter",
          vercel: "Vercel AI Gateway",
        };
        const providerName = providerMap[this.provider] || "TypeSafe";
        if (resp.status === 401 || resp.status === 403) {
          process.stderr.write(`[JEV WARNING] ${providerName} auth failed (HTTP ${resp.status}); falling back to offline simulation.\n`);
          return this.simulateSystemOne(stateStr, questions, chosenModel);
        }
        throw new Error(`${providerName} API HTTP ${resp.status}: ${errText}`);
      }

      const data = await resp.json();
      return this.parseResponse(data, chosenModel, false);
    } catch (err: any) {
      if (err.name === "AbortError") {
        const providerMap: Record<string, string> = {
          commandcode: "Command Code",
          opencode: "OpenCode Zen",
          openrouter: "OpenRouter",
          vercel: "Vercel AI Gateway",
        };
        const providerName = providerMap[this.provider] || "TypeSafe";
        throw new Error(`${providerName} API request timed out after ${this.timeoutMs}ms`);
      }
      throw err;
    } finally {
      clearTimeout(timeoutId);
    }
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

  private parseResponse(data: any, model: string, isMock: boolean): JevResponse {
    const answers: Record<string, Answer> = {};
    const rawAnswers = (data && typeof data === "object" && data.answers && typeof data.answers === "object")
      ? data.answers
      : {};

    for (const [qid, ans] of Object.entries<any>(rawAnswers)) {
      if (!ans || typeof ans !== "object") continue;
      if (ans.type === "choice" || ans.choice !== undefined) {
        answers[qid] = {
          type: "choice",
          choice: String(ans.choice || ""),
          confidence: Number(ans.confidence ?? 1.0),
          probabilities: ans.probabilities,
        };
      } else if (ans.type === "score" || ans.score !== undefined) {
        answers[qid] = {
          type: "score",
          score: Number(ans.score ?? 0.0),
          confidence: Number(ans.confidence ?? 1.0),
          probabilities: ans.probabilities,
          legend: ans.legend,
        };
      } else if (ans.type === "noul" || ans.noul !== undefined) {
        answers[qid] = {
          type: "noul",
          noul: Number(ans.noul ?? 0.0),
        };
      }
    }

    const usage = (data && typeof data === "object" && data.usage) || {
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

  public simulateSystemOne(state: string, questions: Record<string, Question>, model: string): JevResponse {
    const stateLower = state.toLowerCase();
    const stateTokens = new Set(stateLower.match(/\w+/g) || []);
    const answers: Record<string, Answer> = {};

    const realAssertion =
      /(?:assertionerror|assertionfailed|assertionfailederror|assert\b|assert_eq!|assertthat|expect\(.*?\)\.to|expected:.*received:|failures?:|fail(?:ed)?\s+test|^fail(?:ed)?(?!\s+to\b)\b|falha de asserção|fallo de aserción|opentest4j)/i.test(stateLower) ||
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
        let bestScore = 0;

        for (const [opt, desc] of Object.entries(q.criteria)) {
          const optTokens = (opt + " " + desc).toLowerCase().match(/\w+/g) || [];
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
        } else if (qid === "workflow_phase" || ("execute" in q.criteria && "verify" in q.criteria)) {
          const isWaitingQ = stateLower.includes("?") || [
            "waiting on user", "need permission", "please clarify", "which option",
            "would you like me to", "do you want me to", "aguardando usuário",
            "preciso de permissão", "qual opção"
          ].some((w) => stateLower.includes(w));
          const isUnverified = [
            "without running tests", "tests not run", "unverified", "haven't run pytest",
            "todo: run tests", "falta rodar os testes", "sem testar", "need to verify",
            "to verify", "run pytest", "run cargo test", "run npm test", "need to run",
            "updated file", "edited file", "finished editing", "modified file", "wrote code",
            "atualizei o arquivo", "alterei o arquivo", "terminei de editar", "arquivo alterado"
          ].some((w) => stateLower.includes(w));
          const isUnfinished = [
            "todo", "remaining", "next step", "unfinished", "partial", "in progress",
            "falta implementar", "pendente", "continuarei", "step 1 of"
          ].some((w) => stateLower.includes(w));
          const isComplete = [
            "all tests passed", "tests passed (0 failed)", "completed and verified", "100% passing", "completed all", "task complete",
            "concluído com sucesso", "todos os testes passaram"
          ].some((w) => stateLower.includes(w));

          if (isWaitingQ && "ask" in q.criteria) {
            bestChoice = "ask";
          } else if (isUnverified && "verify" in q.criteria) {
            bestChoice = "verify";
          } else if (isUnfinished && "execute" in q.criteria) {
            bestChoice = "execute";
          } else if (isComplete && "complete" in q.criteria) {
            bestChoice = "complete";
          } else if (["plan", "architecture", "design", "planejamento"].some((w) => stateLower.includes(w)) && "plan" in q.criteria) {
            bestChoice = "plan";
          } else if (["research", "investigat", "search", "pesquisando"].some((w) => stateLower.includes(w)) && "research" in q.criteria) {
            bestChoice = "research";
          } else {
            bestChoice = "execute" in q.criteria ? "execute" : Object.keys(q.criteria)[0];
          }
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

        const totalOpts = Object.keys(q.criteria).length;
        const probs: Record<string, number> = {};
        for (const k of Object.keys(q.criteria)) {
          probs[k] = k === bestChoice ? 0.88 : 0.12 / Math.max(1, totalOpts - 1);
        }

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
          ["satisfy", "satisfaz", "satisface", "atende", "passed", "passou", "pasó", "sucesso", "éxito", "pass", "success", "excellent", "exhaustively", "complete", "concluido", "completado"].some((w) => stateLower.includes(w)) &&
          !["not ok", "failed", "falhou"].some((neg) => stateLower.includes(neg))
        ) {
          matchedIdx = nLevels;
        } else if (qid !== "viability" && ["trivial", "minor", "pequeno", "menor"].some((w) => stateLower.includes(w)) && !hasHeavyKeywords) {
          matchedIdx = 1;
        } else if (qid !== "viability" && (hasHeavyKeywords || ["critical", "critico", "crítico", "fatal", "disaster", "destrutivo", "complex", "complexo", "complejo"].some((w) => stateLower.includes(w)))) {
          matchedIdx = nLevels;
        }

        for (let idx = 0; idx < q.criteria.length; idx++) {
          const levelTokens = (q.criteria[idx] || "").toLowerCase().match(/\w+/g) || [];
          if (levelTokens.some((t) => stateTokens.has(t)) && !(hasExplicitFailure && idx > 0 && ["satisfaction", "rigor"].includes(qid))) {
            matchedIdx = idx + 1;
          }
        }

        answers[qid] = {
          type: "score",
          score: matchedIdx,
          confidence: 0.85,
          legend: q.criteria,
        };
      } else if (q.type === "noul") {
        const inst = q.instructions.toLowerCase();
        let prob = 0.15;

        const negativeSignals = ["abort", "abortar", "fail", "falha", "fallo", "error", "erro", "impossible", "impossivel", "imposible", "fatal", "circular", "deadlock", "broken", "unviable", "inviavel", "inviable", "destrutivo"];
        const positiveSignals = ["pass", "passed", "passou", "pasó", "success", "sucesso", "éxito", "resolved", "resuelto", "valid", "válido", "satisfy", "satisfaz", "satisface", "complete", "completado", "proceed", "linear"];

        const proposedPart = stateLower.includes("proposed next step:") ? stateLower.split("proposed next step:")[1] : stateLower;
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
          "todo", "remaining", "next step", "unfinished", "partial", "in progress",
          "without running tests", "tests not run", "unverified", "haven't run pytest",
          "falta implementar", "pendente", "falta rodar os testes", "sem testar", "need to verify", "step 1 of",
          "to verify", "run pytest", "run cargo test", "run npm test", "need to run",
          "updated file", "edited file", "finished editing", "modified file", "wrote code",
          "atualizei o arquivo", "alterei o arquivo", "terminei de editar", "arquivo alterado"
        ].some((w) => stateLower.includes(w));
        const hasNoProgress = [
          "no progress", "stuck", "same output", "unchanged", "repeated without change",
          "sem progresso", "mesma saída"
        ].some((w) => stateLower.includes(w));

        if (qid === "waiting" || inst.includes("waiting on the user")) {
          prob = isWaitingOnUser ? 0.88 : 0.08;
        } else if (qid === "progress" || inst.includes("last nudge produce real progress")) {
          prob = hasNoProgress ? 0.12 : 0.86;
        } else if (qid === "nudge" || inst.includes("gentle nudge")) {
          if (isWaitingOnUser || hasNoProgress || isDone) {
            prob = 0.10;
          } else if (hasUnfinishedWork) {
            prob = 0.89;
          } else {
            prob = 0.14;
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
        input_tokens: Math.max(10, Math.floor(state.length / 4)),
        output_tokens: 0,
      },
      isMock: true,
      rawResponse: { simulated: true },
    };
  }
}
