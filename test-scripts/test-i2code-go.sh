#!/usr/bin/env bash
# Runs all i2code go tests: commit menu, commit action, commit failure, skip commit, implement config.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

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

echo ""
echo "--- Implement config tests ---"
"$SCRIPT_DIR/test-implement-config.sh"

echo ""
echo "=== All i2code Go Tests Passed ==="
