#!/usr/bin/env bash
# Test script for _python_helper.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
HELPER_SCRIPT="$REPO_ROOT/workflow-scripts/_python_helper.sh"

# Test directory (isolated from production)
TEST_WORKDIR=$(mktemp -d)
trap 'rm -rf $TEST_WORKDIR' EXIT

echo "=== Testing _python_helper.sh ==="
echo "Test workdir: $TEST_WORKDIR"

# Test 1: Helper script exists
echo -n "Test 1: Helper script exists... "
if [ -f "$HELPER_SCRIPT" ]; then
    echo "PASS"
else
    echo "FAIL - $HELPER_SCRIPT not found"
    exit 1
fi

# Test 2: Helper script is sourceable
echo -n "Test 2: Helper script is sourceable... "
cd "$TEST_WORKDIR"
# Create a minimal workflow-scripts directory structure for testing
mkdir -p workflow-scripts
cp "$HELPER_SCRIPT" workflow-scripts/
# Create requirements.txt for the test
echo "pytest" > workflow-scripts/requirements.txt

# Source the helper (should not error)
if source workflow-scripts/_python_helper.sh 2>/dev/null; then
    echo "PASS"
else
    echo "FAIL - could not source helper"
    exit 1
fi

# Test 3: ensure_venv function exists
echo -n "Test 3: ensure_venv function exists... "
if type ensure_venv &>/dev/null; then
    echo "PASS"
else
    echo "FAIL - ensure_venv function not defined"
    exit 1
fi

# Test 4: run_python function exists
echo -n "Test 4: run_python function exists... "
if type run_python &>/dev/null; then
    echo "PASS"
else
    echo "FAIL - run_python function not defined"
    exit 1
fi

# Test 5: ensure_venv creates .venv directory
echo -n "Test 5: ensure_venv creates .venv directory... "
cd "$TEST_WORKDIR/workflow-scripts"
ensure_venv
if [ -d ".venv" ]; then
    echo "PASS"
else
    echo "FAIL - .venv directory not created"
    exit 1
fi

# Test 6: .venv contains Python executable
echo -n "Test 6: .venv contains Python executable... "
if [ -x ".venv/bin/python" ]; then
    echo "PASS"
else
    echo "FAIL - .venv/bin/python not found or not executable"
    exit 1
fi

# Test 7: pytest is installed in venv
echo -n "Test 7: pytest is installed in venv... "
if .venv/bin/python -c "import pytest" 2>/dev/null; then
    echo "PASS"
else
    echo "FAIL - pytest not installed in venv"
    exit 1
fi

# Test 8: run_python executes a Python script
echo -n "Test 8: run_python executes a Python script... "
echo 'print("hello from python")' > test_script.py
OUTPUT=$(run_python test_script.py)
if [ "$OUTPUT" = "hello from python" ]; then
    echo "PASS"
else
    echo "FAIL - expected 'hello from python', got '$OUTPUT'"
    exit 1
fi

# Test 9: run_python passes arguments to script
echo -n "Test 9: run_python passes arguments to script... "
echo 'import sys; print(sys.argv[1])' > test_args.py
OUTPUT=$(run_python test_args.py "test_argument")
if [ "$OUTPUT" = "test_argument" ]; then
    echo "PASS"
else
    echo "FAIL - expected 'test_argument', got '$OUTPUT'"
    exit 1
fi

echo ""
echo "=== All tests passed ==="
