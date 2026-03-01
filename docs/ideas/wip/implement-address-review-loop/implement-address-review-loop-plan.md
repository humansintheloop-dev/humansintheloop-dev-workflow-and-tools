Now I have sufficient context from the idea, specification, and discussion files. Let me generate the plan.

---

# Implementation Plan: `implement --address-review-comments`

## Idea Type

**Type A** — User-facing feature

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

- NEVER write production code without first writing a failing test
- Before using Write or Edit on any production `.py` file, ask: "Do I have a failing test?" If not, write the test first
- When task direction changes mid-implementation, return to TDD PLANNING state and write a test first

### Verification Requirements

- Hard rule: NEVER git commit, git push, or open a PR unless you have successfully run the project's test command and it exits 0
- Hard rule: If running tests is blocked for any reason (including permissions), ALWAYS STOP immediately. Print the failing command, the exact error output, and the permission/path required
- Before committing, ALWAYS print a Verification section containing the exact test command (NOT an ad-hoc command - it must be a proper test command such as `./test-scripts/*.sh`, `./scripts/test.sh`, or `pytest`), its exit code, and the last 20 lines of output

## Architecture Notes

This feature makes two surgical modifications to the existing `i2code implement` flow:

1. **`ImplementCommand.execute()`** — conditionally bypass the `_all_tasks_already_complete()` and `_all_tasks_already_complete_in_worktree()` checks when the flag is set.
2. **`WorktreeMode.execute()`** — when `get_next_task()` returns `None` and the flag is set, enter a poll loop (`check CI → process feedback → check PR state → sleep 30s`) instead of printing completion and returning.

All other existing behavior (worktree setup, PR creation, CI monitoring, review processing, task execution) remains unchanged. No new classes, templates, or prompts are needed. The poll loop reuses existing `LoopSteps` collaborators (`PullRequestReviewProcessor`, `GithubActionsBuildFixer`) and the existing `clock` parameter for testable sleep.

**Key files to locate before starting:**
- CLI Click command definition for `implement` (adds the flag)
- `ImplementOpts` dataclass (adds the field)
- `ImplementCommand.execute()` (bypasses completion checks)
- `WorktreeMode.execute()` (adds poll loop)
- `LoopSteps` class (reused collaborators)
- `GitHubClient.get_pr_state()` (checks MERGED/CLOSED)
- Existing test doubles: `FakeGitRepository`, `FakeClaudeRunner`, `FakeWorkflowState`

---

## Steel Thread 1: Flag Registration and Trunk Incompatibility

Proves the new CLI flag exists and validates correctly against incompatible options. This is the foundation all subsequent threads build on.

- [x] **Task 1.1: `--address-review-comments` raises UsageError when combined with `--trunk`**
  - TaskType: OUTCOME
  - Entrypoint: `i2code implement <idea-dir> --address-review-comments --trunk`
  - Observable: Command raises `click.UsageError` with message indicating `--trunk` cannot be combined with `--address-review-comments`
  - Evidence: pytest test creates `ImplementOpts` with both `trunk=True` and `address_review_comments=True`, calls `validate_trunk_options()`, and asserts `click.UsageError` is raised with the expected message
  - Steps:
    - [x] Locate the Click command definition for `implement` and add `--address-review-comments` as `is_flag=True, default=False`
    - [x] Add `address_review_comments: bool = False` field to `ImplementOpts` dataclass
    - [x] Thread the flag value from the Click command through to `ImplementOpts` construction
    - [x] Add `--address-review-comments` to the trunk incompatibility check in `ImplementOpts.validate_trunk_options()`, following the existing pattern for other incompatible flags
    - [x] Write pytest test: construct `ImplementOpts` with both flags set, assert `click.UsageError` is raised
    - [x] Write pytest test: construct `ImplementOpts` with only `--address-review-comments` (no `--trunk`), assert no error

---

## Steel Thread 2: Fail Fast When No PR Exists

Proves the command bypasses task-completion checks when the flag is set, and fails immediately if no PR exists for the idea branch.

- [ ] **Task 2.1: Command fails with clear error when `--address-review-comments` is set but no PR exists**
  - TaskType: OUTCOME
  - Entrypoint: `i2code implement <idea-dir> --address-review-comments` (all tasks complete, no PR exists)
  - Observable: Command exits with non-zero exit code and prints error message indicating no PR was found to monitor
  - Evidence: pytest test using `FakeGitRepository` configured with no PR, all tasks marked complete, and `address_review_comments=True`. Test invokes `WorktreeMode.execute()` (or the relevant entry point) and asserts non-zero exit and error message about missing PR
  - Steps:
    - [ ] In `ImplementCommand.execute()`, modify the `_all_tasks_already_complete()` check (approx. line 29) to skip when `address_review_comments` is `True`
    - [ ] In `ImplementCommand.execute()`, modify the `_all_tasks_already_complete_in_worktree()` check (approx. line 61) to skip when `address_review_comments` is `True`
    - [ ] In `WorktreeMode.execute()`, after worktree setup, add a check: if `address_review_comments` is `True` and `find_pr()` returns `None`, print an error message and return a non-zero exit code
    - [ ] Write pytest test: all tasks complete, no PR, flag set → asserts the task-completion checks are bypassed AND the command fails with the "no PR" error
    - [ ] Write pytest test: verify that without the flag, the existing `_all_tasks_already_complete()` behavior is preserved (regression test)

---

## Steel Thread 3: Post-Implementation Review Addressing

Proves the primary end-to-end flow: after all tasks are complete, the command enters a poll loop that processes review feedback and exits gracefully when the PR is merged.

- [ ] **Task 3.1: Review poll loop processes feedback and exits when PR is merged**
  - TaskType: OUTCOME
  - Entrypoint: `i2code implement <idea-dir> --address-review-comments` (all tasks complete, PR exists and is open)
  - Observable: Command enters review poll loop; processes feedback via `PullRequestReviewProcessor`; on next iteration detects PR state is `MERGED` and exits with code 0 and informational message
  - Evidence: pytest test using `FakeGitRepository` and mock `clock` (to avoid real sleep). Test configures: all tasks complete, PR exists, `process_feedback()` returns feedback on first call, `get_pr_state()` returns `MERGED` on second iteration. Asserts: feedback was processed, exit code is 0, merge message is printed
  - Steps:
    - [ ] Define a named constant `REVIEW_POLL_INTERVAL_SECONDS = 30` in the appropriate module
    - [ ] In `WorktreeMode.execute()`, when `get_next_task()` returns `None` and `address_review_comments` is `True`: instead of calling `_print_completion()` and returning, enter a `while True` loop
    - [ ] Poll loop body: call `review_processor.process_feedback()` — if feedback was processed, continue to next iteration
    - [ ] Poll loop body: call `get_pr_state()` — if `MERGED` or `CLOSED`, print informational message and return exit code 0
    - [ ] Poll loop body: sleep `REVIEW_POLL_INTERVAL_SECONDS` using the existing `clock` parameter from `LoopSteps`
    - [ ] Write pytest test: feedback detected and processed, then PR merged → loop exits gracefully
    - [ ] Write pytest test: PR is `CLOSED` (not merged) → loop exits gracefully with appropriate message
    - [ ] Write pytest test: no feedback, PR still open → loop sleeps and continues polling

---

## Steel Thread 4: CI Self-Healing in Review Loop

Proves that CI failures caused by review-fix commits are caught and fixed automatically within the review poll loop, maintaining the same CI-fix priority as the main task loop.

- [ ] **Task 4.1: Review loop detects and fixes CI failures from review-fix commits**
  - TaskType: OUTCOME
  - Entrypoint: `i2code implement <idea-dir> --address-review-comments` (in review poll loop, CI has failed)
  - Observable: Poll loop calls `build_fixer.check_and_fix_ci()` before processing feedback; when CI failure is detected, fix is applied and loop continues; on subsequent iteration with no failures, feedback is processed normally
  - Evidence: pytest test using `FakeGitRepository` and mock `clock`. Test configures: `check_and_fix_ci()` returns "fix applied" on first call and "no fix needed" on second call, then PR transitions to `MERGED`. Asserts: `check_and_fix_ci()` was called before `process_feedback()`, fix was applied, loop continued
  - Steps:
    - [ ] In the review poll loop (from Task 3.1), add `build_fixer.check_and_fix_ci()` as the FIRST step in each iteration, before `process_feedback()`
    - [ ] If `check_and_fix_ci()` indicates a fix was applied, continue to the next iteration (skip feedback processing for this cycle)
    - [ ] Write pytest test: CI failure on first iteration → fix applied → next iteration processes feedback normally → PR merged → exit
    - [ ] Write pytest test: CI failure is fixed, but the fix itself breaks CI again → second fix attempted → eventually passes

---

## Steel Thread 5: Mid-Implementation Task Execution Before Review Loop

Proves that when the flag is set but tasks still remain in the plan, they execute normally through the existing worktree loop before the review poll loop activates.

- [ ] **Task 5.1: Remaining tasks execute normally before review loop activates**
  - TaskType: OUTCOME
  - Entrypoint: `i2code implement <idea-dir> --address-review-comments` (some tasks remain incomplete)
  - Observable: Incomplete tasks execute through the normal task loop (task → push → CI → feedback → next task); after the last task completes, `get_next_task()` returns `None` and the review poll loop activates instead of exiting
  - Evidence: pytest test using `FakeGitRepository`, `FakeClaudeRunner`, and `FakeWorkflowState`. Test configures: one remaining task in plan, `address_review_comments=True`. Asserts: task executes via `ClaudeRunner`, after task completes the review poll loop activates (verified by `process_feedback()` being called in poll mode), then PR merged → exit
  - Steps:
    - [ ] No new production code expected — this behavior should emerge from the existing task loop combined with the poll loop from Task 3.1/4.1
    - [ ] Write pytest test: one task remains → task executes normally → review loop activates → PR merged → clean exit
    - [ ] Write pytest test: multiple tasks remain → all execute in order → review loop activates after last task
    - [ ] If any production code adjustment is needed to support the transition from task execution to poll loop, make that adjustment here
