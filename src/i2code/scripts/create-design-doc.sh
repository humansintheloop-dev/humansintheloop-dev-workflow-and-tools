#! /bin/bash -e

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# shellcheck disable=SC1091
source "$DIR/_helper.sh"

_validate_idea
_validate_spec

# Archive existing design file if it exists
if [ -f "$DESIGN_FILE" ]; then
    ARCHIVE_DIR="$IDEA_DIR/archive"
    mkdir -p "$ARCHIVE_DIR"
    TIMESTAMP=$(date +%Y%m%d-%H%M%S)
    mv "$DESIGN_FILE" "$ARCHIVE_DIR/${IDEA_NAME}-design-${TIMESTAMP}.md"
    echo "Archived existing design to $ARCHIVE_DIR/${IDEA_NAME}-design-${TIMESTAMP}.md"
fi

export IDEA_FILE DISCUSSION_FILE SPEC_FILE
export DESIGN_SKILLS=$("$DIR/list-plugin-skills.sh")
PROMPT=$(envsubst < "$DIR/../prompt-templates/create-design-doc.md")

SESSION_ID=$(_session_id)
if [ -n "$SESSION_ID" ]; then
    claude --resume "$SESSION_ID" "$@" "$PROMPT"
else
    claude "$@" "$PROMPT"
fi
