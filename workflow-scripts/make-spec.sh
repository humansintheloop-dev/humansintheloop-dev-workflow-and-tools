#! /bin/bash -e

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# shellcheck disable=SC1091
source "$DIR/_helper.sh"

_validate_idea

claude  --resume "$(_session_id)" "/idea-create-spec idea-file=${IDEA_FILE?} discussion-file=${DISCUSSION_FILE?}"