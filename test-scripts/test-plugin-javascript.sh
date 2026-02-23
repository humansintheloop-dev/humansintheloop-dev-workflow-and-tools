#!/usr/bin/env bash
# Runs all JavaScript test files in the hooks directory.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "=== Plugin JavaScript Tests ==="

failed=0
for test_file in "$PROJECT_ROOT"/hooks/*.test.js; do
    echo ""
    echo "--- Running $(basename "$test_file") ---"
    if node "$test_file"; then
        echo "PASS: $(basename "$test_file")"
    else
        echo "FAIL: $(basename "$test_file")"
        failed=1
    fi
done

echo ""
if [[ $failed -ne 0 ]]; then
    echo "=== Some Plugin JavaScript Tests Failed ==="
    exit 1
fi
echo "=== All Plugin JavaScript Tests Passed ==="
