#!/bin/bash -e

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

HITL_TRACKING_DIR="${1?Please specify the hitl-tracking directory}"

shift

if [ ! -d "$HITL_TRACKING_DIR" ]; then
    echo "Error: HITL tracking directory not found: $HITL_TRACKING_DIR" >&2
    exit 1
fi

# Find active issues created this year (2026-*) across all projects
# Filter out issues that have already been marked as type: unknown
CURRENT_YEAR=$(date +%Y)
ALL_ISSUES=$(find "$HITL_TRACKING_DIR" -path "*/issues/active/${CURRENT_YEAR}-*.md" -type f 2>/dev/null | sort)

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

claude "$PROMPT" "$@"
