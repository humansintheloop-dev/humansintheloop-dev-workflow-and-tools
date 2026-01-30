# Discussion: implement-with-worktree

## Context

This discussion captures the refinement of the `implement-with-worktree.sh` script idea.

**Related files:**
- Idea: `wt-pr-based-development-idea.md`
- Workflow reference: `wt-pr-based-development-workflow.md`
- Similar script: `workflow-scripts/implement-plan.sh`

---

## Questions and Answers

### Q1: Script invocation and relationship to implement-plan.sh

The idea file mentions this script is "similar to `implement-plan.sh`" and takes an idea directory as an argument. I see two possible relationships:

A. **Replacement** - `implement-with-worktree.sh` completely replaces `implement-plan.sh` for ideas that use the worktree workflow. Users choose one or the other based on their workflow preference.

B. **Wrapper/orchestrator** - `implement-with-worktree.sh` is a higher-level script that manages worktrees, branches, and PRs, but internally calls `implement-plan.sh` (or reuses its prompt template) for the actual Claude Code invocation.

C. **Parallel implementation** - `implement-with-worktree.sh` is a standalone script that reimplements task execution logic specifically for the worktree context, sharing only `_helper.sh` conventions.

Which relationship do you intend?

**Answer:** C - Parallel implementation. A standalone script that reimplements task execution logic specifically for the worktree context. Bash entry script (`.sh`) calls Python (`.py`) for main logic - cleaner state management and error handling while maintaining consistency with other workflow scripts.

---

### Q2: Mapping plan tasks to slices

The workflow uses "slices" (numbered branches like `01-repro-test`, `02-stabilize-clock`), and the plan file has "Steel Threads" with nested tasks. How should the script map tasks to slices?

A. **One Steel Thread = One Slice** - Each `## Steel Thread N` section in the plan becomes one slice branch and one Draft PR. All tasks within that Steel Thread are implemented before moving to the next slice.

B. **Flat task list, configurable batch size** - Ignore Steel Thread groupings; treat all `- [ ]` tasks as a flat list and batch them into slices (e.g., 3-5 tasks per slice), creating new slice branches as needed.

C. **Single slice for entire plan** - One slice branch for the whole plan; only create a new slice if the current PR exits Draft state unexpectedly.

D. **Explicit slice markers in plan** - Require the plan file to have explicit slice boundary markers (e.g., `<!-- slice: 01-name -->`) that the script parses.

Which approach?

**Answer:** C (with automatic slice creation on Draft exit). Work continues on a single slice until either:
1. All plan tasks are complete, OR
2. The PR is no longer Draft (triggering a new slice to preserve unpushed commits)

The script doesn't proactively batch tasks into slices - it keeps going until interrupted by PR state change or plan completion.

---

### Q3: Detecting and handling PR feedback

The idea file mentions checking for "PR feedback (PR review, inline/Review comments, status checks)" after each push. What should trigger Claude Code to address feedback?

A. **Any new activity** - Any new review comment, inline comment, or failed status check triggers feedback handling.

B. **Blocking feedback only** - Only "Changes Requested" reviews or failed required status checks trigger feedback handling. Informational comments are logged but don't interrupt the task loop.

C. **Manual trigger** - The script logs that feedback exists but continues with tasks. User must manually invoke a separate command to address feedback.

D. **Configurable threshold** - Script has a flag (e.g., `--handle-feedback=blocking|all|none`) to control behavior.

Which approach?

**Answer:** A - Any new activity. Any new review comment, inline comment, or failed status check triggers feedback handling.

---

### Q4: Tracking "new" feedback

To detect "new" feedback, the script needs a baseline. After addressing feedback, how should the script track what's been handled?

A. **Timestamp-based** - Store the last-checked timestamp in a state file. Consider any feedback newer than this timestamp as "new."

B. **Comment ID tracking** - Store IDs of processed comments/reviews in a state file. New IDs indicate new feedback.

C. **Commit SHA comparison** - Compare the PR's latest commit SHA against a stored value. If they match and there's feedback, it's new. After pushing a fix, the SHA changes, resetting the baseline.

D. **Resolved status** - Rely on GitHub's "resolved" status for review comments. Only unresolved comments are considered actionable.

Which approach (or combination)?

**Answer:** B - Comment ID tracking. Store IDs of processed comments/reviews in a state file. New IDs indicate new feedback.

---

### Additional Requirement: Verify idea files are committed

Before creating the integration branch and worktree, the script must verify that the idea files (idea file, discussion file, spec file, plan file) are committed to the current branch. This ensures they will be present in the new worktree. If uncommitted idea files are detected, the script should error with a clear message asking the user to commit them first.

---

### Q5: Handling main advancement

The idea file mentions checking for main advancement after each push. The workflow document (Section 7) describes rebasing the integration branch and updating slice branches. When `main` advances, what should the script do?

A. **Automatic rebase** - Automatically rebase the integration branch onto `main` and update the current slice branch (merge if Ready, rebase if Draft). Continue with tasks.

B. **Pause and notify** - Detect main advancement, notify the user, and pause. User decides whether to rebase now or continue and rebase later.

C. **Deferred handling** - Log that main has advanced but continue with tasks. Handle rebasing only at slice boundaries (when starting a new slice or finishing).

D. **Conflict-aware auto** - Attempt automatic rebase; if conflicts occur, pause and notify user. If clean, continue automatically.

Which approach?

**Answer:** D - Conflict-aware auto. Attempt automatic rebase; if conflicts occur, pause and notify user. If clean, continue automatically.

---

### Q6: Handling Claude Code failure to create a commit

The idea file states: "If Claude has failed to create a new commit, it should display error message and exit." How should the script detect this failure?

A. **Git status check** - After Claude Code returns, check if `git status` shows uncommitted changes or if HEAD hasn't advanced. If either, consider it a failure.

B. **Commit count comparison** - Count commits before and after Claude invocation. If no new commits, it's a failure.

C. **Claude exit code** - Rely on Claude Code's exit code to indicate success/failure.

D. **Combined check** - Use Claude's exit code AND verify HEAD advanced. Both must indicate success.

Which approach?

**Answer:** D - Combined check. Use Claude's exit code AND verify HEAD advanced. Both must indicate success.

---

### Q7: Resumability and state persistence

The idea file states the script "can be interrupted and reinvoked at any time" and should "check for existing worktrees, branches, and PRs and reuse them if they exist." What state should be persisted?

A. **Git-only state** - Rely entirely on Git and GitHub state (worktree exists? branch exists? PR exists? plan file task checkboxes). No separate state file needed.

B. **Minimal state file** - Persist only what can't be derived from Git/GitHub: processed comment IDs, current slice number, last-checked timestamp.

C. **Full state file** - Persist comprehensive state: current task index, slice info, comment IDs, last main SHA, Claude session ID for resumption, etc.

D. **Hybrid** - Use Git/GitHub as primary state source, but maintain a lightweight state file for feedback tracking (comment IDs) and optional Claude session resumption.

Which approach?

**Answer:** B - Minimal state file. Persist only what can't be derived from Git/GitHub: processed comment IDs, current slice number.

---

### Q8: Slice naming convention

When creating slices, how should they be named? The workflow shows examples like `01-repro-test`, `02-stabilize-clock`.

A. **Idea name only** - First slice is `01-<idea-name>`, subsequent slices increment: `02-<idea-name>`, `03-<idea-name>`.

B. **Idea + "impl"** - First slice is `01-<idea-name>-impl`, subsequent slices are `02-<idea-name>-cont`, `03-<idea-name>-cont`.

C. **Auto from plan** - Parse the first Steel Thread heading for the slice name. Subsequent slices (created due to Draft exit) use `<nn>-continued`.

D. **User prompt** - When creating a new slice, prompt the user for a descriptive name.

Which approach?

**Answer:** Derive slice name from plan file content. Parse the Steel Thread heading and current task to generate a descriptive kebab-case slice name. For example:
- Steel Thread: "## Steel Thread 1 – Project Setup"
- First task: "Create project directory structure"
- Slice name: `01-project-setup` (from Steel Thread) or `01-project-setup-create-dirs` (with task context)

Subsequent slices (created due to Draft exit) derive their name from the Steel Thread/task being worked on at that point.

---

### Q9: State file location

Where should the minimal state file (processed comment IDs, current slice number) be stored?

A. **Idea directory** - `docs/features/<idea>/<idea>-wt-state.json` - keeps state with the idea files, gets committed.

B. **Worktree root** - `<worktree>/.wt-state.json` - keeps state in the worktree, not committed (add to .gitignore).

C. **XDG/home config** - `~/.config/idea-to-code/<repo>-<idea>-state.json` - outside repo entirely.

D. **Git ignored in repo root** - `<repo>/.wt-state-<idea>.json` with entry in `.gitignore`.

Which approach?

**Answer:** A - Idea directory. Store at `docs/features/<idea>/<idea>-wt-state.json`. Keeps state with idea files and gets committed.

---

### Q10: Claude Code session management

When invoking Claude Code for each task, should the script maintain session continuity?

A. **Fresh session per task** - Each task gets a new Claude session. Simple, but loses context between tasks.

B. **Single session for entire run** - Use `--resume` to maintain one session across all tasks in a single script invocation. Session ID stored in state file.

C. **Session per slice** - New session when starting a slice, resume within the slice. Balances context retention with slice boundaries.

D. **Configurable** - Default to fresh sessions, but support `--resume-sessions` flag to enable continuity.

Which approach?

**Answer:** A - Fresh session per task. Simple, predictable, matches current `implement-plan.sh` behavior. Claude re-reads codebase anyway, so context loss is manageable.

---

### Q11: Prompt templates

The idea file mentions needing a "new prompt template for handling PR feedback." What prompt templates does this script need?

A. **Reuse existing** - Use the existing `implement-plan.md` prompt template for task implementation. Create one new template for PR feedback handling.

B. **All new templates** - Create new templates specific to the worktree workflow:
   - `wt-implement-task.md` - for implementing a single task
   - `wt-handle-feedback.md` - for addressing PR feedback
   - `wt-resolve-conflicts.md` - for resolving rebase conflicts

C. **Minimal new** - Reuse `implement-plan.md` for tasks. Create only `wt-handle-feedback.md` for feedback. Handle conflicts manually (pause and let user resolve).

Which approach?

**Answer:** A - Reuse existing `implement-plan.md` for task implementation. Create one new template (`wt-handle-feedback.md`) for PR feedback handling.

---

### Q12: Handling failed status checks

Status checks (CI builds, tests, linters) were mentioned as part of feedback. When a status check fails:

A. **Treat like review comments** - Fetch the failure details, pass to Claude with the feedback prompt template, let Claude attempt a fix.

B. **Log and continue** - Log the failure but continue with tasks. Assume the developer will investigate CI failures separately.

C. **Pause and notify** - Stop the task loop, display the failure, and wait for user input before continuing.

D. **Retry limit** - Let Claude attempt to fix (option A), but if it fails twice consecutively on the same check, pause and notify.

Which approach?

**Answer:** A - Treat like review comments. Fetch failure details, pass to Claude with feedback prompt template.

**Important general requirement:** In all cases, Claude should be invoked interactively so a human can interrupt and correct. This applies to task implementation, feedback handling, and status check fixes.

---

### Q13: Completion behavior

When all tasks in the plan are complete (all checkboxes marked), what should the script do?

A. **Mark PR ready and exit** - Automatically run `gh pr ready` to mark the PR ready for review, then exit with success message.

B. **Exit only** - Exit with success message. Leave PR in Draft state for user to mark ready when they choose.

C. **Prompt user** - Ask user whether to mark PR ready or leave as Draft.

D. **Merge to integration and prompt** - Merge slice into integration branch, then prompt whether to mark PR ready or start cleanup.

Which approach?

**Answer:** Mark PR as ready, then wait for feedback. The script continues monitoring and handling feedback (reviews, comments, status checks) rather than exiting immediately.

---

### Q14: Feedback polling while waiting

After marking the PR ready, the script waits for feedback. How should it poll for feedback?

A. **Timed polling** - Poll GitHub every N seconds (e.g., 30s or 60s) for new reviews, comments, or status check results.

B. **User-triggered** - Display a message and wait for user to press a key to check for feedback. Repeat until user exits or PR is merged.

C. **Hybrid** - Poll automatically but also allow user to press a key to force an immediate check or exit.

D. **Webhook-based** - Set up a local webhook receiver (more complex) to get push notifications from GitHub.

Which approach, and if timed, what interval?

**Answer:** A - Timed polling.

---

### Q15: Polling interval and exit conditions

What polling interval, and when should the script stop waiting?

**Interval options:**
- 30 seconds (responsive but more API calls)
- 60 seconds (balanced)
- 120 seconds (conservative)

**Exit conditions** (when should the script stop and exit?):

A. **PR merged** - Exit when the PR is merged into main.

B. **PR merged or closed** - Exit when PR is merged or closed (rejected).

C. **PR approved** - Exit when PR receives an approving review (don't wait for merge).

D. **User interrupt only** - Only exit when user presses Ctrl+C. Keep polling indefinitely.

Suggested default: 60s interval, exit on PR merged or closed. Adjust?

**Answer:** Accepted defaults: 60s polling interval, exit when PR is merged or closed.

---

### Q16: Cleanup after PR merge

When the PR is merged (or closed), should the script perform cleanup (as described in workflow section 8)?

A. **Automatic cleanup** - Remove worktree, delete local branches, optionally delete remote branches.

B. **Prompt for cleanup** - Ask user if they want to clean up worktree and branches.

C. **No cleanup** - Just exit. User runs cleanup manually later.

D. **Separate cleanup command** - Exit without cleanup, but provide a separate `cleanup-worktree.sh` script user can run.

Which approach?

**Answer:** Add a `--cleanup` argument. By default, no cleanup on exit. If `--cleanup` flag is passed, perform cleanup (remove worktree, delete local branches) after PR is merged/closed.

---

### Q17: Command-line interface

Based on discussion so far, the script will accept:
- Positional: idea directory (e.g., `docs/features/wt-pr-based-development`)
- `--cleanup`: Perform cleanup after PR merge/close

Any additional arguments needed?

A. **Minimal** - Just the above. Keep it simple.

B. **Task filter** - Add optional task argument like `implement-plan.sh` (e.g., `--task "Create project structure"`) to implement only specific tasks.

C. **Dry-run** - Add `--dry-run` to show what would be done without executing.

D. **Multiple extras** - Add `--task`, `--dry-run`, and `--poll-interval` for flexibility.

Which approach?

**Answer:** A - Minimal. Just idea directory (positional) and `--cleanup` flag.

---

## Classification

**Type:** C - Platform/infrastructure capability

**Rationale:** This is a developer workflow automation tool that enhances the idea-to-code infrastructure. It doesn't add user-facing features to an application, isn't a POC validating architecture, and isn't an educational example. It's a platform capability that improves developer productivity by automating Git worktree management, PR lifecycle, and Claude Code orchestration.
