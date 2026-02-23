#!/usr/bin/env bash
# Tests that selecting "Implement the entire plan" (option 3) when
# uncommitted changes exist skips the commit and invokes i2code implement.
# Idea files must remain uncommitted after the operation.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
I2CODE_SCRIPT="$PROJECT_ROOT/src/i2code/scripts/idea-to-code.sh"

PASS_COUNT=0
FAIL_COUNT=0

pass() { echo "PASS: $1"; PASS_COUNT=$((PASS_COUNT + 1)); }
fail() { echo "FAIL: $1"; FAIL_COUNT=$((FAIL_COUNT + 1)); }

TMPDIR_SKIP=$(mktemp -d)
trap 'rm -rf "$TMPDIR_SKIP"' EXIT

echo "=== Go Skip Commit Tests ==="

# Set up a git repo with uncommitted idea files in has_plan state
(
    cd "$TMPDIR_SKIP"
    git init --initial-branch=main
    git config user.email "test@test.com"
    git config user.name "Test"
    touch .gitkeep
    git add .gitkeep
    git commit -m "initial"
)

IDEA_DIR="$TMPDIR_SKIP/my-idea"
mkdir -p "$IDEA_DIR"
echo "# My Idea" > "$IDEA_DIR/my-idea-idea.md"
echo "# Spec" > "$IDEA_DIR/my-idea-spec.md"
echo "# Plan" > "$IDEA_DIR/my-idea-plan.md"
# Files are untracked = uncommitted changes

# Create a stub i2code command that records its arguments
STUB_DIR="$TMPDIR_SKIP/stub-bin"
mkdir -p "$STUB_DIR"
STUB_LOG="$TMPDIR_SKIP/i2code-calls.log"

cat > "$STUB_DIR/i2code" <<'STUB'
#!/usr/bin/env bash
echo "$@" >> "$(dirname "$0")/../i2code-calls.log"
exit 0
STUB
chmod +x "$STUB_DIR/i2code"

# ---------------------------------------------------------------
# Test: Select "Implement the entire plan" (option 3 on 4-option menu)
# ---------------------------------------------------------------
echo ""
echo "--- Test: Skip commit and implement directly ---"

# Pipe "3" (Implement) — after i2code implement succeeds, the script loops
# and shows the menu again. EOF from pipe will cause the script to exit.
# Export PATH with stub dir first so the script finds our stub i2code.
(
    cd "$TMPDIR_SKIP" || exit 1
    export PATH="$STUB_DIR:$PATH"
    printf '3\n' | "$I2CODE_SCRIPT" "$IDEA_DIR" >/dev/null 2>&1 || true
)

# Assert 1: The stub recorded an "implement" invocation
if [ -f "$STUB_LOG" ] && grep -q "^implement " "$STUB_LOG"; then
    pass "i2code implement was invoked"
else
    fail "i2code implement was NOT invoked"
    if [ -f "$STUB_LOG" ]; then
        echo "  stub log contents: $(cat "$STUB_LOG")"
    else
        echo "  stub log file does not exist"
    fi
fi

# Assert 2: Idea files are still uncommitted
STATUS_OUTPUT=$(cd "$TMPDIR_SKIP" && git status --porcelain -- "$IDEA_DIR")
if [ -n "$STATUS_OUTPUT" ]; then
    pass "idea files remain uncommitted"
else
    fail "idea files were committed (should have remained uncommitted)"
fi

# ---------------------------------------------------------------
# Results
# ---------------------------------------------------------------
echo ""
echo "--- Go Skip Commit Results: $PASS_COUNT passed, $FAIL_COUNT failed ---"

if [ "$FAIL_COUNT" -gt 0 ]; then
    exit 1
fi

echo ""
echo "=== All Go Skip Commit Tests Passed ==="
