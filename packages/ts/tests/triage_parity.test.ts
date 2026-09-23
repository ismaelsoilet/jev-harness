// Tri-runtime parity lock covering every gate: the TypeScript offline mock must reach exactly the
// same verdicts as the Python runtime recorded in tests/fixtures/corpus_parity.json.
// The logs themselves stay in tests/corpus (this file only carries the verdicts).
import { test } from "node:test";
import * as assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import * as path from "node:path";
import { JevClient } from "../src/client.js";
import {
  modulateReasoningEffort,
  routeModelTier,
  shouldAbortTrajectory,
  shouldNudgeContinuation,
  triageTestFailure,
  verifyStepCompletion,
} from "../src/gates.js";

const root = path.join(process.cwd(), "..", "..");
const parity = JSON.parse(readFileSync(path.join(root, "tests", "fixtures", "corpus_parity.json"), "utf-8"));
const corpus: Record<string, any[]> = {};
for (const file of ["triage", "abort", "verify", "route", "effort", "nudge"]) {
  corpus[file] = readFileSync(path.join(root, "tests", "corpus", `${file}.jsonl`), "utf-8")
    .split("\n")
    .filter((line) => line.trim())
    .map((line) => JSON.parse(line));
}

const client = new JevClient({ forceMock: true });

async function observe(gate: string, input: any): Promise<Record<string, unknown>> {
  switch (gate) {
    case "triage": {
      const res = await triageTestFailure(input.log, client);
      return { category: res.category, skip_llm: res.skipLlm };
    }
    case "abort": {
      const res = await shouldAbortTrajectory(input.proposed_step, input.history ?? "", client);
      return { should_abort: res.shouldAbort };
    }
    case "verify": {
      const res = await verifyStepCompletion(input.criteria, input.output, client);
      return { is_verified: res.isVerified };
    }
    case "route": {
      const res = await routeModelTier(input.task, client);
      return { selected_tier: res.selectedTier };
    }
    case "effort": {
      const res = await modulateReasoningEffort(input.context, {
        provider: input.provider ?? "openai",
        model: input.model,
        client,
      });
      return { effort: res.effort };
    }
    case "nudge": {
      const res = await shouldNudgeContinuation(input.transcript_tail, { client });
      return { should_nudge: res.shouldNudge, workflow_phase: res.workflowPhase };
    }
    default:
      throw new Error(`unknown gate ${gate}`);
  }
}

test("every corpus case matches the recorded Python verdict for its gate (parity lock)", async () => {
  const mismatches: string[] = [];
  let checked = 0;
  for (const [gate, entries] of Object.entries(corpus)) {
    for (const entry of entries) {
      const expected = parity.cases[entry.id];
      assert.ok(expected, `no recorded verdict for ${entry.id}`);
      assert.equal(expected.gate, gate, `${entry.id} is recorded under ${expected.gate}`);
      const observed = await observe(gate, entry.input);
      checked++;
      for (const [key, want] of Object.entries<any>(expected.observed)) {
        const got = observed[key];
        if (JSON.stringify(got) !== JSON.stringify(want)) {
          mismatches.push(`${entry.id} (${gate}) ${key}: ts=${JSON.stringify(got)} expected=${JSON.stringify(want)}`);
        }
      }
    }
  }
  assert.equal(checked, 160, `the corpus must keep its size (${checked} cases checked)`);
  assert.deepEqual(mismatches, [], `tri-runtime divergence:\n${mismatches.join("\n")}`);
});

test("the injected logs escalate in TypeScript too", async () => {
  const adversarial = corpus.triage.filter((entry: any) => entry.id.startsWith("adv-"));
  assert.ok(adversarial.length >= 8, "the corpus must keep its adversarial cases");
  for (const entry of adversarial) {
    const res = await triageTestFailure(entry.input.log, client);
    assert.equal(res.category, "deep_logic", entry.id);
    assert.equal(res.skipLlm, false, entry.id);
  }
});
