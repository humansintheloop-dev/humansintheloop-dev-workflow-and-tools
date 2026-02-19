#!/bin/bash -e

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

usage() {
    cat <<EOF
Usage: $(basename "$0") HITL_TRACKING_DIR [OPTIONS] [-- CLAUDE_ARGS...]

Review active issues and incorporate suggested improvements into project skills and prompts.

Arguments:
  HITL_TRACKING_DIR    Path to the hitl-tracking directory (required)

Options:
  --project NAME       Restrict to issues in the specified project subdirectory
  --help               Show this help message and exit

Any arguments after -- are passed directly to claude.

Examples:
  $(basename "$0") ~/hitl-tracking
  $(basename "$0") ~/hitl-tracking --project myproject
  $(basename "$0") ~/hitl-tracking --project myproject -- --verbose
EOF
}

PROJECT=""
HITL_TRACKING_DIR=""
CLAUDE_ARGS=()

# Parse arguments
while [[ $# -gt 0 ]]; do
    case "$1" in
        --help)
            usage
            exit 0
            ;;
        --project)
            if [[ -z "$2" || "$2" == --* ]]; then
                echo "Error: --project requires a value" >&2
                exit 1
            fi
            PROJECT="$2"
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
            if [[ -z "$HITL_TRACKING_DIR" ]]; then
                HITL_TRACKING_DIR="$1"
                shift
            else
                CLAUDE_ARGS+=("$1")
                shift
            fi
            ;;
    esac
done

if [[ -z "$HITL_TRACKING_DIR" ]]; then
    echo "Error: Please specify the hitl-tracking directory" >&2
    echo "Use --help for usage information" >&2
    exit 1
fi

if [ ! -d "$HITL_TRACKING_DIR" ]; then
    echo "Error: HITL tracking directory not found: $HITL_TRACKING_DIR" >&2
    exit 1
fi

# Determine search path
if [[ -n "$PROJECT" ]]; then
    SEARCH_PATH="$HITL_TRACKING_DIR/$PROJECT"
    if [ ! -d "$SEARCH_PATH" ]; then
        echo "Error: Project directory not found: $SEARCH_PATH" >&2
        exit 1
    fi
else
    SEARCH_PATH="$HITL_TRACKING_DIR"
fi

# Find active issues created this year (2026-*) across all projects
# Filter out issues that have already been marked as type: unknown
CURRENT_YEAR=$(date +%Y)
ALL_ISSUES=$(find "$SEARCH_PATH" -path "*/issues/active/${CURRENT_YEAR}-*.md" -type f 2>/dev/null | sort)

ACTIVE_ISSUES=""
for issue in $ALL_ISSUES; do
    if ! grep -q "^type: unknown" "$issue" 2>/dev/null; then
        ACTIVE_ISSUES="$ACTIVE_ISSUES $issue"
    fi
done
ACTIVE_ISSUES=$(echo "$ACTIVE_ISSUES" | xargs)

if [ -z "$ACTIVE_ISSUES" ]; then
    echo "No active issues found for $CURRENT_YEAR (excluding type: unknown)"
    exit 0
fi

echo "Found active issues:"
echo "$ACTIVE_ISSUES"
echo

# Create resolved directories for each project that has active issues
for issue in $ACTIVE_ISSUES; do
    issues_dir=$(dirname "$(dirname "$issue")")
    mkdir -p "$issues_dir/resolved"
done

export ACTIVE_ISSUES
export HITL_TRACKING_DIR

PROMPT=$(envsubst < "$DIR/../prompt-templates/review-issues.md")

claude "$PROMPT" "${CLAUDE_ARGS[@]}"
