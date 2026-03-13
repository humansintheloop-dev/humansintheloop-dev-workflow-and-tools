# ClaudeRunner: interactive as constructor argument — Specification

## Purpose and Context

`ClaudeRunner` is the central abstraction for invoking Claude CLI processes. It currently exposes two public methods — `run_interactive(cmd, cwd)` and `run_batch(cmd, cwd)` — and every caller duplicates the same if/else dispatch to choose between them based on the `interactive` flag.

This refactoring makes `interactive` a constructor argument and adds a `run(cmd, cwd)` method that dispatches internally, eliminating the duplicated conditional from five call sites.

## Consumers

| Consumer | File | Role |
|----------|------|------|
| TrunkMode | `src/i2code/implement/trunk_mode.py` | Executes plan tasks on current branch |
| WorktreeMode | `src/i2code/implement/worktree_mode.py` | Executes plan tasks on worktree branches |
| ProjectSetup | `src/i2code/implement/project_setup.py` | Runs scaffolding before task execution |
| GithubActionsBuildFixer | `src/i2code/implement/github_actions_build_fixer.py` | Invokes Claude to fix CI failures |
| PullRequestReviewProcessor | `src/i2code/implement/pull_request_review_processor.py` | Invokes Claude for PR feedback fixes and triage |
| Assembly | `src/i2code/implement/command_assembler.py` | Constructs `ClaudeRunner` instances |
| TaskCommitRecovery | `src/i2code/implement/commit_recovery.py` | Always calls `run_batch()` directly |
| Tests | `tests/implement/fake_claude_runner.py` | Test double (`FakeClaudeRunner`) |

## Capabilities and Behaviors

### C1: Constructor accepts `interactive` parameter

`ClaudeRunner` accepts `interactive: bool = True` in its constructor. The default (`True`) matches the current behavior where omitting `--non-interactive` means interactive mode.

### C2: New `run(cmd, cwd)` method dispatches internally

`ClaudeRunner.run(cmd, cwd)` delegates to `run_interactive` when `interactive=True` and to `run_batch` when `interactive=False`. Callers replace their if/else blocks with a single `run()` call.

### C3: Existing methods remain public

`run_interactive(cmd, cwd)` and `run_batch(cmd, cwd)` remain public. Callers that need to bypass the dispatch (e.g., triage always capturing) continue calling `run_batch()` directly.

### C4: FakeClaudeRunner matches the new interface

`FakeClaudeRunner` accepts `interactive: bool = True` in its constructor (matching `ClaudeRunner`). Its `run(cmd, cwd)` method records calls as `("run", cmd, cwd)` — it does not internally dispatch. Dispatch correctness is tested on `ClaudeRunner` itself.

### C5: Construction sites pass `interactive`

The two construction sites in `command_assembler.py` pass `interactive=not opts.non_interactive` when creating `ClaudeRunner`.

### C6: Dispatch sites simplified

Each of the five dispatch sites replaces its if/else block with a single `self._claude_runner.run(cmd, cwd)` call. Local `interactive` variables used for `CommandBuilder` or error-checking logic are retained at those sites — only the dispatch conditional is removed.

### C7: Triage unchanged

`PullRequestReviewProcessor._run_triage()` continues calling `self._claude_runner.run_batch()` directly. Triage always captures output regardless of the interactive setting.

### C8: Commit recovery unchanged

`TaskCommitRecovery.commit_uncommitted_changes()` continues calling `self._claude_runner.run_batch()` directly. Recovery always runs non-interactively to commit previously completed work.

## High-Level API

### ClaudeRunner (after)

```python
class ClaudeRunner:
    def __init__(self, interactive: bool = True):
        self._interactive = interactive

    def run(self, cmd: List[str], cwd: str) -> ClaudeResult:
        if self._interactive:
            return self.run_interactive(cmd, cwd=cwd)
        return self.run_batch(cmd, cwd=cwd)

    def run_interactive(self, cmd: List[str], cwd: str) -> ClaudeResult:
        ...  # unchanged

    def run_batch(self, cmd: List[str], cwd: str) -> ClaudeResult:
        ...  # unchanged
```

### FakeClaudeRunner (after)

```python
class FakeClaudeRunner:
    def __init__(self, interactive: bool = True):
        self._interactive = interactive
        ...  # existing fields unchanged

    def run(self, cmd, cwd):
        self.calls.append(("run", cmd, cwd))
        return self._next_result()

    def run_interactive(self, cmd, cwd):
        ...  # unchanged

    def run_batch(self, cmd, cwd):
        ...  # unchanged
```

## Affected Call Sites — Before and After

### Construction sites

**`command_assembler.py` — `assemble_implement()`**

```python
# Before
claude_runner = ClaudeRunner()

# After
claude_runner = ClaudeRunner(interactive=not opts.non_interactive)
```

**`command_assembler.py` — `assemble_scaffold()`**

```python
# Before
claude_runner=ClaudeRunner(),

# After
claude_runner=ClaudeRunner(interactive=not opts.non_interactive),
```

### Dispatch sites

**`trunk_mode.py` — `_run_claude()`**

```python
# Before
def _run_claude(self, claude_cmd, non_interactive):
    if non_interactive:
        return self._claude_runner.run_batch(claude_cmd, cwd=self._git_repo.working_tree_dir)
    else:
        return self._claude_runner.run_interactive(claude_cmd, cwd=self._git_repo.working_tree_dir)

# After
def _run_claude(self, claude_cmd):
    return self._claude_runner.run(claude_cmd, cwd=self._git_repo.working_tree_dir)
```

The `non_interactive` parameter is removed from `_run_claude` since the runner already knows. Callers of `_run_claude` stop passing it.

**`worktree_mode.py` — `_run_claude()`**

```python
# Before
def _run_claude(self, claude_cmd):
    work_dir = self._git_repo.working_tree_dir
    if self._opts.non_interactive:
        return self._loop_steps.claude_runner.run_batch(claude_cmd, cwd=work_dir)
    else:
        return self._loop_steps.claude_runner.run_interactive(claude_cmd, cwd=work_dir)

# After
def _run_claude(self, claude_cmd):
    return self._loop_steps.claude_runner.run(claude_cmd, cwd=self._git_repo.working_tree_dir)
```

**`project_setup.py` — `run_scaffolding()`**

```python
# Before
if interactive:
    result = self._claude_runner.run_interactive(cmd, cwd=cwd)
else:
    result = self._claude_runner.run_batch(cmd, cwd=cwd)

# After
result = self._claude_runner.run(cmd, cwd=cwd)
```

The `interactive` parameter on `run_scaffolding()` is retained — it is still needed for `build_scaffolding_command(interactive=...)` and the `if interactive or "<SUCCESS>" ...` check on line 72.

**`github_actions_build_fixer.py` — `_invoke_claude_for_fix()`**

```python
# Before
if interactive:
    self._claude_runner.run_interactive(claude_cmd, cwd=self._git_repo.working_tree_dir)
else:
    self._claude_runner.run_batch(claude_cmd, cwd=self._git_repo.working_tree_dir)

# After
self._claude_runner.run(claude_cmd, cwd=self._git_repo.working_tree_dir)
```

The local `interactive` variable is retained for `build_ci_fix_command(interactive=interactive)`.

**`pull_request_review_processor.py` — `_invoke_fix()`**

```python
# Before
if interactive:
    self._claude_runner.run_interactive(fix_cmd, cwd=self._git_repo.working_tree_dir)
else:
    self._claude_runner.run_batch(fix_cmd, cwd=self._git_repo.working_tree_dir)

# After
self._claude_runner.run(fix_cmd, cwd=self._git_repo.working_tree_dir)
```

The local `interactive` variable is retained for `build_fix_command(..., interactive=interactive)`.

## Non-Functional Requirements

- **No behavior change:** This is a pure refactoring. All existing tests must continue to pass (with updated assertions).
- **Code Health:** Target Code Health score of 10.0 for all modified files.

## Scenarios and Workflows

### S1: Primary end-to-end scenario — Trunk mode task execution

A caller constructs `ClaudeRunner(interactive=False)` and passes it to `TrunkMode`. When `TrunkMode` executes a task, it calls `runner.run(cmd, cwd)`, which internally delegates to `run_batch()`. The captured output is checked for `<SUCCESS>` tag and diagnostics are available. This replaces the current flow where `TrunkMode._run_claude()` receives a `non_interactive` parameter and dispatches itself.

### S2: Interactive mode execution

A caller constructs `ClaudeRunner(interactive=True)` (default). `runner.run(cmd, cwd)` internally delegates to `run_interactive()`, which gives Claude direct terminal access. No output is captured.

### S3: Triage and commit recovery bypass `run()` dispatch

`PullRequestReviewProcessor._run_triage()` and `TaskCommitRecovery.commit_uncommitted_changes()` call `runner.run_batch()` directly, regardless of the runner's `interactive` setting. Triage always captures output for programmatic parsing; recovery always runs non-interactively.

### S4: Scaffolding retains `interactive` parameter for command building

`ProjectSetup.run_scaffolding(interactive=...)` still accepts the parameter for `CommandBuilder` and for conditional error checking. The dispatch itself uses `runner.run()`.

### S5: FakeClaudeRunner records `"run"` method name

Tests that previously asserted `calls[0][0] == "run_interactive"` or `"run_batch"` at dispatch sites now assert `calls[0][0] == "run"`. Dispatch correctness is verified in a dedicated unit test on `ClaudeRunner` itself.

## Constraints and Assumptions

- The `interactive` flag is immutable for the lifetime of a `ClaudeRunner` instance. It is set once at construction and does not change.
- All dispatch sites in the codebase have been identified (5 sites). No other dispatch patterns exist.
- `CommandBuilder` methods continue to receive `interactive` as a parameter — they are unaffected by this refactoring.

## Acceptance Criteria

1. `ClaudeRunner.__init__` accepts `interactive: bool = True`.
2. `ClaudeRunner.run(cmd, cwd)` dispatches to `run_interactive` when `interactive=True` and to `run_batch` when `interactive=False`.
3. `run_interactive` and `run_batch` remain public and unchanged in behavior.
4. All five dispatch sites call `runner.run()` instead of the if/else pattern.
5. `TrunkMode._run_claude()` no longer accepts a `non_interactive` parameter.
6. `FakeClaudeRunner.__init__` accepts `interactive: bool = True`.
7. `FakeClaudeRunner.run(cmd, cwd)` records calls as `("run", cmd, cwd)`.
8. `_run_triage()` and `TaskCommitRecovery.commit_uncommitted_changes()` continue calling `run_batch()` directly.
9. A dedicated unit test verifies `ClaudeRunner.run()` dispatches correctly for both `interactive=True` and `interactive=False`.
10. All existing tests pass with updated assertions.
11. Code Health score of 10.0 for all modified files.
