#!/bin/bash -e

# Validate that the idea-to-code plugin is properly installed
# by running Claude and asking it to verify the plugin, skills, and slash commands

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "Validating plugin installation..."
echo

claude -p "hello"

grep idea-to-code ~/.claude/debug/$(ls -t ~/.claude/debug | head -1)