# Idea: implement-with-worktree

Develop `workflow-scripts/implement-with-worktree.sh` (with Python backend) that implements Git/GitHub worktree and PR-based development as described in `wt-pr-based-development-workflow.md`.

## Overview

This script automates slice-based development using Git worktrees and GitHub Draft PRs. It takes an idea directory as input, creates the necessary Git infrastructure (integration branch, worktree, slice branch, Draft PR), then iterates over tasks in the plan file, invoking Claude Code to implement each one.

## Key Behaviors

### Setup and Resumability
- Takes idea directory as argument (e.g., `docs/features/wt-pr-based-development`)
- Verifies idea files are committed before creating branches/worktree
- Can be interrupted and reinvoked - checks for existing worktrees, branches, and PRs and reuses them
- Maintains minimal state file (`<idea>-wt-state.json`) in idea directory for comment ID tracking and slice number

### Slice Management
- Uses single slice for entire plan (branch: `idea/<idea-name>/<nn>-<slice-name>`)
- Slice names derived from Steel Thread heading and current task
- Creates new slice only when current PR exits Draft state unexpectedly
- When PR exits Draft with unpushed commits: preserves commits in integration branch, resets old slice to match remote, starts new slice

### Task Execution Loop
For each uncompleted task in the plan file:
1. Invoke Claude Code interactively (fresh session per task, using `implement-plan.md` template)
2. Verify success: check Claude exit code AND that HEAD advanced
3. If failure: display error and exit
4. Before pushing: verify PR is still in Draft state
5. Push commit to slice branch
6. Check for PR feedback (reviews, comments, failed status checks) - any new activity triggers handling
7. Check for main advancement - auto-rebase if clean, pause if conflicts
8. Continue to next task

### Feedback Handling
- Tracks processed feedback via comment IDs in state file
- Any new review, comment, or failed status check triggers Claude (new `wt-handle-feedback.md` template)
- Status check failures treated same as review comments

### Completion
- When all tasks complete: mark PR ready for review (`gh pr ready`)
- Poll for feedback every 60 seconds
- Continue handling feedback until PR is merged or closed
- Optional `--cleanup` flag: remove worktree and delete local branches on exit

## Command-Line Interface

```
implement-with-worktree.sh <idea-directory> [--cleanup]
```

- `<idea-directory>`: Path to idea directory (e.g., `docs/features/my-feature`)
- `--cleanup`: Perform cleanup (remove worktree, delete local branches) after PR is merged/closed

## New Artifacts Needed

- `workflow-scripts/_python_helper.sh` - shared venv bootstrap logic (reusable by future scripts)
- `workflow-scripts/requirements.txt` - Python dependencies
- `workflow-scripts/implement-with-worktree.sh` - bash entry point (sources helper, calls Python)
- `workflow-scripts/implement-with-worktree.py` - Python implementation (main logic)
- `prompt-templates/wt-handle-feedback.md` - prompt template for addressing PR feedback

## Important Constraints

- Claude Code must always be invoked interactively (human can interrupt and correct)
- Reuse existing `implement-plan.md` prompt template for task implementation
- Bash entry script calls Python for main logic (cleaner state management and error handling)
- Standalone script (not wrapper around `implement-plan.sh`)
