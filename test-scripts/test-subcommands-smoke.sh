#!/usr/bin/env bash
# Smoke tests for i2code subcommand groups and their subcommands.
# Verifies that groups and subcommands are discoverable via --help.
set -euo pipefail

echo "=== Subcommand Smoke Tests ==="

# --- go --help exits 0 ---
echo ""
echo "--- i2code go --help exits 0 ---"
uv run i2code go --help
echo "PASS: go --help exits 0"

# --- idea --help lists brainstorm ---
echo ""
echo "--- i2code idea --help lists brainstorm ---"
OUTPUT=$(uv run i2code idea --help 2>&1)
echo "$OUTPUT"
if [[ "$OUTPUT" != *"brainstorm"* ]]; then
    echo "FAIL: idea --help does not list brainstorm"
    exit 1
fi
echo "PASS: brainstorm listed in idea --help"

# --- idea brainstorm --help exits 0 ---
echo ""
echo "--- i2code idea brainstorm --help exits 0 ---"
uv run i2code idea brainstorm --help
echo "PASS: idea brainstorm --help exits 0"

# --- spec --help lists create and revise ---
echo ""
echo "--- i2code spec --help lists create and revise ---"
OUTPUT=$(uv run i2code spec --help 2>&1)
echo "$OUTPUT"
if [[ "$OUTPUT" != *"create"* ]]; then
    echo "FAIL: spec --help does not list create"
    exit 1
fi
if [[ "$OUTPUT" != *"revise"* ]]; then
    echo "FAIL: spec --help does not list revise"
    exit 1
fi
echo "PASS: create and revise listed in spec --help"

# --- spec create --help exits 0 ---
echo ""
echo "--- i2code spec create --help exits 0 ---"
uv run i2code spec create --help
echo "PASS: spec create --help exits 0"

# --- spec revise --help exits 0 ---
echo ""
echo "--- i2code spec revise --help exits 0 ---"
uv run i2code spec revise --help
echo "PASS: spec revise --help exits 0"

# --- plan --help lists create and revise ---
echo ""
echo "--- i2code plan --help lists create and revise ---"
OUTPUT=$(uv run i2code plan --help 2>&1)
echo "$OUTPUT"
if [[ "$OUTPUT" != *"create"* ]]; then
    echo "FAIL: plan --help does not list create"
    exit 1
fi
if [[ "$OUTPUT" != *"revise"* ]]; then
    echo "FAIL: plan --help does not list revise"
    exit 1
fi
echo "PASS: create and revise listed in plan --help"

# --- plan create --help exits 0 ---
echo ""
echo "--- i2code plan create --help exits 0 ---"
uv run i2code plan create --help
echo "PASS: plan create --help exits 0"

# --- plan revise --help exits 0 ---
echo ""
echo "--- i2code plan revise --help exits 0 ---"
uv run i2code plan revise --help
echo "PASS: plan revise --help exits 0"

# --- design --help lists create ---
echo ""
echo "--- i2code design --help lists create ---"
OUTPUT=$(uv run i2code design --help 2>&1)
echo "$OUTPUT"
if [[ "$OUTPUT" != *"create"* ]]; then
    echo "FAIL: design --help does not list create"
    exit 1
fi
echo "PASS: create listed in design --help"

# --- design create --help exits 0 ---
echo ""
echo "--- i2code design create --help exits 0 ---"
uv run i2code design create --help
echo "PASS: design create --help exits 0"

# --- i2code --help does NOT list idea-to-plan ---
echo ""
echo "--- i2code --help does NOT list idea-to-plan ---"
OUTPUT=$(uv run i2code --help 2>&1)
echo "$OUTPUT"
if [[ "$OUTPUT" == *"idea-to-plan"* ]]; then
    echo "FAIL: i2code --help still lists idea-to-plan"
    exit 1
fi
echo "PASS: idea-to-plan no longer listed in i2code --help"

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
uv run i2code improve analyze-sessions --help
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
uv run i2code improve summary-reports --help
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
uv run i2code improve review-issues --help
echo "PASS: improve review-issues --help exits 0"

# --- update-claude-files is listed in improve --help ---
echo ""
echo "--- i2code improve --help lists update-claude-files ---"
OUTPUT=$(uv run i2code improve --help 2>&1)
echo "$OUTPUT"
if [[ "$OUTPUT" != *"update-claude-files"* ]]; then
    echo "FAIL: improve --help does not list update-claude-files"
    exit 1
fi
echo "PASS: update-claude-files listed in improve --help"

# --- update-claude-files --help exits 0 ---
echo ""
echo "--- i2code improve update-claude-files --help exits 0 ---"
uv run i2code improve update-claude-files --help
echo "PASS: improve update-claude-files --help exits 0"

# --- setup group is listed in i2code --help ---
echo ""
echo "--- i2code --help lists setup ---"
OUTPUT=$(uv run i2code --help 2>&1)
echo "$OUTPUT"
if [[ "$OUTPUT" != *"setup"* ]]; then
    echo "FAIL: i2code --help does not list setup"
    exit 1
fi
echo "PASS: setup listed in i2code --help"

# --- claude-files is listed in setup --help ---
echo ""
echo "--- i2code setup --help lists claude-files ---"
OUTPUT=$(uv run i2code setup --help 2>&1)
echo "$OUTPUT"
if [[ "$OUTPUT" != *"claude-files"* ]]; then
    echo "FAIL: setup --help does not list claude-files"
    exit 1
fi
echo "PASS: claude-files listed in setup --help"

# --- claude-files --help exits 0 ---
echo ""
echo "--- i2code setup claude-files --help exits 0 ---"
uv run i2code setup claude-files --help
echo "PASS: setup claude-files --help exits 0"

# --- update-project is listed in setup --help ---
echo ""
echo "--- i2code setup --help lists update-project ---"
OUTPUT=$(uv run i2code setup --help 2>&1)
echo "$OUTPUT"
if [[ "$OUTPUT" != *"update-project"* ]]; then
    echo "FAIL: setup --help does not list update-project"
    exit 1
fi
echo "PASS: update-project listed in setup --help"

# --- update-project --help exits 0 ---
echo ""
echo "--- i2code setup update-project --help exits 0 ---"
uv run i2code setup update-project --help
echo "PASS: setup update-project --help exits 0"

echo ""
echo "=== All Subcommand Smoke Tests Passed ==="
