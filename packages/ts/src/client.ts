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

export const TYPESAFE_API_URL = "https://api.typesafe.ai/v1/systemone";
export const OPENCODE_API_URL = "https://opencode.ai/zen/v1/systemone";
export const DEFAULT_MODEL = "jev-latest";
export const DEFAULT_USER_AGENT = "Mozilla/5.0 (compatible; JevHarness/0.1.4; +https://github.com/ismaelsoilet/jev-harness)";

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
    this.provider = provider;

    if (options.baseUrl) {
      this.baseUrl = options.baseUrl;
    } else if (this.provider === "opencode") {
      this.baseUrl = OPENCODE_API_URL;
    } else {
      this.baseUrl = TYPESAFE_API_URL;
    }

    if (options.model) {
      this.model = options.model;
    } else if (this.provider === "opencode") {
      this.model = "jev-1.13-free";
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
      if (process.env.JEV_PROVIDER === "opencode") return { key: process.env.OPENCODE_API_KEY, provider: "opencode" };
      if (process.env.TYPESAFE_API_KEY) return { key: process.env.TYPESAFE_API_KEY, provider: "typesafe" };
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

      // 3. User global config (~/.config/jev/credentials.env)
      try {
        const home = os.homedir();
        const globalCreds = path.join(home, ".config", "jev", "credentials.env");
        if (fs.existsSync(globalCreds)) {
          const lines = fs.readFileSync(globalCreds, "utf-8").split("\n");
          for (const raw of lines) {
            const line = raw.trim();
            if (line.startsWith("JEV_PROVIDER=") && line.split("=", 2)[1].replace(/['"]/g, "").trim() === "opencode") return { key: undefined, provider: "opencode" };
            if (line.startsWith("TYPESAFE_API_KEY=")) return { key: line.split("=", 2)[1].replace(/['"]/g, "").trim(), provider: "typesafe" };
            if (line.startsWith("OPENCODE_API_KEY=")) return { key: line.split("=", 2)[1].replace(/['"]/g, "").trim(), provider: "opencode" };
            if (line.startsWith("OPENROUTER_API_KEY=")) return { key: line.split("=", 2)[1].replace(/['"]/g, "").trim(), provider: "openrouter" };
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

    const payload = {
      model: chosenModel,
      state: stateStr,
      questions,
    };

    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), this.timeoutMs);

    try {
      const headers: Record<string, string> = {
        "Content-Type": "application/json",
        "User-Agent": DEFAULT_USER_AGENT,
      };
      if (this.apiKey) {
        headers["Authorization"] = `Bearer ${this.apiKey}`;
      }

      const resp = await fetch(this.baseUrl, {
        method: "POST",
        headers,
        body: JSON.stringify(payload),
        signal: controller.signal,
      });

      if (!resp.ok) {
        const errText = await resp.text();
        const providerName = this.provider === "opencode" ? "OpenCode Zen" : "TypeSafe";
        throw new Error(`${providerName} API HTTP ${resp.status}: ${errText}`);
      }

      const data = await resp.json();
      return this.parseResponse(data, chosenModel, false);
    } catch (err: any) {
      if (err.name === "AbortError") {
        const providerName = this.provider === "opencode" ? "OpenCode Zen" : "TypeSafe";
        throw new Error(`${providerName} API request timed out after ${this.timeoutMs}ms`);
      }
      throw err;
    } finally {
      clearTimeout(timeoutId);
    }
  }

  private parseResponse(data: any, model: string, isMock: boolean): JevResponse {
    const answers: Record<string, Answer> = {};
    const rawAnswers = data.answers || {};

    for (const [qid, ans] of Object.entries<any>(rawAnswers)) {
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

    const usage = data.usage || {
      input_tokens: Math.max(10, Math.floor(String(data.state || "").length / 4)),
      output_tokens: 0,
    };

    return {
      model: data.model || model,
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

    const isExplicitAssertion = /(?:assertionerror|assert\s+)/i.test(stateLower);
    const hasHeavyKeywords = /(?:kernel|distributed|architecture|refactor|concurrency|deadlock|multi-file|consensus)/i.test(stateLower);
    const isNegatedAbort = /\b(?:not|do\s+not|don't|não|nao|never|sem|evitar|avoid)\s+(?:\w+\s+){0,3}(?:abort|abortar|stop|parar|falhar|fail|deadlock|circular|dead\s*end)/i.test(stateLower);

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

          if (
            opt === "deep_logic" &&
            [
              "assertionerror", "assert ", "panicked at", "panic:", "panic",
              "deadlock", "goroutines are asleep", "segmentation fault",
              "nullpointerexception", "nil pointer dereference", "index out of bounds",
              "falha de asserção", "asserção", "erro de lógica"
            ].some((k) => stateLower.includes(k))
          ) {
            matchScore += isExplicitAssertion ? 14 : 8;
          } else if (
            opt === "env_missing" &&
            [
              "modulenotfounderror", "no module named", "not found", "importerror",
              "cannot find module", "err_module_not_found", "ts2307", "cannot find crate",
              "can't find crate", "find crate", "e0463", "cannot find package", "no required module provides package",
              "módulo não encontrado", "nenhum módulo chamado", "pacote não encontrado"
            ].some((k) => stateLower.includes(k))
          ) {
            matchScore += isExplicitAssertion ? 4 : 7;
          } else if (
            opt === "flaky_transient" &&
            [
              "connectionreset", "timeout", "timed out", "econnreset", "econnrefused",
              "etimedout", "socket hang up", "gateway timeout", "503 service unavailable",
              "tempo limite", "tempo limite esgotado", "conexão recusada"
            ].some((k) => stateLower.includes(k))
          ) {
            matchScore += 7;
          } else if (
            opt === "syntax_trivial" &&
            [
              "syntaxerror", "indentationerror", "expected ';'", "ts1005", "missing bracket",
              "erro de sintaxe", "sintaxe inválida", "indentação inesperada"
            ].some((k) => stateLower.includes(k))
          ) {
            matchScore += 6;
          } else if (
            opt === "deterministic" &&
            ["typo", "format", "black", "prettier", "eslint", "lint", "bash", "regex", "script", "renomear"].some((k) => stateLower.includes(k))
          ) {
            matchScore += hasHeavyKeywords ? 2 : 7;
          } else if (opt === "heavy_system2" && hasHeavyKeywords) {
            matchScore += 16;
          } else if (opt === "abort_and_ask") {
            if (!isNegatedAbort && ["repeat", "circular", "deadlock", "same", "tentar novamente", "mesma", "abort"].some((k) => stateLower.includes(k))) {
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
        let matchedIdx = 2;

        if (
          isNegatedAbort ||
          ["satisfy", "satisfaz", "atende", "passed", "passou", "sucesso", "pass", "success", "excellent", "exhaustively", "complete", "concluido", "proceed"].some((w) => stateLower.includes(w))
        ) {
          matchedIdx = nLevels;
        } else if (["trivial", "minor", "pequeno"].some((w) => stateLower.includes(w)) && !hasHeavyKeywords) {
          matchedIdx = 1;
        } else if (hasHeavyKeywords || ["critical", "critico", "fatal", "disaster", "destrutivo", "complex"].some((w) => stateLower.includes(w))) {
          matchedIdx = nLevels;
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

        const negativeSignals = ["abort", "abortar", "fail", "falha", "error", "erro", "impossible", "impossivel", "fatal", "circular", "deadlock", "broken", "unviable", "destrutivo"];
        const positiveSignals = ["pass", "passed", "passou", "success", "sucesso", "resolved", "valid", "satisfy", "complete", "proceed", "linear"];

        if (isNegatedAbort && ["abort", "dead", "unviable", "destructive"].some((w) => inst.includes(w))) {
          prob = 0.08;
        } else if (["abort", "dead", "unviable", "destructive", "dead end", "circular"].some((w) => inst.includes(w))) {
          if (negativeSignals.some((w) => stateLower.includes(w))) {
            prob = 0.88;
          }
        } else if (inst.includes("deterministically") || inst.includes("skip")) {
          if (
            ["modulenotfounderror", "no module named", "pip install", "npm install", "cannot find module"].some((w) => stateLower.includes(w)) &&
            !isExplicitAssertion
          ) {
            prob = 0.95;
          } else if (isExplicitAssertion || stateLower.includes("assertionerror") || stateLower.includes("panicked")) {
            prob = 0.05;
          } else {
            prob = 0.20;
          }
        }
        if (positiveSignals.some((w) => stateLower.includes(w))) {
          if (["pass", "valid", "satisfy", "complete"].some((w) => inst.includes(w))) {
            prob = 0.92;
          } else if (["abort", "dead", "unviable"].some((w) => inst.includes(w))) {
            prob = 0.08;
          }
        }
        if (
          ["modulenotfounderror", "no module named", "pip install", "npm install", "cannot find module"].some((w) => stateLower.includes(w)) &&
          !isExplicitAssertion
        ) {
          if (inst.includes("deterministically") || inst.includes("skip")) {
            prob = 0.95;
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
