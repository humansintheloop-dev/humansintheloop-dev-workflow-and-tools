# Discussion: implement-address-review-loop

## Context from Codebase Analysis

The existing `i2code implement` command already has a `PullRequestReviewProcessor` that:
- Fetches unprocessed PR comments, reviews, and conversation comments
- Triages via Claude (will_fix vs needs_clarification)
- Applies fixes grouped by related comments
- Replies to comments with "Fixed in <SHA>"
- Tracks processed feedback IDs in `WorkflowState` (persisted to `*-wt-state.json`)

This feedback processing currently runs as part of the main `WorktreeMode` loop (priority: CI fixes → PR feedback → next task). It only executes between task completions.

The proposed `--address-review-comments` flag would create a dedicated mode focused solely on the feedback-response cycle.

## Questions and Answers

### Q1: What is the primary use case for `--address-review-comments`?

**Answer:** The flag modifies the existing flow, not replace it:

1. It bypasses the incomplete-task validation in `ImplementCommand.execute()` (which would normally prevent running if tasks are incomplete).
2. Tasks still execute normally if any remain in the plan.
3. When `get_next_task()` returns `None` in `WorktreeMode.execute()`, instead of printing completion and returning, it enters a sleep-poll loop that watches for and addresses new review feedback.

This is a behavioral change to the existing loop's termination condition, not a separate mode.

### Q2: What should the exit condition be for the review-addressing loop?

**Answer:** A — Manual termination only. The user kills the process (Ctrl+C) when they're satisfied. No timeout, PR-event, or idle-based exit.

### Q3: What should the sleep/poll interval be?

**Answer:** A — Fixed interval. Default assumption: 30 seconds between polls. This is a hardcoded constant, not a CLI flag. Can be easily changed later if needed.

### Q4: Should the review loop also handle CI failures triggered by its own fix commits?

**Answer:** A — Yes, keep CI-fix priority. The loop iteration order is: check CI → check feedback → sleep. Same as the current main loop. Fix commits that break CI get caught on the next iteration.

### Q5: Should `--address-review-comments` require that a PR already exists?

**Answer:** B — Fail fast if no PR exists. The point of this flag is to respond to review comments on an existing PR. If there's no PR, there are no comments to address. The command should error with a clear message.

### Q6: How much of the existing flow should change?

**Answer:** Minimal. The existing flow executes as-is. The only two changes are:

1. **`ImplementCommand.execute()`** — skip the incomplete-task validation when `--address-review-comments` is set.
2. **`WorktreeMode.execute()`** — when `get_next_task()` returns `None`, instead of exiting, enter a CI-fix → feedback → 30s sleep poll loop.

Everything else (worktree setup, PR lookup, CI monitoring, review processing, task execution) uses the existing flow unchanged. No new classes or major restructuring needed.

### Q7: Should the review loop exit gracefully if the PR is merged or closed?

**Answer:** A — Yes. Each iteration should check the PR state and exit gracefully if merged or closed. This avoids confusing errors from trying to push to a merged PR.

### Q8: Should `--address-review-comments` be compatible with `--trunk` mode?

**Answer:** Worktree mode only. Incompatible with `--trunk` (no PR exists in trunk mode). Should error if both flags are specified, same pattern as existing `--cleanup`/`--setup-only` incompatibilities with `--trunk`.

### Q9: Should the PR be marked "ready for review" before entering the review loop?

**Answer:** No special handling. The existing `mark_pr_ready()` call runs at its current location as usual. It's idempotent — if the PR is already marked ready from a prior run, the call is harmless.

## Classification

**Type:** A — User-facing feature

**Rationale:** This adds a new CLI flag to the existing `i2code implement` command that changes user-visible behavior — how the command behaves after all plan tasks are complete. It modifies the workflow's termination condition to support a post-implementation review-response cycle. It is not an architecture POC (no new architectural concern to validate), not a platform capability (no new APIs or contracts for other services), and not educational.

