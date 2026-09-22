import { test, describe } from "node:test";
import * as assert from "node:assert/strict";
import { JevClient } from "../src/client.js";
import {
  modulateReasoningEffort,
  routeModelTier,
  shouldAbortTrajectory,
  triageTestFailure,
  verifyStepCompletion,
} from "../src/gates.js";

describe("Jev System One (TypeScript) Decision Gates", () => {
  const client = new JevClient({ forceMock: true });

  test("triageTestFailure detects missing Python module", async () => {
    const res = await triageTestFailure("ModuleNotFoundError: No module named 'scipy'", client);
    assert.equal(res.category, "env_missing");
    assert.equal(res.skipLlm, true);
    assert.match(res.actionRecommendation, /AUTO-ACTION/);
  });

  test("triageTestFailure detects missing TypeScript module TS2307", async () => {
    const res = await triageTestFailure("src/app.ts: error TS2307: Cannot find module 'axios'", client);
    assert.equal(res.category, "env_missing");
    assert.equal(res.skipLlm, true);
  });

  test("triageTestFailure detects flaky transient network error", async () => {
    const res = await triageTestFailure("ECONNRESET: connection reset by peer with timeout", client);
    assert.equal(res.category, "flaky_transient");
    assert.equal(res.skipLlm, true);
  });

  test("triageTestFailure detects deep logic failure", async () => {
    const res = await triageTestFailure("AssertionError: expected true to be false", client);
    assert.equal(res.category, "deep_logic");
    assert.equal(res.skipLlm, false);
  });

  test("shouldAbortTrajectory triggers abort on circular doomed loops", async () => {
    const res = await shouldAbortTrajectory(
      "Tentar refatorar novamente sem testes",
      "Tentativa 1 falhou com timeout. Tentativa 2 falhou com deadlock circular.",
      client
    );
    assert.equal(res.shouldAbort, true);
    assert.equal(res.abortProbability >= 0.7, true);
  });

  test("shouldAbortTrajectory allows safe progressive steps", async () => {
    const res = await shouldAbortTrajectory("Rodar npm run build para inspecionar", "Compilou OK", client);
    assert.equal(res.shouldAbort, false);
  });

  test("routeModelTier routes simple tasks to deterministic tier", async () => {
    const res = await routeModelTier("Corrigir typo e formatar com prettier", client);
    assert.equal(res.selectedTier, "deterministic");
    assert.match(res.recommendedModel, /0 LLM Tokens/);
  });

  test("routeModelTier routes complex architecture to 2026 frontier models", async () => {
    const res = await routeModelTier("Refactor distributed actor supervision kernel and multi-file deadlock", client);
    assert.equal(res.selectedTier, "heavy_system2");
    assert.match(res.recommendedModel, /Claude Fable 5.1 \/ GPT-6 Astra/);
  });

  test("verifyStepCompletion validates criteria satisfaction", async () => {
    const res = await verifyStepCompletion(
      "Deve passar em todos os testes",
      "Todos os testes passaram com sucesso e 100% de cobertura",
      client
    );
    assert.equal(res.isVerified, true);
    assert.equal(res.needsRework, false);
  });

  test("adversarial: shouldAbortTrajectory respects negated abort intent", async () => {
    const res = await shouldAbortTrajectory(
      "Do NOT abort, proceed with database migration steps",
      "Previous step completed migration script",
      client
    );
    assert.equal(res.shouldAbort, false, "Negated abort statement must NOT trigger abort");
    assert.equal(res.action, "proceed");
  });

  test("adversarial: triageTestFailure classifies AssertionError containing module string as deep_logic", async () => {
    const res = await triageTestFailure(
      "FAILED tests/test_loader.py::test_missing - AssertionError: expected 'No module named foo' to be raised",
      client
    );
    assert.equal(res.category, "deep_logic", "AssertionError must take precedence over substring module names");
    assert.equal(res.skipLlm, false, "Logic failure must NOT skip LLM");
  });

  test("adversarial: routeModelTier prioritizes heavy kernel reasoning over typo", async () => {
    const res = await routeModelTier(
      "Architect enterprise distributed kernel allocator and fix typo in docstring",
      client
    );
    assert.equal(res.selectedTier, "heavy_system2", "Heavy architectural keywords must override typo in routing");
  });

  test("adversarial: Portuguese tracebacks and safe uninformative fallback", async () => {
    const resAssert = await triageTestFailure("Falha de asserção: esperava 10 mas obteve 20", client);
    assert.equal(resAssert.category, "deep_logic");
    assert.equal(resAssert.skipLlm, false);

    const resMod = await triageTestFailure("Módulo não encontrado: lodash", client);
    assert.equal(resMod.category, "env_missing");
    assert.equal(resMod.skipLlm, true);

    const resFallback = await triageTestFailure("xyz123 uninformative random text with no keywords", client);
    assert.equal(resFallback.category, "deep_logic");
    assert.equal(resFallback.skipLlm, false);
  });

  test("modulateReasoningEffort modulates mechanical tasks to low and outputs safe provider dialect", async () => {
    const resLow = await modulateReasoningEffort("git status e diff", { provider: "deepseek", client });
    assert.equal(resLow.effort, "low");
    assert.equal(resLow.provider, "deepseek");
    assert.equal(resLow.providerParams.reasoning_effort, "low");
    assert.equal(resLow.isReasoningSupported, true);

    const resQwen = await modulateReasoningEffort("cat package.json", { provider: "qwen", client });
    assert.equal(resQwen.effort, "low");
    assert.deepEqual(resQwen.providerParams, { enable_thinking: false });

    const resDirect = await modulateReasoningEffort("cat package.json", { provider: "openai", model: "gpt-5.6-luna", client });
    assert.equal(resDirect.isReasoningSupported, false);
    assert.deepEqual(resDirect.providerParams, {});

    const resGpt4o = await modulateReasoningEffort("git status", { provider: "openai", model: "gpt-4o", client });
    assert.equal(resGpt4o.isReasoningSupported, false);
    assert.deepEqual(resGpt4o.providerParams, {});

    const resHaiku = await modulateReasoningEffort("git status", { provider: "anthropic", model: "claude-3-5-haiku", client });
    assert.equal(resHaiku.isReasoningSupported, false);
    assert.deepEqual(resHaiku.providerParams, {});
  });

  test("adversarial: Jest assertion failure with module string is deep_logic", async () => {
    const jestLog = `
FAIL src/plugin.test.ts
  ● Plugin Loader › handles failure gracefully

    expect(received).toBe(expected) // Object.is equality

    Expected: "READY"
    Received: "ModuleNotFoundError: No module named 'foo'"

      18 |     const res = await loader.load();
    > 19 |     expect(res.status).toBe("READY");
`;
    const res = await triageTestFailure(jestLog, client);
    assert.equal(res.category, "deep_logic");
    assert.equal(res.skipLlm, false);
  });

  test("adversarial: forward progress is not falsely aborted", async () => {
    const res = await shouldAbortTrajectory(
      "Implement the missing function to fix the error",
      "Previous attempt had a compilation error",
      client
    );
    assert.equal(res.shouldAbort, false);
    assert.equal(res.abortProbability < 0.5, true);
  });

  test("adversarial: high-context prompt cache advisory", async () => {
    const res = await modulateReasoningEffort("git status", {
      provider: "openai",
      model: "o3-mini",
      sessionContextTokens: 45000,
      client,
    });
    assert.equal(res.isReasoningSupported, true);
    assert.match(res.cacheSafeRecommendation, /HIGH CACHE RISK/);
  });

  test("openrouter provider resolves correct baseUrl and default model", () => {
    const openrouterClient = new JevClient({ provider: "openrouter", apiKey: "test-key" });
    assert.equal(openrouterClient.baseUrl, "https://openrouter.ai/api/v1/chat/completions");
    assert.equal(openrouterClient.model, "google/gemini-2.5-flash");
    assert.equal(openrouterClient.isLive, true);
  });

  test("adversarial: infinite loop timeout is classified as deep_logic and does NOT skip LLM", async () => {
    const log = "TIMEOUT: Test suite timed out after 30000ms. Possible infinite loop in worker thread while acquiring lock.";
    const res = await triageTestFailure(log, client);
    assert.equal(res.category, "deep_logic", "Infinite loops and deadlocks must be deep_logic");
    assert.equal(res.skipLlm, false, "Must never skip LLM on infinite loop or deadlock");
  });

  test("adversarial: direct single-pass models safeguards expanded", async () => {
    const directModels = ["gpt-4", "gpt-4-turbo", "claude-3-5-sonnet", "claude-3-haiku", "deepseek-chat", "qwen-2.5-72b", "codestral", "mistral"];
    for (const m of directModels) {
      const res = await modulateReasoningEffort("Fix simple bug", { provider: "openai", model: m, client });
      assert.equal(res.isReasoningSupported, false, `Model ${m} must be recognized as direct single-pass`);
      assert.deepEqual(res.providerParams, {}, `Model ${m} must receive empty provider params`);
    }
  });

  test("adversarial: modulateReasoningEffort safely handles long context with head-tail truncation", async () => {
    const head = "Architectural review needed for distributed system.\n";
    const middle = "A".repeat(5000);
    const tail = "\nImmediate task: fix concurrency deadlock in transaction coordinator.";
    const full = head + middle + tail;
    const res = await modulateReasoningEffort(full, { provider: "openai", client });
    assert.equal(res.effort, "high", "Must detect high complexity from head/tail even after truncation");
  });
});

