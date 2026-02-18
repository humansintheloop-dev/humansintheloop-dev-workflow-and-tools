#!/usr/bin/env bash
# Run pytest integration tests.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "=== Running Integration Tests ==="

echo ""
echo "--- pytest integration tests ---"
uv run --python 3.12 python3 -m pytest "$PROJECT_ROOT/tests/" -v -m integration
