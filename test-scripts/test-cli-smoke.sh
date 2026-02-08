#!/usr/bin/env bash
# CLI smoke tests for i2c plan subcommands.
# Tests that each migrated subcommand runs and produces expected output.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Create a temporary plan file for testing
TEMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TEMP_DIR"' EXIT

PLAN_FILE="$TEMP_DIR/test-plan.md"
cat > "$PLAN_FILE" << 'PLAN'
# Implementation Plan: Smoke Test Plan

## Idea Type
**A. Feature** - A test feature

---

## Overview
This is a smoke test plan.

---

## Steel Thread 5: First Thread
Introduction to first thread.

- [ ] **Task 5.3: First task**
  - TaskType: INFRA
  - Entrypoint: `echo hello`
  - Observable: Something happens
  - Evidence: `echo done`
  - Steps:
    - [ ] Step one
    - [ ] Step two

- [ ] **Task 5.7: Second task**
  - TaskType: OUTCOME
  - Entrypoint: `echo hello2`
  - Observable: Something else happens
  - Evidence: `echo done2`
  - Steps:
    - [ ] Step one

---

## Summary
This plan has 1 thread.
PLAN

echo "=== CLI Smoke Tests ==="

# --- fix-numbering ---
echo ""
echo "--- fix-numbering ---"
OUTPUT=$(uv run i2c plan fix-numbering "$PLAN_FILE" 2>&1)
echo "$OUTPUT"
if [[ "$OUTPUT" != *"Fixed numbering in"* ]]; then
    echo "FAIL: fix-numbering did not print expected confirmation"
    exit 1
fi
# Verify the file was actually renumbered
if grep -q "Steel Thread 5:" "$PLAN_FILE"; then
    echo "FAIL: fix-numbering did not renumber threads"
    exit 1
fi
if ! grep -q "Steel Thread 1:" "$PLAN_FILE"; then
    echo "FAIL: fix-numbering did not produce Thread 1"
    exit 1
fi
echo "PASS: fix-numbering"

echo ""
echo "=== All CLI Smoke Tests Passed ==="
