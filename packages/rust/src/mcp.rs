//! Model Context Protocol (MCP) Server for Jev System One (Rust runtime).
//! Enables native tool-calling for Cursor, Claude Desktop, Antigravity IDE, Windsurf, Zed,
//! OpenCode, Command Code, and any MCP-compliant AI agent over stdio (JSON-RPC 2.0).

use crate::client::JevClient;
use crate::gates::{
    modulate_reasoning_effort_full, route_model_tier, should_abort_trajectory,
    should_nudge_continuation, triage_test_failure, verify_step_completion,
};
use serde_json::{json, Value};
use tokio::io::{AsyncBufReadExt, AsyncWriteExt, BufReader};

pub const PROTOCOL_VERSION: &str = "2024-11-05";
pub const SERVER_NAME: &str = "jev-harness";

pub fn tools_manifest() -> Value {
    let annotations = json!({
        "readOnlyHint": true,
        "destructiveHint": false,
        "idempotentHint": true,
        "openWorldHint": false
    });

    json!([
        {
            "name": "jev_triage_test_failure",
            "title": "Triage Test Failure",
            "description": "Triages test failure traceback, compilation error, or runtime exception using Jev System One non-autoregressive decision classification (70-300ms, zero LLM generation). Detects missing environment packages, flaky transient glitches, or deep logic defects.\n\nUse when: An agent encounters a test failure, traceback, compiler error (e.g. TS2307, ModuleNotFoundError, E0463), or needs to decide whether to invoke a frontier LLM.\nDo NOT use when: Tests pass, or for general code review or feature generation.\n\nReturns: JSON object with 'category' (env_missing, flaky_transient, deep_logic, no_failure), 'skip_llm' (boolean: true if resolvable deterministically without frontier LLM), and 'action_recommendation' (string with concrete recovery action).",
            "annotations": annotations,
            "inputSchema": {
                "type": "object",
                "properties": {
                    "failure_log": {
                        "type": "string",
                        "description": "Raw test failure output, stack trace, or compiler error log."
                    },
                    "test_command": {
                        "type": "string",
                        "description": "Optional test command that was executed (e.g. 'pytest tests/', 'npm test')."
                    }
                },
                "required": ["failure_log"]
            }
        },
        {
            "name": "jev_check_abort",
            "title": "Check Trajectory Abort",
            "description": "Guards against doom loops, repetitive circular retries, dead-ends, and destructive refactoring before burning frontier reasoning tokens. Evaluates the agent's proposed plan against recent attempt history.\n\nUse when: An agent is about to retry a failed step, execute a code edit after previous failed attempts, or before embarking on a potentially circular fix.\nDo NOT use when: Making the first attempt on a fresh task with no prior failure history.\n\nReturns: JSON object with 'should_abort' (boolean: true if the trajectory is stuck in a circular loop), 'abort_probability' (number: 0.0 to 1.0), 'action' (string: PROCEED, HALT, PIVOT), and 'reasoning_summary' (string explaining the decision).",
            "annotations": annotations,
            "inputSchema": {
                "type": "object",
                "properties": {
                    "proposed_step": {
                        "type": "string",
                        "description": "The next proposed plan, code modification, or architectural direction."
                    },
                    "recent_attempts_summary": {
                        "type": "string",
                        "description": "Summary of previous failed attempts, errors encountered, or circular patterns."
                    }
                },
                "required": ["proposed_step"]
            }
        },
        {
            "name": "jev_route_task",
            "title": "Route Task Model Tier",
            "description": "Routes a programming task to the minimal sufficient model tier (deterministic script, lightweight flash model, or heavy frontier reasoning model) to minimize latency and token expenditure.\n\nUse when: Starting a new task, refactoring step, or bug fix to choose between lightweight models and expensive reasoning frontier models.\nDo NOT use when: Diagnosing test execution tracebacks (use jev_triage_test_failure instead).\n\nReturns: JSON object with 'selected_tier' (string: deterministic, lightweight, heavy), 'complexity_score' (number: 1.0 to 5.0), 'recommended_model' (string), and 'rationale' (string).",
            "annotations": annotations,
            "inputSchema": {
                "type": "object",
                "properties": {
                    "task_description": {
                        "type": "string",
                        "description": "Clear description of the task, bug to fix, or feature to implement."
                    }
                },
                "required": ["task_description"]
            }
        },
        {
            "name": "jev_verify_completion",
            "title": "Verify Step Completion",
            "description": "Calibrates step completion against acceptance criteria using typed rubric scoring. Evaluates whether produced evidence proves the task is finished without running redundant review loops.\n\nUse when: An agent believes a task or milestone is complete and wants to verify acceptance criteria before concluding.\nDo NOT use when: Work is still underway or tests are actively failing.\n\nReturns: JSON object with 'is_verified' (boolean: true if acceptance criteria are satisfied with proof), 'satisfaction_probability' (number: 0.0 to 1.0), 'rigor_score' (number: 1.0 to 4.0), 'needs_rework' (boolean), and 'confidence' (number: 0.0 to 1.0).",
            "annotations": annotations,
            "inputSchema": {
                "type": "object",
                "properties": {
                    "acceptance_criteria": {
                        "type": "string",
                        "description": "Explicit requirements, constraints, or definition of done."
                    },
                    "produced_output": {
                        "type": "string",
                        "description": "The evidence, test results, code diff, or output produced."
                    }
                },
                "required": ["acceptance_criteria", "produced_output"]
            }
        },
        {
            "name": "jev_modulate_reasoning_effort",
            "title": "Modulate Reasoning Effort",
            "description": "Dynamically modulates reasoning effort (low, medium, high, etc.) and generation stability lease steps for the immediate LLM call. Maps provider-specific parameters for OpenAI (GPT-6 Astra/o3), DeepSeek (V4.1-Flash/R1), Qwen (3.8 Max), Anthropic (Claude Fable 5.1), and Gemini (3.8 Thinking) to prevent reasoning token waste.\n\nUse when: Preparing a prompt or tool call for a reasoning-capable LLM to calibrate thinking effort according to task complexity.\nDo NOT use when: Calling standard non-reasoning models or local deterministic scripts.\n\nReturns: JSON object with 'effort' (string), 'provider' (string), 'provider_params' (object with provider-native kwargs), 'is_reasoning_supported' (boolean), 'cache_safe_recommendation' (string), and 'lease_steps' (integer).",
            "annotations": annotations,
            "inputSchema": {
                "type": "object",
                "properties": {
                    "context": {
                        "type": "string",
                        "description": "The command, prompt, or next step to evaluate."
                    },
                    "provider": {
                        "type": "string",
                        "enum": ["openai", "deepseek", "qwen", "anthropic", "gemini", "kimi", "mimo"],
                        "default": "openai",
                        "description": "Target provider dialect (openai, deepseek, qwen, anthropic, gemini, kimi, mimo). Default: openai."
                    },
                    "model": {
                        "type": "string",
                        "description": "Optional model identifier to check for direct non-reasoning compatibility."
                    },
                    "session_context_tokens": {
                        "type": "integer",
                        "minimum": 0,
                        "default": 0,
                        "description": "Optional active prompt tokens in session context to evaluate prompt cache risk."
                    },
                    "supported_efforts": {
                        "type": "array",
                        "items": { "type": "string" },
                        "description": "Optional list of supported effort levels (e.g. ['none', 'minimal', 'low', 'medium', 'high', 'xhigh', 'max', 'ultra'])."
                    },
                    "max_lease_steps": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 50,
                        "default": 10,
                        "description": "Optional upper bound for generation stability lease steps (default: 10)."
                    }
                },
                "required": ["context"]
            }
        },
        {
            "name": "jev_evaluate_nudge",
            "title": "Evaluate Continuation Nudge",
            "description": "Evaluates whether an autonomous agent paused prematurely with unfinished work or unverified changes (covering workflow phases: research, ask, plan, execute, verify, complete). Vetoes nudges when waiting on user input or when repeated nudges make no progress.\n\nUse when: A background worker or agent loop stops and you need to determine if it should be nudged to continue autonomously.\nDo NOT use when: The agent explicitly requested user confirmation or required credentials.\n\nReturns: JSON object with 'should_nudge' (boolean), 'workflow_phase' (string: research, ask, plan, execute, verify, complete), 'action' (string: NUDGE, WAIT, STOP), and 'confidence' (number: 0.0 to 1.0).",
            "annotations": annotations,
            "inputSchema": {
                "type": "object",
                "properties": {
                    "transcript_tail": {
                        "type": "string",
                        "description": "Recent agent transcript tail or turn output."
                    },
                    "previous_nudge_summary": {
                        "type": "string",
                        "description": "Optional summary of the previous nudge to check if real progress was made."
                    },
                    "threshold": {
                        "type": "number",
                        "minimum": 0.0,
                        "maximum": 1.0,
                        "default": 0.5,
                        "description": "Optional probability threshold for nudge/waiting/progress (default: 0.5)."
                    }
                },
                "required": ["transcript_tail"]
            }
        }
    ])
}

pub async fn process_message(line: &str, client: &JevClient) -> Option<Value> {
    let trimmed = line.trim();
    if trimmed.is_empty() {
        return None;
    }

    let parsed: Value = match serde_json::from_str(trimmed) {
        Ok(v) => v,
        Err(_) => {
            return Some(json!({
                "jsonrpc": "2.0",
                "id": Value::Null,
                "error": { "code": -32700, "message": "Parse error" }
            }));
        }
    };

    let req_id = parsed.get("id").cloned();
    let method = parsed.get("method").and_then(|m| m.as_str()).unwrap_or("");
    let params = parsed.get("params").cloned().unwrap_or(Value::Null);

    // Notifications without an ID do not expect responses
    if req_id.is_none() && (method.starts_with("notifications/") || method == "initialized") {
        return None;
    }

    match method {
        "initialize" => {
            let id = req_id.unwrap_or(Value::Null);
            Some(json!({
                "jsonrpc": "2.0",
                "id": id,
                "result": {
                    "protocolVersion": PROTOCOL_VERSION,
                    "serverInfo": {
                        "name": SERVER_NAME,
                        "version": env!("CARGO_PKG_VERSION")
                    },
                    "capabilities": {
                        "tools": {
                            "listChanged": false
                        }
                    }
                }
            }))
        }
        "ping" => {
            let id = req_id.unwrap_or(Value::Null);
            Some(json!({
                "jsonrpc": "2.0",
                "id": id,
                "result": {}
            }))
        }
        "tools/list" => {
            let id = req_id.unwrap_or(Value::Null);
            Some(json!({
                "jsonrpc": "2.0",
                "id": id,
                "result": {
                    "tools": tools_manifest()
                }
            }))
        }
        "tools/call" => {
            let id = req_id.unwrap_or(Value::Null);
            let tool_name = params.get("name").and_then(|n| n.as_str()).unwrap_or("");
            let arguments = params.get("arguments").cloned().unwrap_or(json!({}));

            let result_val: Result<Value, String> = match tool_name {
                "jev_triage_test_failure" => {
                    let log = arguments
                        .get("failure_log")
                        .and_then(|v| v.as_str())
                        .unwrap_or("");
                    if log.trim().is_empty() {
                        return Some(json!({
                            "jsonrpc": "2.0",
                            "id": id,
                            "error": { "code": -32602, "message": "Missing required argument 'failure_log'" }
                        }));
                    }
                    triage_test_failure(log, Some(client))
                        .await
                        .map(|r| serde_json::to_value(&r).unwrap_or(json!({})))
                        .map_err(|e| e.to_string())
                }
                "jev_check_abort" | "jev_abort_check" => {
                    let step = arguments
                        .get("proposed_step")
                        .and_then(|v| v.as_str())
                        .unwrap_or("");
                    if step.trim().is_empty() {
                        return Some(json!({
                            "jsonrpc": "2.0",
                            "id": id,
                            "error": { "code": -32602, "message": "Missing required argument 'proposed_step'" }
                        }));
                    }
                    let history = arguments
                        .get("recent_attempts_summary")
                        .and_then(|v| v.as_str())
                        .unwrap_or("");
                    should_abort_trajectory(step, history, Some(client))
                        .await
                        .map(|r| serde_json::to_value(&r).unwrap_or(json!({})))
                        .map_err(|e| e.to_string())
                }
                "jev_route_task" => {
                    let task = arguments
                        .get("task_description")
                        .and_then(|v| v.as_str())
                        .unwrap_or("");
                    if task.trim().is_empty() {
                        return Some(json!({
                            "jsonrpc": "2.0",
                            "id": id,
                            "error": { "code": -32602, "message": "Missing required argument 'task_description'" }
                        }));
                    }
                    route_model_tier(task, Some(client))
                        .await
                        .map(|r| serde_json::to_value(&r).unwrap_or(json!({})))
                        .map_err(|e| e.to_string())
                }
                "jev_verify_completion" => {
                    let criteria = arguments
                        .get("acceptance_criteria")
                        .and_then(|v| v.as_str())
                        .unwrap_or("");
                    let output = arguments
                        .get("produced_output")
                        .and_then(|v| v.as_str())
                        .unwrap_or("");
                    if criteria.trim().is_empty() || output.trim().is_empty() {
                        return Some(json!({
                            "jsonrpc": "2.0",
                            "id": id,
                            "error": { "code": -32602, "message": "Missing required arguments 'acceptance_criteria' or 'produced_output'" }
                        }));
                    }
                    verify_step_completion(criteria, output, Some(client))
                        .await
                        .map(|r| serde_json::to_value(&r).unwrap_or(json!({})))
                        .map_err(|e| e.to_string())
                }
                "jev_modulate_reasoning_effort" => {
                    let context = arguments
                        .get("context")
                        .and_then(|v| v.as_str())
                        .unwrap_or("");
                    if context.trim().is_empty() {
                        return Some(json!({
                            "jsonrpc": "2.0",
                            "id": id,
                            "error": { "code": -32602, "message": "Missing required argument 'context'" }
                        }));
                    }
                    let provider = arguments
                        .get("provider")
                        .and_then(|v| v.as_str())
                        .unwrap_or("openai");
                    let model = arguments.get("model").and_then(|v| v.as_str());
                    let session_tokens = arguments
                        .get("session_context_tokens")
                        .and_then(|v| v.as_u64())
                        .unwrap_or(0) as usize;
                    let max_lease = arguments
                        .get("max_lease_steps")
                        .and_then(|v| v.as_u64())
                        .unwrap_or(10) as u32;

                    let supported_efforts_vec: Option<Vec<&str>> = arguments
                        .get("supported_efforts")
                        .and_then(|v| v.as_array())
                        .map(|arr| arr.iter().filter_map(|x| x.as_str()).collect());

                    modulate_reasoning_effort_full(
                        context,
                        provider,
                        model,
                        session_tokens,
                        supported_efforts_vec.as_deref(),
                        max_lease,
                        Some(client),
                    )
                    .await
                    .map(|r| serde_json::to_value(&r).unwrap_or(json!({})))
                    .map_err(|e| e.to_string())
                }
                "jev_evaluate_nudge" | "jev_should_nudge_continuation" => {
                    let transcript = arguments
                        .get("transcript_tail")
                        .and_then(|v| v.as_str())
                        .unwrap_or("");
                    if transcript.trim().is_empty() {
                        return Some(json!({
                            "jsonrpc": "2.0",
                            "id": id,
                            "error": { "code": -32602, "message": "Missing required argument 'transcript_tail'" }
                        }));
                    }
                    let prev_nudge = arguments
                        .get("previous_nudge_summary")
                        .and_then(|v| v.as_str())
                        .unwrap_or("");
                    let threshold = arguments
                        .get("threshold")
                        .and_then(|v| v.as_f64())
                        .unwrap_or(0.5);

                    should_nudge_continuation(transcript, prev_nudge, threshold, Some(client))
                        .await
                        .map(|r| serde_json::to_value(&r).unwrap_or(json!({})))
                        .map_err(|e| e.to_string())
                }
                _ => {
                    return Some(json!({
                        "jsonrpc": "2.0",
                        "id": id,
                        "error": { "code": -32601, "message": format!("Method not found: {}", tool_name) }
                    }));
                }
            };

            match result_val {
                Ok(val) => {
                    let formatted_text =
                        serde_json::to_string_pretty(&val).unwrap_or_else(|_| val.to_string());
                    Some(json!({
                        "jsonrpc": "2.0",
                        "id": id,
                        "result": {
                            "content": [
                                {
                                    "type": "text",
                                    "text": formatted_text
                                }
                            ],
                            "isError": false
                        }
                    }))
                }
                Err(err_msg) => Some(json!({
                    "jsonrpc": "2.0",
                    "id": id,
                    "result": {
                        "content": [
                            {
                                "type": "text",
                                "text": format!("Error executing {}: {}", tool_name, err_msg)
                            }
                        ],
                        "isError": true
                    }
                })),
            }
        }
        _ => req_id.map(|id| {
            json!({
                "jsonrpc": "2.0",
                "id": id,
                "error": { "code": -32601, "message": format!("Method not found: {}", method) }
            })
        }),
    }
}

pub async fn run_mcp_server(
    client: Option<JevClient>,
) -> Result<(), Box<dyn std::error::Error + Send + Sync>> {
    let active_client = client.unwrap_or_default();
    let stdin = tokio::io::stdin();
    let mut reader = BufReader::new(stdin).lines();
    let mut stdout = tokio::io::stdout();

    while let Ok(Some(line)) = reader.next_line().await {
        if let Some(resp) = process_message(&line, &active_client).await {
            let mut out_str = serde_json::to_string(&resp)?;
            out_str.push('\n');
            stdout.write_all(out_str.as_bytes()).await?;
            stdout.flush().await?;
        }
    }

    Ok(())
}
