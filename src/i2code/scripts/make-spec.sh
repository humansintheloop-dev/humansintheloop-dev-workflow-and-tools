#! /bin/bash -e

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# shellcheck disable=SC1091
source "$DIR/_helper.sh"

_validate_idea

export IDEA_FILE DISCUSSION_FILE
PROMPT=$(envsubst < "$DIR/../prompt-templates/create-spec.md")

SESSION_ID=$(_session_id)
if [ -n "$SESSION_ID" ]; then
    claude --resume "$SESSION_ID" "$@" "$PROMPT"
else
    claude "$@" "$PROMPT"
fi
