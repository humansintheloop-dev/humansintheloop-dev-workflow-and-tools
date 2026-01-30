# Implementation Plan: implement-with-worktree

## Instructions for Coding Agent

- **IMPORTANT**: Use simple commands that you have permission to execute. Avoid complex commands that may fail due to permission issues.
- **ALWAYS** Use the `idea-to-code:plan-tracking` skill to track task completion
- **ALWAYS** Write code using TDD:
  - Use the `idea-to-code:tdd` skill when implementing code
  - NEVER write production code without first writing a failing test
  - Before using the Write tool on any production file, ask: "Do I have a failing test for this?" If not, write the test first.
  - When building something that requires scripting, never run scripts or ad-hoc commands that modify state directly. Always update the test script first, then run the test script.
  - When task direction changes mid-implementation, return to TDD PLANNING state and write a test first
- **ALWAYS** after completing a task, when tests pass and the task has been marked complete, commit the changes.

---

## Testing Strategy

### Test Location and Organization

- Tests live in `tests/workflow-scripts/`
- Use pytest markers to distinguish test types:
  - `@pytest.mark.unit` - Fast unit tests (no external dependencies)
  - `@pytest.mark.integration` - Slower tests requiring git/GitHub

### Unit Tests

Unit tests with pytest for pure Python functions:
- State management (load, save, update)
- Task parsing from plan files
- Branch name generation and sanitization
- Command construction (verify correct arguments without executing)

### Integration Tests

Integration tests use real repositories:

| Component | Approach |
|-----------|----------|
| Git operations | Real local test repository |
| GitHub operations | Real GitHub repository (created per test session, deleted at end) |
| Shell scripts | Tested indirectly via Python integration tests |
| Claude invocations | Mocked (verify command construction, simulate success/failure outcomes) |

### Test Data

- Use `tests/kafka-security-poc` as the test idea directory
- Test repository created fresh per test session for isolation

### Test Repository Initialization

When creating the test GitHub repository, the test setup must:
1. Copy `config-files/CLAUDE.md` to the repo root as `CLAUDE.md`
2. Copy `config-files/settings.local.json` to `.claude/settings.local.json`
3. Add "git commit" to the allowed permissions in settings

### Running Tests

```bash
# Run all tests
pytest tests/workflow-scripts/

# Run only fast unit tests
pytest tests/workflow-scripts/ -m unit

# Run integration tests (requires GitHub auth)
pytest tests/workflow-scripts/ -m integration
```

---

## Steel Thread 1: Project Setup and CLI Skeleton

Set up the Python venv infrastructure, basic CLI structure, and test framework.

- [x] **Task 1.1: Python venv helper bootstraps virtual environment**
  - [x] Create `workflow-scripts/_python_helper.sh` with `ensure_venv` and `run_python` functions
  - [x] Create `workflow-scripts/requirements.txt` with pytest as initial dependency
  - [x] Create `workflow-scripts/.gitignore` to exclude `.venv/`
  - [x] Verify: sourcing helper and calling `ensure_venv` creates `.venv/` directory

- [x] **Task 1.2: CLI accepts idea-directory argument and --cleanup flag**
  - [x] Create `workflow-scripts/implement-with-worktree.sh` that sources helper and invokes Python
  - [x] Create `workflow-scripts/implement-with-worktree.py` with argument parsing (argparse)
  - [x] Script exits with error if no idea-directory provided
  - [x] Script accepts optional `--cleanup` flag
  - [x] Verify: `./implement-with-worktree.sh` shows usage, `./implement-with-worktree.sh some/path` runs without argument error

---

## Steel Thread 2: Idea Validation and State Management

Validate the idea directory structure and manage persistent state.

- [ ] **Task 2.1: Script validates idea directory exists**
  - [ ] Exit with clear error message if directory does not exist
  - [ ] Extract idea-name from directory path (last component)
  - [ ] Verify: running with non-existent path shows "directory not found" error

- [ ] **Task 2.2: Script validates required idea files exist**
  - [ ] Check for `*-idea.md`, `*-discussion.md`, `*-spec.md`, `*-plan.md`
  - [ ] Exit with clear error listing missing files
  - [ ] Verify: running with incomplete idea directory shows which files are missing

- [ ] **Task 2.3: Script validates idea files are committed to Git**
  - [ ] Use `git status --porcelain` to check for uncommitted changes to idea files
  - [ ] Exit with error message if files have uncommitted changes
  - [ ] Verify: uncommitted changes to idea files trigger error

- [ ] **Task 2.4: State file initializes if not exists and loads if exists**
  - [ ] State file location: `<idea-directory>/<idea-name>-wt-state.json`
  - [ ] Initialize with: `{"slice_number": 1, "processed_comment_ids": [], "processed_review_ids": []}`
  - [ ] Load existing state file and validate JSON structure
  - [ ] Provide functions to update and save state
  - [ ] Verify: first run creates state file, subsequent run loads it

---

## Steel Thread 3: Git Infrastructure Setup

Create or reuse integration branch, worktree, and slice branch.

- [ ] **Task 3.1: Integration branch created if not exists, reused if exists**
  - [ ] Branch name: `idea/<idea-name>/integration`
  - [ ] Create from current HEAD if branch doesn't exist
  - [ ] Detect and reuse if branch already exists
  - [ ] Verify: first run creates branch, second run reuses it

- [ ] **Task 3.2: Worktree created if not exists, reused if exists**
  - [ ] Worktree path: `../<repo-name>-wt-<idea-name>`
  - [ ] Create worktree from integration branch if doesn't exist
  - [ ] Detect and reuse if worktree already exists
  - [ ] Change working directory to worktree for subsequent operations
  - [ ] Verify: first run creates worktree, second run reuses it

- [ ] **Task 3.3: Slice branch created with correct naming pattern**
  - [ ] Branch name: `idea/<idea-name>/<nn>-<slice-name>` where nn is zero-padded slice number
  - [ ] Derive slice-name from first task in plan (sanitized for branch name)
  - [ ] Create from integration branch if doesn't exist
  - [ ] Checkout slice branch in worktree
  - [ ] Verify: slice branch created with correct format (e.g., `idea/my-feature/01-project-setup`)

---

## Steel Thread 4: GitHub Draft PR Management

Create or reuse GitHub Draft PR for the slice branch.

- [ ] **Task 4.1: Draft PR created if not exists, reused if exists**
  - [ ] Use `gh pr list` to check for existing PR for slice branch
  - [ ] Use `gh pr create --draft` to create new Draft PR if none exists
  - [ ] PR title derived from slice name
  - [ ] PR body references idea directory and current slice
  - [ ] Store PR number in state or detect from `gh pr list`
  - [ ] Verify: first run creates Draft PR, second run reuses it

- [ ] **Task 4.2: Detect PR Draft state before push operations**
  - [ ] Use `gh pr view` to check if PR is still in Draft state
  - [ ] Return boolean indicating Draft status
  - [ ] Verify: function correctly identifies Draft vs Ready PRs

---

## Steel Thread 5: Task Parsing and Execution Core

Parse tasks from plan file and execute with Claude Code.

- [ ] **Task 5.1: Parse uncompleted tasks from plan file**
  - [ ] Read plan file from idea directory
  - [ ] Extract tasks matching pattern `- [ ]` (unchecked checkboxes)
  - [ ] Return list of task descriptions in order
  - [ ] Skip already-completed tasks (matching `- [x]`)
  - [ ] Verify: correctly parses mix of completed and uncompleted tasks

- [ ] **Task 5.2: Invoke Claude Code interactively for task**
  - [ ] Build Claude command with `implement-plan.md` template
  - [ ] Pass current task context to Claude
  - [ ] Run Claude interactively (not capturing output, user sees everything)
  - [ ] Capture exit code
  - [ ] Verify: Claude invocation command is correctly formed

- [ ] **Task 5.3: Verify task success via exit code and HEAD advancement**
  - [ ] Record HEAD before Claude invocation
  - [ ] After Claude exits, compare HEAD to recorded value
  - [ ] Success requires: exit code 0 AND HEAD advanced
  - [ ] Display clear error message on failure
  - [ ] Exit script if verification fails
  - [ ] Verify: detects both exit code failures and no-commit failures

- [ ] **Task 5.4: Push commit to slice branch after successful task**
  - [ ] Verify PR still in Draft state before pushing
  - [ ] Push current HEAD to slice branch
  - [ ] Handle push failures gracefully
  - [ ] Verify: commit pushed to remote slice branch

---

## Steel Thread 6: Feedback Handling

Detect and handle PR feedback (reviews, comments, status checks).

- [ ] **Task 6.1: Create wt-handle-feedback.md prompt template**
  - [ ] Create `prompt-templates/wt-handle-feedback.md`
  - [ ] Template receives: PR URL, feedback content, feedback type
  - [ ] Instructions for Claude to address feedback and commit fix
  - [ ] Verify: template file exists with required placeholders

- [ ] **Task 6.2: Detect new review comments and reviews**
  - [ ] Use `gh api` to fetch PR comments and reviews
  - [ ] Compare IDs against `processed_comment_ids` and `processed_review_ids` in state
  - [ ] Return list of new (unprocessed) feedback items
  - [ ] Verify: correctly identifies new vs already-processed feedback

- [ ] **Task 6.3: Detect failed status checks**
  - [ ] Use `gh pr checks` to get status check results
  - [ ] Identify failed checks
  - [ ] Treat failures as feedback requiring handling
  - [ ] Verify: correctly detects failed status checks

- [ ] **Task 6.4: Handle feedback with Claude using feedback template**
  - [ ] Invoke Claude with `wt-handle-feedback.md` template
  - [ ] Pass feedback content and context
  - [ ] Verify success (exit code + HEAD advanced)
  - [ ] Push fix commit
  - [ ] Update state with processed feedback IDs
  - [ ] Verify: feedback triggers Claude invocation and state update

---

## Steel Thread 7: Main Branch Advancement

Detect and handle when main branch advances during execution.

- [ ] **Task 7.1: Detect when main branch has advanced**
  - [ ] Track main branch HEAD at start of execution
  - [ ] After each task, fetch and compare current main HEAD
  - [ ] Return boolean indicating whether main has new commits
  - [ ] Verify: correctly detects main advancement

- [ ] **Task 7.2: Auto-rebase integration branch when rebase is clean**
  - [ ] Attempt `git rebase main` on integration branch
  - [ ] If successful, update slice branch to track rebased integration
  - [ ] Force-push slice branch after rebase
  - [ ] Verify: clean rebase completes without user intervention

- [ ] **Task 7.3: Pause and notify user when rebase has conflicts**
  - [ ] Detect rebase conflict (non-zero exit from rebase)
  - [ ] Abort the rebase attempt
  - [ ] Display clear message explaining the conflict
  - [ ] Pause execution (wait for user input or exit)
  - [ ] Verify: conflict triggers pause with clear message

---

## Steel Thread 8: Completion and Polling

Handle completion of all tasks and poll for feedback until PR is merged/closed.

- [ ] **Task 8.1: Mark PR ready for review when all tasks complete**
  - [ ] Detect when no uncompleted tasks remain in plan
  - [ ] Run `gh pr ready` to convert Draft to Ready
  - [ ] Display message indicating PR is ready for review
  - [ ] Verify: PR transitions from Draft to Ready

- [ ] **Task 8.2: Poll for feedback every 60 seconds after marking ready**
  - [ ] Enter polling loop after marking PR ready
  - [ ] Check for new feedback (reviews, comments, checks) each iteration
  - [ ] Handle new feedback with Claude (same as during task execution)
  - [ ] Display countdown/status during wait
  - [ ] Verify: polling loop runs at correct interval

- [ ] **Task 8.3: Exit when PR is merged or closed**
  - [ ] Check PR state via `gh pr view` during each poll
  - [ ] Exit with success message when PR is merged
  - [ ] Exit with message when PR is closed (not merged)
  - [ ] Verify: script exits cleanly on PR merge

---

## Steel Thread 9: Cleanup

Optional cleanup of worktree and local branches.

- [ ] **Task 9.1: Remove worktree when --cleanup flag provided and PR complete**
  - [ ] Only perform cleanup if `--cleanup` flag was provided
  - [ ] Only cleanup after PR is merged or closed
  - [ ] Run `git worktree remove <worktree-path>`
  - [ ] Verify: worktree directory removed

- [ ] **Task 9.2: Delete local branches when --cleanup flag provided**
  - [ ] Delete local integration branch
  - [ ] Delete local slice branch(es)
  - [ ] Do not delete remote branches (GitHub handles via PR)
  - [ ] Verify: local branches deleted, remote branches remain

---

## Steel Thread 10: Slice Rollover on Unexpected PR State Change

Handle edge case where PR exits Draft state unexpectedly.

- [ ] **Task 10.1: Detect PR exited Draft state before push**
  - [ ] Before each push, check PR is still Draft
  - [ ] If not Draft and there are unpushed commits, trigger rollover
  - [ ] Verify: correctly detects unexpected Ready state with local commits

- [ ] **Task 10.2: Preserve unpushed commits and create new slice**
  - [ ] Record unpushed commits in integration branch
  - [ ] Reset old slice branch to match remote (discard local-only changes on that branch)
  - [ ] Increment slice number in state
  - [ ] Create new slice branch from integration (includes preserved commits)
  - [ ] Create new Draft PR for new slice
  - [ ] Push commits to new slice
  - [ ] Verify: no commits lost, work continues on new slice

---

## Steel Thread 11: Interrupt Handling and Resumability

Ensure clean interrupt handling and seamless resume after restart.

- [ ] **Task 11.1: Handle Ctrl+C gracefully**
  - [ ] Register signal handler for SIGINT
  - [ ] On interrupt, save current state and exit cleanly
  - [ ] Do not leave Git in inconsistent state (abort any in-progress operations)
  - [ ] Verify: Ctrl+C exits cleanly without corrupting state

- [ ] **Task 11.2: Resume from correct position after restart**
  - [ ] On startup, load state file
  - [ ] Detect existing worktree, branches, PR and reuse
  - [ ] Start from first uncompleted task in plan
  - [ ] Do not reprocess already-handled feedback
  - [ ] Verify: restart after interrupt continues from correct point

---

## Change History

### 2026-01-30: Added Testing Strategy section

Added comprehensive testing strategy based on discussion:
- Unit tests with pytest for pure Python functions
- Integration tests using real git repositories
- GitHub integration tests using real GitHub repo (created per session, deleted at end)
- Shell scripts tested indirectly through Python tests
- Claude invocations mocked (verify command, simulate outcomes)
- Tests located in `tests/workflow-scripts/`
- Pytest markers (`unit`, `integration`) for selective test execution
- `tests/kafka-security-poc` as test idea directory
- Test repo initialization: copy `config-files/CLAUDE.md` and `config-files/settings.local.json`, add "git commit" permission
