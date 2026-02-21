#!/usr/bin/env bash
# Tests for editor resolution logic in brainstorm-idea.sh.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
BRAINSTORM_SCRIPT="$PROJECT_ROOT/src/i2code/scripts/brainstorm-idea.sh"

PASS_COUNT=0
FAIL_COUNT=0

pass() { echo "PASS: $1"; PASS_COUNT=$((PASS_COUNT + 1)); }
fail() { echo "FAIL: $1"; FAIL_COUNT=$((FAIL_COUNT + 1)); }

echo "=== Editor Resolution Tests ==="

# --- Test: VS Code on PATH creates .md file and invokes code --wait ---
echo ""
echo "--- VS Code on PATH creates .md and uses code --wait ---"

TMPDIR_VS=$(mktemp -d)
TMPDIR_VISUAL=$(mktemp -d)
TMPDIR_EDITOR=$(mktemp -d)
TMPDIR_VI=$(mktemp -d)
trap 'rm -rf "$TMPDIR_VS" "$TMPDIR_VISUAL" "$TMPDIR_EDITOR" "$TMPDIR_VI"' EXIT

IDEA_DIR="$TMPDIR_VS/my-feature"
MOCK_BIN="$TMPDIR_VS/mock-bin"
mkdir -p "$MOCK_BIN"

# Mock 'code' that records its arguments to a marker file
cat > "$MOCK_BIN/code" <<'MOCK'
#!/usr/bin/env bash
echo "$@" > "$(dirname "$0")/../code-marker.txt"
MOCK
chmod +x "$MOCK_BIN/code"

# Mock 'claude' (no-op — brainstorm-idea.sh calls claude after editing)
cat > "$MOCK_BIN/claude" <<'MOCK'
#!/usr/bin/env bash
exit 0
MOCK
chmod +x "$MOCK_BIN/claude"

# Mock 'uuidgen' (brainstorm-idea.sh uses it for session ID)
cat > "$MOCK_BIN/uuidgen" <<'MOCK'
#!/usr/bin/env bash
echo "test-uuid-1234"
MOCK
chmod +x "$MOCK_BIN/uuidgen"

# Mock 'vi' (fallback editor — record invocation but don't open interactive editor)
cat > "$MOCK_BIN/vi" <<'MOCK'
#!/usr/bin/env bash
echo "$@" > "$(dirname "$0")/../vi-marker.txt"
MOCK
chmod +x "$MOCK_BIN/vi"

# Mock 'envsubst' (brainstorm-idea.sh uses it to expand prompt template)
cat > "$MOCK_BIN/envsubst" <<'MOCK'
#!/usr/bin/env bash
cat
MOCK
chmod +x "$MOCK_BIN/envsubst"

# Run brainstorm-idea.sh with mock-bin prepended to PATH
PATH="$MOCK_BIN:$PATH" "$BRAINSTORM_SCRIPT" "$IDEA_DIR"

# Assert 1: idea file has .md extension
if ls "$IDEA_DIR"/my-feature-idea.md >/dev/null 2>&1; then
    pass "idea file has .md extension"
else
    fail "idea file does not have .md extension"
    echo "  Files in idea dir: $(ls "$IDEA_DIR"/ 2>/dev/null || echo '(empty)')"
fi

# Assert 2: idea file contains placeholder text
if grep -q "PLEASE DESCRIBE YOUR IDEA" "$IDEA_DIR"/my-feature-idea.md 2>/dev/null; then
    pass "idea file contains placeholder text"
else
    fail "idea file does not contain placeholder text"
fi

# Assert 3: mock code marker shows --wait was passed
if [ -f "$TMPDIR_VS/code-marker.txt" ]; then
    MARKER_CONTENT=$(cat "$TMPDIR_VS/code-marker.txt")
    if [[ "$MARKER_CONTENT" == *"--wait"* ]]; then
        pass "code was invoked with --wait"
    else
        fail "code was invoked without --wait: $MARKER_CONTENT"
    fi
else
    fail "code was never invoked (no marker file)"
fi

# --- Test: $VISUAL fallback when code is NOT on PATH ---
echo ""
echo "--- \$VISUAL fallback when code is NOT on PATH ---"

IDEA_DIR_VISUAL="$TMPDIR_VISUAL/my-feature"
MOCK_BIN_VISUAL="$TMPDIR_VISUAL/mock-bin"
mkdir -p "$MOCK_BIN_VISUAL"

# Mock VISUAL editor that records its arguments to a marker file
cat > "$MOCK_BIN_VISUAL/my-editor" <<'MOCK'
#!/usr/bin/env bash
echo "$@" > "$(dirname "$0")/../visual-marker.txt"
MOCK
chmod +x "$MOCK_BIN_VISUAL/my-editor"

# Mock 'claude' (no-op)
cat > "$MOCK_BIN_VISUAL/claude" <<'MOCK'
#!/usr/bin/env bash
exit 0
MOCK
chmod +x "$MOCK_BIN_VISUAL/claude"

# Mock 'uuidgen'
cat > "$MOCK_BIN_VISUAL/uuidgen" <<'MOCK'
#!/usr/bin/env bash
echo "test-uuid-5678"
MOCK
chmod +x "$MOCK_BIN_VISUAL/uuidgen"

# Mock 'vi' (fallback — should NOT be invoked in this test)
cat > "$MOCK_BIN_VISUAL/vi" <<'MOCK'
#!/usr/bin/env bash
echo "$@" > "$(dirname "$0")/../vi-marker.txt"
MOCK
chmod +x "$MOCK_BIN_VISUAL/vi"

# Mock 'envsubst'
cat > "$MOCK_BIN_VISUAL/envsubst" <<'MOCK'
#!/usr/bin/env bash
cat
MOCK
chmod +x "$MOCK_BIN_VISUAL/envsubst"

# NOTE: No mock 'code' — so `command -v code` will fail
# Build a PATH that includes system utilities but NOT code
# Prepend mock-bin (which has no 'code') to ensure our mocks take priority
VISUAL="$MOCK_BIN_VISUAL/my-editor" PATH="$MOCK_BIN_VISUAL:/usr/bin:/bin" "$BRAINSTORM_SCRIPT" "$IDEA_DIR_VISUAL"

# Assert 1: idea file has .txt extension (not .md since code is not available)
if ls "$IDEA_DIR_VISUAL"/my-feature-idea.txt >/dev/null 2>&1; then
    pass "\$VISUAL: idea file has .txt extension"
else
    fail "\$VISUAL: idea file does not have .txt extension"
    echo "  Files in idea dir: $(ls "$IDEA_DIR_VISUAL"/ 2>/dev/null || echo '(empty)')"
fi

# Assert 2: mock VISUAL editor marker shows it was invoked with the file path
if [ -f "$TMPDIR_VISUAL/visual-marker.txt" ]; then
    VISUAL_MARKER_CONTENT=$(cat "$TMPDIR_VISUAL/visual-marker.txt")
    if [[ "$VISUAL_MARKER_CONTENT" == *"my-feature-idea.txt"* ]]; then
        pass "\$VISUAL editor was invoked with idea file path"
    else
        fail "\$VISUAL editor was invoked with unexpected args: $VISUAL_MARKER_CONTENT"
    fi
else
    fail "\$VISUAL editor was never invoked (no marker file)"
fi

# --- Test: $EDITOR fallback when code is NOT on PATH and $VISUAL is not set ---
echo ""
echo "--- \$EDITOR fallback when code is NOT on PATH and \$VISUAL is not set ---"

IDEA_DIR_EDITOR="$TMPDIR_EDITOR/my-feature"
MOCK_BIN_EDITOR="$TMPDIR_EDITOR/mock-bin"
mkdir -p "$MOCK_BIN_EDITOR"

# Mock EDITOR that records its arguments to a marker file
cat > "$MOCK_BIN_EDITOR/my-editor" <<'MOCK'
#!/usr/bin/env bash
echo "$@" > "$(dirname "$0")/../editor-marker.txt"
MOCK
chmod +x "$MOCK_BIN_EDITOR/my-editor"

# Mock 'claude' (no-op)
cat > "$MOCK_BIN_EDITOR/claude" <<'MOCK'
#!/usr/bin/env bash
exit 0
MOCK
chmod +x "$MOCK_BIN_EDITOR/claude"

# Mock 'uuidgen'
cat > "$MOCK_BIN_EDITOR/uuidgen" <<'MOCK'
#!/usr/bin/env bash
echo "test-uuid-9012"
MOCK
chmod +x "$MOCK_BIN_EDITOR/uuidgen"

# Mock 'vi' (fallback — should NOT be invoked in this test)
cat > "$MOCK_BIN_EDITOR/vi" <<'MOCK'
#!/usr/bin/env bash
echo "$@" > "$(dirname "$0")/../vi-marker.txt"
MOCK
chmod +x "$MOCK_BIN_EDITOR/vi"

# Mock 'envsubst'
cat > "$MOCK_BIN_EDITOR/envsubst" <<'MOCK'
#!/usr/bin/env bash
cat
MOCK
chmod +x "$MOCK_BIN_EDITOR/envsubst"

# NOTE: No mock 'code' and VISUAL is unset — so $EDITOR should be used
EDITOR="$MOCK_BIN_EDITOR/my-editor" PATH="$MOCK_BIN_EDITOR:/usr/bin:/bin" "$BRAINSTORM_SCRIPT" "$IDEA_DIR_EDITOR"

# Assert 1: idea file has .txt extension (not .md since code is not available)
if ls "$IDEA_DIR_EDITOR"/my-feature-idea.txt >/dev/null 2>&1; then
    pass "\$EDITOR: idea file has .txt extension"
else
    fail "\$EDITOR: idea file does not have .txt extension"
    echo "  Files in idea dir: $(ls "$IDEA_DIR_EDITOR"/ 2>/dev/null || echo '(empty)')"
fi

# Assert 2: mock EDITOR marker shows it was invoked with the file path
if [ -f "$TMPDIR_EDITOR/editor-marker.txt" ]; then
    EDITOR_MARKER_CONTENT=$(cat "$TMPDIR_EDITOR/editor-marker.txt")
    if [[ "$EDITOR_MARKER_CONTENT" == *"my-feature-idea.txt"* ]]; then
        pass "\$EDITOR was invoked with idea file path"
    else
        fail "\$EDITOR was invoked with unexpected args: $EDITOR_MARKER_CONTENT"
    fi
else
    fail "\$EDITOR was never invoked (no marker file)"
fi

# --- Test: vi fallback when code is NOT on PATH, $VISUAL and $EDITOR are not set ---
echo ""
echo "--- vi fallback when code is NOT on PATH, \$VISUAL and \$EDITOR are not set ---"

IDEA_DIR_VI="$TMPDIR_VI/my-feature"
MOCK_BIN_VI="$TMPDIR_VI/mock-bin"
mkdir -p "$MOCK_BIN_VI"

# Mock 'vi' that records its arguments to a marker file
cat > "$MOCK_BIN_VI/vi" <<'MOCK'
#!/usr/bin/env bash
echo "$@" > "$(dirname "$0")/../vi-marker.txt"
MOCK
chmod +x "$MOCK_BIN_VI/vi"

# Mock 'claude' (no-op)
cat > "$MOCK_BIN_VI/claude" <<'MOCK'
#!/usr/bin/env bash
exit 0
MOCK
chmod +x "$MOCK_BIN_VI/claude"

# Mock 'uuidgen'
cat > "$MOCK_BIN_VI/uuidgen" <<'MOCK'
#!/usr/bin/env bash
echo "test-uuid-3456"
MOCK
chmod +x "$MOCK_BIN_VI/uuidgen"

# Mock 'envsubst'
cat > "$MOCK_BIN_VI/envsubst" <<'MOCK'
#!/usr/bin/env bash
cat
MOCK
chmod +x "$MOCK_BIN_VI/envsubst"

# NOTE: No mock 'code', VISUAL unset, EDITOR unset — vi fallback should be used
PATH="$MOCK_BIN_VI:/usr/bin:/bin" "$BRAINSTORM_SCRIPT" "$IDEA_DIR_VI"

# Assert 1: idea file has .txt extension
if ls "$IDEA_DIR_VI"/my-feature-idea.txt >/dev/null 2>&1; then
    pass "vi fallback: idea file has .txt extension"
else
    fail "vi fallback: idea file does not have .txt extension"
    echo "  Files in idea dir: $(ls "$IDEA_DIR_VI"/ 2>/dev/null || echo '(empty)')"
fi

# Assert 2: idea file contains placeholder text
if grep -q "PLEASE DESCRIBE YOUR IDEA" "$IDEA_DIR_VI"/my-feature-idea.txt 2>/dev/null; then
    pass "vi fallback: idea file contains placeholder text"
else
    fail "vi fallback: idea file does not contain placeholder text"
fi

# Assert 3: mock vi marker shows it was invoked with the file path
if [ -f "$TMPDIR_VI/vi-marker.txt" ]; then
    VI_MARKER_CONTENT=$(cat "$TMPDIR_VI/vi-marker.txt")
    if [[ "$VI_MARKER_CONTENT" == *"my-feature-idea.txt"* ]]; then
        pass "vi fallback: vi was invoked with idea file path"
    else
        fail "vi fallback: vi was invoked with unexpected args: $VI_MARKER_CONTENT"
    fi
else
    fail "vi fallback: vi was never invoked (no marker file)"
fi

echo ""
echo "--- Editor Resolution Results: $PASS_COUNT passed, $FAIL_COUNT failed ---"

if [ "$FAIL_COUNT" -gt 0 ]; then
    exit 1
fi

echo ""
echo "=== All Editor Resolution Tests Passed ==="
