# shellcheck disable=SC2148


IDEA_DIR=${1}

shift

if [ -z "$IDEA_DIR" ]; then
    echo "Please specify the directory that will contain the idea-related files"
    exit 1
fi

IDEA_NAME=$(basename "$IDEA_DIR")

if ! ls "$IDEA_DIR"/${IDEA_NAME}-idea.* >/dev/null 2>&1; then
    IDEA_FILE="$IDEA_DIR/${IDEA_NAME}-idea.txt"
else
    IDEA_FILE="$(ls "$IDEA_DIR"/${IDEA_NAME}-idea.*)"
fi

DISCUSSION_FILE="$IDEA_DIR/${IDEA_NAME}-discussion.md"

SESSION_ID_FILE="$IDEA_DIR/${IDEA_NAME}-sessionID.txt"

SPEC_FILE="$IDEA_DIR/${IDEA_NAME}-spec.md"

STORY_FILE="$IDEA_DIR/${IDEA_NAME}-stories.md"

PLAN_WITHOUT_STORIES_FILE="$IDEA_DIR/${IDEA_NAME}-plan.md"

PLAN_WITH_STORIES_FILE="$IDEA_DIR/${IDEA_NAME}-story-plan.md"

# Validation functions
_validate_idea() {
    # Use ls to check if any file matching the pattern exists
    if ! ls $IDEA_FILE >/dev/null 2>&1; then
        echo "Error: Idea file not found: $IDEA_FILE" >&2
        exit 1
    fi
}

_validate_spec() {
    if [ ! -f "$SPEC_FILE" ]; then
        echo "Error: Spec file not found: $SPEC_FILE" >&2
        exit 1
    fi
}

_validate_story() {
    if [ ! -f "$STORY_FILE" ]; then
        echo "Error: Story file not found: $STORY_FILE" >&2
        exit 1
    fi
}

_validate_plan_without_stories() {
    if [ ! -f "$PLAN_WITHOUT_STORIES_FILE" ]; then
        echo "Error: Plan file not found: $PLAN_WITHOUT_STORIES_FILE" >&2
        exit 1
    fi
}

_validate_plan_with_stories() {
    if [ ! -f "$PLAN_WITH_STORIES_FILE" ]; then
        echo "Error: Story plan file not found: $PLAN_WITH_STORIES_FILE" >&2
        exit 1
    fi
}

_session_id() {
    cat "$SESSION_ID_FILE"
}
