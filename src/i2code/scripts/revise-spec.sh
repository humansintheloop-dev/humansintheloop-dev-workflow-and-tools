#! /bin/bash -e

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# shellcheck disable=SC1091
source "$DIR/_helper.sh"

_validate_idea
_validate_spec

claude  "Here are three files:

* ${IDEA_FILE?} - the file containing the idea description
* ${DISCUSSION_FILE?} - the file where questions and answers were saved when brainstorming the idea
* ${SPEC_FILE?}  - a comprehensive, developer-ready specification that was generated as a result of brainstorming

I will ask you to make changes to the specification
"
