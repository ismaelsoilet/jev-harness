"""E2.3 — the documentation link check runs as part of the battery.

A broken internal link is a defect a reader hits immediately; external links are inventoried with
the dates this project inspected them, per the 30-day freshness rule.
"""
import importlib.util
import json
import subprocess
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
CHECKER = REPO_ROOT / "scripts" / "check_links.py"

spec = importlib.util.spec_from_file_location("check_links", CHECKER)
assert spec and spec.loader
check_links = importlib.util.module_from_spec(spec)
spec.loader.exec_module(check_links)


class TestDocumentationLinks(unittest.TestCase):
    def test_no_broken_internal_links(self):
        broken, _external = check_links.check_documents(REPO_ROOT)
        self.assertEqual(broken, [], "internal documentation links must resolve:\n" + "\n".join(broken))

    def test_the_interop_section_states_its_sources_and_dates(self):
        text = (REPO_ROOT / "SYSTEM_1_5_OPPORTUNITIES.md").read_text(encoding="utf-8")
        self.assertIn("## 3.1 Interop", text)
        for tool in ("jev-guard", "foreman", "winnow", "JevRouter"):
            with self.subTest(tool):
                self.assertIn(tool.lower(), text.lower())
        self.assertIn("2026-09-23", text, "the verification date must be recorded")
        self.assertIn("2026-10-23", text, "the freshness deadline must be recorded")
        self.assertGreaterEqual(check_links.count_claims_with_dates(text), 3)

    def test_the_checker_reports_clean_and_is_usable_from_the_cli(self):
        result = subprocess.run(
            [sys.executable, str(CHECKER), "--root", str(REPO_ROOT), "--json"],
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["broken"], [])
        self.assertGreater(payload["external_count"], 20)

    def test_a_broken_link_is_actually_detected(self):
        """A checker that never fails is not a checker."""
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "doc.md").write_text("[good](other.md)\n[bad](missing.md)\n", encoding="utf-8")
            (root / "other.md").write_text("# Other\n", encoding="utf-8")
            broken, _external = check_links.check_documents(root)
        self.assertEqual(len(broken), 1)
        self.assertIn("missing.md", broken[0])


if __name__ == "__main__":
    unittest.main()
