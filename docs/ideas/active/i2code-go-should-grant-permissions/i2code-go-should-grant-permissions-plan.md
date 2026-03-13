I'm sandboxed to the idea directory, so I can't read the source files directly. However, the spec is detailed enough to create the plan. Let me generate it based on the spec's explicit file/function references and command patterns.

# Implementation Plan: i2code go should grant permissions

## Idea Type

**C. Platform/infrastructure capability** — This changes how the `i2code go` orchestrator invokes Claude, granting permissions and changing CWD. No new user-facing features; it removes friction from an existing workflow.

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

## Steel Thread 1: Brainstorm grants permissions and uses repo root CWD

This thread proves the core mechanism works end-to-end on a single subcommand (`brainstorm_idea`). Once this works, the remaining subcommands apply the same pattern.

- [x] **Task 1.1: brainstorm_idea builds claude command with --allowedTools and cwd=repo_root**
  - TaskType: OUTCOME
  - Entrypoint: `pytest tests/idea-cmd/test_brainstorm.py -k allowed_tools`
  - Observable: The claude command built by `brainstorm_idea()` includes `--allowedTools "Read(/<repo_root>/),Write(/<idea_dir>/),Edit(/<idea_dir>/)"` and uses the repo root as `cwd` instead of `project.directory`
  - Evidence: pytest test constructs a project with known repo_root and idea_dir, calls `brainstorm_idea()` with a mock/spy on the subprocess invocation, and asserts the command list contains the correct `--allowedTools` value and `cwd` equals the repo root
  - Steps:
    - [x] Read `src/i2code/idea_cmd/brainstorm.py` to understand how the claude command is currently built and how `cwd` is passed
    - [x] Read existing tests in `tests/idea-cmd/` to understand the test patterns used (mocking, fixtures, etc.)
    - [x] Write a failing test in `tests/idea-cmd/test_brainstorm.py` that asserts `--allowedTools` is present in the claude command and `cwd` is set to the repo root
    - [x] Determine how `brainstorm_idea()` accesses `project.directory` and the repo root — if there is no `repo_root` concept yet, identify where to source it (e.g., `os.getcwd()` at startup, or a project attribute)
    - [x] Modify `brainstorm_idea()` in `src/i2code/idea_cmd/brainstorm.py` to:
      - Accept or derive the repo root path
      - Build the `--allowedTools` flag with `Read(<repo_root>/), Write(<idea_dir>/), Edit(<idea_dir>/)`
      - Pass `cwd=<repo_root>` instead of `cwd=project.directory`
    - [x] Verify the test passes
    - [x] Run the full test suite to ensure no regressions

- [x] **Task 1.2: Extract shared helper for building permission flags**
  - TaskType: REFACTOR
  - Entrypoint: `pytest tests/idea-cmd/test_brainstorm.py -k allowed_tools`
  - Observable: No behavior change — brainstorm still builds the correct command with permissions
  - Evidence: Existing tests from Task 1.1 continue to pass after extracting the helper
  - Steps:
    - [x] Identify the permission-building logic added in Task 1.1
    - [x] Extract a shared function (e.g., `build_allowed_tools_flag(repo_root, idea_dir)`) into a common module (e.g., `src/i2code/claude_cmd.py` or wherever claude command utilities live)
    - [x] Update `brainstorm_idea()` to use the shared helper
    - [x] Write a unit test for the helper function that verifies the flag format: `Read(/<repo_root>/),Write(/<idea_dir>/),Edit(/<idea_dir>/)`
    - [x] Verify all tests pass

## Steel Thread 2: Spec subcommands grant permissions

- [x] **Task 2.1: create_spec builds claude command with --allowedTools and cwd=repo_root**
  - TaskType: OUTCOME
  - Entrypoint: `pytest tests/spec-cmd/test_create_spec.py -k allowed_tools`
  - Observable: The claude command built by `create_spec()` includes `--allowedTools` with correct Read/Write/Edit permissions and uses repo root as `cwd`
  - Evidence: pytest test mocks the subprocess invocation and asserts the command contains `--allowedTools` with the expected value and `cwd` equals the repo root
  - Steps:
    - [x] Read `src/i2code/spec_cmd/create_spec.py` to understand the current command construction
    - [x] Read existing tests in `tests/spec-cmd/` for test patterns
    - [x] Write a failing test asserting `--allowedTools` and `cwd=repo_root`
    - [x] Modify `create_spec()` to use the shared helper from Task 1.2 and pass `cwd=repo_root`
    - [x] Verify the test passes and no regressions

- [x] **Task 2.2: revise_spec builds claude command with --allowedTools and cwd=repo_root**
  - TaskType: OUTCOME
  - Entrypoint: `pytest tests/spec-cmd/test_revise_spec.py -k allowed_tools`
  - Observable: The claude command built by `revise_spec()` includes `--allowedTools` with correct permissions and uses repo root as `cwd`
  - Evidence: pytest test mocks the subprocess invocation and asserts the command contains `--allowedTools` with the expected value and `cwd` equals the repo root
  - Steps:
    - [x] Read `src/i2code/spec_cmd/revise_spec.py` to understand the current command construction
    - [x] Write a failing test asserting `--allowedTools` and `cwd=repo_root`
    - [x] Modify `revise_spec()` to use the shared helper and pass `cwd=repo_root`
    - [x] Verify the test passes and no regressions

## Steel Thread 3: Plan subcommands grant permissions

- [x] **Task 3.1: create_plan builds claude command with --allowedTools and cwd=repo_root**
  - TaskType: OUTCOME
  - Entrypoint: `pytest tests/go-cmd/test_create_plan.py -k allowed_tools`
  - Observable: The claude command built by `_generate_plan()` / `create_plan()` includes `--allowedTools` with correct permissions and uses repo root as `cwd`
  - Evidence: pytest test mocks the subprocess invocation and asserts the command contains `--allowedTools` with the expected value and `cwd` equals the repo root
  - Steps:
    - [x] Read `src/i2code/go_cmd/create_plan.py` to understand the current command construction (note: uses `-p` batch mode)
    - [x] Read existing tests in `tests/go-cmd/` for test patterns
    - [x] Write a failing test asserting `--allowedTools` and `cwd=repo_root`
    - [x] Modify `_generate_plan()` / `create_plan()` to use the shared helper and pass `cwd=repo_root`
    - [x] Verify the test passes and no regressions

- [x] **Task 3.2: revise_plan builds claude command with --allowedTools and cwd=repo_root**
  - TaskType: OUTCOME
  - Entrypoint: `pytest tests/go-cmd/test_revise_plan.py -k allowed_tools`
  - Observable: The claude command built by `revise_plan()` includes `--allowedTools` with correct permissions and uses repo root as `cwd`
  - Evidence: pytest test mocks the subprocess invocation and asserts the command contains `--allowedTools` with the expected value and `cwd` equals the repo root
  - Steps:
    - [x] Read `src/i2code/go_cmd/revise_plan.py` to understand the current command construction
    - [x] Write a failing test asserting `--allowedTools` and `cwd=repo_root`
    - [x] Modify `revise_plan()` to use the shared helper and pass `cwd=repo_root`
    - [x] Verify the test passes and no regressions

## Steel Thread 4: Standalone commands are unaffected

- [x] **Task 4.1: Standalone brainstorm, spec, and plan commands do NOT include --allowedTools**
  - TaskType: OUTCOME
  - Entrypoint: `pytest tests/ -k standalone_no_allowed_tools`
  - Observable: When brainstorm, create_spec, revise_spec, create_plan, or revise_plan are invoked outside of `i2code go` (i.e., as standalone commands), the claude command does NOT include `--allowedTools` and CWD remains `project.directory`
  - Evidence: pytest tests invoke each function in "standalone" mode (without repo_root context) and assert `--allowedTools` is absent from the command and `cwd` equals `project.directory`
  - Steps:
    - [x] Determine how to distinguish `i2code go` invocations from standalone invocations — likely by whether `repo_root` is passed as a parameter (None = standalone, set = go mode)
    - [x] Write failing tests for each subcommand verifying that when `repo_root` is None/not provided, the command omits `--allowedTools` and uses `project.directory` as `cwd`
    - [x] Ensure the implementation from previous tasks already handles this (the shared helper should be conditional on `repo_root` being provided)
    - [x] If needed, adjust the implementation to make the permission granting conditional
    - [x] Verify all tests pass

## Notes for the coding agent

- **Repo root sourcing**: The spec says `<repo_root>` is `os.getcwd()` at startup. Check how `i2code go` captures this — it likely needs to be threaded through to each subcommand function. Look at how `i2code go` orchestrates calls to these functions.
- **Flag format**: The `--allowedTools` value is a single comma-separated string: `"Read(/<repo_root>/),Write(/<idea_dir>/),Edit(/<idea_dir>/)"`— note the trailing slashes on paths.
- **All paths must be absolute** in the `--allowedTools` flag.
- **Implement using TDD** — each task writes a failing test first, then implements.
- **Test pattern**: Look at existing tests to match the project's mock/spy patterns for subprocess calls. The spec explicitly says "observable in tests without launching a real Claude process."
