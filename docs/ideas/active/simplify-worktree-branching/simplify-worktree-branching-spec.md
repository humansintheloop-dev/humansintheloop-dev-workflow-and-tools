# Simplify Worktree Branching — Specification

## Purpose and Background

The `i2code implement` command orchestrates AI-assisted feature development using Git worktrees, GitHub Draft PRs, and Claude Code. Its current worktree mode uses a two-level branching scheme: an integration branch (`idea/<name>/integration`) plus slice branches (`idea/<name>/01-<task-name>`). This scheme was designed to support stacked PRs but was never fully implemented. The extra complexity adds maintenance burden without delivering value.

This specification defines a simplified single-branch model that replaces the integration+slice scheme while preserving all other worktree mode capabilities (PR creation, CI monitoring, PR feedback processing, build fixing).

## Target Users and Personas

- **Developer using `i2code implement`** — runs the command to implement a plan file, reviews the resulting PR, and iterates on feedback.

## Problem Statement and Goals

### Problem

The two-level branching model (integration branch + slice branches) introduces unnecessary complexity:

1. The stacked PR workflow is only partially implemented — slice rollover logic exists in code but is never exercised.
2. Two branches must be created, tracked, and cleaned up per idea.
3. The worktree is checked out on the integration branch and then switched to the slice branch — an extra step with no practical benefit.
4. `WorkflowState` tracks a `slice_number` that never advances beyond 1.
5. Rebase logic (`rebase_integration_branch`, `update_slice_after_rebase`) exists for a workflow that doesn't run.

### Goals

1. Replace the two-level branching with a single `idea/<name>` branch per idea.
2. Remove all dead code related to integration branches, slice branches, slice numbering, and rebase logic.
3. Automatically mark the PR ready for review when all tasks complete.
4. Derive the PR title from the idea file heading instead of the slice branch name.

## In-Scope

- Worktree mode branching simplification (single branch `idea/<name>`)
- Dead code removal: integration branch, slice branch, slice numbering, rebase logic
- `WorkflowState` simplification: remove `slice_number` field
- PR title derived from idea file heading
- PR body simplified to a link to the idea directory
- Automatic `gh pr ready` on completion
- Backward compatibility with existing `*-wt-state.json` files containing `slice_number`

## Out-of-Scope

- Trunk mode — already uses a simple single-branch model, no changes needed.
- Isolate mode plumbing — inherits the worktree mode change automatically; no isolate-specific changes.
- Stacked PR / slice rollover — explicitly removed, not redesigned.
- PR body enrichment (embedding plan contents, idea contents) — body stays minimal.
- New CLI flags (e.g., `--no-ready`, `--draft`) — not needed; completion always marks ready.

## High-Level Functional Requirements

### FR-1: Single Branch Creation

When `i2code implement` runs in worktree mode, it creates (or ensures) a single branch named `idea/<name>`, where `<name>` is the idea directory name. No integration branch or slice branch is created.

### FR-2: Worktree on the Idea Branch

The worktree is created and checked out directly on `idea/<name>`. There is no secondary checkout step.

### FR-3: PR Title from Idea File

The Draft PR title is derived from the first heading (line starting with `# `) in the idea file (`<name>-idea.md`). If no heading is found, fall back to the idea name.

### FR-4: Minimal PR Body

The PR body contains a link to the idea directory in the repository. Format:

```
**Idea directory:** `<idea-directory>`
```

### FR-5: Automatic Ready-for-Review

When all plan tasks are completed, `i2code implement` calls `gh pr ready` to convert the Draft PR to ready-for-review before printing the completion message and PR URL.

### FR-6: WorkflowState Without Slice Number

- New state files are created with only the processed feedback ID lists (no `slice_number`).
- Existing state files that contain `slice_number` are read without error; the field is silently ignored. On next save, `slice_number` is dropped.

### FR-7: Dead Code Removal

The following are removed:

| Component | Location |
|---|---|
| `ensure_integration_branch()` | `git_repository.py` |
| `ensure_slice_branch()` | `git_repository.py` |
| `rebase_integration_branch()` | `branch_lifecycle.py` |
| `update_slice_after_rebase()` | `branch_lifecycle.py` |
| `get_rebase_conflict_message()` | `branch_lifecycle.py` |
| `slice_number` property | `workflow_state.py` |
| `generate_pr_title()` (slice-based) | `pr_helpers.py` |
| `generate_pr_body()` (slice-based) | `pr_helpers.py` |
| `push_to_slice_branch()` | `pr_helpers.py` |
| `should_rollover()` | `pr_helpers.py` |
| `generate_next_slice_branch()` | `pr_helpers.py` |
| Slice-related references in `_worktree_mode()` | `implement_command.py` |
| `state.slice_number` reference in `_push_and_ensure_pr()` | `worktree_mode.py` |

### FR-8: Ensure Idea Branch Method

`GitRepository` gains an `ensure_idea_branch(idea_name)` method that creates (or reuses) the `idea/<name>` branch from the current HEAD.

### FR-9: Updated Worktree Mode Orchestration

The `_worktree_mode()` method in `ImplementCommand` is simplified:

1. Load `WorkflowState` from the state file.
2. `ensure_idea_branch(idea_name)` — creates or reuses `idea/<name>`.
3. `ensure_worktree(idea_name, idea_branch)` — creates the worktree on the idea branch.
4. Set up the worktree project (copy Claude settings, run setup script).
5. Find or note absence of existing PR on the idea branch.
6. Enter the `WorktreeMode` task loop (unchanged in structure).

### FR-10: Updated PR Creation in Task Loop

`_push_and_ensure_pr()` in `WorktreeMode` calls `ensure_pr()` without a `slice_number` argument. The `ensure_pr()` method reads the idea file heading for the title and generates the minimal body.

## Security Requirements

No security-sensitive changes. All operations use the existing `gh` CLI authentication context. No new endpoints, APIs, or authorization boundaries are introduced.

## Non-Functional Requirements

### Backward Compatibility

- Existing `*-wt-state.json` files with `slice_number` must load without error.
- Existing worktrees and branches created under the old scheme are not migrated automatically — they remain as-is. The new code simply creates `idea/<name>` branches going forward.

### Simplicity

- The change is a net reduction in code. No new abstractions, flags, or configuration options are introduced.

### Testability

- All new and modified methods must be covered by unit tests using the existing `FakeGitRepository` pattern.
- The `ensure_pr()` signature change and `mark_pr_ready()` call must be verified in tests.

## Success Metrics

1. The two-level branching code is fully removed — no references to "integration branch" or "slice branch" remain in production code.
2. `i2code implement` creates a single `idea/<name>` branch and a single Draft PR.
3. The PR is automatically marked ready for review on completion.
4. All existing tests pass (after updating for the new behavior).
5. State files with the old `slice_number` field load without error.

## Epics and User Stories

### Epic 1: Single-Branch Worktree Mode

**US-1.1:** As a developer, when I run `i2code implement <idea-dir>`, the tool creates a single branch `idea/<name>` and a worktree checked out on that branch, so that I don't have to reason about integration vs. slice branches.

**US-1.2:** As a developer, when the first task is pushed, a Draft PR is created with the title taken from the idea file heading and a minimal body linking to the idea directory, so that the PR is self-describing.

**US-1.3:** As a developer, when all tasks complete, the Draft PR is automatically marked ready for review, so that I don't need a manual step to request review.

### Epic 2: Dead Code Removal

**US-2.1:** As a maintainer, integration branch, slice branch, slice numbering, and rebase logic are removed from the codebase, so that there is no unused code to maintain.

### Epic 3: State File Simplification

**US-3.1:** As a developer, when I run `i2code implement` on an idea that has an old state file with `slice_number`, the tool works normally and drops the field on next save, so that I don't need to manually clean up state files.

## Scenarios

### Scenario 1: Fresh Idea — End-to-End (Primary)

**Preconditions:** An idea directory exists with `*-idea.md`, `*-spec.md`, and `*-plan.md`. No branch, worktree, or PR exists yet.

**Flow:**
1. Developer runs `i2code implement <idea-dir>`.
2. Tool creates branch `idea/<name>` from HEAD.
3. Tool creates worktree `<repo>-wt-<name>` on that branch.
4. Tool sets up the worktree (Claude settings, setup script).
5. Tool enters the task loop:
   a. Gets the next uncompleted task from the plan.
   b. Runs Claude to implement the task.
   c. Pushes the commit to `idea/<name>`.
   d. On first push: creates a Draft PR with title from the idea file heading and minimal body.
   e. Waits for CI to pass.
   f. Repeats for each remaining task.
6. When no tasks remain: calls `gh pr ready` to mark the PR ready for review.
7. Prints completion message with PR URL.

**Postconditions:** A single branch `idea/<name>` exists with all task commits. A ready-for-review PR exists targeting the default branch.

### Scenario 2: Resume After Interruption

**Preconditions:** An idea has a branch, worktree, state file, and Draft PR from a prior run. Some tasks are already completed.

**Flow:**
1. Developer runs `i2code implement <idea-dir>`.
2. Tool reuses the existing `idea/<name>` branch and worktree.
3. Tool loads the state file and finds the existing PR.
4. Task loop resumes from the first uncompleted task.
5. On completion, PR is marked ready for review.

**Postconditions:** Same as Scenario 1.

### Scenario 3: PR Feedback Mid-Implementation

**Preconditions:** An idea is mid-implementation with a Draft PR. A reviewer has left comments on the PR.

**Flow:**
1. At the top of each task loop iteration, the review processor checks for unprocessed feedback.
2. Feedback is triaged (fix vs. needs clarification).
3. Fixes are applied, pushed, and the reviewer is notified.
4. The task loop continues with the next uncompleted task.

**Postconditions:** Reviewer feedback is addressed. Processed feedback IDs are saved in the state file.

### Scenario 4: CI Failure During Implementation

**Preconditions:** A task has been pushed and CI fails.

**Flow:**
1. The build fixer detects the failing CI run.
2. Claude is invoked to fix the failure based on CI logs.
3. The fix is pushed and CI is re-monitored.
4. If CI passes, the task loop continues.

**Postconditions:** CI is green. The task loop proceeds to the next task.

### Scenario 5: Old State File Migration

**Preconditions:** An existing `*-wt-state.json` contains `slice_number: 1` along with feedback ID lists.

**Flow:**
1. Developer runs `i2code implement <idea-dir>`.
2. `WorkflowState.load()` reads the file, ignoring `slice_number`.
3. On next `save()`, only the feedback ID lists are written.

**Postconditions:** The state file no longer contains `slice_number`.
