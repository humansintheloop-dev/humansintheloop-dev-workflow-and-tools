# Specification: implement --address-review-comments

## Classification

**Type:** A — User-facing feature

**Rationale:** This adds a new CLI flag to the existing `i2code implement` command that changes user-visible behavior — specifically, how the command behaves after all plan tasks are complete. It modifies the workflow's termination condition to support a post-implementation review-response cycle.

## Purpose and Background

The `i2code implement` command executes plan tasks in a worktree, creates a draft PR, and processes reviewer feedback between tasks. Once all tasks complete, the command marks the PR as ready for review and exits.

After exiting, a human reviewer may leave comments on the PR. Currently, addressing those comments requires either manual intervention or re-running `implement` — which fails because all tasks are already marked complete.

The `--address-review-comments` flag closes this gap by keeping the process alive after task completion, continuously polling for and addressing new review feedback.

## Target Users and Personas

**Primary user:** A developer using the `i2code implement` workflow who wants Claude to autonomously respond to PR review comments after all implementation tasks are done.

## Problem Statement and Goals

**Problem:** After `i2code implement` completes all tasks and exits, there is no automated way to have Claude address subsequent PR review feedback. The developer must either manually apply fixes or work around the "all tasks complete" guard to re-enter the implement loop.

**Goals:**

1. Allow `i2code implement` to continue running after all tasks are complete, polling for new review feedback.
2. Reuse the existing `PullRequestReviewProcessor` and `GithubActionsBuildFixer` infrastructure — no duplication.
3. Minimize code changes: two surgical modifications to existing control flow.

## In-Scope

- New `--address-review-comments` boolean flag on the `implement` CLI command.
- Bypassing the incomplete-task validation in `ImplementCommand.execute()` when the flag is set.
- A poll loop in `WorktreeMode.execute()` that runs when no tasks remain and the flag is set.
- Graceful exit when the PR is merged or closed.
- Flag incompatibility validation with `--trunk`.

## Out-of-Scope

- Configurable poll interval (hardcoded to 30 seconds).
- Timeout or idle-based auto-exit.
- New feedback triage or fix logic (reuses existing `PullRequestReviewProcessor`).
- Changes to trunk mode or isolate mode.
- Any new templates or prompts.

## Functional Requirements

### FR-1: New CLI Flag

Add `--address-review-comments` as a boolean flag to the `implement` Click command.

- Flag name: `--address-review-comments`
- Type: `is_flag=True`
- Default: `False`
- Added to `ImplementOpts` dataclass as `address_review_comments: bool = False`

### FR-2: Skip Incomplete-Task Validation

When `--address-review-comments` is set, the two "all tasks already complete" checks in `ImplementCommand.execute()` must be bypassed:

- `_all_tasks_already_complete()` (line 29 of `implement_command.py`) — guards entry to all modes.
- `_all_tasks_already_complete_in_worktree()` (line 61 of `implement_command.py`) — guards entry to worktree mode specifically.

When the flag is set, these checks should not short-circuit the flow, allowing execution to proceed into `WorktreeMode` even when all tasks are complete.

### FR-3: Require Existing PR

When `--address-review-comments` is set, after worktree setup, if no existing PR is found for the idea branch (`find_pr()` returns `None`), the command must fail with a clear error message and non-zero exit code.

### FR-4: Review Poll Loop

When `--address-review-comments` is set and `get_next_task()` returns `None` in `WorktreeMode.execute()`, instead of calling `_print_completion()` and returning, the loop enters a review-polling cycle:

```
while True:
    1. Check CI (build_fixer.check_and_fix_ci()) — if fixes needed, loop back
    2. Check feedback (review_processor.process_feedback()) — if feedback found, loop back
    3. Check PR state (get_pr_state()) — if merged or closed, print message and return
    4. Sleep 30 seconds
```

This reuses the existing `LoopSteps` collaborators. No new classes are needed.

### FR-5: Graceful Exit on PR Merge/Close

Each poll iteration checks the PR state via `GitHubClient.get_pr_state()`. If the state is `MERGED` or `CLOSED`, the loop prints an informational message and exits cleanly (exit code 0).

### FR-6: Flag Incompatibility with --trunk

`--address-review-comments` is incompatible with `--trunk`. If both are specified, raise a `click.UsageError` following the same pattern as existing trunk incompatibilities in `ImplementOpts.validate_trunk_options()`.

### FR-7: Normal Task Execution Preserved

When `--address-review-comments` is set but tasks still remain in the plan, they execute normally through the existing worktree loop. The review poll loop only activates after all tasks are complete.

## Non-Functional Requirements

### NFR-1: Minimal Code Change

The implementation must be limited to:
1. Adding the flag to the CLI and `ImplementOpts`.
2. Conditionally bypassing task-completion checks in `ImplementCommand`.
3. Adding the poll loop branch in `WorktreeMode.execute()`.

No new classes, templates, or major restructuring.

### NFR-2: Poll Interval

Fixed 30-second interval between poll cycles. Defined as a named constant for easy future adjustment.

### NFR-3: Manual Termination

The review poll loop runs indefinitely until the user sends SIGINT (Ctrl+C) or the PR is merged/closed. No timeout or idle detection.

### NFR-4: Testability

The poll loop must be testable using the existing `FakeGitRepository`, `FakeClaudeRunner`, and `FakeWorkflowState` test doubles. The sleep can be injected or mocked via the existing `clock` parameter on `LoopSteps`.

## Success Metrics

1. A developer can run `i2code implement <idea-dir> --address-review-comments` on a completed idea and have Claude respond to PR review comments.
2. The loop exits gracefully when the PR is merged.
3. CI failures caused by review-fix commits are caught and addressed automatically.
4. No regressions to the existing implement workflow when the flag is not used.

## Epics and User Stories

### Epic: Address Review Comments Loop

**US-1:** As a developer, I want to run `i2code implement --address-review-comments` so that Claude continuously monitors and addresses PR review feedback after all tasks are complete.

**US-2:** As a developer, I want the command to exit gracefully when my PR is merged or closed, so I don't have to manually kill the process after the review cycle is done.

**US-3:** As a developer, I want the command to fail immediately if there is no PR to monitor, so I get clear feedback instead of a silent no-op.

**US-4:** As a developer, I want the command to still execute remaining tasks before entering the review loop, so I can use the flag even if some tasks haven't been completed yet.

**US-5:** As a developer, I want CI failures caused by review-fix commits to be caught and fixed automatically, so the review loop is self-healing.

## Scenarios

### Scenario 1: Primary — Post-Implementation Review Addressing (Main End-to-End Scenario)

**Preconditions:** All plan tasks are complete. A PR exists and is marked ready for review.

1. Developer runs `i2code implement <idea-dir> --address-review-comments`.
2. Command bypasses the "all tasks complete" check and enters worktree mode.
3. Worktree setup completes; existing PR is found.
4. `get_next_task()` returns `None` — no tasks to execute.
5. Command enters the review poll loop.
6. Reviewer leaves a comment on the PR.
7. Next poll detects the comment; `PullRequestReviewProcessor` triages and applies a fix.
8. Fix is pushed; CI runs.
9. Loop continues polling.
10. Reviewer approves and merges the PR.
11. Next poll detects `MERGED` state; command exits gracefully.

### Scenario 2: Mid-Implementation with Flag

**Preconditions:** Some plan tasks remain incomplete. A PR may or may not exist yet.

1. Developer runs `i2code implement <idea-dir> --address-review-comments`.
2. Command bypasses the "all tasks complete" check.
3. Remaining tasks execute normally (task → push → CI → feedback → next task).
4. After the last task completes, instead of exiting, the review poll loop activates.
5. Behavior continues as in Scenario 1.

### Scenario 3: No PR Exists — Fail Fast

**Preconditions:** `--address-review-comments` is set. No PR exists for the idea branch.

1. Developer runs `i2code implement <idea-dir> --address-review-comments`.
2. Worktree setup completes. `find_pr()` returns `None`.
3. Command prints an error message and exits with non-zero code.

### Scenario 4: CI Failure During Review Loop

**Preconditions:** Review loop is active. A fix commit breaks CI.

1. Review poll detects feedback, applies a fix, pushes.
2. CI fails.
3. Next iteration: `build_fixer.check_and_fix_ci()` detects the failure and attempts a fix.
4. Fix is pushed; CI re-runs.
5. Loop resumes normal polling.

### Scenario 5: Incompatible Flags

1. Developer runs `i2code implement <idea-dir> --address-review-comments --trunk`.
2. Command raises `UsageError`: `--trunk cannot be combined with: --address-review-comments`.

### Scenario 6: Manual Termination

1. Review loop is active. No new feedback arrives.
2. Developer presses Ctrl+C.
3. Process terminates.

## Change History

### 2026-03-01: Initial specification

Created from brainstorming discussion. Classification: User-facing feature (Type A).
