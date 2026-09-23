/**
 * Repository-local configuration loader for `.jev.json` (zero runtime dependencies).
 *
 * Walks up from the current working directory (max 4 levels), merges the file over
 * safe defaults, and caches the parsed result by file fingerprint so the semantic
 * gates keep their sub-millisecond latency contract.
 *
 * Honored keys:
 *   - model                 (string) -> overrides the provider default model
 *   - skip_llm_threshold    (number) -> triage gate confidence threshold
 *   - abort_threshold       (number) -> trajectory abort gate threshold
 *   - shadow                (boolean)-> decide and report, but never change the exit code
 *
 * Credential keys (`api_key`, `provider`) are resolved by `JevClient.resolveCredentials`.
 */

import * as fs from "node:fs";
import * as path from "node:path";

export const DEFAULT_SKIP_LLM_THRESHOLD = 0.65;
export const DEFAULT_ABORT_THRESHOLD = 0.7;

export interface RepoConfig {
  model: string | null;
  /** Decide and report, but never change the exit code. */
  shadow: boolean;
  skipLlmThreshold: number;
  abortThreshold: number;
}

interface RepoConfigCache {
  fingerprint: string;
  config: RepoConfig;
}

let configCache: RepoConfigCache | null = null;

export function findRepoConfigPath(): string | null {
  let current = process.cwd();
  for (let i = 0; i < 4; i++) {
    const candidate = path.join(current, ".jev.json");
    try {
      if (fs.statSync(candidate).isFile()) return candidate;
    } catch {
      // keep walking up
    }
    const parent = path.dirname(current);
    if (parent === current) break;
    current = parent;
  }
  return null;
}

function clampProbability(value: number): number {
  return Math.min(1.0, Math.max(0.0, value));
}

/**
 * Loads `.jev.json` merged over defaults. Never throws: a corrupted or
 * unreadable config degrades to defaults so gates and CI never break.
 */
export function loadRepoConfig(): RepoConfig {
  const defaults: RepoConfig = {
    model: null,
    shadow: false,
    skipLlmThreshold: DEFAULT_SKIP_LLM_THRESHOLD,
    abortThreshold: DEFAULT_ABORT_THRESHOLD,
  };

  const configPath = findRepoConfigPath();
  if (!configPath) return defaults;

  let fingerprint: string;
  try {
    const stat = fs.statSync(configPath);
    fingerprint = `${configPath}:${stat.mtimeMs}:${stat.size}`;
  } catch {
    return defaults;
  }

  if (configCache && configCache.fingerprint === fingerprint) {
    return { ...configCache.config };
  }

  const config: RepoConfig = { ...defaults };
  try {
    const data = JSON.parse(fs.readFileSync(configPath, "utf-8"));
    if (data && typeof data === "object") {
      if (typeof data.model === "string" && data.model.trim()) {
        config.model = data.model.trim();
      }
      if (typeof data.shadow === "boolean") {
        config.shadow = data.shadow;
      }
      if (typeof data.skip_llm_threshold === "number" && Number.isFinite(data.skip_llm_threshold)) {
        config.skipLlmThreshold = clampProbability(data.skip_llm_threshold);
      }
      if (typeof data.abort_threshold === "number" && Number.isFinite(data.abort_threshold)) {
        config.abortThreshold = clampProbability(data.abort_threshold);
      }
    }
  } catch {
    // A corrupted config must never break the gates.
  }

  configCache = { fingerprint, config: { ...config } };
  return config;
}
