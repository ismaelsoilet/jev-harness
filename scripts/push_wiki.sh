#!/usr/bin/env bash
# ==============================================================================
# Jev Harness — GitHub Wiki Quad-Sync Script
# Synchronizes all 17 bilingual wiki pages from .wiki/ to GitHub Wiki Git repo
# ==============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
WIKI_SRC="$REPO_ROOT/.wiki"
WIKI_REMOTE="https://github.com/ismaelsoilet/jev-harness.wiki.git"
TMP_DIR="/tmp/jev-harness-wiki-sync"

echo "⚡ Jev Harness — Synchronizing Wiki..."

if [ ! -d "$WIKI_SRC" ]; then
    echo "❌ Error: Wiki source directory '$WIKI_SRC' not found." >&2
    exit 1
fi

rm -rf "$TMP_DIR"

echo "📥 Cloning GitHub Wiki repository..."
if ! git clone "$WIKI_REMOTE" "$TMP_DIR"; then
    echo ""
    echo "⚠️  The GitHub Wiki git repository is not yet initialized."
    echo "👉 Please visit https://github.com/ismaelsoilet/jev-harness/wiki"
    echo "   and click 'Create the first page' (or Save page) once to initialize it."
    echo "   Then re-run this script."
    exit 1
fi

echo "📋 Copying 17 bilingual pages to working tree..."
cp -r "$WIKI_SRC"/* "$TMP_DIR"/

cd "$TMP_DIR"
git add .

if git diff-index --quiet HEAD --; then
    echo "✅ Wiki is already up to date. No changes to commit."
    exit 0
fi

echo "💾 Committing changes..."
git commit -m "docs(wiki): synchronize complete bilingual documentation (17 pages)"

echo "🚀 Pushing to GitHub Wiki..."
if git push origin master; then
    echo "🎉 Successfully pushed to master!"
elif git push origin main; then
    echo "🎉 Successfully pushed to main!"
fi

echo "✨ GitHub Wiki synchronization complete! Visit: https://github.com/ismaelsoilet/jev-harness/wiki"
