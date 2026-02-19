#!/usr/bin/env bash
# Lists installed idea-to-code plugin skills as comma-separated names.
# Searches PLUGIN_CACHE_DIR (default: ~/.claude/plugins/cache/) for the
# idea-to-code plugin and outputs skill names as idea-to-code:<name>.
# Prints a warning to stderr and outputs empty string if plugin not found.
set -euo pipefail

CACHE_DIR="${PLUGIN_CACHE_DIR:-$HOME/.claude/plugins/cache}"

# Find a skills directory under the idea-to-code plugin
SKILLS_DIR=$(find "$CACHE_DIR" -path "*idea-to-code*/skills" -type d 2>/dev/null | head -1)

if [[ -z "$SKILLS_DIR" ]]; then
    echo "Warning: idea-to-code plugin not found in $CACHE_DIR" >&2
    echo -n ""
    exit 0
fi

# List subdirectory names, prefix with idea-to-code:, join with comma-space
ls -1 "$SKILLS_DIR" | sort | sed 's/^/idea-to-code:/' | tr '\n' ',' | sed 's/,$//' | sed 's/,/, /g'
