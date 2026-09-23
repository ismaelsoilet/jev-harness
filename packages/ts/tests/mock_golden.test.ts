// E3.9 — golden vectors for the offline mock, shared with Python and Rust.
// The fixture is the same file the other runtimes read: any drift in one runtime breaks parity
// here instead of shipping a false claim.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import * as path from "node:path";
import {
  JevClient,
  MOCK_CHOICE_BEST_CONFLICT,
  MOCK_CHOICE_BEST_PEAKED,
  MOCK_SCORE_BEST_PEAKED,
  mockDistribution,
} from "../src/client.js";

const fixture = JSON.parse(
  readFileSync(path.join(process.cwd(), "..", "..", "tests", "fixtures", "mock_golden.json"), "utf-8")
);
const client = new JevClient({ forceMock: true });

function choiceFor(state: string) {
  const answer = (client as any).simulateSystemOne(
    state,
    { category: { type: "choice", instructions: "What is the root failure type in this error trace?", criteria: fixture.choice_criteria } },
    client.model
  ).answers["category"];
  return answer;
}

function nearly(actual: number, expected: number, label: string) {
  assert.ok(Math.abs(actual - expected) < 1e-9, `${label}: ${actual} != ${expected}`);
}

test("E3.9 mock constants match the cross-runtime contract", () => {
  assert.equal(MOCK_CHOICE_BEST_PEAKED, 0.85);
  assert.equal(MOCK_CHOICE_BEST_CONFLICT, 0.55);
  assert.equal(MOCK_SCORE_BEST_PEAKED, 0.8);
});

test("E3.9 peaked choice distribution matches the golden vector", () => {
  const answer = choiceFor(fixture.peaked.state);
  assert.equal(answer.choice, fixture.peaked.expected.choice);
  for (const [key, value] of Object.entries<number>(fixture.peaked.expected.probabilities)) {
    nearly(answer.probabilities[key], value, `peaked ${key}`);
  }
  assert.equal(Object.keys(answer.probabilities).length, Object.keys(fixture.choice_criteria).length);
});

test("E3.9 conflicting signals lower the peak (deterministic escalation)", () => {
  const answer = choiceFor(fixture.conflict.state);
  assert.equal(answer.choice, fixture.conflict.expected.choice);
  for (const [key, value] of Object.entries<number>(fixture.conflict.expected.probabilities)) {
    nearly(answer.probabilities[key], value, `conflict ${key}`);
  }
  nearly(answer.probabilities[answer.choice], MOCK_CHOICE_BEST_CONFLICT, "conflict peak");
});

test("E3.9 distributions sum to one in every vector", () => {
  for (const name of ["peaked", "conflict"] as const) {
    const answer = choiceFor(fixture[name].state);
    const total = Object.values<number>(answer.probabilities).reduce((a, b) => a + b, 0);
    nearly(total, 1.0, `${name} sum`);
  }
});

test("E3.9 score distribution is exposed and matches the golden vector", () => {
  const answer = (client as any).simulateSystemOne(
    fixture.score.state,
    { severity: { type: "score", instructions: "How severe is this failure?", criteria: fixture.score.levels } },
    client.model
  ).answers["severity"];
  nearly(answer.score, fixture.score.expected.score, "score");
  for (const [key, value] of Object.entries<number>(fixture.score.expected.probabilities)) {
    nearly(answer.probabilities[key], value, `score ${key}`);
  }
  nearly(
    Object.values<number>(answer.probabilities).reduce((a, b) => a + b, 0),
    1.0,
    "score sum"
  );
});

test("E3.9 noul stays a scalar and mockDistribution handles degenerate inputs", () => {
  const answer = (client as any).simulateSystemOne(
    fixture.noul.state,
    { skip_llm: { type: "noul", instructions: fixture.noul.instruction } },
    client.model
  ).answers["skip_llm"];
  nearly(answer.noul, fixture.noul.expected.noul, "noul");
  assert.equal(answer.probabilities, undefined, "Noul has no distribution by contract");

  assert.deepEqual(mockDistribution(["only"], "only", 0.85), { only: 1.0 });
  const two = mockDistribution(["a", "b"], "b", 0.5);
  nearly(two.a, 0.5, "two a");
  nearly(two.b, 0.5, "two b");
});
