Now I have everything I need. Here's the plan:

---

# ClaudeRunner: interactive as constructor argument — Plan

## Idea Type

**C. Platform/infrastructure capability** — This is a pure internal refactoring of the `ClaudeRunner` API. No user-facing behavior changes.

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

- NEVER write production code (`src/main/java/**/*.java`) without first writing a failing test
- Before using Write on any `.java` file in `src/main/`, ask: "Do I have a failing test?" If not, write the test first
- When task direction changes mid-implementation, return to TDD PLANNING state and write a test first

### Verification Requirements

- Hard rule: NEVER git commit, git push, or open a PR unless you have successfully run the project's test command and it exits 0
- Hard rule: If running tests is blocked for any reason (including permissions), ALWAYS STOP immediately. Print the failing command, the exact error output, and the permission/path required
- Before committing, ALWAYS print a Verification section containing the exact test command (NOT an ad-hoc command - it must be a proper test command such as `./test-scripts/*.sh`, `./scripts/test.sh`, or `./gradlew build`/`./gradlew check`), its exit code, and the last 20 lines of output

## Steel Thread 1: ClaudeRunner interactive dispatch and consumer migration

All tasks use TDD. The test command is: `uv run --with pytest --with pytest-mock pytest tests/implement/ -v -m unit`

- [ ] **Task 1.1: ClaudeRunner.run() dispatches to run_interactive or run_with_capture based on interactive constructor argument**
  - TaskType: OUTCOME
  - Entrypoint: `uv run --with pytest --with pytest-mock pytest tests/implement/test_claude_runner.py -v -m unit`
  - Observable: `ClaudeRunner(interactive=True).run(cmd, cwd)` delegates to `run_interactive`; `ClaudeRunner(interactive=False).run(cmd, cwd)` delegates to `run_with_capture`. Constructor accepts `interactive: bool = True`.
  - Evidence: Two new unit tests in `TestClaudeRunnerRun` class pass — one for `interactive=True`, one for `interactive=False`
  - Steps:
    - [ ] Write a new `TestClaudeRunnerRun` test class in `tests/implement/test_claude_runner.py` with two tests:
      - `test_run_delegates_to_run_interactive_when_interactive_true`: Instantiate `ClaudeRunner(interactive=True)`, mock `run_interactive`, call `run()`, assert `run_interactive` was called
      - `test_run_delegates_to_run_with_capture_when_interactive_false`: Instantiate `ClaudeRunner(interactive=False)`, mock `run_with_capture`, call `run()`, assert `run_with_capture` was called
    - [ ] Add `interactive: bool = True` parameter to `ClaudeRunner.__init__()` in `src/i2code/implement/claude_runner.py`, store as `self._interactive`
    - [ ] Add `run(self, cmd: List[str], cwd: str) -> ClaudeResult` method to `ClaudeRunner` that dispatches based on `self._interactive`

- [ ] **Task 1.2: FakeClaudeRunner accepts interactive and records run() calls**
  - TaskType: REFACTOR
  - Entrypoint: `uv run --with pytest --with pytest-mock pytest tests/implement/test_claude_runner.py -v -m unit`
  - Observable: No behavior change for existing methods; new `run()` method records `("run", cmd, cwd)` tuples
  - Evidence: Existing `TestFakeClaudeRunner` tests pass, plus new `test_records_run_call` test passes
  - Steps:
    - [ ] Add `test_records_run_call` to `TestFakeClaudeRunner` in `tests/implement/test_claude_runner.py`: call `fake.run(cmd, cwd)` and assert `fake.calls == [("run", cmd, cwd)]`
    - [ ] Add `interactive: bool = True` parameter to `FakeClaudeRunner.__init__()` in `tests/implement/fake_claude_runner.py`, store as `self._interactive`
    - [ ] Add `run(self, cmd, cwd)` method to `FakeClaudeRunner` that appends `("run", cmd, cwd)` and returns `self._next_result()`
    - [ ] Update the docstring example in `FakeClaudeRunner` to show the `run()` method

- [ ] **Task 1.3: cli.py passes interactive when constructing ClaudeRunner**
  - TaskType: REFACTOR
  - Entrypoint: `uv run --with pytest --with pytest-mock pytest tests/implement/ -v -m unit`
  - Observable: No behavior change — default `interactive=True` matches previous behavior; `--non-interactive` flag now sets `interactive=False` at construction
  - Evidence: All existing unit tests pass unchanged
  - Steps:
    - [ ] In `src/i2code/implement/cli.py:55` `implement_cmd()`: change `ClaudeRunner()` to `ClaudeRunner(interactive=not opts.non_interactive)`
    - [ ] In `src/i2code/implement/cli.py:93` `scaffold_cmd()`: change `ClaudeRunner()` to `ClaudeRunner(interactive=not non_interactive)`

- [ ] **Task 1.4: TrunkMode._run_claude() uses runner.run() instead of if/else dispatch**
  - TaskType: REFACTOR
  - Entrypoint: `uv run --with pytest --with pytest-mock pytest tests/implement/test_trunk_mode.py -v -m unit`
  - Observable: No behavior change — TrunkMode produces identical results for both interactive and non-interactive execution
  - Evidence: All `TestTrunkModeExecute` tests pass with updated assertions
  - Steps:
    - [ ] In `src/i2code/implement/trunk_mode.py`: simplify `_run_claude(self, claude_cmd, non_interactive)` to `_run_claude(self, claude_cmd)` — remove the `non_interactive` parameter and replace the if/else with `return self._claude_runner.run(claude_cmd, cwd=self._git_repo.working_tree_dir)`
    - [ ] Update the call site at `src/i2code/implement/trunk_mode.py:51`: change `self._run_claude(claude_cmd, non_interactive)` to `self._run_claude(claude_cmd)`
    - [ ] In `tests/implement/test_trunk_mode.py`:
      - `test_invokes_claude_for_first_task` at `tests/implement/test_trunk_mode.py:75`: change assertion from `method == "run_interactive"` to `method == "run"`
      - `test_non_interactive_uses_run_with_capture` at `tests/implement/test_trunk_mode.py:205`: change assertion from `method == "run_with_capture"` to `method == "run"`, and update class/method docstring

- [ ] **Task 1.5: WorktreeMode._run_claude() uses runner.run() instead of if/else dispatch**
  - TaskType: REFACTOR
  - Entrypoint: `uv run --with pytest --with pytest-mock pytest tests/implement/test_worktree_mode.py -v -m unit`
  - Observable: No behavior change — WorktreeMode produces identical results for both interactive and non-interactive execution
  - Evidence: All `TestWorktreeMode*` tests pass with updated assertions
  - Steps:
    - [ ] In `src/i2code/implement/worktree_mode.py`: simplify `_run_claude(self, claude_cmd)` — replace the if/else block with `return self._claude_runner.run(claude_cmd, cwd=self._git_repo.working_tree_dir)`
    - [ ] In `tests/implement/test_worktree_mode.py`:
      - `test_non_interactive_uses_capture_and_checks_success_tag` at `tests/implement/test_worktree_mode.py:386`: change assertion from `method == "run_with_capture"` to `method == "run"`, and update class docstring

- [ ] **Task 1.6: ProjectSetup.run_scaffolding() uses runner.run() instead of if/else dispatch**
  - TaskType: REFACTOR
  - Entrypoint: `uv run --with pytest --with pytest-mock pytest tests/implement/test_project_setup.py -v -m unit`
  - Observable: No behavior change — run_scaffolding() produces identical results for both interactive and non-interactive execution
  - Evidence: All `TestRunScaffolding` tests pass with updated assertions
  - Steps:
    - [ ] In `src/i2code/implement/project_setup.py:67-70` `run_scaffolding()`: replace the if/else dispatch with `result = self._claude_runner.run(cmd, cwd=cwd)`. Keep the `interactive` parameter (needed for `build_scaffolding_command` and the `if interactive or "<SUCCESS>" ...` check)
    - [ ] In `tests/implement/test_project_setup.py`:
      - `test_interactive_calls_run_interactive` at `tests/implement/test_project_setup.py:196`: change assertion from `method == "run_interactive"` to `method == "run"`, rename test to `test_interactive_calls_run`
      - `test_non_interactive_calls_run_with_capture` at `tests/implement/test_project_setup.py:215`: change assertion from `method == "run_with_capture"` to `method == "run"`, rename test to `test_non_interactive_calls_run`
      - `test_forwards_mock_claude` at `tests/implement/test_project_setup.py:232`: change assertion from `method == "run_interactive"` to `method == "run"`

- [ ] **Task 1.7: GithubActionsBuildFixer._invoke_claude_for_fix() uses runner.run() instead of if/else dispatch**
  - TaskType: REFACTOR
  - Entrypoint: `uv run --with pytest --with pytest-mock pytest tests/implement/test_github_actions_build_fixer.py -v -m unit`
  - Observable: No behavior change — _invoke_claude_for_fix() produces identical results for both interactive and non-interactive execution
  - Evidence: All `TestGithubActionsBuildFixer` tests pass with updated assertions
  - Steps:
    - [ ] In `src/i2code/implement/github_actions_build_fixer.py:142-145` `_invoke_claude_for_fix()`: replace the if/else dispatch with `self._claude_runner.run(claude_cmd, cwd=self._git_repo.working_tree_dir)`. Keep the local `interactive` variable (needed for `build_ci_fix_command`)
    - [ ] At `tests/implement/test_github_actions_build_fixer.py:118`: change assertion from `fake_runner.calls[0][0] == "run_with_capture"` to `fake_runner.calls[0][0] == "run"`

- [ ] **Task 1.8: PullRequestReviewProcessor._invoke_fix() uses runner.run() instead of if/else dispatch**
  - TaskType: REFACTOR
  - Entrypoint: `uv run --with pytest --with pytest-mock pytest tests/implement/test_pull_request_review_processor.py -v -m unit`
  - Observable: No behavior change — _invoke_fix() produces identical results; _run_triage() continues calling run_with_capture() directly
  - Evidence: All `TestProcessPrFeedback*` tests pass with updated assertions
  - Steps:
    - [ ] In `src/i2code/implement/pull_request_review_processor.py:265-268` `_invoke_fix()`: replace the if/else dispatch with `self._claude_runner.run(fix_cmd, cwd=self._git_repo.working_tree_dir)`. Keep the local `interactive` variable (needed for `build_fix_command`)
    - [ ] Verify `_run_triage()` at `src/i2code/implement/pull_request_review_processor.py:175` still calls `run_with_capture()` directly — no changes needed
    - [ ] In `tests/implement/test_pull_request_review_processor.py`:
      - `test_triage_uses_claude_runner_run_with_capture` at `tests/implement/test_pull_request_review_processor.py:153`: **no change** — triage still uses `run_with_capture`
      - `test_fix_interactive_uses_run_interactive` at `tests/implement/test_pull_request_review_processor.py:236`: change second assertion from `fake_claude.calls[1][0] == "run_interactive"` to `fake_claude.calls[1][0] == "run"`, rename test to `test_fix_interactive_uses_run`

## Change History

- **2026-02-22:** Standardized all file references to use relative paths with suffix in backticks (e.g., `src/i2code/implement/cli.py`) and all location references to use `path:linenumber` format in backticks (e.g., `src/i2code/implement/cli.py:55`). Replaced bare "(line N)" annotations throughout all tasks.
