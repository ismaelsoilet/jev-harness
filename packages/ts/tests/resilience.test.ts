// E0.2 - provider resilience: retry with backoff, Retry-After, fail-open/fail-closed.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import { JevClient, MAX_STATE_CHARS, redactSecrets } from "../src/client.js";
import { runCli } from "../src/cli.js";

const SUCCESS = {
  model: "jev-test",
  answers: { q: { type: "noul", noul: 0.9 } },
  usage: { input_tokens: 1, output_tokens: 1 },
};

function client(opts: any = {}) {
  return new JevClient({
    forceMock: false,
    provider: "typesafe",
    apiKey: "test-key",
    maxRetries: 3,
    retryBaseDelayMs: 0,
    ...opts,
  });
}

async function withFetch(fake: any, fn: () => Promise<void>) {
  const original = globalThis.fetch;
  globalThis.fetch = fake as any;
  try {
    await fn();
  } finally {
    globalThis.fetch = original;
  }
}

test("E0.2 429 then success retries and stays live", async () => {
  let calls = 0;
  await withFetch(
    async () => {
      calls++;
      if (calls === 1) return new Response("", { status: 429, headers: { "retry-after": "0" } });
      return new Response(JSON.stringify(SUCCESS), { status: 200, headers: { "content-type": "application/json" } });
    },
    async () => {
      const resp = await client().systemOne("state", { q: { type: "noul", instructions: "x" } } as any);
      assert.equal(calls, 2);
      assert.equal(resp.isMock, false);
      assert.equal(resp.degradedReason, undefined);
    }
  );
});

test("E0.2 repeated 429 falls back and is marked", async () => {
  let calls = 0;
  await withFetch(
    async () => {
      calls++;
      return new Response("", { status: 429 });
    },
    async () => {
      const resp = await client().systemOne("state", { q: { type: "noul", instructions: "x" } } as any);
      assert.equal(calls, 3);
      assert.equal(resp.isMock, true);
      assert.equal(resp.degradedReason, "http_429");
    }
  );
});

test("E0.2 503 falls back by default and marks the reason", async () => {
  await withFetch(
    async () => new Response("", { status: 503 }),
    async () => {
      const resp = await client().systemOne("state", { q: { type: "noul", instructions: "x" } } as any);
      assert.equal(resp.isMock, true);
      assert.equal(resp.degradedReason, "http_503");
    }
  );
});

test("E0.2 network error falls back as connection", async () => {
  await withFetch(
    async () => {
      throw new TypeError("fetch failed");
    },
    async () => {
      const resp = await client().systemOne("state", { q: { type: "noul", instructions: "x" } } as any);
      assert.equal(resp.isMock, true);
      assert.equal(resp.degradedReason, "connection");
    }
  );
});

test("E0.2 timeout (AbortError) falls back as timeout", async () => {
  await withFetch(
    async () => {
      throw Object.assign(new Error("aborted"), { name: "AbortError" });
    },
    async () => {
      const resp = await client().systemOne("state", { q: { type: "noul", instructions: "x" } } as any);
      assert.equal(resp.isMock, true);
      assert.equal(resp.degradedReason, "timeout");
    }
  );
});

test("E0.2 401 falls back immediately without retry", async () => {
  let calls = 0;
  await withFetch(
    async () => {
      calls++;
      return new Response("", { status: 401 });
    },
    async () => {
      const resp = await client().systemOne("state", { q: { type: "noul", instructions: "x" } } as any);
      assert.equal(calls, 1);
      assert.equal(resp.degradedReason, "auth_401");
    }
  );
});

test("E0.2 fail-closed rejects instead of degrading", async () => {
  await withFetch(
    async () => new Response("", { status: 500 }),
    async () => {
      await assert.rejects(
        () => client({ failOpen: false }).systemOne("state", { q: { type: "noul", instructions: "x" } } as any),
        /HTTP 500/
      );
    }
  );
});

test("E0.2 invalid JSON body degrades marked (invalid_response)", async () => {
  await withFetch(
    async () => new Response("<html>gateway</html>", { status: 200 }),
    async () => {
      const c = client({ maxRetries: 1 });
      const resp = await c.systemOne("state", { q: { type: "noul", instructions: "x" } } as any);
      assert.equal(resp.isMock, true);
      assert.equal(resp.degradedReason, "invalid_response");
    }
  );
});

test("E0.2 fail-closed rejects on 401 without retry", async () => {
  let calls = 0;
  await withFetch(
    async () => {
      calls++;
      return new Response("", { status: 401 });
    },
    async () => {
      await assert.rejects(
        () => client({ failOpen: false }).systemOne("state", { q: { type: "noul", instructions: "x" } } as any),
        /auth failed/
      );
      assert.equal(calls, 1);
    }
  );
});

test("E0.3 unicode state counts code points, not bytes", async () => {
  const c = new JevClient({
    provider: "typesafe",
    apiKey: "k",
    baseUrl: "http://127.0.0.1:9/v1/systemone",
    maxRetries: 1,
    retryBaseDelayMs: 0,
  });
  const resp = await c.systemOne("é".repeat(MAX_STATE_CHARS - 1), { q: { type: "noul", instructions: "x" } } as any);
  assert.equal(resp.isMock, true); // accepted by the guard, degraded by the dead endpoint
});

test("E0.2 retryDelayMs honors Retry-After and caps backoff", () => {
  const c = client({ retryBaseDelayMs: 500 });
  assert.equal(c.retryDelayMs(1, "2"), 2000);
  assert.equal(c.retryDelayMs(1, "1.5"), 1500); // fractional seconds, as in Python/Rust
  assert.equal(c.retryDelayMs(1, "not-a-number"), 500);
  assert.equal(c.retryDelayMs(5), 5000); // capped
});

const MALFORMED = JSON.stringify({
  model: "jev-test",
  answers: { severity: { type: "score", score: "N/A", confidence: 0.5 } },
});

test("E0.2 malformed 200 payload degrades and is marked (never a silent NaN)", async () => {
  let calls = 0;
  await withFetch(
    async () => {
      calls++;
      return new Response(MALFORMED, { status: 200, headers: { "content-type": "application/json" } });
    },
    async () => {
      const resp = await client({ maxRetries: 3 }).systemOne("state", {
        q: { type: "noul", instructions: "x" },
      } as any);
      assert.equal(calls, 3); // retried like a bad status, then degraded
      assert.equal(resp.isMock, true);
      assert.equal(resp.degradedReason, "invalid_response");
      assert.equal(Number.isNaN((resp.answers as any).severity?.score ?? 0), false);
    }
  );
});

test("E0.2 malformed payload rejects under failOpen=false", async () => {
  await withFetch(
    async () => new Response(MALFORMED, { status: 200, headers: { "content-type": "application/json" } }),
    async () => {
      await assert.rejects(
        () =>
          client({ failOpen: false, maxRetries: 1 }).systemOne("state", {
            q: { type: "noul", instructions: "x" },
          } as any),
        /malformed response/
      );
    }
  );
});

test("E0.2 empty or non-object answers are treated as malformed", async () => {
  for (const body of [JSON.stringify({ model: "x", answers: [] }), JSON.stringify({ model: "x", answers: {} })]) {
    await withFetch(
      async () => new Response(body, { status: 200, headers: { "content-type": "application/json" } }),
      async () => {
        const resp = await client({ maxRetries: 1 }).systemOne("state", {
          q: { type: "noul", instructions: "x" },
        } as any);
        assert.equal(resp.isMock, true, body);
        assert.equal(resp.degradedReason, "invalid_response", body);
      }
    );
  }
});

test("E0.2 an uninterpretable answer beside a valid one is malformed, not dropped", async () => {
  const bodies = [
    JSON.stringify({
      model: "jev-test",
      answers: {
        category: { type: "choice", choice: "env_missing", confidence: 0.98 },
        skip_llm: { type: "noul", noul: 0.9 },
        severity: { type: "score_v2", value: 3 },
      },
    }),
    JSON.stringify({ model: "x", answers: { q: { type: "score" } } }),
    JSON.stringify({ model: "x", answers: { q: { type: "score", score: "1.0", confidence: 0.9 } } }),
    JSON.stringify({ model: "x", answers: { q: { score: 1.0, confidence: 0.5 } } }),
    JSON.stringify({ model: "x", answers: { q: "boom" } }),
  ];
  for (const body of bodies) {
    await withFetch(
      async () => new Response(body, { status: 200, headers: { "content-type": "application/json" } }),
      async () => {
        const resp = await client({ maxRetries: 1 }).systemOne("state", {
          q: { type: "noul", instructions: "x" },
        } as any);
        assert.equal(resp.isMock, true, body);
        assert.equal(resp.degradedReason, "invalid_response", body);
      }
    );
  }
});

test("E0.2 the CLI reports the degradation in json and in human output", async () => {
  const logged: string[] = [];
  const originalLog = console.log;
  const originalKey = process.env.TYPESAFE_API_KEY;
  console.log = (...args: any[]) => {
    logged.push(args.join(" "));
  };
  process.env.TYPESAFE_API_KEY = "test-key";
  try {
    await withFetch(
      async () => new Response(MALFORMED, { status: 200, headers: { "content-type": "application/json" } }),
      async () => {
        await runCli(["test-gate", "--json", "--sample", "AssertionError: assert 1 == 2"]);
        const payload = JSON.parse(logged.join("\n"));
        assert.equal(payload.degraded_reason, "invalid_response");
        assert.equal(payload.is_mock, true);
      }
    );
  } finally {
    console.log = originalLog;
    if (originalKey === undefined) delete process.env.TYPESAFE_API_KEY;
    else process.env.TYPESAFE_API_KEY = originalKey;
  }
});

test("E3.5 credential-shaped material is masked before the state leaves the process", () => {
  const secrets: Record<string, string> = {
    api_key_pair: 'api_key = "vck_live_9f8a7b6c5d4e3f2a1b0c"',
    bearer_jwt: "Authorization: Bearer eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxIn0.abcdefghijklmnop",
    github: "token ghp_" + "A".repeat(24),
    aws: "AKIAIOSFODNN7EXAMPLE",
    db_url: "postgres://admin:hunter2@db.internal:5432/app",
    private_key: "-----BEGIN RSA PRIVATE KEY-----\nMIIEowIBAAKCAQEA\n-----END RSA PRIVATE KEY-----",
  };
  const fragments = ["vck_live_9f8a7b6c5d4e3f2a1b0c", "ghp_" + "A".repeat(24), "AKIAIOSFODNN7EXAMPLE", "hunter2", "MIIEowIBAAKCAQEA"];
  for (const [name, secret] of Object.entries(secrets)) {
    const cleaned = redactSecrets(secret);
    assert.ok(cleaned.includes("[REDACTED"), name);
    for (const fragment of fragments) {
      assert.equal(cleaned.includes(fragment), false, `${name} leaked ${fragment}`);
    }
  }
  assert.equal(redactSecrets("AssertionError: assert 4 == 5"), "AssertionError: assert 4 == 5");
});
