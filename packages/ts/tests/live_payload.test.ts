// E0.1 - recorded live System One payload parity (Score answers must parse).
import { test } from "node:test";
import * as assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import * as path from "node:path";
import { JevClient } from "../src/client.js";

const fixture = JSON.parse(
  readFileSync(path.join(process.cwd(), "..", "..", "tests", "fixtures", "systemone_live_score.json"), "utf-8")
);

test("E0.1 live score payload parses with probabilities and map legend", () => {
  const client = new JevClient({ forceMock: true });
  const resp: any = (client as any).parseResponse(fixture, "jev-test", false);
  const severity = resp.answers["severity"];
  assert.equal(severity.type, "score");
  assert.ok(Math.abs(severity.score - 1.76) < 1e-9, `score=${severity.score}`);
  assert.ok(Math.abs(severity.probabilities["1"] - 0.44) < 1e-9);
  assert.equal(typeof severity.legend, "object");
  const viability = resp.answers["viability"];
  assert.ok(Math.abs(viability.score - 2.11) < 1e-9);
  const category = resp.answers["category"];
  assert.equal(category.choice, "env_missing");
  assert.ok(Math.abs(category.confidence - 0.98) < 1e-9);
});
