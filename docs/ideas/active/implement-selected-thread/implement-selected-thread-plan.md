# Implementation Plan: Implement Selected Thread

## Idea Type

**C. Platform/infrastructure capability** — The idea adds a `--thread N` option to the `i2code implement` CLI, a developer workflow tool whose consumers are developers driving the idea-to-code workflow and scripts that invoke it.

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

`i2code implement --trunk` loops on `IdeaProject.get_next_task()` (`src/i2code/implement/trunk_mode.py:24`), which walks every thread in the plan, so a trunk run does not stop until the plan is complete. This plan adds `--thread N` to `i2code implement`. In trunk mode it runs the incomplete tasks of thread N only, then stops and names the next thread to run.

The project already has a working build and CI (`.github/workflows/ci.yml`, `./test-scripts/test-end-to-end.sh`). No build, CI or deployment infrastructure is created. Steel Thread 1 confirms that the existing unit test suite passes and delivers the primary scenario end to end.

Design, following the design pattern catalog (`design-pattern-catalog/index.md`):

- **Command + Assembler** (`design-pattern-catalog/commands/command-assembler.md`): `implement_cmd` packs `--thread` into `ImplementOpts.thread`. `ImplementCommand` and `TrunkMode` are tested directly with fakes. The CLI test only checks that the flag is forwarded.
- **Compose Method** (`design-pattern-catalog/refactoring/compose-method.md`): `TrunkMode.execute` delegates task selection to a selection object with a small interface: `validate()`, `next_task()` and `report_completion()`. `AllTasksSelection` keeps today's behavior. `ThreadSelection` implements thread N. Both live in `src/i2code/implement/task_selection.py`, so `TrunkMode` keeps a Code Health score of 10.0.
- Plan queries go in the plan domain: `Plan.get_next_task_in_thread` and `Plan.incomplete_threads_before`. `IdeaProject` exposes each query by opening the plan file with `with_plan_file`, the same way `IdeaProject.get_next_task` (`src/i2code/implement/idea_project.py:132`) does.

Testing:

- Unit tests are marked `@pytest.mark.unit` and run with `./test-scripts/test-unit.sh`.
- End-to-end tests run the real `i2code implement` CLI as a subprocess against a temporary local git repository, with a `--mock-claude` script that marks the first incomplete task complete and commits. They live in `tests/implement/test_trunk_thread_integration.py`, are marked `@pytest.mark.integration`, and run with `./test-scripts/test-integration.sh`. They make no GitHub or Claude API calls.

Every commit must pass `uvx pyright --level error src/` and the CodeScene `pre_commit_code_health_safeguard`, with a Code Health score of 10.0 for new and modified files, as `CLAUDE.md` requires.

---

## Steel Thread 1: Run One Thread in Trunk Mode and Stop

The developer runs `i2code implement --trunk --thread 1 <idea-directory>` on a plan with incomplete threads. i2code runs the tasks of thread 1 only, then reports that thread 1 is complete and prints the command for the next thread.

- [ ] **Task 1.1: `--trunk --thread 1` runs only thread 1's tasks and names the next thread**
  - TaskType: OUTCOME
  - Entrypoint: `i2code implement --trunk --thread 1 --mock-claude <script> <idea-directory>`
  - Observable: Every task of thread 1 is marked `[x]` in the plan file and has its own commit. Every task of threads 2 and 3 is still `[ ]`. Stdout contains `Thread 1 (Thread 1) is complete.` followed by `Next: i2code implement --trunk --thread 2 <idea-directory>`, where `<idea-directory>` is the resolved absolute idea directory. Exit status 0.
  - Evidence: `uv run --python 3.12 python3 -m pytest tests/implement/test_trunk_thread_integration.py::TestRunSelectedThread -v -m integration` runs the CLI as a subprocess on a committed three-thread plan, then asserts the exit status, the plan file checkboxes, the number of new commits (one per thread 1 task) and the two stdout lines
  - Steps:
    - [ ] Run `./test-scripts/test-unit.sh` and confirm the existing unit tests pass before making changes, and confirm `.github/workflows/ci.yml` exists. Do not change CI.
    - [ ] Move `create_mock_claude_script_that_marks_tasks_complete` from `tests/implement/test_task_execution_integration.py:35` to `tests/implement/conftest.py`, and update the import in `tests/implement/test_task_execution_integration.py`. Follow the `idea-to-code:file-organization` skill.
    - [ ] Add an `extra_args` parameter (default `None`) to `run_script` in `tests/implement/conftest.py:86` that appends extra CLI arguments, so tests can pass `--trunk` and `--thread N`
    - [ ] Create `tests/implement/test_trunk_thread_integration.py` with a fixture that builds on `test_git_repo_with_commit`. It creates `test-feature/` containing `test-feature-idea.md`, `test-feature-spec.md` and a plan written by `write_plan_file` (`tests/implement/conftest.py:125`) with threads 1, 2 and 3 of two incomplete tasks each, and commits them
    - [ ] Write the failing acceptance test `TestRunSelectedThread.test_runs_only_selected_thread_and_names_next_thread`, marked `@pytest.mark.integration`, that runs `run_script(idea_dir, cwd=tmpdir, mock_claude=script, extra_args=["--trunk", "--thread", "1"])`. Run it and confirm it fails because Click reports `No such option: --thread`.
    - [ ] Add `thread: int | None = None` to `ImplementOpts` (`src/i2code/implement/implement_opts.py:9`) and add `"thread"` to `_INNER_IGNORED` (`src/i2code/implement/implement_opts.py:45`). The existing `TestInnerFlagExhaustiveness` test (`tests/implement/test_implement_opts.py:111`) checks that every field is categorized.
    - [ ] Write a unit test in `tests/implement/test_implement_command.py` next to `test_uses_command_factory_and_forwards_opts` (`tests/implement/test_implement_command.py:377`) that invokes `implement_cmd` with `--trunk --thread 3` through `CliRunner`, with a `command_factory` in `ctx.obj`, and asserts that `opts.thread == 3`. Then add `@click.option("--thread", type=int, metavar="N", help="Implement only the incomplete tasks of thread N, then stop (requires --trunk)")` to `implement_cmd` (`src/i2code/implement/cli.py:55`).
    - [ ] Write unit tests in `tests/plan-domain/test_plan_get_next_task_in_thread.py` for `Plan.get_next_task_in_thread(thread)`. It returns the first incomplete task of the given thread as a `NumberedTask`, returns `None` when that thread has no incomplete task, and skips incomplete tasks in earlier and later threads. Implement it in `src/i2code/plan_domain/plan.py` next to `get_next_task` (`src/i2code/plan_domain/plan.py:58`).
    - [ ] Write unit tests in `tests/implement/test_idea_project.py` for `IdeaProject.get_next_task_in_thread(thread)` and `IdeaProject.thread_title(thread)`. They read the plan file with `with_plan_file` and delegate to `Plan.get_next_task_in_thread` and `Plan.get_thread(thread).title`. Implement them in `src/i2code/implement/idea_project.py`.
    - [ ] Write a unit test in `tests/implement/test_task_selection.py` for `AllTasksSelection`. `next_task()` returns `project.get_next_task()`, and `report_completion()` prints `All tasks completed!`. Create `src/i2code/implement/task_selection.py` with `AllTasksSelection`. Its `validate()` does nothing.
    - [ ] Refactor `TrunkMode.execute` (`src/i2code/implement/trunk_mode.py:24`) to build `AllTasksSelection` when `opts.thread` is `None`. The method calls `selection.validate()`, then `commit_if_needed()`, then loops on `selection.next_task()`, then calls `selection.report_completion()`. Run `tests/implement/test_trunk_mode.py` and confirm the existing tests pass unchanged.
    - [ ] Write unit tests in `tests/implement/test_task_selection.py` for `ThreadSelection(project, thread, idea_directory)`. `next_task()` returns `project.get_next_task_in_thread(thread)`. When a later thread has an incomplete task, `report_completion()` prints `Thread N (<title>) is complete.` and `Next: i2code implement --trunk --thread M <idea_directory>`, where M is `project.get_next_task().number.thread`. Implement `ThreadSelection` in `src/i2code/implement/task_selection.py`.
    - [ ] Write a unit test in `tests/implement/test_trunk_mode.py` with `opts.thread=1` and a plan whose threads 1 and 2 are both incomplete. It asserts that `FakeClaudeRunner` runs thread 1's tasks only, and that `commit_if_needed` runs before the first task, using a recording commit recovery whose call is asserted with `assert_called_once`. Make `TrunkMode` build `ThreadSelection(project, opts.thread, opts.idea_directory)` when `opts.thread` is set.
    - [ ] Run the acceptance test and confirm it passes
    - [ ] Add `--thread N` to the `### Additional Flags` section and the `## 3. Trunk Mode (`--trunk`)` section of `docs/design/implement-steps.md`
    - [ ] Run `./test-scripts/test-unit.sh`, `./test-scripts/test-integration.sh` and `uvx pyright --level error src/`, and run the CodeScene `pre_commit_code_health_safeguard` on the staged changes

- [ ] **Task 1.2: Finishing the last incomplete thread reports that all tasks are complete**
  - TaskType: OUTCOME
  - Entrypoint: `i2code implement --trunk --thread 3 --mock-claude <script> <idea-directory>`
  - Observable: With threads 1 and 2 complete, every task of thread 3 is marked `[x]`. Stdout contains `All tasks completed!` and contains neither `Thread 3 (Thread 3) is complete.` nor a `Next:` line. Exit status 0.
  - Evidence: `uv run --python 3.12 python3 -m pytest tests/implement/test_trunk_thread_integration.py::TestRunSelectedThread::test_last_thread_reports_all_tasks_completed -v -m integration` runs the CLI as a subprocess, then asserts the exit status, the plan file checkboxes and stdout
  - Steps:
    - [ ] Write the failing acceptance test `test_last_thread_reports_all_tasks_completed` in `tests/implement/test_trunk_thread_integration.py`. Its plan has threads 1 and 2 complete and thread 3 incomplete.
    - [ ] Write a unit test in `tests/implement/test_task_selection.py`: when `project.get_next_task()` returns `None`, `ThreadSelection.report_completion()` prints `All tasks completed!` and nothing else. Implement it in `src/i2code/implement/task_selection.py`.
    - [ ] Run the acceptance test and confirm it passes

---

## Steel Thread 2: Reject `--thread` Without `--trunk`

The developer runs `--thread` in worktree or isolate mode. i2code reports a usage error before it creates any branch, worktree, clone or PR.

- [ ] **Task 2.1: `--thread` without `--trunk` exits with a usage error before any setup**
  - TaskType: OUTCOME
  - Entrypoint: `i2code implement --thread 2 <idea-directory>`, `i2code implement --isolate --thread 2 <idea-directory>` and `i2code implement --shell --thread 2 <idea-directory>`
  - Observable: Each command writes `Error: --thread requires --trunk` to stderr and exits with status 2. After each run, the repository has no `idea/test-feature` branch and no `-wt-test-feature` worktree directory next to the repository.
  - Evidence: `uv run --python 3.12 python3 -m pytest tests/implement/test_trunk_thread_integration.py::TestThreadRequiresTrunk -v -m integration` runs each command as a subprocess, then asserts the exit status, stderr, the branch list and the absence of the worktree directory
  - Steps:
    - [ ] Write the failing acceptance test `TestThreadRequiresTrunk`, parametrized over the three argument lists
    - [ ] Write unit tests in `tests/implement/test_implement_opts.py` for `ImplementOpts.validate_thread_option()`. It raises `click.UsageError("--thread requires --trunk")` when `thread` is set and `trunk` is false, and passes when `thread` is `None` or `trunk` is true. Implement it in `src/i2code/implement/implement_opts.py` next to `validate_trunk_options` (`src/i2code/implement/implement_opts.py:66`).
    - [ ] Write a unit test in `tests/implement/test_implement_command.py`: with `isolation_type` set and `thread=2`, `execute()` raises `click.UsageError` and `mode_factory.make_isolate_mode` is not called. Call `self.opts.validate_thread_option()` at the end of `_validate_and_apply_defaults` (`src/i2code/implement/implement_command.py:122`), after `isolation_type` and `shell` have set `isolate`.
    - [ ] Run the acceptance test and confirm it passes

---

## Steel Thread 3: Reject an Out-of-Range Thread Number

The developer gives a thread number the plan does not have. i2code reports the valid range and runs no task.

- [ ] **Task 3.1: An out-of-range thread number exits with a usage error naming the valid range**
  - TaskType: OUTCOME
  - Entrypoint: `i2code implement --trunk --thread 4 --mock-claude <script> <idea-directory>` and `i2code implement --trunk --thread 0 --mock-claude <script> <idea-directory>`
  - Observable: On a three-thread plan, each command writes `Error: --thread must be between 1 and 3` to stderr and exits with status 2. HEAD is unchanged and the plan file is unchanged.
  - Evidence: `uv run --python 3.12 python3 -m pytest tests/implement/test_trunk_thread_integration.py::TestThreadOutOfRange -v -m integration` records HEAD and the plan file contents, runs each command as a subprocess, then asserts the exit status, stderr, HEAD and the plan file contents
  - Steps:
    - [ ] Write the failing acceptance test `TestThreadOutOfRange`, parametrized over `4` and `0`
    - [ ] Write a unit test in `tests/implement/test_idea_project.py` for `IdeaProject.thread_count()`, which returns `len(plan.threads)` read with `with_plan_file`. Implement it in `src/i2code/implement/idea_project.py`.
    - [ ] Write unit tests in `tests/implement/test_task_selection.py`: `ThreadSelection.validate()` raises `click.UsageError("--thread must be between 1 and 3")` for thread 0 and thread 4 on a three-thread plan. Implement the range check in `ThreadSelection.validate()`.
    - [ ] Write a unit test in `tests/implement/test_trunk_mode.py` with `opts.thread=4`. It asserts that `TrunkMode.execute()` raises `click.UsageError`, that the recording commit recovery's `commit_if_needed` is not called (`assert_not_called`), and that `FakeClaudeRunner` ran no command.
    - [ ] Run the acceptance test and confirm it passes

---

## Steel Thread 4: Enforce Thread Order

The developer selects a thread while an earlier thread still has incomplete tasks. i2code names the incomplete earlier threads and runs no task.

- [ ] **Task 4.1: Selecting a thread with incomplete earlier threads exits with an error naming them**
  - TaskType: OUTCOME
  - Entrypoint: `i2code implement --trunk --thread 3 --mock-claude <script> <idea-directory>`
  - Observable: With thread 1 incomplete and thread 2 incomplete, stderr contains `Error: Cannot run thread 3: earlier threads have incomplete tasks: 1, 2` and the exit status is 1. With thread 1 complete and thread 2 incomplete, stderr contains `Error: Cannot run thread 3: earlier threads have incomplete tasks: 2`. In both cases HEAD and the plan file are unchanged.
  - Evidence: `uv run --python 3.12 python3 -m pytest tests/implement/test_trunk_thread_integration.py::TestThreadOrder -v -m integration` records HEAD and the plan file contents, runs the command as a subprocess for each plan state, then asserts the exit status, stderr, HEAD and the plan file contents
  - Steps:
    - [ ] Write the failing acceptance test `TestThreadOrder`, parametrized over the two plan states
    - [ ] Write unit tests in `tests/plan-domain/test_plan_incomplete_threads_before.py` for `Plan.incomplete_threads_before(thread)`. It returns, in ascending order, the numbers of threads below `thread` that have at least one incomplete task, and returns an empty list for thread 1. Implement it in `src/i2code/plan_domain/plan.py`.
    - [ ] Write a unit test in `tests/implement/test_idea_project.py` for `IdeaProject.incomplete_threads_before(thread)`, which delegates to the plan read with `with_plan_file`. Implement it in `src/i2code/implement/idea_project.py`.
    - [ ] Write a unit test in `tests/implement/test_task_selection.py`: when earlier threads are incomplete, `ThreadSelection.validate()` prints `Error: Cannot run thread 3: earlier threads have incomplete tasks: 1, 2` to stderr and calls `sys.exit(1)`. Implement the order check in `ThreadSelection.validate()` after the range check.
    - [ ] Write a unit test in `tests/implement/test_trunk_mode.py`: when the order check fails, the recording commit recovery's `commit_if_needed` is not called (`assert_not_called`) and `FakeClaudeRunner` ran no command
    - [ ] Run the acceptance test and confirm it passes

---

## Steel Thread 5: Report an Already Complete Thread

The developer selects a thread that has no incomplete tasks. i2code reports it, names the next thread and runs no task.

- [ ] **Task 5.1: Selecting an already complete thread reports it and names the next thread**
  - TaskType: OUTCOME
  - Entrypoint: `i2code implement --trunk --thread 2 --mock-claude <script> <idea-directory>`
  - Observable: With threads 1 and 2 complete and thread 3 incomplete, stdout contains `Thread 2 (Thread 2) is already complete.` followed by `Next: i2code implement --trunk --thread 3 <idea-directory>`. The exit status is 0. HEAD and the plan file are unchanged.
  - Evidence: `uv run --python 3.12 python3 -m pytest tests/implement/test_trunk_thread_integration.py::TestThreadAlreadyComplete -v -m integration` records HEAD and the plan file contents, runs the command as a subprocess, then asserts the exit status, stdout, HEAD and the plan file contents
  - Steps:
    - [ ] Write the failing acceptance test `TestThreadAlreadyComplete`
    - [ ] Write unit tests in `tests/implement/test_task_selection.py` for `ThreadSelection.is_already_complete()` and `ThreadSelection.report_already_complete()`. The second prints `Thread N (<title>) is already complete.` followed by the same next-thread line that `report_completion()` prints. Extract that shared line into a private method of `ThreadSelection`. Add `is_already_complete()` returning `False` to `AllTasksSelection`.
    - [ ] Write a unit test in `tests/implement/test_trunk_mode.py`: with `opts.thread=2` on an already complete thread 2, `TrunkMode.execute()` prints the already-complete message, the recording commit recovery's `commit_if_needed` is not called (`assert_not_called`), and `FakeClaudeRunner` ran no command. In `TrunkMode.execute`, after `selection.validate()`, call `selection.report_already_complete()` and return when `selection.is_already_complete()` is true.
    - [ ] Run the acceptance test and confirm it passes

---

## Steel Thread 6: Show the Selected Thread in a Dry Run

The developer runs a dry run with `--thread`. i2code shows the selected thread without reading the plan's task state.

- [ ] **Task 6.1: `--dry-run --trunk --thread N` prints the selected thread**
  - TaskType: OUTCOME
  - Entrypoint: `i2code implement --dry-run --trunk --thread 5 <idea-directory>`
  - Observable: On a three-thread plan, stdout contains the `Mode: trunk`, `Idea: test-feature` and `Directory: <idea-directory>` lines followed by `Thread: 5`. The exit status is 0, because a dry run does not apply the range check. `--dry-run --thread 5` without `--trunk` still exits with `Error: --thread requires --trunk` and status 2. A dry run without `--thread` prints no `Thread:` line.
  - Evidence: `uv run --python 3.12 python3 -m pytest tests/implement/test_trunk_thread_integration.py::TestThreadDryRun -v -m integration` runs each command as a subprocess, then asserts the exit status and the stdout and stderr lines in order
  - Steps:
    - [ ] Write the failing acceptance test `TestThreadDryRun` with the three cases
    - [ ] Write unit tests in `tests/implement/test_implement_command.py` in `TestImplementCommandDryRun` (`tests/implement/test_implement_command.py:39`): with `thread=5`, `_print_dry_run` prints `Thread: 5` after `Directory:`, and without `thread` it prints no `Thread:` line. Implement this in `_print_dry_run` (`src/i2code/implement/implement_command.py:146`).
    - [ ] Run the acceptance test and confirm it passes

---

## Steel Thread 7: Resume a Thread After a Failed Task

A task in the selected thread fails all three attempts. The developer reruns the same thread, and i2code resumes at the thread's first incomplete task.

- [ ] **Task 7.1: Rerunning a thread after a failed task resumes at the thread's first incomplete task**
  - TaskType: OUTCOME
  - Entrypoint: `i2code implement --trunk --thread 2 --non-interactive --mock-claude <script> <idea-directory>`, run twice
  - Observable: With thread 1 complete, the first run uses a mock script that exits 1 without committing. Stderr contains `Error: Task failed after 3 attempts.`, the exit status is 1 and the plan file is unchanged. The second run uses the completing mock script. It marks every task of thread 2 `[x]`, leaves thread 3 `[ ]`, prints `Thread 2 (Thread 2) is complete.` and exits with status 0.
  - Evidence: `uv run --python 3.12 python3 -m pytest tests/implement/test_trunk_thread_integration.py::TestThreadResumeAfterFailure -v -m integration` runs the command as a subprocess twice and asserts the exit status, stderr, stdout and plan file checkboxes after each run
  - Steps:
    - [ ] Add `create_failing_mock_claude_script(tmpdir)` to `tests/implement/conftest.py`. It writes an executable script that exits 1 without changing any file.
    - [ ] Write the acceptance test `TestThreadResumeAfterFailure` and run it. If it passes without production changes, the behavior already comes from `ThreadSelection.next_task()` and the existing retry loop in `TrunkMode._execute_task` (`src/i2code/implement/trunk_mode.py:36`); record this in the commit message. If it fails, write a failing unit test in `tests/implement/test_trunk_mode.py` that reproduces the failure, then fix `src/i2code/implement/trunk_mode.py`.
    - [ ] Run `./test-scripts/test-unit.sh`, `./test-scripts/test-integration.sh` and `uvx pyright --level error src/`, and run the CodeScene `pre_commit_code_health_safeguard` on the staged changes

---

## Change History