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

- [x] **Task 1.1: Rename run_with_capture to run_batch in ClaudeRunner and FakeClaudeRunner and all callers**
  - TaskType: REFACTOR
  - Entrypoint: `uv run --with pytest --with pytest-mock pytest tests/implement/ -v -m unit`
  - Observable: All references to run_with_capture are renamed to run_batch across production code and tests
  - Evidence: `All existing unit tests pass with updated method name`
  - Steps:
    - [x] Rename run_with_capture to run_batch in ClaudeRunner class at src/i2code/implement/claude_runner.py:246
    - [x] Rename run_with_capture to run_batch in FakeClaudeRunner class at tests/implement/fake_claude_runner.py:54
    - [x] Rename run_with_capture to run_batch in module-level function run_claude_with_output_capture — update the call in ClaudeRunner.run_batch to call run_claude_with_output_capture (function name unchanged, only the method name changes)
    - [x] Update all direct callers: src/i2code/implement/commit_recovery.py:55, src/i2code/implement/pull_request_review_processor.py:175
    - [x] Update all test assertions that reference "run_with_capture" to "run_batch" across test files: test_claude_runner.py, test_trunk_mode.py, test_worktree_mode.py, test_github_actions_build_fixer.py, test_pull_request_review_processor.py
- [x] **Task 1.2: ClaudeRunner.run() dispatches to run_interactive or run_batch based on interactive constructor argument**
  - TaskType: OUTCOME
  - Entrypoint: `uv run --with pytest --with pytest-mock pytest tests/implement/test_claude_runner.py -v -m unit`
  - Observable: `ClaudeRunner(interactive=True).run(cmd, cwd)` delegates to `run_interactive`; `ClaudeRunner(interactive=False).run(cmd, cwd)` delegates to `run_batch`. Constructor accepts `interactive: bool = True`.
  - Evidence: Two new unit tests in `TestClaudeRunnerRun` class pass — one for `interactive=True`, one for `interactive=False`
  - Steps:
    - [x] Write a new `TestClaudeRunnerRun` test class in `tests/implement/test_claude_runner.py` with two tests:
      - `test_run_delegates_to_run_interactive_when_interactive_true`: Instantiate `ClaudeRunner(interactive=True)`, mock `run_interactive`, call `run()`, assert `run_interactive` was called
      - `test_run_delegates_to_run_batch_when_interactive_false`: Instantiate `ClaudeRunner(interactive=False)`, mock `run_batch`, call `run()`, assert `run_batch` was called
    - [x] Add `interactive: bool = True` parameter to `ClaudeRunner.__init__()` in `src/i2code/implement/claude_runner.py`, store as `self._interactive`
    - [x] Add `run(self, cmd: List[str], cwd: str) -> ClaudeResult` method to `ClaudeRunner` that dispatches based on `self._interactive`

- [x] **Task 1.3: FakeClaudeRunner accepts interactive and records run() calls**
  - TaskType: REFACTOR
  - Entrypoint: `uv run --with pytest --with pytest-mock pytest tests/implement/test_claude_runner.py -v -m unit`
  - Observable: No behavior change for existing methods; new `run()` method records `("run", cmd, cwd)` tuples
  - Evidence: Existing `TestFakeClaudeRunner` tests pass, plus new `test_records_run_call` test passes
  - Steps:
    - [x] Add `test_records_run_call` to `TestFakeClaudeRunner` in `tests/implement/test_claude_runner.py`: call `fake.run(cmd, cwd)` and assert `fake.calls == [("run", cmd, cwd)]`
    - [x] Add `interactive: bool = True` parameter to `FakeClaudeRunner.__init__()` in `tests/implement/fake_claude_runner.py`, store as `self._interactive`
    - [x] Add `run(self, cmd, cwd)` method to `FakeClaudeRunner` that appends `("run", cmd, cwd)` and returns `self._next_result()`
    - [x] Update the docstring example in `FakeClaudeRunner` to show the `run()` method

- [x] **Task 1.4: command_assembler.py passes interactive when constructing ClaudeRunner**
  - TaskType: REFACTOR
  - Entrypoint: `uv run --with pytest --with pytest-mock pytest tests/implement/ -v -m unit`
  - Observable: No behavior change — default `interactive=True` matches previous behavior; `--non-interactive` flag now sets `interactive=False` at construction
  - Evidence: All existing unit tests pass unchanged
  - Steps:
    - [x] In `src/i2code/implement/command_assembler.py:24` `assemble_implement()`: change `ClaudeRunner()` to `ClaudeRunner(interactive=not opts.non_interactive)`
    - [x] In `src/i2code/implement/command_assembler.py:54` `assemble_scaffold()`: change `ClaudeRunner()` to `ClaudeRunner(interactive=not opts.non_interactive)`

- [x] **Task 1.5: TrunkMode._run_claude() uses runner.run() instead of if/else dispatch**
  - TaskType: REFACTOR
  - Entrypoint: `uv run --with pytest --with pytest-mock pytest tests/implement/test_trunk_mode.py -v -m unit`
  - Observable: No behavior change — TrunkMode produces identical results for both interactive and non-interactive execution
  - Evidence: All `TestTrunkModeExecute` tests pass with updated assertions
  - Steps:
    - [x] In `src/i2code/implement/trunk_mode.py:86-90`: simplify `_run_claude(self, claude_cmd, non_interactive)` to `_run_claude(self, claude_cmd)` — remove the `non_interactive` parameter and replace the if/else with `return self._claude_runner.run(claude_cmd, cwd=self._git_repo.working_tree_dir)`
    - [x] Update the call site at `src/i2code/implement/trunk_mode.py:54`: change `self._run_claude(claude_cmd, non_interactive)` to `self._run_claude(claude_cmd)`
    - [x] In `tests/implement/test_trunk_mode.py`:
      - `test_invokes_claude_for_first_task` at `tests/implement/test_trunk_mode.py:84`: change assertion from `method == "run_interactive"` to `method == "run"`
      - `test_non_interactive_uses_run_batch` at `tests/implement/test_trunk_mode.py:218`: change assertion from `method == "run_batch"` to `method == "run"`, and update class/method docstring
      - `test_recovery_needed_and_succeeds` at `tests/implement/test_trunk_mode.py:335`: change assertion from `fake_runner.calls[1][0] == "run_interactive"` to `"run"` (recovery call at line 334 stays `"run_batch"`)
      - `test_no_recovery_needed` at `tests/implement/test_trunk_mode.py:379`: change assertion from `method == "run_interactive"` to `method == "run"`

- [x] **Task 1.6: WorktreeMode._run_claude() uses runner.run() instead of if/else dispatch**
  - TaskType: REFACTOR
  - Entrypoint: `uv run --with pytest --with pytest-mock pytest tests/implement/test_worktree_mode.py -v -m unit`
  - Observable: No behavior change — WorktreeMode produces identical results for both interactive and non-interactive execution
  - Evidence: All `TestWorktreeMode*` tests pass with updated assertions
  - Steps:
    - [x] In `src/i2code/implement/worktree_mode.py:147-152`: simplify `_run_claude(self, claude_cmd)` — replace the if/else block with `return self._loop_steps.claude_runner.run(claude_cmd, cwd=self._git_repo.working_tree_dir)`
    - [x] In `tests/implement/test_worktree_mode.py`:
      - `test_non_interactive_uses_capture_and_checks_success_tag` at `tests/implement/test_worktree_mode.py:495`: change assertion from `method == "run_batch"` to `method == "run"`, and update class docstring
      - `test_recovery_needed_and_succeeds` at `tests/implement/test_worktree_mode.py:602`: change assertion from `fake_runner.calls[1][0] == "run_interactive"` to `"run"` (recovery call at line 601 stays `"run_batch"`)
      - `test_no_recovery_needed` at `tests/implement/test_worktree_mode.py:650`: change assertion from `method == "run_interactive"` to `method == "run"`

- [x] **Task 1.7: ProjectSetup.run_scaffolding() uses runner.run() instead of if/else dispatch**
  - TaskType: REFACTOR
  - Entrypoint: `uv run --with pytest --with pytest-mock pytest tests/implement/test_project_setup.py -v -m unit`
  - Observable: No behavior change — run_scaffolding() produces identical results for both interactive and non-interactive execution
  - Evidence: All `TestRunScaffolding` tests pass with updated assertions
  - Steps:
    - [x] In `src/i2code/implement/project_setup.py:67-70` `run_scaffolding()`: replace the if/else dispatch with `result = self._claude_runner.run(cmd, cwd=cwd)`. Keep the `interactive` parameter (needed for `build_scaffolding_command` and the `if interactive or "<SUCCESS>" ...` check)
    - [x] In `tests/implement/test_project_setup.py`:
      - `test_interactive_calls_run_interactive` at `tests/implement/test_project_setup.py:184`: change assertion from `method == "run_interactive"` to `method == "run"`, rename test to `test_interactive_calls_run`
      - `test_non_interactive_calls_run_batch` at `tests/implement/test_project_setup.py:200`: change assertion from `method == "run_batch"` to `method == "run"`, rename test to `test_non_interactive_calls_run`
      - `test_forwards_mock_claude` at `tests/implement/test_project_setup.py:220`: change assertion from `method == "run_interactive"` to `method == "run"`

- [x] **Task 1.8: GithubActionsBuildFixer._invoke_claude_for_fix() uses runner.run() instead of if/else dispatch**
  - TaskType: REFACTOR
  - Entrypoint: `uv run --with pytest --with pytest-mock pytest tests/implement/test_github_actions_build_fixer.py -v -m unit`
  - Observable: No behavior change — _invoke_claude_for_fix() produces identical results for both interactive and non-interactive execution
  - Evidence: All `TestGithubActionsBuildFixer` tests pass with updated assertions
  - Steps:
    - [x] In `src/i2code/implement/github_actions_build_fixer.py:141-145` `_invoke_claude_for_fix()`: replace the if/else dispatch with `self._claude_runner.run(claude_cmd, cwd=self._git_repo.working_tree_dir)`. Keep the local `interactive` variable (needed for `build_ci_fix_command`)
    - [x] At `tests/implement/test_github_actions_build_fixer.py:118`: change assertion from `fake_runner.calls[0][0] == "run_batch"` to `fake_runner.calls[0][0] == "run"`

- [ ] **Task 1.9: PullRequestReviewProcessor._invoke_fix() uses runner.run() instead of if/else dispatch**
  - TaskType: REFACTOR
  - Entrypoint: `uv run --with pytest --with pytest-mock pytest tests/implement/test_pull_request_review_processor.py -v -m unit`
  - Observable: No behavior change — _invoke_fix() produces identical results; _run_triage() continues calling run_batch() directly
  - Evidence: All `TestProcessPrFeedback*` tests pass with updated assertions
  - Steps:
    - [ ] In `src/i2code/implement/pull_request_review_processor.py:264-268` `_invoke_fix()`: replace the if/else dispatch with `self._claude_runner.run(fix_cmd, cwd=self._git_repo.working_tree_dir)`. Keep the local `interactive` variable (needed for `build_fix_command`)
    - [ ] Verify `_run_triage()` at `src/i2code/implement/pull_request_review_processor.py:175` still calls `run_batch()` directly — no changes needed
    - [ ] In `tests/implement/test_pull_request_review_processor.py`:
      - `test_triage_uses_claude_runner_run_batch` at `tests/implement/test_pull_request_review_processor.py:139`: **no change** — triage still uses `run_batch`
      - `test_fix_interactive_uses_run_interactive` at `tests/implement/test_pull_request_review_processor.py:214`: change second assertion from `fake_claude.calls[1][0] == "run_interactive"` to `fake_claude.calls[1][0] == "run"`, rename test to `test_fix_interactive_uses_run`

## Change History

- **2026-02-22:** Standardized all file references to use relative paths with suffix in backticks (e.g., `src/i2code/implement/cli.py`) and all location references to use `path:linenumber` format in backticks (e.g., `src/i2code/implement/cli.py:55`). Replaced bare "(line N)" annotations throughout all tasks.
- **2026-02-24:** Revised spec and plan to match actual code. Construction sites are in `command_assembler.py` (not `cli.py`). WorktreeMode uses `self._loop_steps.claude_runner` (not `self._claude_runner`). Added `TaskCommitRecovery` as a consumer. Added missing recovery test assertion updates to Tasks 1.5/1.6. Updated line numbers throughout.
- **2026-02-24:** Renamed `run_with_capture` → `run_batch` across idea, spec, and plan. Added new Task 1.1 for the rename in production code and tests.

### 2026-02-24 20:43 - mark-step-complete
Wrote TestClaudeRunnerRun class with two tests

### 2026-02-24 20:43 - mark-step-complete
Added interactive: bool = True parameter to ClaudeRunner.__init__()

### 2026-02-24 20:43 - mark-step-complete
Added run() method that dispatches based on self._interactive

### 2026-02-24 20:43 - mark-task-complete
ClaudeRunner.run() dispatches to run_interactive or run_batch based on interactive constructor argument. All 18 tests pass.

### 2026-02-24 21:42 - mark-step-complete
Changed ClaudeRunner() to ClaudeRunner(interactive=not opts.non_interactive) in assemble_implement()

### 2026-02-24 21:42 - mark-step-complete
Changed ClaudeRunner() to ClaudeRunner(interactive=not opts.non_interactive) in assemble_scaffold()

### 2026-02-24 21:42 - mark-task-complete
Both assemble_implement() and assemble_scaffold() now pass interactive=not opts.non_interactive to ClaudeRunner; all 390 unit tests pass unchanged

### 2026-02-24 21:54 - mark-task-complete
Simplified _run_claude to use runner.run() instead of if/else dispatch

### 2026-02-24 22:56 - mark-step-complete
Replaced if/else dispatch with runner.run() delegation

### 2026-02-24 22:56 - mark-step-complete
Updated test assertions from run_interactive/run_batch to run

### 2026-02-24 22:57 - mark-task-complete
Simplified WorktreeMode._run_claude() to use runner.run() instead of if/else dispatch

### 2026-02-24 23:22 - mark-task-complete
Replaced if/else dispatch with runner.run() in run_scaffolding(); updated TestRunScaffolding assertions

### 2026-02-25 06:52 - mark-step-complete
Replaced if/else dispatch with self._claude_runner.run()

### 2026-02-25 06:52 - mark-step-complete
Changed assertion from run_batch to run

### 2026-02-25 06:52 - mark-task-complete
Replaced if/else dispatch with runner.run() in _invoke_claude_for_fix()
