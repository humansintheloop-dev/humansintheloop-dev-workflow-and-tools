#!/bin/bash -e

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

usage() {
    cat <<EOF
Usage: $(basename "$0") PROJECT_DIR --config-dir CONFIG_DIR [-- CLAUDE_ARGS...]

Push template updates into a project's Claude files.

Arguments:
  PROJECT_DIR          Path to the project directory (required)

Options:
  --config-dir DIR     Path to the config-files directory (required)
  --help               Show this help message and exit

Any arguments after -- are passed directly to claude.

Examples:
  $(basename "$0") ~/my-project --config-dir ~/workflow/config-files
  $(basename "$0") ~/my-project --config-dir ~/workflow/config-files -- --verbose
EOF
}

PROJECT_DIR=""
CONFIG_DIR=""
CLAUDE_ARGS=()

# Parse arguments
while [[ $# -gt 0 ]]; do
    case "$1" in
        --help)
            usage
            exit 0
            ;;
        --config-dir)
            if [[ -z "$2" || "$2" == --* ]]; then
                echo "Error: --config-dir requires a value" >&2
                exit 1
            fi
            CONFIG_DIR="$2"
            shift 2
            ;;
        --)
            shift
            CLAUDE_ARGS=("$@")
            break
            ;;
        --*)
            echo "Error: Unrecognized option: $1" >&2
            echo "Use --help for usage information" >&2
            exit 1
            ;;
        *)
            if [[ -z "$PROJECT_DIR" ]]; then
                PROJECT_DIR="$1"
                shift
            else
                CLAUDE_ARGS+=("$1")
                shift
            fi
            ;;
    esac
done

if [[ -z "$PROJECT_DIR" ]]; then
    echo "Error: Please specify the project directory" >&2
    echo "Use --help for usage information" >&2
    exit 1
fi

if [[ -z "$CONFIG_DIR" ]]; then
    echo "Error: --config-dir is required" >&2
    echo "Use --help for usage information" >&2
    exit 1
fi

if [ ! -d "$PROJECT_DIR" ]; then
    echo "Error: Project directory not found: $PROJECT_DIR" >&2
    exit 1
fi

PROJECT_DIR=$(cd "$PROJECT_DIR" && pwd)

# Project Claude files
PROJECT_CLAUDE_MD="$PROJECT_DIR/CLAUDE.md"
PROJECT_SETTINGS="$PROJECT_DIR/.claude/settings.local.json"

# Template files
CONFIG_CLAUDE_MD="$CONFIG_DIR/CLAUDE.md"
CONFIG_SETTINGS="$CONFIG_DIR/settings.local.json"

# Derive git repo root from config-dir path
REPO_ROOT=$(git -C "$CONFIG_DIR" rev-parse --show-toplevel 2>/dev/null || true)

# Get the relative path of config-dir within the repo
if [ -n "$REPO_ROOT" ]; then
    CONFIG_REL_PATH=$(cd "$CONFIG_DIR" && pwd)
    CONFIG_REL_PATH="${CONFIG_REL_PATH#$REPO_ROOT/}"

    # Get current SHA of config-files directory
    CURRENT_SHA=$(git -C "$REPO_ROOT" log -1 --format="%H" -- "$CONFIG_REL_PATH/")
else
    CURRENT_SHA=""
fi

# Extract previous SHA from project's CLAUDE.md if it exists
PREVIOUS_SHA=""
if [ -f "$PROJECT_CLAUDE_MD" ]; then
    PREVIOUS_SHA=$(grep -o 'claude-config-files-sha: [a-f0-9]*' "$PROJECT_CLAUDE_MD" 2>/dev/null | cut -d' ' -f2 || true)
fi

# Generate diff of config-files since previous SHA
if [ -n "$PREVIOUS_SHA" ] && [ -n "$CURRENT_SHA" ] && [ -n "$REPO_ROOT" ]; then
    CONFIG_DIFF=$(git -C "$REPO_ROOT" diff "$PREVIOUS_SHA".."$CURRENT_SHA" -- "$CONFIG_REL_PATH/" 2>/dev/null || echo "Unable to generate diff - previous SHA not found in history")
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

claude "$PROMPT" "${CLAUDE_ARGS[@]}"
