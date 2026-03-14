Now I have all the context needed. Here is the implementation plan:

---

# Implementation Plan: Bulk-Complete Ideas with Finished Plans

## Idea Type

A. User-facing feature

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

Add a `--completed-plans` flag to `i2code idea state` that bulk-transitions all `wip` ideas with fully-completed plans to `completed` state. This fills the workflow gap between `i2code implement` (completes plan tasks) and `i2code idea archive --completed` (archives completed ideas).

The implementation modifies `src/i2code/idea_cmd/state_cmd.py` to add the new flag, following the same bulk-operation pattern established by `_archive_completed()` in `src/i2code/idea_cmd/archive_cmd.py`. All tasks use TDD.

### Key existing code

- **CLI command**: `src/i2code/idea_cmd/state_cmd.py` — the `idea_state` Click command (line 87)
- **Bulk pattern reference**: `src/i2code/idea_cmd/archive_cmd.py:55` — `_archive_completed()` function
- **Idea listing**: `src/i2code/idea/resolver.py` — `list_ideas(git_root)` returns `list[IdeaInfo]`
- **State transition**: `src/i2code/idea_cmd/state_cmd.py:46` — `execute_transition(name, old_path, new_state, git_root)`
- **Plan parser**: `src/i2code/plan_domain/parser.py:14` — `parse(text)` returns `Plan`
- **Plan model**: `src/i2code/plan_domain/plan.py` — `get_next_task()` (line 58), `task_progress()` (line 68)
- **Existing tests**: `tests/idea-cmd/test_idea_state_cli.py`

---

## Steel Thread 1: Bulk-complete wip ideas with finished plans

This thread implements the primary happy-path scenario (Scenario 1 from spec): multiple wip ideas with completed plans are transitioned in a single command.

- [x] **Task 1.1: `--completed-plans` transitions wip ideas with all-done plans to completed**
  - TaskType: OUTCOME
  - Entrypoint: `i2code idea state --completed-plans`
  - Observable: All `wip` ideas whose plan files have every task marked `[x]` are transitioned to `completed`. Each transition prints `Move idea <name> from wip to completed`. A single git commit is created with message `Mark ideas with completed plans as completed: <names>`. Ideas with incomplete plans remain in `wip`.
  - Evidence: pytest test in `tests/idea-cmd/test_idea_state_cli.py` that creates three wip ideas (two with fully-completed plans, one with an incomplete plan), invokes the CLI, asserts exit code 0, verifies output contains both transition messages, verifies the incomplete idea remains wip, and checks the git commit message.
  - Steps:
    - [x] Write a test class `TestCompletedPlans` in `tests/idea-cmd/test_idea_state_cli.py` with a test that sets up a git repo with three active wip ideas, creates plan files (two fully completed, one incomplete), invokes `i2code idea state --completed-plans`, and asserts the expected output, metadata state changes, and commit message
    - [x] Add `--completed-plans` flag to the `idea_state` Click command in `src/i2code/idea_cmd/state_cmd.py`. Make `name_or_path` optional (change `required` to `False`, default to `None`)
    - [x] Implement `_complete_finished_plans(git_root, no_commit)` function in `src/i2code/idea_cmd/state_cmd.py` following the `_archive_completed()` pattern from `src/i2code/idea_cmd/archive_cmd.py:55`: use `list_ideas(git_root)` to find wip ideas, check each for a plan file at `<idea_dir>/<name>-plan.md`, parse it with `i2code.plan_domain.parser.parse()`, check `plan.task_progress().total > 0` and `plan.get_next_task() is None`, call `execute_transition()` for matches, then commit
    - [x] Update the `idea_state` command body to dispatch to `_complete_finished_plans()` when `--completed-plans` is set

## Steel Thread 2: Empty result handling

Implements Scenario 2: no matching ideas found.

- [x] **Task 2.1: Print informational message when no wip ideas have completed plans**
  - TaskType: OUTCOME
  - Entrypoint: `i2code idea state --completed-plans`
  - Observable: Prints `No wip ideas with completed plans found` to stdout, exits 0, no git commit created
  - Evidence: pytest test that creates wip ideas without plan files (or with incomplete plans), invokes the CLI, asserts exit code 0 and output message, and verifies no new commit was created
  - Steps:
    - [x] Write test in `TestCompletedPlans` that sets up a git repo with a wip idea that has no plan file and a wip idea with an incomplete plan, invokes `--completed-plans`, asserts output is `No wip ideas with completed plans found` and exit code is 0
    - [x] Verify the `_complete_finished_plans()` implementation handles the empty case (this should already work from Task 1.1's implementation)

## Steel Thread 3: `--no-commit` support

Implements Scenario 3: stage without committing.

- [ ] **Task 3.1: `--completed-plans --no-commit` stages changes without creating a commit**
  - TaskType: OUTCOME
  - Entrypoint: `i2code idea state --completed-plans --no-commit`
  - Observable: Matching ideas' metadata files are updated and staged, transition messages are printed, but no git commit is created
  - Evidence: pytest test that creates a wip idea with completed plan, invokes with both flags, asserts transition message in output, verifies metadata file shows `completed`, and checks no new commit was created
  - Steps:
    - [ ] Write test in `TestCompletedPlans` that sets up git repo with one wip idea with a completed plan, invokes `--completed-plans --no-commit`, asserts output, checks metadata state is `completed`, and verifies commit count hasn't changed
    - [ ] Verify `_complete_finished_plans()` respects the `no_commit` parameter (should already work from Task 1.1)

## Steel Thread 4: Mutual exclusivity and validation

Implements Scenarios 4, 5, and 6: error handling and edge cases.

- [ ] **Task 4.1: Error when both `name_or_path` and `--completed-plans` are provided**
  - TaskType: OUTCOME
  - Entrypoint: `i2code idea state my-idea --completed-plans`
  - Observable: Raises `UsageError` with message `Provide an idea name or use --completed-plans, not both.`, non-zero exit code
  - Evidence: pytest test that invokes with both a name argument and `--completed-plans` flag, asserts non-zero exit code and error message in output
  - Steps:
    - [ ] Write test in `TestCompletedPlans` that invokes `i2code idea state my-idea --completed-plans` and asserts the usage error message and non-zero exit
    - [ ] Add validation at the top of `idea_state` command: if both `name_or_path` and `completed_plans` are provided, raise `click.UsageError`; if neither is provided (and `name_or_path` is None and not `completed_plans`), raise `click.UsageError` with `Provide an idea name or use --completed-plans.`

- [ ] **Task 4.2: Wip ideas without plan files or with empty plans are skipped**
  - TaskType: OUTCOME
  - Entrypoint: `i2code idea state --completed-plans`
  - Observable: Wip idea without plan file is skipped. Wip idea with empty plan (zero tasks) is skipped. Only ideas with at least one task and all tasks complete are transitioned.
  - Evidence: pytest test that creates three wip ideas: one without a plan file, one with an empty plan (no tasks), and one with a fully completed plan. Asserts only the completed-plan idea is transitioned.
  - Steps:
    - [ ] Write test in `TestCompletedPlans` with three wip ideas (no plan, empty plan, completed plan), invokes `--completed-plans`, asserts only the completed-plan idea appears in output and has state `completed`
    - [ ] Verify the implementation correctly skips ideas where plan file doesn't exist or `task_progress().total == 0` (should already work from Task 1.1)

---

## Change History
### 2026-03-14 15:54 - mark-step-complete
Test class TestCompletedPlans written with test_transitions_wip_ideas_with_completed_plans

### 2026-03-14 15:55 - mark-step-complete
Added --completed-plans flag and made name_or_path optional

### 2026-03-14 15:55 - mark-step-complete
Implemented _complete_finished_plans following _archive_completed pattern

### 2026-03-14 15:55 - mark-step-complete
Updated idea_state command body to dispatch to _complete_finished_plans

### 2026-03-14 15:55 - mark-task-complete
All steps completed, test passes, CodeScene quality gates pass

### 2026-03-14 15:56 - mark-step-complete
Test written and passes

### 2026-03-14 15:56 - mark-step-complete
Implementation already handles empty case from Task 1.1

### 2026-03-14 15:56 - mark-task-complete
Test verifies empty case handling
