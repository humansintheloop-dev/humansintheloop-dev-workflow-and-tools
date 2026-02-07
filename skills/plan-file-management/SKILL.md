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

## insert-thread-before

Insert a fully structured thread before a specified thread, then auto-renumber.

    uv run skills/plan-file-management/scripts/plan-manager.py insert-thread-before <plan_file> --before <N> --title <title> --introduction <text> --tasks <json> --rationale <text>

The `--tasks` argument is a JSON array of task objects (see spec for schema).

## insert-thread-after

Insert a fully structured thread after a specified thread, then auto-renumber.

    uv run skills/plan-file-management/scripts/plan-manager.py insert-thread-after <plan_file> --after <N> --title <title> --introduction <text> --tasks <json> --rationale <text>

## get-next-task

Return the first uncompleted task across the plan, with full metadata and steps. Prints a message if all tasks are complete.

    uv run skills/plan-file-management/scripts/plan-manager.py get-next-task <plan_file>

## get-summary

Return the plan's name, idea type, overview, and progress (thread count, task count, completed task count).

    uv run skills/plan-file-management/scripts/plan-manager.py get-summary <plan_file>

## get-thread

Return a specific thread's full content including number, title, introduction, and all tasks with their metadata and steps.

    uv run skills/plan-file-management/scripts/plan-manager.py get-thread <plan_file> --thread <N>

Errors if the thread does not exist.
