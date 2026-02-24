Now I have a complete understanding of the codebase. Let me generate the plan.

---

# Simplify Worktree Branching — Implementation Plan

## Idea Type

**D. Refactoring of existing internal tooling** — This is a simplification of existing internal infrastructure (the `i2code implement` command's worktree mode). It is closest to type C (platform/infrastructure capability), but since it modifies an existing Python CLI tool with full CI already in place, no new CI or infrastructure setup is needed.

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

- NEVER write production code (`src/i2code/**/*.py`) without first writing a failing test
- Before using Write on any `.py` file in `src/`, ask: "Do I have a failing test?" If not, write the test first
- When task direction changes mid-implementation, return to TDD PLANNING state and write a test first

### Verification Requirements

- Hard rule: NEVER git commit, git push, or open a PR unless you have successfully run the project's test command and it exits 0
- Hard rule: If running tests is blocked for any reason (including permissions), ALWAYS STOP immediately. Print the failing command, the exact error output, and the permission/path required
- Before committing, ALWAYS print a Verification section containing the exact test command (NOT an ad-hoc command - it must be a proper test command such as `./test-scripts/*.sh`, `./scripts/test.sh`, or `uv run python3 -m pytest tests/ -v -m "unit or integration"`), its exit code, and the last 20 lines of output

### Test command

The unit test command for this project is:

```bash
uv run python3 -m pytest tests/ -v -m "unit or integration"
```

CI runs `./test-scripts/test-end-to-end.sh`.

---

## Steel Thread 1: Single Idea Branch Replaces Integration and Slice Branches

This steel thread implements the core branching simplification: replacing the two-level branching model (integration + slice) with a single `idea/<name>` branch, and updating PR title/body generation. All existing CI infrastructure is already in place.

- [x] **Task 1.1: WorkflowState drops slice_number on load and save**
  - TaskType: OUTCOME
  - Entrypoint: `uv run python3 -m pytest tests/implement/test_workflow_state.py -v`
  - Observable: `WorkflowState.load()` creates new state files without `slice_number`, reads old files containing `slice_number` without error, and `save()` omits `slice_number` from the persisted JSON
  - Evidence: Unit tests verify: (1) new state files have no `slice_number` key, (2) old state files with `slice_number` load successfully with feedback IDs intact, (3) after loading an old file and saving, the saved JSON has no `slice_number`
  - Steps:
    - [x] Update existing tests in `tests/implement/test_workflow_state.py`: remove assertions on `state.slice_number`, add tests for backward-compatible loading (file with `slice_number` loads without error, feedback IDs are preserved), and add a test that `save()` after loading an old file drops `slice_number`
    - [x] Modify `src/i2code/implement/workflow_state.py`: remove `slice_number` from the default data dict in `load()`, remove the `slice_number` property, add logic in `load()` to silently pop `slice_number` from loaded data
    - [x] Update `tests/implement/fake_workflow_state.py`: remove `slice_number` parameter and property from `FakeWorkflowState`

- [x] **Task 1.2: GitRepository gains ensure_idea_branch and ensure_pr drops slice_number**
  - TaskType: OUTCOME
  - Entrypoint: `uv run python3 -m pytest tests/implement/test_git_repository.py -v`
  - Observable: `ensure_idea_branch(idea_name)` creates or reuses a branch named `idea/<name>` from HEAD. `ensure_pr()` accepts only `idea_directory` and `idea_name` (no `slice_number`) and creates a Draft PR with the title derived from the idea file heading and a minimal body containing just the idea directory link
  - Evidence: Unit tests verify: (1) `ensure_idea_branch("my-feature")` creates branch `idea/my-feature`, (2) calling it again reuses the existing branch, (3) `ensure_pr()` without `slice_number` creates a PR with the correct title and body format
  - Steps:
    - [x] Add test class `TestEnsureIdeaBranch` in `tests/implement/test_git_repository.py` with tests for creating a new idea branch and reusing an existing one
    - [x] Add `ensure_idea_branch(idea_name)` method to `src/i2code/implement/git_repository.py` that delegates to `ensure_branch(f"idea/{idea_name}")`
    - [x] Add a helper function `extract_title_from_idea_file(idea_directory, idea_name)` in `src/i2code/implement/pr_helpers.py` that reads the first `# ` heading from the idea file, with fallback to the idea name. Add tests for it in `tests/implement/test_pr_helpers.py`
    - [x] Update `generate_pr_title()` in `src/i2code/implement/pr_helpers.py` to accept `(idea_name, idea_directory)` and use `extract_title_from_idea_file`. Update `generate_pr_body()` to accept only `(idea_directory)` and produce the minimal format: `**Idea directory:** \`<idea-directory>\``
    - [x] Update `ensure_pr()` in `src/i2code/implement/git_repository.py` to accept only `(idea_directory, idea_name)` — remove `slice_number` parameter, call the updated title/body generators
    - [x] Update tests in `tests/implement/test_git_repository.py` `TestEnsurePr` to match the new 2-argument signature
    - [x] Update `tests/implement/test_pr_helpers.py` `TestPRTitleGeneration` and `TestPRBodyGeneration` to test the new behavior
    - [x] Update `FakeGitRepository.ensure_pr()` in `tests/implement/fake_git_repository.py` to accept only `(idea_directory, idea_name)` — remove `slice_number`
    - [x] Add `ensure_idea_branch()` stub to `tests/implement/fake_git_repository.py`

- [x] **Task 1.3: ImplementCommand._worktree_mode uses single idea branch**
  - TaskType: OUTCOME
  - Entrypoint: `uv run python3 -m pytest tests/implement/test_implement_command.py -v`
  - Observable: `_worktree_mode()` creates a single `idea/<name>` branch (no integration or slice branch), creates the worktree on that branch, sets `git_repo.branch` to the idea branch, and finds existing PRs on the idea branch
  - Evidence: Unit tests verify: (1) `ensure_idea_branch` is called instead of `ensure_integration_branch`/`ensure_slice_branch`, (2) `ensure_worktree` receives the idea branch name, (3) `git_repo.branch` is set to the idea branch, (4) `find_pr` is called with the idea branch name
  - Steps:
    - [x] Update `TestImplementCommandWorktreeMode` in `tests/implement/test_implement_command.py` to verify the new single-branch flow: mock `ensure_idea_branch` instead of `ensure_integration_branch`/`ensure_slice_branch`, verify no `slice_number` references, verify `checkout` is not called (worktree is already on the idea branch)
    - [x] Update `TestDeferredPRCreation` to remove the `slice_number=1` mock on `WorkflowState.load`
    - [x] Rewrite `_worktree_mode()` in `src/i2code/implement/implement_command.py`:
      1. Load `WorkflowState` from state file
      2. Call `self.git_repo.ensure_idea_branch(self.project.name)` to get the idea branch
      3. Create worktree on the idea branch (or set up isolated mode without `checkout`)
      4. Set `self.git_repo.branch = idea_branch`
      5. Find existing PR on the idea branch
      6. Delegate to `worktree_mode.execute()`
    - [x] Remove the `WorkflowState` import if no longer needed in `_worktree_mode()` (check if state is still loaded here — it is, for the state file)

- [ ] **Task 1.4: WorktreeMode._push_and_ensure_pr drops slice_number and completion marks PR ready**
  - TaskType: OUTCOME
  - Entrypoint: `uv run python3 -m pytest tests/implement/test_worktree_mode.py -v`
  - Observable: `_push_and_ensure_pr()` calls `ensure_pr()` without `slice_number`. When all tasks complete, `_print_completion()` calls `gh_client.mark_pr_ready()` before printing the PR URL. The push error message says "branch" instead of "slice branch"
  - Evidence: Unit tests verify: (1) `ensure_pr` is called with only `(directory, name)` — no third argument, (2) when all tasks are complete and a PR exists, `mark_pr_ready` is called on the gh_client, (3) the "ready for review" status is printed
  - Steps:
    - [ ] Add test in `tests/implement/test_worktree_mode.py` `TestWorktreeModeAllComplete`: when all tasks are complete and PR exists, `mark_pr_ready` is called on `fake_gh` and output contains "ready for review"
    - [ ] Add test: when all tasks are complete but no PR exists (pr_number is None), `mark_pr_ready` is NOT called
    - [ ] Update `_push_and_ensure_pr()` in `src/i2code/implement/worktree_mode.py`: remove `self._loop_steps.state.slice_number` from the `ensure_pr()` call, change error message from "slice branch" to "branch"
    - [ ] Update `_print_completion()` in `src/i2code/implement/worktree_mode.py`: call `self._git_repo.gh_client.mark_pr_ready(self._git_repo.pr_number)` before printing the PR URL, print "PR marked ready for review" on success
    - [ ] Verify existing `test_executes_single_task_push_pr_ci` still passes (the `ensure_pr` call args assertion may need updating)

## Steel Thread 2: Dead Code Removal

This steel thread removes all dead code related to the old integration/slice branching model.

- [ ] **Task 2.1: Remove dead branching and rebase code**
  - TaskType: REFACTOR
  - Entrypoint: `uv run python3 -m pytest tests/ -v -m "unit or integration"`
  - Observable: No behavior change — all existing tests pass. The following dead code is removed: `ensure_integration_branch()` and `ensure_slice_branch()` from `git_repository.py`, `rebase_integration_branch()`, `update_slice_after_rebase()`, and `get_rebase_conflict_message()` from `branch_lifecycle.py`
  - Evidence: Full test suite passes. Grep for `integration_branch`, `slice_branch`, `rebase_integration`, `update_slice_after_rebase`, `get_rebase_conflict_message` in `src/` returns no results
  - Steps:
    - [ ] Remove `ensure_integration_branch()` and `ensure_slice_branch()` from `src/i2code/implement/git_repository.py`
    - [ ] Remove `ensure_integration_branch()` and `ensure_slice_branch()` stubs from `tests/implement/fake_git_repository.py`
    - [ ] Remove `rebase_integration_branch()`, `update_slice_after_rebase()`, and `get_rebase_conflict_message()` from `src/i2code/implement/branch_lifecycle.py`
    - [ ] Remove `TestRebaseOperations` and `TestRebaseConflictHandling` test classes from `tests/implement/test_branch_lifecycle.py`
    - [ ] Run full test suite to confirm no behavior change

- [ ] **Task 2.2: Remove dead PR helper functions and their tests**
  - TaskType: REFACTOR
  - Entrypoint: `uv run python3 -m pytest tests/ -v -m "unit or integration"`
  - Observable: No behavior change — all existing tests pass. The following dead code is removed: `push_to_slice_branch()`, `should_rollover()`, `generate_next_slice_branch()` from `pr_helpers.py`
  - Evidence: Full test suite passes. Grep for `push_to_slice_branch`, `should_rollover`, `generate_next_slice_branch`, `slice_number` in `src/` returns no results
  - Steps:
    - [ ] Remove `push_to_slice_branch()`, `should_rollover()`, and `generate_next_slice_branch()` from `src/i2code/implement/pr_helpers.py`
    - [ ] Remove `TestPushToSliceBranch` and `TestSliceRollover` test classes from `tests/implement/test_pr_helpers.py`
    - [ ] Remove the `sanitize_branch_name` import from `pr_helpers.py` if it's no longer used
    - [ ] Search `src/` for any remaining references to "slice", "integration_branch", or "rollover" and remove them
    - [ ] Run full test suite to confirm no behavior change

---

## Change History
### 2026-02-24 16:47 - mark-step-complete
Updated tests: removed slice_number assertions, added backward-compat loading test and save-drops-slice_number test

### 2026-02-24 16:47 - mark-step-complete
Removed slice_number from default data, removed property, added pop on load

### 2026-02-24 16:47 - mark-step-complete
Removed slice_number constructor parameter from FakeWorkflowState; property retained temporarily for worktree_mode consumers (Task 1.4)

### 2026-02-24 16:47 - mark-task-complete
WorkflowState.load() creates files without slice_number, reads old files with slice_number without error, save() omits slice_number

### 2026-02-24 17:09 - mark-step-complete
Updated TestImplementCommandWorktreeMode with 7 tests for single-branch flow: ensure_idea_branch called, no integration/slice branch, worktree receives idea branch, branch set to idea branch, find_pr uses idea branch, checkout not called, delegates to mode_factory

### 2026-02-24 17:09 - mark-step-complete
Removed slice_number=1 from WorkflowState.load mock, updated to use ensure_idea_branch and assert on worktree git_repo

### 2026-02-24 17:09 - mark-step-complete
Rewrote _worktree_mode(): calls ensure_idea_branch, passes idea branch to ensure_worktree, sets git_repo.branch to idea branch, finds PR on idea branch, no checkout call

### 2026-02-24 17:09 - mark-step-complete
WorkflowState import is still needed — state is loaded from state file on line 84

### 2026-02-24 17:09 - mark-task-complete
_worktree_mode() creates single idea/<name> branch, worktree on that branch, sets git_repo.branch, finds PRs on idea branch. All 802 tests pass.
