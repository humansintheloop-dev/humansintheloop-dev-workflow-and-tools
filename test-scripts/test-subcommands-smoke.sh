#!/usr/bin/env bash
# Smoke tests for i2code subcommand groups and their subcommands.
# Verifies that groups and subcommands are discoverable via --help.
set -euo pipefail

echo "=== Subcommand Smoke Tests ==="

# --- idea-to-plan group is listed in i2code --help ---
echo ""
echo "--- i2code --help lists idea-to-plan ---"
OUTPUT=$(uv run i2code --help 2>&1)
echo "$OUTPUT"
if [[ "$OUTPUT" != *"idea-to-plan"* ]]; then
    echo "FAIL: i2code --help does not list idea-to-plan"
    exit 1
fi
echo "PASS: idea-to-plan listed in i2code --help"

# --- brainstorm is listed in idea-to-plan --help ---
echo ""
echo "--- i2code idea-to-plan --help lists brainstorm ---"
OUTPUT=$(uv run i2code idea-to-plan --help 2>&1)
echo "$OUTPUT"
if [[ "$OUTPUT" != *"brainstorm"* ]]; then
    echo "FAIL: idea-to-plan --help does not list brainstorm"
    exit 1
fi
echo "PASS: brainstorm listed in idea-to-plan --help"

# --- brainstorm --help exits 0 ---
echo ""
echo "--- i2code idea-to-plan brainstorm --help exits 0 ---"
OUTPUT=$(uv run i2code idea-to-plan brainstorm --help 2>&1)
echo "$OUTPUT"
echo "PASS: idea-to-plan brainstorm --help exits 0"

# --- spec is listed in idea-to-plan --help ---
echo ""
echo "--- i2code idea-to-plan --help lists spec ---"
OUTPUT=$(uv run i2code idea-to-plan --help 2>&1)
echo "$OUTPUT"
if [[ "$OUTPUT" != *"spec"* ]]; then
    echo "FAIL: idea-to-plan --help does not list spec"
    exit 1
fi
echo "PASS: spec listed in idea-to-plan --help"

# --- spec --help exits 0 ---
echo ""
echo "--- i2code idea-to-plan spec --help exits 0 ---"
OUTPUT=$(uv run i2code idea-to-plan spec --help 2>&1)
echo "$OUTPUT"
echo "PASS: idea-to-plan spec --help exits 0"

# --- revise-spec is listed in idea-to-plan --help ---
echo ""
echo "--- i2code idea-to-plan --help lists revise-spec ---"
OUTPUT=$(uv run i2code idea-to-plan --help 2>&1)
echo "$OUTPUT"
if [[ "$OUTPUT" != *"revise-spec"* ]]; then
    echo "FAIL: idea-to-plan --help does not list revise-spec"
    exit 1
fi
echo "PASS: revise-spec listed in idea-to-plan --help"

# --- revise-spec --help exits 0 ---
echo ""
echo "--- i2code idea-to-plan revise-spec --help exits 0 ---"
OUTPUT=$(uv run i2code idea-to-plan revise-spec --help 2>&1)
echo "$OUTPUT"
echo "PASS: idea-to-plan revise-spec --help exits 0"

echo ""
echo "=== All Subcommand Smoke Tests Passed ==="
