#!/bin/bash -e

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

HITL_TRACKING_DIR="${1?Please specify the hitl-tracking directory}"

shift

if [ ! -d "$HITL_TRACKING_DIR" ]; then
    echo "Error: HITL tracking directory not found: $HITL_TRACKING_DIR" >&2
    exit 1
fi

# Parse optional --project-name argument
FILTER_PROJECT=""
if [ "$1" = "--project-name" ]; then
    FILTER_PROJECT="${2?Please specify a project name after --project-name}"
    shift 2
fi

TODAY=$(date +%Y-%m-%d)
TIMESTAMP=$(date +%Y-%m-%d-%H%M%S)

# Find all projects with sessions from today
if [ -n "$FILTER_PROJECT" ]; then
    # Filter to specific project
    PROJECT_DIR="$HITL_TRACKING_DIR/$FILTER_PROJECT"
    if [ ! -d "$PROJECT_DIR" ]; then
        echo "Error: Project not found: $FILTER_PROJECT" >&2
        exit 1
    fi
    if find "$PROJECT_DIR/sessions" -name "session-${TODAY}-*.md" -type f 2>/dev/null | grep -q .; then
        PROJECTS_WITH_SESSIONS="$PROJECT_DIR"
    else
        echo "No sessions from today ($TODAY) for project: $FILTER_PROJECT"
        exit 0
    fi
else
    PROJECTS_WITH_SESSIONS=$(find "$HITL_TRACKING_DIR" -path "*/sessions/session-${TODAY}-*" -type f 2>/dev/null | \
        sed 's|/sessions/session-.*||' | sort -u)
fi

if [ -z "$PROJECTS_WITH_SESSIONS" ]; then
    echo "No projects with sessions from today ($TODAY)"
    exit 0
fi

echo "Found projects with sessions from today:"
echo "$PROJECTS_WITH_SESSIONS"
echo

for PROJECT_DIR in $PROJECTS_WITH_SESSIONS; do
    PROJECT_NAME=$(basename "$PROJECT_DIR")
    export PROJECT_NAME
    echo "Processing project: $PROJECT_NAME"

    # Gather today's session filenames
    export SESSION_FILES=$(find "$PROJECT_DIR/sessions" -name "session-${TODAY}-*.md" -type f 2>/dev/null | sort)
    if [ -z "$SESSION_FILES" ]; then
        export SESSION_FILES="No sessions found for today."
    fi

    # Gather today's issue filenames
    export ISSUE_FILES=$(find "$PROJECT_DIR/issues/active" -name "${TODAY}-*.md" -type f 2>/dev/null | sort)
    if [ -z "$ISSUE_FILES" ]; then
        export ISSUE_FILES="No issues filed today."
    fi

    # Create summary-reports directory
    REPORTS_DIR="$PROJECT_DIR/summary-reports"
    mkdir -p "$REPORTS_DIR"

    REPORT_FILE="$REPORTS_DIR/summary-${TIMESTAMP}.md"

    # Generate the prompt
    PROMPT=$(envsubst < "$DIR/../prompt-templates/create-summary-report.md")

    echo "Generating report: $REPORT_FILE"

    # Invoke Claude and save the output
    echo "$PROMPT" | claude --print --add-dir "$PROJECT_DIR" --allowedTools "Read" "$@" > "$REPORT_FILE"

    echo "Report saved: $REPORT_FILE"
    echo
done

echo "Done. Generated reports for $(echo "$PROJECTS_WITH_SESSIONS" | wc -l | xargs) project(s)."
