use crate::{
    client::{JevClient, COMMANDCODE_API_URL},
    gates::{
        modulate_reasoning_effort_full, route_model_tier, should_abort_trajectory,
        should_nudge_continuation, triage_test_failure, verify_step_completion,
    },
};
use clap::{Parser, Subcommand};
use std::fs;
use std::io::{self, IsTerminal, Read};
use std::path::{Path, PathBuf};
use std::process;

/// Shadow mode never changes the caller's pipeline: it reports the would-be exit code.
pub fn shadow_exit(shadow: bool, code: i32) -> i32 {
    if shadow {
        eprintln!("[SHADOW] would exit {} - no action taken.", code);
        0
    } else {
        code
    }
}

/// Shadow mode never breaks the caller's pipeline: report the would-be code and exit 0.
/// CLI misuse (missing input, bad flag) keeps exiting 2 — it is not a gate outcome.
pub fn exit_gate_error(shadow: bool, message: &str) -> ! {
    eprintln!("{}", message);
    process::exit(shadow_exit(shadow, 2));
}

/// `[SIMULATION/MOCK]`, naming the degradation when a provider failure caused it (E0.2).
pub fn mock_mode_label(degraded_reason: &str) -> String {
    if degraded_reason.is_empty() {
        "[SIMULATION/MOCK]".to_string()
    } else {
        format!("[SIMULATION/MOCK - degraded: {}]", degraded_reason)
    }
}

/// Ensures `.jev/` is git-ignored in the project (E3.8): local state must never be committed.
/// Returns the entry when it was added.
pub fn ensure_state_ignored(cwd: &std::path::Path) -> Option<&'static str> {
    let gitignore = cwd.join(".gitignore");
    let entry = ".jev/";
    let existing = fs::read_to_string(&gitignore).unwrap_or_default();
    let ignored = [".jev/", ".jev", "/.jev/", "/.jev"];
    if existing.lines().any(|line| ignored.contains(&line.trim())) {
        return None;
    }
    let separator = if existing.is_empty() || existing.ends_with('\n') {
        ""
    } else {
        "\n"
    };
    let header = if existing.is_empty() {
        "# Added by jev-harness: local decision state (sessions, receipts, cache)\n"
    } else {
        ""
    };
    if fs::write(
        &gitignore,
        format!("{}{}{}{}", existing, separator, header, entry),
    )
    .is_err()
    {
        return None;
    }
    Some(entry)
}

/// Human label for where the effective model came from (E0.3).
pub fn model_origin_label(source: &str) -> String {
    match source {
        "argument" => "explicit argument".to_string(),
        "env" => "JEV_MODEL environment variable".to_string(),
        ".jev.json" => "repository .jev.json".to_string(),
        other => {
            if other == "provider_default" {
                "provider default".to_string()
            } else {
                other.to_string()
            }
        }
    }
}

#[derive(Parser)]
#[command(
    name = "jev",
    author = "ISMAEL HOSNI SOILET DE LIMA <soilet.ismael@gmail.com>",
    version = env!("CARGO_PKG_VERSION"),
    about = "Zero-overhead System One decision harness and token optimizer for AI coding agents",
    long_about = None
)]
pub struct Cli {
    #[arg(long, global = true, help = "Force offline heuristic simulation mode")]
    pub mock: bool,

    #[arg(long, global = true, help = "Output results in machine-readable JSON")]
    pub json: bool,

    #[arg(
        long,
        global = true,
        help = "Override backend provider (typesafe, commandcode, opencode, openrouter, vercel)"
    )]
    pub provider: Option<String>,

    #[arg(
        long,
        global = true,
        help = "Surface provider errors instead of falling back to the offline engine (default: fail-open)"
    )]
    pub fail_closed: bool,

    #[arg(
        long,
        global = true,
        help = "Maximum provider attempts for retryable failures (default: 3)"
    )]
    pub retries: Option<u32>,

    #[arg(
        long,
        global = true,
        help = "Decide and report, but never change the exit code (also via .jev.json)"
    )]
    pub shadow: bool,

    #[command(subcommand)]
    pub command: Commands,
}

#[derive(Subcommand)]
pub enum ExportTargets {
    #[command(about = "Write the Foreman operator bundle (preset TOML + companion class + README)")]
    Foreman {
        #[arg(long, help = "Target directory (default: ./foreman-responsibilities/)")]
        out_dir: Option<String>,
    },
}

#[derive(Subcommand)]
pub enum Commands {
    #[command(about = "Display active credentials, provider, and engine mode")]
    Status,

    #[command(about = "Write integration bundles for other tools (currently: foreman)")]
    Export {
        #[command(subcommand)]
        target: ExportTargets,
    },

    #[command(about = "Run stdio MCP server for Cursor, Claude Desktop, Antigravity IDE")]
    Mcp,

    #[command(about = "Initialize Jev Harness configuration and agent adapters in current repo")]
    Init {
        #[arg(long, help = "Configure Cursor MCP server")]
        cursor: bool,
        #[arg(
            long,
            help = "Override the detected test command for the generated git hook"
        )]
        test_cmd: Option<String>,
        #[arg(long, help = "Configure Antigravity IDE hooks")]
        antigravity: bool,
        #[arg(long, help = "Configure all available agent integrations")]
        all: bool,
        #[arg(long, help = "Install git pre-commit test-gate hook")]
        git: bool,
    },

    #[command(about = "Display ROI, token savings, and telemetry statistics")]
    Metrics {
        #[arg(long, help = "Reset session metrics")]
        reset: bool,
    },

    #[command(
        alias = "triage",
        about = "Triage test traceback & determine if frontier LLM call can be skipped"
    )]
    TestGate {
        #[arg(help = "Direct error string or path to error log file")]
        log_pos: Option<String>,

        #[arg(short, long, help = "Path to error log or raw string")]
        log: Option<String>,

        #[arg(long, help = "Sample error string (alias for --log)")]
        sample: Option<String>,
    },

    #[command(
        alias = "abort",
        about = "Evaluate if current trajectory or refactor direction should be aborted"
    )]
    AbortCheck {
        #[arg(help = "Proposed next step plan")]
        plan_pos: Option<String>,

        #[arg(short, long, help = "Proposed next step plan")]
        plan: Option<String>,

        #[arg(
            short = 'H',
            long,
            default_value = "",
            help = "Recent attempts or error history"
        )]
        history: String,
    },

    #[command(about = "Select minimal sufficient model tier for a given task")]
    Route {
        #[arg(help = "Task description")]
        task_pos: Option<String>,

        #[arg(short, long, help = "Task description")]
        task: Option<String>,
    },

    #[command(about = "Verify if actual step output satisfies required criteria")]
    Verify {
        #[arg(short, long, help = "Acceptance criteria to satisfy")]
        criteria: String,

        #[arg(short, long, help = "Actual output to verify")]
        output: String,
    },

    #[command(
        alias = "astra-jev",
        alias = "effort",
        about = "Dynamically modulate reasoning effort per-generation (Astra-Jev)"
    )]
    ReasoningEffort {
        #[arg(help = "Immediate step context or prompt description")]
        context_pos: Option<String>,

        #[arg(short, long, help = "Immediate step context or prompt description")]
        context: Option<String>,

        #[arg(
            long = "target-provider",
            default_value = "openai",
            help = "Target model provider (openai, deepseek, qwen, anthropic, gemini)"
        )]
        target_provider: String,

        #[arg(
            short,
            long,
            help = "Target model name (e.g. gpt-5.6-luna, deepseek-v4.1-flash)"
        )]
        model: Option<String>,

        #[arg(
            long = "session-context-tokens",
            default_value = "0",
            help = "Active prompt tokens in session context"
        )]
        session_context_tokens: usize,

        #[arg(
            long = "supported-efforts",
            help = "Comma-separated list of supported effort levels"
        )]
        supported_efforts: Option<String>,

        #[arg(
            long = "max-lease-steps",
            default_value = "10",
            help = "Maximum generations to lease unchanged effort"
        )]
        max_lease_steps: u32,
    },

    #[command(
        alias = "nudge",
        about = "Evaluate if agent stopped prematurely with unfinished work or unverified changes (Jev Nudge Gate)"
    )]
    NudgeGate {
        #[arg(help = "Recent agent transcript tail or path to file")]
        transcript_pos: Option<String>,

        #[arg(short, long, help = "Recent agent transcript tail or path to file")]
        transcript: Option<String>,

        #[arg(
            short = 'P',
            long = "previous-nudge",
            default_value = "",
            help = "Summary of the previous nudge to verify progress"
        )]
        previous_nudge: String,

        #[arg(
            long,
            default_value = "0.5",
            help = "Probability threshold for nudge/waiting/progress (default: 0.5)"
        )]
        threshold: f64,
    },
}

fn read_input(arg_pos: Option<String>, arg_flag: Option<String>) -> io::Result<String> {
    if let Some(target) = arg_flag.or(arg_pos) {
        let p = Path::new(&target);
        if p.is_file() {
            return fs::read_to_string(p);
        }
        return Ok(target);
    }

    if !io::stdin().is_terminal() {
        let mut buffer = String::new();
        io::stdin().read_to_string(&mut buffer)?;
        return Ok(buffer);
    }

    Ok(String::new())
}

/// Best-effort detection of the repository test command for the generated git hook.
/// Mirrors the Python and TypeScript runtimes.
const ENV_EXAMPLE: &str = "# Jev Harness provider credentials. Offline mode needs NO key (zero network calls).\n# Docs: https://github.com/ismaelsoilet/jev-harness/blob/main/docs/AGENT_INTEGRATION_GUIDE.md\n#\n# OpenCode Zen (free tier) - https://opencode.ai/auth\n# JEV_PROVIDER=opencode\n# OPENCODE_API_KEY=\"your_key_here\"\n#\n# TypeSafe AI (direct) - https://console.typesafe.ai\n# TYPESAFE_API_KEY=\"your_key_here\"\n#\n# Command Code - https://commandcode.ai/signup  (or run: cmd login)\n# CMD_API_KEY=\"your_key_here\"\n#\n# OpenRouter (alpha access only)\n# OPENROUTER_API_KEY=\"your_key_here\"\n#\n# Vercel AI Gateway\n# AI_GATEWAY_API_KEY=\"your_key_here\"\n";

/// Returns the project venv binary (e.g. ./.venv/bin/python) when present, else the fallback.
/// Hook-safe: paths are relative to the repository root, which is the CWD Git uses for hooks.
fn project_bin(cwd: &Path, name: &str, fallback: &str) -> String {
    let candidates = [
        PathBuf::from(".venv").join("bin").join(name),
        PathBuf::from("venv").join("bin").join(name),
        PathBuf::from(".venv")
            .join("Scripts")
            .join(format!("{}.exe", name)),
        PathBuf::from("venv")
            .join("Scripts")
            .join(format!("{}.exe", name)),
    ];
    for rel in candidates {
        if cwd.join(&rel).exists() {
            return format!("./{}", rel.to_string_lossy().replace('\\', "/"));
        }
    }
    fallback.to_string()
}

fn detect_test_command(cwd: &Path, override_cmd: &str) -> String {
    if !override_cmd.trim().is_empty() {
        return override_cmd.trim().to_string();
    }
    let python_bin = project_bin(cwd, "python", "python3");
    let package_json = cwd.join("package.json");
    if package_json.is_file() {
        if let Ok(content) = fs::read_to_string(&package_json) {
            if let Ok(value) = serde_json::from_str::<serde_json::Value>(&content) {
                if value.get("scripts").and_then(|s| s.get("test")).is_some() {
                    return "npm test --silent".to_string();
                }
            }
        }
    }
    if cwd.join("Cargo.toml").is_file() {
        return "cargo test --quiet".to_string();
    }
    let pyproject = cwd.join("pyproject.toml");
    let pytest_marker = cwd.join("pytest.ini").is_file()
        || cwd.join("tox.ini").is_file()
        || (pyproject.is_file()
            && fs::read_to_string(&pyproject)
                .map(|c| c.contains("[tool.pytest"))
                .unwrap_or(false));
    if pytest_marker {
        return format!("{} -m pytest -q", python_bin);
    }
    if pyproject.is_file() || cwd.join("setup.py").is_file() || cwd.join("tests").is_dir() {
        return format!("{} -m unittest", python_bin);
    }
    String::new()
}

/// Generated pre-commit hook: the runner decides, Jev only advises.
fn build_git_hook(test_cmd: &str, jev_bin: &str) -> String {
    format!(
        r#"#!/bin/sh
# Jev Harness pre-commit gate (generated by `jev-harness init --git`).
# The test runner decides whether the commit is blocked; Jev only triages a failing
# run so it can be fixed deterministically when possible.
# Regenerate with: jev-harness init --git

TEST_CMD="{cmd}"
JEV_BIN="{jev}"

if [ -z "$TEST_CMD" ]; then
  echo "[jev] No test command detected. Edit this hook and set TEST_CMD (e.g. npm test)." >&2
  exit 0
fi

if ! TEST_OUTPUT=$(sh -c "$TEST_CMD" 2>&1); then
  printf '%s\n' "$TEST_OUTPUT" | "$JEV_BIN" test-gate
  exit 1
fi
exit 0
"#,
        cmd = test_cmd,
        jev = jev_bin
    )
}

pub async fn run_cli() {
    let cli = Cli::parse();
    let shadow = cli.shadow || crate::config::load_repo_config().shadow;
    let mut client = JevClient::new(None, None, None, None, cli.mock).with_failure_policy(
        !cli.fail_closed,
        cli.retries.unwrap_or(3),
        500,
    );
    if let Some(ref p) = cli.provider {
        client.provider = p.clone();
        if p == "commandcode" {
            client.base_url = COMMANDCODE_API_URL.to_string();
            client.model = "typesafe/jev".to_string();
        } else if p == "opencode" {
            client.base_url = "https://opencode.ai/zen/v1/systemone".to_string();
            client.model = "jev-1.13-free".to_string();
        }
    }

    match cli.command {
        Commands::Status => {
            println!("\n=== JEV HARNESS (RUST) STATUS ===");
            let is_live =
                !client.force_mock && (client.provider == "opencode" || client.api_key.is_some());
            if is_live {
                if client.provider == "opencode" {
                    println!("Provider:    OPENCODE ZEN (Free Tier)");
                    println!("Endpoint:    {}", client.base_url);
                    println!("Engine Mode: LIVE (OpenCode Zen Free Community Model)");
                } else if client.provider == "commandcode" {
                    let masked = if let Some(ref key) = client.api_key {
                        if key.len() > 10 {
                            format!("{}...{}", &key[..6], &key[key.len() - 4..])
                        } else {
                            "***".to_string()
                        }
                    } else {
                        "***".to_string()
                    };
                    println!("API Key:     Configured ({})", masked);
                    println!("Provider:    COMMAND CODE (Free $0.00/M Deal - typesafe/jev)");
                    println!("Endpoint:    {}", client.base_url);
                    println!("Engine Mode: LIVE");
                } else {
                    let masked = if let Some(ref key) = client.api_key {
                        if key.len() > 10 {
                            format!("{}...{}", &key[..6], &key[key.len() - 4..])
                        } else {
                            "***".to_string()
                        }
                    } else {
                        "***".to_string()
                    };
                    println!("API Key:     Configured ({})", masked);
                    println!("Provider:    {}", client.provider.to_uppercase());
                    println!("Endpoint:    {}", client.base_url);
                    println!("Engine Mode: LIVE");
                }
            } else {
                println!("API Key:     NOT DETECTED");
                println!("Engine Mode: SIMULATION / MOCK (Heuristic offline mode active)");
            }
            println!("Model:       {}", client.model);
            println!("Model origin: {}", model_origin_label(&client.model_source));
            if client.model == "jev-latest" {
                println!(
                    "Note:        'jev-latest' is a moving alias - pin a version (e.g. \"model\": \"jev-1.13.0\") when your thresholds are calibrated."
                );
            }
            println!("=================================\n");
            process::exit(0);
        }

        Commands::Mcp => {
            if let Err(e) = crate::mcp::run_mcp_server(Some(client)).await {
                eprintln!("MCP server error: {}", e);
                process::exit(1);
            }
            process::exit(0);
        }

        Commands::Export { target } => {
            match target {
                ExportTargets::Foreman { out_dir } => {
                    let directory = PathBuf::from(
                        out_dir.unwrap_or_else(|| crate::foreman::FOREMAN_DEFAULT_OUT_DIR.to_string()),
                    );
                    if directory
                        .components()
                        .any(|component| component.as_os_str() == ".foreman")
                    {
                        eprintln!(
                            "Error: refusing to write into a '.foreman/' directory - that path is Foreman run state, not configuration. Point --out-dir at the Foreman installation's responsibilities directory instead."
                        );
                        process::exit(2);
                    }
                    let _ = fs::create_dir_all(&directory);
                    let _ = fs::write(
                        directory.join(crate::foreman::FOREMAN_PRESET_FILENAME),
                        crate::foreman::FOREMAN_RESPONSIBILITY_TOML,
                    );
                    let _ = fs::write(
                        directory.join(crate::foreman::FOREMAN_COMPANION_FILENAME),
                        crate::foreman::FOREMAN_COMPANION_CLASS_SOURCE,
                    );
                    let _ = fs::write(
                        directory.join(crate::foreman::FOREMAN_README_FILENAME),
                        crate::foreman::FOREMAN_OPERATOR_README,
                    );
                    println!(
                        "\n[OK] Foreman operator bundle written to: {}",
                        directory.display()
                    );
                    println!("  [+] {}", crate::foreman::FOREMAN_PRESET_FILENAME);
                    println!("  [+] {}", crate::foreman::FOREMAN_COMPANION_FILENAME);
                    println!("  [+] {}", crate::foreman::FOREMAN_README_FILENAME);
                    println!(
                        "The pair ships together: a TOML without the installed class makes foreman exit 2."
                    );
                    println!(
                        "Next: foreman run --repo <repo> --job \"<job>\" --responsibilities-dir {}\n",
                        directory.display()
                    );
                    process::exit(0);
                }
            }
        }

        Commands::Init {
            cursor,
            antigravity: _,
            all,
            git,
            test_cmd,
        } => {
            let cwd = std::env::current_dir().unwrap_or_else(|_| PathBuf::from("."));
            let test_cmd_override = test_cmd.clone().unwrap_or_default();
            println!("Initializing Jev Harness integration in: {}", cwd.display());

            let skills_dir = cwd.join(".agents").join("skills").join("jev-harness");
            let _ = fs::create_dir_all(&skills_dir);
            let skill_file = skills_dir.join("SKILL.md");
            let skill_content = "---\nname: jev-harness\ndescription: Repository adapter for Jev System One.\nlicense: MIT\n---\n\n# Local Jev Harness Adapter\n\nThis repository is connected to the global **Jev System One Harness**.\n";
            if skill_file.exists() {
                println!(
                    "  [=] Existing agent skill preserved: {}",
                    skill_file.display()
                );
            } else {
                let _ = fs::write(&skill_file, skill_content);
                println!("  [+] Created agent skill: {}", skill_file.display());
            }

            let jev_json = cwd.join(".jev.json");
            if !jev_json.exists() {
                let _ = fs::write(&jev_json, "{\n  \"api_key\": \"\",\n  \"model\": \"jev-latest\",\n  \"skip_llm_threshold\": 0.65,\n  \"abort_threshold\": 0.70\n}\n");
                println!("  [+] Created repo config: {}", jev_json.display());
            }

            if ensure_state_ignored(&cwd).is_some() {
                println!("  [+] Added '.jev/' to .gitignore (local sessions, receipts and cache)");
            }

            let env_example = cwd.join(".env.jev.example");
            if !env_example.exists() {
                let _ = fs::write(&env_example, ENV_EXAMPLE);
                println!("  [+] Created env template: {}", env_example.display());
            }

            if cursor || all || cwd.join(".cursor").exists() {
                let cursor_dir = cwd.join(".cursor");
                let _ = fs::create_dir_all(&cursor_dir);
                let cursor_mcp = cursor_dir.join("mcp.json");
                if !cursor_mcp.exists() {
                    let _ = fs::write(&cursor_mcp, "{\n  \"mcpServers\": {\n    \"jev-harness\": {\n      \"command\": \"jev\",\n      \"args\": [\"mcp\"]\n    }\n  }\n}\n");
                    println!("  [+] Created Cursor MCP config: {}", cursor_mcp.display());
                }
            }
            let mut git_gate_active = true;
            if git || all {
                let git_hooks = cwd.join(".git").join("hooks");
                if git_hooks.is_dir() {
                    let marker = "Jev Harness pre-commit gate";
                    let pre_commit = git_hooks.join("pre-commit");
                    let test_cmd = detect_test_command(&cwd, &test_cmd_override);
                    let jev_bin = project_bin(&cwd, "jev-harness", "jev-harness");
                    let hook_script = build_git_hook(&test_cmd, &jev_bin);
                    let existing = fs::read_to_string(&pre_commit).unwrap_or_default();
                    if !existing.is_empty()
                        && !existing.to_lowercase().contains(&marker.to_lowercase())
                    {
                        let sample = git_hooks.join("pre-commit.jev");
                        let _ = fs::write(&sample, &hook_script);
                        #[cfg(unix)]
                        {
                            use std::os::unix::fs::PermissionsExt;
                            let _ = fs::set_permissions(&sample, fs::Permissions::from_mode(0o755));
                        }
                        git_gate_active = false;
                        println!("  [!] An existing pre-commit hook was preserved; the Jev gate is NOT active yet. Merge {} into it (or use the pre-commit framework) to enable it.", sample.display());
                    } else {
                        let _ = fs::write(&pre_commit, &hook_script);
                        #[cfg(unix)]
                        {
                            use std::os::unix::fs::PermissionsExt;
                            let _ =
                                fs::set_permissions(&pre_commit, fs::Permissions::from_mode(0o755));
                        }
                        let detected = detect_test_command(&cwd, &test_cmd_override);
                        let detail = if detected.is_empty() {
                            " (no test command detected yet)".to_string()
                        } else {
                            format!(" (test command: {})", detected)
                        };
                        println!(
                            "  [+] Installed Git pre-commit guardrail: {}{}",
                            pre_commit.display(),
                            detail
                        );
                    }
                }
            }
            if git_gate_active {
                println!("\n[OK] Repository configured successfully! You can now run 'jev-harness status'.\n");
            } else {
                println!("\n[!] Repository configured, but the Jev commit gate is NOT active (an existing hook was preserved). Merge .git/hooks/pre-commit.jev to enable it.\n");
            }
            process::exit(0);
        }

        Commands::Metrics { reset } => {
            let home = std::env::var("HOME")
                .or_else(|_| std::env::var("USERPROFILE"))
                .unwrap_or_else(|_| ".".to_string());
            let config_dir = PathBuf::from(&home).join(".config").join("jev");
            let session_path = config_dir.join("session.json");

            if reset {
                if session_path.exists() {
                    let _ = fs::remove_file(&session_path);
                }
                println!("\n[OK] Jev Harness metrics reset successfully.\n");
                process::exit(0);
            }

            let mut triage_calls = 0u64;
            let mut skipped_llm = 0u64;
            let mut abort_guards = 0u64;
            let mut deterministic_routes = 0u64;
            let mut effort_modulations = 0u64;
            let mut nudge_continuations = 0u64;
            let mut tokens_saved = 0u64;
            let mut cost_saved = 0.0f64;

            if let Ok(content) = fs::read_to_string(&session_path) {
                if let Ok(val) = serde_json::from_str::<serde_json::Value>(&content) {
                    triage_calls = val
                        .get("total_triage_calls")
                        .and_then(|v| v.as_u64())
                        .unwrap_or(0);
                    skipped_llm = val
                        .get("skipped_llm_calls")
                        .and_then(|v| v.as_u64())
                        .unwrap_or(0);
                    abort_guards = val
                        .get("abort_guards_triggered")
                        .and_then(|v| v.as_u64())
                        .unwrap_or(0);
                    deterministic_routes = val
                        .get("deterministic_routes")
                        .and_then(|v| v.as_u64())
                        .unwrap_or(0);
                    effort_modulations = val
                        .get("effort_modulations")
                        .and_then(|v| v.as_u64())
                        .unwrap_or(0);
                    nudge_continuations = val
                        .get("nudge_continuations")
                        .and_then(|v| v.as_u64())
                        .unwrap_or(0);
                    tokens_saved = val
                        .get("estimated_tokens_saved")
                        .and_then(|v| v.as_u64())
                        .unwrap_or(0);
                    cost_saved = val
                        .get("estimated_cost_saved_usd")
                        .and_then(|v| v.as_f64())
                        .unwrap_or(0.0);
                }
            }

            if cli.json {
                let out = serde_json::json!({
                    "total_triage_calls": triage_calls,
                    "skipped_llm_calls": skipped_llm,
                    "abort_guards_triggered": abort_guards,
                    "deterministic_routes": deterministic_routes,
                    "effort_modulations": effort_modulations,
                    "nudge_continuations": nudge_continuations,
                    "estimated_tokens_saved": tokens_saved,
                    "estimated_cost_saved_usd": (cost_saved * 100.0).round() / 100.0,
                    "estimates_are_heuristic": true,
                });
                println!("{}", serde_json::to_string_pretty(&out).unwrap());
            } else {
                println!("\n=== JEV HARNESS ROI & TOKEN METRICS (RUST) ===");
                println!("Total Test Triages:      {}", triage_calls);
                println!(
                    "LLM Calls Intercepted:   {} (Fixed deterministically)",
                    skipped_llm
                );
                println!("Doom Loops Aborted:      {}", abort_guards);
                println!("Deterministic Routes:    {}", deterministic_routes);
                println!(
                    "Effort Modulations:      {} (Astra-Jev per-generation)",
                    effort_modulations
                );
                println!(
                    "Continuation Nudges:     {} (Jev Nudge Gate)",
                    nudge_continuations
                );
                println!(
                    "Estimated Tokens Saved:  ⚡ {} tokens (heuristic estimate)",
                    tokens_saved
                );
                println!(
                    "Estimated API Cost Saved: 💸 ${:.2} USD (heuristic estimate)",
                    cost_saved
                );
                println!(
                    "Assumption Model:        {} tokens/${:.2} per intercepted triage; {} tokens/${:.2} per aborted doom loop",
                    26200, 0.31, 80000, 1.20
                );
                println!("==============================================\n");
            }
            process::exit(0);
        }

        Commands::TestGate {
            log_pos,
            log,
            sample,
        } => {
            if let Some(path) = log.as_ref() {
                if !std::path::Path::new(path).is_file() {
                    // `--log` is documented as a file: a typo must not be triaged as log text.
                    eprintln!("Error: log file not found: {}", path);
                    eprintln!("Hint: pass the log text as a positional argument, use --sample for a literal string, or pipe it via stdin.");
                    process::exit(2);
                }
            }
            let text = match read_input(log_pos, log.or(sample)) {
                Ok(t) if !t.trim().is_empty() => t,
                _ => {
                    eprintln!("Error: No test failure log provided. Pass log via argument or pipe via stdin.");
                    process::exit(2);
                }
            };

            match triage_test_failure(&text, Some(&client)).await {
                Ok(res) => {
                    if cli.json {
                        let mut value = serde_json::to_value(&res).unwrap_or(serde_json::json!({}));
                        if shadow {
                            if let Some(obj) = value.as_object_mut() {
                                obj.insert("shadow".to_string(), serde_json::json!(true));
                                obj.insert(
                                    "would_exit".to_string(),
                                    serde_json::json!(if res.skip_llm { 0 } else { 1 }),
                                );
                            }
                        }
                        println!("{}", serde_json::to_string_pretty(&value).unwrap());
                    } else {
                        println!("\n--- JEV TEST TRIAGE VERDICT (RUST) ---");
                        println!("Category:        {}", res.category.to_uppercase());
                        if res.category == "no_failure" {
                            println!("No failure detected: the test run appears successful. Nothing to triage.");
                            println!("Mode:            [DETERMINISTIC]");
                            println!("--------------------------------\n");
                            process::exit(0);
                        }
                        println!("Confidence:      {:.1}%", res.confidence * 100.0);
                        println!(
                            "Skip LLM Call:   {}",
                            if res.skip_llm {
                                "YES (Save Tokens!)"
                            } else {
                                "NO (Dispatch to System 2)"
                            }
                        );
                        println!("Severity Score:  {:.1} / 4.0", res.severity_score);
                        println!("Recommendation:  {}", res.action_recommendation);
                        if res.is_mock {
                            println!("Mode:            {}", mock_mode_label(&res.degraded_reason));
                        }
                        println!("--------------------------------------\n");
                    }
                    process::exit(shadow_exit(shadow, if res.skip_llm { 0 } else { 1 }));
                }
                Err(e) => {
                    exit_gate_error(shadow, &format!("Error: triaging test failure: {}", e));
                }
            }
        }

        Commands::AbortCheck {
            plan_pos,
            plan,
            history,
        } => {
            let plan_text = match read_input(plan_pos, plan) {
                Ok(p) if !p.trim().is_empty() => p,
                _ => {
                    eprintln!(
                        "Error: No plan provided. Pass --plan <text> or positional argument."
                    );
                    process::exit(2);
                }
            };

            match should_abort_trajectory(&plan_text, &history, Some(&client)).await {
                Ok(res) => {
                    if cli.json {
                        println!("{}", serde_json::to_string_pretty(&res).unwrap());
                    } else {
                        println!("\n--- JEV ABORT GATE VERDICT (RUST) ---");
                        println!(
                            "Should Abort:     {}",
                            if res.should_abort {
                                "YES - STOP & RECONSIDER"
                            } else {
                                "NO - PROCEED"
                            }
                        );
                        println!("Abort Probability: {:.1}%", res.abort_probability * 100.0);
                        println!("Viability Score:   {:.1} / 4.0", res.viability_score);
                        println!("Summary:           {}", res.reasoning_summary);
                        if res.is_mock {
                            println!(
                                "Mode:              {}",
                                mock_mode_label(&res.degraded_reason)
                            );
                        }
                        println!("-------------------------------------\n");
                    }
                    process::exit(shadow_exit(shadow, if res.should_abort { 1 } else { 0 }));
                }
                Err(e) => {
                    exit_gate_error(shadow, &format!("Error: evaluating abort gate: {}", e));
                }
            }
        }

        Commands::Route { task_pos, task } => {
            let task_text = match read_input(task_pos, task) {
                Ok(t) if !t.trim().is_empty() => t,
                _ => {
                    eprintln!("Error: No task description provided. Pass --task <text>.");
                    process::exit(2);
                }
            };

            match route_model_tier(&task_text, Some(&client)).await {
                Ok(res) => {
                    if cli.json {
                        println!("{}", serde_json::to_string_pretty(&res).unwrap());
                    } else {
                        println!("\n--- JEV MODEL ROUTE VERDICT (RUST) ---");
                        println!("Selected Tier:     {}", res.selected_tier.to_uppercase());
                        println!("Confidence:        {:.1}%", res.confidence * 100.0);
                        println!("Recommended Model: {}", res.recommended_model);
                        println!("Rationale:         {}", res.rationale);
                        if res.is_mock {
                            println!(
                                "Mode:              {}",
                                mock_mode_label(&res.degraded_reason)
                            );
                        }
                        println!("--------------------------------------\n");
                    }
                    process::exit(0);
                }
                Err(e) => {
                    exit_gate_error(shadow, &format!("Error: routing model tier: {}", e));
                }
            }
        }

        Commands::Verify { criteria, output } => {
            match verify_step_completion(&criteria, &output, Some(&client)).await {
                Ok(res) => {
                    if cli.json {
                        println!("{}", serde_json::to_string_pretty(&res).unwrap());
                    } else {
                        println!("\n--- JEV VERIFICATION VERDICT (RUST) ---");
                        println!(
                            "Verified:          {}",
                            if res.is_verified {
                                "PASS"
                            } else {
                                "REWORK NEEDED"
                            }
                        );
                        println!(
                            "Satisfaction Prob: {:.1}%",
                            res.satisfaction_probability * 100.0
                        );
                        println!("Rigor Score:       {:.1} / 4.0", res.rigor_score);
                        if res.is_mock {
                            println!(
                                "Mode:              {}",
                                mock_mode_label(&res.degraded_reason)
                            );
                        }
                        println!("---------------------------------------\n");
                    }
                    process::exit(shadow_exit(shadow, if res.is_verified { 0 } else { 1 }));
                }
                Err(e) => {
                    exit_gate_error(shadow, &format!("Error: verifying step completion: {}", e));
                }
            }
        }

        Commands::ReasoningEffort {
            context_pos,
            context,
            target_provider,
            model,
            session_context_tokens,
            supported_efforts,
            max_lease_steps,
        } => {
            let ctx = match read_input(context_pos, context) {
                Ok(t) if !t.trim().is_empty() => t,
                _ => {
                    eprintln!(
                        "Error: Context/step description must be provided via argument or stdin."
                    );
                    process::exit(2);
                }
            };

            let supported_vec = supported_efforts.map(|s| {
                s.split(',')
                    .map(|item| item.trim().to_lowercase())
                    .filter(|item| !item.is_empty())
                    .collect::<Vec<String>>()
            });
            let supported_refs = supported_vec
                .as_ref()
                .map(|v| v.iter().map(|s| s.as_str()).collect::<Vec<&str>>());

            match modulate_reasoning_effort_full(
                &ctx,
                &target_provider,
                model.as_deref(),
                session_context_tokens,
                supported_refs.as_deref(),
                max_lease_steps,
                Some(&client),
            )
            .await
            {
                Ok(res) => {
                    if cli.json {
                        println!("{}", serde_json::to_string_pretty(&res).unwrap());
                    } else {
                        println!("\n--- JEV REASONING EFFORT VERDICT (RUST) ---");
                        println!("Effort:            {}", res.effort.to_uppercase());
                        println!("Confidence:        {:.1}%", res.confidence * 100.0);
                        println!("Complexity Score:  {:.1} / 4.0", res.complexity_score);
                        println!("Lease Steps:       {}", res.lease_steps);
                        println!("Provider:          {}", res.provider);
                        println!(
                            "Supported:         {}",
                            if res.is_reasoning_supported {
                                "YES"
                            } else {
                                "NO (Direct model)"
                            }
                        );
                        println!("Rationale:         {}", res.rationale);
                        println!("Provider Params:   {}", res.provider_params);
                        if !res.cache_safe_recommendation.is_empty() {
                            println!("Cache Advisory:    {}", res.cache_safe_recommendation);
                        }
                        if res.is_mock {
                            println!(
                                "Mode:              {}",
                                mock_mode_label(&res.degraded_reason)
                            );
                        }
                        println!("------------------------------------------\n");
                    }
                    process::exit(0);
                }
                Err(e) => {
                    exit_gate_error(
                        shadow,
                        &format!("Error: modulating reasoning effort: {}", e),
                    );
                }
            }
        }

        Commands::NudgeGate {
            transcript_pos,
            transcript,
            previous_nudge,
            threshold,
        } => {
            let tail = match read_input(transcript_pos, transcript) {
                Ok(t) if !t.trim().is_empty() => t,
                _ => {
                    eprintln!("Error: No transcript tail provided. Pass --transcript <text> or pipe via stdin.");
                    process::exit(2);
                }
            };

            match should_nudge_continuation(&tail, &previous_nudge, threshold, Some(&client)).await
            {
                Ok(res) => {
                    if cli.json {
                        println!("{}", serde_json::to_string_pretty(&res).unwrap());
                    } else {
                        println!("\n=== JEV CONTINUATION NUDGE GATE (RUST) ===");
                        println!(
                            "Should Nudge:      {}",
                            if res.should_nudge {
                                "YES (Inject Continuation)"
                            } else {
                                "NO (Stop & Yield to User)"
                            }
                        );
                        println!("Workflow Phase:    {}", res.workflow_phase.to_uppercase());
                        println!("Nudge Prob:        {:.1}%", res.nudge_probability * 100.0);
                        println!("Waiting Prob:      {:.1}%", res.waiting_probability * 100.0);
                        println!(
                            "Progress Prob:     {:.1}%",
                            res.progress_probability * 100.0
                        );
                        println!("Rationale:         {}", res.rationale);
                        if !res.suggested_nudge_prompt.is_empty() {
                            println!("Suggested Prompt:  {}", res.suggested_nudge_prompt);
                        }
                        if res.is_mock {
                            println!(
                                "Engine Mode:       {}",
                                mock_mode_label(&res.degraded_reason)
                            );
                        }
                        println!("==========================================\n");
                    }
                    process::exit(shadow_exit(shadow, if res.should_nudge { 0 } else { 1 }));
                }
                Err(e) => {
                    exit_gate_error(shadow, &format!("Error: evaluating nudge gate: {}", e));
                }
            }
        }
    }
}
