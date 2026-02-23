Now I have a thorough understanding of the codebase. Here is the plan:

---

# Plan: `i2code implement` creates wrong branch when all tasks are complete

## Idea Type

**C. Platform/infrastructure capability** — This is a bug fix in the `i2code` CLI tool, which is developer infrastructure.

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
| `idea-to-code:dockerfile-guidelines` | When creating or modifying Dockerfiles |
| `idea-to-code:file-organization` | When moving, renaming, or reorganizing files |
| `idea-to-code:debugging-ci-failures` | When investigating CI build failures |
| `idea-to-code:test-runner-java-gradle` | When running tests in Java/Gradle projects |

### TDD Requirements

- NEVER write production code (`src/main/java/**/*.java`) without first writing a failing test
- Before using Write on any `.java` file in `src/main/`, ask: "Do I have a failing test?" If not, write the test first
- When task direction changes mid-implementation, return to TDD PLANNING state and write a test first

### Verification Requirements

- Hard rule: NEVER git commit, git push, or open a PR unless you have successfully run the project's test command and it exits 0
- Hard rule: If running tests is blocked for any reason (including permissions), ALWAYS STOP immediately. Print the failing command, the exact error output, and the permission/path required
- Before committing, ALWAYS print a Verification section containing the exact test command (NOT an ad-hoc command - it must be a proper test command such as `./test-scripts/*.sh`, `./scripts/test.sh`, or `./gradlew build`/`./gradlew check`), its exit code, and the last 20 lines of output

## Overview

This plan fixes a bug where `i2code implement` creates a wrong branch when all tasks are complete. The fix adds two guards: one in `_worktree_mode()` (the essential safety net) and one in `execute()` (the earlier, mode-independent check). All tasks use TDD.

### Key files

- `src/i2code/implement/implement_command.py` — `_worktree_mode()` and `execute()` (fix locations)
- `tests/implement/test_implement_command.py` — existing tests (add new tests here)
- `tests/implement/fake_idea_project.py` — `FakeIdeaProject` (already returns `None` from `get_next_task()`)

### Test runner

- Unit tests: `uv run python3 -m pytest tests/implement/test_implement_command.py -v -m unit`
- All tests: `./test-scripts/test-end-to-end.sh`

## Steel Thread 1: Guard `_worktree_mode()` when all tasks are complete

This thread fixes the essential bug: `_worktree_mode()` must exit with an error when `get_next_task()` returns `None`, before creating any branches or modifying the worktree.

- [ ] **Task 1.1: Integration test: implement exits with error when all tasks are complete**
  - TaskType: OUTCOME
  - Entrypoint: `uv run python3 -m pytest tests/implement/test_all_tasks_complete_integration.py -v -m integration`
  - Observable: Running i2code implement on an idea where all plan tasks are marked complete exits with a non-zero status, stderr contains "all tasks", and no new branches, worktrees, or Claude invocations occur.
  - Evidence: `Integration test creates a test git repo, commits idea files with all tasks marked [x] complete, creates a mock Claude script that writes a sentinel file when invoked, runs run_script(idea_dir, cwd=tmpdir, mock_claude=script_path), and asserts: (a) non-zero returncode, (b) stderr contains "all tasks", (c) no idea/* branches created, (d) no worktree directory created, (e) mock Claude script was never invoked (sentinel file absent).`
  - Steps:
    - [ ] Add a new integration test file tests/implement/test_all_tasks_complete_integration.py with a test class TestAllTasksCompleteExitsWithError marked @pytest.mark.integration. The test uses the test_git_repo_with_commit fixture, creates a valid idea directory with all plan tasks marked [x] complete (using write_plan_file with completed=True), creates a mock Claude script that writes a sentinel file when invoked, runs run_script(idea_dir, cwd=tmpdir, mock_claude=script_path), and asserts: (a) non-zero returncode, (b) stderr contains "all tasks", (c) no idea/* branches created beyond master, (d) no worktree directory created, (e) sentinel file does not exist (Claude was never invoked). Verify the test fails.
- [ ] **Task 1.2: `_worktree_mode()` exits with error when all tasks are complete**
  - TaskType: OUTCOME
  - Entrypoint: `uv run python3 -m pytest tests/implement/test_implement_command.py -v -m unit`
  - Observable: When `get_next_task()` returns `None`, `_worktree_mode()` prints an error message to stderr containing "all tasks" and exits with `sys.exit(1)`. It does NOT call `ensure_integration_branch`, `ensure_slice_branch`, `ensure_worktree`, or `checkout` on the git repository.
  - Evidence: Unit test invokes `_worktree_mode()` via `execute()` with `FakeIdeaProject` (which returns `None` from `get_next_task()` by default), asserts `SystemExit` with code 1, asserts stderr contains "all tasks", and asserts that `git_repo.ensure_integration_branch`, `git_repo.ensure_slice_branch`, `git_repo.ensure_worktree`, and `git_repo.checkout` were NOT called.
  - Steps:
    - [ ] Add a new test class `TestWorktreeModeAllTasksComplete` in `tests/implement/test_implement_command.py` with a test that creates an `ImplementCommand` using `FakeIdeaProject` (which returns `None` from `get_next_task()` by default), calls `execute()`, and asserts: (a) `SystemExit` with code 1, (b) stderr contains "all tasks", (c) `git_repo.ensure_integration_branch` was not called, (d) `git_repo.ensure_slice_branch` was not called, (e) `git_repo.ensure_worktree` was not called, (f) `git_repo.checkout` was not called. Verify the test fails.
    - [ ] In `src/i2code/implement/implement_command.py`, add a guard at the top of `_worktree_mode()` that calls `self.project.get_next_task()`, and if it returns `None`, prints an error message to stderr and calls `sys.exit(1)` — before the existing `WorkflowState.load()` call. Verify the test passes.

## Steel Thread 2: Earlier check in `execute()` before mode dispatch

This thread adds a mode-independent guard in `execute()` that catches the all-tasks-complete condition before dispatching to any mode.

- [ ] **Task 2.1: `execute()` exits with error when all tasks are complete before dispatching to any mode**
  - TaskType: OUTCOME
  - Entrypoint: `uv run python3 -m pytest tests/implement/test_implement_command.py -v -m unit`
  - Observable: When `get_next_task()` returns `None`, `execute()` prints an error message to stderr indicating all tasks are complete and exits with `sys.exit(1)` — without dispatching to `_worktree_mode()`, `_trunk_mode()`, or `_isolate_mode()`.
  - Evidence: Unit tests for each mode (worktree, trunk, isolate) configure `FakeIdeaProject` to return `None` from `get_next_task()`, call `execute()`, assert `SystemExit` with code 1, assert stderr contains "all tasks", and assert that `_worktree_mode()` / `_trunk_mode()` / `_isolate_mode()` were NOT called.
  - Steps:
    - [ ] Add a new test class `TestExecuteAllTasksComplete` in `tests/implement/test_implement_command.py` with three tests: (a) worktree mode — `FakeIdeaProject` returns `None`, `execute()` raises `SystemExit(1)`, stderr contains "all tasks", `_worktree_mode` not called; (b) trunk mode — same assertions with `trunk=True`; (c) isolate mode — same assertions with `isolate=True`. Verify all three tests fail.
    - [ ] In `src/i2code/implement/implement_command.py`, add a guard in `execute()` after `validate_idea_files_committed` (and the `dry_run` check) but before the mode dispatch `if/elif/else` block. The guard calls `self.project.get_next_task()` and, if it returns `None`, prints an error to stderr and calls `sys.exit(1)`. Verify the tests pass.

- [ ] **Task 2.2: `execute()` proceeds normally when tasks remain (regression guard)**
  - TaskType: OUTCOME
  - Entrypoint: `uv run python3 -m pytest tests/implement/test_implement_command.py -v -m unit`
  - Observable: When `get_next_task()` returns a valid `NumberedTask`, `execute()` dispatches to the appropriate mode method without exiting early.
  - Evidence: All existing dispatch tests (`TestImplementCommandTrunkDispatch`, `TestImplementCommandIsolateDispatch`, `TestImplementCommandWorktreeDispatch`) continue to pass. These tests use `FakeIdeaProject` which currently returns `None` — they must be updated to configure a next task so they exercise the normal dispatch path through the new guard.
  - Steps:
    - [ ] Update `_make_command()` in `tests/implement/test_implement_command.py` to configure `FakeIdeaProject` with a default `NumberedTask` (so `get_next_task()` returns a task instead of `None`). This ensures all existing dispatch tests pass through the new `execute()` guard.
    - [ ] Verify all existing tests still pass: `TestImplementCommandDryRun`, `TestImplementCommandTrunkDispatch`, `TestImplementCommandIsolateDispatch`, `TestImplementCommandWorktreeDispatch`, `TestImplementCommandValidation`, `TestImplementCommandTrunkMode`, `TestImplementCommandIsolateMode`, `TestImplementCommandWorktreeMode`.

---

## Change History
### 2026-02-24 07:54 - insert-task-before
Outside-in TDD: start with an integration test that exercises the real command flow before drilling down to unit tests in _worktree_mode()

### 2026-02-24 07:57 - delete-task
Existing test test_worktree_mode_delegates_to_mode_factory already covers the regression guard. The set_next_task() addition is handled in Task 2.2.
