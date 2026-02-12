#!/bin/bash -e

# Test script for session recording

echo "=== Reinstalling plugin ==="
./reinstall-plugin.sh

echo ""
echo "=== Clearing debug log and session state ==="
rm -f .hitl/sessions/debug.log
rm -f .hitl/sessions/.current-session

echo ""
echo "=== Recording start time ==="
mkdir -p .hitl/sessions
START_MARKER=".hitl/sessions/.test-start-marker"
touch "$START_MARKER"
sleep 1  # Ensure any new files have a later timestamp

echo ""
echo "=== Running claude with test prompt (triggers tool use) ==="
claude -p "Read the first 5 lines of README.adoc"

echo ""
echo "=== Debug log contents ==="
cat .hitl/sessions/debug.log 2>/dev/null || echo "No debug log found"

echo ""
echo "=== Session files created during this test ==="
find .hitl/sessions -name "session-*.md" -newer "$START_MARKER" -exec cat {} \; 2>/dev/null || echo "No new session files found"

# Clean up marker
rm -f "$START_MARKER"
