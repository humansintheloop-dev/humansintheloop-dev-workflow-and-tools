#!/usr/bin/env bash
# End-to-end test runner: runs unit tests, CLI smoke tests, and integration tests.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

"$SCRIPT_DIR/test-unit.sh"

echo ""
echo "--- CLI smoke tests ---"
"$SCRIPT_DIR/test-plan-cli-smoke.sh"

echo ""
echo "--- Subcommand smoke tests ---"
"$SCRIPT_DIR/test-subcommands-smoke.sh"

echo ""
echo "--- list-plugin-skills tests ---"
"$SCRIPT_DIR/test-list-plugin-skills.sh"

echo ""
echo "--- Editor resolution tests ---"
"$SCRIPT_DIR/test-editor-resolution.sh"

echo ""
echo "--- Go commit menu tests ---"
"$SCRIPT_DIR/test-go-commit-menu.sh"

echo ""
echo "--- Go commit action tests ---"
"$SCRIPT_DIR/test-go-commit-action.sh"

echo ""
echo "--- Go commit failure tests ---"
"$SCRIPT_DIR/test-go-commit-failure.sh"

echo ""
echo "--- Go skip commit tests ---"
"$SCRIPT_DIR/test-go-skip-commit.sh"

"$SCRIPT_DIR/test-integration.sh"

"$SCRIPT_DIR/test-integration-gh.sh"

echo ""
"$SCRIPT_DIR/test-verify-all-tests-have-markers.sh"

echo ""
echo "=== All Tests Passed ==="
