# Host plugins (E2.2)

Two thin adapters that install the same behaviour in the hosts agents actually use. Neither
duplicates logic: both point at the canonical rules in
[`docs/AGENT_INTEGRATION_GUIDE.md`](../docs/AGENT_INTEGRATION_GUIDE.md) and register the MCP server
that already exists.

| Host | Bundle | What it adds |
| :--- | :--- | :--- |
| **Claude Code** | [`claude-code/`](claude-code/) | A plugin manifest (`.claude-plugin/plugin.json`), the skill (`skills/jev-harness/SKILL.md`) and MCP registration (`.mcp.json`) |
| **Codex / OpenCode** | [`codex/`](codex/) | The same skill content as a standalone bundle for hosts that consume skills rather than plugins |

## Install: Claude Code

```bash
# 1. From the marketplace form (recommended once published)
claude plugin marketplace add ismaelsoilet/jev-harness
claude plugin install jev-harness

# 2. Or point Claude Code at this directory directly
claude --plugin-dir /path/to/jev-harness/plugins/claude-code
```

The bundled `.mcp.json` registers the stdio server (`npx -y @ismaelsoilet/jev-harness mcp`), so the
`jev_*` tools appear alongside the skill.

## Install: Codex / OpenCode

```bash
mkdir -p .opencode/skills && cp -r /path/to/jev-harness/plugins/codex/skills/jev-harness .opencode/skills/
```

For Codex, copy the same `skills/jev-harness/` directory into the skills path your build reads.

## Manual verification (documented, not automated end to end)

The bundles are validated structurally in the test suite (`tests/test_plugins.py`): manifests
parse, the skill frontmatter is present, the MCP command is the published one, and nothing
re-implements gate logic. A clean-host install cannot be automated from this repository, so the
human check is:

1. `jev-harness doctor` → reports the CLI, credentials, model origin, state permissions and the
   receipts/cache status (the `git_hook` check only applies inside a repository).
2. Install the bundle as above, start the host and ask it to triage a known-red log
   (`AssertionError: assert 4 == 5`): the skill should lead it to `test-gate`, and the answer must
   be `deep_logic` with exit `1`.
3. Ask it to triage a green log (`5 passed in 0.12s`): no escalation, exit `0`, zero API calls.
4. Confirm the MCP tools are listed (`tools/list`) when the host supports MCP.
