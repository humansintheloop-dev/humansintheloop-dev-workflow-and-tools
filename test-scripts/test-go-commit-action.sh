#!/usr/bin/env bash
# Tests that selecting "Commit changes" commits the idea files,
# the commit message matches the expected format, and the next
# menu iteration shows "Implement the entire plan [default]".
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
I2CODE_SCRIPT="$PROJECT_ROOT/src/i2code/scripts/idea-to-code.sh"

PASS_COUNT=0
FAIL_COUNT=0

pass() { echo "PASS: $1"; PASS_COUNT=$((PASS_COUNT + 1)); }
fail() { echo "FAIL: $1"; FAIL_COUNT=$((FAIL_COUNT + 1)); }

TMPDIR_COMMIT=$(mktemp -d)
trap 'rm -rf "$TMPDIR_COMMIT"' EXIT

echo "=== Go Commit Action Tests ==="

# Set up a git repo with uncommitted idea files in has_plan state
(
    cd "$TMPDIR_COMMIT"
    git init --initial-branch=main
    git config user.email "test@test.com"
    git config user.name "Test"
    touch .gitkeep
    git add .gitkeep
    git commit -m "initial"
)

IDEA_DIR="$TMPDIR_COMMIT/my-idea"
mkdir -p "$IDEA_DIR"
echo "# My Idea" > "$IDEA_DIR/my-idea-idea.md"
echo "# Spec" > "$IDEA_DIR/my-idea-spec.md"
echo "# Plan" > "$IDEA_DIR/my-idea-plan.md"
# Files are untracked = uncommitted changes

# ---------------------------------------------------------------
# Test: Select "Commit changes" (option 2), then "Exit" (option 3
# on the next iteration which shows the normal 3-option menu)
# ---------------------------------------------------------------
echo ""
echo "--- Test: Commit changes action ---"

# Pipe "2" (Commit changes on 4-option menu) then "3" (Exit on 3-option menu)
STDERR_OUTPUT=$(
    cd "$TMPDIR_COMMIT" || exit 1
    printf '2\n3\n' | "$I2CODE_SCRIPT" "$IDEA_DIR" 2>&1 >/dev/null || true
)

# Assert 1: Files are committed (git status is clean for idea dir)
STATUS_OUTPUT=$(cd "$TMPDIR_COMMIT" && git status --porcelain -- "$IDEA_DIR")
if [ -z "$STATUS_OUTPUT" ]; then
    pass "idea files are committed (git status is clean)"
else
    fail "idea files are NOT committed (git status shows changes)"
    echo "  git status output: $STATUS_OUTPUT"
fi

# Assert 2: Commit message matches expected format
COMMIT_MSG=$(cd "$TMPDIR_COMMIT" && git log -1 --pretty=format:%s)
EXPECTED_MSG="Add idea docs for my-idea"
if [ "$COMMIT_MSG" = "$EXPECTED_MSG" ]; then
    pass "commit message matches expected format: '$EXPECTED_MSG'"
else
    fail "commit message does NOT match expected format"
    echo "  expected: '$EXPECTED_MSG'"
    echo "  actual:   '$COMMIT_MSG'"
fi

# Assert 3: Second menu iteration shows "Implement the entire plan [default]"
if echo "$STDERR_OUTPUT" | grep -q "Implement the entire plan \[default\]"; then
    pass "second menu shows 'Implement the entire plan [default]'"
else
    fail "second menu does NOT show 'Implement the entire plan [default]'"
    echo "  stderr output: $STDERR_OUTPUT"
fi

# ---------------------------------------------------------------
# Results
# ---------------------------------------------------------------
echo ""
echo "--- Go Commit Action Results: $PASS_COUNT passed, $FAIL_COUNT failed ---"

if [ "$FAIL_COUNT" -gt 0 ]; then
    exit 1
fi

echo ""
echo "=== All Go Commit Action Tests Passed ==="
