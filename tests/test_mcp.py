"""
Tests for Model Context Protocol (MCP) server stdio JSON-RPC 2.0 interface.
"""

import json
from pathlib import Path
import sys
import unittest

_PKG_ROOT = str(Path(__file__).resolve().parents[1] / "src")
if _PKG_ROOT not in sys.path:
    sys.path.insert(0, _PKG_ROOT)

from jev_harness.client import JevClient
from jev_harness.mcp_server import process_message


class TestMCPServer(unittest.TestCase):
    def setUp(self):
        self.client = JevClient(force_mock=True)

    def test_mcp_initialize(self):
        req = json.dumps({
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {"protocolVersion": "2024-11-05"},
        })
        resp = process_message(req, self.client)
        self.assertIsNotNone(resp)
        self.assertEqual(resp["id"], 1)
        self.assertEqual(resp["result"]["serverInfo"]["name"], "jev-harness")
        self.assertIn("tools", resp["result"]["capabilities"])

    def test_mcp_tools_list(self):
        req = json.dumps({
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/list",
            "params": {},
        })
        resp = process_message(req, self.client)
        self.assertIsNotNone(resp)
        tools = resp["result"]["tools"]
        tool_names = [t["name"] for t in tools]
        self.assertIn("jev_triage_test_failure", tool_names)
        self.assertIn("jev_abort_check", tool_names)
        self.assertIn("jev_route_task", tool_names)
        self.assertIn("jev_verify_completion", tool_names)
        self.assertIn("jev_modulate_reasoning_effort", tool_names)

    def test_mcp_tools_call_triage(self):
        req = json.dumps({
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {
                "name": "jev_triage_test_failure",
                "arguments": {
                    "failure_log": "ModuleNotFoundError: No module named 'scipy'",
                },
            },
        })
        resp = process_message(req, self.client)
        self.assertIsNotNone(resp)
        self.assertFalse(resp["result"]["isError"])
        content = json.loads(resp["result"]["content"][0]["text"])
        self.assertEqual(content["category"], "env_missing")
        self.assertTrue(content["skip_llm"])
        # Contract parity: both snake_case keys must be present (matches the TS runtime).
        self.assertIn("action_recommendation", content)
        self.assertIn("recommendation", content)
        self.assertEqual(content["action_recommendation"], content["recommendation"])

    def test_mcp_tools_call_triage_green_run(self):
        req = json.dumps({
            "jsonrpc": "2.0",
            "id": 31,
            "method": "tools/call",
            "params": {
                "name": "jev_triage_test_failure",
                "arguments": {"failure_log": "Tests: 12 passed, 12 total"},
            },
        })
        resp = process_message(req, self.client)
        content = json.loads(resp["result"]["content"][0]["text"])
        self.assertEqual(content["category"], "no_failure")
        self.assertTrue(content["skip_llm"])

    def test_mcp_tools_call_abort(self):
        req = json.dumps({
            "jsonrpc": "2.0",
            "id": 4,
            "method": "tools/call",
            "params": {
                "name": "jev_abort_check",
                "arguments": {
                    "proposed_step": "Tentar novamente sem alterar nada",
                    "recent_attempts_summary": "Falha circular 3 vezes",
                },
            },
        })
        resp = process_message(req, self.client)
        self.assertIsNotNone(resp)
        content = json.loads(resp["result"]["content"][0]["text"])
        self.assertTrue(content["should_abort"])

    def test_mcp_unknown_tool(self):
        req = json.dumps({
            "jsonrpc": "2.0",
            "id": 5,
            "method": "tools/call",
            "params": {
                "name": "unknown_tool",
                "arguments": {},
            },
        })
        resp = process_message(req, self.client)
        self.assertIsNotNone(resp)
        self.assertIn("error", resp)
        self.assertEqual(resp["error"]["code"], -32601)

    def test_mcp_missing_required_arguments(self):
        req = json.dumps({
            "jsonrpc": "2.0",
            "id": 6,
            "method": "tools/call",
            "params": {
                "name": "jev_triage_test_failure",
                "arguments": {},
            },
        })
        resp = process_message(req, self.client)
        self.assertIsNotNone(resp)
        self.assertIn("error", resp)
        self.assertEqual(resp["error"]["code"], -32602)
        self.assertIn("required", resp["error"]["message"])

    def test_mcp_malformed_json(self):
        resp = process_message("{broken json", self.client)
        self.assertIsNotNone(resp)
        self.assertEqual(resp["error"]["code"], -32700)

    def test_mcp_ping(self):
        req = json.dumps({"jsonrpc": "2.0", "id": 10, "method": "ping"})
        resp = process_message(req, self.client)
        self.assertIsNotNone(resp)
        self.assertEqual(resp["result"], {})

    def test_mcp_notification_ignored(self):
        req = json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized"})
        resp = process_message(req, self.client)
        self.assertIsNone(resp)

    def test_mcp_tools_call_route(self):
        req = json.dumps({
            "jsonrpc": "2.0",
            "id": 11,
            "method": "tools/call",
            "params": {
                "name": "jev_route_task",
                "arguments": {"task_description": "Fix typo in docstring"},
            },
        })
        resp = process_message(req, self.client)
        self.assertIsNotNone(resp)
        content = json.loads(resp["result"]["content"][0]["text"])
        self.assertEqual(content["selected_tier"], "deterministic")

    def test_mcp_tools_call_verify(self):
        req = json.dumps({
            "jsonrpc": "2.0",
            "id": 12,
            "method": "tools/call",
            "params": {
                "name": "jev_verify_completion",
                "arguments": {
                    "acceptance_criteria": "All unit tests pass",
                    "produced_output": "All 35 tests passed OK with complete evidence",
                },
            },
        })
        resp = process_message(req, self.client)
        self.assertIsNotNone(resp)
        content = json.loads(resp["result"]["content"][0]["text"])
        self.assertTrue(content["is_verified"])

    def test_mcp_tools_call_reasoning_effort(self):
        req = json.dumps({
            "jsonrpc": "2.0",
            "id": 13,
            "method": "tools/call",
            "params": {
                "name": "jev_modulate_reasoning_effort",
                "arguments": {
                    "context": "git status e verificar arquivos",
                    "provider": "deepseek",
                },
            },
        })
        resp = process_message(req, self.client)
        self.assertIsNotNone(resp)
        content = json.loads(resp["result"]["content"][0]["text"])
        self.assertEqual(content["effort"], "low")
        self.assertEqual(content["provider"], "deepseek")
        self.assertIn("extra_body", content["provider_params"])
        self.assertEqual(content["provider_params"]["reasoning_effort"], "low")

    def test_mcp_tools_call_reasoning_effort_with_tokens(self):
        req = json.dumps({
            "jsonrpc": "2.0",
            "id": 14,
            "method": "tools/call",
            "params": {
                "name": "jev_modulate_reasoning_effort",
                "arguments": {
                    "context": "git status",
                    "provider": "openai",
                    "session_context_tokens": 45000,
                },
            },
        })
        resp = process_message(req, self.client)
        self.assertIsNotNone(resp)
        content = json.loads(resp["result"]["content"][0]["text"])
        self.assertIn("HIGH CACHE RISK", content["cache_safe_recommendation"])

    def test_mcp_run_server_loop(self):
        from io import StringIO
        from unittest.mock import patch
        from jev_harness.mcp_server import run_mcp_server

        req = json.dumps({"jsonrpc": "2.0", "id": 99, "method": "ping"}) + "\n"
        with patch("sys.stdin", StringIO(req)), patch("sys.stdout", new_callable=StringIO) as mock_out:
            run_mcp_server(client=self.client)
            output = mock_out.getvalue().strip()
            self.assertIn('"id": 99', output)

    def test_mcp_tools_call_nudge_continuation(self):
        req = json.dumps({
            "jsonrpc": "2.0",
            "id": 15,
            "method": "tools/call",
            "params": {
                "name": "jev_should_nudge_continuation",
                "arguments": {
                    "transcript_tail": "Modified client.py without running tests. Need to verify.",
                },
            },
        })
        resp = process_message(req, self.client)
        self.assertIsNotNone(resp)
        self.assertFalse(resp["result"]["isError"])
        content = json.loads(resp["result"]["content"][0]["text"])
        self.assertTrue(content["should_nudge"])
        self.assertEqual(content["workflow_phase"], "verify")


if __name__ == "__main__":
    unittest.main()
