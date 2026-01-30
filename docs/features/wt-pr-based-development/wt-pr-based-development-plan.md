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

- [x] **Task 1.3: Integration test for CLI skeleton**
  - [x] Create test that runs `implement-with-worktree.sh` with no arguments and verifies usage output
  - [x] Create test that runs script with `--help` and verifies help text
  - [x] Verify: tests run the actual shell script and check exit codes/output

---

## Steel Thread 2: Idea Validation and State Management

Validate the idea directory structure and manage persistent state.

- [x] **Task 2.1: Script validates idea directory exists**
  - [x] Exit with clear error message if directory does not exist
  - [x] Extract idea-name from directory path (last component)
  - [x] Verify: running with non-existent path shows "directory not found" error

- [x] **Task 2.2: Script validates required idea files exist**
  - [x] Check for `*-idea.md`, `*-discussion.md`, `*-spec.md`, `*-plan.md`
  - [x] Exit with clear error listing missing files
  - [x] Verify: running with incomplete idea directory shows which files are missing

- [x] **Task 2.3: Script validates idea files are committed to Git**
  - [x] Use GitPython to check for uncommitted changes to idea files
  - [x] Exit with error message if files have uncommitted changes
  - [x] Verify: uncommitted changes to idea files trigger error

- [x] **Task 2.4: State file initializes if not exists and loads if exists**
  - [x] State file location: `<idea-directory>/<idea-name>-wt-state.json`
  - [x] Initialize with: `{"slice_number": 1, "processed_comment_ids": [], "processed_review_ids": []}`
  - [x] Load existing state file and validate JSON structure
  - [x] Provide functions to update and save state
  - [x] Verify: first run creates state file, subsequent run loads it

- [x] **Task 2.5: Integration test for idea validation**
  - [x] Create local test git repository with test idea directory
  - [x] Run script with non-existent directory, verify error message and exit code
  - [x] Run script with incomplete idea directory (missing files), verify error lists missing files
  - [x] Run script with uncommitted idea files, verify error message
  - [x] Run script with valid committed idea directory, verify state file created
  - [x] Verify: tests run actual script against real test repository

---

## Steel Thread 3: Git Infrastructure Setup

Create or reuse integration branch, worktree, and slice branch.

- [x] **Task 3.1: Integration branch created if not exists, reused if exists**
  - [x] Branch name: `idea/<idea-name>/integration`
  - [x] Create from current HEAD if branch doesn't exist
  - [x] Detect and reuse if branch already exists
  - [x] Verify: first run creates branch, second run reuses it

- [x] **Task 3.2: Worktree created if not exists, reused if exists**
  - [x] Worktree path: `../<repo-name>-wt-<idea-name>`
  - [x] Create worktree from integration branch if doesn't exist
  - [x] Detect and reuse if worktree already exists
  - [x] Change working directory to worktree for subsequent operations
  - [x] Verify: first run creates worktree, second run reuses it

- [x] **Task 3.3: Slice branch created with correct naming pattern**
  - [x] Branch name: `idea/<idea-name>/<nn>-<slice-name>` where nn is zero-padded slice number
  - [x] Derive slice-name from first task in plan (sanitized for branch name)
  - [x] Create from integration branch if doesn't exist
  - [x] Checkout slice branch in worktree
  - [x] Verify: slice branch created with correct format (e.g., `idea/my-feature/01-project-setup`)

- [x] **Task 3.4: Integration test for git infrastructure setup**
  - [x] Create local test git repository with valid idea directory
  - [x] Run script and verify integration branch `idea/<idea-name>/integration` exists
  - [x] Verify worktree directory created at `../<repo-name>-wt-<idea-name>`
  - [x] Verify slice branch created with correct pattern
  - [x] Run script again, verify branches and worktree are reused (not duplicated)
  - [x] Verify: tests run actual script and check git state with GitPython

---

## Steel Thread 4: GitHub Draft PR Management

Create or reuse GitHub Draft PR for the slice branch.

- [x] **Task 4.1: Draft PR created if not exists, reused if exists**
  - [x] Use `gh pr list` to check for existing PR for slice branch
  - [x] Use `gh pr create --draft` to create new Draft PR if none exists
  - [x] PR title derived from slice name
  - [x] PR body references idea directory and current slice
  - [x] Store PR number in state or detect from `gh pr list`
  - [x] Verify: first run creates Draft PR, second run reuses it

- [x] **Task 4.2: Detect PR Draft state before push operations**
  - [x] Use `gh pr view` to check if PR is still in Draft state
  - [x] Return boolean indicating Draft status
  - [x] Verify: function correctly identifies Draft vs Ready PRs

- [x] **Task 4.3: Integration test for GitHub PR management**
  - [x] Create test GitHub repository (use pytest fixture with cleanup)
  - [x] Run script with valid idea directory, verify Draft PR created on GitHub
  - [x] Verify PR title and body contain expected content
  - [x] Run script again, verify existing PR is reused (PR count unchanged)
  - [x] Verify: tests use real GitHub API via `gh` CLI

---

## Steel Thread 5: Task Parsing and Execution Core

Parse tasks from plan file and execute with Claude Code.

- [x] **Task 5.1: Parse uncompleted tasks from plan file**
  - [x] Read plan file from idea directory
  - [x] Extract tasks matching pattern `- [ ]` (unchecked checkboxes)
  - [x] Return list of task descriptions in order
  - [x] Skip already-completed tasks (matching `- [x]`)
  - [x] Verify: correctly parses mix of completed and uncompleted tasks

- [x] **Task 5.2: Invoke Claude Code interactively for task**
  - [x] Build Claude command with `implement-plan.md` template
  - [x] Pass current task context to Claude
  - [x] Run Claude interactively (not capturing output, user sees everything)
  - [x] Capture exit code
  - [x] Verify: Claude invocation command is correctly formed

- [x] **Task 5.3: Verify task success via exit code and HEAD advancement**
  - [x] Record HEAD before Claude invocation
  - [x] After Claude exits, compare HEAD to recorded value
  - [x] Success requires: exit code 0 AND HEAD advanced
  - [x] Display clear error message on failure
  - [x] Exit script if verification fails
  - [x] Verify: detects both exit code failures and no-commit failures

- [x] **Task 5.4: Push commit to slice branch after successful task**
  - [x] Verify PR still in Draft state before pushing
  - [x] Push current HEAD to slice branch
  - [x] Handle push failures gracefully
  - [x] Verify: commit pushed to remote slice branch

- [x] **Task 5.5: Integration test for task execution (with mocked Claude)**
  - [x] Create test repository with idea directory containing plan with uncompleted tasks
  - [x] Mock Claude invocation to simulate success (exit 0) and create a commit
  - [x] Run script and verify task is detected from plan
  - [x] Verify commit is pushed to slice branch on GitHub
  - [x] Verify: tests use real git/GitHub but mock Claude subprocess

---

## Steel Thread 6: Feedback Handling

Detect and handle PR feedback (reviews, comments, status checks).

- [x] **Task 6.1: Create wt-handle-feedback.md prompt template**
  - [x] Create `prompt-templates/wt-handle-feedback.md`
  - [x] Template receives: PR URL, feedback content, feedback type
  - [x] Instructions for Claude to address feedback and commit fix
  - [x] Verify: template file exists with required placeholders

- [x] **Task 6.2: Detect new review comments and reviews**
  - [x] Use `gh api` to fetch PR comments and reviews
  - [x] Compare IDs against `processed_comment_ids` and `processed_review_ids` in state
  - [x] Return list of new (unprocessed) feedback items
  - [x] Verify: correctly identifies new vs already-processed feedback

- [x] **Task 6.3: Detect failed status checks**
  - [x] Use `gh pr checks` to get status check results
  - [x] Identify failed checks
  - [x] Treat failures as feedback requiring handling
  - [x] Verify: correctly detects failed status checks

- [x] **Task 6.4: Handle feedback with Claude using feedback template**
  - [x] Invoke Claude with `wt-handle-feedback.md` template
  - [x] Pass feedback content and context
  - [x] Verify success (exit code + HEAD advanced)
  - [x] Push fix commit
  - [x] Update state with processed feedback IDs
  - [x] Verify: feedback triggers Claude invocation and state update

- [x] **Task 6.5: Integration test for feedback handling**
  - [x] Create test GitHub repository with PR that has review comments
  - [x] Run script with mocked Claude that creates fix commit
  - [x] Verify script detects new comments and invokes Claude with feedback template
  - [x] Verify processed comment IDs are saved to state file
  - [x] Run script again, verify same comments are not reprocessed
  - [x] Verify: tests use real GitHub PR with comments, mock Claude

---

## Steel Thread 7: Main Branch Advancement

Detect and handle when main branch advances during execution.

- [x] **Task 7.1: Detect when main branch has advanced**
  - [x] Track main branch HEAD at start of execution
  - [x] After each task, fetch and compare current main HEAD
  - [x] Return boolean indicating whether main has new commits
  - [x] Verify: correctly detects main advancement

- [x] **Task 7.2: Auto-rebase integration branch when rebase is clean**
  - [x] Attempt `git rebase main` on integration branch
  - [x] If successful, update slice branch to track rebased integration
  - [x] Force-push slice branch after rebase
  - [x] Verify: clean rebase completes without user intervention

- [x] **Task 7.3: Pause and notify user when rebase has conflicts**
  - [x] Detect rebase conflict (non-zero exit from rebase)
  - [x] Abort the rebase attempt
  - [x] Display clear message explaining the conflict
  - [x] Pause execution (wait for user input or exit)
  - [x] Verify: conflict triggers pause with clear message

- [ ] **Task 7.4: Integration test for main branch advancement**
  - [ ] Create test repository, run script to create integration branch
  - [ ] Add commits to main branch (simulate main advancing)
  - [ ] Run script again, verify it detects main advanced
  - [ ] Test clean rebase scenario: verify integration branch rebased automatically
  - [ ] Test conflict scenario: create conflicting changes, verify script pauses with message
  - [ ] Verify: tests use real git operations for rebase scenarios

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

- [ ] **Task 8.4: Integration test for completion and polling**
  - [ ] Create test repository with plan where all tasks are completed
  - [ ] Run script, verify PR is marked ready for review (`gh pr ready` called)
  - [ ] Test merge scenario: merge PR via `gh pr merge`, verify script exits with success
  - [ ] Test close scenario: close PR via `gh pr close`, verify script exits with message
  - [ ] Verify: tests use real GitHub PR state transitions

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

- [ ] **Task 9.3: Integration test for cleanup**
  - [ ] Create test repository, run script to create worktree and branches
  - [ ] Merge PR to complete workflow
  - [ ] Run script with `--cleanup` flag, verify worktree directory removed
  - [ ] Verify local branches deleted but remote branches remain
  - [ ] Verify: tests check filesystem and git state after cleanup

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

- [ ] **Task 10.3: Integration test for slice rollover**
  - [ ] Create test repository with PR in Draft state
  - [ ] Create local commits on slice branch (not pushed)
  - [ ] Mark PR as ready via `gh pr ready` (simulate unexpected state change)
  - [ ] Run script, verify it detects PR is no longer Draft
  - [ ] Verify new slice branch created with incremented number
  - [ ] Verify unpushed commits preserved on new slice
  - [ ] Verify new Draft PR created for new slice
  - [ ] Verify: tests check commit preservation and new PR creation

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

- [ ] **Task 11.3: Integration test for interrupt handling and resumability**
  - [ ] Create test repository, run script partially (complete some tasks)
  - [ ] Simulate interrupt (kill process or send SIGINT)
  - [ ] Verify state file is saved and git is in consistent state
  - [ ] Run script again, verify it resumes from correct task (not from beginning)
  - [ ] Verify already-processed feedback is not reprocessed
  - [ ] Verify: tests check state persistence and correct resume behavior

---

## Change History

### 2026-01-30: Added integration test tasks to each steel thread

Added explicit integration test tasks to each steel thread to ensure the script is wired together and behaves correctly end-to-end:
- Task 1.3: Integration test for CLI skeleton
- Task 2.5: Integration test for idea validation
- Task 3.4: Integration test for git infrastructure setup
- Task 4.3: Integration test for GitHub PR management
- Task 5.5: Integration test for task execution (with mocked Claude)
- Task 6.5: Integration test for feedback handling
- Task 7.4: Integration test for main branch advancement
- Task 8.4: Integration test for completion and polling
- Task 9.3: Integration test for cleanup
- Task 10.3: Integration test for slice rollover
- Task 11.3: Integration test for interrupt handling and resumability

These tasks run the actual `implement-with-worktree.sh` script against real test repositories and verify observable behavior, addressing the gap where unit-tested functions weren't wired into main().

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
