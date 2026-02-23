#!/usr/bin/env bash
# Tests for implement config: variable definition, prompting, and persistence.
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
# Helper: create_mock_i2code
# ---------------------------------------------------------------
MOCK_DIR="$TMPDIR_ROOT/mock-bin"
MOCK_ARGS_FILE="$TMPDIR_ROOT/mock-i2code-args"

create_mock_i2code() {
    mkdir -p "$MOCK_DIR"
    cat > "$MOCK_DIR/i2code" <<'MOCK_SCRIPT'
#!/usr/bin/env bash
if [ "$1" = "implement" ]; then
    printf '%s\n' "$@" > "${MOCK_ARGS_FILE}"
fi
exit 0
MOCK_SCRIPT
    chmod +x "$MOCK_DIR/i2code"
    # Export so subshells can see it
    export MOCK_ARGS_FILE
}

# ---------------------------------------------------------------
# Test 2: First run prompting saves config file
# ---------------------------------------------------------------
echo ""
echo "--- Test 2: First run prompting saves config file ---"

# Set up a fresh idea directory for this test
TEST2_DIR="$TMPDIR_ROOT/test2-idea"
mkdir -p "$TEST2_DIR"
echo "My idea" > "$TEST2_DIR/test2-idea-idea.txt"
echo "# Spec" > "$TEST2_DIR/test2-idea-spec.md"
echo "- [ ] Task 1" > "$TEST2_DIR/test2-idea-plan.md"

create_mock_i2code

# Pipe: 2 (Implement) → 2 (Non-interactive) → 2 (Trunk) → 4 (Exit)
printf '%s\n' 2 2 2 4 | PATH="$MOCK_DIR:$PATH" "$PROJECT_ROOT/src/i2code/scripts/idea-to-code.sh" "$TEST2_DIR" > /dev/null 2>&1 || true

CONFIG_FILE="$TEST2_DIR/test2-idea-implement-config.yaml"

if [ -f "$CONFIG_FILE" ]; then
    pass "Config file exists at $CONFIG_FILE"
else
    fail "Config file does not exist at $CONFIG_FILE"
fi

if [ -f "$CONFIG_FILE" ] && grep -q 'interactive: false' "$CONFIG_FILE"; then
    pass "Config file contains 'interactive: false'"
else
    fail "Config file does not contain 'interactive: false'"
fi

if [ -f "$CONFIG_FILE" ] && grep -q 'trunk: true' "$CONFIG_FILE"; then
    pass "Config file contains 'trunk: true'"
else
    fail "Config file does not contain 'trunk: true'"
fi

# ---------------------------------------------------------------
# Test 3: Config with non-interactive and trunk passes flags
# ---------------------------------------------------------------
echo ""
echo "--- Test 3: Config with non-interactive and trunk passes flags ---"

TEST3_DIR="$TMPDIR_ROOT/test3-idea"
mkdir -p "$TEST3_DIR"
echo "My idea" > "$TEST3_DIR/test3-idea-idea.txt"
echo "# Spec" > "$TEST3_DIR/test3-idea-spec.md"
echo "- [ ] Task 1" > "$TEST3_DIR/test3-idea-plan.md"

# Pre-create config file with non-interactive and trunk
printf 'interactive: false\ntrunk: true\n' > "$TEST3_DIR/test3-idea-implement-config.yaml"

create_mock_i2code

# Pipe: 2 (Implement) → 4 (Exit)
printf '%s\n' 2 4 | PATH="$MOCK_DIR:$PATH" "$PROJECT_ROOT/src/i2code/scripts/idea-to-code.sh" "$TEST3_DIR" > /dev/null 2>&1 || true

if [ -f "$MOCK_ARGS_FILE" ] && grep -q '^--non-interactive$' "$MOCK_ARGS_FILE"; then
    pass "Mock i2code received --non-interactive flag"
else
    fail "Mock i2code did not receive --non-interactive flag"
    [ -f "$MOCK_ARGS_FILE" ] && echo "  Actual args:" && cat "$MOCK_ARGS_FILE"
fi

if [ -f "$MOCK_ARGS_FILE" ] && grep -q '^--trunk$' "$MOCK_ARGS_FILE"; then
    pass "Mock i2code received --trunk flag"
else
    fail "Mock i2code did not receive --trunk flag"
    [ -f "$MOCK_ARGS_FILE" ] && echo "  Actual args:" && cat "$MOCK_ARGS_FILE"
fi

# ---------------------------------------------------------------
# Test 4: Config with defaults passes no extra flags
# ---------------------------------------------------------------
echo ""
echo "--- Test 4: Config with defaults passes no extra flags ---"

TEST4_DIR="$TMPDIR_ROOT/test4-idea"
mkdir -p "$TEST4_DIR"
echo "My idea" > "$TEST4_DIR/test4-idea-idea.txt"
echo "# Spec" > "$TEST4_DIR/test4-idea-spec.md"
echo "- [ ] Task 1" > "$TEST4_DIR/test4-idea-plan.md"

# Pre-create config file with default values
printf 'interactive: true\ntrunk: false\n' > "$TEST4_DIR/test4-idea-implement-config.yaml"

create_mock_i2code

# Pipe: 2 (Implement) → 4 (Exit)
printf '%s\n' 2 4 | PATH="$MOCK_DIR:$PATH" "$PROJECT_ROOT/src/i2code/scripts/idea-to-code.sh" "$TEST4_DIR" > /dev/null 2>&1 || true

if [ -f "$MOCK_ARGS_FILE" ] && grep -q '\-\-non-interactive' "$MOCK_ARGS_FILE"; then
    fail "Mock i2code should NOT have --non-interactive flag with default config"
    echo "  Actual args:" && cat "$MOCK_ARGS_FILE"
else
    pass "Mock i2code did not receive --non-interactive flag (correct for defaults)"
fi

if [ -f "$MOCK_ARGS_FILE" ] && grep -q '\-\-trunk' "$MOCK_ARGS_FILE"; then
    fail "Mock i2code should NOT have --trunk flag with default config"
    echo "  Actual args:" && cat "$MOCK_ARGS_FILE"
else
    pass "Mock i2code did not receive --trunk flag (correct for defaults)"
fi

# Verify i2code was called with implement and the idea dir
if [ -f "$MOCK_ARGS_FILE" ] && grep -q '^implement$' "$MOCK_ARGS_FILE"; then
    pass "Mock i2code received 'implement' subcommand"
else
    fail "Mock i2code did not receive 'implement' subcommand"
    [ -f "$MOCK_ARGS_FILE" ] && echo "  Actual args:" && cat "$MOCK_ARGS_FILE"
fi

# ---------------------------------------------------------------
# Test 5: Config display shown when config exists
# ---------------------------------------------------------------
echo ""
echo "--- Test 5: Config display shown when config exists ---"

TEST5_DIR="$TMPDIR_ROOT/test5-idea"
mkdir -p "$TEST5_DIR"
echo "My idea" > "$TEST5_DIR/test5-idea-idea.txt"
echo "# Spec" > "$TEST5_DIR/test5-idea-spec.md"
echo "- [ ] Task 1" > "$TEST5_DIR/test5-idea-plan.md"

# Pre-create config file with non-interactive and trunk
printf 'interactive: false\ntrunk: true\n' > "$TEST5_DIR/test5-idea-implement-config.yaml"

create_mock_i2code

# Capture stderr from the piped run
STDERR5="$TMPDIR_ROOT/test5-stderr"
printf '%s\n' 2 4 | PATH="$MOCK_DIR:$PATH" "$PROJECT_ROOT/src/i2code/scripts/idea-to-code.sh" "$TEST5_DIR" > /dev/null 2>"$STDERR5" || true

if grep -q 'Implementation options:' "$STDERR5"; then
    pass "stderr contains 'Implementation options:'"
else
    fail "stderr does not contain 'Implementation options:'"
    echo "  Captured stderr:" && cat "$STDERR5"
fi

if grep -q 'Mode: non-interactive' "$STDERR5"; then
    pass "stderr contains 'Mode: non-interactive'"
else
    fail "stderr does not contain 'Mode: non-interactive'"
    echo "  Captured stderr:" && cat "$STDERR5"
fi

if grep -q 'Branch: trunk' "$STDERR5"; then
    pass "stderr contains 'Branch: trunk'"
else
    fail "stderr does not contain 'Branch: trunk'"
    echo "  Captured stderr:" && cat "$STDERR5"
fi

# ---------------------------------------------------------------
# Test 6: No prompting when config exists
# ---------------------------------------------------------------
echo ""
echo "--- Test 6: No prompting when config exists ---"

TEST6_DIR="$TMPDIR_ROOT/test6-idea"
mkdir -p "$TEST6_DIR"
echo "My idea" > "$TEST6_DIR/test6-idea-idea.txt"
echo "# Spec" > "$TEST6_DIR/test6-idea-spec.md"
echo "- [ ] Task 1" > "$TEST6_DIR/test6-idea-plan.md"

# Pre-create config file with default values
printf 'interactive: true\ntrunk: false\n' > "$TEST6_DIR/test6-idea-implement-config.yaml"

create_mock_i2code

# Capture stderr from the piped run
STDERR6="$TMPDIR_ROOT/test6-stderr"
printf '%s\n' 2 4 | PATH="$MOCK_DIR:$PATH" "$PROJECT_ROOT/src/i2code/scripts/idea-to-code.sh" "$TEST6_DIR" > /dev/null 2>"$STDERR6" || true

if grep -q 'How should Claude run?' "$STDERR6"; then
    fail "stderr should NOT contain 'How should Claude run?' when config exists"
    echo "  Captured stderr:" && cat "$STDERR6"
else
    pass "stderr does not contain 'How should Claude run?' (prompting skipped)"
fi

if grep -q 'Where should implementation happen?' "$STDERR6"; then
    fail "stderr should NOT contain 'Where should implementation happen?' when config exists"
    echo "  Captured stderr:" && cat "$STDERR6"
else
    pass "stderr does not contain 'Where should implementation happen?' (prompting skipped)"
fi

# ---------------------------------------------------------------
# Test 7: Configure menu overwrites config
# ---------------------------------------------------------------
echo ""
echo "--- Test 7: Configure menu overwrites config ---"

TEST7_DIR="$TMPDIR_ROOT/test7-idea"
mkdir -p "$TEST7_DIR"
echo "My idea" > "$TEST7_DIR/test7-idea-idea.txt"
echo "# Spec" > "$TEST7_DIR/test7-idea-spec.md"
echo "- [ ] Task 1" > "$TEST7_DIR/test7-idea-plan.md"

# Pre-create config file with default values (interactive: true, trunk: false)
printf 'interactive: true\ntrunk: false\n' > "$TEST7_DIR/test7-idea-implement-config.yaml"

create_mock_i2code

# Pipe: 3 (Configure) → 2 (Non-interactive) → 2 (Trunk) → 4 (Exit)
printf '%s\n' 3 2 2 4 | PATH="$MOCK_DIR:$PATH" "$PROJECT_ROOT/src/i2code/scripts/idea-to-code.sh" "$TEST7_DIR" > /dev/null 2>&1 || true

CONFIG7_FILE="$TEST7_DIR/test7-idea-implement-config.yaml"

if [ -f "$CONFIG7_FILE" ] && grep -q 'interactive: false' "$CONFIG7_FILE"; then
    pass "Config file overwritten with 'interactive: false'"
else
    fail "Config file does not contain 'interactive: false'"
    [ -f "$CONFIG7_FILE" ] && echo "  Actual config:" && cat "$CONFIG7_FILE"
fi

if [ -f "$CONFIG7_FILE" ] && grep -q 'trunk: true' "$CONFIG7_FILE"; then
    pass "Config file overwritten with 'trunk: true'"
else
    fail "Config file does not contain 'trunk: true'"
    [ -f "$CONFIG7_FILE" ] && echo "  Actual config:" && cat "$CONFIG7_FILE"
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
