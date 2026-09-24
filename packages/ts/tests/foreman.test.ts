// Foreman integration parity tests (change `foreman-integration`).
//
// The golden values live in `tests/fixtures/foreman_cases.json`, shared verbatim with the Python
// and Rust suites. Capability matrix: `recovery` is Python-only, so this runtime must always
// return `recovery: null` — a declared divergence, never a silently absent key.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import { readFileSync, mkdtempSync, readdirSync, existsSync } from "node:fs";
import { tmpdir } from "node:os";
import * as path from "node:path";
import { runCli } from "../src/cli.js";
import {
  FOREMAN_COMPANION_CLASS_SOURCE,
  FOREMAN_COMPANION_FILENAME,
  FOREMAN_DEFAULT_OUT_DIR,
  FOREMAN_OPERATOR_README,
  FOREMAN_PRESET_FILENAME,
  FOREMAN_README_FILENAME,
  FOREMAN_RESPONSIBILITY_TOML,
  FOREMAN_SCHEMA_VERSION,
  STAGNANT_EVIDENCE,
  evaluateWorkerHealth,
  extractTestResults,
  findAssertionLine,
} from "../src/foreman.js";

const repoRoot = path.join(process.cwd(), "..", "..");
const fixture = JSON.parse(
  readFileSync(path.join(repoRoot, "tests", "fixtures", "foreman_cases.json"), "utf-8")
);
const readFixture = (name: string) => readFileSync(path.join(repoRoot, "tests", "fixtures", name), "utf-8");

test("triage fixture cases match the shared golden values", async () => {
  for (const testCase of fixture.triage_cases) {
    const records = await extractTestResults(testCase.stdout, testCase.stderr);
    assert.equal(records.length, testCase.expect.records, testCase.name);
    if (records.length === 0) continue;
    const record = records[0];
    assert.equal(record.category, testCase.expect.category, testCase.name);
    assert.equal(record.skipLlm, testCase.expect.skip_llm, testCase.name);
    assert.equal(record.actionRecommendation, testCase.expect.action_recommendation, testCase.name);
    assert.equal(record.assertionSlice, testCase.expect.assertion_slice, testCase.name);
    assert.ok(Math.abs(record.severityScore - testCase.expect.severity_score) < 1e-9, testCase.name);
    assert.ok(Math.abs(record.confidence - testCase.expect.confidence) < 1e-9, testCase.name);
    assert.equal(record.foremanSchemaVersion, FOREMAN_SCHEMA_VERSION);
    // Declared divergence: this runtime never produces a recovery object.
    assert.equal(record.recovery, null, testCase.name);
  }
});

test("health fixture cases match the shared golden values", () => {
  for (const testCase of fixture.health_cases) {
    const verdict = evaluateWorkerHealth(testCase.snapshots, testCase.window);
    assert.equal(verdict.shouldAbort, testCase.expect.should_abort, testCase.name);
    assert.equal(verdict.reason, testCase.expect.reason, testCase.name);
    assert.equal(verdict.evidence.completeSignals, testCase.expect.complete_signals, testCase.name);
    assert.equal(verdict.evidence.insufficientHistory, testCase.expect.insufficient_history, testCase.name);
    assert.equal(verdict.evidence.stagnantOutput, testCase.expect.stagnant_output, testCase.name);
    assert.equal(verdict.evidence.stagnantDiff, testCase.expect.stagnant_diff, testCase.name);
  }
});

test("stagnation reason constant is shared", () => {
  const stagnant = fixture.health_cases.find((c: any) => c.name === "stagnant_output_and_diff");
  assert.equal(evaluateWorkerHealth(stagnant.snapshots, stagnant.window).reason, STAGNANT_EVIDENCE);
});

test("findAssertionLine ports the perception primitive", () => {
  assert.equal(
    findAssertionLine("collected 1 item\nE   ModuleNotFoundError: No module named 'requests'"),
    "E   ModuleNotFoundError: No module named 'requests'"
  );
  assert.equal(findAssertionLine("12 passed in 0.31s"), null);
  assert.equal(findAssertionLine(""), null);
});

test("preset, README and class source are byte-identical to the canonical artifacts", () => {
  assert.equal(FOREMAN_RESPONSIBILITY_TOML, readFixture("foreman_responsibility.toml"));
  assert.equal(FOREMAN_OPERATOR_README, readFixture("foreman_operator_readme.md"));
  assert.equal(
    FOREMAN_COMPANION_CLASS_SOURCE,
    readFileSync(path.join(repoRoot, "src", "jev_harness", "integrations", "foreman_responsibility.py"), "utf-8")
  );
});

test("capability matrix: recovery is declared, never silently absent", async () => {
  // The matrix uses the canonical snake_case names; this runtime exposes camelCase.
  const camelCase = (key: string) => key.replace(/_(\w)/g, (_match, letter: string) => letter.toUpperCase());
  const records = await extractTestResults(fixture.triage_cases[0].stdout, "");
  assert.ok("recovery" in records[0]);
  for (const key of fixture.capability_matrix.typescript) {
    assert.ok(camelCase(key) in records[0], `missing key ${key}`);
  }
  assert.ok(!fixture.capability_matrix.typescript.includes("recovery"));
  assert.ok(fixture.capability_matrix.python.includes("recovery"));
});

test("export foreman writes the three-file bundle and is idempotent", async () => {
  const directory = mkdtempSync(path.join(tmpdir(), "jev-foreman-"));
  const target = path.join(directory, "bundle");
  const readBundle = () =>
    Object.fromEntries(
      readdirSync(target).map((name) => [name, readFileSync(path.join(target, name), "utf-8")])
    );
  assert.equal(await runCli(["export", "foreman", "--out-dir", target]), 0);
  assert.deepEqual(
    Object.keys(readBundle()).sort(),
    [FOREMAN_COMPANION_FILENAME, FOREMAN_PRESET_FILENAME, FOREMAN_README_FILENAME].sort()
  );
  const first = readBundle();
  assert.equal(await runCli(["export", "foreman", "--out-dir", target]), 0);
  assert.deepEqual(readBundle(), first);
  assert.equal(first[FOREMAN_PRESET_FILENAME], readFixture("foreman_responsibility.toml"));
  assert.equal(first[FOREMAN_README_FILENAME], readFixture("foreman_operator_readme.md"));
});

test("export without a target fails with usage", async () => {
  assert.equal(await runCli(["export"]), 2);
});

test("export refuses to write into a .foreman directory (run state)", async () => {
  const directory = mkdtempSync(path.join(tmpdir(), "jev-foreman-guard-"));
  const target = path.join(directory, ".foreman", "responsibilities");
  assert.equal(await runCli(["export", "foreman", "--out-dir", target]), 2);
  assert.equal(existsSync(target), false);
});

test("default export directory is not run state", async () => {
  const directory = mkdtempSync(path.join(tmpdir(), "jev-foreman-default-"));
  const previous = process.cwd();
  process.chdir(directory);
  try {
    assert.equal(await runCli(["export", "foreman"]), 0);
    assert.ok(readdirSync(directory).includes(FOREMAN_DEFAULT_OUT_DIR));
    assert.ok(!path.join(directory, FOREMAN_DEFAULT_OUT_DIR).includes(".foreman"));
  } finally {
    process.chdir(previous);
  }
});
