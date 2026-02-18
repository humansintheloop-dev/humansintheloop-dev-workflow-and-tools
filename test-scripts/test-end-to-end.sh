#!/usr/bin/env bash
# End-to-end test runner: runs unit tests, CLI smoke tests, and integration tests.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

"$SCRIPT_DIR/test-unit.sh"

echo ""
echo "--- CLI smoke tests ---"
"$SCRIPT_DIR/test-plan-cli-smoke.sh"

"$SCRIPT_DIR/test-integration.sh"

"$SCRIPT_DIR/test-integration-gh.sh"

echo ""
"$SCRIPT_DIR/test-verify-all-tests-have-markers.sh"

echo ""
echo "=== All Tests Passed ==="
