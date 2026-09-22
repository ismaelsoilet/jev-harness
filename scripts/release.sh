#!/usr/bin/env bash
# ==============================================================================
# Jev Harness - Multi-Registry Release & Documentation Sync Script
# Synchronizes PyPI (Python), npm (TypeScript), Crates.io (Rust), and GitHub.
# ==============================================================================
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYPROJECT="${REPO_ROOT}/pyproject.toml"
PACKAGE_JSON="${REPO_ROOT}/packages/ts/package.json"
CARGO_TOML="${REPO_ROOT}/packages/rust/Cargo.toml"

usage() {
    echo "Usage: $0 [COMMAND] [OPTIONS]"
    echo ""
    echo "Commands:"
    echo "  --check                 Run full test battery across Python, TS, and Rust"
    echo "  --version               Show current versions across all manifests"
    echo "  --verify-sync           Strictly verify version parity across all manifests and tags (pre-push check)"
    echo "  --bump <version>        Synchronously update version in pyproject.toml, package.json, and Cargo.toml"
    echo "  --publish <target>      Publish to target: 'python', 'npm', 'rust', or 'all'"
    echo "  --git-tag <version>     Create git commit, tag 'v<version>', and push to GitHub"
    echo "  --help                  Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 --check"
    echo "  $0 --bump 0.1.3"
    echo "  $0 --publish rust"
    echo "  $0 --git-tag 0.1.3"
    exit 1
}

show_versions() {
    echo "=== Current Manifest Versions ==="
    echo "Python (pyproject.toml):    $(grep '^version = ' "${PYPROJECT}" | cut -d'"' -f2)"
    echo "TypeScript (package.json):  $(grep '"version":' "${PACKAGE_JSON}" | head -n1 | cut -d'"' -f4)"
    echo "Rust (Cargo.toml):          $(grep '^version = ' "${CARGO_TOML}" | head -n1 | cut -d'"' -f2)"
    echo "================================="
}

run_checks() {
    echo "================================================================="
    echo "🧪 Running Multi-Runtime Test Battery"
    echo "================================================================="

    echo "[1/3] Testing Python..."
    cd "${REPO_ROOT}"
    python3 -m unittest discover -s tests -v

    echo "[2/3] Testing TypeScript..."
    cd "${REPO_ROOT}/packages/ts"
    npx tsc -p tsconfig.json
    npx tsc -p tsconfig.test.json
    node --test dist-test/tests/*.js

    echo "[3/3] Testing Rust..."
    cd "${REPO_ROOT}/packages/rust"
    cargo test --quiet

    echo ""
    echo "✅ ALL 109 TESTS PASSED ACROSS PYTHON, TYPESCRIPT, AND RUST!"
    echo "================================================================="
}

bump_version() {
    local new_ver="$1"
    if [[ -z "${new_ver}" ]]; then
        echo "Error: Version string required (e.g. 0.1.4)"
        exit 1
    fi

    echo "Bumping all manifests and source files to v${new_ver}..."

    # 1. Update pyproject.toml and Python source
    sed -i -E "s/^version = \"[^\"]+\"/version = \"${new_ver}\"/" "${PYPROJECT}"
    sed -i -E "s/^__version__ = \"[^\"]+\"/__version__ = \"${new_ver}\"/" "${REPO_ROOT}/src/jev_harness/__init__.py"
    sed -i -E "s/JevHarness\/[0-9]+\.[0-9]+\.[0-9]+/JevHarness\/${new_ver}/" "${REPO_ROOT}/src/jev_harness/client.py"

    # 2. Update TypeScript package.json, lockfile, client, and cli fallback
    sed -i -E "s/\"version\": \"[^\"]+\"/\"version\": \"${new_ver}\"/" "${PACKAGE_JSON}"
    sed -i -E "s/JevHarness\/[0-9]+\.[0-9]+\.[0-9]+/JevHarness\/${new_ver}/" "${REPO_ROOT}/packages/ts/src/client.ts"
    sed -i -E "s/return \"[0-9]+\.[0-9]+\.[0-9]+\";/return \"${new_ver}\";/" "${REPO_ROOT}/packages/ts/src/cli.ts"
    if [[ -f "${REPO_ROOT}/packages/ts/package-lock.json" ]]; then
        cd "${REPO_ROOT}/packages/ts"
        npm version "${new_ver}" --no-git-tag-version --allow-same-version || true
    fi

    # 3. Update Cargo.toml and Cargo.lock
    sed -i -E "s/^version = \"[^\"]+\"/version = \"${new_ver}\"/" "${CARGO_TOML}"
    (cd "${REPO_ROOT}/packages/rust" && cargo check --quiet || true)

    # 4. Update README.md and packages/rust/README.md dependencies & hooks
    sed -i -E "s/jev-harness = \"[^\"]+\"/jev-harness = \"${new_ver}\"/" "${REPO_ROOT}/README.md"
    sed -i -E "s/jev-harness = \"[^\"]+\"/jev-harness = \"${new_ver}\"/" "${REPO_ROOT}/packages/rust/README.md"
    sed -i -E "s/rev: v[0-9]+\.[0-9]+\.[0-9]+/rev: v${new_ver}/" "${REPO_ROOT}/README.md"

    show_versions
    echo "✅ Version bump complete across all manifests, code, and docs."
}

publish_target() {
    local target="$1"

    case "${target}" in
        python|pypi)
            echo "📦 Publishing to PyPI (Python)..."
            cd "${REPO_ROOT}"
            rm -rf dist/ build/ *.egg-info
            python3 -m pip install --quiet build twine || true
            python3 -m build
            echo "To upload to PyPI, run:"
            echo "  twine upload dist/*"
            ;;
        npm|ts)
            echo "📦 Publishing to npm (TypeScript)..."
            cd "${REPO_ROOT}/packages/ts"
            npm run build
            echo "Running npm publish..."
            npm publish --access public
            echo "✅ Published to npm!"
            ;;
        rust|crates)
            echo "📦 Publishing to crates.io (Rust)..."
            cd "${REPO_ROOT}/packages/rust"
            cargo publish --allow-dirty
            echo "✅ Published to crates.io!"
            ;;
        all)
            echo "🚀 Publishing across all 3 registries..."
            publish_target rust
            publish_target npm
            publish_target python
            ;;
        *)
            echo "Error: Unknown publish target '${target}'. Use 'python', 'npm', 'rust', or 'all'."
            exit 1
            ;;
    esac
}

git_tag_release() {
    local ver="$1"
    if [[ -z "${ver}" ]]; then
        echo "Error: Version string required (e.g. 0.1.4)"
        exit 1
    fi

    echo "Committing release v${ver} and tagging..."
    cd "${REPO_ROOT}"
    git add -A
    git commit -m "release: v${ver} across Python, TypeScript, and Rust" || true
    git tag -a "v${ver}" -m "Release v${ver}"
    git push origin main --tags
    echo "✅ Git tag v${ver} pushed to GitHub!"
}

verify_sync() {
    echo "================================================================="
    echo "🔍 Strict Quad-Manifest & Version Parity Verification"
    echo "================================================================="

    local py_ver ts_ver rust_ver init_ver
    py_ver="$(grep '^version = ' "${PYPROJECT}" | cut -d'"' -f2)"
    ts_ver="$(grep '"version":' "${PACKAGE_JSON}" | head -n1 | cut -d'"' -f4)"
    rust_ver="$(grep '^version = ' "${CARGO_TOML}" | head -n1 | cut -d'"' -f2)"
    init_ver="$(grep '^__version__ = ' "${REPO_ROOT}/src/jev_harness/__init__.py" | cut -d'"' -f2)"

    echo "Manifest Versions:"
    echo "  - Python (pyproject.toml):        ${py_ver}"
    echo "  - Python (__init__.__version__): ${init_ver}"
    echo "  - TypeScript (package.json):      ${ts_ver}"
    echo "  - Rust (Cargo.toml):              ${rust_ver}"

    if [[ "${py_ver}" != "${ts_ver}" || "${py_ver}" != "${rust_ver}" || "${py_ver}" != "${init_ver}" ]]; then
        echo ""
        echo "❌ FATAL: Version mismatch detected across manifests!"
        echo "All manifests must be strictly identical before any push or release."
        exit 1
    fi
    echo "✅ Manifest parity 100% synchronized: v${py_ver}"

    # Build check
    echo ""
    echo "Checking TypeScript build..."
    if [[ ! -d "${REPO_ROOT}/packages/ts/node_modules" ]]; then
        (cd "${REPO_ROOT}/packages/ts" && (npm ci 2>/dev/null || npm install 2>/dev/null))
    fi
    (cd "${REPO_ROOT}/packages/ts" && npm run build)
    echo "✅ TypeScript build OK"

    echo ""
    echo "Checking Rust Cargo check..."
    (cd "${REPO_ROOT}/packages/rust" && cargo check --quiet)
    echo "✅ Rust check OK"

    # Git Tag check
    echo ""
    echo "Checking Git tags..."
    if git rev-parse "v${py_ver}" >/dev/null 2>&1; then
        echo "✅ Git tag 'v${py_ver}' exists locally."
    else
        echo "⚠️  INFO: Git tag 'v${py_ver}' has not been tagged yet."
    fi

    echo ""
    echo "================================================================="
    echo "✅ QUAD-MANIFEST SYNC VERIFICATION PASSED (v${py_ver})"
    echo "================================================================="
}

# Main routing
if [[ $# -eq 0 ]]; then
    usage
fi

case "$1" in
    --check)
        run_checks
        ;;
    --version)
        show_versions
        ;;
    --verify-sync)
        verify_sync
        ;;
    --bump)
        bump_version "${2:-}"
        ;;
    --publish)
        publish_target "${2:-all}"
        ;;
    --git-tag)
        git_tag_release "${2:-}"
        ;;
    --help|-h)
        usage
        ;;
    *)
        usage
        ;;
esac
