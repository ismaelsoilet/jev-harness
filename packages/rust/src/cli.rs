use clap::{Parser, Subcommand};
use crate::{
    client::JevClient,
    gates::{route_model_tier, should_abort_trajectory, triage_test_failure, verify_step_completion},
};
use std::fs;
use std::io::{self, IsTerminal, Read};
use std::path::Path;
use std::process;

#[derive(Parser)]
#[command(
    name = "jev",
    author = "ISMAEL HOSNI SOILET DE LIMA <soilet.ismael@gmail.com>",
    version = "0.1.0",
    about = "Zero-overhead System One decision harness and token optimizer for AI coding agents",
    long_about = None
)]
pub struct Cli {
    #[arg(long, global = true, help = "Force offline heuristic simulation mode")]
    pub mock: bool,

    #[arg(long, global = true, help = "Output results in machine-readable JSON")]
    pub json: bool,

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

        #[arg(short = 'H', long, default_value = "", help = "Recent attempts or error history")]
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
    let client = JevClient::new(None, None, None, None, cli.mock);

    match cli.command {
        Commands::Status => {
            println!("\n=== JEV HARNESS (RUST) STATUS ===");
            if let Some(ref key) = client.api_key {
                let masked = if key.len() > 10 {
                    format!("{}...{}", &key[..6], &key[key.len() - 4..])
                } else {
                    "***".to_string()
                };
                println!("API Key:     Configured ({})", masked);
                println!("Provider:    {}", client.provider.to_uppercase());
                println!("Endpoint:    {}", client.base_url);
                println!("Engine Mode: LIVE");
            } else {
                println!("API Key:     NOT DETECTED");
                println!("Engine Mode: SIMULATION / MOCK (Heuristic offline mode active)");
            }
            println!("Model:       {}", client.model);
            println!("=================================\n");
            process::exit(0);
        }

        Commands::TestGate { log_pos, log } => {
            let text = match read_input(log_pos, log) {
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
            let plan_text = match plan.or(plan_pos) {
                Some(p) if !p.trim().is_empty() => p,
                _ => {
                    eprintln!("Error: No plan provided. Pass --plan <text> or positional argument.");
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
            let task_text = match task.or(task_pos) {
                Some(t) if !t.trim().is_empty() => t,
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
    }
}
