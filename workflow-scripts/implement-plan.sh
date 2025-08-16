#! /bin/bash -e

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# shellcheck disable=SC1091
source "$DIR/_helper.sh"

_validate_idea
_validate_spec
_validate_plan_without_stories

claude "You are building this application:

* Idea - ${IDEA_FILE?} 
* Specification - ${SPEC_FILE?} 

The set of implementation tasks are in this file ${PLAN_WITHOUT_STORIES_FILE?}.

Update the plan file when a task is implemented"