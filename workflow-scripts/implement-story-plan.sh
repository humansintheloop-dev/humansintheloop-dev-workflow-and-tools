#! /bin/bash -e

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# shellcheck disable=SC1091
source "$DIR/_helper.sh"

_validate_idea
_validate_spec
_validate_story
_validate_plan_with_stories

SPECIFIC_TASK=

if [ -n "$1" ] ; then
  SPECIFIC_TASK="Implement this task only: $1"
fi

claude  "You are building this application:

* Idea - ${IDEA_FILE?} 
* Specification - ${SPEC_FILE?} 
* User stories - ${STORY_FILE?} 

The set of implementation tasks are in this file ${PLAN_WITH_STORIES_FILE?}.

${SPECIFIC_TASK}

IMPORTANT when a task is implemented (the tests have been written and pass), Update the plan file to mark the task as completed.
Do this  BEFORE committing the task's changes  so that the commit includes the task's changes and the updated plan"