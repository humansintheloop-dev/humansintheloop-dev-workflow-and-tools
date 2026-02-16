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
echo "=== Verifying All Tests Have Markers ==="

UNMARKED=$(uv run --python 3.12 --with pytest --with GitPython --with pytest-mock --with Jinja2 \
    python3 -m pytest "$PROJECT_ROOT/tests/" --co -q -m "not unit and not integration" 2>&1)
UNMARKED_COUNT=$(echo "$UNMARKED" | tail -1 | grep -o '^[0-9]*' || echo "0")

if [[ "$UNMARKED_COUNT" -gt 0 ]]; then
    echo ""
    echo "FAIL: $UNMARKED_COUNT tests missing unit/integration marker:"
    echo "$UNMARKED"
    exit 1
fi
echo "PASS: All tests have markers"

echo ""
echo "=== All Tests Passed ==="
