#!/usr/bin/env bash
# Test script for implement-with-worktree.sh CLI argument handling

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
SCRIPT="$REPO_ROOT/workflow-scripts/implement-with-worktree.sh"

echo "=== Testing implement-with-worktree.sh CLI ==="

# Test 1: Script exists
echo -n "Test 1: Script exists... "
if [ -f "$SCRIPT" ]; then
    echo "PASS"
else
    echo "FAIL - $SCRIPT not found"
    exit 1
fi

# Test 2: Script is executable
echo -n "Test 2: Script is executable... "
if [ -x "$SCRIPT" ]; then
    echo "PASS"
else
    echo "FAIL - $SCRIPT is not executable"
    exit 1
fi

# Test 3: Script shows usage and exits with error when no arguments provided
echo -n "Test 3: No arguments shows usage and exits with error... "
set +e
OUTPUT=$("$SCRIPT" 2>&1)
EXIT_CODE=$?
set -e
# Check that it mentions idea-directory in the error/usage
if echo "$OUTPUT" | grep -qi "idea.directory\|usage"; then
    if [ $EXIT_CODE -ne 0 ]; then
        echo "PASS"
    else
        echo "FAIL - should exit with non-zero when no arguments"
        exit 1
    fi
else
    echo "FAIL - output should mention idea-directory or usage"
    echo "Output was: $OUTPUT"
    exit 1
fi

# Test 4: Script accepts idea-directory argument without error
echo -n "Test 4: Accepts idea-directory argument... "
# We just test that it doesn't fail on argument parsing
# It will fail later because the directory doesn't exist, which is expected
OUTPUT=$("$SCRIPT" /some/fake/path 2>&1 || true)
# Check that it doesn't complain about missing required argument
if echo "$OUTPUT" | grep -qi "required\|usage"; then
    echo "FAIL - should not complain about missing required argument when path is provided"
    echo "Output was: $OUTPUT"
    exit 1
else
    echo "PASS"
fi

# Test 5: Script accepts --cleanup flag
echo -n "Test 5: Accepts --cleanup flag... "
OUTPUT=$("$SCRIPT" /some/fake/path --cleanup 2>&1 || true)
# Check that it doesn't complain about unrecognized argument
if echo "$OUTPUT" | grep -qi "unrecognized\|invalid option"; then
    echo "FAIL - should recognize --cleanup flag"
    echo "Output was: $OUTPUT"
    exit 1
else
    echo "PASS"
fi

# Test 6: Python script exists
echo -n "Test 6: Python script exists... "
PY_SCRIPT="$REPO_ROOT/workflow-scripts/implement-with-worktree.py"
if [ -f "$PY_SCRIPT" ]; then
    echo "PASS"
else
    echo "FAIL - $PY_SCRIPT not found"
    exit 1
fi

echo ""
echo "=== All CLI tests passed ==="
