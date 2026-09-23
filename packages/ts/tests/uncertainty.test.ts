// E3.1 — the uncertainty math must be identical in Python, TypeScript and Rust.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import * as path from "node:path";
import { buildUncertainty, distributionShape, LOW_CONFIDENCE_THRESHOLD, normalizeLevelKeys, validateQuestionOptions } from "../src/uncertainty.js";

const fixture = JSON.parse(
  readFileSync(path.join(process.cwd(), "..", "..", "tests", "fixtures", "uncertainty_golden.json"), "utf-8")
);

function nearly(actual: number | null, expected: number | null, label: string) {
  if (expected === null) {
    assert.equal(actual, null, label);
    return;
  }
  assert.ok(actual !== null && Math.abs(actual - expected) < 1e-8, `${label}: ${actual} != ${expected}`);
}

test("E3.1 shape metrics match the golden vectors", () => {
  for (const [name, vector] of Object.entries<any>(fixture.vectors)) {
    const shape = distributionShape(vector.probabilities);
    assert.equal(shape.levels, vector.shape.levels, name);
    nearly(shape.margin, vector.shape.margin, `${name} margin`);
    nearly(shape.normalized_entropy, vector.shape.normalized_entropy, `${name} entropy`);
  }
});

test("E3.1 escalation precedence matches the golden vectors", () => {
  for (const [key, entry] of Object.entries<any>(fixture.escalation)) {
    const result = buildUncertainty(entry.probabilities, entry.confidence, entry.category);
    assert.equal(result.escalate_to_system2, entry.expected.escalate_to_system2, key);
    nearly(result.margin, entry.expected.margin, `${key} margin`);
    nearly(result.normalized_entropy, entry.expected.normalized_entropy, `${key} entropy`);
    nearly(result.confidence, entry.expected.confidence, `${key} confidence`);
  }
});

test("E3.1 guards: zeros, single level, both key conventions", () => {
  const withZeros = distributionShape({ "0": 0.7, "1": 0.3, "2": 0 });
  assert.equal(withZeros.levels, 2);
  nearly(withZeros.margin, 0.4, "zeros margin");
  assert.equal(distributionShape({ "1": 1 }).normalized_entropy, null);
  assert.equal(distributionShape(undefined).margin, null);

  const zeroBased = normalizeLevelKeys({ "0": 0.5, "1": 0.5 });
  const oneBased = normalizeLevelKeys({ "1": 0.5, "2": 0.5 });
  assert.deepEqual([...zeroBased.keys()], [...oneBased.keys()]);
  assert.equal(LOW_CONFIDENCE_THRESHOLD, 0.65);
  assert.equal(buildUncertainty(null, 0.64, "route").escalate_to_system2, true);
  assert.equal(buildUncertainty(null, 0.66, "route").escalate_to_system2, false);
});

test("E3.1 a single-option question is rejected", () => {
  assert.throws(() => validateQuestionOptions(["only"]), /at least two options/);
  assert.doesNotThrow(() => validateQuestionOptions(["a", "b"]));
});
