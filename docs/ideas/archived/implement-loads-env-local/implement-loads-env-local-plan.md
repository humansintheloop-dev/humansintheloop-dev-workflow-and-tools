Now I have everything I need from the spec. This is a **Platform/infrastructure capability (Type C)** — a small internal change to `i2code implement`. Let me generate the plan.

# implement-loads-env-local Plan

**Idea Type:** C — Platform/infrastructure capability

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

---

## Steel Thread 1: Load `.env.local` at Startup

This steel thread implements the core capability: `ImplementCommand.execute()` loads `.env.local` from CWD before mode selection, using `python-dotenv` with `override=False`.

- [x] **Task 1.1: Add `python-dotenv` dependency and load `.env.local` in `ImplementCommand.execute()`**
  - TaskType: INFRA
  - Entrypoint: `uvx pyright --level error src/ && python -m pytest`
  - Observable: `python-dotenv` is listed in `pyproject.toml` dependencies; when `.env.local` exists in CWD with `FOO=bar`, after `ImplementCommand.execute()` begins, `os.environ["FOO"]` equals `"bar"`
  - Evidence: pytest test creates a `.env.local` in a tmp directory, sets CWD to that directory, calls the load path, and asserts `os.environ` contains the expected variable. CI (existing `.github/workflows/ci.yml`) runs tests and passes.
  - Steps:
    - [x] Add `python-dotenv` to `pyproject.toml` under `[project] dependencies`
    - [x] Write a test (e.g., `tests/implement/test_load_env_local.py`) that:
      - Creates a temporary directory with a `.env.local` file containing `TEST_ENV_VAR=test_value`
      - Ensures `TEST_ENV_VAR` is not already in `os.environ`
      - Changes CWD to the temp directory (or patches accordingly)
      - Calls `load_dotenv(".env.local")` (or the wrapper if one is introduced)
      - Asserts `os.environ["TEST_ENV_VAR"] == "test_value"`
      - Cleans up the env var after the test
    - [x] Add `from dotenv import load_dotenv` to `ImplementCommand` module
    - [x] Add `load_dotenv(".env.local")` as the first line of `ImplementCommand.execute()`, before `self._validate_and_apply_defaults()`

## Steel Thread 2: Missing `.env.local` Is Silently Ignored

- [x] **Task 2.1: No error when `.env.local` does not exist in CWD**
  - TaskType: OUTCOME
  - Entrypoint: `python -m pytest`
  - Observable: When `.env.local` does not exist in CWD, `ImplementCommand.execute()` proceeds without error, warning, or log message
  - Evidence: pytest test sets CWD to a temp directory with no `.env.local`, invokes the load path, and asserts no exception is raised and execution continues normally
  - Steps:
    - [x] Write a test in `tests/implement/test_load_env_local.py` that:
      - Sets CWD to a temp directory with no `.env.local`
      - Calls `load_dotenv(".env.local")`
      - Asserts no exception is raised (the call returns `False`)
      - Asserts execution proceeds normally (no side effects on `os.environ`)

## Steel Thread 3: Existing Environment Variables Are Not Overridden

- [x] **Task 3.1: Shell env vars take precedence over `.env.local` values**
  - TaskType: OUTCOME
  - Entrypoint: `python -m pytest`
  - Observable: When `GITHUB_TOKEN=shell-value` is already in `os.environ` and `.env.local` contains `GITHUB_TOKEN=file-value`, after loading, `os.environ["GITHUB_TOKEN"]` remains `"shell-value"`
  - Evidence: pytest test pre-sets an env var, creates `.env.local` with the same key but different value, calls `load_dotenv(".env.local")`, and asserts the original value is preserved
  - Steps:
    - [x] Write a test in `tests/implement/test_load_env_local.py` that:
      - Sets `os.environ["TEST_EXISTING_VAR"] = "shell-value"`
      - Creates a temp `.env.local` with `TEST_EXISTING_VAR=file-value`
      - Calls `load_dotenv(".env.local")` (which uses `override=False` by default)
      - Asserts `os.environ["TEST_EXISTING_VAR"] == "shell-value"`
      - Cleans up after the test

## Steel Thread 4: IsolateMode `.env.local` Handling Is Unchanged

- [x] **Task 4.1: `IsolateMode._find_env_file()` behavior is unaffected**
  - TaskType: OUTCOME
  - Entrypoint: `python -m pytest`
  - Observable: `IsolateMode._find_env_file()` still locates `.env.local` in `main_repo_dir` and passes it via `--env-file` — the new `load_dotenv` call does not interfere
  - Evidence: Existing tests for `IsolateMode._find_env_file()` continue to pass without modification. If no such tests exist, write a test that verifies `_find_env_file()` returns the expected path when `.env.local` exists in `main_repo_dir`.
  - Steps:
    - [x] Verify existing `IsolateMode` tests pass unchanged
    - [x] If no test exists for `_find_env_file()`, write one in the appropriate test module that asserts the method returns the correct path when `.env.local` is present in `main_repo_dir`

---

## Steel Thread 5: Skip load_dotenv in Isolate Mode
In isolate mode, nono propagates environment variables to the sandbox and isolarium receives `.env.local` via `--env-file`. Loading `.env.local` into the host process is unnecessary and could cause confusion. The `load_dotenv` call must be skipped when `--isolate` is specified.

- [x] **Task 5.1: Do not call `load_dotenv` when running in isolate mode**
  - TaskType: OUTCOME
  - Entrypoint: `python -m pytest`
  - Observable: When `--isolate` is specified, `load_dotenv(".env.local")` is not called; `.env.local` values do not appear in the host `os.environ`
  - Evidence: `pytest test sets up `.env.local` in a temp CWD, invokes `ImplementCommand.execute()` with isolate mode, and asserts the `.env.local` variables are NOT loaded into `os.environ``
  - Steps:
    - [x] Write a test that verifies `load_dotenv` is NOT called when isolate mode is active (e.g., mock `load_dotenv` and assert it is not called, or check that `.env.local` vars are absent from `os.environ`)
    - [x] Move the `load_dotenv(".env.local")` call so it only runs for trunk and worktree modes, not isolate mode
    - [x] Verify existing tests for trunk/worktree loading still pass
## Change History
### 2026-03-12 08:24 - mark-step-complete
All 39 IsolateMode tests pass unchanged, including TestIsolateModeEnvFile

### 2026-03-12 08:24 - mark-step-complete
Tests already exist in TestIsolateModeEnvFile: test_includes_env_file_when_present and test_omits_env_file_when_not_present

### 2026-03-12 08:24 - mark-task-complete
Existing TestIsolateModeEnvFile tests verify _find_env_file() behavior; all 39 IsolateMode tests pass unchanged

### 2026-03-12 09:23 - insert-thread-after
Requirement change: nono propagates env vars to sandbox; isolate mode should rely solely on isolarium --env-file mechanism, not load_dotenv in the host process

### 2026-03-12 09:31 - mark-step-complete
Test verifies load_dotenv is not called when isolate=True; .env.local vars absent from os.environ

### 2026-03-12 09:31 - mark-step-complete
Moved load_dotenv after _validate_and_apply_defaults(), guarded with if not self.opts.isolate

### 2026-03-12 09:31 - mark-step-complete
All 1236 tests pass including existing trunk/worktree loading tests

### 2026-03-12 09:31 - mark-task-complete
load_dotenv skipped in isolate mode; all 1236 tests pass
