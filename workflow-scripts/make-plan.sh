#! /bin/bash -e

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# shellcheck disable=SC1091
source "$DIR/_helper.sh"

_validate_idea
_validate_spec

claude  "/idea-to-code:idea-create-implementation-plan ${IDEA_FILE?} ${SPEC_FILE?}"