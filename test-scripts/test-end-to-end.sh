#!/usr/bin/env bash
# End-to-end test runner: runs pytest unit tests.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "=== Running Plan Manager Tests ==="

echo ""
echo "--- pytest unit tests ---"
uv run --python 3.12 --with pytest python3 -m pytest "$PROJECT_ROOT/tests/plan-manager/" -v

echo ""
echo "=== All Plan Manager Tests Passed ==="
