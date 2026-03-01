# Specification: `i2code implement` creates wrong branch when all tasks are complete

## Purpose and background

`i2code implement` is a CLI command that drives the implement workflow — creating Git branches, worktrees, and PRs to execute tasks from a plan file. The command derives the slice branch name from the next incomplete task.

When all tasks in a plan are already complete, `get_next_task()` returns `None`. The current code falls back to the literal string `"implementation"`, which produces a branch name like `idea/<name>/01-implementation`. This branch doesn't match the existing slice branch, so `ensure_slice_branch` creates a new branch from the integration branch (pointing at the initial commit), and `checkout` switches the worktree to it — effectively resetting the worktree to a blank state.

No work is lost (the original branch still exists), but the worktree now points to a wrong, empty branch.

## Target users

Developers using `i2code implement` to execute plan-driven development workflows.

## Problem statement

Running `i2code implement` on an idea where all tasks are complete silently creates a new empty branch and checks it out, resetting the worktree. The user sees no error message and must manually recover by checking out the correct branch.

## Goals

1. Prevent `_worktree_mode()` from creating branches or modifying the worktree when no tasks remain.
2. Provide a clear error message telling the user that all tasks are complete.
3. Exit cleanly (non-zero) so scripts and CI can detect the condition.

## In scope

- Guard in `_worktree_mode()` that checks `get_next_task()` before any branch or worktree operations (essential fix).
- Earlier check in `ImplementCommand.execute()` that catches the all-tasks-complete condition before dispatching to any mode (implemented after the bug fix).
- Error message and non-zero exit when no incomplete tasks exist.
- Unit tests reproducing the bug and verifying both guards.

## Out of scope

- Changes to `_trunk_mode()` or `_isolate_mode()` (they have different task-selection flows).
- Changes to `ensure_slice_branch()` or `ensure_integration_branch()` (the root cause is in the caller, not these methods).

## High-level functional requirements

### FR-1: Early exit when no tasks remain

`_worktree_mode()` must call `get_next_task()` before any calls to `ensure_integration_branch`, `ensure_slice_branch`, `ensure_worktree`, or `checkout`. If `get_next_task()` returns `None`, the method must:

1. Print an error message to stderr indicating all tasks are complete.
2. Exit with a non-zero status code (via `sys.exit(1)`).

### FR-2: No side effects on early exit

When `get_next_task()` returns `None`, `_worktree_mode()` must not:

- Create or modify any Git branches.
- Create or modify any worktrees.
- Change the checked-out branch.
- Create or modify any PRs.

### FR-3: Earlier check in `execute()`

After the `_worktree_mode()` guard is in place, add a check in `ImplementCommand.execute()` that calls `get_next_task()` and exits with an error message if no tasks remain — before dispatching to any mode. This catches the condition earlier and applies regardless of mode.

Note: this check may produce false positives when the main repo is not up to date (PR not merged, changes not pulled), so the `_worktree_mode()` guard (FR-1) remains the essential safety net.

## Security requirements

Not applicable — this is a local CLI bug fix with no network endpoints, authentication, or authorization changes.

## Non-functional requirements

- **UX**: The error message must clearly state that all tasks are complete and suggest what the user can do (e.g., check the plan file).
- **Reliability**: The guard must execute before any Git state mutations to guarantee no partial side effects.
- **Backward compatibility**: No changes to command-line interface, flags, or exit codes for the normal (tasks-exist) path.

## Success metrics

- Running `i2code implement` on a fully-completed idea exits with an error message and non-zero status.
- The worktree, branches, and checked-out branch remain unchanged after the command exits.
- All existing tests continue to pass.

## User stories

### US-1: Developer runs implement on a completed idea

**As a** developer using `i2code implement`,
**when** I run the command on an idea where all plan tasks are complete,
**I want** to see a clear error message and have the command exit without modifying my worktree,
**so that** I don't accidentally end up on a blank branch and need to manually recover.

## Scenarios

### Scenario 1 (primary end-to-end): Worktree mode with all tasks complete

**Given** an idea project where `get_next_task()` returns `None` (all tasks complete),
**when** `_worktree_mode()` is invoked,
**then** it prints an error message to stderr containing "all tasks" (or equivalent),
**and** exits with a non-zero status,
**and** does not call `ensure_integration_branch`, `ensure_slice_branch`, `ensure_worktree`, or `checkout` on the git repository.

### Scenario 2: `execute()` rejects all-tasks-complete before mode dispatch

**Given** an idea project where `get_next_task()` returns `None` (all tasks complete),
**when** `execute()` is called (in any mode: worktree, trunk, or isolate),
**then** it prints an error message to stderr indicating all tasks are complete,
**and** exits with a non-zero status,
**and** does not dispatch to `_worktree_mode()`, `_trunk_mode()`, or `_isolate_mode()`.

### Scenario 3: Normal path with tasks remaining (regression guard)

**Given** an idea project where `get_next_task()` returns a valid `NumberedTask`,
**when** `execute()` and `_worktree_mode()` are invoked,
**then** they proceed normally — creating branches, setting up the worktree, and delegating to `make_worktree_mode().execute()`.

## Key files

- `src/i2code/implement/implement_command.py:82-112` — `_worktree_mode()` (fix location)
- `src/i2code/implement/git_repository.py:112-126` — `ensure_slice_branch()` (context)
- `src/i2code/implement/idea_project.py:88-90` — `get_next_task()` (context)
- `tests/implement/test_implement_command.py` — existing tests (add new tests here)
- `tests/implement/fake_idea_project.py:62-63` — `FakeIdeaProject.get_next_task()` already returns `None` by default (useful for test setup)
