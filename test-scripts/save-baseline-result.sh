#!/usr/bin/env bash
# Copies a plugin eval run's aggregate-result.json to the committed baseline result.
# The copy drops each grader's evidence (the session's output, which can contain
# any path) and replaces the project root with "." so it passes gitleaks.
#
# Usage: save-baseline-result.sh <run-output-dir>
set -euo pipefail

if [[ $# -ne 1 ]]; then
    echo "Usage: $0 <run-output-dir>" >&2
    exit 2
fi

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
BASELINE_RESULTS_DIR="$PROJECT_ROOT/claude-code-plugins/idea-to-code/evals/baseline-results"

mkdir -p "$BASELINE_RESULTS_DIR"
jq --arg root "$PROJECT_ROOT" \
    'del(.. | .evidence?) | walk(if type == "string" then gsub($root; ".") else . end)' \
    "$1/aggregate-result.json" > "$BASELINE_RESULTS_DIR/aggregate-result.json"
echo "Baseline result: $BASELINE_RESULTS_DIR/aggregate-result.json"
