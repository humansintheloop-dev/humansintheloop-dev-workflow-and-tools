# Implementation Plan: Plan File Management Scripts

## Idea Type

**C. Platform/infrastructure capability** - A CLI script that provides Claude with programmatic access to manipulate steel-thread implementation plan files, replacing error-prone raw text editing with typed, auto-renumbering operations.

---

## Instructions for Coding Agent

- IMPORTANT: Use simple commands that you have permission to execute. Avoid complex commands that may fail due to permission issues.

### Required Skills

Use these skills by invoking them before the relevant action:

| Skill | When to Use |
|-------|-------------|
| `idea-to-code:plan-tracking` | ALWAYS - track task completion in the plan file |
| `idea-to-code:tdd` | When implementing code - write failing tests first |
| `idea-to-code:commit-guidelines` | Before creating any git commit |
| `idea-to-code:incremental-development` | When writing multiple similar files (tests, classes, configs) |
| `idea-to-code:testing-scripts-and-infrastructure` | When building shell scripts or test infrastructure |
| `idea-to-code:file-organization` | When moving, renaming, or reorganizing files |

### TDD Requirements

- NEVER write production code without first writing a failing test
- Before using Write on any `.py` file in `skills/`, ask: "Do I have a failing test?" If not, write the test first
- When task direction changes mid-implementation, return to TDD PLANNING state and write a test first

### Testing Strategy

- **Unit tests using pytest** are the primary testing approach. Each operation is implemented as a pure function that takes a plan as a string and returns a string (e.g., `fix_numbering(plan: str) -> str`, `reorder_threads(plan: str, order: list[int]) -> str`). Pytest tests call these functions directly and assert the result. Test fixtures are inline strings in the test code, not separate files.
- **Test runner**: `pytest tests/plan-manager/` runs all unit tests.

### Verification Requirements

- Hard rule: NEVER git commit, git push, or open a PR unless you have successfully run the project's test command and it exits 0
- Hard rule: If running tests is blocked for any reason (including permissions), ALWAYS STOP immediately. Print the failing command, the exact error output, and the permission/path required
- Before committing, ALWAYS print a Verification section containing the exact test command, its exit code, and the last 20 lines of output

---

## Overview

This plan implements the Plan File Management Scripts that give Claude structured, typed access to read and modify steel-thread implementation plan files. The scripts are a single Python script (`skills/plan-file-management/scripts/plan-manager.py`) using PEP 723 inline metadata with no dependencies beyond the Python standard library, run via `uv run`. The script is integrated via the `plan-file-management` skill's `SKILL.md`.

The script exposes 15 subcommands: 4 read operations (list-threads, get-thread, get-next-task, get-summary) and 11 write operations (fix-numbering, reorder-threads, insert/delete/replace-thread, insert/delete-task, mark-task-complete, mark-step-complete). Write operations auto-renumber threads and tasks, perform atomic file writes, and append to a change history section.

The implementation uses TDD throughout. Each task includes writing failing tests first, then implementing code to make them pass.

---

## Steel Thread 1: Script with Fix Numbering

Migrates the existing `fix-plan-numbering.py` into `plan-manager.py` as the `fix-numbering` subcommand. Establishes the script infrastructure with `argparse` subcommands. The existing `fix_numbering` pure function and its tests are preserved; only the import path and CLI entry point change.

- [x] **Task 1.1: plan-manager.py script with fix-numbering subcommand and passing unit tests**
  - TaskType: INFRA
  - Entrypoint: `uv run skills/plan-file-management/scripts/plan-manager.py fix-numbering <plan_file>`
  - Observable: Script runs, accepts `fix-numbering` subcommand. Pytest tests verify `fix_numbering` function correctly renumbers a misnumbered plan.
  - Evidence: `pytest tests/plan-manager/` passes
  - Steps:
    - [x] Create `skills/plan-file-management/scripts/plan-manager.py` with PEP 723 inline metadata (no dependencies, `>=3.10`)
    - [x] Set up `argparse` with subcommand structure
    - [x] Migrate `fix_numbering(plan: str) -> str` pure function from `fix-plan-numbering.py`
    - [x] Migrate `atomic_write` helper from `fix-plan-numbering.py`
    - [x] Implement `fix-numbering` subcommand that reads the file, calls `fix_numbering`, and writes the result
    - [x] Update `tests/plan-manager/test_fix_numbering.py` import path to import from `plan-manager.py` module
    - [x] Verify all existing tests pass with the new import path
    - [x] Update `skills/plan-file-management/SKILL.md` to reference `plan-manager.py fix-numbering` instead of `fix-plan-numbering.py`

---

## Steel Thread 2: Mark Task Complete

Implements task-level completion, marking the task and all its steps complete.

- [x] **Task 2.1: mark-task-complete marks a task and all its steps as complete**
  - TaskType: OUTCOME
  - Entrypoint: `uv run skills/plan-file-management/scripts/plan-manager.py mark-task-complete <plan_file> --thread <N> --task <M> --rationale <text>`
  - Observable: After running `mark-task-complete`, the task line and all its step lines have `- [x]`, and change history is appended
  - Evidence: `pytest tests/plan-manager/` passes
  - Steps:
    - [x] Implement `mark_task_complete(plan: str, thread_number: int, task_number: int, rationale: str) -> str` as a pure function
    - [x] Change task line `- [ ]` to `- [x]` and all steps within the task from `- [ ]` to `- [x]`
    - [x] Append to change history
    - [x] Return error if task does not exist or is already complete
    - [x] Register `mark-task-complete` subcommand with argparse
    - [x] Write pytest tests covering: task and steps marked complete, change history appended, error on already-complete task, error on nonexistent task
    - [x] Update `skills/plan-file-management/SKILL.md` to document the `mark-task-complete` subcommand

---

## Steel Thread 3: Reorder Threads

Implements thread reordering, allowing threads to be rearranged according to a specified ordering with auto-renumbering.

- [x] **Task 3.1: reorder-threads rearranges threads and renumbers**
  - TaskType: OUTCOME
  - Entrypoint: `uv run skills/plan-file-management/scripts/plan-manager.py reorder-threads <plan_file> --order 2,1 --rationale <text>`
  - Observable: After running `reorder-threads` with `--order 2,1` on a 2-thread plan, the threads are swapped in position, all threads and tasks are renumbered sequentially, and change history is appended
  - Evidence: `pytest tests/plan-manager/` passes
  - Steps:
    - [x] Implement `reorder_threads(plan: str, thread_order: list[int], rationale: str) -> str` as a pure function
    - [x] Auto-renumber all threads and tasks after reordering
    - [x] Append to change history with rationale
    - [x] Return error if `thread_order` does not contain exactly the set of existing thread numbers
    - [x] Register `reorder-threads` subcommand with argparse
    - [x] Write pytest tests covering: correct reordering and renumbering, change history appended, error on invalid thread_order (missing threads, duplicates, nonexistent numbers)
    - [x] Update `skills/plan-file-management/SKILL.md` to document the `reorder-threads` subcommand

---

## Steel Thread 4: Insert Thread

Implements thread insertion (before and after), with auto-renumbering.

- [x] **Task 4.1: insert-thread-before inserts a thread and renumbers**
  - TaskType: OUTCOME
  - Entrypoint: `uv run skills/plan-file-management/scripts/plan-manager.py insert-thread-before <plan_file> --before 2 --title <title> --introduction <text> --tasks <json> --rationale <text>`
  - Observable: After running `insert-thread-before` with `--before 2`, the new thread appears before the old thread 2, all threads are renumbered sequentially, all task numbers reflect new thread numbers, and change history is appended
  - Evidence: `pytest tests/plan-manager/` passes
  - Steps:
    - [x] Implement thread serialization: convert structured thread data (title, introduction, tasks with all fields) to markdown
    - [x] Implement `insert_thread_before(plan: str, before_thread: int, title: str, introduction: str, tasks: list, rationale: str) -> str` as a pure function
    - [x] Auto-renumber all threads and tasks after insertion
    - [x] Return error if `before_thread` does not exist
    - [x] Register `insert-thread-before` subcommand with argparse
    - [x] Write pytest tests covering: correct insertion position, renumbering, change history, error on nonexistent thread
    - [x] Update `skills/plan-file-management/SKILL.md` to document the `insert-thread-before` subcommand

- [x] **Task 4.2: insert-thread-after inserts a thread after the specified thread**
  - TaskType: OUTCOME
  - Entrypoint: `uv run skills/plan-file-management/scripts/plan-manager.py insert-thread-after <plan_file> --after 1 --title <title> --introduction <text> --tasks <json> --rationale <text>`
  - Observable: After running `insert-thread-after` with `--after 1`, the new thread appears after thread 1, all threads are renumbered, and change history is appended
  - Evidence: `pytest tests/plan-manager/` passes
  - Steps:
    - [x] Implement `insert_thread_after(plan: str, after_thread: int, title: str, introduction: str, tasks: list, rationale: str) -> str` as a pure function
    - [x] Auto-renumber all threads and tasks
    - [x] Return error if `after_thread` does not exist
    - [x] Register `insert-thread-after` subcommand with argparse
    - [x] Write pytest tests covering: correct insertion position, renumbering, error on nonexistent thread
    - [x] Update `skills/plan-file-management/SKILL.md` to document the `insert-thread-after` subcommand

---

## Steel Thread 5: Get Next Uncompleted Task

Implements the `get-next-task` read operation.

- [x] **Task 5.1: get-next-task returns the first uncompleted task across the plan**
  - TaskType: OUTCOME
  - Entrypoint: `uv run skills/plan-file-management/scripts/plan-manager.py get-next-task <plan_file>`
  - Observable: `get-next-task` prints the first task where `completed` is false, including thread_number, task_number, full metadata, and steps. Prints a message when all tasks are complete.
  - Evidence: `pytest tests/plan-manager/` passes
  - Steps:
    - [x] Implement `get_next_task(plan: str) -> dict` as a pure function: iterate through threads and tasks, returning first uncompleted task
    - [x] Return descriptive message when no uncompleted tasks remain
    - [x] Register `get-next-task` subcommand with argparse
    - [x] Write pytest tests covering: returns correct next uncompleted task (skips completed ones), returns all-complete message when no tasks remain
    - [x] Update `skills/plan-file-management/SKILL.md` to document the `get-next-task` subcommand

---

## Steel Thread 6: Get Thread Details

Implements the `get-thread` read operation, returning a thread's full content including tasks and steps.

- [x] **Task 6.1: get-thread returns full thread content with tasks and steps**
  - TaskType: OUTCOME
  - Entrypoint: `uv run skills/plan-file-management/scripts/plan-manager.py get-thread <plan_file> --thread 1`
  - Observable: `get-thread` prints the specified thread's number, title, introduction, and all tasks with their metadata (title, completed, task_type, entrypoint, observable, evidence, steps with completion status)
  - Evidence: `pytest tests/plan-manager/` passes
  - Steps:
    - [x] Implement full task metadata parsing: title, completed flag, task_type, entrypoint, observable, evidence
    - [x] Implement step parsing: description and completed flag from `- [ ]`/`- [x]` lines under `Steps:`
    - [x] Implement introduction extraction (text between thread heading and first task)
    - [x] Implement `get_thread(plan: str, thread_number: int) -> dict` as a pure function
    - [x] Register `get-thread` subcommand with argparse
    - [x] Write pytest tests covering: correct introduction, task metadata, step parsing, error on nonexistent thread_number
    - [x] Update `skills/plan-file-management/SKILL.md` to document the `get-thread` subcommand

---

## Steel Thread 7: Get Plan Summary

Adds the `get-summary` read operation, returning plan metadata and progress.

- [x] **Task 7.1: get-summary returns plan metadata**
  - TaskType: OUTCOME
  - Entrypoint: `uv run skills/plan-file-management/scripts/plan-manager.py get-summary <plan_file>`
  - Observable: `get-summary` prints plan name, idea type, overview, thread count, task count, and completed task count
  - Evidence: `pytest tests/plan-manager/` passes
  - Steps:
    - [x] Implement `get_summary(plan: str) -> dict` as a pure function: extract `# Implementation Plan:` heading, `## Idea Type` section, `## Overview` section, count threads and tasks
    - [x] Register `get-summary` subcommand with argparse
    - [x] Write pytest tests covering: correct plan name, idea type, overview, thread/task counts including completed count
    - [x] Update `skills/plan-file-management/SKILL.md` to document the `get-summary` subcommand

---

## Steel Thread 8: List Threads

Implements the `list-threads` read operation, returning all threads with completion status.

- [x] **Task 8.1: list-threads returns all threads with completion status**
  - TaskType: OUTCOME
  - Entrypoint: `uv run skills/plan-file-management/scripts/plan-manager.py list-threads <plan_file>`
  - Observable: `list-threads` prints a list of threads each with number, title, total_tasks, and completed_tasks
  - Evidence: `pytest tests/plan-manager/` passes
  - Steps:
    - [x] Implement `list_threads(plan: str) -> list[dict]` as a pure function: extract thread numbers, titles, count total and completed tasks per thread
    - [x] Register `list-threads` subcommand with argparse
    - [x] Write pytest tests covering: correct thread numbers, titles, task counts with mix of completed and uncompleted tasks
    - [x] Update `skills/plan-file-management/SKILL.md` to document the `list-threads` subcommand

---

## Steel Thread 9: Mark Step Complete

Implements step-level completion, proving atomic writes and change history work.

- [x] **Task 9.1: mark-step-complete changes a step from unchecked to checked and appends change history**
  - TaskType: OUTCOME
  - Entrypoint: `uv run skills/plan-file-management/scripts/plan-manager.py mark-step-complete <plan_file> --thread <N> --task <M> --step <S> --rationale <text>`
  - Observable: After running `mark-step-complete`, the plan has `- [x]` on the specified step line and a new entry in the `## Change History` section with timestamp, operation name, and rationale.
  - Evidence: `pytest tests/plan-manager/` passes
  - Steps:
    - [x] Implement atomic file write (write to temp file in same directory, then `os.rename`)
    - [x] Implement change history appending: find or create `## Change History` section, append `### <timestamp> - <operation>` with rationale
    - [x] Implement `mark_step_complete(plan: str, thread_number: int, task_number: int, step_number: int, rationale: str) -> str` as a pure function
    - [x] Return error if step does not exist or is already complete
    - [x] Register `mark-step-complete` subcommand with argparse
    - [x] Write pytest tests covering: step checkbox changed to `[x]`, change history appended with rationale, error on already-complete step, error on nonexistent step
    - [x] Update `skills/plan-file-management/SKILL.md` to document the `mark-step-complete` subcommand

---

## Steel Thread 10: Delete Thread

Implements thread deletion with auto-renumbering.

- [x] **Task 10.1: delete-thread removes a thread and renumbers remaining threads**
  - TaskType: OUTCOME
  - Entrypoint: `uv run skills/plan-file-management/scripts/plan-manager.py delete-thread <plan_file> --thread 1 --rationale <text>`
  - Observable: After running `delete-thread` with `--thread 1`, thread 1 and all its tasks are removed, remaining threads are renumbered starting from 1, and change history is appended
  - Evidence: `pytest tests/plan-manager/` passes
  - Steps:
    - [x] Implement `delete_thread(plan: str, thread_number: int, rationale: str) -> str` as a pure function: remove all content from thread heading to the next thread heading (or Summary section)
    - [x] Auto-renumber remaining threads and tasks
    - [x] Return error if `thread_number` does not exist
    - [x] Append to change history with rationale
    - [x] Register `delete-thread` subcommand with argparse
    - [x] Write pytest tests covering: thread removed, remaining threads renumbered, change history appended, error on nonexistent thread
    - [x] Update `skills/plan-file-management/SKILL.md` to document the `delete-thread` subcommand

---

## Steel Thread 11: Replace Thread

Implements thread replacement, keeping position but replacing content entirely.

- [x] **Task 11.1: replace-thread replaces a thread's content in place**
  - TaskType: OUTCOME
  - Entrypoint: `uv run skills/plan-file-management/scripts/plan-manager.py replace-thread <plan_file> --thread 1 --title <title> --introduction <text> --tasks <json> --rationale <text>`
  - Observable: After running `replace-thread` with `--thread 1` and new content, thread 1 has the new title, introduction, and tasks, other threads are unchanged, tasks are correctly numbered, and change history is appended
  - Evidence: `pytest tests/plan-manager/` passes
  - Steps:
    - [x] Implement `replace_thread(plan: str, thread_number: int, title: str, introduction: str, tasks: list, rationale: str) -> str` as a pure function
    - [x] Auto-renumber tasks within the replaced thread
    - [x] Return error if `thread_number` does not exist
    - [x] Append to change history with rationale
    - [x] Register `replace-thread` subcommand with argparse
    - [x] Write pytest tests covering: new content at correct position, other threads unchanged, renumbering, change history, error on nonexistent thread
    - [x] Update `skills/plan-file-management/SKILL.md` to document the `replace-thread` subcommand

---

## Steel Thread 12: Insert Task

Implements task insertion within a thread (before and after), with auto-renumbering of tasks.

- [x] **Task 12.1: insert-task-before inserts a task and renumbers within the thread**
  - TaskType: OUTCOME
  - Entrypoint: `uv run skills/plan-file-management/scripts/plan-manager.py insert-task-before <plan_file> --thread 1 --before 1 --title <title> --task-type INFRA --entrypoint <cmd> --observable <text> --evidence <cmd> --steps <json> --rationale <text>`
  - Observable: After running `insert-task-before` with `--thread 1 --before 1`, the new task appears before the old task 1.1, all tasks within thread 1 are renumbered, and change history is appended
  - Evidence: `pytest tests/plan-manager/` passes
  - Steps:
    - [x] Implement task serialization: convert structured task data to markdown (checkbox line, metadata, steps)
    - [x] Implement `insert_task_before(plan: str, thread_number: int, before_task: int, title: str, task_type: str, entrypoint: str, observable: str, evidence: str, steps: list[str], rationale: str) -> str` as a pure function
    - [x] Auto-renumber tasks within the thread after insertion
    - [x] Return error if `thread_number` or `before_task` does not exist
    - [x] Register `insert-task-before` subcommand with argparse
    - [x] Write pytest tests covering: correct insertion position, renumbering, change history, error on nonexistent thread/task
    - [x] Update `skills/plan-file-management/SKILL.md` to document the `insert-task-before` subcommand

- [x] **Task 12.2: insert-task-after inserts a task after the specified task**
  - TaskType: OUTCOME
  - Entrypoint: `uv run skills/plan-file-management/scripts/plan-manager.py insert-task-after <plan_file> --thread 1 --after 1 --title <title> --task-type INFRA --entrypoint <cmd> --observable <text> --evidence <cmd> --steps <json> --rationale <text>`
  - Observable: After running `insert-task-after` with `--thread 1 --after 1`, the new task appears after task 1.1, tasks are renumbered, and change history is appended
  - Evidence: `pytest tests/plan-manager/` passes
  - Steps:
    - [x] Implement `insert_task_after(plan: str, thread_number: int, after_task: int, title: str, task_type: str, entrypoint: str, observable: str, evidence: str, steps: list[str], rationale: str) -> str` as a pure function
    - [x] Auto-renumber tasks within the thread
    - [x] Return error if `thread_number` or `after_task` does not exist
    - [x] Register `insert-task-after` subcommand with argparse
    - [x] Write pytest tests covering: correct insertion position, renumbering, error on nonexistent thread/task
    - [x] Update `skills/plan-file-management/SKILL.md` to document the `insert-task-after` subcommand

---

## Steel Thread 13: Delete Task

Implements task deletion within a thread with auto-renumbering.

- [x] **Task 13.1: delete-task removes a task and renumbers remaining tasks in the thread**
  - TaskType: OUTCOME
  - Entrypoint: `uv run skills/plan-file-management/scripts/plan-manager.py delete-task <plan_file> --thread 1 --task 1 --rationale <text>`
  - Observable: After running `delete-task` with `--thread 1 --task 1`, the task is removed, remaining tasks in thread 1 are renumbered, and change history is appended
  - Evidence: `pytest tests/plan-manager/` passes
  - Steps:
    - [x] Implement `delete_task(plan: str, thread_number: int, task_number: int, rationale: str) -> str` as a pure function
    - [x] Auto-renumber remaining tasks in the thread
    - [x] Return error if `thread_number` or `task_number` does not exist
    - [x] Append to change history
    - [x] Register `delete-task` subcommand with argparse
    - [x] Write pytest tests covering: task removed, remaining tasks renumbered, change history appended, error on nonexistent thread/task
    - [x] Update `skills/plan-file-management/SKILL.md` to document the `delete-task` subcommand

---

## Steel Thread 14: Round-Trip Fidelity and Error Handling

Validates that reading a plan and writing it back produces identical output, and that all error cases return clear messages.

- [x] **Task 14.1: Round-trip read/write produces identical plan file content**
  - TaskType: OUTCOME
  - Entrypoint: `uv run skills/plan-file-management/scripts/plan-manager.py fix-numbering <plan_file>`
  - Observable: Running `fix-numbering` on an already correctly-numbered plan produces byte-identical output
  - Evidence: `pytest tests/plan-manager/` passes
  - Steps:
    - [x] Write pytest tests that call `fix_numbering` on a correctly-numbered plan and assert the output equals the input
    - [x] Ensure parser preserves all whitespace, blank lines, horizontal rules, and section ordering

- [x] **Task 14.2: Error cases return clear, actionable messages**
  - TaskType: OUTCOME
  - Entrypoint: `uv run skills/plan-file-management/scripts/plan-manager.py`
  - Observable: Calling functions with invalid parameters (nonexistent thread, nonexistent task, already-complete task) returns errors with subcommand name, failing parameter, and human-readable message
  - Evidence: `pytest tests/plan-manager/` passes
  - Steps:
    - [x] Write pytest tests covering error cases: nonexistent `thread_number` on `get_thread`, `mark_task_complete` on already-complete task, `mark_step_complete` on already-complete step, `delete_thread` on nonexistent thread, `insert_task_before` on nonexistent task

---

## Steel Thread 15: Reorder Tasks
Implements task reordering within a thread, allowing tasks to be rearranged according to a specified ordering with auto-renumbering. Analogous to reorder-threads but operates on tasks within a single thread. For example, `--order 3,1,2` on thread 1 moves task 1.3 to position 1, task 1.1 to position 2, and task 1.2 to position 3.

- [x] **Task 15.1: reorder-tasks rearranges tasks within a thread and renumbers**
  - TaskType: OUTCOME
  - Entrypoint: `uv run skills/plan-file-management/scripts/plan-manager.py reorder-tasks <plan_file> --thread 1 --order 3,1,2 --rationale <text>`
  - Observable: After running reorder-tasks with --thread 1 --order 3,1,2 on a thread with 3 tasks, the tasks are rearranged to the new order, all tasks are renumbered sequentially, and change history is appended
  - Evidence: `pytest tests/plan-manager/ passes`
  - Steps:
    - [x] Implement reorder_tasks(plan: str, thread_number: int, task_order: list[int], rationale: str) -> str as a pure function
    - [x] Auto-renumber all tasks within the thread after reordering
    - [x] Append to change history with rationale
    - [x] Return error if thread_number does not exist
    - [x] Return error if task_order does not contain exactly the set of existing task numbers in the thread
    - [x] Register reorder-tasks subcommand with argparse
    - [x] Write pytest tests covering: correct reordering and renumbering, change history appended, error on invalid task_order (missing tasks, duplicates, nonexistent numbers), error on nonexistent thread
    - [x] Update skills/plan-file-management/SKILL.md to document the reorder-tasks subcommand

---

## Steel Thread 16: Move Task
Implements moving an existing task to a new position within the same thread. Unlike reorder-tasks which requires specifying the full ordering, move-task-before and move-task-after relocate a single task relative to another task. For example, `move-task-before --thread 1 --task 6 --before 3` moves task 1.6 to just before task 1.3, then renumbers all tasks in the thread.

- [x] **Task 16.1: move-task-before moves a task to before another task within the same thread**
  - TaskType: OUTCOME
  - Entrypoint: `uv run skills/plan-file-management/scripts/plan-manager.py move-task-before <plan_file> --thread 1 --task 6 --before 3 --rationale <text>`
  - Observable: After running move-task-before with --thread 1 --task 6 --before 3, task 1.6 appears before old task 1.3, all tasks are renumbered sequentially, and change history is appended
  - Evidence: `pytest tests/plan-manager/ passes`
  - Steps:
    - [x] Implement move_task_before(plan: str, thread_number: int, task_number: int, before_task: int, rationale: str) -> str as a pure function
    - [x] Auto-renumber all tasks within the thread after moving
    - [x] Append to change history with rationale
    - [x] Return error if thread_number, task_number, or before_task does not exist
    - [x] Return error if task_number equals before_task
    - [x] Register move-task-before subcommand with argparse
    - [x] Write pytest tests covering: correct move position, renumbering, change history, error on nonexistent thread/task, error on same task
    - [x] Update skills/plan-file-management/SKILL.md to document the move-task-before subcommand

- [ ] **Task 16.2: move-task-after moves a task to after another task within the same thread**
  - TaskType: OUTCOME
  - Entrypoint: `uv run skills/plan-file-management/scripts/plan-manager.py move-task-after <plan_file> --thread 1 --task 1 --after 3 --rationale <text>`
  - Observable: After running move-task-after with --thread 1 --task 1 --after 3, task 1.1 appears after old task 1.3, all tasks are renumbered sequentially, and change history is appended
  - Evidence: `pytest tests/plan-manager/ passes`
  - Steps:
    - [ ] Implement move_task_after(plan: str, thread_number: int, task_number: int, after_task: int, rationale: str) -> str as a pure function
    - [ ] Auto-renumber all tasks within the thread after moving
    - [ ] Return error if thread_number, task_number, or after_task does not exist
    - [ ] Register move-task-after subcommand with argparse
    - [ ] Write pytest tests covering: correct move position, renumbering, error on nonexistent thread/task
    - [ ] Update skills/plan-file-management/SKILL.md to document the move-task-after subcommand

---

## Summary

This plan covers 16 steel threads with 21 tasks implementing the complete Plan File Management Scripts:

1. **Script with Fix Numbering**: Migrates existing fix-numbering into plan-manager.py, establishes script infrastructure with argparse subcommands
2. **Mark Task Complete**: Task-level completion with cascading step completion
3. **Reorder Threads**: Rearrange threads according to a specified ordering with auto-renumbering
4. **Insert Thread**: Insert before/after with auto-renumbering
5. **Get Next Task**: Returns first uncompleted task across the plan
6. **Get Thread Details**: Returns full thread content with tasks and steps
7. **Get Plan Summary**: Returns plan metadata and progress
8. **List Threads**: Returns all threads with completion status
9. **Mark Step Complete**: Atomic writes and change history
10. **Delete Thread**: Remove thread with auto-renumbering
11. **Replace Thread**: Replace thread content in place
12. **Insert Task**: Insert before/after within a thread
13. **Delete Task**: Remove task with auto-renumbering
14. **Round-Trip Fidelity and Error Handling**: Verifies no formatting drift and validates all error cases
15. **Reorder Tasks**: Rearrange tasks within a thread with auto-renumbering
16. **Move Task**: Move a single task before/after another task within the same thread

---

## Change History
### 2026-02-06 - Reorder steel threads
Reordered steel threads 1-8 per user request. New order prioritizes Fix Numbering (1), Mark Task Complete (2), Insert Thread (3), Get Next Uncompleted Task (4), Get Thread Details (5), MCP Server Starts (6), List Threads (7), Mark Step Complete (8). Threads 9-13 unchanged. All thread and task numbers renumbered to match new positions.

### 2026-02-06 - Add plan_reorder_threads tool
Added `plan_reorder_threads` write operation to spec and plan. Inserted as Steel Thread 3 (after Mark Task Complete). Renumbered subsequent threads 3→4 through 13→14. Updated spec with tool definition, scenario, and acceptance criteria count (10→11 write tools). Plan now has 14 steel threads with 17 tasks.

### 2026-02-06 - Revise testing strategy and Steel Thread 1
Added Testing Strategy section: core tests are unit tests of pure functions (string in, string out); MCP server gets a single smoke test. Revised Steel Thread 1 to include MCP server creation (server.py, CI, plugin registration) alongside fix_numbering as the first tool. Revised Steel Thread 7 from "MCP Server Starts" to "Get Plan Summary" since server infrastructure is now created in Thread 1.

### 2026-02-06 - Inline string fixtures
Updated Testing Strategy to specify that test fixtures are inline strings in test code, not separate files. Removed steps that created fixture files (sample-plan.md, misnumbered-plan.md, all-complete-plan.md).

### 2026-02-06 - Switch to pytest
Replaced all per-test shell scripts with pytest. Each task now has a "Write pytest tests" step instead of "Create test-scripts/test-X.sh". Evidence fields reference `pytest` instead of individual shell scripts. Only two shell scripts remain: `test-scripts/test-mcp-smoke.sh` (MCP smoke test) and `test-scripts/test-end-to-end.sh` (runs pytest + smoke test). Pure functions are now explicitly named in each task's steps (e.g., `mark_task_complete(plan, thread_number, task_number, rationale) -> str`).

### 2026-02-07 - Pivot from MCP server to skill script
Rewrote plan to reflect pivot from MCP server (`mcp-servers/plan-manager/server.py`) to CLI script with subcommands (`skills/plan-file-management/scripts/plan-manager.py`). Removed MCP-specific infrastructure (mcp SDK, stdio transport, MCP smoke test, plugin mcpServers registration, CI workflow for MCP). Steel Thread 1 now describes migrating existing `fix-plan-numbering.py` into `plan-manager.py` as the `fix-numbering` subcommand. All tool registrations changed to argparse subcommand registrations. Testing strategy simplified to pytest only.

### 2026-02-07 - Add SKILL.md update steps
Added a step to each subcommand task (threads 2-13) to update `skills/plan-file-management/SKILL.md` with documentation for the new subcommand when implemented.

### 2026-02-07 11:24 - mark-task-complete
Implemented get_thread pure function, CLI subcommand, tests, and SKILL.md docs

### 2026-02-07 11:25 - mark-task-complete
Implemented get_summary pure function, CLI subcommand, tests, and SKILL.md docs

### 2026-02-07 11:26 - mark-task-complete
Implemented list_threads pure function, CLI subcommand, tests, and SKILL.md docs

### 2026-02-07 11:28 - mark-task-complete
Implemented mark_step_complete pure function, CLI subcommand, tests, and SKILL.md docs

### 2026-02-07 11:29 - mark-task-complete
Implemented delete_thread pure function, CLI subcommand, tests, and SKILL.md docs

### 2026-02-07 11:30 - mark-task-complete
Implemented replace_thread pure function, CLI subcommand, tests, and SKILL.md docs

### 2026-02-07 11:32 - mark-task-complete
Implemented insert_task_before pure function, CLI subcommand, tests, and SKILL.md docs

### 2026-02-07 11:32 - mark-task-complete
Implemented insert_task_after pure function, CLI subcommand, tests, and SKILL.md docs

### 2026-02-07 11:34 - mark-task-complete
Implemented delete_task pure function, CLI subcommand, tests, and SKILL.md docs

### 2026-02-07 11:35 - mark-task-complete
Added comprehensive round-trip fidelity tests with full plan fixture

### 2026-02-07 11:35 - mark-task-complete
Added error message format validation tests covering all subcommands

### 2026-02-07 11:57 - insert-thread-after
Added reorder-tasks feature to support rearranging tasks within a thread

### 2026-02-07 11:59 - insert-thread-after
Added move-task-before and move-task-after for simple single-task relocation within a thread

### 2026-02-07 12:03 - mark-task-complete
Implemented reorder_tasks pure function, CLI subcommand, 11 tests, SKILL.md docs

### 2026-02-07 12:05 - mark-task-complete
Implemented move_task_before pure function, CLI subcommand, 10 tests, SKILL.md docs
