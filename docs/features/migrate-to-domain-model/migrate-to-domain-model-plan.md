# Implementation Plan: Migrate Plan Management to Domain Model

## Idea Type

**B. Refactoring/improvement** - Migrate all remaining plan-management operations from standalone string-manipulation functions (tasks.py, threads.py, plans.py, _helpers.py) to the line-owning domain model (plan_domain), following the patterns established in commits d6fcd97 (get_next_task) and 26d3ec2 (mark_task_complete).

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
| `idea-to-code:file-organization` | When moving, renaming, or reorganizing files |

### TDD Requirements

- NEVER write production code without first writing a failing test
- Follow outside-in TDD: CLI integration test first, then domain model unit tests
- Write ONE test at a time, not batches

### Testing Strategy

- **CLI integration tests** use Click's `CliRunner` to invoke commands against temp plan files
- **Domain model unit tests** test Task/Thread/Plan methods directly
- **Test runner**: `uv run --with pytest pytest tests/plan-domain/ tests/plan-manager/ -v`

### Migration Pattern (from reference commits)

Each operation migration follows these steps:

1. Write CLI integration test locking in current behavior
2. Add domain model method(s) with TDD (Task/Thread/Plan layers)
3. Wire CLI handler to use `with_error_handling()` + `with_plan_file_update()` (write ops) or `with_plan_file()` (read ops)
4. Remove standalone function from tasks.py/threads.py/plans.py
5. Delete old unit tests (replaced by domain + CLI tests)
6. Prune duplicate acceptance tests per removing-acceptance-tests guidelines

### Delegation Pattern

Plan methods are pure one-liner delegations — they never validate task ranges or reach into `thread.tasks[]` directly:

- `Plan.get_thread(thread)` validates and returns the Thread (1-based)
- `Thread.get_task(task)` validates and returns the Task (1-based)
- Plan delegates to Thread: `self.get_thread(thread).some_method(task, ...)`
- Thread delegates to Task: `self.get_task(task).some_method(...)`

Error messages are owned by the layer that validates: `get_thread` raises `"thread N does not exist"`, `get_task` raises `"task N does not exist"`.

### Key Files

| File | Role |
|------|------|
| `src/i2code/plan_domain/task.py` | Task entity - add mutation/factory methods |
| `src/i2code/plan_domain/thread.py` | Thread entity - add structural/factory methods |
| `src/i2code/plan_domain/plan.py` | Plan aggregate root - add delegation methods |
| `src/i2code/plan/task_cli.py` | Task CLI handlers - wire to domain model |
| `src/i2code/plan/thread_cli.py` | Thread CLI handlers - wire to domain model |
| `src/i2code/plan/plan_cli.py` | Plan CLI handlers - wire to domain model |
| `src/i2code/plan/plan_file_io.py` | Context managers: with_plan_file, with_plan_file_update, with_error_handling |
| `src/i2code/plan/tasks.py` | Standalone functions to remove (delete file when empty) |
| `src/i2code/plan/threads.py` | Standalone functions to remove (delete file when empty) |
| `src/i2code/plan/plans.py` | Standalone functions to remove (delete file when empty) |
| `src/i2code/plan/_helpers.py` | Shared helpers - consolidate into plan_file_io.py at end |

### Verification Requirements

- Hard rule: NEVER git commit unless you have successfully run the test command and it exits 0
- Before committing, ALWAYS run: `uv run --with pytest pytest tests/plan-domain/ tests/plan-manager/ -v`

---

## Overview

This plan migrates all remaining plan-management operations from standalone string-manipulation pure functions to the line-owning domain model (`plan_domain`). Two operations have already been migrated: `get_next_task` (read-only, commit d6fcd97) and `mark_task_complete` (write, commit 26d3ec2).

The domain model (`Plan` -> `Thread` -> `Task`) owns raw markdown lines and handles renumbering during serialization via `to_text()`. This eliminates the need for regex-based line scanning in each operation and the explicit `fix_numbering()` calls that structural operations currently require.

After migration, the standalone modules (`tasks.py`, `threads.py`, `plans.py`) and most of `_helpers.py` will be deleted, leaving all plan logic in the domain model and all I/O concerns in `plan_file_io.py`.

19 operations remain to migrate: 3 task state mutations, 7 task structural operations, 5 thread structural operations, and 4 plan-level read operations.

---

## Steel Thread 1: Task State Mutations
Migrate mark_task_incomplete, mark_step_complete, and mark_step_incomplete. These follow the exact pattern from the mark_task_complete migration: add mutation method(s) to Task, add delegation to Plan, wire CLI with `with_error_handling` + `with_plan_file_update`, remove standalone function.

- [x] **Task 1.1: Migrate mark_task_incomplete to domain model**
  - TaskType: OUTCOME
  - Entrypoint: `uv run i2code plan mark-task-incomplete tests/fixtures/plan.md --thread 1 --task 1`
  - Observable: CLI marks a completed task and all its steps as incomplete via domain model. File is updated atomically. Existing behavior preserved.
  - Evidence: `uv run --with pytest pytest tests/plan-domain/ tests/plan-manager/ -v`
  - Steps:
    - [x] Write CLI integration test for mark_task_incomplete_cmd
    - [x] Add Task.mark_incomplete() mutation method with TDD
    - [x] Add Plan.mark_task_incomplete() delegation method with TDD
    - [x] Wire mark_task_incomplete_cmd to use with_error_handling + with_plan_file_update
    - [x] Remove mark_task_incomplete() from tasks.py
    - [x] Delete old test_mark_task_incomplete.py, update test_error_messages.py
    - [x] Prune duplicate acceptance tests

- [x] **Task 1.2: Migrate mark_step_complete and mark_step_incomplete to domain model**
  - TaskType: OUTCOME
  - Entrypoint: `uv run i2code plan mark-step-complete tests/fixtures/plan.md --thread 1 --task 1 --step 1 --rationale "done"`
  - Observable: CLI marks individual steps complete/incomplete via domain model. Both operations work through Task-level step mutation methods.
  - Evidence: `uv run --with pytest pytest tests/plan-domain/ tests/plan-manager/ -v`
  - Steps:
    - [x] Write CLI integration tests for mark_step_complete_cmd and mark_step_incomplete_cmd
    - [x] Add Task.mark_step_complete(step_number) mutation method with TDD
    - [x] Add Task.mark_step_incomplete(step_number) mutation method with TDD
    - [x] Add Plan.mark_step_complete() and Plan.mark_step_incomplete() delegation methods with TDD
    - [x] Wire both CLI handlers to use with_error_handling + with_plan_file_update
    - [x] Remove mark_step_complete() and mark_step_incomplete() from tasks.py
    - [x] Delete old test_mark_step_complete.py and test_mark_step_incomplete.py, update test_error_messages.py
    - [x] Prune duplicate acceptance tests

---

## Steel Thread 2: Task Structural Operations
Migrate insert, delete, replace, reorder, and move task operations. These require a Task factory method (`Task.create()`) to build new tasks from structured data, and Thread-level methods for structural manipulation. The domain model's `to_text()` handles renumbering, eliminating the need for explicit `fix_numbering()` calls.

- [x] **Task 2.1: Migrate delete_task to domain model**
  - TaskType: OUTCOME
  - Entrypoint: `uv run i2code plan delete-task tests/fixtures/plan.md --thread 1 --task 1 --rationale "removed"`
  - Observable: CLI removes a task from a thread via domain model. Remaining tasks are renumbered by to_text(). No Task factory needed for this operation.
  - Evidence: `uv run --with pytest pytest tests/plan-domain/ tests/plan-manager/ -v`
  - Steps:
    - [x] Write CLI integration test for delete_task_cmd
    - [x] Add Thread.delete_task(task_index) method with TDD
    - [x] Add Plan.delete_task(thread, task) delegation method with TDD
    - [x] Wire delete_task_cmd to use with_error_handling + with_plan_file_update
    - [x] Remove delete_task() from tasks.py
    - [x] Delete old test_delete_task.py, update test_error_messages.py
    - [x] Prune duplicate acceptance tests

- [x] **Task 2.2: Add Task.create() factory method**
  - TaskType: INFRA
  - Entrypoint: `uv run --with pytest pytest tests/plan-domain/test_task_create.py -v`
  - Observable: Task.create(title, task_type, entrypoint, observable, evidence, steps) returns a Task with correctly formatted markdown lines. Round-trips through to_lines() produce expected output.
  - Evidence: `uv run --with pytest pytest tests/plan-domain/ -v`
  - Steps:
    - [x] Write tests for Task.create() verifying title, metadata, steps, and to_lines() output
    - [x] Implement Task.create() class method that builds _lines from structured data

- [x] **Task 2.3: Migrate insert_task_before and insert_task_after to domain model**
  - TaskType: OUTCOME
  - Entrypoint: `uv run i2code plan insert-task-before tests/fixtures/plan.md --thread 1 --before 1 --title "New" --task-type INFRA --entrypoint "echo" --observable "works" --evidence "echo" --steps '["step"]' --rationale "added"`
  - Observable: CLI inserts tasks via domain model using Task.create() and Thread.insert_task(). Renumbering handled by to_text().
  - Evidence: `uv run --with pytest pytest tests/plan-domain/ tests/plan-manager/ -v`
  - Steps:
    - [x] Write CLI integration tests for insert_task_before_cmd and insert_task_after_cmd
    - [x] Add Thread.insert_task(index, task) method with TDD
    - [x] Add Plan.insert_task_before() and Plan.insert_task_after() delegation methods with TDD
    - [x] Wire both CLI handlers to use with_error_handling + with_plan_file_update
    - [x] Remove insert_task_before() and insert_task_after() from tasks.py
    - [x] Delete old test_insert_task.py, update test_error_messages.py
    - [x] Prune duplicate acceptance tests

- [x] **Task 2.4: Migrate replace_task to domain model**
  - TaskType: OUTCOME
  - Entrypoint: `uv run i2code plan replace-task tests/fixtures/plan.md --thread 1 --task 1 --title "Replaced" --task-type OUTCOME --entrypoint "echo" --observable "new" --evidence "echo" --steps '["step"]' --rationale "replaced"`
  - Observable: CLI replaces a task's content in place via domain model using Task.create() and Thread.replace_task().
  - Evidence: `uv run --with pytest pytest tests/plan-domain/ tests/plan-manager/ -v`
  - Steps:
    - [x] Write CLI integration test for replace_task_cmd
    - [x] Add Thread.replace_task(index, task) method with TDD
    - [x] Add Plan.replace_task() delegation method with TDD
    - [x] Wire replace_task_cmd to use with_error_handling + with_plan_file_update
    - [x] Remove replace_task() from tasks.py
    - [x] Delete old test_replace_task.py, update test_error_messages.py
    - [x] Prune duplicate acceptance tests

- [x] **Task 2.5: Migrate reorder_tasks to domain model**
  - TaskType: OUTCOME
  - Entrypoint: `uv run i2code plan reorder-tasks tests/fixtures/plan.md --thread 1 --order 2,1 --rationale "reordered"`
  - Observable: CLI reorders tasks within a thread via domain model. Renumbering handled by to_text().
  - Evidence: `uv run --with pytest pytest tests/plan-domain/ tests/plan-manager/ -v`
  - Steps:
    - [x] Write CLI integration test for reorder_tasks_cmd
    - [x] Add Thread.reorder_tasks(order) method with TDD
    - [x] Add Plan.reorder_tasks() delegation method with TDD
    - [x] Wire reorder_tasks_cmd to use with_error_handling + with_plan_file_update
    - [x] Remove reorder_tasks() from tasks.py
    - [x] Delete old test_reorder_tasks.py, update test_error_messages.py
    - [x] Prune duplicate acceptance tests

- [ ] **Task 2.6: Migrate move_task_before and move_task_after to domain model**
  - TaskType: OUTCOME
  - Entrypoint: `uv run i2code plan move-task-before tests/fixtures/plan.md --thread 1 --task 2 --before 1 --rationale "moved"`
  - Observable: CLI moves tasks within a thread via domain model. Implemented using Thread.reorder_tasks() internally.
  - Evidence: `uv run --with pytest pytest tests/plan-domain/ tests/plan-manager/ -v`
  - Steps:
    - [ ] Write CLI integration tests for move_task_before_cmd and move_task_after_cmd
    - [ ] Add Plan.move_task_before() and Plan.move_task_after() delegation methods with TDD
    - [ ] Wire both CLI handlers to use with_error_handling + with_plan_file_update
    - [ ] Remove move_task_before() and move_task_after() from tasks.py
    - [ ] Delete old test_move_task_before.py and test_move_task_after.py, update test_error_messages.py
    - [ ] Prune duplicate acceptance tests

- [ ] **Task 2.7: Delete tasks.py**
  - TaskType: INFRA
  - Entrypoint: `uv run --with pytest pytest tests/plan-domain/ tests/plan-manager/ -v`
  - Observable: tasks.py is empty of functions and deleted. All imports of tasks.py removed from task_cli.py. All tests pass.
  - Evidence: `uv run --with pytest pytest tests/plan-domain/ tests/plan-manager/ -v`
  - Steps:
    - [ ] Verify tasks.py has no remaining functions
    - [ ] Remove tasks.py import from task_cli.py
    - [ ] Delete tasks.py
    - [ ] Run all tests to confirm nothing breaks

---

## Steel Thread 3: Thread Structural Operations
Migrate insert, delete, replace, and reorder thread operations. These require a Thread factory method (`Thread.create()`) to build new threads from structured data, and Plan-level methods for structural manipulation.

- [ ] **Task 3.1: Migrate delete_thread to domain model**
  - TaskType: OUTCOME
  - Entrypoint: `uv run i2code plan delete-thread tests/fixtures/plan.md --thread 1 --rationale "removed"`
  - Observable: CLI removes a thread via domain model. Remaining threads renumbered by to_text(). No Thread factory needed for this operation.
  - Evidence: `uv run --with pytest pytest tests/plan-domain/ tests/plan-manager/ -v`
  - Steps:
    - [ ] Write CLI integration test for delete_thread_cmd
    - [ ] Add Plan.delete_thread(thread) method with TDD
    - [ ] Wire delete_thread_cmd to use with_error_handling + with_plan_file_update
    - [ ] Remove delete_thread() from threads.py
    - [ ] Delete old test_delete_thread.py, update test_error_messages.py
    - [ ] Prune duplicate acceptance tests

- [ ] **Task 3.2: Add Thread.create() factory method and migrate insert_thread_before/after**
  - TaskType: OUTCOME
  - Entrypoint: `uv run i2code plan insert-thread-before tests/fixtures/plan.md --before 1 --title "New" --introduction "Intro" --tasks '[{"title":"T","task_type":"INFRA","entrypoint":"echo","observable":"x","evidence":"echo","steps":["s"]}]' --rationale "added"`
  - Observable: Thread.create() builds a Thread from structured data using Task.create() for each task. CLI inserts threads via domain model.
  - Evidence: `uv run --with pytest pytest tests/plan-domain/ tests/plan-manager/ -v`
  - Steps:
    - [ ] Write tests for Thread.create() verifying header lines and task construction
    - [ ] Implement Thread.create() class method
    - [ ] Write CLI integration tests for insert_thread_before_cmd and insert_thread_after_cmd
    - [ ] Add Plan.insert_thread_before() and Plan.insert_thread_after() methods with TDD
    - [ ] Wire both CLI handlers to use with_error_handling + with_plan_file_update
    - [ ] Remove insert_thread_before() and insert_thread_after() from threads.py
    - [ ] Delete old test_insert_thread.py, update test_error_messages.py
    - [ ] Prune duplicate acceptance tests

- [ ] **Task 3.3: Migrate replace_thread to domain model**
  - TaskType: OUTCOME
  - Entrypoint: `uv run i2code plan replace-thread tests/fixtures/plan.md --thread 1 --title "Replaced" --introduction "New intro" --tasks '[{"title":"T","task_type":"INFRA","entrypoint":"echo","observable":"x","evidence":"echo","steps":["s"]}]' --rationale "replaced"`
  - Observable: CLI replaces a thread via domain model using Thread.create() and Plan.replace_thread().
  - Evidence: `uv run --with pytest pytest tests/plan-domain/ tests/plan-manager/ -v`
  - Steps:
    - [ ] Write CLI integration test for replace_thread_cmd
    - [ ] Add Plan.replace_thread() method with TDD
    - [ ] Wire replace_thread_cmd to use with_error_handling + with_plan_file_update
    - [ ] Remove replace_thread() from threads.py
    - [ ] Delete old test_replace_thread.py, update test_error_messages.py
    - [ ] Prune duplicate acceptance tests

- [ ] **Task 3.4: Migrate reorder_threads to domain model**
  - TaskType: OUTCOME
  - Entrypoint: `uv run i2code plan reorder-threads tests/fixtures/plan.md --order 2,1 --rationale "reordered"`
  - Observable: CLI reorders threads via domain model. Renumbering handled by to_text().
  - Evidence: `uv run --with pytest pytest tests/plan-domain/ tests/plan-manager/ -v`
  - Steps:
    - [ ] Write CLI integration test for reorder_threads_cmd
    - [ ] Add Plan.reorder_threads(order) method with TDD
    - [ ] Wire reorder_threads_cmd to use with_error_handling + with_plan_file_update
    - [ ] Remove reorder_threads() from threads.py
    - [ ] Delete old test_reorder_threads.py, update test_error_messages.py
    - [ ] Prune duplicate acceptance tests

- [ ] **Task 3.5: Delete threads.py**
  - TaskType: INFRA
  - Entrypoint: `uv run --with pytest pytest tests/plan-domain/ tests/plan-manager/ -v`
  - Observable: threads.py is empty of functions and deleted. All imports of threads.py removed from thread_cli.py. All tests pass.
  - Evidence: `uv run --with pytest pytest tests/plan-domain/ tests/plan-manager/ -v`
  - Steps:
    - [ ] Verify threads.py has no remaining functions
    - [ ] Remove threads.py import from thread_cli.py
    - [ ] Delete threads.py
    - [ ] Run all tests to confirm nothing breaks

---

## Steel Thread 4: Plan Read Operations and Final Cleanup
Migrate fix_numbering, list_threads, get_summary, and get_thread to use the domain model. Then delete the now-empty standalone modules and consolidate _helpers.py.

- [ ] **Task 4.1: Migrate fix_numbering to domain model**
  - TaskType: OUTCOME
  - Entrypoint: `uv run i2code plan fix-numbering tests/fixtures/plan.md`
  - Observable: CLI fix-numbering is implemented as a parse + to_text() round-trip via with_plan_file_update. The domain model's serialization handles renumbering inherently.
  - Evidence: `uv run --with pytest pytest tests/plan-domain/ tests/plan-manager/ -v`
  - Steps:
    - [ ] Write CLI integration test for fix_numbering_cmd
    - [ ] Wire fix_numbering_cmd to use with_plan_file_update (parse + to_text round-trip renumbers)
    - [ ] Remove fix_numbering() from plans.py
    - [ ] Update any remaining callers (should be none after threads 1-3)
    - [ ] Delete old test_fix_numbering.py
    - [ ] Prune duplicate acceptance tests

- [ ] **Task 4.2: Migrate list_threads to domain model**
  - TaskType: OUTCOME
  - Entrypoint: `uv run i2code plan list-threads tests/fixtures/plan.md`
  - Observable: CLI list-threads reads thread data from domain model properties (Thread.title, task counts). Uses with_plan_file for read-only access.
  - Evidence: `uv run --with pytest pytest tests/plan-domain/ tests/plan-manager/ -v`
  - Steps:
    - [ ] Write CLI integration test for list_threads_cmd
    - [ ] Add Thread.title property with TDD (parse from _header_lines[0])
    - [ ] Wire list_threads_cmd to use with_plan_file and iterate domain model
    - [ ] Remove list_threads() from plans.py
    - [ ] Delete old test_list_threads.py
    - [ ] Prune duplicate acceptance tests

- [ ] **Task 4.3: Migrate get_summary to domain model**
  - TaskType: OUTCOME
  - Entrypoint: `uv run i2code plan get-summary tests/fixtures/plan.md`
  - Observable: CLI get-summary reads plan metadata from domain model properties. Uses with_plan_file for read-only access.
  - Evidence: `uv run --with pytest pytest tests/plan-domain/ tests/plan-manager/ -v`
  - Steps:
    - [ ] Write CLI integration test for get_summary_cmd
    - [ ] Add Plan.name, Plan.idea_type, Plan.overview properties with TDD (parse from _preamble_lines)
    - [ ] Wire get_summary_cmd to use with_plan_file and read domain properties
    - [ ] Remove get_summary() from plans.py
    - [ ] Delete old test_get_summary.py
    - [ ] Prune duplicate acceptance tests

- [ ] **Task 4.4: Migrate get_thread to domain model**
  - TaskType: OUTCOME
  - Entrypoint: `uv run i2code plan get-thread tests/fixtures/plan.md --thread 1`
  - Observable: CLI get-thread reads thread content from domain model. Thread.title, Thread.introduction properties provide data. Task metadata comes from existing Task properties.
  - Evidence: `uv run --with pytest pytest tests/plan-domain/ tests/plan-manager/ -v`
  - Steps:
    - [ ] Write CLI integration test for get_thread_cmd
    - [ ] Add Thread.introduction property with TDD (parse from _header_lines)
    - [ ] Wire get_thread_cmd to use with_plan_file and with_error_handling
    - [ ] Remove get_thread() from plans.py
    - [ ] Delete old test_get_thread.py, update test_error_messages.py
    - [ ] Prune duplicate acceptance tests

- [ ] **Task 4.5: Delete plans.py, consolidate _helpers.py, final cleanup**
  - TaskType: INFRA
  - Entrypoint: `uv run --with pytest pytest tests/plan-domain/ tests/plan-manager/ -v`
  - Observable: plans.py deleted. append_change_history moved from _helpers.py into plan_file_io.py. _helpers.py deleted. No remaining imports of deleted modules. All tests pass.
  - Evidence: `uv run --with pytest pytest tests/plan-domain/ tests/plan-manager/ -v`
  - Steps:
    - [ ] Verify plans.py has no remaining functions
    - [ ] Delete plans.py and remove its imports from plan_cli.py
    - [ ] Move append_change_history into plan_file_io.py
    - [ ] Delete _helpers.py and update all imports
    - [ ] Run all tests to confirm nothing breaks

---

## Summary
This plan migrates 19 remaining operations across 4 threads: 3 task state mutations, 7 task structural operations, 5 thread structural operations, and 4 plan-level read operations. Each migration follows the established pattern from commits d6fcd97 and 26d3ec2. After completion, all plan logic lives in the domain model (plan_domain), all I/O in plan_file_io.py, and the standalone modules (tasks.py, threads.py, plans.py, _helpers.py) are deleted.

---

## Change History
### 2026-02-14 15:37 - mark-step-complete
CLI integration tests for mark_step_complete_cmd and mark_step_incomplete_cmd written and passing

### 2026-02-14 15:37 - mark-step-complete
Task.mark_step_complete(step_number) implemented with TDD

### 2026-02-14 15:38 - mark-step-complete
Task.mark_step_incomplete(step_number) implemented with TDD, extracted shared _validated_step_line_index helper

### 2026-02-14 15:40 - mark-step-complete
Plan.mark_step_complete() and Plan.mark_step_incomplete() delegation methods implemented with TDD

### 2026-02-14 15:40 - mark-step-complete
CLI handlers wired to use with_error_handling + with_plan_file_update

### 2026-02-14 15:41 - mark-step-complete
Removed mark_step_complete() and mark_step_incomplete() from tasks.py

### 2026-02-14 16:05 - mark-step-complete
Deleted old test_mark_step_complete.py and test_mark_step_incomplete.py; test_error_messages.py already uses domain model

### 2026-02-14 16:06 - mark-step-complete
Removed 4 duplicate mark_step error tests from test_error_messages.py (covered by plan-domain tests)

### 2026-02-14 16:06 - mark-task-complete
Migrated mark_step_complete and mark_step_incomplete to domain model; deleted old tests and pruned duplicates

### 2026-02-14 16:12 - mark-task-complete
Migrated delete_task to domain model with Thread.delete_task() and Plan.delete_task() methods

### 2026-02-14 16:22 - mark-task-complete
Migrated insert_task_before and insert_task_after to domain model

### 2026-02-14 16:29 - mark-task-complete
Migrated replace_task to domain model with Thread.replace_task() and Plan.replace_task()

### 2026-02-14 16:51 - mark-task-complete
Migrated reorder_tasks to domain model with TDD
