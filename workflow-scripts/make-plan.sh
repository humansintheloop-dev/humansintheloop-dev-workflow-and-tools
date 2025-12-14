#! /bin/bash -e

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# shellcheck disable=SC1091
source "$DIR/_helper.sh"

_validate_idea
_validate_spec

export IDEA_FILE SPEC_FILE
PROMPT=$(envsubst < "$DIR/../prompt-templates/create-implementation-plan.md")

claude "$PROMPT"