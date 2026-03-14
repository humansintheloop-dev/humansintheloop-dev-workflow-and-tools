# Platform Capability Specification: implement-with-worktree.sh

## Purpose and Context

This specification defines `implement-with-worktree.sh`, a workflow automation script that implements Git worktree and GitHub Draft PR-based development. The script orchestrates the complete lifecycle of implementing a development plan: from creating Git infrastructure (integration branches, worktrees, slice branches) through task execution with Claude Code, PR feedback handling, and optional cleanup.

### Background

The existing `implement-plan.sh` script executes plan tasks sequentially but lacks integration with Git worktree workflows and PR lifecycle management. The worktree-based workflow (documented in `wt-pr-based-development-workflow.md`) provides benefits including:

- Isolated development environments via Git worktrees
- Incremental review through Draft PRs and slices
- Continuous integration with `main` branch advances
- Structured feedback handling from PR reviews and CI

This script automates these manual workflow steps while preserving human oversight through interactive Claude Code sessions.

### Relationship to Existing Scripts

- **Parallel implementation** to `implement-plan.sh` (not a wrapper or replacement)
- Shares `_helper.sh` conventions for consistency
- Reuses existing `implement-plan.md` prompt template for task implementation
- Introduces one new prompt template for feedback handling

---

## Consumers

| Consumer | Usage |
|----------|-------|
| Individual developers | Primary users running the script to implement feature plans |
| CI/automation systems | Not a direct consumer; script is interactive-only |
| Code reviewers | Indirect consumers; receive well-structured Draft PRs for review |

---

## Capabilities and Behaviors

### 1. Setup and Initialization

The script performs idempotent setup, detecting and reusing existing infrastructure:

| Capability | Behavior |
|------------|----------|
| Idea file validation | Verify idea files (idea, discussion, spec, plan) are committed before proceeding |
| Integration branch | Create `idea/<idea-name>/integration` branch from current HEAD, or reuse if exists |
| Worktree creation | Create worktree at `../<repo>-wt-<idea-name>`, or reuse if exists |
| Slice branch | Create `idea/<idea-name>/<nn>-<slice-name>` branch, or reuse current slice |
| Draft PR | Create GitHub Draft PR for slice branch, or reuse existing |
| State file | Initialize or load `<idea>-wt-state.json` in idea directory |

### 2. Task Execution Loop

For each uncompleted task in the plan file (tasks with unchecked `- [ ]` markers):

| Step | Behavior |
|------|----------|
| 1. Invoke Claude | Run Claude Code interactively with `implement-plan.md` template, fresh session |
| 2. Verify success | Check Claude exit code = 0 AND HEAD advanced (new commit created) |
| 3. Handle failure | Display error message and exit script if verification fails |
| 4. Verify Draft state | Before pushing, confirm PR is still in Draft state |
| 5. Push commit | Push to slice branch |
| 6. Check feedback | Query GitHub for new reviews, comments, or failed status checks |
| 7. Handle feedback | If new feedback exists, invoke Claude with `wt-handle-feedback.md` template |
| 8. Check main | Detect if `main` has advanced since last check |
| 9. Rebase if needed | Auto-rebase if clean; pause and notify user if conflicts |
| 10. Continue | Proceed to next uncompleted task |

### 3. Slice Management

| Scenario | Behavior |
|----------|----------|
| Normal operation | Continue on single slice for entire plan |
| PR exits Draft unexpectedly | Preserve unpushed commits in integration branch, reset old slice to match remote, create new slice branch and PR |
| Slice naming | Derive from Steel Thread heading and current task (e.g., `01-project-setup`) |

### 4. Feedback Handling

| Feedback Type | Detection | Handling |
|---------------|-----------|----------|
| Review comments | New comment IDs not in state file | Invoke Claude with feedback template |
| Inline comments | New comment IDs not in state file | Invoke Claude with feedback template |
| "Changes Requested" reviews | New review IDs not in state file | Invoke Claude with feedback template |
| Failed status checks | Check status via `gh` CLI | Invoke Claude with feedback template |

Processed feedback is tracked by storing comment/review IDs in the state file.

### 5. Main Branch Advancement

| Scenario | Behavior |
|----------|----------|
| Main advanced, clean rebase | Auto-rebase integration branch onto main, update slice branch |
| Main advanced, conflicts | Pause execution, notify user, wait for manual resolution |
| Main unchanged | Continue normally |

### 6. Completion Behavior

| Phase | Behavior |
|-------|----------|
| All tasks complete | Mark PR ready for review (`gh pr ready`) |
| Polling loop | Poll GitHub every 60 seconds for new feedback |
| Feedback during polling | Handle with Claude (same as during task execution) |
| PR merged | Exit script (perform cleanup if `--cleanup` flag) |
| PR closed | Exit script (perform cleanup if `--cleanup` flag) |

### 7. Cleanup (Optional)

When `--cleanup` flag is provided and PR is merged/closed:

| Action | Details |
|--------|---------|
| Remove worktree | `git worktree remove <worktree-path>` |
| Delete local branches | Delete integration and slice branches |
| Remote branches | Not deleted (GitHub handles via PR merge) |

---

## High-Level APIs and Contracts

### Command-Line Interface

```
implement-with-worktree.sh <idea-directory> [--cleanup]
```

| Argument | Required | Description |
|----------|----------|-------------|
| `<idea-directory>` | Yes | Path to idea directory (e.g., `docs/features/my-feature`) |
| `--cleanup` | No | Perform cleanup after PR is merged or closed |

### State File Contract

Location: `<idea-directory>/<idea-name>-wt-state.json`

```json
{
  "slice_number": 1,
  "processed_comment_ids": ["IC_abc123", "IC_def456"],
  "processed_review_ids": ["PRR_xyz789"]
}
```

| Field | Type | Description |
|-------|------|-------------|
| `slice_number` | integer | Current slice number (for `<nn>` in branch names) |
| `processed_comment_ids` | string[] | GitHub comment IDs already handled |
| `processed_review_ids` | string[] | GitHub review IDs already handled |

### Branch Naming Contract

| Branch Type | Pattern | Example |
|-------------|---------|---------|
| Integration | `idea/<idea-name>/integration` | `idea/wt-pr-based-development/integration` |
| Slice | `idea/<idea-name>/<nn>-<slice-name>` | `idea/wt-pr-based-development/01-project-setup` |

### Worktree Location Contract

| Item | Pattern | Example |
|------|---------|---------|
| Worktree path | `../<repo-name>-wt-<idea-name>` | `../genai-development-workflow-wt-wt-pr-based-development` |

### Prompt Template Contract

| Template | Location | Purpose |
|----------|----------|---------|
| Task implementation | `prompt-templates/implement-plan.md` | Existing template for implementing plan tasks |
| Feedback handling | `prompt-templates/wt-handle-feedback.md` | New template for addressing PR feedback |

---

## Non-Functional Requirements

### Reliability

| Requirement | Specification |
|-------------|---------------|
| Idempotency | Script can be interrupted and reinvoked; detects and reuses existing Git/GitHub state |
| Failure handling | On Claude failure (bad exit code or no commit), display error and exit cleanly |
| State persistence | Minimal state file survives script restarts; Git/GitHub are primary state sources |

### Observability

| Requirement | Specification |
|-------------|---------------|
| Progress indication | Display current task being executed, feedback being handled |
| Error messages | Clear messages when verification fails, conflicts occur, or PR state changes |
| Polling status | Indicate when polling for feedback and time until next check |

### Interactivity

| Requirement | Specification |
|-------------|---------------|
| Human oversight | All Claude invocations are interactive (user can interrupt/correct) |
| No background execution | Script runs in foreground; user must keep terminal open |
| Ctrl+C handling | Clean exit on user interrupt |

### Performance

| Requirement | Specification |
|-------------|---------------|
| Polling interval | 60 seconds between GitHub API calls during feedback wait |
| API efficiency | Use `gh` CLI for GitHub operations (handles auth, rate limiting) |

---

## Scenarios and Workflows

### Primary End-to-End Scenario: Implement Feature Plan with Review Feedback

**Actors:** Developer, Code Reviewer (human), Claude Code

**Preconditions:**
- Idea directory exists with committed idea, discussion, spec, and plan files
- Plan file contains tasks with unchecked `- [ ]` markers
- Developer has `gh` CLI authenticated

**Flow:**

1. Developer runs `implement-with-worktree.sh docs/features/my-feature`
2. Script creates integration branch, worktree, slice branch, and Draft PR
3. Script identifies first uncompleted task from plan file
4. Script invokes Claude Code interactively to implement task
5. Developer observes Claude working, can interrupt if needed
6. Claude commits changes, script verifies success
7. Script pushes to slice branch
8. Script checks for PR feedback (none yet)
9. Script checks if main advanced (no)
10. Script proceeds to next task, repeats steps 4-9
11. After several tasks, reviewer adds comment to Draft PR
12. Script detects new comment on next feedback check
13. Script invokes Claude with feedback template to address comment
14. Claude commits fix, script pushes
15. All tasks complete; script runs `gh pr ready`
16. Script enters polling loop (60s interval)
17. Reviewer approves PR
18. Reviewer merges PR
19. Script detects PR merged, exits

**Postconditions:**
- All plan tasks marked complete
- PR merged to main
- Worktree and branches remain (no `--cleanup` flag)

---

### Scenario: Resume After Interruption

**Preconditions:**
- Script was previously interrupted mid-execution
- Worktree, integration branch, slice branch, and Draft PR exist
- Some tasks completed, some remaining

**Flow:**

1. Developer runs `implement-with-worktree.sh docs/features/my-feature`
2. Script detects existing worktree, reuses it
3. Script detects existing integration and slice branches, reuses them
4. Script detects existing Draft PR, reuses it
5. Script loads state file, knows which feedback was already processed
6. Script reads plan file, identifies uncompleted tasks
7. Script continues from first uncompleted task

**Postconditions:**
- Execution continues seamlessly from interruption point

---

### Scenario: Main Branch Advances with Clean Rebase

**Preconditions:**
- Script is running, some tasks completed
- Another developer merges unrelated PR to main

**Flow:**

1. Script pushes latest commit to slice branch
2. Script detects main has advanced
3. Script attempts rebase of integration branch onto main
4. Rebase succeeds (no conflicts)
5. Script updates slice branch
6. Script continues to next task

**Postconditions:**
- Integration and slice branches incorporate latest main changes
- No user intervention required

---

### Scenario: Main Branch Advances with Conflicts

**Preconditions:**
- Script is running, some tasks completed
- Another developer merges conflicting changes to main

**Flow:**

1. Script pushes latest commit to slice branch
2. Script detects main has advanced
3. Script attempts rebase of integration branch onto main
4. Rebase fails (conflicts detected)
5. Script displays conflict notification
6. Script pauses and waits for user to resolve conflicts manually
7. User resolves conflicts, signals script to continue (or restarts script)
8. Script resumes from current task

**Postconditions:**
- User resolved conflicts manually
- Script continues after resolution

---

### Scenario: PR Exits Draft State Unexpectedly

**Preconditions:**
- Script is running with Draft PR
- User has unpushed commits in worktree
- External actor marks PR as ready (unexpected)

**Flow:**

1. Claude commits new changes locally
2. Before pushing, script checks PR state
3. Script detects PR is no longer Draft
4. Script preserves unpushed commits in integration branch
5. Script resets old slice branch to match remote
6. Script increments slice number
7. Script creates new slice branch from integration
8. Script creates new Draft PR for new slice
9. Script pushes commits to new slice
10. Script continues with next task

**Postconditions:**
- Old slice preserved as-is (now Ready for review)
- New slice created for continued work
- No commits lost

---

### Scenario: Claude Fails to Create Commit

**Preconditions:**
- Script invokes Claude for a task
- Claude encounters issue and exits without committing

**Flow:**

1. Script invokes Claude Code for task
2. Claude runs but exits with error (or exits successfully but no commit)
3. Script checks exit code and HEAD position
4. Script detects failure (bad exit code or HEAD unchanged)
5. Script displays error message with details
6. Script exits

**Postconditions:**
- User informed of failure
- Can investigate and re-run script after fixing issue

---

### Scenario: Cleanup After Merge

**Preconditions:**
- All tasks complete, PR merged
- Script invoked with `--cleanup` flag

**Flow:**

1. Script detects PR is merged
2. Script removes worktree directory
3. Script deletes local integration branch
4. Script deletes local slice branch(es)
5. Script exits with success message

**Postconditions:**
- Worktree directory removed
- Local branches cleaned up
- Remote branches remain (handled by GitHub)

---

## Constraints and Assumptions

### Constraints

| Constraint | Rationale |
|------------|-----------|
| Interactive-only | Human oversight required; no headless/CI execution |
| Single concurrent execution | One script instance per idea; no parallel slice work |
| GitHub-only | Uses `gh` CLI; GitLab/Bitbucket not supported |
| Python 3.x | Script implemented in Python for cleaner state management and error handling |
| `gh` CLI with JSON output | Use `--json` flags and `gh api` for structured data; avoids fragile text parsing |

### Assumptions

| Assumption | Impact if False |
|------------|-----------------|
| `gh` CLI authenticated | Script fails on first GitHub operation |
| Idea files committed | Script errors with message to commit files |
| Plan file has standard format | Task parsing may fail; relies on `- [ ]` markers |
| Network connectivity | GitHub operations fail; script must handle gracefully |
| User has push access | Push operations fail |

---

## Acceptance Criteria

### Setup and Initialization

- [ ] Script creates integration branch if not exists
- [ ] Script reuses existing integration branch if exists
- [ ] Script creates worktree if not exists
- [ ] Script reuses existing worktree if exists
- [ ] Script creates slice branch with correct naming pattern
- [ ] Script creates Draft PR if not exists
- [ ] Script reuses existing Draft PR if exists
- [ ] Script errors with clear message if idea files not committed
- [ ] Script initializes state file if not exists
- [ ] Script loads existing state file if exists

### Task Execution

- [ ] Script identifies uncompleted tasks from plan file
- [ ] Script invokes Claude Code interactively for each task
- [ ] Script uses fresh Claude session per task
- [ ] Script verifies Claude exit code after each invocation
- [ ] Script verifies HEAD advanced after each invocation
- [ ] Script displays error and exits if verification fails
- [ ] Script pushes commit after successful task completion

### Feedback Handling

- [ ] Script detects new review comments via ID comparison
- [ ] Script detects new inline comments via ID comparison
- [ ] Script detects failed status checks
- [ ] Script invokes Claude with feedback template for new feedback
- [ ] Script updates state file with processed feedback IDs
- [ ] Script treats all feedback types uniformly (reviews, comments, checks)

### Main Branch Handling

- [ ] Script detects when main has advanced
- [ ] Script auto-rebases when rebase is clean
- [ ] Script pauses and notifies user when conflicts occur
- [ ] Script updates slice branch after successful rebase

### Slice Management

- [ ] Script detects when PR exits Draft state unexpectedly
- [ ] Script preserves unpushed commits when creating new slice
- [ ] Script creates new slice branch with incremented number
- [ ] Script creates new Draft PR for new slice

### Completion

- [ ] Script marks PR ready when all tasks complete
- [ ] Script polls for feedback every 60 seconds after marking ready
- [ ] Script continues handling feedback during polling
- [ ] Script exits when PR is merged
- [ ] Script exits when PR is closed

### Cleanup

- [ ] Script performs no cleanup by default
- [ ] Script removes worktree when `--cleanup` flag provided and PR merged/closed
- [ ] Script deletes local branches when `--cleanup` flag provided and PR merged/closed

### Resumability

- [ ] Script can be interrupted with Ctrl+C
- [ ] Script continues from correct task after restart
- [ ] Script does not reprocess already-handled feedback after restart
- [ ] Script reuses all existing Git/GitHub infrastructure after restart

---

## Artifacts to Create

| Artifact | Path | Description |
|----------|------|-------------|
| Python helper | `workflow-scripts/_python_helper.sh` | Shared venv bootstrap logic |
| Requirements | `workflow-scripts/requirements.txt` | Python dependencies |
| Entry script | `workflow-scripts/implement-with-worktree.sh` | Bash wrapper that invokes Python |
| Main logic | `workflow-scripts/implement-with-worktree.py` | Python implementation |
| Feedback template | `prompt-templates/wt-handle-feedback.md` | Prompt template for addressing PR feedback |

### Python Environment Management

The workflow scripts use a shared Python virtual environment with auto-bootstrap:

```
workflow-scripts/
├── _python_helper.sh      # Shared venv bootstrap logic
├── .venv/                 # Auto-created (in .gitignore)
├── requirements.txt       # Python dependencies
├── implement-with-worktree.sh
├── implement-with-worktree.py
└── (future .sh/.py pairs)
```

**`_python_helper.sh`** provides:
- `ensure_venv` - Creates venv and installs dependencies if missing
- `run_python` - Ensures venv exists, then runs Python script with arguments

**Entry scripts** source the helper and delegate to Python:
```bash
#!/usr/bin/env bash
source "$(dirname "$0")/_python_helper.sh"
run_python "$(dirname "$0")/implement-with-worktree.py" "$@"
```

**User experience**: Clone repo, run script, venv is created automatically on first run.

---

## Out of Scope

The following are explicitly out of scope for this capability:

- Parallel slice execution (multiple slices simultaneously)
- GitLab or Bitbucket support
- Headless/CI execution mode
- Automatic conflict resolution
- Remote branch cleanup
- Custom polling intervals (hardcoded to 60s)
- Task filtering (all tasks executed in order)

---

## Change History

### 2026-01-30: Updated branch naming conventions

Changed branch naming to group all idea-related branches under `idea/<idea-name>/` prefix:
- Integration: `integration/<idea-name>` → `idea/<idea-name>/integration`
- Slice: `plan/<idea-name>/<nn>-<slice-name>` → `idea/<idea-name>/<nn>-<slice-name>`

Rationale: Better organization by grouping all branches for an idea under a common prefix.

### 2026-01-30: Changed implementation to Python with Bash wrapper

Implementation split into two files:
- `implement-with-worktree.sh` - Bash entry point (thin wrapper)
- `implement-with-worktree.py` - Python implementation (main logic)

Rationale: Estimated ~400-500 lines of pure bash with complex JSON state management via jq. Python provides cleaner state file handling, better error handling, and easier testing. Bash wrapper maintains consistency with other workflow scripts.

### 2026-01-30: Added Python venv auto-bootstrap

Added `_python_helper.sh` and `requirements.txt` for shared Python environment management:
- Venv auto-created on first script run
- Shared across all Python workflow scripts
- Zero manual setup for users cloning the repo

Rationale: Support multiple Python scripts with minimal duplication and easy onboarding.

### 2026-01-30: Use `gh` CLI with JSON output

GitHub operations use `gh` CLI with `--json` flags and `gh api` for structured responses:
```python
# Example: list PRs with structured output
result = subprocess.run(
    ["gh", "pr", "list", "--json", "number,title,isDraft,headRefName"],
    capture_output=True, text=True
)
prs = json.loads(result.stdout)
```

Rationale: Leverages user's existing `gh auth` setup (no separate token configuration) while giving Python clean JSON to parse instead of fragile text output.
