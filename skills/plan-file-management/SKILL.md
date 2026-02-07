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

## list-threads

Return all threads with their numbers, titles, and task completion counts.

    uv run skills/plan-file-management/scripts/plan-manager.py list-threads <plan_file>

## get-summary

Return the plan's name, idea type, overview, and progress (thread count, task count, completed task count).

    uv run skills/plan-file-management/scripts/plan-manager.py get-summary <plan_file>

## get-thread

Return a specific thread's full content including number, title, introduction, and all tasks with their metadata and steps.

    uv run skills/plan-file-management/scripts/plan-manager.py get-thread <plan_file> --thread <N>

Errors if the thread does not exist.

## mark-step-complete

Mark a single step as complete. Appends to change history.

    uv run skills/plan-file-management/scripts/plan-manager.py mark-step-complete <plan_file> --thread <N> --task <M> --step <S> --rationale <text>

Errors if the step does not exist or is already complete.

## replace-thread

Replace a thread's entire content (title, introduction, tasks) in place, then auto-renumber.

    uv run skills/plan-file-management/scripts/plan-manager.py replace-thread <plan_file> --thread <N> --title <title> --introduction <text> --tasks <json> --rationale <text>

Errors if the thread does not exist.

## insert-task-before

Insert a task before a specified task within a thread, then auto-renumber tasks.

    uv run skills/plan-file-management/scripts/plan-manager.py insert-task-before <plan_file> --thread <N> --before <M> --title <title> --task-type <INFRA|OUTCOME> --entrypoint <cmd> --observable <text> --evidence <cmd> --steps <json> --rationale <text>

The `--steps` argument is a JSON array of step description strings.

## insert-task-after

Insert a task after a specified task within a thread, then auto-renumber tasks.

    uv run skills/plan-file-management/scripts/plan-manager.py insert-task-after <plan_file> --thread <N> --after <M> --title <title> --task-type <INFRA|OUTCOME> --entrypoint <cmd> --observable <text> --evidence <cmd> --steps <json> --rationale <text>

## reorder-tasks

Reorder tasks within a thread according to a specified ordering, then auto-renumber tasks.

    uv run skills/plan-file-management/scripts/plan-manager.py reorder-tasks <plan_file> --thread <N> --order <comma-separated-task-numbers> --rationale <text>

Example: `--thread 1 --order 3,1,2` moves task 1.3 to position 1.1, task 1.1 to position 1.2, task 1.2 to position 1.3.

Errors if `--order` does not contain exactly the set of existing task numbers in the thread, or if the thread does not exist.

## move-task-before

Move a task to before another task within the same thread, then auto-renumber tasks.

    uv run skills/plan-file-management/scripts/plan-manager.py move-task-before <plan_file> --thread <N> --task <M> --before <P> --rationale <text>

Example: `--thread 1 --task 6 --before 3` moves task 1.6 to the position before task 1.3.

Errors if the thread or either task does not exist, or if task and before are the same.

## delete-task

Remove a task from a thread, then auto-renumber remaining tasks.

    uv run skills/plan-file-management/scripts/plan-manager.py delete-task <plan_file> --thread <N> --task <M> --rationale <text>

Errors if the thread or task does not exist.

## delete-thread

Remove a thread entirely, then auto-renumber remaining threads and tasks.

    uv run skills/plan-file-management/scripts/plan-manager.py delete-thread <plan_file> --thread <N> --rationale <text>

Errors if the thread does not exist.
