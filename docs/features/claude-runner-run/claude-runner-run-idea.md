# ClaudeRunner: interactive as constructor argument

## Problem

Every caller of `ClaudeRunner` duplicates the same dispatch conditional:

```python
if non_interactive:
    runner.run_batch(cmd, cwd)
else:
    runner.run_interactive(cmd, cwd)
```

This pattern appears in five call sites across the codebase.

## Goal

Make `interactive` a constructor argument of `ClaudeRunner` and add a single `run(cmd, cwd)` method that dispatches internally. Callers replace the if/else with one call.

Keep `run_batch()` for the special case where triage always captures output regardless of the interactive setting.

## Locations

### ClaudeRunner and FakeClaudeRunner

- `src/i2code/implement/claude_runner.py:240` — add `interactive` constructor param, add `run()` method
- `tests/implement/fake_claude_runner.py` — match new interface

### Construction sites (pass `interactive` at creation)

- `src/i2code/implement/cli.py:55` — `implement_cmd()` creates `ClaudeRunner()`
- `src/i2code/implement/cli.py:93` — `scaffold_cmd()` creates `ClaudeRunner()`

### Dispatch sites (replace if/else with `run()`)

- `src/i2code/implement/trunk_mode.py:84-88` — `_run_claude()` dispatches based on `non_interactive` param
- `src/i2code/implement/worktree_mode.py:126-131` — `_run_claude()` dispatches based on `self._opts.non_interactive`
- `src/i2code/implement/project_setup.py:67-70` — `run_scaffolding()` dispatches based on `interactive` param (keep param for CommandBuilder and error checking)
- `src/i2code/implement/github_actions_build_fixer.py:142-145` — `_invoke_claude_for_fix()` dispatches based on local `interactive` var (keep var for CommandBuilder)
- `src/i2code/implement/pull_request_review_processor.py:265-268` — `_invoke_fix()` dispatches based on local `interactive` var (keep var for CommandBuilder)

### Unchanged

- `src/i2code/implement/pull_request_review_processor.py:175` — triage always calls `run_batch()` directly
