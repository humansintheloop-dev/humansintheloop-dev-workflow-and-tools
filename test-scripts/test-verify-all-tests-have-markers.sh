#!/usr/bin/env bash
# Verify that all pytest tests have a recognized marker (unit, integration, or integration_gh).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "=== Verifying All Tests Have Markers ==="

UNMARKED=$(uv run --python 3.12 --with pytest --with GitPython --with pytest-mock --with Jinja2 \
    python3 -m pytest "$PROJECT_ROOT/tests/" --co -q -m "not unit and not integration and not integration_gh" 2>&1) || true
UNMARKED_COUNT=$(echo "$UNMARKED" | tail -1 | grep -o '^[0-9]*' || echo "0")

if [[ "$UNMARKED_COUNT" -gt 0 ]]; then
    echo ""
    echo "FAIL: $UNMARKED_COUNT tests missing unit/integration marker:"
    echo "$UNMARKED"
    exit 1
fi
echo "PASS: All tests have markers"
