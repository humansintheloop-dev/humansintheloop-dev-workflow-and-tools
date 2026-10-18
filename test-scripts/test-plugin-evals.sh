#!/usr/bin/env bash
# Runs the idea-to-code plugin's skill-based eval suite with `claude plugin eval`.
# Results go to logs/plugin-evals/<timestamp>/, with each run's transcript copied to
# traces/<case>-<run>.jsonl in that directory. Runs real Claude sessions and costs
# money, so it is run manually and is not part of test-end-to-end.sh or CI.
# Before the run it rebuilds ~/.cache/i2code-plugin-evals, an i2code install that the eval
# sandbox can run, from the working tree.
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
EVAL_I2CODE_DIR="$HOME/.cache/i2code-plugin-evals"
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

# The eval sandbox denies reads under $HOME except for PATH entries, so i2code, its venv
# and its Python must all live beneath one directory that is put on PATH.
build_eval_i2code() {
    rm -rf "$EVAL_I2CODE_DIR"
    mkdir -p "$EVAL_I2CODE_DIR"
    cp -R "$(uv_python_install_dir)" "$EVAL_I2CODE_DIR/python"
    uv venv --python "$EVAL_I2CODE_DIR/python/bin/python3" "$EVAL_I2CODE_DIR/venv"
    uv pip install --python "$EVAL_I2CODE_DIR/venv/bin/python" "$PROJECT_ROOT"
    write_eval_i2code_wrapper
}

# --system skips the active or project venv, whose interpreter links back into uv's store.
# `uv python find` answers through a minor-version symlink (cpython-3.12-...), so resolve
# it to the real install directory before copying.
uv_python_install_dir() {
    local python_executable
    python_executable="$(uv python find --managed-python --system 3.12)"
    (cd -P "$(dirname "$python_executable")/.." && pwd -P)
}

# GitPython runs `git version` on import. Apple's /usr/bin/git shim fails in the sandbox,
# because it writes a cache file under the denied temp directory, so the wrapper names the
# first other git on PATH.
write_eval_i2code_wrapper() {
    local git_executable
    git_executable="$(git_other_than_apple_shim)"
    cat > "$EVAL_I2CODE_DIR/i2code" <<EOF
#!/bin/sh
GIT_PYTHON_GIT_EXECUTABLE=$git_executable exec "$EVAL_I2CODE_DIR/venv/bin/i2code" "\$@"
EOF
    chmod +x "$EVAL_I2CODE_DIR/i2code"
}

git_other_than_apple_shim() {
    local git_executable
    git_executable="$(type -ap git | grep -v -x /usr/bin/git | head -n 1 || true)"
    if [[ -z "$git_executable" ]]; then
        echo "ERROR: no git other than /usr/bin/git is on PATH; install one, e.g. brew install git" >&2
        exit 1
    fi
    echo "$git_executable"
}

render_case_prompts() {
    (cd "$PROJECT_ROOT" && uv run python test-scripts/render_eval_prompts.py "$PLUGIN_DIR/$EVAL_DIR")
}

run_plugin_evals() {
    PATH="$EVAL_I2CODE_DIR:$PATH" claude plugin eval "$PLUGIN_DIR" \
        --eval-dir "$EVAL_DIR" \
        --no-publish \
        --trust-plugin \
        --scaffold \
        --ablation none \
        --concurrency 4 \
        --keep-temp \
        ${CASE_OPTIONS[@]+"${CASE_OPTIONS[@]}"} \
        --allow-tools Read,Write,Edit,Glob,Grep,Bash,Skill \
        --max-cost-usd "${EVAL_MAX_COST_USD:-25}" \
        --output-dir "$OUTPUT_DIR" \
        --json "$OUTPUT_DIR/eval-result.json"
}

copy_run_traces() {
    local aggregate_result="$OUTPUT_DIR/aggregate-result.json"
    [[ -f "$aggregate_result" ]] || return 0
    mkdir -p "$OUTPUT_DIR/traces"
    jq -r '.cases[] | .name as $case | .arms.with | to_entries[]
           | select(.value.tracePath) | "\($case)-\(.key + 1)\t\(.value.tracePath)"' "$aggregate_result" |
        while IFS=$'\t' read -r run_name trace_path; do
            if [[ -f "$trace_path" ]]; then
                cp "$trace_path" "$OUTPUT_DIR/traces/$run_name.jsonl"
            fi
        done
}

parse_arguments "$@"

echo "=== Plugin Evals ($EVAL_DIR) ==="

require_commands_on_path claude i2code jq
build_eval_i2code
if [[ "$BASELINE" == false ]]; then
    render_case_prompts
fi
mkdir -p "$OUTPUT_DIR"

status=0
run_plugin_evals || status=$?
copy_run_traces

if [[ "$BASELINE" == true ]]; then
    "$SCRIPT_DIR/save-baseline-result.sh" "$OUTPUT_DIR"
fi

echo ""
echo "Results: $OUTPUT_DIR/aggregate-result.json"
echo "=== Plugin Evals exited with $status ==="
exit "$status"
