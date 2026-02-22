Now I have a comprehensive understanding of the entire codebase. Let me generate the plan.

---

# Implementation Plan: i2code implement — Handle Failed Commit Recovery

## Idea Type

**C. Platform/infrastructure capability** — This feature adds internal recovery logic to the `i2code implement` workflow. It doesn't introduce user-facing CLI flags or endpoints; it improves the robustness of an existing internal tool.

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

- NEVER write production code (`src/i2code/**/*.py`) without first writing a failing test
- Before using Write on any `.py` file in `src/i2code/`, ask: "Do I have a failing test?" If not, write the test first
- When task direction changes mid-implementation, return to TDD PLANNING state and write a test first

### Verification Requirements

- Hard rule: NEVER git commit, git push, or open a PR unless you have successfully run the project's test command and it exits 0
- Hard rule: If running tests is blocked for any reason (including permissions), ALWAYS STOP immediately. Print the failing command, the exact error output, and the permission/path required
- Before committing, ALWAYS print a Verification section containing the exact test command (NOT an ad-hoc command - it must be a proper test command such as `./test-scripts/*.sh`, `./test-scripts/test-end-to-end.sh`, or `uv run --with pytest pytest tests/`), its exit code, and the last 20 lines of output

## Overview

This plan adds a pre-loop commit recovery mechanism to `i2code implement`. When a previous run fails during `git commit`, it leaves uncommitted changes in the working tree. On rerun, the recovery detects this state, classifies the affected task as fully or partially complete, and either commits the recovered changes (fully complete) or skips recovery (partially complete, letting the main loop resume naturally).

The implementation follows the existing architecture:
- A new `CommitRecovery` class (similar to `GithubActionsBuildFixer`) encapsulates detection, classification, Claude invocation, and retry logic
- A new `commit_recovery.j2` Jinja2 template (similar to `ci_fix.j2`) provides the Claude prompt
- A new `build_recovery_command()` method on `CommandBuilder` builds the Claude command
- `TrunkMode` and `WorktreeMode` call `CommitRecovery` at the start of their task loops
- `GitRepository` gains a `diff_file_against_head()` method for detection

Tests use the existing fake infrastructure (`FakeGitRepository`, `FakeClaudeRunner`, `FakeIdeaProject`) and the conftest helpers (`write_plan_file`, `mark_task_complete`, `advance_head`, `combined`).

Test command: `uv run --with pytest --with pytest-mock pytest tests/implement/ -v -m unit`
Full test suite: `./test-scripts/test-end-to-end.sh`

---

## Steel Thread 1: Detect Uncommitted Completed Task and Commit Recovery

This steel thread implements the primary end-to-end flow: detecting that a fully completed task has uncommitted changes, invoking Claude to commit them, and then proceeding with the normal task loop. It covers Scenario 1 (full task recovery) and Scenario 4 (no recovery needed) from the spec.

All steps should be implemented using TDD.

- [x] **Task 1.1: Detect uncommitted plan-file changes showing a fully completed task**
  - TaskType: OUTCOME
  - Entrypoint: `uv run --with pytest --with pytest-mock pytest tests/implement/test_commit_recovery.py -v -m unit`
  - Observable: `CommitRecovery.needs_recovery()` returns `True` when git diff shows a task changed from `[ ]` to `[x]` in the working tree vs HEAD; returns `False` when no such diff exists
  - Evidence: Unit tests create a `FakeGitRepository` with controlled `diff_file_against_head()` return values, and assert `needs_recovery()` returns the correct boolean
  - Steps:
    - [x] Add `diff_file_against_head(file_path)` method to `GitRepository` (`src/i2code/implement/git_repository.py`) that runs `git diff HEAD -- <file_path>` and returns the diff output as a string (empty string if no diff). Add the same method to `FakeGitRepository` with a `set_diff_output()` setter for test control.
    - [x] Create `src/i2code/implement/commit_recovery.py` with a `CommitRecovery` class. Constructor takes `git_repo`, `project` (IdeaProject), and `claude_runner`. Add a `needs_recovery()` method that: (1) gets the plan file path from `project.plan_file`, (2) calls `git_repo.diff_file_against_head(plan_file)`, (3) if diff is empty, returns `False`, (4) parses the working-tree plan file using the plan domain parser, (5) parses the HEAD version by reading the committed content via a new `show_file_at_head()` method on `GitRepository`, (6) compares tasks: if any task header changed from `[ ]` (HEAD) to `[x]` (working tree), returns `True`, otherwise returns `False`.
    - [x] Add `show_file_at_head(file_path)` to `GitRepository` that runs `git show HEAD:<relative_path>` and returns the file content. Add the same to `FakeGitRepository` with a `set_file_at_head()` setter.
    - [x] Write unit tests in `tests/implement/test_commit_recovery.py` for: (a) no diff → returns `False`, (b) diff shows fully completed task → returns `True`, (c) diff shows only step changes (partial) → returns `False`.

- [ ] **Task 1.2: Invoke Claude to commit recovered changes in TrunkMode**
  - TaskType: OUTCOME
  - Entrypoint: `uv run --with pytest --with pytest-mock pytest tests/implement/test_trunk_mode.py tests/implement/test_commit_recovery.py -v -m unit`
  - Observable: When `TrunkMode.execute()` is called and `CommitRecovery.needs_recovery()` returns `True`, Claude is invoked with a recovery prompt before the main task loop. After successful recovery (HEAD advances), the main loop continues with the next incomplete task.
  - Evidence: Unit tests configure `FakeGitRepository` and `FakeClaudeRunner` to simulate recovery scenario. Assert: (1) Claude is called with recovery prompt first, (2) HEAD advances during recovery, (3) main loop starts after recovery and processes the next task.
  - Steps:
    - [ ] Create the `commit_recovery.j2` Jinja2 template in `src/i2code/implement/templates/`. The template instructs Claude to: stage all uncommitted changes, generate an appropriate commit message for the recovered task, and commit. Include the plan file path and a summary of the uncommitted changes.
    - [ ] Add `build_recovery_command(plan_file, diff_summary, interactive)` to `CommandBuilder` that renders `commit_recovery.j2` and applies `_with_mode()`.
    - [ ] Add a `recover()` method to `CommitRecovery` that: (1) prints "Detected uncommitted changes from a previous run, attempting to commit...", (2) builds the recovery command via `CommandBuilder`, (3) invokes Claude using `claude_runner.run_interactive()` or `run_with_capture()`, (4) checks `check_claude_success()`, (5) returns `True` on success, `False` on failure.
    - [ ] Add a `check_and_recover()` method to `CommitRecovery` that calls `needs_recovery()` and, if `True`, calls `recover()`.
    - [ ] Modify `TrunkMode.__init__()` to accept an optional `commit_recovery` parameter (defaulting to `None`). At the top of `execute()`, before the `while True` loop, call `commit_recovery.check_and_recover()` if provided.
    - [ ] Update `ModeFactory.make_trunk_mode()` to create a `CommitRecovery` instance and pass it to `TrunkMode`.
    - [ ] Write unit tests for `CommitRecovery.recover()`: (a) Claude succeeds (HEAD advances, exit 0) → returns `True`, prints success message, (b) Claude fails → returns `False`.
    - [ ] Write unit tests for `TrunkMode` with recovery: (a) recovery needed and succeeds → main loop continues with next task, (b) no recovery needed → main loop starts normally (existing tests should still pass).

- [ ] **Task 1.3: Retry on recovery failure, then exit with error**
  - TaskType: OUTCOME
  - Entrypoint: `uv run --with pytest --with pytest-mock pytest tests/implement/test_commit_recovery.py -v -m unit`
  - Observable: When the first recovery attempt fails (Claude exits non-zero or HEAD unchanged), `CommitRecovery` retries once. If the retry also fails, it prints "Error: Could not commit recovered changes after 2 attempts. Please commit manually and rerun." and calls `sys.exit(1)`.
  - Evidence: Unit tests configure `FakeClaudeRunner` to fail twice, assert: (1) Claude is called twice, (2) error message is printed, (3) `sys.exit(1)` is raised.
  - Steps:
    - [ ] Modify `CommitRecovery.check_and_recover()` to implement retry logic: attempt recovery up to 2 times. On first failure, print "Recovery attempt 1 failed, retrying..." and try again. On second failure, print the error message and call `sys.exit(1)`. On success at any attempt, print "Recovery commit successful." and return.
    - [ ] Write unit tests for: (a) first attempt fails, second succeeds → prints retry message, then success, (b) both attempts fail → prints error and exits with code 1, (c) first attempt succeeds → no retry.

- [ ] **Task 1.4: Invoke Claude to commit recovered changes in WorktreeMode**
  - TaskType: OUTCOME
  - Entrypoint: `uv run --with pytest --with pytest-mock pytest tests/implement/test_worktree_mode.py -v -m unit`
  - Observable: When `WorktreeMode.execute()` is called and `CommitRecovery.needs_recovery()` returns `True`, recovery is attempted before the main task loop (before `check_and_fix_ci` and `process_feedback`). After successful recovery, the main loop continues normally.
  - Evidence: Unit tests configure `FakeGitRepository` and `FakeClaudeRunner` to simulate recovery in worktree mode. Assert: (1) recovery Claude call happens before any task-loop Claude call, (2) main loop starts after recovery.
  - Steps:
    - [ ] Modify `WorktreeMode.__init__()` to accept an optional `commit_recovery` parameter (defaulting to `None`). At the top of `execute()`, before the `while True` loop, call `commit_recovery.check_and_recover()` if provided.
    - [ ] Update `ModeFactory.make_worktree_mode()` to create a `CommitRecovery` instance and pass it to `WorktreeMode`.
    - [ ] Write unit tests for `WorktreeMode` with recovery: (a) recovery needed and succeeds → main loop continues, (b) no recovery needed → main loop starts normally (existing tests should still pass).

## Steel Thread 2: Skip Recovery for Partially Completed Tasks

This steel thread implements Scenario 2: when only steps are marked `[x]` but the task header remains `[ ]`, recovery is skipped and the main loop resumes the task naturally.

All steps should be implemented using TDD.

- [ ] **Task 2.1: Partial task completion skips recovery**
  - TaskType: OUTCOME
  - Entrypoint: `uv run --with pytest --with pytest-mock pytest tests/implement/test_commit_recovery.py -v -m unit`
  - Observable: When the plan file diff shows step checkboxes changed from `[ ]` to `[x]` but the task header remains `[ ]`, `needs_recovery()` returns `False` and no recovery commit is attempted
  - Evidence: Unit tests provide a plan file where steps are marked complete but the task header is still `[ ]`. Assert `needs_recovery()` returns `False`. A separate integration-style test verifies that `TrunkMode.execute()` proceeds directly to the main loop without a recovery call.
  - Steps:
    - [ ] Verify and strengthen the existing `needs_recovery()` logic: the comparison must check task *headers* only (not steps). If only steps changed from `[ ]` to `[x]` but the task header remains `[ ]`, return `False`.
    - [ ] Write unit tests for: (a) task header `[ ]` in both HEAD and working tree, but steps changed → returns `False`, (b) task header changed from `[ ]` to `[x]` → returns `True` (regression test for Task 1.1), (c) no changes at all → returns `False`.

---

## Change History

### 2026-02-22: Initial plan

Created implementation plan based on the specification. Four tasks in Steel Thread 1 cover detection, TrunkMode integration, retry logic, and WorktreeMode integration. Steel Thread 2 covers the partial-task skip scenario. All tasks follow TDD using the existing fake infrastructure.
