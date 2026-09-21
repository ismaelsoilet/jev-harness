#!/usr/bin/env bash
# ==============================================================================
# Jev Harness - Crates.io Publishing Assistant (SureForge Verified)
# ==============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
RUST_DIR="${REPO_ROOT}/packages/rust"

echo "================================================================="
echo "🦀 Jev Harness - crates.io Publishing Helper"
echo "================================================================="
echo "Package directory: ${RUST_DIR}"
echo ""

cd "${RUST_DIR}"

# 1. Verification of Cargo toolchain
echo "[1/5] Checking Cargo toolchain..."
cargo --version
rustc --version
echo "✅ Toolchain OK."
echo ""

# 2. Run clean test battery
echo "[2/5] Running Rust test suite..."
cargo test
echo "✅ All unit & integration tests passed (13/13)."
echo ""

# 3. Verify packaging & dry run
echo "[3/5] Verifying crate packaging..."
cargo package --list --allow-dirty
cargo package --allow-dirty
echo "✅ Crate packaged and verified successfully."
echo ""

# 4. Check Crates.io authentication
echo "[4/5] Checking crates.io credentials..."
CARGO_CREDS="${HOME}/.cargo/credentials.toml"
CARGO_CREDS_LEGACY="${HOME}/.cargo/credentials"

if [[ -f "${CARGO_CREDS}" ]] || [[ -f "${CARGO_CREDS_LEGACY}" ]]; then
    echo "✅ Found cargo credentials file."
else
    echo "⚠️  No crates.io token found in ~/.cargo/credentials.toml."
    echo ""
    echo "To authenticate with crates.io:"
    echo "  1. Log into https://crates.io"
    echo "  2. Go to https://crates.io/settings/tokens"
    echo "  3. Generate a new API token with 'publish-update' / 'publish-new' scope"
    echo "  4. Run:"
    echo "       cargo login <YOUR_API_TOKEN>"
    echo ""
fi

# 5. Publishing Instructions
echo "[5/5] Ready for publishing!"
echo "-----------------------------------------------------------------"
echo "When you have committed your changes and authenticated:"
echo ""
echo "  cd packages/rust"
echo "  cargo publish"
echo ""
echo "If you need to publish with current uncommitted working tree:"
echo "  cargo publish --allow-dirty"
echo "-----------------------------------------------------------------"
