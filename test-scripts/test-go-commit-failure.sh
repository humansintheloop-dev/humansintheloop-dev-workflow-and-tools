#!/usr/bin/env bash
# Tests that when "Commit changes" is selected and git commit fails,
# handle_error presents "Retry" and "Abort workflow", and selecting
# "Abort workflow" exits with code 1.
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

REAL_GIT="$(command -v git)"

echo "=== Go Commit Failure Tests ==="

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

# Create git stub that fails on commit, passes through everything else
STUB_DIR="$TMPDIR_COMMIT/stub-bin"
mkdir -p "$STUB_DIR"
cat > "$STUB_DIR/git" << STUB_EOF
#!/usr/bin/env bash
if [ "\$1" = "commit" ]; then
    echo "git commit: simulated failure" >&2
    exit 1
fi
exec "$REAL_GIT" "\$@"
STUB_EOF
chmod +x "$STUB_DIR/git"

# ---------------------------------------------------------------
# Test: Commit fails → handle_error shows Retry/Abort → Abort exits 1
# ---------------------------------------------------------------
echo ""
echo "--- Test: Commit failure triggers retry/abort prompt ---"

# Pipe "2" (Commit changes on 4-option menu) then "2" (Abort workflow)
# Run with stub git on PATH
OUTPUT_FILE="$TMPDIR_COMMIT/test-output.txt"
set +e
(
    cd "$TMPDIR_COMMIT"
    export PATH="$STUB_DIR:$PATH"
    printf '2\n2\n' | "$I2CODE_SCRIPT" "$IDEA_DIR" >"$OUTPUT_FILE" 2>&1
)
EXIT_CODE=$?
set -e
OUTPUT=$(cat "$OUTPUT_FILE")

# Assert 1: Exit code is 1
if [ "$EXIT_CODE" -eq 1 ]; then
    pass "exit code is 1"
else
    fail "exit code is $EXIT_CODE, expected 1"
fi

# Assert 2: Output contains "Retry"
if echo "$OUTPUT" | grep -q "Retry"; then
    pass "output contains 'Retry'"
else
    fail "output does NOT contain 'Retry'"
    echo "  output: $OUTPUT"
fi

# Assert 3: Output contains "Abort workflow"
if echo "$OUTPUT" | grep -q "Abort workflow"; then
    pass "output contains 'Abort workflow'"
else
    fail "output does NOT contain 'Abort workflow'"
    echo "  output: $OUTPUT"
fi

# ---------------------------------------------------------------
# Results
# ---------------------------------------------------------------
echo ""
echo "--- Go Commit Failure Results: $PASS_COUNT passed, $FAIL_COUNT failed ---"

if [ "$FAIL_COUNT" -gt 0 ]; then
    exit 1
fi

echo ""
echo "=== All Go Commit Failure Tests Passed ==="
