I don't have permission to read source files outside the current directory. I'll generate the plan based on the detailed spec. The spec provides clear API signatures in FR-3 and FR-4.

Here is the plan:

---

# Scaffolding-Task Conflict Bug — Implementation Plan

## Idea Type

**C. Platform/infrastructure capability** — This is an internal developer tool regression test, not a user-facing feature.

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

## Overview

This plan creates a `@pytest.mark.manual` test that reproduces the scaffolding-task CI file conflict bug. The test calls real Claude (non-interactive mode) to run scaffolding and then execute the first plan task, asserting that the two phases produce conflicting CI workflow files (`.github/workflows/ci.yaml` vs `.github/workflows/ci.yml`).

Since this is a Python project with pytest, there is no CI workflow to create — the existing project CI already runs pytest. The test is marked `manual` and excluded from normal runs.

## Steel Thread 1: Reproduce Scaffolding-Task CI File Conflict

This single steel thread implements the primary scenario: set up a temp repo, run scaffolding, run the first task, and assert the conflict.

- [x] **Task 1.1: Test setup creates a temp git repo with hello-world idea fixtures**
  - TaskType: OUTCOME
  - Entrypoint: `uv run pytest tests/implement/test_scaffolding_task_conflict.py::test_scaffolding_task_conflict_creates_duplicate_ci_files -m manual -v`
  - Observable: A pytest test function exists, is tagged `@pytest.mark.manual`, creates a temp git repo containing the hello-world fixtures under `docs/features/hello-world/`, and the repo has an initial commit
  - Evidence: The test runs (may fail at later assertions), but the temp repo setup succeeds — verified by asserting the fixtures directory exists and `git log` shows a commit in the temp repo
  - Steps:
    - [x] Create `tests/implement/test_scaffolding_task_conflict.py` with a test function `test_scaffolding_task_conflict_creates_duplicate_ci_files`
    - [x] Add `@pytest.mark.manual` decorator
    - [x] Use `tmp_path` fixture to create a temporary directory
    - [x] Implement helper logic to: `git init` the temp dir, copy fixtures from `tests/implement/fixtures/hello-world/` into `docs/features/hello-world/` within the temp repo, `git add .`, `git commit`
    - [x] Assert that `docs/features/hello-world/hello-world-idea.txt` exists in the temp repo
    - [x] Assert that `docs/features/hello-world/hello-world-plan.md` exists in the temp repo
    - [x] Run the test to verify setup works (test should pass at this point since only setup assertions exist)

- [ ] **Task 1.2: Scaffolding phase creates ci.yaml in the temp repo**
  - TaskType: OUTCOME
  - Entrypoint: `uv run pytest tests/implement/test_scaffolding_task_conflict.py::test_scaffolding_task_conflict_creates_duplicate_ci_files -m manual -v`
  - Observable: After running `ScaffoldingCreator.run_scaffolding()` in non-interactive mode, `.github/workflows/ci.yaml` exists in the temp repo
  - Evidence: The test invokes scaffolding via the lower-level API (`CommandBuilder`, `ClaudeRunner(interactive=False)`, `ScaffoldingCreator`) against the temp repo, then asserts `.github/workflows/ci.yaml` exists
  - Steps:
    - [ ] Import `ScaffoldingCreator`, `CommandBuilder`, and `ClaudeRunner` from the appropriate `i2code.implement` modules
    - [ ] In the test, after repo setup, create `CommandBuilder()`, `ClaudeRunner(interactive=False)`, and `ScaffoldingCreator(command_builder, claude_runner)`
    - [ ] Call `scaffolding_creator.run_scaffolding(idea_directory, cwd=temp_repo, interactive=False)` where `idea_directory` is the `docs/features/hello-world/` path within the temp repo
    - [ ] Assert that `temp_repo / ".github" / "workflows" / "ci.yaml"` exists

- [ ] **Task 1.3: First task execution creates conflicting ci.yml, reproducing the bug**
  - TaskType: OUTCOME
  - Entrypoint: `uv run pytest tests/implement/test_scaffolding_task_conflict.py::test_scaffolding_task_conflict_creates_duplicate_ci_files -m manual -v`
  - Observable: After executing the first plan task via `CommandBuilder.build_task_command()` + `ClaudeRunner.run()`, `.github/workflows/ci.yml` does NOT exist (this assertion is expected to FAIL, reproducing the bug). The test is tagged `@pytest.mark.manual` and uses `pytest.xfail(reason="Bug: scaffolding-task conflict creates duplicate CI files", strict=True)` or equivalent to document that failure is expected
  - Evidence: The test extracts the first task via `IdeaProject(idea_directory).get_next_task()`, builds and runs the task command with `TaskCommandOpts(interactive=False)`, then asserts `ci.yml` does NOT exist — this assertion fails, confirming the bug
  - Steps:
    - [ ] Import `IdeaProject` and `TaskCommandOpts` from the appropriate `i2code` modules
    - [ ] After scaffolding, create `IdeaProject(idea_directory)` and call `get_next_task()` to get the first task
    - [ ] Build the task command via `CommandBuilder().build_task_command(idea_directory, task.print())` with `TaskCommandOpts(interactive=False)`
    - [ ] Run the command via `ClaudeRunner(interactive=False).run(cmd, cwd=temp_repo)`
    - [ ] Assert that `temp_repo / ".github" / "workflows" / "ci.yml"` does NOT exist
    - [ ] Mark the final assertion with `pytest.xfail` or add a comment explaining the assertion is expected to fail, reproducing the bug
    - [ ] Verify the test runs end-to-end and the final assertion fails as expected (confirming the bug)
