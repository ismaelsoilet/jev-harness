import * as fs from "node:fs";
import * as path from "node:path";
import { fileURLToPath } from "node:url";
import { JevClient, OPENCODE_API_URL } from "./client.js";
import {
  routeModelTier,
  shouldAbortTrajectory,
  triageTestFailure,
  verifyStepCompletion,
} from "./gates.js";

function readInput(valOrPath?: string): string {
  if (valOrPath) {
    if (fs.existsSync(valOrPath) && fs.statSync(valOrPath).isFile()) {
      return fs.readFileSync(valOrPath, "utf-8");
    }
    return valOrPath;
  }
  if (!process.stdin.isTTY) {
    return fs.readFileSync(0, "utf-8");
  }
  return "";
}

function getPackageVersion(): string {
  try {
    const pkgPath = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../package.json");
    if (fs.existsSync(pkgPath)) {
      const data = JSON.parse(fs.readFileSync(pkgPath, "utf-8"));
      if (data.version) return data.version;
    }
  } catch {
    // fallback
  }
  return "0.1.3";
}

export async function runCli(argv: string[] = process.argv.slice(2)): Promise<number> {
  const args = argv;
  const isMock = args.includes("--mock");
  const isJson = args.includes("--json");

  let providerVal: string | undefined;
  const providerEq = args.find((a) => a.startsWith("--provider="));
  if (providerEq) {
    providerVal = providerEq.split("=")[1];
  } else {
    const pIdx = args.findIndex((a) => a === "--provider");
    if (pIdx !== -1) {
      providerVal = args[pIdx + 1];
    }
  }

  // Filter out flags and their argument values to find the subcommand
  const nonCommandIndices = new Set<number>();
  for (let i = 0; i < args.length; i++) {
    if (args[i].startsWith("-")) {
      nonCommandIndices.add(i);
      if (
        (args[i] === "--provider" ||
          args[i] === "--log" ||
          args[i] === "-l" ||
          args[i] === "--sample" ||
          args[i] === "--plan" ||
          args[i] === "-p" ||
          args[i] === "--history" ||
          args[i] === "-H" ||
          args[i] === "--task" ||
          args[i] === "-t" ||
          args[i] === "--criteria" ||
          args[i] === "-c" ||
          args[i] === "--output" ||
          args[i] === "-o") &&
        i + 1 < args.length &&
        !args[i + 1].startsWith("-")
      ) {
        nonCommandIndices.add(i + 1);
        i++;
      }
    }
  }
  const command = args.find((_, idx) => !nonCommandIndices.has(idx));

  const client = new JevClient({ forceMock: isMock });
  if (providerVal) {
    client.provider = providerVal;
    if (providerVal === "opencode") {
      client.baseUrl = OPENCODE_API_URL;
      client.model = "jev-1.13-free";
    }
  }

  if (args.includes("--version") || args.includes("-v") || args.includes("-V")) {
    console.log(`@ismaelsoilet/jev-harness ${getPackageVersion()}`);
    return 0;
  }

  if (!command || command === "help" || args.includes("-h") || args.includes("--help")) {
    console.log(`
Usage: jev-harness <command> [options]

Commands:
  status                                 Show API status & engine mode
  test-gate --log <file_or_string>       Triage test traceback & gate LLM calls
  abort-check --plan <text>              Guard against doom loops and unviable refactors
  route --task <text>                    Select minimal sufficient model tier
  verify --criteria <c> --output <o>     Calibrate criteria verification

Options:
  --mock                                 Force offline heuristic simulation
  --json                                 Output machine-readable JSON
  --provider <typesafe|opencode|...>     Override backend provider
`);
    return 0;
  }

  if (command === "status") {
    console.log("\n=== JEV HARNESS (TS) STATUS ===");
    if (client.isLive) {
      if (client.provider === "opencode") {
        console.log("Provider:    OPENCODE ZEN (Free Tier)");
        console.log(`Endpoint:    ${client.baseUrl}`);
        console.log("Engine Mode: LIVE (OpenCode Zen Free Community Model)");
      } else {
        const masked = client.apiKey && client.apiKey.length > 10 ? client.apiKey.slice(0, 6) + "..." + client.apiKey.slice(-4) : "***";
        console.log(`API Key:     Configured (${masked})`);
        console.log(`Provider:    ${client.provider.toUpperCase()}`);
        console.log(`Endpoint:    ${client.baseUrl}`);
        console.log("Engine Mode: LIVE");
      }
    } else {
      console.log("API Key:     NOT DETECTED");
      console.log("Engine Mode: SIMULATION / MOCK (Heuristic offline mode active)");
    }
    console.log(`Model:       ${client.model}`);
    console.log("===============================\n");
    return 0;
  }

  if (command === "test-gate" || command === "triage") {
    const logIdx = args.findIndex((a) => a === "--log" || a === "-l" || a === "--sample");
    let logVal = logIdx !== -1 ? args[logIdx + 1] : undefined;
    if (!logVal) {
      // Check for positional argument after command
      const cmdIdx = args.indexOf(command);
      if (cmdIdx !== -1 && args[cmdIdx + 1] && !args[cmdIdx + 1].startsWith("-")) {
        logVal = args[cmdIdx + 1];
      }
    }
    const text = readInput(logVal).trim();

    if (!text) {
      console.error("Error: No test failure log provided. Pass --log <file_or_string> or pipe via stdin.");
      return 2;
    }

    const res = await triageTestFailure(text, client);

    if (isJson) {
      console.log(JSON.stringify(res, null, 2));
    } else {
      console.log("\n--- JEV TEST TRIAGE VERDICT (TS) ---");
      console.log(`Category:        ${res.category.toUpperCase()}`);
      console.log(`Confidence:      ${(res.confidence * 100).toFixed(1)}%`);
      console.log(`Skip LLM Call:   ${res.skipLlm ? "YES (Save Tokens!)" : "NO (Dispatch to System 2)"}`);
      console.log(`Severity Score:  ${res.severityScore.toFixed(1)} / 4.0`);
      console.log(`Recommendation:  ${res.actionRecommendation}`);
      if (res.isMock) console.log("Mode:            [SIMULATION/MOCK]");
      console.log("------------------------------------\n");
    }
    return res.skipLlm ? 0 : 1;
  }

  if (command === "abort-check" || command === "abort") {
    const planIdx = args.findIndex((a) => a === "--plan" || a === "-p");
    const histIdx = args.findIndex((a) => a === "--history" || a === "-H");
    let plan = planIdx !== -1 ? args[planIdx + 1] : undefined;
    if (!plan) {
      const cmdIdx = args.indexOf(command);
      if (cmdIdx !== -1 && args[cmdIdx + 1] && !args[cmdIdx + 1].startsWith("-")) {
        plan = args[cmdIdx + 1];
      }
    }
    const history = histIdx !== -1 ? args[histIdx + 1] : "";
    const cleanPlan = (plan ? readInput(plan) : "").trim();

    if (!cleanPlan) {
      console.error("Error: No plan provided. Pass --plan <text>.");
      return 2;
    }

    const res = await shouldAbortTrajectory(cleanPlan, history, client);

    if (isJson) {
      console.log(JSON.stringify(res, null, 2));
    } else {
      console.log("\n--- JEV ABORT GATE VERDICT (TS) ---");
      console.log(`Should Abort:     ${res.shouldAbort ? "YES - STOP & RECONSIDER" : "NO - PROCEED"}`);
      console.log(`Abort Probability: ${(res.abortProbability * 100).toFixed(1)}%`);
      console.log(`Viability Score:   ${res.viabilityScore.toFixed(1)} / 4.0`);
      console.log(`Summary:           ${res.reasoningSummary}`);
      if (res.isMock) console.log("Mode:              [SIMULATION/MOCK]");
      console.log("-----------------------------------\n");
    }
    return res.shouldAbort ? 1 : 0;
  }

  if (command === "route") {
    const taskIdx = args.findIndex((a) => a === "--task" || a === "-t");
    let task = taskIdx !== -1 ? args[taskIdx + 1] : undefined;
    if (!task) {
      const cmdIdx = args.indexOf(command);
      if (cmdIdx !== -1 && args[cmdIdx + 1] && !args[cmdIdx + 1].startsWith("-")) {
        task = args[cmdIdx + 1];
      }
    }
    const cleanTask = (task ? readInput(task) : "").trim();

    if (!cleanTask) {
      console.error("Error: No task description provided. Pass --task <text>.");
      return 2;
    }

    const res = await routeModelTier(cleanTask, client);

    if (isJson) {
      console.log(JSON.stringify(res, null, 2));
    } else {
      console.log("\n--- JEV MODEL ROUTE VERDICT (TS) ---");
      console.log(`Selected Tier:     ${res.selectedTier.toUpperCase()}`);
      console.log(`Confidence:        ${(res.confidence * 100).toFixed(1)}%`);
      console.log(`Recommended Model: ${res.recommendedModel}`);
      console.log(`Rationale:         ${res.rationale}`);
      if (res.isMock) console.log("Mode:              [SIMULATION/MOCK]");
      console.log("------------------------------------\n");
    }
    return 0;
  }

  if (command === "verify") {
    const critIdx = args.findIndex((a) => a === "--criteria" || a === "-c");
    const outIdx = args.findIndex((a) => a === "--output" || a === "-o");
    const criteria = critIdx !== -1 ? args[critIdx + 1] : undefined;
    const output = outIdx !== -1 ? args[outIdx + 1] : undefined;
    const cleanCrit = (criteria ? readInput(criteria) : "").trim();
    const cleanOut = (output ? readInput(output) : "").trim();

    if (!cleanCrit || !cleanOut) {
      console.error("Error: Both --criteria and --output must be provided.");
      return 2;
    }

    const res = await verifyStepCompletion(cleanCrit, cleanOut, client);

    if (isJson) {
      console.log(JSON.stringify(res, null, 2));
    } else {
      console.log("\n--- JEV VERIFICATION VERDICT (TS) ---");
      console.log(`Verified:          ${res.isVerified ? "PASS" : "REWORK NEEDED"}`);
      console.log(`Satisfaction Prob: ${(res.satisfactionProbability * 100).toFixed(1)}%`);
      console.log(`Rigor Score:       ${res.rigorScore.toFixed(1)} / 4.0`);
      if (res.isMock) console.log("Mode:              [SIMULATION/MOCK]");
      console.log("-------------------------------------\n");
    }
    return res.isVerified ? 0 : 1;
  }

  console.error(`Unknown command: ${command}`);
  return 2;
}

if (process.argv[1] && fileURLToPath(import.meta.url) === path.resolve(process.argv[1])) {
  runCli().then((code) => process.exit(code));
}
