## Problem

Plan CLI commands that create threads or tasks require complex, multi-line strings to be passed inline on the command line. This is error-prone and unwieldy.

Specifically:

1. **`--tasks-file` is inconsistently supported on thread commands.** `replace-thread` supports `--tasks-file` as an alternative to `--tasks`, but `insert-thread-before` and `insert-thread-after` do not — they only accept `--tasks` inline.

2. **Single-task commands have no file-based input at all.** Commands like `insert-task-before`, `insert-task-after`, and `replace-task` require every field (`--title`, `--task-type`, `--entrypoint`, `--observable`, `--evidence`, `--steps`) as individual CLI options, making them verbose and hard to use for tasks with complex content.

## Proposed Solution

Two changes:

### A. Propagate `--tasks-file` to insert-thread commands

Add `--tasks-file` (mutually exclusive with `--tasks`) to:
- `insert-thread-before`
- `insert-thread-after`

This matches the existing pattern in `replace-thread`.

### B. Add `--task-file` to single-task commands

Add `--task-file` to:
- `insert-task-before`
- `insert-task-after`
- `replace-task`

When `--task-file` is provided, all task fields come from the JSON file. The individual field options (`--title`, `--task-type`, etc.) and `--task-file` are mutually exclusive — no mixing/overriding.

The JSON format reuses the existing task object shape (same as elements in `--tasks` arrays):

```json
{
  "title": "Task name",
  "task_type": "INFRA",
  "entrypoint": "command",
  "observable": "What to observe",
  "evidence": "verification command",
  "steps": ["Step 1", "Step 2"]
}
```

## Classification

**A. User-facing feature** — Improves CLI ergonomics for existing plan management commands.
