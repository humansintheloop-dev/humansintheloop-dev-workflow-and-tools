#! /bin/bash -e

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# shellcheck disable=SC1091
source "$DIR/_helper.sh"


if ! ls "$IDEA_FILE" >/dev/null 2>&1; then
    mkdir -p "$IDEA_DIR"
    echo "PLEASE DESCRIBE YOUR IDEA" >> "$IDEA_FILE"
    vi "$IDEA_FILE"
fi

if [ ! -f "$SESSION_ID_FILE" ]; then
    uuidgen > "$SESSION_ID_FILE"
    SESSION_ARG="--session-id"
else
    SESSION_ARG="--resume"
fi

export IDEA_FILE DISCUSSION_FILE
PROMPT=$(envsubst < "$DIR/../prompt-templates/brainstorm-idea.md")

claude "$SESSION_ARG" "$(_session_id)" "$PROMPT"
