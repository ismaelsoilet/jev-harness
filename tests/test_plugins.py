"""E2.2 — host plugins: manifests are valid, and the bundles stay thin adapters.

A plugin that re-implements the gates would drift from the canonical rules, so the tests check
that the bundles *point at* the guide rather than restating (or worse, reimplementing) it.
"""
import json
import re
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
PLUGINS = REPO_ROOT / "plugins"
MANIFEST = PLUGINS / "claude-code" / ".claude-plugin" / "plugin.json"
MCP_CONFIG = PLUGINS / "claude-code" / ".mcp.json"
SKILLS = {
    "claude-code": PLUGINS / "claude-code" / "skills" / "jev-harness" / "SKILL.md",
    "codex": PLUGINS / "codex" / "skills" / "jev-harness" / "SKILL.md",
}
GUIDE_URL = "docs/AGENT_INTEGRATION_GUIDE.md"


def frontmatter(text: str) -> dict:
    match = re.match(r"^---\n(.*?)\n---\n", text, re.DOTALL)
    if not match:
        return {}
    fields = {}
    for line in match.group(1).splitlines():
        key, _, value = line.partition(":")
        fields[key.strip()] = value.strip()
    return fields


class TestClaudeCodeBundle(unittest.TestCase):
    def test_manifest_is_valid_and_version_synced(self):
        self.assertTrue(MANIFEST.is_file(), "the plugin manifest must exist")
        data = json.loads(MANIFEST.read_text(encoding="utf-8"))
        for field in ("name", "version", "description", "author", "license", "homepage"):
            with self.subTest(field):
                self.assertIn(field, data)
        self.assertEqual(data["name"], "jev-harness")
        self.assertEqual(data["license"], "MIT")

        pyproject = (REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")
        package_version = re.search(r'^version = "([^"]+)"', pyproject, re.MULTILINE).group(1)
        self.assertEqual(data["version"], package_version, "the plugin ships with the package version")

    def test_mcp_registration_uses_the_published_command(self):
        config = json.loads(MCP_CONFIG.read_text(encoding="utf-8"))
        server = config["mcpServers"]["jev-harness"]
        self.assertEqual(server["command"], "npx")
        joined = " ".join(server["args"])
        self.assertIn("@ismaelsoilet/jev-harness", joined)
        self.assertIn("mcp", joined)


class TestSkillBundles(unittest.TestCase):
    def test_frontmatter_names_the_skill_and_describes_the_trigger(self):
        for host, path in SKILLS.items():
            with self.subTest(host):
                self.assertTrue(path.is_file(), f"{host} bundle must ship a SKILL.md")
                fields = frontmatter(path.read_text(encoding="utf-8"))
                self.assertEqual(fields.get("name"), "jev-harness")
                description = fields.get("description", "")
                self.assertGreater(len(description), 60, "the description is the trigger: be specific")
                self.assertIn("offline", description.lower())

    def test_bundles_point_at_the_canonical_rules_instead_of_duplicating_them(self):
        for host, path in SKILLS.items():
            with self.subTest(host):
                text = path.read_text(encoding="utf-8")
                self.assertIn(GUIDE_URL, text, "link the integration guide")
                self.assertLess(len(text), 8000, "an adapter, not a second manual")
                # No reimplementation: the adapter must not contain Python/TS/JS code of the gates.
                self.assertNotIn("def ", text)
                self.assertNotIn("function ", text)
                self.assertNotIn("class ", text)

    def test_bundles_state_the_non_negotiables(self):
        for host, path in SKILLS.items():
            with self.subTest(host):
                text = path.read_text(encoding="utf-8")
                self.assertIn("test-gate", text)
                self.assertIn("verify", text)
                self.assertIn("abort-check", text)
                self.assertIn("exit", text.lower(), "the exit-code contract must be visible")


class TestPluginReadme(unittest.TestCase):
    def test_documents_install_and_manual_verification(self):
        readme = (PLUGINS / "README.md").read_text(encoding="utf-8")
        self.assertIn("claude plugin", readme)
        self.assertIn(".opencode/skills", readme)
        self.assertIn("Manual verification", readme)
        self.assertIn("jev-harness doctor", readme)
        self.assertIn("tests/test_plugins.py", readme, "point at the automated part")


if __name__ == "__main__":
    unittest.main()
