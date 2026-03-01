# ClaudeRunner: interactive as constructor argument — Discussion

## Classification

**Category:** C. Platform/infrastructure capability

**Rationale:** This is an internal refactoring that consolidates a duplicated dispatch pattern (interactive vs. captured execution) into `ClaudeRunner` itself. It reduces coupling across 5 call sites without changing any user-facing behavior. The change improves maintainability and makes the `ClaudeRunner` interface easier to use correctly.

## Codebase Analysis

### Current State

- `ClaudeRunner` has no constructor params and two public methods: `run_interactive(cmd, cwd)` and `run_with_capture(cmd, cwd)`
- `FakeClaudeRunner` mirrors this interface and records calls as `(method_name, cmd, cwd)` tuples
- The `interactive` flag originates from CLI `--non-interactive` (inverted) and flows through `ImplementOpts`

### Dispatch Sites (5 locations with duplicated if/else)

1. `trunk_mode.py:84-88` — `_run_claude()` dispatches on `non_interactive` param
2. `worktree_mode.py:126-131` — `_run_claude()` dispatches on `self._opts.non_interactive`
3. `project_setup.py:67-70` — `run_scaffolding()` dispatches on `interactive` param
4. `github_actions_build_fixer.py:142-145` — `_invoke_claude_for_fix()` dispatches on local `interactive` var
5. `pull_request_review_processor.py:265-268` — `_invoke_fix()` dispatches on local `interactive` var

### Exception

- `pull_request_review_processor.py:175` — `_run_triage()` always calls `run_with_capture()` directly (triage is never interactive)

## Questions & Answers

### Q1: Should `run_interactive` become private after introducing `run()`?

Once all dispatch sites switch to `run()`, nothing will call `run_interactive()` directly. Should it become `_run_interactive`?

- A. Make it private — cleaner interface, only `run()` and `run_with_capture()` are public
- B. Keep it public — preserve the option for callers to explicitly choose interactive execution

**Answer:** B. Keep it public. All three methods (`run`, `run_interactive`, `run_with_capture`) remain part of the public interface.

### Q2: How should `FakeClaudeRunner.run()` record calls?

With the new `run()` method, should the fake record calls as `("run", cmd, cwd)` or internally dispatch and record as `("run_interactive", ...)` / `("run_with_capture", ...)`?

- A. Record as `"run"` — tests assert callers use `run()`, dispatch correctness is tested separately on `ClaudeRunner` itself (separation of concerns)
- B. Dispatch internally and record the underlying method — tests verify the full chain but duplicate dispatch logic in the fake

**Answer:** A. Record as `"run"`. Caller tests verify the correct API is used; dispatch correctness is tested once on `ClaudeRunner` itself. `FakeClaudeRunner` stays simple with no dispatch logic.

