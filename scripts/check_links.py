#!/usr/bin/env python3
"""
E2.3 — offline link checker for the documentation.

Internal links (relative file paths and `#anchors`) are verified locally: a broken link in the
docs is a defect a reader hits immediately. External links are *listed with their check date*
instead of being fetched, so the check stays deterministic and never fails because a third-party
site is slow or offline. Every comparative claim in the interop section carries a source URL and a
date; this script reports the inventory so a reviewer can confirm the freshness rule (30 days).

Exit codes: 0 clean · 1 broken internal link · 2 invocation error.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Dict, List, Sequence, Tuple

MARKDOWN_LINK = re.compile(r"(?<!\!)\[(?P<text>[^\]]*)\]\((?P<target>[^)\s]+)(?:\s+\"[^\"]*\")?\)")
HEADING = re.compile(r"^(#{1,6})\s+(?P<title>.+?)\s*$", re.MULTILINE)
EXTERNAL = re.compile(r"^[a-zA-Z][a-zA-Z0-9+.-]*://")

# Fenced code blocks are skipped: URLs inside examples are not links.
FENCE = re.compile(r"^```.*?^```", re.MULTILINE | re.DOTALL)


def slug(title: str) -> str:
    """GitHub-style anchor slug for a heading.

    Two details matter for parity with GitHub: emoji (astral chars) are dropped but the space they
    occupied still becomes a hyphen (`## 🚀 Quickstart` -> `-quickstart`), and a literal `&` is
    dropped leaving the two surrounding hyphens (`Provider Access & API Keys` ->
    `provider-access--api-keys`).
    """
    text = re.sub(r"<[^>]+>", "", title)
    text = re.sub(r"[`*_~]", "", text)
    text = text.lower()
    # `\w` keeps letters/digits/underscore and drops emoji plus their variation selectors
    # (U+FE0F), which is what GitHub does.
    text = re.sub(r"[^\w\s-]", "", text, flags=re.UNICODE)
    return text.replace(" ", "-")


def anchors_of(text: str) -> set:
    stripped = FENCE.sub("", text)
    return {slug(match.group("title")) for match in HEADING.finditer(stripped)}


def links_of(text: str) -> List[str]:
    stripped = FENCE.sub("", text)
    return [match.group("target") for match in MARKDOWN_LINK.finditer(stripped)]


def check_documents(root: Path, patterns: Sequence[str] = ("*.md", "docs/**/*.md")) -> Tuple[List[str], Dict[str, List[str]]]:
    """Returns (broken internal links, external link inventory by file)."""
    seen = set()
    documents: List[Path] = []
    for pattern in patterns:
        for doc in sorted(root.glob(pattern)):
            if doc not in seen and ".git/" not in str(doc) and doc.is_file():
                seen.add(doc)
                documents.append(doc)

    anchor_cache: Dict[Path, set] = {doc: anchors_of(doc.read_text(encoding="utf-8")) for doc in documents}
    broken: List[str] = []
    external: Dict[str, List[str]] = {}

    for doc in documents:
        text = doc.read_text(encoding="utf-8")
        for target in links_of(text):
            if EXTERNAL.match(target) or target.startswith("mailto:"):
                external.setdefault(str(doc.relative_to(root)), []).append(target)
                continue
            path_part, _, anchor = target.partition("#")
            if not path_part:
                if anchor and anchor not in anchor_cache[doc]:
                    broken.append(f"{doc.relative_to(root)}: missing local anchor '#{anchor}'")
                continue
            candidate = (doc.parent / path_part).resolve()
            if not candidate.exists():
                broken.append(f"{doc.relative_to(root)}: missing target '{path_part}'")
                continue
            if anchor and candidate.suffix == ".md" and anchor not in anchor_cache.get(candidate, anchors_of(candidate.read_text(encoding='utf-8'))):
                broken.append(f"{doc.relative_to(root)}: missing anchor '#{anchor}' in {path_part}")
    return broken, external


def count_claims_with_dates(text: str) -> int:
    """Comparative claims should carry a date (the freshness rule from the repository rules)."""
    claims = re.findall(r"(?m)^\|.*(?:★|stars?|created|criado).*\|.*$", text, re.IGNORECASE)
    return sum(1 for claim in claims if re.search(r"\d{4}-\d{2}-\d{2}|\d{2}/\d{2}/\d{4}", claim))


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Offline link checker for the documentation.")
    parser.add_argument("--root", default=".", help="Repository root (default: current directory)")
    parser.add_argument("--json", action="store_true", help="Machine-readable report")
    parser.add_argument("--list-external", action="store_true", help="Print the external link inventory")
    args = parser.parse_args(argv)

    root = Path(args.root).resolve()
    if not root.is_dir():
        print(f"Error: {root} is not a directory", file=sys.stderr)
        return 2

    broken, external = check_documents(root)
    if args.json:
        import json

        print(
            json.dumps(
                {
                    "broken": broken,
                    "external_count": sum(len(items) for items in external.values()),
                    "external": external if args.list_external else {},
                },
                indent=2,
            )
        )
    else:
        if args.list_external:
            for doc, targets in sorted(external.items()):
                for target in targets:
                    print(f"{doc}: {target}")
        if broken:
            print("Broken internal links:")
            for line in broken:
                print(f"  - {line}")
        else:
            print(f"Link check OK: {sum(len(v) for v in external.values())} external link(s) recorded.")

    return 1 if broken else 0


if __name__ == "__main__":
    sys.exit(main())
