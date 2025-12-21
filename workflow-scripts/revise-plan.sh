#! /bin/bash -e

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# shellcheck disable=SC1091
source "$DIR/_helper.sh"

_validate_idea
_validate_spec
_validate_plan_without_stories

export IDEA_FILE SPEC_FILE PLAN_WITHOUT_STORIES_FILE
PROMPT=$(envsubst < "$DIR/../prompt-templates/revise-plan.md")

claude "$PROMPT"