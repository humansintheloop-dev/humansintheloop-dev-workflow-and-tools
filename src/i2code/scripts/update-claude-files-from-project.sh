#!/bin/bash -e

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

PROJECT_DIR="${1?Please specify the project directory}"

shift

if [ ! -d "$PROJECT_DIR" ]; then
    echo "Error: Project directory not found: $PROJECT_DIR" >&2
    exit 1
fi

PROJECT_DIR=$(cd "$PROJECT_DIR" && pwd)

# Check for Claude files in the project
PROJECT_CLAUDE_MD="$PROJECT_DIR/CLAUDE.md"
PROJECT_SETTINGS="$PROJECT_DIR/.claude/settings.local.json"

if [ ! -f "$PROJECT_CLAUDE_MD" ] && [ ! -f "$PROJECT_SETTINGS" ]; then
    echo "Error: No Claude files found in project. Expected at least one of:" >&2
    echo "  - $PROJECT_CLAUDE_MD" >&2
    echo "  - $PROJECT_SETTINGS" >&2
    exit 1
fi

CONFIG_DIR="$DIR/../config-files"
CONFIG_CLAUDE_MD="$CONFIG_DIR/CLAUDE.md"
CONFIG_SETTINGS="$CONFIG_DIR/settings.local.json"

export PROJECT_DIR
export PROJECT_CLAUDE_MD
export PROJECT_SETTINGS
export CONFIG_CLAUDE_MD
export CONFIG_SETTINGS

PROMPT=$(envsubst < "$DIR/../prompt-templates/update-claude-files-from-project.md")

claude "$PROMPT" "$@"
