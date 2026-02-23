#!/usr/bin/env bash
# Tests that IMPLEMENT_CONFIG_FILE is set correctly when _helper.sh is sourced.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

PASS_COUNT=0
FAIL_COUNT=0

pass() { echo "PASS: $1"; PASS_COUNT=$((PASS_COUNT + 1)); }
fail() { echo "FAIL: $1"; FAIL_COUNT=$((FAIL_COUNT + 1)); }

echo "=== Implement Config Tests ==="

# ---------------------------------------------------------------
# Setup
# ---------------------------------------------------------------
TMPDIR_ROOT=$(mktemp -d)
trap 'rm -rf "$TMPDIR_ROOT"' EXIT

IDEA_DIR="$TMPDIR_ROOT/my-idea"
mkdir -p "$IDEA_DIR"
echo "My idea" > "$IDEA_DIR/my-idea-idea.txt"
echo "# Spec" > "$IDEA_DIR/my-idea-spec.md"
echo "- [ ] Task 1" > "$IDEA_DIR/my-idea-plan.md"

# ---------------------------------------------------------------
# Test 1: IMPLEMENT_CONFIG_FILE is set to expected path
# ---------------------------------------------------------------
echo ""
echo "--- Test 1: IMPLEMENT_CONFIG_FILE is set correctly ---"

# Source _helper.sh in a subshell and capture the variable
ACTUAL=$(bash -c "source '$PROJECT_ROOT/src/i2code/scripts/_helper.sh' '$IDEA_DIR'; echo \"\$IMPLEMENT_CONFIG_FILE\"")
EXPECTED="$IDEA_DIR/my-idea-implement-config.yaml"

if [ "$ACTUAL" = "$EXPECTED" ]; then
    pass "IMPLEMENT_CONFIG_FILE equals $EXPECTED"
else
    fail "IMPLEMENT_CONFIG_FILE expected '$EXPECTED' but got '$ACTUAL'"
fi

# ---------------------------------------------------------------
# Results
# ---------------------------------------------------------------
echo ""
echo "--- Implement Config Results: $PASS_COUNT passed, $FAIL_COUNT failed ---"

if [ "$FAIL_COUNT" -gt 0 ]; then
    exit 1
fi

echo ""
echo "=== All Implement Config Tests Passed ==="
