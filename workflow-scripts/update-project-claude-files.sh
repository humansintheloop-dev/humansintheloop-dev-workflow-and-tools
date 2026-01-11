#!/bin/bash -e

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

PROJECT_DIR="${1?Please specify the project directory}"

shift

if [ ! -d "$PROJECT_DIR" ]; then
    echo "Error: Project directory not found: $PROJECT_DIR" >&2
    exit 1
fi

PROJECT_DIR=$(cd "$PROJECT_DIR" && pwd)

# Project Claude files
PROJECT_CLAUDE_MD="$PROJECT_DIR/CLAUDE.md"
PROJECT_SETTINGS="$PROJECT_DIR/.claude/settings.local.json"

# Template files
CONFIG_DIR="$DIR/../config-files"
CONFIG_CLAUDE_MD="$CONFIG_DIR/CLAUDE.md"
CONFIG_SETTINGS="$CONFIG_DIR/settings.local.json"

# Get current SHA of config-files directory
CURRENT_SHA=$(git -C "$DIR/.." log -1 --format="%H" -- config-files/)

# Extract previous SHA from project's CLAUDE.md if it exists
PREVIOUS_SHA=""
if [ -f "$PROJECT_CLAUDE_MD" ]; then
    PREVIOUS_SHA=$(grep -o 'claude-config-files-sha: [a-f0-9]*' "$PROJECT_CLAUDE_MD" 2>/dev/null | cut -d' ' -f2 || true)
fi

# Generate diff of config-files since previous SHA
if [ -n "$PREVIOUS_SHA" ]; then
    CONFIG_DIFF=$(git -C "$DIR/.." diff "$PREVIOUS_SHA".."$CURRENT_SHA" -- config-files/ 2>/dev/null || echo "Unable to generate diff - previous SHA not found in history")
else
    CONFIG_DIFF="No previous SHA found. This appears to be the first sync. Full template contents will be used as reference."
fi

export PROJECT_DIR
export PROJECT_CLAUDE_MD
export PROJECT_SETTINGS
export CONFIG_CLAUDE_MD
export CONFIG_SETTINGS
export CURRENT_SHA
export PREVIOUS_SHA
export CONFIG_DIFF

PROMPT=$(envsubst < "$DIR/../prompt-templates/update-project-claude-files.md")

claude "$PROMPT" "$@"
