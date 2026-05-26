# Discussion: plan-file-support-task-file

## Classification

**A. User-facing feature** — Improves CLI ergonomics for existing plan management commands. Not architecture, infrastructure, or educational.

## Codebase Analysis (pre-discussion)

Before asking questions, the following was established from code exploration:

- `--tasks-file` exists only on `replace-thread` (`thread_cli.py:94`), not on `insert-thread-before` or `insert-thread-after`, which use `_thread_spec_options` (only `--title`, `--introduction`, `--tasks`).
- The `_resolve_tasks_json` helper exists but is only called from `replace_thread_cmd`.
- Single-task commands (`insert-task-before`, `insert-task-after`, `replace-task`) use `_task_spec_options` which requires 6 individual options: `--title`, `--task-type`, `--entrypoint`, `--observable`, `--evidence`, `--steps`.
- Task JSON object format is already established in the `--tasks` array elements and in `Thread.create()` / `Task.create()` factory methods.

## Q&A

### Q1: What is the scope of this idea?

**Options presented:**
- A. Propagate --tasks-file to insert-thread commands
- B. Broader file input for any long option (--introduction, --steps, etc.)
- C. Task-level file input for single-task commands

**Answer:** A and C — propagate `--tasks-file` to insert-thread commands, and add `--task-file` to single-task commands. Broader file input for arbitrary options is out of scope.

### Q2: When --task-file is provided, should individual field options be allowed to override fields from the file?

**Options presented:**
- A. File-only, no overrides (mutually exclusive with individual options)
- B. Allow field overrides (file as defaults, CLI overrides)

**Answer:** A — file-only, no overrides. `--task-file` and individual field options are mutually exclusive, keeping the interface simple.

### Q3: Should the --task-file JSON format reuse the existing task object shape?

**Options presented:**
- A. Same shape as --tasks array elements
- B. Different format

**Answer:** A — reuse the existing JSON object structure for consistency. A user can copy one element from a `--tasks` array into its own file.

## Derived Conclusions

The following were derived from the answers above without needing additional questions:

- **Affected thread commands for `--tasks-file`:** `insert-thread-before`, `insert-thread-after` (2 commands). `replace-thread` already has it.
- **Affected task commands for `--task-file`:** `insert-task-before`, `insert-task-after`, `replace-task` (3 commands). Mark, move, reorder, and delete commands don't create tasks.
- **Error behavior:** Follows `_resolve_tasks_json` pattern — error if both file and inline provided, error if neither provided.
- **Click option type:** `click.Path(exists=True)` for `--task-file`, matching `replace-thread`'s `--tasks-file`.
