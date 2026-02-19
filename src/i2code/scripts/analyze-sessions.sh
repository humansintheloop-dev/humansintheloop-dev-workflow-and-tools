#! /bin/bash -e

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

PROJECT_TRACKING_DIR="${1?}"

if [ ! -d "$PROJECT_TRACKING_DIR" ]; then
    echo "Error: Project tracking directory not found: $PROJECT_TRACKING_DIR" >&2
    exit 1
fi

export SESSIONS_DIR="$PROJECT_TRACKING_DIR/sessions"
export ISSUES_DIR="$PROJECT_TRACKING_DIR/issues"

if [ ! -d "$SESSIONS_DIR" ]; then
    echo "Error: Sessions directory not found: $SESSIONS_DIR" >&2
    exit 1
fi

# Extract session IDs from filenames and find related issue files
SESSION_IDS=$(ls "$SESSIONS_DIR"/session-*.md 2>/dev/null | sed -E 's/.*session-[0-9]{4}-[0-9]{2}-[0-9]{2}-[0-9]{6}-(.*)\.md/\1/' | sort -u)

if [ -d "$ISSUES_DIR" ]; then
    export ISSUES=$(grep -l -E "$(echo $SESSION_IDS | tr ' ' '|')" "$ISSUES_DIR"/active/*.md 2>/dev/null | tr '\n' ' ')
fi

export REPORT_FILE=${PROJECT_TRACKING_DIR}/report-$(date +%Y%m%d-%H%M%S).adoc

PROMPT=$(envsubst < "$DIR/../prompt-templates/analyze-sessions.md")

claude --add-dir "$SESSIONS_DIR" --add-dir "$ISSUES_DIR" --allowedTools Read,Edit,Write -p "$PROMPT"
