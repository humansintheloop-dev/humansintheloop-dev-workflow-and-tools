#!/bin/bash -e

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

usage() {
    cat <<EOF
Usage: $(basename "$0") PROJECT_DIR --config-dir CONFIG_DIR [-- CLAUDE_ARGS...]

Review project Claude files and update config-files templates with improvements.

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

# Check for Claude files in the project
PROJECT_CLAUDE_MD="$PROJECT_DIR/CLAUDE.md"
PROJECT_SETTINGS="$PROJECT_DIR/.claude/settings.local.json"

if [ ! -f "$PROJECT_CLAUDE_MD" ] && [ ! -f "$PROJECT_SETTINGS" ]; then
    echo "Error: No Claude files found in project. Expected at least one of:" >&2
    echo "  - $PROJECT_CLAUDE_MD" >&2
    echo "  - $PROJECT_SETTINGS" >&2
    exit 1
fi

CONFIG_CLAUDE_MD="$CONFIG_DIR/CLAUDE.md"
CONFIG_SETTINGS="$CONFIG_DIR/settings.local.json"

export PROJECT_DIR
export PROJECT_CLAUDE_MD
export PROJECT_SETTINGS
export CONFIG_CLAUDE_MD
export CONFIG_SETTINGS

PROMPT=$(envsubst < "$DIR/../prompt-templates/update-claude-files-from-project.md")

claude "$PROMPT" "${CLAUDE_ARGS[@]}"
