Add a `--completed-plans` flag to `i2code idea state` that automatically
transitions ideas from `wip` to `completed` when all plan tasks are done.

Currently, completing all plan tasks does not update the idea's lifecycle state.
Users must manually run `i2code idea state <name> completed` for each idea.
This creates a gap between finishing implementation and archiving.

The `--completed-plans` flag will:

- Scan all active ideas in `wip` state
- For each, check if a plan file exists with at least one task
- If all tasks in the plan are complete (`Plan.get_next_task() is None`), transition the idea to `completed`
- Stage all metadata changes and create a single git commit
- Print each transitioned idea name
- Print an informational message if no matching ideas are found
- Support `--no-commit` to stage without committing

This fills the workflow gap between `i2code implement` (completes plan tasks)
and `i2code idea archive --completed` (archives completed ideas).
