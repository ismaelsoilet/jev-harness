// E0.3/E1.1 - payload limits and shadow mode (decide without acting).
import { test } from "node:test";
import * as assert from "node:assert/strict";
import { JevClient, MAX_STATE_CHARS } from "../src/client.js";
import { runCli } from "../src/cli.js";
import { spawnSync } from "node:child_process";
import * as fs from "node:fs";
import * as os from "node:os";
import * as path from "node:path";

test("E0.3 oversized state is rejected before the network", async () => {
  const client = new JevClient({ provider: "typesafe", apiKey: "k" });
  await assert.rejects(
    () => client.systemOne("x".repeat(MAX_STATE_CHARS + 1), { q: { type: "noul", instructions: "x" } } as any),
    /exceeds/
  );
});

test("E1.1 shadow keeps the pipeline unblocked and reports the would-be exit", async () => {
  const normal = await runCli(["test-gate", "--mock", "--sample", "AssertionError: assert 4 == 5"]);
  assert.equal(normal, 1);
  const shadow = await runCli(["test-gate", "--mock", "--shadow", "--sample", "AssertionError: assert 4 == 5"]);
  assert.equal(shadow, 0);
});

test("E1.1 shadow JSON exposes the envelope", async () => {
  const logged: string[] = [];
  const originalLog = console.log;
  console.log = (...args: any[]) => {
    logged.push(args.join(" "));
  };
  try {
    const code = await runCli([
      "test-gate",
      "--mock",
      "--shadow",
      "--json",
      "--sample",
      "AssertionError: assert 4 == 5",
    ]);
    assert.equal(code, 0);
  } finally {
    console.log = originalLog;
  }
  const payload = JSON.parse(logged.join("\n"));
  assert.equal(payload.shadow, true);
  assert.equal(payload.would_exit, 1);
});

test("E1.1 published bin entrypoint exits without a stack trace", () => {
  const bin = path.join(process.cwd(), "bin", "cli.js");
  assert.ok(fs.readFileSync(bin, "utf-8").includes(".catch("), "bin must guard unexpected errors");
  const result = spawnSync(process.execPath, [bin, "test-gate", "--mock", "--shadow", "--sample", "AssertionError: x"], {
    encoding: "utf-8",
  });
  assert.equal(result.status, 0);
});

test("E0.3 exact payload limit is accepted (boundary is inclusive)", async () => {
  const client = new JevClient({ provider: "typesafe", apiKey: "k", maxRetries: 1, retryBaseDelayMs: 0 });
  client.baseUrl = "http://127.0.0.1:9/v1/systemone";
  const resp = await client.systemOne("x".repeat(MAX_STATE_CHARS), {
    q: { type: "noul", instructions: "x" },
  } as any);
  assert.equal(resp.isMock, true); // accepted by the guard, degraded by the dead endpoint
});

function inTempRepo(config: unknown, fn: (dir: string) => void) {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "jev-model-"));
  const originalCwd = process.cwd();
  try {
    fs.writeFileSync(path.join(dir, ".jev.json"), JSON.stringify(config));
    process.chdir(dir);
    fn(dir);
  } finally {
    process.chdir(originalCwd);
    fs.rmSync(dir, { recursive: true, force: true });
  }
}

test("E0.3 pinned model is sent in the request payload with its origin reported", async () => {
  let body: any;
  const originalFetch = globalThis.fetch;
  let client!: JevClient;
  inTempRepo({ model: "jev-1.13.0" }, () => {
    client = new JevClient({ provider: "typesafe", apiKey: "k", maxRetries: 1, retryBaseDelayMs: 0 });
  });
  assert.equal(client.modelSource, ".jev.json");
  assert.equal(client.model, "jev-1.13.0");
  try {
    globalThis.fetch = (async (_url: any, init: any) => {
      body = JSON.parse(init.body);
      return new Response(
        JSON.stringify({
          model: "jev-test",
          answers: { q: { type: "noul", noul: 0.9 } },
          usage: { input_tokens: 1, output_tokens: 1 },
        }),
        { status: 200, headers: { "content-type": "application/json" } }
      );
    }) as any;
    await client.systemOne("state", { q: { type: "noul", instructions: "x" } } as any);
  } finally {
    globalThis.fetch = originalFetch;
  }
  assert.equal(body.model, "jev-1.13.0");
});

test("E0.3 JEV_MODEL env var wins over repo config; explicit option wins over both", () => {
  const originalEnv = process.env.JEV_MODEL;
  try {
    process.env.JEV_MODEL = "jev-1.13.0";
    inTempRepo({ model: "from-repo" }, () => {
      const fromEnv = new JevClient({ provider: "typesafe", apiKey: "k" });
      assert.equal(fromEnv.model, "jev-1.13.0");
      assert.equal(fromEnv.modelSource, "env");
    });
    const fromArg = new JevClient({ provider: "typesafe", apiKey: "k", model: "from-argument" });
    assert.equal(fromArg.model, "from-argument");
    assert.equal(fromArg.modelSource, "argument");
  } finally {
    if (originalEnv === undefined) delete process.env.JEV_MODEL;
    else process.env.JEV_MODEL = originalEnv;
  }
});

test("E0.3 provider default is labelled when nothing pins the model", () => {
  const originalEnv = process.env.JEV_MODEL;
  delete process.env.JEV_MODEL;
  try {
    inTempRepo({}, () => {
      const client = new JevClient({ provider: "opencode", apiKey: "k" });
      assert.equal(client.model, "jev-1.13-free");
      assert.equal(client.modelSource, "provider_default");
    });
  } finally {
    if (originalEnv !== undefined) process.env.JEV_MODEL = originalEnv;
  }
});

test("E0.3 status prints the model and its origin", async () => {
  const logged: string[] = [];
  const originalLog = console.log;
  console.log = (...args: any[]) => {
    logged.push(args.join(" "));
  };
  try {
    const code = await runCli(["status", "--mock"]);
    assert.equal(code, 0);
  } finally {
    console.log = originalLog;
  }
  const output = logged.join("\n");
  assert.match(output, /Model:\s+\S+/);
  assert.match(output, /Model origin:/);
});

test("E1.1 shadow masks a gate/provider failure but never CLI misuse", async () => {
  const huge = "x".repeat(MAX_STATE_CHARS + 1);
  const guarded = await runCli([
    "route",
    "--provider",
    "opencode",
    "--shadow",
    "--fail-closed",
    "--task",
    huge,
  ]);
  assert.equal(guarded, 0, "shadow must not break the pipeline on a provider/payload failure");

  const unguarded = await runCli(["route", "--provider", "opencode", "--fail-closed", "--task", huge]);
  assert.equal(unguarded, 2, "without shadow the same failure is surfaced");

  const misuse = await runCli(["test-gate", "--shadow", "--log", "/definitely/not/here.log"]);
  assert.equal(misuse, 2, "CLI misuse is not a gate outcome and must stay 2");
});
