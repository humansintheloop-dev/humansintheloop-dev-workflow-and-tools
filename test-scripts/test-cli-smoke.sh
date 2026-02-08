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

# --- get-next-task ---
echo ""
echo "--- get-next-task ---"
OUTPUT=$(uv run i2c plan get-next-task "$PLAN_FILE" 2>&1)
echo "$OUTPUT"
if [[ "$OUTPUT" != *"Thread 1, Task 1.1:"* ]]; then
    echo "FAIL: get-next-task did not return expected task"
    exit 1
fi
if [[ "$OUTPUT" != *"TaskType:"* ]]; then
    echo "FAIL: get-next-task missing TaskType"
    exit 1
fi
echo "PASS: get-next-task"

# --- list-threads ---
echo ""
echo "--- list-threads ---"
OUTPUT=$(uv run i2c plan list-threads "$PLAN_FILE" 2>&1)
echo "$OUTPUT"
if [[ "$OUTPUT" != *"Thread 1:"* ]]; then
    echo "FAIL: list-threads did not return threads"
    exit 1
fi
if [[ "$OUTPUT" != *"tasks completed"* ]]; then
    echo "FAIL: list-threads missing completion count"
    exit 1
fi
echo "PASS: list-threads"

# --- get-summary ---
echo ""
echo "--- get-summary ---"
OUTPUT=$(uv run i2c plan get-summary "$PLAN_FILE" 2>&1)
echo "$OUTPUT"
if [[ "$OUTPUT" != *"Plan:"* ]]; then
    echo "FAIL: get-summary missing Plan:"
    exit 1
fi
if [[ "$OUTPUT" != *"Idea Type:"* ]]; then
    echo "FAIL: get-summary missing Idea Type:"
    exit 1
fi
if [[ "$OUTPUT" != *"Tasks:"* ]]; then
    echo "FAIL: get-summary missing Tasks:"
    exit 1
fi
echo "PASS: get-summary"

# --- get-thread ---
echo ""
echo "--- get-thread ---"
OUTPUT=$(uv run i2c plan get-thread "$PLAN_FILE" --thread 1 2>&1)
echo "$OUTPUT"
if [[ "$OUTPUT" != *"Thread 1:"* ]]; then
    echo "FAIL: get-thread did not return thread"
    exit 1
fi
if [[ "$OUTPUT" != *"Introduction to first thread"* ]]; then
    echo "FAIL: get-thread missing introduction"
    exit 1
fi
echo "PASS: get-thread"

echo ""
echo "=== All CLI Smoke Tests Passed ==="
