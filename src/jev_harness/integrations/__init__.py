"""
Integration configurations and presets for leading AI coding environments:
- OpenCode
- Command Code
- Cursor
- Claude Desktop
- Antigravity IDE
- Windsurf & Zed
- Git / Husky / Pre-commit
"""

OPENCODE_CONFIG_SNIPPET = """# .opencode/config.json or agent tool registration
{
  "tools": [
    {
      "name": "jev_triage",
      "command": "jev-harness test-gate --log ${error_log} --json"
    },
    {
      "name": "jev_abort_check",
      "command": "jev-harness abort-check --plan '${plan}' --history '${history}' --json"
    }
  ]
}
"""

CURSOR_MCP_SNIPPET = """// .cursor/mcp.json or ~/.cursor/mcp.json
{
  "mcpServers": {
    "jev-harness": {
      "command": "jev-mcp",
      "args": []
    }
  }
}
"""

CLAUDE_DESKTOP_MCP_SNIPPET = """// claude_desktop_config.json
{
  "mcpServers": {
    "jev-harness": {
      "command": "jev-mcp",
      "args": []
    }
  }
}
"""

ANTIGRAVITY_HOOK_SNIPPET = """// ~/.gemini/config/hooks.json or .agents/hooks.json
{
  "jev-token-guard": {
    "PreInvocation": [
      {
        "type": "command",
        "command": "echo '{\\"injectSteps\\": [{\\"ephemeralMessage\\": \\"[JEV ACTIVE] If tests fail, pipe error to jev-harness test-gate. If skip_llm=true, fix deterministically without burning frontier LLM tokens.\\"}]}'"
      }
    ]
  }
}
"""
