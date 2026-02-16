#!/usr/bin/env bash
# End-to-end test runner: runs unit tests, CLI smoke tests, and integration tests.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "=== Running Unit Tests ==="

echo ""
echo "--- pytest unit tests ---"
uv run --python 3.12 --with pytest --with GitPython --with pytest-mock --with Jinja2 python3 -m pytest "$PROJECT_ROOT/tests/" -v -m unit

echo ""
echo "--- CLI smoke tests ---"
"$SCRIPT_DIR/test-plan-cli-smoke.sh"

echo ""
echo "=== Running Integration Tests ==="

echo ""
echo "--- pytest integration tests ---"
uv run --python 3.12 --with pytest --with GitPython --with pytest-mock --with Jinja2 python3 -m pytest "$PROJECT_ROOT/tests/" -v -m integration

echo ""
"$SCRIPT_DIR/test-verify-all-tests-have-markers.sh"

echo ""
echo "=== All Tests Passed ==="
