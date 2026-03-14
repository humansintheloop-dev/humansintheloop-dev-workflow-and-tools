The sandbox restricts access to the project root. I have sufficient context from the idea and spec files to generate the plan. The spec clearly describes a formatting bug fix in the plan domain parser/serializer — no design pattern catalog entry is likely to apply to this narrow fix. Let me proceed with the plan generation.

Based on the idea and spec, here is the plan:

---

# Implementation Plan: Normalize Blank Lines and Separators in Plan File Output

## Idea Type

**A. User-facing feature** (bug fix)

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

## Steel Thread 1: Parser Strips Trailing Whitespace and Serializers Emit Separators

This steel thread fixes the core bug: the parser currently stores inter-element spacing as trailing content in each element's `_lines`, but `Task.create()` and `Thread.create()` don't add this spacing. The fix normalizes responsibility — the parser strips trailing whitespace, and the serializers (`Thread.to_lines()`, `Plan.to_text()`) emit separators explicitly.

- [x] **Task 1.1: Parser strips trailing blank lines from task `_lines`**
  - TaskType: OUTCOME
  - Entrypoint: `pytest tests/plan-domain/`
  - Observable: When a plan is parsed, each `Task` object's `_lines` list contains no trailing empty-string elements. The existing test `tests/plan-domain/test_thread_to_lines_blank_lines.py` assertions about blank lines between tasks begin to be addressed.
  - Evidence: `pytest tests/plan-domain/` passes — specifically, a new test in `tests/plan-domain/test_parser_strips_trailing_blanks.py` parses a plan with blank lines between tasks and asserts that each task's `_lines` list does not end with `''`
  - Steps:
    - [x] Write a test in `tests/plan-domain/test_parser_strips_trailing_blanks.py` that parses a plan with two tasks separated by a blank line and asserts the first task's `_lines` does not end with `''`
    - [x] Modify `src/i2code/plan_domain/parser.py` — in `_parse_thread`, after slicing `_lines` for each task, strip trailing empty lines (lines that are `''` or whitespace-only)
    - [x] Run `pytest tests/plan-domain/` and verify the new test passes and existing tests still pass (some round-trip tests may now need adjustment — defer that to Task 1.3)

- [ ] **Task 1.2: `Thread.to_lines()` emits a blank line between consecutive tasks**
  - TaskType: OUTCOME
  - Entrypoint: `pytest tests/plan-domain/test_thread_to_lines_blank_lines.py`
  - Observable: `insert-task-before` and `insert-task-after` produce output with a blank line between all tasks. The 2 currently-failing tests in `tests/plan-domain/test_thread_to_lines_blank_lines.py` now pass.
  - Evidence: `pytest tests/plan-domain/test_thread_to_lines_blank_lines.py` — all 4 tests pass (previously 2 failed)
  - Steps:
    - [ ] Modify `src/i2code/plan_domain/thread.py` — in `Thread.to_lines()`, insert `lines.append('')` before each task except the first
    - [ ] Run `pytest tests/plan-domain/test_thread_to_lines_blank_lines.py` and verify all 4 tests pass

- [ ] **Task 1.3: Round-trip tests pass after parser and serializer changes**
  - TaskType: OUTCOME
  - Entrypoint: `pytest tests/plan-domain/test_parse_write_round_trip.py`
  - Observable: Parsing a standard plan file and serializing it back produces identical output. Round-trip equivalence is maintained.
  - Evidence: `pytest tests/plan-domain/test_parse_write_round_trip.py` — all tests pass
  - Steps:
    - [ ] Run `pytest tests/plan-domain/test_parse_write_round_trip.py` and identify any failures caused by the parser/serializer changes from Tasks 1.1 and 1.2
    - [ ] Fix any round-trip test failures — the parser now strips trailing blanks from tasks, and `Thread.to_lines()` now adds them back, so round-trip should be preserved for well-formatted plans
    - [ ] If the `test_no_separator_lines` test exists and expects threads without `---` separators to round-trip without `---`, update it to expect `---` separators in output (per FR4/FR5 in the spec)
    - [ ] Run full `pytest tests/plan-domain/` and verify all tests pass

---

## Steel Thread 2: Plan-Level Thread Separator Normalization

This thread addresses thread-level spacing: `---` separators between threads and before the postamble.

- [ ] **Task 2.1: Parser strips trailing `---` and blank lines from thread lines**
  - TaskType: OUTCOME
  - Entrypoint: `pytest tests/plan-domain/`
  - Observable: When a plan with multiple threads separated by `---` is parsed, each `Thread` object's lines (including `_header_lines` and the last task's `_lines`) contain no trailing `---` or blank lines that serve as inter-thread spacing.
  - Evidence: `pytest tests/plan-domain/` passes — specifically, a new test in `tests/plan-domain/test_parser_strips_thread_separators.py` parses a multi-thread plan and asserts that each thread's raw lines do not end with `---` or `''`
  - Steps:
    - [ ] Write a test in `tests/plan-domain/test_parser_strips_thread_separators.py` that parses a plan with two threads separated by `\n---\n` and asserts the first thread's lines do not end with `''` or `---`
    - [ ] Modify `src/i2code/plan_domain/parser.py` — when constructing `Thread` objects, strip trailing lines that are `---` or empty from the thread's raw line slice before assigning to `_header_lines` and tasks

- [ ] **Task 2.2: `Plan.to_text()` emits `---` separators between threads**
  - TaskType: OUTCOME
  - Entrypoint: `pytest tests/plan-domain/`
  - Observable: `insert-thread-before`, `insert-thread-after`, and `replace-thread` produce plan output with `---` separators between all threads. Serializing a multi-thread plan always includes `\n---\n` between consecutive threads.
  - Evidence: `pytest tests/plan-domain/` passes — a new test in `tests/plan-domain/test_plan_to_text_thread_separators.py` parses a multi-thread plan, inserts a thread, serializes, and verifies `---` separators appear between all threads
  - Steps:
    - [ ] Write a test in `tests/plan-domain/test_plan_to_text_thread_separators.py` that: (a) parses a plan with 2 threads, inserts a new thread before thread 1, serializes, and asserts `---` separators between all 3 threads; (b) parses a plan with 2 threads, serializes without modifications, and asserts round-trip equivalence
    - [ ] Modify `src/i2code/plan_domain/plan.py` — in `Plan.to_text()`, emit `['', '---', '']` before each thread except the first

- [ ] **Task 2.3: `Plan.to_text()` emits separator before postamble**
  - TaskType: OUTCOME
  - Entrypoint: `pytest tests/plan-domain/`
  - Observable: When a plan has a postamble, serialization emits `\n---\n` between the last thread and the postamble.
  - Evidence: `pytest tests/plan-domain/` passes — a new test in `tests/plan-domain/test_plan_to_text_thread_separators.py` (or the same file from Task 2.2) parses a plan with a postamble, serializes, and verifies the `---` separator appears before the postamble
  - Steps:
    - [ ] Add a test that parses a plan with threads and a postamble, serializes it, and asserts `---` and blank lines appear between the last thread and the postamble
    - [ ] Modify `src/i2code/plan_domain/plan.py` — in `Plan.to_text()`, emit `['', '---', '']` before the postamble when it exists
    - [ ] Verify the parser also strips trailing `---`/blank lines from the postamble's leading edge (the parser change from Task 2.1 should handle this, but verify)

- [ ] **Task 2.4: Full round-trip and integration verification**
  - TaskType: OUTCOME
  - Entrypoint: `pytest tests/plan-domain/`
  - Observable: All tests in `tests/plan-domain/` pass, including round-trip tests, blank-line tests, and the new separator tests. The `replace-task` scenario also produces correct spacing.
  - Evidence: `pytest tests/plan-domain/` — all tests pass with exit code 0
  - Steps:
    - [ ] Add a test for the `replace-task` scenario: parse a plan with 2 tasks, replace task 2, serialize, verify blank line between task 1 and the replacement task
    - [ ] Run `pytest tests/plan-domain/` and fix any remaining failures
    - [ ] Verify all 4 scenarios from the spec are covered by tests: (1) insert task and verify spacing, (2) replace task and verify spacing, (3) insert thread and verify separators, (4) round-trip with no modifications

---

## Change History
### 2026-03-14 11:45 - mark-step-complete
Test written in test_parser_strips_trailing_blanks.py

### 2026-03-14 11:45 - mark-step-complete
Added _strip_trailing_blank_lines in parser.py _parse_thread

### 2026-03-14 11:45 - mark-step-complete
New test passes, 6 round-trip failures deferred to Task 1.3 as planned

### 2026-03-14 11:45 - mark-task-complete
Parser strips trailing blank lines; new test passes; round-trip test fixes deferred to Task 1.3
