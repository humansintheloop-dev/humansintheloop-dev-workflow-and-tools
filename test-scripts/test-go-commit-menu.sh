#!/usr/bin/env bash
# Tests that the has_plan menu shows "Commit changes [default]" when
# the idea directory has uncommitted changes, and "Implement the entire
# plan [default]" when everything is committed.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
I2CODE_SCRIPT="$PROJECT_ROOT/src/i2code/scripts/idea-to-code.sh"

PASS_COUNT=0
FAIL_COUNT=0

pass() { echo "PASS: $1"; PASS_COUNT=$((PASS_COUNT + 1)); }
fail() { echo "FAIL: $1"; FAIL_COUNT=$((FAIL_COUNT + 1)); }

TMPDIR_UNCOMMITTED=$(mktemp -d)
TMPDIR_COMMITTED=$(mktemp -d)
trap 'rm -rf "$TMPDIR_UNCOMMITTED" "$TMPDIR_COMMITTED"' EXIT

echo "=== Go Commit Menu Tests ==="

# ---------------------------------------------------------------
# Test 1: Uncommitted changes → menu shows "Commit changes [default]"
# ---------------------------------------------------------------
echo ""
echo "--- Test 1: uncommitted changes present ---"

# Set up a git repo with idea files in has_plan state
(
    cd "$TMPDIR_UNCOMMITTED"
    git init --initial-branch=main
    git config user.email "test@test.com"
    git config user.name "Test"
    touch .gitkeep
    git add .gitkeep
    git commit -m "initial"
)

IDEA_DIR_1="$TMPDIR_UNCOMMITTED/my-idea"
mkdir -p "$IDEA_DIR_1"
echo "# My Idea" > "$IDEA_DIR_1/my-idea-idea.md"
echo "# Spec" > "$IDEA_DIR_1/my-idea-spec.md"
echo "# Plan" > "$IDEA_DIR_1/my-idea-plan.md"
# Files are untracked = uncommitted changes

# Pipe "4" then "3" — in a 4-option menu "4" selects Exit;
# in the current 3-option menu "4" is invalid, then "3" selects Exit.
# Capture stderr (menus are written there); stdout goes to /dev/null.
# Run from within the temp repo so git status works correctly.
STDERR_OUTPUT_1=$(
    cd "$TMPDIR_UNCOMMITTED" || exit 1
    printf '4\n3\n' | "$I2CODE_SCRIPT" "$IDEA_DIR_1" 2>&1 >/dev/null || true
)

if echo "$STDERR_OUTPUT_1" | grep -q "Commit changes \[default\]"; then
    pass "menu shows 'Commit changes [default]' when uncommitted changes exist"
else
    fail "menu does NOT show 'Commit changes [default]' when uncommitted changes exist"
    echo "  stderr output: $STDERR_OUTPUT_1"
fi

# ---------------------------------------------------------------
# Test 2: No uncommitted changes → menu shows "Implement the entire plan: i2code implement [default]"
# ---------------------------------------------------------------
echo ""
echo "--- Test 2: no uncommitted changes ---"

# Set up a git repo with all idea files committed
(
    cd "$TMPDIR_COMMITTED"
    git init --initial-branch=main
    git config user.email "test@test.com"
    git config user.name "Test"
    touch .gitkeep
    git add .gitkeep
    git commit -m "initial"
)

IDEA_DIR_2="$TMPDIR_COMMITTED/my-idea"
mkdir -p "$IDEA_DIR_2"
echo "# My Idea" > "$IDEA_DIR_2/my-idea-idea.md"
echo "# Spec" > "$IDEA_DIR_2/my-idea-spec.md"
echo "# Plan" > "$IDEA_DIR_2/my-idea-plan.md"
# Commit all idea files
(
    cd "$TMPDIR_COMMITTED"
    git add my-idea
    git commit -m "add idea files"
)

# Pipe "4" (Exit) into the script — 4-option menu
# Run from within the temp repo so git status works correctly.
STDERR_OUTPUT_2=$(
    cd "$TMPDIR_COMMITTED" || exit 1
    printf '4\n' | "$I2CODE_SCRIPT" "$IDEA_DIR_2" 2>&1 >/dev/null || true
)

if echo "$STDERR_OUTPUT_2" | grep -q "Implement the entire plan: i2code implement.*\[default\]"; then
    pass "menu shows 'Implement the entire plan: i2code implement [default]' when no uncommitted changes"
else
    fail "menu does NOT show 'Implement the entire plan: i2code implement [default]' when no uncommitted changes"
    echo "  stderr output: $STDERR_OUTPUT_2"
fi

if echo "$STDERR_OUTPUT_2" | grep -q "Commit changes"; then
    fail "menu shows 'Commit changes' when no uncommitted changes exist"
    echo "  stderr output: $STDERR_OUTPUT_2"
else
    pass "menu does NOT show 'Commit changes' when no uncommitted changes"
fi

# ---------------------------------------------------------------
# Results
# ---------------------------------------------------------------
echo ""
echo "--- Go Commit Menu Results: $PASS_COUNT passed, $FAIL_COUNT failed ---"

if [ "$FAIL_COUNT" -gt 0 ]; then
    exit 1
fi

echo ""
echo "=== All Go Commit Menu Tests Passed ==="
