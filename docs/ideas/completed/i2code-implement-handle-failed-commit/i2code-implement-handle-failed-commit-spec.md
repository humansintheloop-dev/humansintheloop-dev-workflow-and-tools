# Specification: i2code implement — Handle Failed Commit Recovery

## Purpose and Background

`i2code implement` orchestrates plan-driven development by running Claude in a loop: for each task, Claude implements the code, marks the task complete in the plan file (`[ ]` → `[x]`), and commits all changes. The commit is the final step — if it fails (e.g., due to a permissions issue), `i2code implement` exits with an error, leaving the repository with uncommitted work.

On rerun, `get_next_task()` reads the plan file from disk (not from Git), sees the task as `[x]`, skips it, and advances to the next task. This causes two tasks' changes to be committed together, violating the one-task-per-commit principle.

This feature adds a pre-loop recovery step that detects uncommitted plan-file changes and commits them before entering the main task loop.

## Target Users

- Developers using `i2code implement` in TrunkMode or WorktreeMode.

## Problem Statement

When a commit fails during task execution, the repository is left in an inconsistent state:

1. The plan file on disk has uncommitted changes marking a task (or steps within a task) as done.
2. Implementation code for that task is also uncommitted.
3. On rerun, the task loop skips the already-marked task and proceeds to the next one.
4. Both tasks' changes are eventually committed together, breaking atomic task commits.

## Goals

1. Detect uncommitted plan-file changes that indicate a previously failed commit.
2. Recover fully completed tasks by invoking Claude to commit all uncommitted changes before the main task loop begins.
3. For partially completed tasks (some steps done, task header still `[ ]`), skip recovery and let the main loop resume the task naturally.
4. Maintain the existing architecture where Claude owns all git commit operations.

## In-Scope

- A `CommitRecovery` class encapsulating detection, Claude invocation, and retry logic. Called from TrunkMode (start of task loop) and WorktreeMode (after worktree setup, before task loop).
- Detection via `git diff HEAD` on the plan file.
- Using plan domain logic to determine whether the affected task is fully or partially complete.
- Invoking Claude to stage, generate a commit message, and commit all uncommitted changes.
- One retry on recovery failure, then exit with error.
- TrunkMode and WorktreeMode.

## Out-of-Scope

- IsolateMode (delegates to a VM; local repo state is not relevant).
- Recovering from other types of failures (e.g., network errors, CI failures — already handled by `GithubActionsBuildFixer`).
- Changing how Claude commits during normal task execution.
- Adding new CLI flags.

## Functional Requirements

### FR-1: Detect Uncommitted Plan-File Changes

Before entering the main task loop, check for uncommitted changes to the plan file using `git diff HEAD`.

- Compare the working-tree plan file against the last committed version.
- Use the plan domain parser (`src/i2code/plan_domain/parser.py`) to parse both versions.
- Use `Task.is_completed` and `Task.steps` to determine if any task or step changed from incomplete to complete.
- If no such changes are found, proceed to the main loop without action.

### FR-2: Classify the Recovery Scenario

Using plan domain logic, determine the state of the affected task:

- **Fully complete:** Task header is `[x]` in the working tree but `[ ]` in HEAD. → Trigger recovery commit.
- **Partially complete:** One or more steps changed to `[x]`, but the task header remains `[ ]`. → Skip recovery. The main loop's `get_next_task()` will return this task and Claude resumes it with the uncommitted changes still in the working tree.

### FR-3: Invoke Claude to Commit Recovered Changes

When uncommitted plan-file changes are detected:

1. Print an informational message (e.g., "Detected uncommitted changes from a previous run, attempting to commit...").
2. Build a recovery command via `CommandBuilder` using a new Jinja2 template (`commit_recovery.j2`).
3. Invoke Claude non-interactively using `ClaudeRunner.run_with_capture()`.
4. Claude stages all uncommitted changes, generates an appropriate commit message, and commits.
5. Verify success using `check_claude_success()` (exit code 0 and HEAD advanced).

### FR-4: Retry on Recovery Failure

If the recovery commit fails (Claude exits non-zero or HEAD does not advance):

1. Print a message indicating the first attempt failed.
2. Retry the recovery once (same invocation).
3. If the retry also fails, print a clear error message explaining the situation and advising the user to commit manually. Exit with `sys.exit(1)`.

### FR-5: Continue to Main Loop After Successful Recovery

After a successful recovery commit, proceed to the mode dispatch (TrunkMode or WorktreeMode) as normal. The main loop's `get_next_task()` will handle selecting the correct next task based on the plan file state.

## Security Requirements

- **Who can perform this operation:** The same user running `i2code implement`. No new roles or permissions are introduced.
- **Authorization:** Uses the same Claude permissions already configured for task execution (`REQUIRED_PERMISSIONS` in `git_setup.py`).
- **Constraints:** The recovery commit operates only on the local repository. No remote operations (push, PR creation) occur during recovery.

## Non-Functional Requirements

### Reliability

- The recovery must be idempotent: running `i2code implement` multiple times after a failed commit should produce the same result as running it once.
- If recovery fails after retry, the repository state must be unchanged (no partial commits).

### User Experience

- Print clear, informational messages at each stage: detection, attempt, success, failure.
- On failure, the error message must explain what the user should do (commit manually).

### Performance

- The recovery adds one `git diff` check and (at most) two Claude invocations before the main loop. This is acceptable given the existing per-task Claude invocation cost.

### Maintainability

- Follow the existing `CommandBuilder` + Jinja2 template pattern for the recovery prompt.
- Follow the existing `GithubActionsBuildFixer` pattern for retry logic.
- Encapsulate all recovery logic in a `CommitRecovery` class called from TrunkMode and WorktreeMode. Recovery cannot live before mode dispatch because WorktreeMode's uncommitted changes are in the worktree directory, which is set up inside `_worktree_mode()`.

## Success Metrics

1. After a failed commit, rerunning `i2code implement` produces a separate commit for the recovered task's changes.
2. The recovered commit has a meaningful, Claude-generated commit message.
3. The main loop resumes correctly with the next task after recovery.
4. Partially complete tasks (header still `[ ]`) are not committed — the main loop resumes them naturally.

## Epics and User Stories

### Epic: Failed Commit Recovery

**US-1: Recover from a fully completed but uncommitted task**
As a developer, when I rerun `i2code implement` after a failed commit where the task was fully completed, I want the tool to automatically commit the previous task's changes so that each task has its own commit.

**US-2: Resume a partially completed task without committing incomplete work**
As a developer, when I rerun `i2code implement` after an interruption where some steps were completed but not the whole task, I want the tool to skip recovery and resume the task from where it left off, keeping the uncommitted changes in the working tree.

**US-3: Handle recovery failure gracefully**
As a developer, when the recovery commit itself fails, I want a clear error message telling me what happened and what to do, rather than the tool silently proceeding or crashing.

**US-4: Transparent recovery**
As a developer, I want to see informational messages during recovery so I understand what the tool is doing and why.

## User-Facing Scenarios

### Scenario 1: Full Task Recovery (Primary End-to-End Scenario)

**Precondition:** A previous `i2code implement` run completed task 1.3 (all steps and task header marked `[x]`, implementation code written) but the `git commit` failed. The repository has uncommitted changes.

**Flow:**
1. User runs `i2code implement`.
2. `i2code implement` detects uncommitted plan-file changes via `git diff HEAD`.
3. It parses both versions and determines task 1.3 is fully complete but uncommitted.
4. It prints: "Detected uncommitted changes from a previous run, attempting to commit..."
5. It invokes Claude to commit all uncommitted changes.
6. Claude stages, generates a commit message, and commits successfully.
7. It prints: "Recovery commit successful."
8. The main loop starts. `get_next_task()` returns task 1.4.
9. Normal task execution continues.

**Postcondition:** Task 1.3's changes are in their own commit. Task 1.4 starts cleanly.

### Scenario 2: Partial Task — Skip Recovery and Resume

**Precondition:** A previous run was interrupted while working on task 2.1. Steps 1 and 2 are marked `[x]`, but the task header is still `[ ]`. There is uncommitted implementation code for those steps.

**Flow:**
1. User runs `i2code implement`.
2. `i2code implement` checks for uncommitted plan-file changes.
3. It parses both versions and determines task 2.1 has partial progress (steps completed, task header still `[ ]`).
4. Recovery is skipped — no commit is made.
5. The main loop starts. `get_next_task()` returns task 2.1 (header still `[ ]`).
6. Claude resumes task 2.1 with the uncommitted changes already in the working tree, continuing from step 3.

**Postcondition:** No recovery commit. The task resumes naturally and Claude completes it with a single commit covering all the work.

### Scenario 3: Recovery Failure

**Precondition:** Same as Scenario 1, but Claude cannot commit (e.g., persistent permissions issue).

**Flow:**
1. User runs `i2code implement`.
2. Detection finds uncommitted completed task.
3. First recovery attempt fails (Claude exits non-zero or HEAD unchanged).
4. It prints: "Recovery attempt 1 failed, retrying..."
5. Second attempt also fails.
6. It prints: "Error: Could not commit recovered changes after 2 attempts. Please commit manually and rerun."
7. `i2code implement` exits with code 1.

**Postcondition:** Repository state is unchanged. User is informed of what to do.

### Scenario 4: No Recovery Needed

**Precondition:** The repository has no uncommitted plan-file changes (clean state or changes unrelated to task completion).

**Flow:**
1. User runs `i2code implement`.
2. `git diff HEAD` on the plan file shows no checkbox changes.
3. Recovery is skipped silently.
4. Main loop starts normally.

**Postcondition:** No overhead. Normal execution proceeds.

## Change History

### 2026-02-22: Only recover fully complete tasks

Changed partial-task handling: do not commit incomplete work. When only steps are marked `[x]` but the task header is still `[ ]`, skip recovery entirely and let the main loop resume the task naturally. Claude will complete the remaining steps and commit everything together. This simplifies the recovery logic to a single case (fully complete task) and avoids creating commits for half-done work.

### 2026-02-22: Make scenarios mode-agnostic

Removed `--trunk` from scenarios 1-4 since recovery behavior is the same regardless of mode. Removed the separate WorktreeMode scenario (Scenario 5) since it added no distinct recovery behavior.

### 2026-02-22: CommitRecovery class, not pre-dispatch placement

Recovery cannot live in `ImplementCommand.execute()` before mode dispatch. In WorktreeMode, uncommitted changes from a failed previous run are in the worktree directory, which is set up inside `_worktree_mode()`. Changed to a `CommitRecovery` class that each mode calls at the appropriate point: TrunkMode at the start of its task loop, WorktreeMode after worktree setup but before its task loop.
