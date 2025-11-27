#!/bin/bash -e

# Test script for session recording

echo "=== Reinstalling plugin ==="
./reinstall-plugin.sh

echo ""
echo "=== Clearing debug log and session state ==="
rm -f .claude/sessions/debug.log
rm -f .claude/sessions/.current-session

echo ""
echo "=== Recording start time ==="
mkdir -p .claude/sessions
START_MARKER=".claude/sessions/.test-start-marker"
touch "$START_MARKER"
sleep 1  # Ensure any new files have a later timestamp

echo ""
echo "=== Running claude with test prompt (triggers tool use) ==="
claude -p "Read the first 5 lines of README.adoc"

echo ""
echo "=== Debug log contents ==="
cat .claude/sessions/debug.log 2>/dev/null || echo "No debug log found"

echo ""
echo "=== Session files created during this test ==="
find .claude/sessions -name "session-*.md" -newer "$START_MARKER" -exec cat {} \; 2>/dev/null || echo "No new session files found"

# Clean up marker
rm -f "$START_MARKER"
