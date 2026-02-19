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

# --- revise-plan is listed in idea-to-plan --help ---
echo ""
echo "--- i2code idea-to-plan --help lists revise-plan ---"
OUTPUT=$(uv run i2code idea-to-plan --help 2>&1)
echo "$OUTPUT"
if [[ "$OUTPUT" != *"revise-plan"* ]]; then
    echo "FAIL: idea-to-plan --help does not list revise-plan"
    exit 1
fi
echo "PASS: revise-plan listed in idea-to-plan --help"

# --- revise-plan --help exits 0 ---
echo ""
echo "--- i2code idea-to-plan revise-plan --help exits 0 ---"
OUTPUT=$(uv run i2code idea-to-plan revise-plan --help 2>&1)
echo "$OUTPUT"
echo "PASS: idea-to-plan revise-plan --help exits 0"

# --- make-plan is listed in idea-to-plan --help ---
echo ""
echo "--- i2code idea-to-plan --help lists make-plan ---"
OUTPUT=$(uv run i2code idea-to-plan --help 2>&1)
echo "$OUTPUT"
if [[ "$OUTPUT" != *"make-plan"* ]]; then
    echo "FAIL: idea-to-plan --help does not list make-plan"
    exit 1
fi
echo "PASS: make-plan listed in idea-to-plan --help"

# --- make-plan --help exits 0 ---
echo ""
echo "--- i2code idea-to-plan make-plan --help exits 0 ---"
OUTPUT=$(uv run i2code idea-to-plan make-plan --help 2>&1)
echo "$OUTPUT"
echo "PASS: idea-to-plan make-plan --help exits 0"

# --- design-doc is listed in idea-to-plan --help ---
echo ""
echo "--- i2code idea-to-plan --help lists design-doc ---"
OUTPUT=$(uv run i2code idea-to-plan --help 2>&1)
echo "$OUTPUT"
if [[ "$OUTPUT" != *"design-doc"* ]]; then
    echo "FAIL: idea-to-plan --help does not list design-doc"
    exit 1
fi
echo "PASS: design-doc listed in idea-to-plan --help"

# --- design-doc --help exits 0 ---
echo ""
echo "--- i2code idea-to-plan design-doc --help exits 0 ---"
OUTPUT=$(uv run i2code idea-to-plan design-doc --help 2>&1)
echo "$OUTPUT"
echo "PASS: idea-to-plan design-doc --help exits 0"

# --- run is listed in idea-to-plan --help ---
echo ""
echo "--- i2code idea-to-plan --help lists run ---"
OUTPUT=$(uv run i2code idea-to-plan --help 2>&1)
echo "$OUTPUT"
if [[ "$OUTPUT" != *"run"* ]]; then
    echo "FAIL: idea-to-plan --help does not list run"
    exit 1
fi
echo "PASS: run listed in idea-to-plan --help"

# --- run --help exits 0 ---
echo ""
echo "--- i2code idea-to-plan run --help exits 0 ---"
OUTPUT=$(uv run i2code idea-to-plan run --help 2>&1)
echo "$OUTPUT"
echo "PASS: idea-to-plan run --help exits 0"

# --- improve group is listed in i2code --help ---
echo ""
echo "--- i2code --help lists improve ---"
OUTPUT=$(uv run i2code --help 2>&1)
echo "$OUTPUT"
if [[ "$OUTPUT" != *"improve"* ]]; then
    echo "FAIL: i2code --help does not list improve"
    exit 1
fi
echo "PASS: improve listed in i2code --help"

# --- analyze-sessions is listed in improve --help ---
echo ""
echo "--- i2code improve --help lists analyze-sessions ---"
OUTPUT=$(uv run i2code improve --help 2>&1)
echo "$OUTPUT"
if [[ "$OUTPUT" != *"analyze-sessions"* ]]; then
    echo "FAIL: improve --help does not list analyze-sessions"
    exit 1
fi
echo "PASS: analyze-sessions listed in improve --help"

# --- analyze-sessions --help exits 0 ---
echo ""
echo "--- i2code improve analyze-sessions --help exits 0 ---"
OUTPUT=$(uv run i2code improve analyze-sessions --help 2>&1)
echo "$OUTPUT"
echo "PASS: improve analyze-sessions --help exits 0"

# --- summary-reports is listed in improve --help ---
echo ""
echo "--- i2code improve --help lists summary-reports ---"
OUTPUT=$(uv run i2code improve --help 2>&1)
echo "$OUTPUT"
if [[ "$OUTPUT" != *"summary-reports"* ]]; then
    echo "FAIL: improve --help does not list summary-reports"
    exit 1
fi
echo "PASS: summary-reports listed in improve --help"

# --- summary-reports --help exits 0 ---
echo ""
echo "--- i2code improve summary-reports --help exits 0 ---"
OUTPUT=$(uv run i2code improve summary-reports --help 2>&1)
echo "$OUTPUT"
echo "PASS: improve summary-reports --help exits 0"

# --- review-issues is listed in improve --help ---
echo ""
echo "--- i2code improve --help lists review-issues ---"
OUTPUT=$(uv run i2code improve --help 2>&1)
echo "$OUTPUT"
if [[ "$OUTPUT" != *"review-issues"* ]]; then
    echo "FAIL: improve --help does not list review-issues"
    exit 1
fi
echo "PASS: review-issues listed in improve --help"

# --- review-issues --help exits 0 ---
echo ""
echo "--- i2code improve review-issues --help exits 0 ---"
OUTPUT=$(uv run i2code improve review-issues --help 2>&1)
echo "$OUTPUT"
echo "PASS: improve review-issues --help exits 0"

echo ""
echo "=== All Subcommand Smoke Tests Passed ==="
