#! /bin/bash -e

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# shellcheck disable=SC1091
source "$DIR/_helper.sh"

_validate_idea
_validate_spec
_validate_plan_without_stories

SPECIFIC_TASK=

if [ -n "$1" ] ; then
  SPECIFIC_TASK="Implement this task only: $1"
fi

export IDEA_FILE SPEC_FILE PLAN_WITHOUT_STORIES_FILE SPECIFIC_TASK
PROMPT=$(envsubst < "$DIR/../prompt-templates/implement-plan.md")

claude "$@" "$PROMPT"
