#!/usr/bin/env bash
# Runs the idea-to-code plugin's skill-based eval suite with `claude plugin eval`.
# Results go to logs/plugin-evals/<timestamp>/. Runs real Claude sessions and costs
# money, so it is run manually and is not part of test-end-to-end.sh or CI.
#
# Usage: test-plugin-evals.sh [--baseline] [--case <glob>]
#   --baseline     runs the frozen prompts in evals/baseline without re-rendering them
#                  and saves aggregate-result.json to evals/baseline-results/ with
#                  save-baseline-result.sh
#   --case <glob>  runs only the cases whose name matches <glob>
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
PLUGIN_DIR="$PROJECT_ROOT/claude-code-plugins/idea-to-code"
EVAL_DIR="evals/skills"
OUTPUT_DIR="$PROJECT_ROOT/logs/plugin-evals/$(date +%Y%m%d-%H%M%S)"
BASELINE=false
CASE_OPTIONS=()

usage() {
    echo "Usage: $0 [--baseline] [--case <glob>]" >&2
    exit 2
}

parse_arguments() {
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --baseline)
                BASELINE=true
                EVAL_DIR="evals/baseline"
                shift
                ;;
            --case)
                [[ $# -ge 2 ]] || usage
                CASE_OPTIONS=(--case "$2")
                shift 2
                ;;
            *)
                usage
                ;;
        esac
    done
}

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
        --concurrency 4 \
        ${CASE_OPTIONS[@]+"${CASE_OPTIONS[@]}"} \
        --allow-tools Read,Write,Edit,Glob,Grep,Bash,Skill \
        --max-cost-usd "${EVAL_MAX_COST_USD:-25}" \
        --output-dir "$OUTPUT_DIR" \
        --json "$OUTPUT_DIR/eval-result.json"
}

parse_arguments "$@"

echo "=== Plugin Evals ($EVAL_DIR) ==="

require_commands_on_path claude i2code jq
if [[ "$BASELINE" == false ]]; then
    render_case_prompts
fi
mkdir -p "$OUTPUT_DIR"

status=0
run_plugin_evals || status=$?

if [[ "$BASELINE" == true ]]; then
    "$SCRIPT_DIR/save-baseline-result.sh" "$OUTPUT_DIR"
fi

echo ""
echo "Results: $OUTPUT_DIR/aggregate-result.json"
echo "=== Plugin Evals exited with $status ==="
exit "$status"
