You are implementing the following application:

* Idea: @${IDEA_FILE}
* Specification: @${SPEC_FILE}
* Implementation tasks: @${PLAN_WITHOUT_STORIES_FILE}

Your task:

${SPECIFIC_TASK}

If ${SPECIFIC_TASK} is empty or not provided:
  - Select the next incomplete task from the plan file (a task with a `[ ]` checkbox).
  - Execute tasks sequentially, one at a time, until no incomplete tasks remain.

Follow the active TDD, plan-tracking, and plan-file-management skills:

Do not work on future tasks until the current one is complete.
If all tasks are complete, stop and report success.
