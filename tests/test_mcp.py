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


if __name__ == "__main__":
    unittest.main()
