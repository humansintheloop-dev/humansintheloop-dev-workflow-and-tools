# Implementation Plan: Improve Modularity of Implement Package

## Idea Type

**B. Refactoring/improvement** - Extract the 2332-line procedural `implement.py` into cohesive classes with injectable dependencies, eliminating the need for `unittest.mock.patch` in tests.

---

## Instructions for Coding Agent

- IMPORTANT: Use simple commands that you have permission to execute. Avoid complex commands that may fail due to permission issues.

### Required Skills

Use these skills by invoking them before the relevant action:

| Skill | When to Use |
|-------|-------------|
| `idea-to-code:plan-tracking` | ALWAYS - track task completion in the plan file |
| `idea-to-code:tdd` | When implementing code - write failing tests first |
| `idea-to-code:commit-guidelines` | Before creating any git commit |
| `idea-to-code:file-organization` | When moving, renaming, or reorganizing files |

### Design Rules

These rules govern all code written during this refactoring:

1. **Wrap external systems in injectable classes.** Every external system (subprocess, filesystem, network) must be accessed through a class that is passed in as a constructor argument, never imported and called directly. Domain logic must never call `subprocess.run`, `os.path`, or `Repo()` directly.

2. **Data that travels together is a class.** If two or more values are passed together to three or more functions, they must become a class with those values as attributes.

3. **Tests must not use `unittest.mock.patch`.** Tests use dependency injection and fake collaborators, not monkey-patching. If a function cannot be tested without `@patch`, refactor the function to accept its dependencies as arguments.

4. **File size limit.** No source file may exceed 300 lines. When a module grows beyond this, extract a class or module before adding more code.

5. **State belongs to objects, not loop variables.** If a loop or long function tracks mutable state in local variables that are passed to called functions, that state and those functions belong in a class.

### TDD Requirements

- NEVER write production code without first writing a failing test
- Follow outside-in TDD: acceptance test first, then unit tests one layer at a time
- Write ONE test at a time, not batches
- Stub with `raise NotImplementedError` so tests execute (not collection errors)

### Testing Strategy

- **New tests** use fake collaborators (e.g., `FakeGitRepository`, `FakeClaudeRunner`) — no `@patch`
- **Existing tests** are migrated to fakes as their corresponding production code is refactored
- **Integration tests** (`test_git_infrastructure.py`, `test_project_setup_integration.py`, `test_task_execution_integration.py`) are left unchanged — they already use real Git repos and fake shell scripts
- **Test runner**: `uv run --with pytest --with pytest-mock pytest tests/implement/ -v`

### Key Files

| File | Current Role | Target |
|------|-------------|--------|
| `src/i2code/implement/implement.py` | 2332-line God module with 60+ functions | Split into classes below |
| `src/i2code/implement/cli.py` | 387-line Click handler with 180-line implement_cmd | Thin dispatcher to execution modes |
| `src/i2code/implement/git_utils.py` | Single function (get_default_branch) | Absorbed into GitHubClient |

### Target Class Structure

| Class | Module | File | Responsibility |
|-------|--------|------|----------------|
| `IdeaProject` | `i2code.idea` | `idea_project.py` | Value object: directory + name + plan file path. Owns validation. |
| `WorkflowState` | `i2code.implement` | `workflow_state.py` | Encapsulates state persistence (slice_number, processed IDs). Owns load/save. |
| `GitHubClient` | `i2code.git` | `github_client.py` | Wraps all `gh` CLI calls. Injected into GitRepository. |
| `GitRepository` | `i2code.git` | `git_repository.py` | Wraps all Git operations (GitPython + subprocess). Tracks current branch and PR number. Delegates GitHub operations to GitHubClient. |
| `ClaudeRunner` | `i2code.claude` | `claude_runner.py` | Wraps Claude invocation. Strategy: real Claude vs mock script. Owns `ClaudeResult`. |
| `CommandBuilder` | `i2code.claude` | `command_builder.py` | Builds all Claude command lists (task, scaffolding, triage, fix, CI fix). |
| `TrunkMode` | `i2code.implement` | `trunk_mode.py` | Execution mode: tasks on current branch, no Git infrastructure. |
| `WorktreeMode` | `i2code.implement` | `worktree_mode.py` | Execution mode: worktree + PR + CI workflow. |
| `IsolateMode` | `i2code.implement` | `isolate_mode.py` | Execution mode: delegates to isolarium VM. |

### Pre-Commit Checklist

Hard rule: NEVER git commit unless all three steps pass.

Before every commit, run these in order:

1. **Lint**: `ruff check src/ tests/` — fix any violations before proceeding
2. **Code Health**: Run CodeScene `pre_commit_code_health_safeguard` on the repository. If Code Health regresses, refactor before committing. See [CODE_SCENE.md](../../../CODE_SCENE.md) for details.
3. **Tests**: `./test-scripts/test-end-to-end.sh` — must exit 0

---

## Overview

`src/i2code/implement/implement.py` is a 2332-line procedural module containing 60+ free functions organized by comment headers (`# GitHub PR Management Functions`, `# Feedback Detection Functions`, etc.). The only class is `ClaudeResult`, a pure data holder. The companion `cli.py` contains a 180-line `implement_cmd` function that branches on 5 execution modes via cascading if/elif blocks and imports 30 functions from `implement.py`.

Tests require 6-21 `@patch` decorators per test because functions call `subprocess.run` and `Repo()` directly with no seams for injection. `MagicMock()` is used without `spec=`, hiding interface drift. The inline `MockResult` class is duplicated ~15 times.

This plan extracts the natural class boundaries into injectable collaborators, enabling tests that construct fakes instead of patching import paths. Each thread is independently committable and leaves all tests passing.

---

## Steel Thread 1: Extract IdeaProject Value Object
Extract `(idea_directory, idea_name)` pair into a value object that owns validation and path computation. This is the simplest extraction — pure logic, no external dependencies — and establishes the pattern for subsequent threads.

- [ ] **Task 1.1: Extract IdeaProject class**
  - TaskType: OUTCOME
  - Entrypoint: `uv run --with pytest --with pytest-mock pytest tests/implement/ -v`
  - Observable: `IdeaProject` class exists in `idea_project.py` with `directory`, `name`, `plan_file`, and `state_file` properties. `validate()` and `validate_files()` are methods. Callers in `cli.py` and `implement.py` use `IdeaProject` instead of passing `(idea_directory, idea_name)` pairs.
  - Evidence: Pre-commit checklist passes. New unit tests for `IdeaProject` use no mocks.
  - Steps:
    - [ ] Write unit tests for IdeaProject (construction, properties, validation)
    - [ ] Implement IdeaProject class in `src/i2code/implement/idea_project.py`
    - [ ] Update `cli.py` to construct IdeaProject and pass it to callers
    - [ ] Update functions in `implement.py` that take `(idea_directory, idea_name)` to take `IdeaProject`
    - [ ] Remove standalone `validate_idea_directory`, `validate_idea_files`, `get_state_file_path` from `implement.py`
    - [ ] Run pre-commit checklist (ruff, CodeScene safeguard, `./test-scripts/test-end-to-end.sh`)

- [ ] **Task 1.2: Extract WorkflowState class**
  - TaskType: OUTCOME
  - Entrypoint: `uv run --with pytest --with pytest-mock pytest tests/implement/ -v`
  - Observable: `WorkflowState` class exists in `workflow_state.py`. Owns load/save and `mark_comments_processed()`, `mark_reviews_processed()`, `mark_conversations_processed()`. No more raw dict mutation scattered through `process_pr_feedback`.
  - Evidence: Pre-commit checklist passes. New unit tests for WorkflowState use no mocks.
  - Steps:
    - [ ] Write unit tests for WorkflowState (load, save, mark_processed, default state)
    - [ ] Implement WorkflowState class in `src/i2code/implement/workflow_state.py`
    - [ ] Update `process_pr_feedback` and `cli.py` to use WorkflowState instead of raw dict
    - [ ] Remove `init_or_load_state`, `save_state`, `get_state_file_path` from `implement.py`
    - [ ] Run pre-commit checklist (ruff, CodeScene safeguard, `./test-scripts/test-end-to-end.sh`)

---

## Steel Thread 2: Extract GitHubClient
Extract all `gh` CLI calls into an injectable class. This is the highest-leverage extraction — it eliminates ~15 duplicate `MockResult` classes in tests and creates the component that `GitRepository` will later compose with.

- [ ] **Task 2.1: Extract GitHubClient with PR operations**
  - TaskType: OUTCOME
  - Entrypoint: `uv run --with pytest --with pytest-mock pytest tests/implement/ -v`
  - Observable: `GitHubClient` class exists in `github_client.py` with a shared `_run_gh()` helper. PR operations (`find_pr`, `create_draft_pr`, `is_pr_draft`, `get_pr_state`, `get_pr_url`, `mark_pr_ready`) are methods. `FakeGitHubClient` exists in test conftest.
  - Evidence: Pre-commit checklist passes. Tests for PR operations use `FakeGitHubClient` instead of `monkeypatch`/`MockResult`.
  - Steps:
    - [ ] Write `FakeGitHubClient` in test conftest with canned responses
    - [ ] Write unit tests for GitHubClient PR methods using FakeGitHubClient pattern
    - [ ] Implement GitHubClient class with `_run_gh()` helper and PR methods
    - [ ] Migrate `test_github_pr.py` PR tests to use FakeGitHubClient
    - [ ] Update callers in `implement.py` to accept GitHubClient
    - [ ] Remove standalone PR functions from `implement.py`
    - [ ] Run pre-commit checklist (ruff, CodeScene safeguard, `./test-scripts/test-end-to-end.sh`)

- [ ] **Task 2.2: Move feedback and CI operations to GitHubClient**
  - TaskType: OUTCOME
  - Entrypoint: `uv run --with pytest --with pytest-mock pytest tests/implement/ -v`
  - Observable: `fetch_pr_comments`, `fetch_pr_reviews`, `fetch_pr_conversation_comments`, `reply_to_review_comment`, `reply_to_pr_comment`, `fetch_failed_checks`, `get_workflow_runs_for_commit`, `get_workflow_failure_logs`, `wait_for_workflow_completion`, `get_default_branch` are methods on GitHubClient.
  - Evidence: Pre-commit checklist passes. `git_utils.py` deleted (absorbed into GitHubClient).
  - Steps:
    - [ ] Add feedback methods to GitHubClient with tests
    - [ ] Add CI/workflow methods to GitHubClient with tests
    - [ ] Move `get_default_branch` from `git_utils.py` into GitHubClient
    - [ ] Migrate `test_claude_invocation.py` feedback/CI tests to use FakeGitHubClient
    - [ ] Delete `git_utils.py`
    - [ ] Remove standalone feedback/CI functions from `implement.py`
    - [ ] Run pre-commit checklist (ruff, CodeScene safeguard, `./test-scripts/test-end-to-end.sh`)

---

## Steel Thread 3: Extract GitRepository
Extract all Git operations into a class that tracks branch and PR state. Composes with GitHubClient for remote operations. This eliminates the `(slice_branch, pr_number)` parameter threading.

- [ ] **Task 3.1: Extract GitRepository with branch operations**
  - TaskType: OUTCOME
  - Entrypoint: `uv run --with pytest --with pytest-mock pytest tests/implement/ -v`
  - Observable: `GitRepository` class exists in `git_repository.py`. Owns `head_sha`, `head_advanced_since()`, `ensure_branch()`, `checkout()`, `ensure_worktree()`. Wraps GitPython `Repo`. `FakeGitRepository` exists in test conftest.
  - Evidence: Pre-commit checklist passes. `test_git_infrastructure.py` integration tests unchanged.
  - Steps:
    - [ ] Write `FakeGitRepository` in test conftest
    - [ ] Write unit tests for GitRepository branch operations
    - [ ] Implement GitRepository class wrapping GitPython Repo
    - [ ] Update `run_trunk_loop` to accept GitRepository
    - [ ] Migrate `test_trunk_mode.py` to use FakeGitRepository (remove `@patch("...Repo")`)
    - [ ] Run pre-commit checklist (ruff, CodeScene safeguard, `./test-scripts/test-end-to-end.sh`)

- [ ] **Task 3.2: Add push, PR, and CI tracking to GitRepository**
  - TaskType: OUTCOME
  - Entrypoint: `uv run --with pytest --with pytest-mock pytest tests/implement/ -v`
  - Observable: GitRepository tracks `_branch` and `_pr_number` as state. `push()`, `ensure_pr()`, `wait_for_ci()`, `fix_ci_failure()` are methods that use tracked state. These methods delegate to the composed GitHubClient.
  - Evidence: Pre-commit checklist passes. Callers no longer pass `slice_branch` and `pr_number` as arguments.
  - Steps:
    - [ ] Add `_branch` and `_pr_number` state to GitRepository
    - [ ] Add `push()`, `ensure_pr()`, `wait_for_ci()` methods with tests
    - [ ] Add `fix_ci_failure()` method that uses tracked branch/sha
    - [ ] Update `implement_cmd` worktree path to use GitRepository state
    - [ ] Remove standalone `push_branch_to_remote`, `ensure_draft_pr`, `branch_has_been_pushed` from `implement.py`
    - [ ] Run pre-commit checklist (ruff, CodeScene safeguard, `./test-scripts/test-end-to-end.sh`)

---

## Steel Thread 4: Extract ClaudeRunner and CommandBuilder
Extract Claude invocation into an injectable strategy and consolidate the 6 command-building functions.

- [ ] **Task 4.1: Extract ClaudeRunner with strategy pattern**
  - TaskType: OUTCOME
  - Entrypoint: `uv run --with pytest --with pytest-mock pytest tests/implement/ -v`
  - Observable: `ClaudeRunner` class exists in `claude_runner.py` with `run_interactive()` and `run_with_capture()` methods. `MockClaudeRunner` subclass wraps mock shell scripts. `FakeClaudeRunner` exists in test conftest. `ClaudeResult` moves into this module.
  - Evidence: Pre-commit checklist passes. `run_trunk_loop` accepts ClaudeRunner instead of `mock_claude` string.
  - Steps:
    - [ ] Write `FakeClaudeRunner` in test conftest
    - [ ] Write unit tests for ClaudeRunner
    - [ ] Implement ClaudeRunner and MockClaudeRunner in `claude_runner.py`
    - [ ] Move ClaudeResult into `claude_runner.py`
    - [ ] Update `run_trunk_loop` to accept ClaudeRunner
    - [ ] Migrate `test_trunk_mode.py` to use FakeClaudeRunner (remove `@patch("...run_claude_interactive")` etc.)
    - [ ] Remove `run_claude_interactive`, `run_claude_with_output_capture` from `implement.py`
    - [ ] Run pre-commit checklist (ruff, CodeScene safeguard, `./test-scripts/test-end-to-end.sh`)

- [ ] **Task 4.2: Extract CommandBuilder**
  - TaskType: OUTCOME
  - Entrypoint: `uv run --with pytest --with pytest-mock pytest tests/implement/ -v`
  - Observable: `CommandBuilder` class exists in `command_builder.py`. Consolidates `build_claude_command`, `build_scaffolding_prompt`, `build_triage_command`, `build_fix_command`, `build_ci_fix_command`, `build_feedback_command` into methods with shared interactive/non-interactive logic.
  - Evidence: Pre-commit checklist passes. The `if interactive: ... else: ...` pattern exists in one place.
  - Steps:
    - [ ] Write unit tests for CommandBuilder methods
    - [ ] Implement CommandBuilder class
    - [ ] Update ClaudeRunner and callers to use CommandBuilder
    - [ ] Remove standalone build_* functions from `implement.py`
    - [ ] Run pre-commit checklist (ruff, CodeScene safeguard, `./test-scripts/test-end-to-end.sh`)

---

## Steel Thread 5: Extract Execution Modes and Slim implement_cmd
Replace the 180-line `implement_cmd` with a thin dispatcher and three execution mode classes.

- [ ] **Task 5.1: Extract TrunkMode**
  - TaskType: OUTCOME
  - Entrypoint: `uv run --with pytest --with pytest-mock pytest tests/implement/ -v`
  - Observable: `TrunkMode` class exists in `trunk_mode.py`. Accepts `GitRepository`, `IdeaProject`, `ClaudeRunner` as constructor arguments. `execute()` method contains the task loop. `implement_cmd` delegates to `TrunkMode` when `--trunk` is set.
  - Evidence: Pre-commit checklist passes. `test_trunk_mode.py` tests use zero `@patch` decorators.
  - Steps:
    - [ ] Write tests for TrunkMode.execute() using fakes
    - [ ] Implement TrunkMode class
    - [ ] Update `implement_cmd` trunk branch to construct and call TrunkMode
    - [ ] Remove `run_trunk_loop` from `implement.py`
    - [ ] Migrate remaining `test_trunk_mode.py` tests from @patch to fakes
    - [ ] Run pre-commit checklist (ruff, CodeScene safeguard, `./test-scripts/test-end-to-end.sh`)

- [ ] **Task 5.2: Extract WorktreeMode**
  - TaskType: OUTCOME
  - Entrypoint: `uv run --with pytest --with pytest-mock pytest tests/implement/ -v`
  - Observable: `WorktreeMode` class exists in `worktree_mode.py`. Encapsulates the worktree + PR + CI loop. Accepts `GitRepository`, `IdeaProject`, `WorkflowState`, `ClaudeRunner`. `implement_cmd` default path delegates to `WorktreeMode`.
  - Evidence: Pre-commit checklist passes. `test_cli_integration.py` tests use drastically fewer patches.
  - Steps:
    - [ ] Write tests for WorktreeMode.execute() using fakes
    - [ ] Implement WorktreeMode class
    - [ ] Update `implement_cmd` default branch to construct and call WorktreeMode
    - [ ] Migrate `test_cli_integration.py` tests from @patch to fakes
    - [ ] Run pre-commit checklist (ruff, CodeScene safeguard, `./test-scripts/test-end-to-end.sh`)

- [ ] **Task 5.3: Extract IsolateMode and final cleanup**
  - TaskType: OUTCOME
  - Entrypoint: `uv run --with pytest --with pytest-mock pytest tests/implement/ -v`
  - Observable: `IsolateMode` class exists in `isolate_mode.py`. `implement_cmd` is a thin dispatcher (<50 lines): validate → select mode → execute. `implement.py` contains only `process_pr_feedback`, `check_claude_success`, `print_task_failure_diagnostics` and pure helpers (sanitize_branch_name, generate_pr_title, etc.) — all under 300 lines total.
  - Evidence: Pre-commit checklist passes. No test file uses `unittest.mock.patch`. `implement.py` is under 300 lines.
  - Steps:
    - [ ] Write tests for IsolateMode using fakes
    - [ ] Implement IsolateMode class
    - [ ] Reduce `implement_cmd` to thin dispatcher
    - [ ] Move remaining pure helpers into appropriate class files
    - [ ] Verify `implement.py` is under 300 lines or deleted
    - [ ] Audit all test files: no `from unittest.mock import patch` remains
    - [ ] Run pre-commit checklist (ruff, CodeScene safeguard, `./test-scripts/test-end-to-end.sh`)

---

## Summary

This plan extracts 9 classes across 5 threads from the 2332-line procedural `implement.py`:

| Thread | Extractions | Key Outcome |
|--------|------------|-------------|
| 1 | IdeaProject, WorkflowState | Eliminate `(idea_directory, idea_name)` parameter pairs and raw dict state |
| 2 | GitHubClient | Eliminate ~15 duplicate MockResult classes, create injectable GitHub abstraction |
| 3 | GitRepository | Eliminate `slice_branch`/`pr_number` parameter threading, unify Git access |
| 4 | ClaudeRunner, CommandBuilder | Eliminate mock_claude conditionals, consolidate 6 build_* functions |
| 5 | TrunkMode, WorktreeMode, IsolateMode | Replace 180-line if/elif with polymorphism, achieve zero `@patch` in tests |

Each thread is independently committable and leaves all tests passing. The order matters: Thread 1 creates value objects used everywhere, Thread 2-3 create the injectable infrastructure, Thread 4 handles Claude invocation, and Thread 5 wires it all together.
