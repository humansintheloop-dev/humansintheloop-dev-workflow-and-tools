#!/usr/bin/env bash
# Run i2code implement end-to-end tests across isolation types.
#
# Usage: test-all-with-isolarium.sh [--types type1,type2,...] [--resume] [-- extra-args...]
#   --types   Comma-separated isolation types (default: nono,container,vm)
#   --resume  Skip isolation types that already passed
#   All other arguments are passed through to test-i2code-implement.sh.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$PROJECT_ROOT"

GUARD_DIR="logs/test-isolarium-guards"
ISOLATION_TYPES_STR="nono,container,vm"
RESUME=false
EXTRA_ARGS=()

while [[ $# -gt 0 ]]; do
    case $1 in
        --types) ISOLATION_TYPES_STR="$2"; shift 2 ;;
        --resume) RESUME=true; shift ;;
        *) EXTRA_ARGS+=("$1"); shift ;;
    esac
done

IFS=',' read -ra ISOLATION_TYPES <<< "$ISOLATION_TYPES_STR"

if [ "$RESUME" = false ]; then
    rm -rf "$GUARD_DIR"
fi
mkdir -p "$GUARD_DIR"

OVERALL_START=$(date +%s)
PASSED=()
FAILED=()
SKIPPED=()

timePhase() {
    local label="$1"
    shift
    local start_time
    start_time=$(date +%s)
    if "$@"; then
        local end_time
        end_time=$(date +%s)
        echo "TIMING: $label took $((end_time - start_time))s"
        PASSED+=("$label")
    else
        local end_time
        end_time=$(date +%s)
        echo "TIMING: $label FAILED after $((end_time - start_time))s"
        FAILED+=("$label")
        return 1
    fi
}

guarded() {
    local guard="$1"
    shift
    if [ -f "$GUARD_DIR/$guard" ]; then
        echo "SKIP: $guard (already done)"
        SKIPPED+=("$guard")
        return
    fi
    if ! "$@"; then
        EXIT_CODE=1
        exit 1
    fi
    touch "$GUARD_DIR/$guard"
}

EXIT_CODE=0

printSummary() {
    local overall_end
    overall_end=$(date +%s)
    echo ""
    echo "========================================="
    echo "  ISOLARIUM TEST SUMMARY"
    echo "========================================="
    echo "Total time: $((overall_end - OVERALL_START))s"
    echo ""
    if [ ${#PASSED[@]} -gt 0 ]; then
        echo "PASSED (${#PASSED[@]}):"
        for t in "${PASSED[@]}"; do echo "  + $t"; done
    fi
    if [ ${#SKIPPED[@]} -gt 0 ]; then
        echo ""
        echo "SKIPPED (${#SKIPPED[@]}):"
        for t in "${SKIPPED[@]}"; do echo "  ~ $t"; done
    fi
    if [ ${#FAILED[@]} -gt 0 ]; then
        echo ""
        echo "FAILED (${#FAILED[@]}):"
        for t in "${FAILED[@]}"; do echo "  ! $t"; done
    fi
    echo "========================================="
    return "$EXIT_CODE"
}

trap printSummary EXIT

echo "========================================="
echo "  Running i2code implement for: ${ISOLATION_TYPES[*]}"
echo "========================================="

runIsolationType() {
    local isolation_type="$1"

    timePhase "isolation-type: $isolation_type" \
        "$SCRIPT_DIR/test-i2code-implement.sh" \
        --ref needs-get-accounts-endpoint \
        --non-interactive \
        --isolation-type "$isolation_type" \
        --skip-scaffolding \
        --debug-claude \
        ${EXTRA_ARGS[@]+"${EXTRA_ARGS[@]}"} \
        --repo \
        cer/i2code-test-repo-banking
}

for isolation_type in "${ISOLATION_TYPES[@]}"; do
    guarded "$isolation_type" runIsolationType "$isolation_type"
done

if [ ${#FAILED[@]} -gt 0 ]; then
    EXIT_CODE=1
    exit 1
fi
