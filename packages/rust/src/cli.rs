use crate::{
    client::{JevClient, COMMANDCODE_API_URL},
    gates::{
        modulate_reasoning_effort_full, route_model_tier,
        should_abort_trajectory, should_nudge_continuation, triage_test_failure,
        verify_step_completion,
    },
};
use clap::{Parser, Subcommand};
use std::fs;
use std::io::{self, IsTerminal, Read};
use std::path::Path;
use std::process;

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

    #[command(subcommand)]
    pub command: Commands,
}

#[derive(Subcommand)]
pub enum Commands {
    #[command(about = "Display active credentials, provider, and engine mode")]
    Status,

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

pub async fn run_cli() {
    let cli = Cli::parse();
    let mut client = JevClient::new(None, None, None, None, cli.mock);
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
            println!("=================================\n");
            process::exit(0);
        }

        Commands::TestGate {
            log_pos,
            log,
            sample,
        } => {
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
                        println!("{}", serde_json::to_string_pretty(&res).unwrap());
                    } else {
                        println!("\n--- JEV TEST TRIAGE VERDICT (RUST) ---");
                        println!("Category:        {}", res.category.to_uppercase());
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
                            println!("Mode:            [SIMULATION/MOCK]");
                        }
                        println!("--------------------------------------\n");
                    }
                    process::exit(if res.skip_llm { 0 } else { 1 });
                }
                Err(e) => {
                    eprintln!("Error triaging test failure: {}", e);
                    process::exit(2);
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
                            println!("Mode:              [SIMULATION/MOCK]");
                        }
                        println!("-------------------------------------\n");
                    }
                    process::exit(if res.should_abort { 1 } else { 0 });
                }
                Err(e) => {
                    eprintln!("Error evaluating abort gate: {}", e);
                    process::exit(2);
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
                            println!("Mode:              [SIMULATION/MOCK]");
                        }
                        println!("--------------------------------------\n");
                    }
                    process::exit(0);
                }
                Err(e) => {
                    eprintln!("Error routing model tier: {}", e);
                    process::exit(2);
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
                            println!("Mode:              [SIMULATION/MOCK]");
                        }
                        println!("---------------------------------------\n");
                    }
                    process::exit(if res.is_verified { 0 } else { 1 });
                }
                Err(e) => {
                    eprintln!("Error verifying step completion: {}", e);
                    process::exit(2);
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
            let supported_refs = supported_vec.as_ref().map(|v| {
                v.iter().map(|s| s.as_str()).collect::<Vec<&str>>()
            });

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
                            println!("Mode:              [SIMULATION/MOCK]");
                        }
                        println!("------------------------------------------\n");
                    }
                    process::exit(0);
                }
                Err(e) => {
                    eprintln!("Error modulating reasoning effort: {}", e);
                    process::exit(2);
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
                        println!("Workflow Phase:    {}", res.sureforge_phase.to_uppercase());
                        println!("Nudge Prob:        {:.1}%", res.nudge_probability * 100.0);
                        println!("Waiting Prob:      {:.1}%", res.waiting_probability * 100.0);
                        println!("Progress Prob:     {:.1}%", res.progress_probability * 100.0);
                        println!("Rationale:         {}", res.rationale);
                        if !res.suggested_nudge_prompt.is_empty() {
                            println!("Suggested Prompt:  {}", res.suggested_nudge_prompt);
                        }
                        if res.is_mock {
                            println!("Engine Mode:       [SIMULATION / MOCK]");
                        }
                        println!("==========================================\n");
                    }
                    process::exit(if res.should_nudge { 0 } else { 1 });
                }
                Err(e) => {
                    eprintln!("Error evaluating nudge gate: {}", e);
                    process::exit(2);
                }
            }
        }
    }
}
