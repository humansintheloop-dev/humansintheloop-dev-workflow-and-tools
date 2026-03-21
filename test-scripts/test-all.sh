#!/usr/bin/env bash
# Run all tests locally, ordered from fastest to slowest.
# Use --resume to skip already-completed phases.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$PROJECT_ROOT"

GUARD_DIR="logs/test-all-guards"
RESUME=false

for arg in "$@"; do
    case "$arg" in
        --resume) RESUME=true ;;
        *)
            echo "Usage: $0 [--resume]"
            exit 1
            ;;
    esac
done

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
    echo "  TEST SUMMARY"
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

# ── Linting ──────────────────────────────────────────────────────

runLinting() {
    echo ""
    echo "=== Linting ==="
    echo ""

    timePhase "ruff check" uv run --with ruff ruff check

    timePhase "pyright" uvx pyright --level error "$PROJECT_ROOT/src/"

    timePhase "shellcheck" shellcheck "$SCRIPT_DIR"/*.sh
}

# ── Unit tests ───────────────────────────────────────────────────

runUnitTests() {
    echo ""
    echo "=== Unit Tests ==="
    echo ""

    timePhase "pytest unit" "$SCRIPT_DIR/test-unit.sh"

    timePhase "plugin javascript" "$SCRIPT_DIR/test-plugin-javascript.sh"

    timePhase "verify test markers" "$SCRIPT_DIR/test-verify-all-tests-have-markers.sh"
}

# ── CLI smoke tests ──────────────────────────────────────────────

runSmokeTests() {
    echo ""
    echo "=== CLI Smoke Tests ==="
    echo ""

    timePhase "plan CLI smoke" "$SCRIPT_DIR/test-plan-cli-smoke.sh"

    timePhase "subcommand smoke" "$SCRIPT_DIR/test-subcommands-smoke.sh"
}

# ── Integration tests ────────────────────────────────────────────

runIntegrationTests() {
    echo ""
    echo "=== Integration Tests ==="
    echo ""

    timePhase "pytest integration" "$SCRIPT_DIR/test-integration.sh"

    timePhase "pytest integration_gh" \
        uv run python3 -m pytest "$PROJECT_ROOT/tests/" -v -m integration_gh

    timePhase "pytest integration_claude" \
        uv run python3 -m pytest "$PROJECT_ROOT/tests/" -v -m integration_claude
}

# ── Run all phases ───────────────────────────────────────────────

guarded "linting" runLinting
guarded "unit-tests" runUnitTests
guarded "smoke-tests" runSmokeTests
guarded "integration-tests" runIntegrationTests

if [ ${#FAILED[@]} -gt 0 ]; then
    EXIT_CODE=1
    exit 1
fi
