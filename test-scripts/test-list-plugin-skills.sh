#!/usr/bin/env bash
# Tests for list-plugin-skills.sh
# Validates output format when plugin exists and when absent.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
LIST_SKILLS="$PROJECT_ROOT/src/i2code/scripts/list-plugin-skills.sh"

echo "=== list-plugin-skills.sh Tests ==="

# --- Test 1: Plugin exists with multiple skills ---
echo ""
echo "--- Test: outputs comma-separated skills when plugin exists ---"

TMPDIR_TEST=$(mktemp -d)
trap 'rm -rf "$TMPDIR_TEST"' EXIT

# Create fake plugin cache structure
FAKE_PLUGIN="$TMPDIR_TEST/idea-to-code-marketplace/idea-to-code/1.0.0/skills"
mkdir -p "$FAKE_PLUGIN/tdd"
mkdir -p "$FAKE_PLUGIN/plan-tracking"
mkdir -p "$FAKE_PLUGIN/commit-guidelines"

OUTPUT=$(PLUGIN_CACHE_DIR="$TMPDIR_TEST" "$LIST_SKILLS")

# Verify comma-separated format with idea-to-code: prefix
# Sort both expected and actual to handle directory listing order
EXPECTED="idea-to-code:commit-guidelines, idea-to-code:plan-tracking, idea-to-code:tdd"
SORTED_OUTPUT=$(echo "$OUTPUT" | tr ',' '\n' | sed 's/^ //' | sort | tr '\n' ',' | sed 's/,$//' | sed 's/,/, /g')
SORTED_EXPECTED=$(echo "$EXPECTED" | tr ',' '\n' | sed 's/^ //' | sort | tr '\n' ',' | sed 's/,$//' | sed 's/,/, /g')

if [[ "$SORTED_OUTPUT" != "$SORTED_EXPECTED" ]]; then
    echo "FAIL: Expected '$SORTED_EXPECTED' but got '$SORTED_OUTPUT'"
    exit 1
fi
echo "PASS: outputs comma-separated skills when plugin exists"

# --- Test 2: Plugin not installed ---
echo ""
echo "--- Test: outputs empty string and warning when plugin absent ---"

EMPTY_DIR=$(mktemp -d)
# Don't add to trap since we'll clean up manually or it's in the same parent

STDERR_FILE=$(mktemp)
OUTPUT=$(PLUGIN_CACHE_DIR="$EMPTY_DIR" "$LIST_SKILLS" 2>"$STDERR_FILE") || true
STDERR_OUTPUT=$(cat "$STDERR_FILE")
rm -f "$STDERR_FILE"
rm -rf "$EMPTY_DIR"

if [[ -n "$OUTPUT" ]]; then
    echo "FAIL: Expected empty output but got '$OUTPUT'"
    exit 1
fi

if [[ "$STDERR_OUTPUT" != *"warning"* && "$STDERR_OUTPUT" != *"Warning"* && "$STDERR_OUTPUT" != *"WARNING"* ]]; then
    echo "FAIL: Expected warning on stderr but got '$STDERR_OUTPUT'"
    exit 1
fi
echo "PASS: outputs empty string and warning when plugin absent"

# --- Test 3: Plugin exists with single skill ---
echo ""
echo "--- Test: outputs single skill without trailing comma ---"

SINGLE_DIR=$(mktemp -d)
SINGLE_PLUGIN="$SINGLE_DIR/idea-to-code-marketplace/idea-to-code/1.0.0/skills"
mkdir -p "$SINGLE_PLUGIN/tdd"

OUTPUT=$(PLUGIN_CACHE_DIR="$SINGLE_DIR" "$LIST_SKILLS")
rm -rf "$SINGLE_DIR"

if [[ "$OUTPUT" != "idea-to-code:tdd" ]]; then
    echo "FAIL: Expected 'idea-to-code:tdd' but got '$OUTPUT'"
    exit 1
fi
echo "PASS: outputs single skill without trailing comma"

echo ""
echo "=== All list-plugin-skills.sh Tests Passed ==="
