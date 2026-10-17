#!/usr/bin/env bash
# Runs the idea-to-code plugin's skill-based eval suite with `claude plugin eval`.
# Results go to logs/plugin-evals/<timestamp>/. Runs real Claude sessions and costs
# money, so it is run manually and is not part of test-end-to-end.sh or CI.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
PLUGIN_DIR="$PROJECT_ROOT/claude-code-plugins/idea-to-code"
EVAL_DIR="evals/skills"
OUTPUT_DIR="$PROJECT_ROOT/logs/plugin-evals/$(date +%Y%m%d-%H%M%S)"

require_commands_on_path() {
    local missing=0
    for command_name in "$@"; do
        if ! command -v "$command_name" > /dev/null; then
            echo "ERROR: required command '$command_name' is not on PATH" >&2
            missing=1
        fi
    done
    if [[ $missing -ne 0 ]]; then
        exit 1
    fi
}

render_case_prompts() {
    (cd "$PROJECT_ROOT" && uv run python test-scripts/render_eval_prompts.py "$PLUGIN_DIR/$EVAL_DIR")
}

run_plugin_evals() {
    claude plugin eval "$PLUGIN_DIR" \
        --eval-dir "$EVAL_DIR" \
        --no-publish \
        --trust-plugin \
        --scaffold \
        --ablation none \
        --allow-tools Read,Write,Edit,Glob,Grep,Bash,Skill \
        --max-cost-usd "${EVAL_MAX_COST_USD:-25}" \
        --output-dir "$OUTPUT_DIR" \
        --json "$OUTPUT_DIR/eval-result.json"
}

echo "=== Plugin Evals ==="

require_commands_on_path claude i2code
render_case_prompts
mkdir -p "$OUTPUT_DIR"

status=0
run_plugin_evals || status=$?

echo ""
echo "Results: $OUTPUT_DIR/aggregate-result.json"
echo "=== Plugin Evals exited with $status ==="
exit "$status"
