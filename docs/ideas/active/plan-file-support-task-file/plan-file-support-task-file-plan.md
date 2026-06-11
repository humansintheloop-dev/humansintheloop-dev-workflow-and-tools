Now I have enough context. The project already has a working CI pipeline. Let me produce the plan.

# Implementation Plan: File-Based Input for Plan CLI Commands

## Idea Type

**A. User-facing feature** — Improves CLI ergonomics for existing `i2code plan` thread- and task-creation commands.

---

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

## Overview

The `i2code plan` CLI exposes commands that create threads (`insert-thread-before`, `insert-thread-after`, `replace-thread`) and single tasks (`insert-task-before`, `insert-task-after`, `replace-task`). Only `replace-thread` currently supports `--tasks-file`; the other thread-creation commands require inline `--tasks`, and the single-task commands have no file-based input at all.

This plan adds file-based input across all five affected commands:

- **`--tasks-file`** added to `insert-thread-before` and `insert-thread-after` (matches existing `replace-thread` pattern).
- **`--task-file`** added to `insert-task-before`, `insert-task-after`, and `replace-task` (loads the entire task definition from a JSON object).
- **Consistency refactor** of `replace-thread` so it uses the shared `_thread_spec_options` decorator alongside the other insert-thread commands.

All existing inline option behavior is preserved. Implementation should follow TDD — each task adds the failing test first, then production code to make it pass.

### Key existing code locations

- `src/i2code/plan/thread_cli.py:12-20` — `_thread_spec_options` decorator (currently lacks `--tasks-file`).
- `src/i2code/plan/thread_cli.py:23-34` — `_resolve_tasks_json` helper (already used by `replace-thread`).
- `src/i2code/plan/thread_cli.py:88-103` — `replace_thread_cmd` (defines options inline rather than via the shared decorator).
- `src/i2code/plan/task_cli.py:12-23` — `_task_spec_options` decorator for single-task commands.
- `src/i2code/plan/task_cli.py:26-39` — `_parse_task_spec` helper.
- `tests/plan-manager/test_insert_thread_cli.py` — tests for `insert-thread-before` and `insert-thread-after`.
- `tests/plan-manager/test_replace_thread_cli.py` — reference pattern showing `--tasks-file` test setup.
- `tests/plan-manager/test_insert_task_before_cli.py`, `test_insert_task_after_cli.py`, `test_replace_task_cli.py` — tests for the three single-task commands.

### Test command

The project uses Python/`uv`. Run the affected test suite with:

```
uv run --python 3.12 python3 -m pytest tests/plan-manager/ -v
```

The full end-to-end CI script is `./test-scripts/test-end-to-end.sh`; use it before committing.

---

## Steel Thread 1: Verify existing build passes

Establishes the baseline. The project already has a working build, CI workflow (`.github/workflows/ci.yml`), and test infrastructure (`test-scripts/test-end-to-end.sh`); no infrastructure work is needed beyond confirming everything passes before changes begin.

- [x] **Task 1.1: Existing test suite passes on a clean checkout**
  - TaskType: INFRA
  - Entrypoint: `./test-scripts/test-end-to-end.sh`
  - Observable: Script exits with code 0; all `tests/plan-manager/` tests pass.
  - Evidence: `./test-scripts/test-end-to-end.sh` runs the full pytest suite (including `tests/plan-manager/`) and exits 0.
  - Steps:
    - [x] Run `./test-scripts/test-end-to-end.sh` from the project root.
    - [x] Confirm exit code 0 and that no plan-manager tests fail.
    - [x] If anything fails, STOP — diagnose and report before continuing.

---

## Steel Thread 2: `--tasks-file` on `insert-thread-after` (US-1.1)

Implements the primary user story: a coding agent writes a JSON array of tasks to a file and passes it via `--tasks-file` to `insert-thread-after`. This is the smallest behaviour change that proves the file-loading path end-to-end on an insert-thread command.

- [x] **Task 2.1: `insert-thread-after --tasks-file` inserts a thread using JSON from a file**
  - TaskType: OUTCOME
  - Entrypoint: `i2code plan insert-thread-after <plan> --after <n> --title <t> --introduction <i> --tasks-file <path> --rationale <r>`
  - Observable: When `--tasks-file` points to a JSON array of task objects, the command inserts a new thread after thread `n` whose tasks are parsed from the file; the plan file is updated and exit code is 0. If both `--tasks` and `--tasks-file` are provided, command exits 1 with stderr `"insert-thread-after: --tasks and --tasks-file are mutually exclusive"`. If neither is provided, command exits 1 with stderr `"insert-thread-after: either --tasks or --tasks-file is required"`.
  - Evidence: New pytest tests in `tests/plan-manager/test_insert_thread_cli.py` invoke `insert_thread_after_cmd` via `CliRunner` with (a) a `--tasks-file`, (b) both options, (c) neither option, and assert plan content and exit codes. Tests run via `uv run --python 3.12 python3 -m pytest tests/plan-manager/test_insert_thread_cli.py -v` and pass.
  - Steps:
    - [x] In `tests/plan-manager/test_insert_thread_cli.py`, add a `tasks_source` parameter to `_invoke_thread_cmd` (mirroring `tests/plan-manager/test_replace_thread_cli.py:71`) so it can write `NEW_TASKS_JSON` to a temp file and pass `--tasks-file` instead of `--tasks`.
    - [x] Add `test_inserts_thread_using_tasks_file` to `TestInsertThreadAfterCli` that asserts the plan was updated and exit code is 0.
    - [x] Add `test_error_when_both_tasks_and_tasks_file_provided` that builds args containing both `--tasks` and `--tasks-file` and asserts exit 1 with the exact mutual-exclusivity message.
    - [x] Add `test_error_when_neither_tasks_nor_tasks_file_provided` that omits both and asserts exit 1 with the "either ... or ... is required" message.
    - [x] Run the test file — confirm the new tests fail (`--tasks-file` does not yet exist on `insert-thread-after`).
    - [x] In `src/i2code/plan/thread_cli.py:12-20`, update `_thread_spec_options` so `--tasks` becomes `required=False, default=None` and add `click.option("--tasks-file", default=None, type=click.Path(exists=True), help="Path to JSON file containing task objects")`.
    - [x] In `insert_thread_after_cmd` (`src/i2code/plan/thread_cli.py:66`), call `_resolve_tasks_json("insert-thread-after", kwargs.pop("tasks"), kwargs.pop("tasks_file"))` to obtain the JSON string before invoking `_parse_thread`.
    - [x] Re-run the test file and confirm all tests pass (including pre-existing tests for the inline `--tasks` path).

---

## Steel Thread 3: `--tasks-file` on `insert-thread-before` (US-1.2, US-1.3)

Applies the same shared infrastructure to `insert-thread-before`. Because Steel Thread 2 already updated `_thread_spec_options`, the option appears automatically on `insert-thread-before`; this thread verifies the behaviour and locks in tests for the mutual-exclusivity errors.

- [x] **Task 3.1: `insert-thread-before --tasks-file` inserts a thread using JSON from a file**
  - TaskType: OUTCOME
  - Entrypoint: `i2code plan insert-thread-before <plan> --before <n> --title <t> --introduction <i> --tasks-file <path> --rationale <r>`
  - Observable: When `--tasks-file` is supplied, a new thread is inserted before thread `n` using tasks parsed from the file; exit code 0. Conflicting options produce the same mutual-exclusivity errors as `insert-thread-after`, prefixed with `"insert-thread-before:"`.
  - Evidence: New pytest tests in `tests/plan-manager/test_insert_thread_cli.py` exercise the file-based path and both error cases for `insert_thread_before_cmd`; the test file passes via `uv run --python 3.12 python3 -m pytest tests/plan-manager/test_insert_thread_cli.py -v`.
  - Steps:
    - [x] Add `test_inserts_thread_using_tasks_file` to `TestInsertThreadBeforeCli` mirroring the `insert-thread-after` test, with `("--before", "2")` positioning.
    - [x] Add `test_error_when_both_tasks_and_tasks_file_provided` for `insert_thread_before_cmd`, asserting `"insert-thread-before: --tasks and --tasks-file are mutually exclusive"`.
    - [x] Add `test_error_when_neither_tasks_nor_tasks_file_provided` for `insert_thread_before_cmd`, asserting `"insert-thread-before: either --tasks or --tasks-file is required"`.
    - [x] Run the new tests; confirm they pass without further production changes (decorator change from Steel Thread 2 already covers this command).
    - [x] In `insert_thread_before_cmd` (`src/i2code/plan/thread_cli.py:52`), call `_resolve_tasks_json("insert-thread-before", kwargs.pop("tasks"), kwargs.pop("tasks_file"))` and confirm tests still pass.

---

## Steel Thread 4: Refactor `replace-thread` to use shared decorator (US-3.1)

`replace_thread_cmd` currently defines its options inline (`src/i2code/plan/thread_cli.py:88-103`). With `--tasks-file` now in `_thread_spec_options`, `replace_thread_cmd` can use the shared decorator and `_resolve_tasks_json` directly. This is a structure-only change — existing tests must continue to pass unchanged.

- [x] **Task 4.1: `replace-thread` uses `_thread_spec_options` without behaviour change**
  - TaskType: REFACTOR
  - Entrypoint: `i2code plan replace-thread <plan> --thread <n> --title <t> --introduction <i> (--tasks <json> | --tasks-file <path>) --rationale <r>`
  - Observable: No behaviour change — all existing `replace-thread` behaviour, error messages, and option names are unchanged. The duplicated `--title`, `--introduction`, `--tasks`, `--tasks-file` option definitions in `replace_thread_cmd` are replaced by `@_thread_spec_options`.
  - Evidence: The pre-existing `tests/plan-manager/test_replace_thread_cli.py` suite continues to pass unchanged via `uv run --python 3.12 python3 -m pytest tests/plan-manager/test_replace_thread_cli.py -v`.
  - Steps:
    - [x] Run `tests/plan-manager/test_replace_thread_cli.py` and confirm it passes on the current code (baseline).
    - [x] In `src/i2code/plan/thread_cli.py`, replace the four inline `@click.option` lines on `replace_thread_cmd` (`thread_cli.py:91-94`) with `@_thread_spec_options`, change the signature to `(plan_file, thread, rationale, **kwargs)`, and call `_resolve_tasks_json("replace-thread", kwargs.pop("tasks"), kwargs.pop("tasks_file"))` followed by `_parse_thread("replace-thread", title=kwargs["title"], introduction=kwargs["introduction"], tasks=tasks_json)`.
    - [x] Re-run `tests/plan-manager/test_replace_thread_cli.py` and confirm all tests still pass.
    - [x] Run the full plan-manager test suite (`uv run --python 3.12 python3 -m pytest tests/plan-manager/ -v`) to confirm no regressions in other commands.

---

## Steel Thread 5: `--task-file` on `insert-task-after` (US-2.1)

Introduces the new `--task-file` option for single-task commands. This is the primary user story for single-task file input. Implementation adds a shared helper (`_resolve_task_spec`) so the same logic applies cleanly to `insert-task-before` and `replace-task` in subsequent threads.

- [x] **Task 5.1: `insert-task-after --task-file` inserts a task using JSON from a file**
  - TaskType: OUTCOME
  - Entrypoint: `i2code plan insert-task-after <plan> --thread <t> --after <n> --task-file <path> --rationale <r>`
  - Observable: When `--task-file` points to a JSON object containing all six required fields (`title`, `task_type`, `entrypoint`, `observable`, `evidence`, `steps`), a new task is inserted after task `n` in thread `t`, populated from the file; exit code 0. Mutual-exclusivity errors: providing both `--task-file` and any individual task option exits 1 with stderr `"insert-task-after: --task-file and individual task options are mutually exclusive"`. Providing neither `--task-file` nor all individual options exits 1 with stderr `"insert-task-after: either --task-file or all individual task options are required"`. A `--task-file` JSON missing a required field exits 1 with stderr `"insert-task-after: --task-file JSON is missing required field: <name>"`. An invalid-JSON file exits 1 with stderr `"insert-task-after: --task-file is not valid JSON: <error>"`.
  - Evidence: New pytest tests in `tests/plan-manager/test_insert_task_after_cli.py` cover: (a) successful insert via `--task-file`, (b) mixing `--task-file` with an individual option, (c) providing no options at all, (d) missing required field in JSON, (e) invalid JSON file. Tests pass via `uv run --python 3.12 python3 -m pytest tests/plan-manager/test_insert_task_after_cli.py -v`.
  - Steps:
    - [x] In `tests/plan-manager/test_insert_task_after_cli.py`, add a helper `_invoke_insert_after_with_task_file` that writes a JSON object containing all six fields to `tmp_path / "task.json"` and invokes the command with `--task-file` (and no individual options).
    - [x] Add `test_inserts_using_task_file` asserting the inserted task title and step content appear in the updated plan and exit code is 0.
    - [x] Add `test_error_when_task_file_combined_with_individual_option` that passes both `--task-file` and `--title`, asserting exit 1 and the exact mutual-exclusivity message.
    - [x] Add `test_error_when_no_options_provided` that omits both `--task-file` and all individual options, asserting exit 1 and the "either ... or ..." message.
    - [x] Add `test_error_when_task_file_missing_required_field` that writes JSON omitting `evidence`, asserting exit 1 and the missing-field message naming `evidence`.
    - [x] Add `test_error_when_task_file_invalid_json` that writes `"not-json"` to the file, asserting exit 1 and the "not valid JSON" message.
    - [x] Run the test file and confirm the new tests fail (no `--task-file` yet).
    - [x] In `src/i2code/plan/task_cli.py`, change each option in `_task_spec_options` (`task_cli.py:12-23`) to `required=False, default=None`, and add `click.option("--task-file", default=None, type=click.Path(exists=True), help="Path to JSON file containing a task object")`.
    - [x] In `src/i2code/plan/task_cli.py`, add a new helper `_resolve_task_spec(command_name, **kwargs)` that:
      - exits 1 with the mutual-exclusivity message if `kwargs["task_file"]` is set AND any of `title`/`task_type`/`entrypoint`/`observable`/`evidence`/`steps` is set;
      - exits 1 with the "either ... or ..." message if no `task_file` AND any of the six individual fields is None;
      - when `task_file` is set, reads and parses the JSON object, exits 1 with the invalid-JSON message on `JSONDecodeError`, exits 1 with the missing-required-field message if any of the six keys is absent, and constructs a `Task` via `Task.create(...)` using `TaskMetadata(...)`;
      - when individual fields are set, behaves identically to the existing `_parse_task_spec` (steps JSON parsed with the same `_parse_task_spec` error message).
    - [x] Update `insert_task_after_cmd` (`src/i2code/plan/task_cli.py:121`) to call `_resolve_task_spec("insert-task-after", **kwargs)` instead of `_parse_task_spec(...)`.
    - [x] Re-run the test file and confirm all tests (new and pre-existing) pass.

---

## Steel Thread 6: `--task-file` on `insert-task-before` (US-2.2)

- [x] **Task 6.1: `insert-task-before --task-file` inserts a task using JSON from a file**
  - TaskType: OUTCOME
  - Entrypoint: `i2code plan insert-task-before <plan> --thread <t> --before <n> --task-file <path> --rationale <r>`
  - Observable: With `--task-file` supplying a complete task JSON object, a new task is inserted before task `n` in thread `t`; exit code 0. Mutual-exclusivity, missing-field, and invalid-JSON errors are produced with the prefix `"insert-task-before:"` and the same message bodies as `insert-task-after`.
  - Evidence: New tests in `tests/plan-manager/test_insert_task_before_cli.py` cover the file-based path and the same four error cases. Tests pass via `uv run --python 3.12 python3 -m pytest tests/plan-manager/test_insert_task_before_cli.py -v`.
  - Steps:
    - [x] Mirror the helper and test cases from Steel Thread 5 in `tests/plan-manager/test_insert_task_before_cli.py`, using `before="1"` positioning.
    - [x] Run the test file; confirm the new tests fail.
    - [x] Update `insert_task_before_cmd` (`src/i2code/plan/task_cli.py:105`) to call `_resolve_task_spec("insert-task-before", **kwargs)`.
    - [x] Re-run the test file and confirm all tests pass.

---

## Steel Thread 7: `--task-file` on `replace-task` (US-2.3)

- [x] **Task 7.1: `replace-task --task-file` replaces a task using JSON from a file**
  - TaskType: OUTCOME
  - Entrypoint: `i2code plan replace-task <plan> --thread <t> --task <n> --task-file <path> --rationale <r>`
  - Observable: With `--task-file` supplying a complete task JSON object, task `n` in thread `t` is replaced with the file-defined task and re-set to incomplete; exit code 0. Mutual-exclusivity, missing-field, and invalid-JSON errors are produced with the prefix `"replace-task:"` and the same message bodies as the insert-task commands.
  - Evidence: New tests in `tests/plan-manager/test_replace_task_cli.py` cover the file-based path and the same four error cases. Tests pass via `uv run --python 3.12 python3 -m pytest tests/plan-manager/test_replace_task_cli.py -v`.
  - Steps:
    - [x] Add helper and tests to `tests/plan-manager/test_replace_task_cli.py` mirroring Steel Thread 5's structure, using `task="2"` (the incomplete task in `PLAN_WITH_THREE_TASKS`).
    - [x] Include an assertion that the replaced task is rendered as incomplete (`- [ ] **Task 1.2: ...`).
    - [x] Run the test file; confirm the new tests fail.
    - [x] Update `replace_task_cmd` (`src/i2code/plan/task_cli.py:150`) to call `_resolve_task_spec("replace-task", **kwargs)`.
    - [x] Re-run the test file and confirm all tests pass.

---

## Steel Thread 8: Final consistency check and documentation

Validates the full system end-to-end after all five commands gain file-based input. Updates `README.md` and any CLI help text references if needed.

- [x] **Task 8.1: Full plan-manager test suite and end-to-end script pass; README mentions `--task-file`/`--tasks-file` consistently**
  - TaskType: INFRA
  - Entrypoint: `./test-scripts/test-end-to-end.sh`
  - Observable: `./test-scripts/test-end-to-end.sh` exits 0. `README.md` (if it documents the plan CLI) lists `--tasks-file` for all three thread-creation commands and `--task-file` for all three single-task commands; no stale references remain to "only `replace-thread` supports `--tasks-file`".
  - Evidence: `./test-scripts/test-end-to-end.sh` exits 0; `grep -n "tasks-file\|task-file" README.md` shows consistent coverage of all six commands (or, if `README.md` does not document these commands at all, confirm with `grep -L "i2code plan" README.md`).
  - Steps:
    - [x] Run `./test-scripts/test-end-to-end.sh` from the project root; confirm exit code 0.
    - [x] Check `README.md` for plan-CLI documentation. If `--tasks-file` is documented anywhere, ensure all three thread commands and all three task commands appear with the appropriate file option; otherwise no README change is needed.
    - [x] If any production code was changed in a way that requires CodeScene review, run the `pre_commit_code_health_safeguard` MCP tool on changed files before committing.

---

## Change History
### 2026-05-26 09:50 - mark-task-complete
Existing test suite passes on clean checkout - test-end-to-end.sh exits 0, all plan-manager tests pass

### 2026-05-26 10:15 - mark-task-complete
insert-thread-after --tasks-file works; mutual-exclusivity errors raised; insert-thread-before updated for shared decorator

### 2026-05-26 10:20 - mark-task-complete
insert-thread-before --tasks-file tests added; production already wired via shared decorator

### 2026-05-26 10:35 - mark-task-complete
insert-task-after --task-file works; _resolve_task_spec helper handles file/individual options with mutex, missing-field, and invalid-JSON errors

### 2026-05-26 10:43 - mark-task-complete
insert-task-before --task-file works; uses _resolve_task_spec helper from Steel Thread 5

### 2026-05-26 10:48 - mark-task-complete
replace-task --task-file works via _resolve_task_spec; tests cover file path, mutex, missing-field, and invalid-JSON errors

### 2026-05-26 10:55 - mark-step-complete
test-end-to-end.sh completed with exit code 0; all plan-manager tests, plugin JS tests, integration GH tests, wheel contents test, and marker verification passed.

### 2026-05-26 10:55 - mark-step-complete
No README.md exists at repo root (only README.adoc, which does not mention --tasks-file or --task-file); no README change is needed per task criteria.

### 2026-05-26 10:55 - mark-step-complete
No production code was changed in this task; only ran existing test scripts and verified documentation state.

### 2026-05-26 10:55 - mark-task-complete
End-to-end test suite passes (exit 0). README.md does not exist; README.adoc does not document --tasks-file/--task-file, so no documentation change required. No production code changes were made — task was a verification-only step.
