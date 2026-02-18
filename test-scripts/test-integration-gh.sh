#!/usr/bin/env bash
# Run pytest integration_gh tests (requires gh auth).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "=== Running GitHub Integration Tests ==="

echo ""
echo "--- pytest integration_gh tests (requires gh auth) ---"
if [[ -z "${CI:-}" ]]; then
    uv run --python 3.12 python3 -m pytest "$PROJECT_ROOT/tests/" -v -m integration_gh
else
    echo "SKIPPED: integration_gh tests not run in CI (no GH_TOKEN)"
fi
