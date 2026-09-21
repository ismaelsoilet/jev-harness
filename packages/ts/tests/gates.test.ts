import { test, describe } from "node:test";
import * as assert from "node:assert/strict";
import { JevClient } from "../src/client.js";
import {
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
});
