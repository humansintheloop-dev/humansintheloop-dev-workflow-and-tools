# Specification: Commit Uncommitted Changes Before Implement

## Purpose and Background

The `i2code go` orchestrator guides users through the idea-to-code workflow: brainstorm → spec → plan → implement. During the brainstorming, spec, and plan phases, files are created and modified in the idea directory (e.g., `*-idea.md`, `*-discussion.md`, `*-spec.md`, `*-plan.md`). By the time the user reaches the `has_plan` state and is ready to implement, these files are often uncommitted.

If `i2code implement` runs before the idea files are committed, the implementation happens on top of a dirty working tree. This creates a messy git history where idea artifacts and implementation changes get interleaved in commits, or idea files are left as untracked/modified noise throughout the implementation.

## Target Users

Developers using the `i2code go` CLI workflow to move from idea to implementation.

## Problem Statement

When the user reaches the `has_plan` state in `i2code go`, the idea directory typically contains uncommitted changes from prior workflow steps. There is no prompt or mechanism to commit these before implementation begins.

## Goals

1. Ensure idea directory files are committed before implementation starts.
2. Make committing the default action when uncommitted changes exist, so users naturally fall into the right workflow.
3. Preserve the existing workflow when no uncommitted changes are present.

## In Scope

- Detecting uncommitted changes (staged, unstaged, untracked) within the idea directory.
- Adding a "Commit changes" menu option in the `has_plan` state.
- Running `git add` and `git commit` scoped to the idea directory to perform the commit.

## Out of Scope

- Detecting or committing changes outside the idea directory.
- Adding commit checks to states other than `has_plan`.
- Changing the `i2code implement` command behavior.

## Functional Requirements

### FR-1: Detect uncommitted changes in the idea directory

When entering the `has_plan` state, check for uncommitted changes (staged, unstaged, or untracked files) scoped to the idea directory. Use `git status --porcelain -- <idea-directory>` (or equivalent) to determine if any changes exist.

### FR-2: Dynamic menu in `has_plan` state

**When uncommitted changes exist in the idea directory**, display:

```
Implementation plan exists. What would you like to do?
  1) Revise the plan
  2) Commit changes [default]
  3) Implement the entire plan
  4) Exit
```

**When no uncommitted changes exist**, display the current menu unchanged:

```
Implementation plan exists. What would you like to do?
  1) Revise the plan
  2) Implement the entire plan [default]
  3) Exit
```

### FR-3: Commit via git

When the user selects "Commit changes", run:

```bash
git add <idea-directory>
git commit -m "Add idea docs for <idea-name>" -- <idea-directory>
```

Where `<idea-directory>` is the path to the idea directory (the `$dir` variable in `idea-to-code.sh`) and `<idea-name>` is the idea name (the `$IDEA_NAME` variable).

### FR-4: Loop back after commit

After a successful commit, continue the main workflow loop. On the next iteration, `detect_state` runs again, the uncommitted-changes check runs again, and if no more changes remain, the menu shows "Implement" as the default.

### FR-5: Handle commit failure

If the `git commit` command fails (non-zero exit), use the existing `handle_error` pattern to offer "Retry" or "Abort workflow".

## Non-Functional Requirements

### NFR-1: No workflow disruption

When there are no uncommitted changes, the user experience is identical to the current behavior. No extra prompts, delays, or output.

### NFR-2: Fast detection

The git status check should add negligible latency (< 1 second) to the menu display.

## Success Metrics

- Idea directory files are consistently committed before `i2code implement` runs.
- No user complaints about unexpected prompts when the idea directory is clean.

## Epics and User Stories

### Epic: Commit idea files before implementation

**US-1**: As a developer using `i2code go`, when my plan is ready and I have uncommitted idea files, I want to be prompted to commit them before implementing, so that my git history separates idea artifacts from implementation changes.

**US-2**: As a developer using `i2code go`, when my plan is ready and all idea files are already committed, I want to see the normal implement menu with no extra steps, so the workflow is not slowed down.

**US-3**: As a developer using `i2code go`, when I commit my idea files and there are still uncommitted changes (e.g., the commit only covered some files), I want to be prompted again on the next loop iteration, so that nothing is missed.

## Scenarios

### S-1: Primary scenario — commit then implement (steel-thread candidate)

1. User has completed brainstorming, spec, and plan phases. The idea directory contains uncommitted files.
2. User runs `i2code go <idea-directory>`.
3. State is detected as `has_plan`.
4. Git status check finds uncommitted changes in the idea directory.
5. Menu shows "Commit changes" as option 2 (default).
6. User presses Enter (accepts default).
7. `git add <idea-directory>` and `git commit -m "Add idea docs for <idea-name>" -- <idea-directory>` run and succeed.
8. Workflow loops back. State is still `has_plan`.
9. Git status check finds no uncommitted changes.
10. Menu shows "Implement the entire plan" as option 2 (default).
11. User presses Enter to implement.

### S-2: No uncommitted changes

1. User runs `i2code go <idea-directory>` with all idea files already committed.
2. State is detected as `has_plan`.
3. Git status check finds no uncommitted changes.
4. Menu shows the current options with "Implement the entire plan" as default.
5. Behavior is identical to today.

### S-3: User skips commit and implements directly

1. State is `has_plan` with uncommitted changes.
2. Menu shows "Commit changes" as default.
3. User selects option 3 ("Implement the entire plan") instead.
4. Implementation proceeds without committing idea files.

### S-4: Commit failure

1. State is `has_plan` with uncommitted changes.
2. User selects "Commit changes".
3. `git commit` command fails.
4. User is offered "Retry" or "Abort workflow" via `handle_error`.
