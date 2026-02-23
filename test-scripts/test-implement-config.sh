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
# Test 8: Corrupt config triggers re-prompting
# ---------------------------------------------------------------
echo ""
echo "--- Test 8: Corrupt config triggers re-prompting ---"

TEST8_DIR="$TMPDIR_ROOT/test8-idea"
mkdir -p "$TEST8_DIR"
echo "My idea" > "$TEST8_DIR/test8-idea-idea.txt"
echo "# Spec" > "$TEST8_DIR/test8-idea-spec.md"
echo "- [ ] Task 1" > "$TEST8_DIR/test8-idea-plan.md"

# Write corrupt content to config file
echo "not yaml garbage" > "$TEST8_DIR/test8-idea-implement-config.yaml"

create_mock_i2code

# Capture stderr; pipe: 2 (Implement) → 1 (Interactive) → 1 (Worktree) → 4 (Exit)
STDERR8="$TMPDIR_ROOT/test8-stderr"
printf '%s\n' 2 1 1 4 | PATH="$MOCK_DIR:$PATH" "$PROJECT_ROOT/src/i2code/scripts/idea-to-code.sh" "$TEST8_DIR" > /dev/null 2>"$STDERR8" || true

if grep -q 'How should Claude run?' "$STDERR8"; then
    pass "Corrupt config: stderr contains 'How should Claude run?' (prompting occurred)"
else
    fail "Corrupt config: stderr does not contain 'How should Claude run?'"
    echo "  Captured stderr:" && cat "$STDERR8"
fi

CONFIG8_FILE="$TEST8_DIR/test8-idea-implement-config.yaml"
if [ -f "$CONFIG8_FILE" ] && grep -q 'interactive: true' "$CONFIG8_FILE"; then
    pass "Corrupt config: new config has 'interactive: true'"
else
    fail "Corrupt config: new config does not have 'interactive: true'"
    [ -f "$CONFIG8_FILE" ] && echo "  Actual config:" && cat "$CONFIG8_FILE"
fi

if [ -f "$CONFIG8_FILE" ] && grep -q 'trunk: false' "$CONFIG8_FILE"; then
    pass "Corrupt config: new config has 'trunk: false'"
else
    fail "Corrupt config: new config does not have 'trunk: false'"
    [ -f "$CONFIG8_FILE" ] && echo "  Actual config:" && cat "$CONFIG8_FILE"
fi

# ---------------------------------------------------------------
# Test 9: Empty config triggers re-prompting
# ---------------------------------------------------------------
echo ""
echo "--- Test 9: Empty config triggers re-prompting ---"

TEST9_DIR="$TMPDIR_ROOT/test9-idea"
mkdir -p "$TEST9_DIR"
echo "My idea" > "$TEST9_DIR/test9-idea-idea.txt"
echo "# Spec" > "$TEST9_DIR/test9-idea-spec.md"
echo "- [ ] Task 1" > "$TEST9_DIR/test9-idea-plan.md"

# Write empty file as config
: > "$TEST9_DIR/test9-idea-implement-config.yaml"

create_mock_i2code

# Capture stderr; pipe: 2 (Implement) → 1 (Interactive) → 1 (Worktree) → 4 (Exit)
STDERR9="$TMPDIR_ROOT/test9-stderr"
printf '%s\n' 2 1 1 4 | PATH="$MOCK_DIR:$PATH" "$PROJECT_ROOT/src/i2code/scripts/idea-to-code.sh" "$TEST9_DIR" > /dev/null 2>"$STDERR9" || true

if grep -q 'How should Claude run?' "$STDERR9"; then
    pass "Empty config: stderr contains 'How should Claude run?' (prompting occurred)"
else
    fail "Empty config: stderr does not contain 'How should Claude run?'"
    echo "  Captured stderr:" && cat "$STDERR9"
fi

CONFIG9_FILE="$TEST9_DIR/test9-idea-implement-config.yaml"
if [ -f "$CONFIG9_FILE" ] && grep -q 'interactive: true' "$CONFIG9_FILE"; then
    pass "Empty config: new config has 'interactive: true'"
else
    fail "Empty config: new config does not have 'interactive: true'"
    [ -f "$CONFIG9_FILE" ] && echo "  Actual config:" && cat "$CONFIG9_FILE"
fi

if [ -f "$CONFIG9_FILE" ] && grep -q 'trunk: false' "$CONFIG9_FILE"; then
    pass "Empty config: new config has 'trunk: false'"
else
    fail "Empty config: new config does not have 'trunk: false'"
    [ -f "$CONFIG9_FILE" ] && echo "  Actual config:" && cat "$CONFIG9_FILE"
fi

# ---------------------------------------------------------------
# Test 10: Partial config (one valid field) does NOT trigger re-prompting
# ---------------------------------------------------------------
echo ""
echo "--- Test 10: Partial config does NOT trigger re-prompting ---"

TEST10_DIR="$TMPDIR_ROOT/test10-idea"
mkdir -p "$TEST10_DIR"
echo "My idea" > "$TEST10_DIR/test10-idea-idea.txt"
echo "# Spec" > "$TEST10_DIR/test10-idea-spec.md"
echo "- [ ] Task 1" > "$TEST10_DIR/test10-idea-plan.md"

# Config with only trunk: true (no interactive: line)
printf 'trunk: true\n' > "$TEST10_DIR/test10-idea-implement-config.yaml"

create_mock_i2code

# Capture stderr; pipe: 2 (Implement) → 4 (Exit)
STDERR10="$TMPDIR_ROOT/test10-stderr"
printf '%s\n' 2 4 | PATH="$MOCK_DIR:$PATH" "$PROJECT_ROOT/src/i2code/scripts/idea-to-code.sh" "$TEST10_DIR" > /dev/null 2>"$STDERR10" || true

if grep -q 'How should Claude run?' "$STDERR10"; then
    fail "Partial config: stderr should NOT contain 'How should Claude run?' (should not re-prompt)"
    echo "  Captured stderr:" && cat "$STDERR10"
else
    pass "Partial config: no re-prompting occurred (correct)"
fi

# Verify defaults were applied: trunk: true from file, interactive defaults to true
if grep -q 'Mode: interactive' "$STDERR10"; then
    pass "Partial config: default 'Mode: interactive' applied"
else
    fail "Partial config: 'Mode: interactive' not shown in stderr"
    echo "  Captured stderr:" && cat "$STDERR10"
fi

if grep -q 'Branch: trunk' "$STDERR10"; then
    pass "Partial config: 'Branch: trunk' read from file"
else
    fail "Partial config: 'Branch: trunk' not shown in stderr"
    echo "  Captured stderr:" && cat "$STDERR10"
fi

# ---------------------------------------------------------------
# Test 11: Menu option shows invocation when config exists
# ---------------------------------------------------------------
echo ""
echo "--- Test 11: Menu option shows invocation when config exists ---"

TEST11_DIR="$TMPDIR_ROOT/test11-idea"
mkdir -p "$TEST11_DIR"
echo "My idea" > "$TEST11_DIR/test11-idea-idea.txt"
echo "# Spec" > "$TEST11_DIR/test11-idea-spec.md"
echo "- [ ] Task 1" > "$TEST11_DIR/test11-idea-plan.md"

# Pre-create config with non-interactive and trunk
printf 'interactive: false\ntrunk: true\n' > "$TEST11_DIR/test11-idea-implement-config.yaml"

create_mock_i2code

# Capture stderr; pipe: 2 (Implement) → 4 (Exit)
STDERR11="$TMPDIR_ROOT/test11-stderr"
printf '%s\n' 2 4 | PATH="$MOCK_DIR:$PATH" "$PROJECT_ROOT/src/i2code/scripts/idea-to-code.sh" "$TEST11_DIR" > /dev/null 2>"$STDERR11" || true

if grep -q 'i2code implement --non-interactive --trunk' "$STDERR11"; then
    pass "Menu option shows 'i2code implement --non-interactive --trunk'"
else
    fail "Menu option does not show 'i2code implement --non-interactive --trunk'"
    echo "  Captured stderr:" && cat "$STDERR11"
fi

# ---------------------------------------------------------------
# Test 12: Menu option shows invocation with no flags for default config
# ---------------------------------------------------------------
echo ""
echo "--- Test 12: Menu option shows invocation with no flags for default config ---"

TEST12_DIR="$TMPDIR_ROOT/test12-idea"
mkdir -p "$TEST12_DIR"
echo "My idea" > "$TEST12_DIR/test12-idea-idea.txt"
echo "# Spec" > "$TEST12_DIR/test12-idea-spec.md"
echo "- [ ] Task 1" > "$TEST12_DIR/test12-idea-plan.md"

# Pre-create config with defaults
printf 'interactive: true\ntrunk: false\n' > "$TEST12_DIR/test12-idea-implement-config.yaml"

create_mock_i2code

# Capture stderr; pipe: 2 (Implement) → 4 (Exit)
STDERR12="$TMPDIR_ROOT/test12-stderr"
printf '%s\n' 2 4 | PATH="$MOCK_DIR:$PATH" "$PROJECT_ROOT/src/i2code/scripts/idea-to-code.sh" "$TEST12_DIR" > /dev/null 2>"$STDERR12" || true

# Should show "i2code implement" in the menu (no extra flags)
if grep -q 'Implement the entire plan: i2code implement' "$STDERR12"; then
    pass "Menu option shows 'i2code implement' for default config"
else
    fail "Menu option does not show 'i2code implement' for default config"
    echo "  Captured stderr:" && cat "$STDERR12"
fi

# Should NOT show --non-interactive or --trunk in the menu line
if grep 'Implement the entire plan:' "$STDERR12" | grep -q '\-\-non-interactive\|--trunk'; then
    fail "Menu option should NOT show flags for default config"
    echo "  Captured stderr:" && cat "$STDERR12"
else
    pass "Menu option correctly omits flags for default config"
fi

# ---------------------------------------------------------------
# Test 13: First menu shows invocation even when no config file exists
# ---------------------------------------------------------------
echo ""
echo "--- Test 13: First menu shows invocation even when no config file exists ---"

TEST13_DIR="$TMPDIR_ROOT/test13-idea"
mkdir -p "$TEST13_DIR"
echo "My idea" > "$TEST13_DIR/test13-idea-idea.txt"
echo "# Spec" > "$TEST13_DIR/test13-idea-spec.md"
echo "- [ ] Task 1" > "$TEST13_DIR/test13-idea-plan.md"
# No config file created

create_mock_i2code

# Capture stderr; pipe: 2 (Implement) → 1 (Interactive) → 1 (Worktree) → 4 (Exit)
STDERR13="$TMPDIR_ROOT/test13-stderr"
printf '%s\n' 2 1 1 4 | PATH="$MOCK_DIR:$PATH" "$PROJECT_ROOT/src/i2code/scripts/idea-to-code.sh" "$TEST13_DIR" > /dev/null 2>"$STDERR13" || true

# Extract only the FIRST menu block (lines before "How should Claude run?")
FIRST_MENU13="$TMPDIR_ROOT/test13-first-menu"
sed '/How should Claude run/q' "$STDERR13" > "$FIRST_MENU13"

# First menu should show "i2code implement" even without config (defaults = no flags)
if grep -q 'Implement the entire plan: i2code implement' "$FIRST_MENU13"; then
    pass "First menu shows 'i2code implement' even without config file"
else
    fail "First menu does not show 'i2code implement' without config file"
    echo "  First menu output:" && cat "$FIRST_MENU13"
fi

# ---------------------------------------------------------------
# Test 14: Configure option shown in uncommitted-changes menu when config exists
# ---------------------------------------------------------------
echo ""
echo "--- Test 14: Configure option shown in uncommitted-changes menu when config exists ---"

# Set up idea dir inside a temporary git repo with uncommitted changes
TEST14_REPO="$TMPDIR_ROOT/test14-repo"
mkdir -p "$TEST14_REPO"
git init "$TEST14_REPO" > /dev/null 2>&1
(cd "$TEST14_REPO" && git config user.email "test@test" && git config user.name "test" && git commit --allow-empty -m "init" > /dev/null 2>&1)
TEST14_IDEA="$TEST14_REPO/test14-idea"
mkdir -p "$TEST14_IDEA"
echo "My idea" > "$TEST14_IDEA/test14-idea-idea.txt"
echo "# Spec" > "$TEST14_IDEA/test14-idea-spec.md"
echo "- [ ] Task 1" > "$TEST14_IDEA/test14-idea-plan.md"
printf 'interactive: false\ntrunk: true\n' > "$TEST14_IDEA/test14-idea-implement-config.yaml"
# Stage a file so git status shows uncommitted changes
(cd "$TEST14_REPO" && git add "$TEST14_IDEA/test14-idea-idea.txt")

create_mock_i2code

# Run from INSIDE the test repo so has_uncommitted_changes detects staged files
STDERR14="$TMPDIR_ROOT/test14-stderr"
(cd "$TEST14_REPO" && printf '%s\n' 5 4 | PATH="$MOCK_DIR:$PATH" "$PROJECT_ROOT/src/i2code/scripts/idea-to-code.sh" "$TEST14_IDEA" > /dev/null 2>"$STDERR14") || true

# Verify we actually hit the uncommitted-changes branch (should see "Commit changes")
if grep -q 'Commit changes' "$STDERR14"; then
    pass "Uncommitted-changes menu branch detected"
else
    fail "Did NOT hit uncommitted-changes menu branch"
    echo "  Captured stderr:" && cat "$STDERR14"
fi

if grep -q 'Configure implement options' "$STDERR14"; then
    pass "Configure option shown in uncommitted-changes menu when config exists"
else
    fail "Configure option NOT shown in uncommitted-changes menu when config exists"
    echo "  Captured stderr:" && cat "$STDERR14"
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
