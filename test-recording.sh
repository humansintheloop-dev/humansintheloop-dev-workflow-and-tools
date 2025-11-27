#!/bin/bash -e

# Test script for session recording

echo "=== Reinstalling plugin ==="
./reinstall-plugin.sh

echo ""
echo "=== Clearing old debug log ==="
rm -f .claude/sessions/debug.log

echo ""
echo "=== Running claude with test prompt ==="
claude -p "hello"

echo ""
echo "=== Debug log contents ==="
cat .claude/sessions/debug.log 2>/dev/null || echo "No debug log found"

echo ""
echo "=== Latest session file ==="
ls -t .claude/sessions/*.md 2>/dev/null | head -1 | xargs cat 2>/dev/null || echo "No session files found"
