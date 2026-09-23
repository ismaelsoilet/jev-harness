"""
Model Context Protocol (MCP) Server for Jev System One.
Enables native tool-calling for Cursor, Claude Desktop, Antigravity IDE, Windsurf, Zed,
OpenCode, Command Code, and any MCP-compliant AI agent over stdio (JSON-RPC 2.0).

Zero external dependencies (pure Python standard library).
"""

from __future__ import annotations

import json
from pathlib import Path
import sys
from typing import Any, Dict, List, Optional

try:
    from . import __version__
    from .client import JevClient
    from .gates import (
        modulate_reasoning_effort,
        route_model_tier,
        should_abort_trajectory,
        should_nudge_continuation,
        triage_test_failure,
        verify_step_completion,
    )
except (ImportError, ValueError):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from jev_harness import __version__
    from jev_harness.client import JevClient
    from jev_harness.gates import (
        modulate_reasoning_effort,
        route_model_tier,
        should_abort_trajectory,
        should_nudge_continuation,
        triage_test_failure,
        verify_step_completion,
    )

PROTOCOL_VERSION = "2024-11-05"
SERVER_NAME = "jev-harness"
SERVER_VERSION = __version__


TOOLS_MANIFEST: List[Dict[str, Any]] = [
    {
        "name": "jev_triage_test_failure",
        "description": (
            "Triages test traceback, compile error, or runtime failure using Jev System One (70-300ms, zero-generation). "
            "Returns root cause category, skip_llm flag (true if resolvable deterministically without frontier LLM), "
            "and immediate action recommendation."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "failure_log": {
                    "type": "string",
                    "description": "Raw test failure output, stack trace, or compiler error log.",
                }
            },
            "required": ["failure_log"],
        },
    },
    {
        "name": "jev_abort_check",
        "description": (
            "Guards against doom loops, dead-ends, circular retries, and destructive refactors. "
            "Evaluates proposed plan against recent attempt history before burning tokens."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "proposed_step": {
                    "type": "string",
                    "description": "The next proposed plan, code modification, or architectural direction.",
                },
                "recent_attempts_summary": {
                    "type": "string",
                    "description": "Summary of previous failed attempts, errors encountered, or circular patterns.",
                },
            },
            "required": ["proposed_step"],
        },
    },
    {
        "name": "jev_route_task",
        "description": (
            "Routes programming task to the minimal sufficient model tier (deterministic script, "
            "lightweight fast flash model, or heavy frontier reasoning model) to optimize cost and latency."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "task_description": {
                    "type": "string",
                    "description": "Clear description of the task, bug to fix, or feature to implement.",
                }
            },
            "required": ["task_description"],
        },
    },
    {
        "name": "jev_verify_completion",
        "description": (
            "Calibrates step completion against acceptance criteria using typed rubric scoring. "
            "Checks if evidence is sufficient to declare done without launching expensive extra review loops."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "acceptance_criteria": {
                    "type": "string",
                    "description": "Explicit requirements, constraints, or definition of done.",
                },
                "produced_output": {
                    "type": "string",
                    "description": "The evidence, test results, code diff, or output produced.",
                },
            },
            "required": ["acceptance_criteria", "produced_output"],
        },
    },
    {
        "name": "jev_modulate_reasoning_effort",
        "description": (
            "Dynamically modulates reasoning effort (low, medium, high, etc.) and stability lease steps for the immediate generation step. "
            "Maps exact parameters for OpenAI (GPT-6 Astra/o3), DeepSeek (V4.1-Flash/R1), Qwen (3.8 Max), "
            "Anthropic (Claude Fable 5.1), and Gemini (3.8 Thinking). Eliminates reasoning token waste "
            "and cuts multi-minute delays on mechanical tool calls."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "context": {
                    "type": "string",
                    "description": "The command, prompt, or next step to evaluate.",
                },
                "provider": {
                    "type": "string",
                    "description": "Target provider (openai, deepseek, qwen, anthropic, gemini, kimi, mimo). Default: openai.",
                },
                "model": {
                    "type": "string",
                    "description": "Optional model identifier to check for direct non-reasoning compatibility.",
                },
                "session_context_tokens": {
                    "type": "integer",
                    "description": "Optional active prompt tokens in session context to evaluate prompt cache risk.",
                },
                "supported_efforts": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Optional list of supported effort levels (e.g. ['none', 'minimal', 'low', 'medium', 'high', 'xhigh', 'max', 'ultra']).",
                },
                "max_lease_steps": {
                    "type": "integer",
                    "description": "Optional upper bound for generation stability lease steps (default: 10).",
                },
            },
            "required": ["context"],
        },
    },
    {
        "name": "jev_should_nudge_continuation",
        "description": (
            "Evaluates whether an autonomous agent paused prematurely with unfinished work or unverified changes "
            "(Workflow phases: research, ask, plan, execute, verify, complete + CommandCode Jev Nudge protocol). "
            "Vetoes nudges when waiting on user permission/input or when the previous nudge produced no progress."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "transcript_tail": {
                    "type": "string",
                    "description": "Recent agent transcript tail or turn output.",
                },
                "previous_nudge_summary": {
                    "type": "string",
                    "description": "Optional summary of the previous nudge to check if real progress was made.",
                },
                "threshold": {
                    "type": "number",
                    "description": "Optional probability threshold for nudge/waiting/progress (default: 0.5).",
                },
            },
            "required": ["transcript_tail"],
        },
    },
]


def handle_initialize(req_id: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "jsonrpc": "2.0",
        "id": req_id,
        "result": {
            "protocolVersion": PROTOCOL_VERSION,
            "serverInfo": {
                "name": SERVER_NAME,
                "version": SERVER_VERSION,
            },
            "capabilities": {
                "tools": {
                    "listChanged": False,
                }
            },
        },
    }


def handle_tools_list(req_id: Any) -> Dict[str, Any]:
    return {
        "jsonrpc": "2.0",
        "id": req_id,
        "result": {
            "tools": TOOLS_MANIFEST,
        },
    }


def handle_tools_call(req_id: Any, params: Dict[str, Any], client: JevClient) -> Dict[str, Any]:
    tool_name = params.get("name", "")
    args = params.get("arguments", {})

    try:
        if tool_name == "jev_triage_test_failure":
            log_text = args.get("failure_log", "")
            if not log_text or not str(log_text).strip():
                return {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "error": {
                        "code": -32602,
                        "message": "Invalid params: 'failure_log' is required and cannot be empty.",
                    },
                }
            res = triage_test_failure(str(log_text), client=client)
            text_content = json.dumps(
                {
                    "category": res.category,
                    "uncertainty": getattr(res, "uncertainty", None),
                    "recovery": getattr(res, "recovery", None),
                    "confidence": res.confidence,
                    "skip_llm": res.skip_llm,
                    "skip_llm_prob": res.skip_llm_prob,
                    "severity_score": res.severity_score,
                    "action_recommendation": res.action_recommendation,
                    "recommendation": res.action_recommendation,
                    "is_mock": res.is_mock,
                    "degraded_reason": getattr(res, "degraded_reason", ""),
                },
                indent=2,
            )

        elif tool_name == "jev_abort_check":
            step = args.get("proposed_step", "")
            if not step or not str(step).strip():
                return {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "error": {
                        "code": -32602,
                        "message": "Invalid params: 'proposed_step' is required and cannot be empty.",
                    },
                }
            hist = args.get("recent_attempts_summary", "")
            res = should_abort_trajectory(str(step), recent_attempts_summary=str(hist), client=client)
            text_content = json.dumps(
                {
                    "should_abort": res.should_abort,
                    "uncertainty": getattr(res, "uncertainty", None),
                    "abort_probability": res.abort_probability,
                    "action": res.action,
                    "viability_score": res.viability_score,
                    "reasoning_summary": res.reasoning_summary,
                    "summary": res.reasoning_summary,
                    "is_mock": res.is_mock,
                    "degraded_reason": getattr(res, "degraded_reason", ""),
                },
                indent=2,
            )

        elif tool_name == "jev_route_task":
            task = args.get("task_description", "")
            if not task or not str(task).strip():
                return {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "error": {
                        "code": -32602,
                        "message": "Invalid params: 'task_description' is required and cannot be empty.",
                    },
                }
            res = route_model_tier(str(task), client=client)
            text_content = json.dumps(
                {
                    "selected_tier": res.selected_tier,
                    "uncertainty": getattr(res, "uncertainty", None),
                    "confidence": res.confidence,
                    "complexity_score": res.complexity_score,
                    "recommended_model": res.recommended_model,
                    "rationale": res.rationale,
                    "is_mock": res.is_mock,
                    "degraded_reason": getattr(res, "degraded_reason", ""),
                },
                indent=2,
            )

        elif tool_name == "jev_verify_completion":
            crit = args.get("acceptance_criteria", "")
            out = args.get("produced_output", "")
            if not crit or not str(crit).strip() or not out or not str(out).strip():
                return {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "error": {
                        "code": -32602,
                        "message": "Invalid params: 'acceptance_criteria' and 'produced_output' are both required.",
                    },
                }
            res = verify_step_completion(str(crit), str(out), client=client)
            text_content = json.dumps(
                {
                    "is_verified": res.is_verified,
                    "uncertainty": getattr(res, "uncertainty", None),
                    "satisfaction_probability": res.satisfaction_probability,
                    "rigor_score": res.rigor_score,
                    "confidence": res.confidence,
                    "needs_rework": res.needs_rework,
                    "is_mock": res.is_mock,
                    "degraded_reason": getattr(res, "degraded_reason", ""),
                },
                indent=2,
            )

        elif tool_name == "jev_modulate_reasoning_effort":
            ctx = args.get("context", "")
            if not ctx or not str(ctx).strip():
                return {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "error": {
                        "code": -32602,
                        "message": "Invalid params: 'context' is required and cannot be empty.",
                    },
                }
            prov = args.get("provider", "openai")
            mdl = args.get("model", None)
            tokens = int(args.get("session_context_tokens", 0) or 0)
            supported = args.get("supported_efforts", None)
            max_lease = int(args.get("max_lease_steps", 10) or 10)
            res = modulate_reasoning_effort(
                str(ctx),
                provider=str(prov),
                model=mdl,
                session_context_tokens=tokens,
                supported_efforts=supported,
                max_lease_steps=max_lease,
                client=client,
            )
            text_content = json.dumps(
                {
                    "effort": res.effort,
                    "uncertainty": getattr(res, "uncertainty", None),
                    "confidence": res.confidence,
                    "complexity_score": res.complexity_score,
                    "rationale": res.rationale,
                    "provider": res.provider,
                    "provider_params": res.provider_params,
                    "is_reasoning_supported": res.is_reasoning_supported,
                    "cache_safe_recommendation": res.cache_safe_recommendation,
                    "lease_steps": res.lease_steps,
                    "is_mock": res.is_mock,
                    "degraded_reason": getattr(res, "degraded_reason", ""),
                },
                indent=2,
            )

        elif tool_name == "jev_should_nudge_continuation":
            tail = args.get("transcript_tail", "")
            if not tail or not str(tail).strip():
                return {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "error": {
                        "code": -32602,
                        "message": "Invalid params: 'transcript_tail' is required and cannot be empty.",
                    },
                }
            prev = args.get("previous_nudge_summary", "") or ""
            thresh = float(args.get("threshold", 0.5) if args.get("threshold") is not None else 0.5)
            res = should_nudge_continuation(
                transcript_tail=str(tail),
                previous_nudge_summary=str(prev),
                threshold=thresh,
                client=client,
            )
            text_content = json.dumps(
                {
                    "should_nudge": res.should_nudge,
                    "uncertainty": getattr(res, "uncertainty", None),
                    "nudge_probability": res.nudge_probability,
                    "waiting_probability": res.waiting_probability,
                    "progress_probability": res.progress_probability,
                    "workflow_phase": res.workflow_phase,
                    "suggested_nudge_prompt": res.suggested_nudge_prompt,
                    "rationale": res.rationale,
                    "is_mock": res.is_mock,
                    "degraded_reason": getattr(res, "degraded_reason", ""),
                },
                indent=2,
            )
        else:
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {
                    "code": -32601,
                    "message": f"Unknown tool: {tool_name}",
                },
            }

        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "content": [
                    {
                        "type": "text",
                        "text": text_content,
                    }
                ],
                "isError": False,
            },
        }
    except Exception as exc:
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "content": [
                    {
                        "type": "text",
                        "text": f"Error executing {tool_name}: {exc}",
                    }
                ],
                "isError": True,
            },
        }


def process_message(line: str, client: JevClient) -> Optional[Dict[str, Any]]:
    line = line.strip()
    if not line:
        return None

    try:
        msg = json.loads(line)
    except json.JSONDecodeError:
        return {
            "jsonrpc": "2.0",
            "id": None,
            "error": {"code": -32700, "message": "Parse error"},
        }

    method = msg.get("method")
    req_id = msg.get("id")
    params = msg.get("params", {})

    # Handle notifications (no id)
    if method == "notifications/initialized":
        return None
    if method == "ping":
        return {"jsonrpc": "2.0", "id": req_id, "result": {}}

    if method == "initialize":
        return handle_initialize(req_id, params)
    elif method == "tools/list":
        return handle_tools_list(req_id)
    elif method == "tools/call":
        return handle_tools_call(req_id, params, client)
    else:
        if req_id is not None:
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {
                    "code": -32601,
                    "message": f"Method not found: {method}",
                },
            }
        return None


def run_mcp_server(client: Optional[JevClient] = None) -> None:
    """Runs the stdio MCP server loop until stdin closes."""
    active_client = client or JevClient()
    for raw_line in sys.stdin:
        response = process_message(raw_line, active_client)
        if response is not None:
            sys.stdout.write(json.dumps(response) + "\n")
            sys.stdout.flush()


def main() -> None:
    run_mcp_server()


if __name__ == "__main__":
    main()
