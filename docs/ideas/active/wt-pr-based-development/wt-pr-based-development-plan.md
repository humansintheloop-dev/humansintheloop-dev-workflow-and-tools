# Implementation Plan: implement-with-worktree.sh

## Idea Type

**C. Platform/infrastructure capability** - This is a workflow automation script that implements Git worktree and GitHub Draft PR-based development.

---

## Overview

This plan implements `implement-with-worktree.sh`, a workflow automation script that orchestrates Git worktree/PR-based development. The script creates Git infrastructure (integration branches, worktrees, slice branches), manages Draft PRs, executes plan tasks via Claude Code, handles PR feedback, and manages the complete PR lifecycle.

The implementation follows TDD practices - each task includes writing a failing test first, then implementing code to make it pass.

---

## Steel Thread 1: Project Setup and Minimal Entry Point

Establishes the Python environment infrastructure and creates a minimal working entry point.

- [ ] **Task 1.1: Bash entry script invokes Python with arguments**
  - TaskType: INFRA
  - Entrypoint: `workflow-scripts/implement-with-worktree.sh --help`
  - Observable: Exit code 0, stdout contains usage information including `<idea-directory>` and `--cleanup` options
  - Evidence: `./workflow-scripts/implement-with-worktree.sh --help | grep -q "idea-directory" && echo "PASS"`
  - Steps:
    - [ ] Create `workflow-scripts/_python_helper.sh` with `ensure_venv` and `run_python` functions
    - [ ] Create `workflow-scripts/requirements.txt` with initial dependencies (none required initially)
    - [ ] Create `workflow-scripts/implement-with-worktree.sh` that sources helper and delegates to Python
    - [ ] Create `workflow-scripts/implement-with-worktree.py` with argparse CLI that shows help
    - [ ] Add `.venv/` to `.gitignore` if not already present

- [ ] **Task 1.2: Script validates idea directory argument**
  - TaskType: OUTCOME
  - Entrypoint: `workflow-scripts/implement-with-worktree.sh /nonexistent/path`
  - Observable: Exit code non-zero, stderr contains error message about directory not existing
  - Evidence: `! ./workflow-scripts/implement-with-worktree.sh /nonexistent/path 2>&1 | grep -q "does not exist" && echo "PASS"`
  - Steps:
    - [ ] Add idea directory path validation in Python
    - [ ] Return appropriate exit code and error message

---

## Steel Thread 2: Idea File Validation

Ensures all required idea files are committed before proceeding.

- [ ] **Task 2.1: Script verifies idea files exist**
  - TaskType: OUTCOME
  - Entrypoint: `workflow-scripts/implement-with-worktree.sh <test-idea-dir>` (where test-idea-dir lacks required files)
  - Observable: Exit code non-zero, stderr lists missing files (idea, spec, plan)
  - Evidence: Create temp directory without required files, run script, verify error message mentions missing files
  - Steps:
    - [ ] Check for `*-idea.md`, `*-spec.md`, `*-plan.md` files in idea directory
    - [ ] Report which files are missing

- [ ] **Task 2.2: Script verifies idea files are committed**
  - TaskType: OUTCOME
  - Entrypoint: `workflow-scripts/implement-with-worktree.sh <test-idea-dir>` (where files exist but are uncommitted)
  - Observable: Exit code non-zero, stderr indicates files must be committed before proceeding
  - Evidence: Create temp git repo with uncommitted idea files, run script, verify error about uncommitted files
  - Steps:
    - [ ] Use `git status --porcelain` to check if idea files have uncommitted changes
    - [ ] Error with clear message if uncommitted changes exist

---

## Steel Thread 3: Integration Branch Management

Creates or reuses the integration branch.

- [ ] **Task 3.1: Script creates integration branch when not exists**
  - TaskType: OUTCOME
  - Entrypoint: `workflow-scripts/implement-with-worktree.sh <test-idea-dir>` (in repo without integration branch)
  - Observable: Integration branch `idea/<idea-name>/integration` exists, based on current HEAD
  - Evidence: Set up test repo, run script, verify `git branch --list "idea/*/integration"` shows the branch
  - Steps:
    - [ ] Extract idea name from directory path
    - [ ] Create branch using `git branch idea/<idea-name>/integration`

- [ ] **Task 3.2: Script reuses existing integration branch**
  - TaskType: OUTCOME
  - Entrypoint: `workflow-scripts/implement-with-worktree.sh <test-idea-dir>` (in repo where integration branch exists)
  - Observable: No new branch created, script proceeds using existing branch, no error
  - Evidence: Create integration branch first, run script twice, verify only one branch exists (idempotent)
  - Steps:
    - [ ] Check if integration branch exists before creating
    - [ ] Log message indicating reuse of existing branch

---

## Steel Thread 4: Worktree Management

Creates or reuses the worktree directory.

- [ ] **Task 4.1: Script creates worktree when not exists**
  - TaskType: OUTCOME
  - Entrypoint: `workflow-scripts/implement-with-worktree.sh <test-idea-dir>` (where worktree doesn't exist)
  - Observable: Worktree directory exists at `../<repo-name>-wt-<idea-name>`, linked to integration branch
  - Evidence: Run script, verify worktree directory exists and `git worktree list` shows it
  - Steps:
    - [ ] Determine worktree path using repo name and idea name
    - [ ] Create worktree with `git worktree add <path> <integration-branch>`

- [ ] **Task 4.2: Script reuses existing worktree**
  - TaskType: OUTCOME
  - Entrypoint: `workflow-scripts/implement-with-worktree.sh <test-idea-dir>` (where worktree exists)
  - Observable: No new worktree created, script proceeds using existing worktree, no error
  - Evidence: Create worktree first, run script twice, verify `git worktree list` shows exactly one worktree for idea
  - Steps:
    - [ ] Check if worktree already exists via `git worktree list`
    - [ ] Log message indicating reuse of existing worktree

---

## Steel Thread 5: Slice Branch and Draft PR Management

Creates slice branch and Draft PR for the work.

- [ ] **Task 5.1: Script creates slice branch with correct naming**
  - TaskType: OUTCOME
  - Entrypoint: `workflow-scripts/implement-with-worktree.sh <test-idea-dir>`
  - Observable: Slice branch `idea/<idea-name>/01-<slice-name>` exists in worktree
  - Evidence: Run script, verify branch exists with pattern `idea/*/01-*`
  - Steps:
    - [ ] Parse plan file to extract steel thread heading for slice name
    - [ ] Create branch `idea/<idea-name>/<nn>-<slice-name>` in worktree
    - [ ] Initialize or load state file with slice_number

- [ ] **Task 5.2: Script creates Draft PR for slice branch**
  - TaskType: OUTCOME
  - Entrypoint: `workflow-scripts/implement-with-worktree.sh <test-idea-dir>`
  - Observable: Draft PR exists on GitHub for the slice branch, PR is in draft state
  - Evidence: Run script, verify `gh pr list --json number,isDraft,headRefName` shows draft PR for slice branch
  - Steps:
    - [ ] Push slice branch to remote
    - [ ] Create Draft PR using `gh pr create --draft`
    - [ ] Store PR number in state if needed

- [ ] **Task 5.3: Script reuses existing Draft PR**
  - TaskType: OUTCOME
  - Entrypoint: `workflow-scripts/implement-with-worktree.sh <test-idea-dir>` (where Draft PR exists)
  - Observable: No new PR created, script proceeds using existing PR
  - Evidence: Create PR first, run script twice, verify only one PR exists for the branch
  - Steps:
    - [ ] Query existing PRs for the slice branch before creating
    - [ ] Log message indicating reuse of existing PR

---

## Steel Thread 6: State File Management

Manages the persistent state file for tracking progress.

- [ ] **Task 6.1: Script initializes state file when not exists**
  - TaskType: OUTCOME
  - Entrypoint: `workflow-scripts/implement-with-worktree.sh <test-idea-dir>` (without existing state file)
  - Observable: State file `<idea-dir>/<idea-name>-wt-state.json` created with initial structure
  - Evidence: Run script, verify state file exists with `slice_number`, `processed_comment_ids`, `processed_review_ids` fields
  - Steps:
    - [ ] Define state file schema as Python dataclass or TypedDict
    - [ ] Create state file with initial values on first run

- [ ] **Task 6.2: Script loads and preserves existing state**
  - TaskType: OUTCOME
  - Entrypoint: `workflow-scripts/implement-with-worktree.sh <test-idea-dir>` (with existing state file containing processed IDs)
  - Observable: Existing processed IDs preserved after script run, not reset to empty
  - Evidence: Create state file with test IDs, run script, verify IDs still present
  - Steps:
    - [ ] Load existing state file at startup
    - [ ] Merge/preserve existing data when updating state

---

## Steel Thread 7: Task Parsing and Identification

Parses the plan file to identify uncompleted tasks.

- [ ] **Task 7.1: Script identifies uncompleted tasks from plan file**
  - TaskType: OUTCOME
  - Entrypoint: `workflow-scripts/implement-with-worktree.sh <test-idea-dir>` (with plan containing mix of completed/uncompleted tasks)
  - Observable: Script outputs/logs which task it will work on next (first uncompleted `- [ ]` task)
  - Evidence: Create plan with some checked tasks, verify script identifies correct next task
  - Steps:
    - [ ] Parse plan file for `- [ ]` markers (uncompleted) vs `- [x]` (completed)
    - [ ] Extract task descriptions and ordering
    - [ ] Identify first uncompleted task

- [ ] **Task 7.2: Script detects when all tasks are complete**
  - TaskType: OUTCOME
  - Entrypoint: `workflow-scripts/implement-with-worktree.sh <test-idea-dir>` (with all tasks marked complete)
  - Observable: Script transitions to "mark PR ready" phase instead of task execution
  - Evidence: Create plan with all tasks checked, verify script outputs message about completing PR
  - Steps:
    - [ ] Check if any uncompleted tasks remain
    - [ ] Transition to completion phase when none remain

---

## Steel Thread 8: Claude Code Invocation for Tasks

Invokes Claude Code interactively to implement tasks.

- [ ] **Task 8.1: Script invokes Claude Code with implement-plan template**
  - TaskType: OUTCOME
  - Entrypoint: `workflow-scripts/implement-with-worktree.sh <test-idea-dir>` (with uncompleted task)
  - Observable: Claude Code is invoked interactively with correct template and task context
  - Evidence: Mock/capture Claude invocation, verify command includes template path and task information
  - Steps:
    - [ ] Build Claude Code command with `--prompt` using implement-plan.md template
    - [ ] Include current task context in prompt
    - [ ] Execute interactively (preserving stdin/stdout)

- [ ] **Task 8.2: Script verifies Claude exit code**
  - TaskType: OUTCOME
  - Entrypoint: `workflow-scripts/implement-with-worktree.sh <test-idea-dir>` (simulating Claude failure)
  - Observable: Script exits with error when Claude returns non-zero exit code
  - Evidence: Mock Claude to return exit code 1, verify script exits with error message
  - Steps:
    - [ ] Capture Claude exit code
    - [ ] Exit with clear error message if non-zero

- [ ] **Task 8.3: Script verifies HEAD advanced after Claude**
  - TaskType: OUTCOME
  - Entrypoint: `workflow-scripts/implement-with-worktree.sh <test-idea-dir>` (simulating Claude success without commit)
  - Observable: Script exits with error when HEAD unchanged after Claude invocation
  - Evidence: Mock Claude to exit 0 but create no commit, verify script detects and errors
  - Steps:
    - [ ] Record HEAD before Claude invocation
    - [ ] Compare HEAD after invocation
    - [ ] Error if unchanged

---

## Steel Thread 9: Push and Continue Loop

Pushes commits and continues to next task.

- [ ] **Task 9.1: Script pushes commit after successful task**
  - TaskType: OUTCOME
  - Entrypoint: `workflow-scripts/implement-with-worktree.sh <test-idea-dir>` (after successful Claude task)
  - Observable: New commit pushed to remote slice branch
  - Evidence: After script run, verify `git log origin/<slice-branch>` contains the new commit
  - Steps:
    - [ ] Execute `git push` to slice branch
    - [ ] Handle push failures appropriately

- [ ] **Task 9.2: Script continues to next task after push**
  - TaskType: OUTCOME
  - Entrypoint: `workflow-scripts/implement-with-worktree.sh <test-idea-dir>` (with multiple uncompleted tasks)
  - Observable: Script processes multiple tasks in sequence, not just the first one
  - Evidence: Set up plan with 2 tasks, mock Claude to create commits, verify both tasks attempted
  - Steps:
    - [ ] Implement task loop that continues until all tasks complete or error
    - [ ] Re-parse plan file after each task to find next uncompleted

---

## Steel Thread 10: PR Draft State Verification

Verifies PR remains in draft state before pushing.

- [ ] **Task 10.1: Script verifies PR is still draft before push**
  - TaskType: OUTCOME
  - Entrypoint: `workflow-scripts/implement-with-worktree.sh <test-idea-dir>` (with PR still in draft)
  - Observable: Push proceeds normally when PR is draft
  - Evidence: Create draft PR, run script, verify push succeeds
  - Steps:
    - [ ] Query PR state via `gh pr view --json isDraft`
    - [ ] Proceed with push if draft

- [ ] **Task 10.2: Script handles PR exiting draft unexpectedly**
  - TaskType: OUTCOME
  - Entrypoint: `workflow-scripts/implement-with-worktree.sh <test-idea-dir>` (where PR was marked ready externally)
  - Observable: Script creates new slice branch and draft PR, preserving unpushed commits
  - Evidence: Create draft PR, mark it ready externally, run script with local commits, verify new slice created
  - Steps:
    - [ ] Detect when PR is no longer draft
    - [ ] Preserve commits in integration branch
    - [ ] Reset old slice to match remote
    - [ ] Increment slice number and create new branch/PR

---

## Steel Thread 11: Feedback Detection

Detects new PR feedback (reviews, comments, failed checks).

- [ ] **Task 11.1: Script detects new review comments**
  - TaskType: OUTCOME
  - Entrypoint: `workflow-scripts/implement-with-worktree.sh <test-idea-dir>` (with new comments on PR)
  - Observable: Script identifies unprocessed comment IDs not in state file
  - Evidence: Add comment to PR, verify script detects it as new feedback
  - Steps:
    - [ ] Query PR comments via `gh api` or `gh pr view --json`
    - [ ] Compare comment IDs against state file
    - [ ] Identify new/unprocessed comments

- [ ] **Task 11.2: Script detects failed status checks**
  - TaskType: OUTCOME
  - Entrypoint: `workflow-scripts/implement-with-worktree.sh <test-idea-dir>` (with failed CI check)
  - Observable: Script identifies failed status checks as feedback requiring action
  - Evidence: Set up failing check on PR, verify script detects and reports it
  - Steps:
    - [ ] Query status checks via `gh pr checks` or API
    - [ ] Identify failed checks

---

## Steel Thread 12: Feedback Handling with Claude

Invokes Claude to address PR feedback.

- [ ] **Task 12.1: Create wt-handle-feedback.md prompt template**
  - TaskType: INFRA
  - Entrypoint: `cat prompt-templates/wt-handle-feedback.md`
  - Observable: Template file exists with appropriate structure for feedback handling context
  - Evidence: Verify file exists and contains placeholders for feedback content
  - Steps:
    - [ ] Create template with sections for feedback context, PR state, and instructions
    - [ ] Include placeholders for specific feedback content

- [ ] **Task 12.2: Script invokes Claude with feedback template**
  - TaskType: OUTCOME
  - Entrypoint: `workflow-scripts/implement-with-worktree.sh <test-idea-dir>` (with unprocessed feedback)
  - Observable: Claude invoked with wt-handle-feedback.md template including feedback content
  - Evidence: Mock Claude invocation, verify template and feedback content passed correctly
  - Steps:
    - [ ] Build prompt with feedback template and actual feedback content
    - [ ] Invoke Claude interactively
    - [ ] Update state file with processed feedback IDs after handling

---

## Steel Thread 13: Main Branch Advancement Handling

Detects and handles main branch advancing.

- [ ] **Task 13.1: Script detects main branch advancement**
  - TaskType: OUTCOME
  - Entrypoint: `workflow-scripts/implement-with-worktree.sh <test-idea-dir>` (where main advanced)
  - Observable: Script detects that main has new commits since integration branch was created
  - Evidence: Advance main after creating integration branch, verify script detects the change
  - Steps:
    - [ ] Compare main HEAD with integration branch base
    - [ ] Identify when main has advanced

- [ ] **Task 13.2: Script auto-rebases on clean main advancement**
  - TaskType: OUTCOME
  - Entrypoint: `workflow-scripts/implement-with-worktree.sh <test-idea-dir>` (with non-conflicting main changes)
  - Observable: Integration branch rebased onto new main, slice branch updated
  - Evidence: Advance main with non-conflicting changes, verify rebase succeeds and branches updated
  - Steps:
    - [ ] Attempt `git rebase main` on integration branch
    - [ ] Update slice branch after successful rebase
    - [ ] Push updated branches

- [ ] **Task 13.3: Script pauses on rebase conflicts**
  - TaskType: OUTCOME
  - Entrypoint: `workflow-scripts/implement-with-worktree.sh <test-idea-dir>` (with conflicting main changes)
  - Observable: Script pauses, displays conflict message, waits for user resolution
  - Evidence: Create conflicting changes on main, verify script pauses with clear message
  - Steps:
    - [ ] Detect rebase conflict
    - [ ] Display clear message about conflicts
    - [ ] Pause execution (or exit with instructions to resume)

---

## Steel Thread 14: Completion and PR Ready

Marks PR ready and enters polling loop when all tasks complete.

- [ ] **Task 14.1: Script marks PR ready when all tasks complete**
  - TaskType: OUTCOME
  - Entrypoint: `workflow-scripts/implement-with-worktree.sh <test-idea-dir>` (with all tasks complete)
  - Observable: PR transitioned from draft to ready for review via `gh pr ready`
  - Evidence: Complete all tasks, verify PR is no longer draft
  - Steps:
    - [ ] Execute `gh pr ready` when no uncompleted tasks remain
    - [ ] Log transition message

- [ ] **Task 14.2: Script polls for feedback after marking ready**
  - TaskType: OUTCOME
  - Entrypoint: `workflow-scripts/implement-with-worktree.sh <test-idea-dir>` (in polling phase)
  - Observable: Script checks for feedback every 60 seconds, displays polling status
  - Evidence: Enter polling phase, verify script outputs polling messages with timing
  - Steps:
    - [ ] Implement 60-second polling loop
    - [ ] Check for new feedback on each iteration
    - [ ] Display countdown/status between polls

- [ ] **Task 14.3: Script handles feedback during polling**
  - TaskType: OUTCOME
  - Entrypoint: `workflow-scripts/implement-with-worktree.sh <test-idea-dir>` (polling, with new feedback)
  - Observable: New feedback during polling triggers Claude invocation same as during task execution
  - Evidence: Add feedback during polling phase, verify Claude invoked to handle it
  - Steps:
    - [ ] Reuse feedback detection and handling from task execution phase
    - [ ] Continue polling after handling feedback

---

## Steel Thread 15: PR Merge/Close Detection and Exit

Detects PR merge or close and exits appropriately.

- [ ] **Task 15.1: Script detects PR merged and exits**
  - TaskType: OUTCOME
  - Entrypoint: `workflow-scripts/implement-with-worktree.sh <test-idea-dir>` (polling, PR gets merged)
  - Observable: Script exits with success when PR is merged
  - Evidence: Merge PR during polling, verify script exits cleanly with success message
  - Steps:
    - [ ] Check PR state on each poll iteration
    - [ ] Exit with success when PR is merged

- [ ] **Task 15.2: Script detects PR closed and exits**
  - TaskType: OUTCOME
  - Entrypoint: `workflow-scripts/implement-with-worktree.sh <test-idea-dir>` (polling, PR gets closed)
  - Observable: Script exits when PR is closed (without merge)
  - Evidence: Close PR during polling, verify script exits with appropriate message
  - Steps:
    - [ ] Detect closed (not merged) state
    - [ ] Exit with informational message

---

## Steel Thread 16: Cleanup on Exit

Performs optional cleanup when --cleanup flag provided.

- [ ] **Task 16.1: Script skips cleanup by default**
  - TaskType: OUTCOME
  - Entrypoint: `workflow-scripts/implement-with-worktree.sh <test-idea-dir>` (PR merged, no --cleanup)
  - Observable: Worktree and local branches remain after script exit
  - Evidence: Run without --cleanup flag, verify worktree and branches still exist
  - Steps:
    - [ ] Default cleanup behavior is no-op

- [ ] **Task 16.2: Script removes worktree with --cleanup flag**
  - TaskType: OUTCOME
  - Entrypoint: `workflow-scripts/implement-with-worktree.sh <test-idea-dir> --cleanup` (PR merged)
  - Observable: Worktree directory removed after PR merged
  - Evidence: Run with --cleanup, verify worktree directory no longer exists
  - Steps:
    - [ ] Execute `git worktree remove` when cleanup requested
    - [ ] Handle case where worktree has uncommitted changes

- [ ] **Task 16.3: Script deletes local branches with --cleanup flag**
  - TaskType: OUTCOME
  - Entrypoint: `workflow-scripts/implement-with-worktree.sh <test-idea-dir> --cleanup` (PR merged)
  - Observable: Local integration and slice branches deleted after cleanup
  - Evidence: Run with --cleanup, verify branches no longer in `git branch --list`
  - Steps:
    - [ ] Delete integration branch
    - [ ] Delete all slice branches for this idea
    - [ ] Do not delete remote branches (GitHub handles via PR)

---

## Steel Thread 17: Interrupt Handling

Handles Ctrl+C gracefully.

- [ ] **Task 17.1: Script handles Ctrl+C cleanly**
  - TaskType: OUTCOME
  - Entrypoint: `workflow-scripts/implement-with-worktree.sh <test-idea-dir>` (interrupted with Ctrl+C)
  - Observable: Script exits cleanly without corrupting state file or leaving partial git operations
  - Evidence: Send SIGINT during execution, verify state file valid and git state consistent
  - Steps:
    - [ ] Install signal handler for SIGINT
    - [ ] Ensure state file is written atomically (write to temp, rename)
    - [ ] Exit with appropriate message

---

## Summary

This plan covers 17 steel threads with 34 tasks implementing the complete `implement-with-worktree.sh` workflow:

1. **Project Setup**: Python venv infrastructure and CLI entry point
2. **Idea Validation**: File existence and commit status checks
3. **Integration Branch**: Create/reuse integration branch
4. **Worktree**: Create/reuse worktree directory
5. **Slice and PR**: Create slice branch and Draft PR
6. **State File**: Initialize and manage persistent state
7. **Task Parsing**: Identify uncompleted tasks from plan
8. **Claude Invocation**: Run Claude for task implementation
9. **Push Loop**: Push commits and continue to next task
10. **Draft Verification**: Verify PR draft state before push
11. **Feedback Detection**: Detect reviews, comments, failed checks
12. **Feedback Handling**: Invoke Claude for feedback
13. **Main Advancement**: Detect and handle main branch changes
14. **Completion**: Mark PR ready and poll for feedback
15. **Merge Detection**: Detect PR merge/close and exit
16. **Cleanup**: Optional cleanup of worktree and branches
17. **Interrupt Handling**: Clean Ctrl+C handling
