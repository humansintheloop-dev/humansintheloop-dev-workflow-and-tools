Now I have all the information I need. Let me compose the plan.

# Project Initializer - Implementation Plan

## Idea Type

**C. Platform/infrastructure capability** - This is an internal capability that ensures project scaffolding (CI, build system, placeholder code) is pushed from the host before delegating to an isolarium VM, working around GitHub App token limitations.

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
- Before using Write on any `.py` file in `src/i2code/`, ask: "Do I have a failing test?" If not, write the test first
- When task direction changes mid-implementation, return to TDD PLANNING state and write a test first

### Verification Requirements

- Hard rule: NEVER git commit, git push, or open a PR unless you have successfully run the project's test command and it exits 0
- Hard rule: If running tests is blocked for any reason (including permissions), ALWAYS STOP immediately. Print the failing command, the exact error output, and the permission/path required
- Before committing, ALWAYS print a Verification section containing the exact test command (NOT an ad-hoc command - it must be a proper test command such as `uv run --with pytest pytest tests/implement/`), its exit code, and the last 20 lines of output

## Overview

This plan implements the Project Initializer as two capabilities:

1. **CAP-1**: `ensure_project_setup()` — runs on the host in the `--isolate` code path to generate project scaffolding via Claude, push it, and wait for CI before delegating to isolarium.
2. **CAP-2**: `ensure_integration_branch()` remote tracking — when running `--isolated` inside the VM, create a local tracking branch from the remote integration branch instead of creating from HEAD.

The plan is organized so each steel thread delivers one independently testable behavior, building incrementally from the simplest change (remote tracking) through the full scaffolding flow.

### Key Conventions

- Test runner: `uv run --with pytest pytest tests/implement/`
- Source module: `src/i2code/implement/implement.py`
- CLI module: `src/i2code/implement/cli.py`
- Test directory: `tests/implement/`
- Existing test patterns: `@pytest.mark.unit` for fast tests, `@pytest.mark.integration` for tests requiring real git

---

## Steel Thread 1: Integration Branch Remote Tracking (CAP-2)

This thread modifies `ensure_integration_branch()` to support remote branch tracking when running in `--isolated` mode. This is the simplest change and is needed by the VM to pick up scaffolding pushed by the host.

- [x] **Task 1.1: `ensure_integration_branch()` creates local tracking branch from remote when `isolated=True`**
  - TaskType: OUTCOME
  - Entrypoint: `uv run --with pytest pytest tests/implement/test_git_infrastructure.py -k "integration_branch"`
  - Observable: When `isolated=True` and the local branch does not exist but `origin/{branch_name}` does, a local tracking branch is created from the remote ref. When neither exists, falls back to creating from HEAD. When the local branch already exists, it is reused regardless of `isolated` flag. When `isolated=False` (default), behavior is unchanged — always creates from HEAD.
  - Evidence: Unit tests verify all four scenarios: (1) isolated + remote exists → tracks remote, (2) isolated + no remote → creates from HEAD, (3) isolated + local exists → reuses local, (4) non-isolated (default) → unchanged behavior
  - Steps:
    - [x] Add unit tests to `tests/implement/test_git_infrastructure.py` for the four scenarios above. Use `monkeypatch` or `mocker` to simulate remote refs on the `Repo` object. Tests should fail because `ensure_integration_branch()` does not yet accept `isolated` parameter.
    - [x] Modify `ensure_integration_branch()` in `src/i2code/implement/implement.py` to accept `isolated: bool = False`. When `isolated=True` and local branch does not exist, check `repo.remotes.origin.refs` for `idea/{idea_name}/integration`. If found, create local branch tracking the remote ref. Otherwise, fall back to creating from HEAD.
    - [x] Verify all new and existing tests pass

- [x] **Task 1.2: `--isolated` CLI path passes `isolated=True` to `ensure_integration_branch()`**
  - TaskType: OUTCOME
  - Entrypoint: `uv run --with pytest pytest tests/implement/test_cli_integration.py -k "isolated"`
  - Observable: When `--isolated` flag is set, `ensure_integration_branch()` is called with `isolated=True`. When `--isolated` is not set, it is called with `isolated=False` (default).
  - Evidence: Unit test mocks `ensure_integration_branch` and verifies the `isolated` keyword argument matches the CLI flag
  - Steps:
    - [x] Add a unit test that patches `ensure_integration_branch` and invokes the CLI with `--isolated`, asserting `isolated=True` was passed. Add a corresponding test for the non-isolated path asserting default behavior.
    - [x] Modify `src/i2code/implement/cli.py` to pass `isolated=isolated` to the `ensure_integration_branch()` call (line 111). Import the updated function signature.
    - [x] Verify all tests pass

---

## Steel Thread 2: Scaffolding Prompt Construction (CAP-1 foundation)

This thread implements the `build_scaffolding_prompt()` function that constructs the Claude command for project scaffolding. It is a pure function with no side effects, making it easy to test in isolation.

- [ ] **Task 2.1: `build_scaffolding_prompt()` constructs Claude command referencing idea files**
  - TaskType: OUTCOME
  - Entrypoint: `uv run --with pytest pytest tests/implement/test_project_setup.py -k "scaffolding_prompt"`
  - Observable: Returns a list suitable for `subprocess` that includes: the `claude` command, a goal-oriented prompt referencing the idea directory files (`*-idea.*`, `*-spec.md`), and appropriate flags for interactive vs non-interactive mode.
  - Evidence: Unit tests verify: (1) interactive mode returns `["claude", <prompt>]`, (2) non-interactive mode returns `["claude", "--verbose", "--output-format=stream-json", "-p", <prompt>]`, (3) prompt references the idea directory files, (4) prompt describes the desired scaffolding outcome (Gradle skeleton, test scripts, ci.yaml) without prescribing specific versions
  - Steps:
    - [ ] Create `tests/implement/test_project_setup.py` with unit tests for `build_scaffolding_prompt()` covering interactive and non-interactive modes, and verifying prompt content references idea files and describes goal-oriented scaffolding outcomes
    - [ ] Implement `build_scaffolding_prompt(idea_directory, interactive=True)` in `src/i2code/implement/implement.py`. The prompt should describe the desired outcome: minimal buildable project with CI, placeholder code, appropriate build system based on idea files, and `ci.yaml` that validates the scaffolding. Return command as a list suitable for subprocess.
    - [ ] Verify all tests pass

- [ ] **Task 2.2: `build_scaffolding_prompt()` supports `--mock-claude` substitution**
  - TaskType: OUTCOME
  - Entrypoint: `uv run --with pytest pytest tests/implement/test_project_setup.py -k "mock_claude"`
  - Observable: When `mock_claude` path is provided, returns `[mock_script, "setup"]` instead of the Claude command. When `mock_claude` is `None`, returns the normal Claude command.
  - Evidence: Unit tests verify mock substitution produces `[mock_script, "setup"]` and `None` produces normal Claude command
  - Steps:
    - [ ] Add unit tests for mock_claude substitution in `tests/implement/test_project_setup.py`
    - [ ] Add `mock_claude: Optional[str] = None` parameter to `build_scaffolding_prompt()`. When set, return `[mock_claude, "setup"]` instead of the Claude command.
    - [ ] Verify all tests pass

---

## Steel Thread 3: Project Setup Orchestration (CAP-1 core)

This thread implements `ensure_project_setup()`, which orchestrates the full scaffolding flow: checkout integration branch, invoke Claude, detect new commits, push, and wait for CI.

- [ ] **Task 3.1: `ensure_project_setup()` checks out integration branch and invokes Claude for scaffolding**
  - TaskType: OUTCOME
  - Entrypoint: `uv run --with pytest pytest tests/implement/test_project_setup.py -k "ensure_project_setup"`
  - Observable: Function checks out the integration branch, invokes Claude (or mock) with the scaffolding prompt, and returns `True` when scaffolding succeeds. The working directory for Claude invocation is the repo working tree.
  - Evidence: Unit tests mock `run_claude_interactive`/`run_claude_with_output_capture`, `push_branch_to_remote`, and `wait_for_workflow_completion`. Verify: (1) integration branch is checked out before Claude invocation, (2) Claude is invoked with scaffolding prompt and correct cwd, (3) interactive mode calls `run_claude_interactive`, non-interactive calls `run_claude_with_output_capture`
  - Steps:
    - [ ] Add unit tests for `ensure_project_setup()` in `tests/implement/test_project_setup.py` that mock git operations, Claude invocation, push, and CI wait. Test both interactive and non-interactive modes.
    - [ ] Implement `ensure_project_setup()` in `src/i2code/implement/implement.py` with signature matching the spec. The function should: (1) checkout the integration branch, (2) record HEAD SHA before Claude, (3) invoke Claude using `build_scaffolding_prompt()` result and appropriate runner based on `interactive` flag, (4) record HEAD SHA after Claude.
    - [ ] Verify all tests pass

- [ ] **Task 3.2: `ensure_project_setup()` skips push and CI when no new commits are made**
  - TaskType: OUTCOME
  - Entrypoint: `uv run --with pytest pytest tests/implement/test_project_setup.py -k "no_new_commits"`
  - Observable: When Claude makes no commits (HEAD SHA unchanged after invocation), the function skips pushing and CI wait, and returns `True`.
  - Evidence: Unit test simulates Claude making no commits (HEAD unchanged). Verifies `push_branch_to_remote` and `wait_for_workflow_completion` are NOT called, and function returns `True`.
  - Steps:
    - [ ] Add unit test where HEAD SHA does not change after Claude invocation. Assert push and CI wait are not called, and return value is `True`.
    - [ ] Implement the no-new-commits detection in `ensure_project_setup()`: compare HEAD before and after Claude invocation. If unchanged, skip push/CI and return `True`.
    - [ ] Verify all tests pass

- [ ] **Task 3.3: `ensure_project_setup()` pushes and waits for CI when Claude makes commits**
  - TaskType: OUTCOME
  - Entrypoint: `uv run --with pytest pytest tests/implement/test_project_setup.py -k "push_and_ci"`
  - Observable: When Claude makes commits (HEAD advances), the function pushes the integration branch and waits for CI. Returns `True` when CI passes.
  - Evidence: Unit test simulates HEAD advancing after Claude. Verifies `push_branch_to_remote` is called with the integration branch name, `wait_for_workflow_completion` is called with the branch and new SHA, and function returns `True` when CI succeeds.
  - Steps:
    - [ ] Add unit test where HEAD advances after Claude invocation and CI passes. Assert push and CI wait are called with correct arguments, and return value is `True`.
    - [ ] Implement the push-and-CI-wait path in `ensure_project_setup()`: call `push_branch_to_remote(integration_branch)`, then `wait_for_workflow_completion(integration_branch, new_sha, ci_timeout)`. Return the CI result.
    - [ ] Verify all tests pass

- [ ] **Task 3.4: `ensure_project_setup()` invokes `fix_ci_failure()` when CI fails**
  - TaskType: OUTCOME
  - Entrypoint: `uv run --with pytest pytest tests/implement/test_project_setup.py -k "ci_failure_retry"`
  - Observable: When CI fails after pushing scaffolding, `fix_ci_failure()` is invoked with the integration branch, new SHA, repo working tree path, and the configured retry/interactive/mock parameters. Returns the result of `fix_ci_failure()`.
  - Evidence: Unit test simulates CI failure after push. Verifies `fix_ci_failure()` is called with correct arguments including `max_retries=ci_fix_retries`, `interactive`, and `mock_claude`. Return value matches `fix_ci_failure()` result.
  - Steps:
    - [ ] Add unit test where CI fails after push. Mock `fix_ci_failure` and verify it is called with correct arguments. Test both success and failure return values.
    - [ ] Implement CI failure handling: when `wait_for_workflow_completion` returns `(False, failing_run)`, call `fix_ci_failure()` with the integration branch, new SHA, repo working tree, `ci_fix_retries`, `interactive`, and `mock_claude`.
    - [ ] Verify all tests pass

- [ ] **Task 3.5: `ensure_project_setup()` respects `skip_ci_wait` flag**
  - TaskType: OUTCOME
  - Entrypoint: `uv run --with pytest pytest tests/implement/test_project_setup.py -k "skip_ci_wait"`
  - Observable: When `skip_ci_wait=True` and Claude makes commits, the function pushes but does not wait for CI. Returns `True` immediately after push.
  - Evidence: Unit test with `skip_ci_wait=True` and HEAD advancing. Verifies push is called but `wait_for_workflow_completion` is NOT called. Return value is `True`.
  - Steps:
    - [ ] Add unit test with `skip_ci_wait=True` where Claude makes commits. Assert push is called, CI wait is not called, and function returns `True`.
    - [ ] Add `skip_ci_wait` handling to `ensure_project_setup()`: after push, if `skip_ci_wait` is `True`, return `True` without waiting.
    - [ ] Verify all tests pass

---

## Steel Thread 4: CLI Integration (`--isolate` code path)

This thread wires `ensure_project_setup()` into the `--isolate` CLI code path so scaffolding runs on the host before delegation to isolarium.

- [ ] **Task 4.1: `--isolate` code path calls `ensure_project_setup()` before delegating to isolarium**
  - TaskType: OUTCOME
  - Entrypoint: `uv run --with pytest pytest tests/implement/test_project_setup.py -k "cli_isolate"`
  - Observable: When `--isolate` is set, the CLI creates the integration branch, calls `ensure_project_setup()` with the repo, idea directory, idea name, integration branch, and all relevant options (interactive, mock_claude, ci_fix_retries, ci_timeout, skip_ci_wait), and only delegates to isolarium if setup succeeds. If setup fails, exits with error code without delegating.
  - Evidence: Unit tests mock `ensure_project_setup`, `ensure_integration_branch`, and `subprocess.run` (for isolarium). Verify: (1) `ensure_integration_branch` is called before `ensure_project_setup`, (2) `ensure_project_setup` is called with correct arguments, (3) isolarium delegation only happens after successful setup, (4) CLI exits with error when setup fails.
  - Steps:
    - [ ] Add unit tests to `tests/implement/test_project_setup.py` (or a new `tests/implement/test_cli_isolate.py` if cleaner) that mock `ensure_integration_branch`, `ensure_project_setup`, and `subprocess.run`. Test: setup success → isolarium delegated, setup failure → exit with error, all parameters forwarded correctly.
    - [ ] Restructure the `--isolate` code path in `src/i2code/implement/cli.py` (lines 77-102): after validation, call `ensure_integration_branch(repo, idea_name)` to get/create the integration branch, then call `ensure_project_setup()` with the appropriate parameters. Only proceed to build and run the isolarium command if setup returns `True`. If setup fails, print error and `sys.exit(1)`.
    - [ ] Add `ensure_project_setup` and `build_scaffolding_prompt` to the imports in `cli.py`
    - [ ] Verify all tests pass

- [ ] **Task 4.2: `--isolate` forwards `--non-interactive` mode correctly to `ensure_project_setup()`**
  - TaskType: OUTCOME
  - Entrypoint: `uv run --with pytest pytest tests/implement/test_project_setup.py -k "non_interactive_isolate"`
  - Observable: When `--isolate --non-interactive` is set, `ensure_project_setup()` is called with `interactive=False`. When `--isolate` is set without `--non-interactive`, `ensure_project_setup()` is called with `interactive=True`.
  - Evidence: Unit tests mock `ensure_project_setup` and invoke CLI with and without `--non-interactive`. Verify the `interactive` argument matches the flag.
  - Steps:
    - [ ] Add unit tests for interactive and non-interactive modes in the `--isolate` path
    - [ ] Ensure the CLI passes `interactive=not non_interactive` to `ensure_project_setup()`
    - [ ] Verify all tests pass

---

## Steel Thread 5: Integration Test with Mock Claude

This thread adds an integration test that exercises the full `ensure_project_setup()` flow using a mock Claude script, verifying end-to-end behavior without real Claude invocations.

- [ ] **Task 5.1: Integration test verifies `ensure_project_setup()` with mock Claude script**
  - TaskType: INFRA
  - Entrypoint: `uv run --with pytest pytest tests/implement/test_project_setup_integration.py -k "mock_claude_setup"`
  - Observable: A mock Claude script creates a placeholder file and commits it. `ensure_project_setup()` invokes the mock, detects the new commit, and the function completes. The integration branch contains the mock-created commit.
  - Evidence: Integration test creates a temporary git repo with a remote, a mock Claude script that creates a file and commits, calls `ensure_project_setup()` with `mock_claude` and `skip_ci_wait=True`, and verifies: (1) the integration branch has the mock commit, (2) the function returns `True`.
  - Steps:
    - [ ] Create `tests/implement/test_project_setup_integration.py` with a `@pytest.mark.integration` test. The test should: create a temp git repo with an initial commit, set up a bare remote, create a mock Claude script that writes a file and commits, call `ensure_project_setup()` with `mock_claude` and `skip_ci_wait=True`, and verify the integration branch has the new commit and the function returns `True`.
    - [ ] Create the mock Claude script as a fixture (a bash script that creates `scaffolding.txt`, `git add`, `git commit`). The script should receive `"setup"` as its argument (matching `build_scaffolding_prompt` mock convention).
    - [ ] Verify the integration test passes

- [ ] **Task 5.2: Integration test verifies `ensure_project_setup()` is idempotent (no-op on repeat run)**
  - TaskType: INFRA
  - Entrypoint: `uv run --with pytest pytest tests/implement/test_project_setup_integration.py -k "idempotent"`
  - Observable: When `ensure_project_setup()` is called a second time and the mock Claude makes no new commits, the function returns `True` without pushing.
  - Evidence: Integration test runs `ensure_project_setup()` twice with a mock that only creates files if they don't exist. Second run detects no new commits and returns `True` without error.
  - Steps:
    - [ ] Add an integration test that runs `ensure_project_setup()` twice. The mock Claude script should be idempotent (only creates files if missing, uses `git diff --cached` to avoid empty commits). Verify second run returns `True` and the branch has only the commits from the first run.
    - [ ] Verify the integration test passes

---

## Change History

(Append rationale for any plan modifications here)
