# Implementation Plan: Restructure Unit Tests by Module

## Idea Type

**B. Refactoring/improvement** - Reorganize unit tests in `tests/implement/` so each test file maps to exactly one production module, eliminating duplication and centralizing coverage.

---

## Instructions for Coding Agent

### Required Skills

| Skill | When to Use |
|-------|-------------|
| `idea-to-code:plan-tracking` | ALWAYS - track task completion in the plan file |
| `idea-to-code:commit-guidelines` | Before creating any git commit |
| `idea-to-code:file-organization` | When moving, renaming, or deleting test files |

### Design Rules

1. **One test file per production module.** `test_<module>.py` tests only classes/functions from `<module>.py`.
2. **Delete duplicates, don't move them.** If a test already exists in the destination, delete the copy.
3. **Preserve test behavior.** Move tests verbatim — don't rewrite or refactor during the move.
4. **Run tests after each step.** Verify the suite passes before proceeding.
5. **Leftovers rule.** When a thread consolidates `test_foo.py`, if that file still contains tests belonging to other modules, rename it to `test_foo_leftovers.py`. Later threads pull from the leftovers file. Thread 12 deletes any empty leftovers files.

---

## Benefit Ranking (declining)

| Rank | Module | Files today | Issue |
|------|--------|-------------|-------|
| 1 | CommandBuilder | 3 files | ~16 duplicate tests across `test_command_builder`, `test_claude_invocation`, `test_github_pr` |
| 2 | WorkflowState | 3 files | `test_state_management.py` is an almost-complete duplicate of `test_workflow_state.py` |
| 3 | ImplementCommand | 3 files | `test_dry_run.py` + 5 classes in `test_cli_integration.py` all duplicate `test_implement_command.py` |
| 4 | PullRequestReviewProcessor | 3 files | 5 static-method test classes homeless in `test_github_pr.py` |
| 5 | GitRepository | 3 files | Large block of infrastructure tests in wrong file |
| 6 | pr_helpers | 2 files | No test file exists — 21 tests scattered across kitchen-sink files |
| 7 | branch_lifecycle | 1 file | No test file exists — 19 tests buried in `test_claude_invocation.py` |
| 8 | claude_runner | 2 files | `check_claude_success` + output capture tests in wrong file |
| 9 | git_setup | 2 files | File misnamed (`test_idea_validation.py`); 2 tests homeless |
| 10 | IdeaProject | 2 files | 1 stray test |

---

## Steel Thread 1: Delete Pure Duplicates

- [x] **Task 1.1: Delete `test_dry_run.py`**
  - TaskType: code
  - Entrypoint: `tests/implement/test_dry_run.py`
  - Observable: File deleted, `test_implement_command.py` tests still pass
  - Evidence: `uv run --with pytest pytest tests/implement/test_implement_command.py -v`
  - Steps:
    - [x] Move `test_dry_run_does_not_execute` (unique — verifies mode method NOT called) to `TestImplementCommandDryRun` in `test_implement_command.py`
    - [x] Delete `test_dry_run.py` (remaining 3 tests are exact duplicates)
    - [x] Run tests

- [x] **Task 1.2: Delete `test_state_management.py`**
  - TaskType: code
  - Entrypoint: `tests/implement/test_state_management.py`
  - Observable: File deleted, `test_workflow_state.py` tests still pass
  - Evidence: `uv run --with pytest pytest tests/implement/test_workflow_state.py -v`
  - Steps:
    - [x] Verify all 5 tests duplicate `test_workflow_state.py`
    - [x] Delete `test_state_management.py`
    - [x] Run tests

## Steel Thread 2: Consolidate `test_command_builder.py` (Rank 1)

- [x] **Task 2.1: Delete duplicate CommandBuilder tests from `test_claude_invocation.py`**
  - TaskType: code
  - Observable: 16 duplicate tests removed from source file
  - Steps:
    - [x] Delete `TestClaudeCommandConstruction` (7 tests — all duplicate `TestCommandBuilderTaskCommand`)
    - [x] Delete `TestFeedbackHandling` duplicate tests (2 of 3); move `test_build_feedback_command_uses_feedback_template` (unique — verifies command references template) to `test_command_builder.py`
    - [x] Delete `TestBuildCiFixCommand` duplicate tests (3 of 4); move `test_build_ci_fix_command_renders_ci_fix_template` (unique — verifies render_template call) to `test_command_builder.py`
    - [x] Run tests

- [x] **Task 2.2: Move unique CommandBuilder tests to `test_command_builder.py`**
  - TaskType: code
  - Observable: 7 unique tests added, source files renamed to `_leftovers`
  - Evidence: `uv run --with pytest pytest tests/implement/test_command_builder.py -v`
  - Steps:
    - [x] Move `TestFeedbackTemplate` (4 tests) from `test_claude_invocation.py`
    - [x] Move `test_claude_prompt_uses_worktree_idea_directory` (1 test) from `test_claude_invocation.py`
    - [x] Move unique `test_build_triage_command_requests_json_output` (1 test) from `test_github_pr.py`; delete 2 duplicate triage tests
    - [x] Move unique `test_build_fix_command_interactive` feedback/description check (1 test) from `test_github_pr.py`; delete 1 duplicate fix test
    - [x] Rename remaining `test_github_pr.py` → `test_github_pr_leftovers.py`
    - [x] Rename remaining `test_claude_invocation.py` → `test_claude_invocation_leftovers.py`
    - [x] Run tests

## Steel Thread 3: Consolidate `test_workflow_state.py` (Rank 2)

- [x] **Task 3.1: Move stray WorkflowState test**
  - TaskType: code
  - Observable: `test_includes_processed_conversation_ids` added to `TestWorkflowStateDefaultState`
  - Evidence: `uv run --with pytest pytest tests/implement/test_workflow_state.py -v`
  - Steps:
    - [x] Move `TestDefaultStateIncludesConversationIds` (1 test) from `test_github_pr_leftovers.py` into existing `TestWorkflowStateDefaultState`
    - [x] Run tests

## Steel Thread 4: Consolidate `test_implement_command.py` (Rank 3)

- [x] **Task 4.1: Remove duplicate unit tests from `test_cli_integration.py`**
  - TaskType: code
  - Observable: Only 2 `@pytest.mark.integration` classes remain in `test_cli_integration.py`
  - Evidence: `uv run --with pytest pytest tests/implement/test_cli_integration.py -v`
  - Steps:
    - [x] Remove `TestIsolatedFlagPassthrough` (2 tests), `TestTrunkModeAcceptance` (1), `TestTrunkModeIncompatibleFlags` (1), `TestIgnoreUncommittedIdeaChanges` (2), `TestWorktreeModeAcceptance` (1)
    - [x] Remove unused helpers `_make_mock_project`, `_make_numbered_task`
    - [x] Clean up imports
    - [x] Run tests

- [x] **Task 4.2: Move `TestDeferredPRCreation` to `test_implement_command.py`**
  - TaskType: code
  - Observable: Test moved from `test_github_pr_leftovers.py`
  - Evidence: `uv run --with pytest pytest tests/implement/test_implement_command.py -v`
  - Steps:
    - [x] Move `TestDeferredPRCreation` (1 test) from `test_github_pr_leftovers.py`
    - [x] Run tests

## Steel Thread 5: Consolidate `test_pull_request_review_processor.py` (Rank 4)

- [x] **Task 5.1: Move static method tests from `test_github_pr_leftovers.py`**
  - TaskType: code
  - Observable: 5 classes (14 tests) added
  - Evidence: `uv run --with pytest pytest tests/implement/test_pull_request_review_processor.py -v`
  - Steps:
    - [x] Move `TestFormatAllFeedback` (4), `TestGetNewFeedback` (3), `TestParseTriageResult` (3), `TestGetFeedbackByIds` (2), `TestDetermineCommentType` (2) from `test_github_pr_leftovers.py`
    - [x] Delete `TestFeedbackDetection` (2 tests) from `test_claude_invocation_leftovers.py` — duplicates `TestGetNewFeedback`
    - [x] Run tests

## Steel Thread 6: Consolidate `test_git_repository*.py` (Rank 5)

- [ ] **Task 6.1: Create `test_git_repository_setup.py`**
  - TaskType: code
  - Observable: New file with infrastructure/setup tests, `test_git_infrastructure.py` deleted
  - Evidence: `uv run --with pytest pytest tests/implement/test_git_repository*.py -v`
  - Steps:
    - [ ] Create `test_git_repository_setup.py` with `TestIntegrationBranch` (7), unique `TestWorktree` (3), `TestSliceBranch` (3), `TestSliceNameSanitization` (4) from `test_git_infrastructure.py`
    - [ ] Move `TestEnsurePrOnGitRepository` (3 tests) from `test_github_pr_leftovers.py`
    - [ ] Delete 2 duplicate worktree tests (already in `test_git_repository.py`)
    - [ ] Delete `test_git_infrastructure.py`
    - [ ] Run tests

## Steel Thread 7: Create `test_pr_helpers.py` (Rank 6)

- [ ] **Task 7.1: Create `test_pr_helpers.py` with all pr_helpers tests**
  - TaskType: code
  - Observable: New file with 21 tests from 7 classes
  - Evidence: `uv run --with pytest pytest tests/implement/test_pr_helpers.py -v`
  - Steps:
    - [ ] Create file with `TestPRTitleGeneration` (2), `TestPRBodyGeneration` (1) from `test_github_pr_leftovers.py`
    - [ ] Move `TestPushOperations` (2), `TestPushToSliceBranch` (3), `TestPRReadyForReview` (2), `TestPRPolling` (6), `TestSliceRollover` (5) from `test_claude_invocation_leftovers.py`
    - [ ] Run tests

## Steel Thread 8: Create `test_branch_lifecycle.py` (Rank 7)

- [ ] **Task 8.1: Create `test_branch_lifecycle.py` with all branch_lifecycle tests**
  - TaskType: code
  - Observable: New file with 19 tests from 5 classes
  - Evidence: `uv run --with pytest pytest tests/implement/test_branch_lifecycle.py -v`
  - Steps:
    - [ ] Create file with `TestMainBranchAdvancement` (5), `TestRebaseOperations` (5), `TestRebaseConflictHandling` (3), `TestCleanupOperations` (4), `TestInterruptHandling` (2) from `test_claude_invocation_leftovers.py`
    - [ ] Run tests

## Steel Thread 9: Consolidate `test_claude_runner.py` (Rank 8)

- [ ] **Task 9.1: Move claude_runner tests**
  - TaskType: code
  - Observable: 2 classes (6 tests) added
  - Evidence: `uv run --with pytest pytest tests/implement/test_claude_runner.py -v`
  - Steps:
    - [ ] Move `TestRunClaudeWithOutputCapture` (2 tests) and `TestClaudeInvocationResult` (4 tests) from `test_claude_invocation_leftovers.py`
    - [ ] Run tests

## Steel Thread 10: Create `test_git_setup.py` (Rank 9)

- [ ] **Task 10.1: Rename `test_idea_validation.py` and add stray test**
  - TaskType: code
  - Observable: File renamed, `TestCalculateClaudePermissions` added
  - Evidence: `uv run --with pytest pytest tests/implement/test_git_setup.py -v`
  - Steps:
    - [ ] `git mv tests/implement/test_idea_validation.py tests/implement/test_git_setup.py`
    - [ ] Move `TestCalculateClaudePermissions` (2 tests) from `test_claude_invocation_leftovers.py`
    - [ ] Run tests

## Steel Thread 11: Consolidate `test_idea_project.py` (Rank 10)

- [ ] **Task 11.1: Move stray IdeaProject test**
  - TaskType: code
  - Observable: `test_worktree_idea_project` added
  - Evidence: `uv run --with pytest pytest tests/implement/test_idea_project.py -v`
  - Steps:
    - [ ] Move `test_worktree_idea_project` (1 test) from `test_claude_invocation_leftovers.py`
    - [ ] Run tests

## Steel Thread 12: Delete Emptied Source Files & Verify

- [ ] **Task 12.1: Delete emptied leftovers files and verify**
  - TaskType: code
  - Observable: `test_github_pr_leftovers.py` and `test_claude_invocation_leftovers.py` deleted
  - Evidence: `uv run --with pytest pytest tests/implement/ -v -m unit`
  - Steps:
    - [ ] Verify `test_github_pr_leftovers.py` has no remaining test classes
    - [ ] Delete `test_github_pr_leftovers.py`
    - [ ] Verify `test_claude_invocation_leftovers.py` has no remaining test classes
    - [ ] Delete `test_claude_invocation_leftovers.py`
    - [ ] Run full unit test suite
    - [ ] Verify each test file maps to exactly one production module

---

## Final Test File Inventory

| Test File | Production Module | Status |
|---|---|---|
| `test_implement_command.py` | `implement_command.py` | Expanded |
| `test_implement_opts.py` | `implement_opts.py` | Unchanged |
| `test_trunk_mode.py` | `trunk_mode.py` | Unchanged |
| `test_worktree_mode.py` | `worktree_mode.py` | Unchanged |
| `test_isolate_mode.py` | `isolate_mode.py` | Unchanged |
| `test_idea_project.py` | `idea_project.py` | Expanded |
| `test_git_repository.py` | `git_repository.py` (core ops) | Unchanged |
| `test_git_repository_setup.py` | `git_repository.py` (setup/infra) | **New** |
| `test_git_setup.py` | `git_setup.py` | **Renamed** + expanded |
| `test_pr_helpers.py` | `pr_helpers.py` | **New** |
| `test_branch_lifecycle.py` | `branch_lifecycle.py` | **New** |
| `test_command_builder.py` | `command_builder.py` | Expanded |
| `test_claude_runner.py` | `claude_runner.py` | Expanded |
| `test_workflow_state.py` | `workflow_state.py` | Expanded |
| `test_project_setup.py` | `project_setup.py` | Unchanged |
| `test_github_client.py` | `github_client.py` | Unchanged |
| `test_pull_request_review_processor.py` | `pull_request_review_processor.py` | Expanded |
| `test_github_actions_build_fixer.py` | `github_actions_build_fixer.py` | Unchanged |
| `test_github_actions_monitor.py` | `github_actions_monitor.py` | Unchanged |
| `test_fake_idea_project.py` | FakeIdeaProject conformance | Unchanged |
| `test_cli_integration.py` | CLI subprocess | Trimmed |

Integration test files (unchanged): `test_*_integration.py` (4 files)

**Deleted:** `test_dry_run.py`, `test_state_management.py`, `test_github_pr.py`, `test_claude_invocation.py`, `test_git_infrastructure.py`, `test_idea_validation.py` (renamed)

**Net change:** ~30 duplicate tests eliminated, ~50 tests moved to correct module files

---

## Change History
### 2026-02-19 08:47 - mark-task-complete
Moved test_dry_run_does_not_execute to TestImplementCommandDryRun, deleted test_dry_run.py, all 18 tests pass

### 2026-02-19 08:50 - mark-step-complete
All 5 tests verified as duplicates of test_workflow_state.py

### 2026-02-19 08:50 - mark-step-complete
File deleted via git rm

### 2026-02-19 08:50 - mark-step-complete
All 11 tests in test_workflow_state.py pass

### 2026-02-19 08:50 - mark-task-complete
Deleted duplicate test_state_management.py; all 11 tests in test_workflow_state.py pass

### 2026-02-19 08:55 - mark-step-complete
Deleted TestClaudeCommandConstruction (7 tests) from test_claude_invocation.py

### 2026-02-19 08:55 - mark-step-complete
Deleted 2 duplicate TestFeedbackHandling tests; moved test_build_feedback_command_uses_feedback_template to test_command_builder.py

### 2026-02-19 08:55 - mark-step-complete
Deleted 3 duplicate TestBuildCiFixCommand tests; moved test_build_ci_fix_command_renders_ci_fix_template to test_command_builder.py

### 2026-02-19 08:55 - mark-step-complete
All 78 tests pass (down from 90 — 14 duplicates removed, 2 unique tests moved)

### 2026-02-19 08:55 - mark-task-complete
Deleted 14 duplicate tests from test_claude_invocation.py (7 TestClaudeCommandConstruction, 3 TestFeedbackHandling, 4 TestBuildCiFixCommand); moved 2 unique tests to test_command_builder.py

### 2026-02-19 09:00 - mark-step-complete
Moved TestFeedbackTemplate (4 tests) to test_command_builder.py

### 2026-02-19 09:00 - mark-step-complete
Moved test_claude_prompt_uses_worktree_idea_directory to test_command_builder.py

### 2026-02-19 09:00 - mark-step-complete
Moved unique triage test; deleted 2 duplicate triage tests

### 2026-02-19 09:00 - mark-step-complete
Moved unique fix test feedback/description check; deleted 1 duplicate fix test

### 2026-02-19 09:00 - mark-step-complete
Renamed test_github_pr.py to test_github_pr_leftovers.py

### 2026-02-19 09:00 - mark-step-complete
Renamed test_claude_invocation.py to test_claude_invocation_leftovers.py

### 2026-02-19 09:00 - mark-step-complete
All 32 tests in test_command_builder.py pass; 70 leftover tests pass

### 2026-02-19 09:00 - mark-task-complete
7 unique tests moved to test_command_builder.py; 3 duplicates deleted; source files renamed to _leftovers

### 2026-02-19 09:03 - mark-task-complete
Moved test_init_state_includes_processed_conversation_ids from TestDefaultStateIncludesConversationIds in test_github_pr_leftovers.py into TestWorkflowStateDefaultState in test_workflow_state.py

### 2026-02-19 09:08 - mark-task-complete
Removed 5 unit test classes, 2 helpers, cleaned up imports. Only 2 integration classes remain.

### 2026-02-19 09:12 - mark-step-complete
Moved TestDeferredPRCreation from test_github_pr_leftovers.py to test_implement_command.py

### 2026-02-19 09:12 - mark-step-complete
All 19 tests pass in test_implement_command.py, all 20 tests pass in test_github_pr_leftovers.py

### 2026-02-19 09:12 - mark-task-complete
TestDeferredPRCreation moved to test_implement_command.py, all tests pass

### 2026-02-19 09:16 - mark-task-complete
Moved 5 test classes (14 tests) to test_pull_request_review_processor.py, deleted duplicate TestFeedbackDetection from test_claude_invocation_leftovers.py
