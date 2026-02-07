---
name: plan-file-management
description: Guidelines for structural operations on plan files (renumbering). Claude should use this skill when the user asks to renumber or fix numbering in a plan file, or after inserting, deleting, or reordering threads/tasks.
---

# Plan File Management

Structural operations on plan files such as renumbering threads and tasks.

All operations are subcommands of `plan-manager.py`, invoked as:

    uv run skills/plan-file-management/scripts/plan-manager.py <subcommand> <plan_file> [options]

## fix-numbering

Renumber all threads and tasks sequentially. Run this after arbitrary edits made outside the script.

    uv run skills/plan-file-management/scripts/plan-manager.py fix-numbering <path-to-plan-file>

Run this after:
- Inserting or deleting threads or tasks
- Rearranging plan sections
- When the user asks to renumber or fix numbering

## mark-task-complete

Mark a task and all its steps as complete. Optionally appends to change history if rationale is provided.

    uv run skills/plan-file-management/scripts/plan-manager.py mark-task-complete <plan_file> --thread <N> --task <M> [--rationale <text>]

Errors if the task does not exist or is already complete.

## reorder-threads

Reorder threads according to a specified ordering, then auto-renumber all threads and tasks.

    uv run skills/plan-file-management/scripts/plan-manager.py reorder-threads <plan_file> --order <comma-separated-thread-numbers> --rationale <text>

Example: `--order 3,1,2` moves thread 3 to position 1, thread 1 to position 2, thread 2 to position 3.

Errors if `--order` does not contain exactly the set of existing thread numbers.
