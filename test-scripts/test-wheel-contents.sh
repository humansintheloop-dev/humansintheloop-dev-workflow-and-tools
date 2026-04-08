#!/usr/bin/env bash
# Test that the built wheel contains non-Python config files.
set -euo pipefail

echo "=== Wheel Contents Test ==="

DIST_DIR=$(mktemp -d)
trap 'rm -rf "$DIST_DIR"' EXIT

echo "--- Building wheel ---"
uv build --wheel --out-dir "$DIST_DIR"

WHEEL=$(ls "$DIST_DIR"/*.whl)
echo "Built: $WHEEL"

echo "--- Checking wheel contents ---"
CONTENTS=$(unzip -l "$WHEEL")

FAIL=0

for FILE in "i2code/config_files/CLAUDE.md" "i2code/config_files/settings.local.json"; do
    if echo "$CONTENTS" | grep -q "$FILE"; then
        echo "PASS: $FILE found in wheel"
    else
        echo "FAIL: $FILE NOT found in wheel"
        FAIL=1
    fi
done

if [ "$FAIL" -ne 0 ]; then
    echo ""
    echo "Wheel contents:"
    echo "$CONTENTS"
    exit 1
fi

echo ""
echo "=== Wheel Contents Test Passed ==="
