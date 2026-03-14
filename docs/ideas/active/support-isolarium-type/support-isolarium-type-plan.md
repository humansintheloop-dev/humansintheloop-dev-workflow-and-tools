Now I have a complete understanding of the codebase. Let me generate the plan.

# Plan: Support Isolarium Type

## Idea Type

**A. User-facing feature** — adds `--isolation-type TYPE` CLI option to `i2code implement`.

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
- Before committing, ALWAYS print a Verification section containing the exact test command (NOT an ad-hoc command - it must be a proper test command such as `./test-scripts/*.sh`, `./scripts/test.sh`, or `./gradlew build`/`./gradlew check`), its exit code, and the last 20 lines of output

### Design Pattern

This feature follows the **Command + Assembler** pattern documented in `design-pattern-catalog/commands/command-assembler.md`. The data flows:

```
cli.py (Click option) → ImplementOpts (dataclass field) → ImplementCommand (orchestrator) → IsolateMode (isolarium command builder)
```

Test each layer with fakes — no `@patch` on `IsolateMode` tests.

## Steel Thread 1: Specify Isolation Type in Isolarium Command

Implements **US-1**: `i2code implement --isolate --isolation-type docker idea-dir` produces an isolarium command with `--type docker` in global args.

- [x] **Task 1.1: IsolateMode inserts --type TYPE into isolarium global args when isolation_type is provided**
  - TaskType: OUTCOME
  - Entrypoint: `IsolateMode.execute(isolation_type="docker")` via unit test
  - Observable: The isolarium command captured by `FakeSubprocessRunner` contains `--type docker` in the global args (after `--name` and before `run`). When `isolation_type` is `None`, the command does NOT contain `--type` (backwards compatibility).
  - Evidence: `pytest tests/implement/test_isolate_mode.py -k "isolation_type" -v` passes
  - Steps:
    - [x] Add test class `TestIsolateModeIsolationType` to `tests/implement/test_isolate_mode.py` with:
      - `test_includes_type_in_isolarium_global_args_when_isolation_type_provided` — asserts `--type docker` appears after `--name i2code-<name>` and before `run` in the captured command
      - `test_omits_type_from_isolarium_when_isolation_type_is_none` — asserts `--type` does NOT appear when `isolation_type=None` (backwards compatibility, Scenario 5)
      - `test_isolation_type_not_forwarded_to_inner_command` — asserts `--type` does NOT appear after the `--` separator (FR-4)
    - [x] Add `isolation_type=None` parameter to `IsolateMode.execute()` in `src/i2code/implement/isolate_mode.py`
    - [x] Add `isolation_type=None` parameter to `IsolateMode._build_isolarium_command()` in `src/i2code/implement/isolate_mode.py`
    - [x] In `_build_isolarium_command()`, insert `["--type", isolation_type]` into isolarium global args (between `--name i2code-<name>` and `run`) when `isolation_type` is not None

- [x] **Task 1.2: --isolation-type CLI option flows through ImplementOpts to IsolateMode**
  - TaskType: OUTCOME
  - Entrypoint: `ImplementCommand.execute()` with `opts.isolation_type="docker"` and `opts.isolate=True`
  - Observable: The `isolation_type` value reaches `IsolateMode.execute()` as a keyword argument
  - Evidence: `pytest tests/implement/test_implement_command.py -k "isolation_type" -v` passes
  - Steps:
    - [x] Add `isolation_type: str | None = None` field to `ImplementOpts` in `src/i2code/implement/implement_opts.py`
    - [x] Add test `test_isolate_mode_receives_isolation_type` to `tests/implement/test_implement_command.py` — construct `ImplementCommand` with `isolation_type="docker"` and `isolate=True`, verify `mode_factory.make_isolate_mode()` is called and the resulting mode's `execute()` receives `isolation_type="docker"`
    - [x] Add `@click.option("--isolation-type", metavar="TYPE", help="Isolation environment type (passed as --type to isolarium)")` to `implement_cmd` in `src/i2code/implement/cli.py`
    - [x] In `ImplementCommand._isolate_mode()` at `src/i2code/implement/implement_command.py`, pass `isolation_type=self.opts.isolation_type` to `isolate_mode.execute()`

## Steel Thread 2: Isolation Type Implies Isolate Mode

Implements **US-2**: `i2code implement --isolation-type docker idea-dir` automatically enables isolate mode without requiring `--isolate`.

- [x] **Task 2.1: --isolation-type implies --isolate when --isolate is not explicitly set**
  - TaskType: OUTCOME
  - Entrypoint: `ImplementCommand.execute()` with `opts.isolation_type="docker"` and `opts.isolate=False`
  - Observable: The command dispatches to `_isolate_mode()` (not `_worktree_mode()`). In dry-run mode, output shows `Mode: isolate`.
  - Evidence: `pytest tests/implement/test_implement_command.py -k "isolation_type_implies" -v` passes
  - Steps:
    - [x] Add test class `TestImplementCommandIsolationTypeImplied` to `tests/implement/test_implement_command.py` with:
      - `test_isolation_type_implies_isolate_mode` — construct with `isolation_type="docker"`, `isolate=False`; verify `_isolate_mode()` is called
      - `test_dry_run_shows_isolate_when_isolation_type_set` — construct with `dry_run=True`, `isolation_type="docker"`; verify output contains "isolate" (FR-6, Scenario 6)
      - `test_isolation_type_with_explicit_isolate_dispatches_normally` — construct with `isolation_type="docker"`, `isolate=True`; verify `_isolate_mode()` is called (Scenario 2)
    - [x] In `ImplementCommand.execute()` at `src/i2code/implement/implement_command.py`, before the dry-run check and mode dispatch, add: if `self.opts.isolation_type` is set, set `self.opts.isolate = True`

## Steel Thread 3: Error on Incompatible Mode

Implements **US-4**: `i2code implement --trunk --isolation-type docker idea-dir` raises a clear error.

- [ ] **Task 3.1: --isolation-type with --trunk raises UsageError**
  - TaskType: OUTCOME
  - Entrypoint: `ImplementOpts.validate_trunk_options()` with `trunk=True` and `isolation_type="docker"`
  - Observable: `click.UsageError` raised with message containing `--trunk cannot be combined with: --isolation-type`
  - Evidence: `pytest tests/implement/test_implement_opts.py -k "isolation_type" -v` passes
  - Steps:
    - [ ] Add `test_isolation_type_raises_usage_error` to `TestValidateTrunkOptions` parametrized test list in `tests/implement/test_implement_opts.py` — construct `ImplementOpts(trunk=True, isolation_type="docker")`, assert `UsageError` with "cannot be combined"
    - [ ] Add `test_error_message_includes_isolation_type_with_other_flags` — construct with `trunk=True, isolation_type="docker", cleanup=True`, assert error message lists both `--cleanup` and `--isolation-type`
    - [ ] In `validate_trunk_options()` at `src/i2code/implement/implement_opts.py`, add check: if `self.isolation_type` is not None, append `"--isolation-type"` to the incompatible list

---

## Change History
### 2026-02-24 17:32 - mark-task-complete
isolation_type implies isolate: tests pass, dispatches to _isolate_mode()
