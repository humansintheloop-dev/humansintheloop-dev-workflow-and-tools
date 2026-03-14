# Specification: Normalize Blank Lines and Separators in Plan File Output

## Purpose and Background

The `i2code plan` CLI manages plan files — markdown documents containing steel threads with numbered tasks. Subcommands like `insert-task-before`, `insert-task-after`, `replace-task`, and their thread-level equivalents modify the plan's domain model, which is then serialized back to markdown.

Currently, inter-element spacing (blank lines between tasks, `---` separators between threads) is stored as raw trailing lines within each element's `_lines` list. This works for parsed plans (round-trip preserves formatting), but breaks when new elements are created via `Task.create()` or `Thread.create()` — these produce lines without trailing whitespace, causing output where consecutive elements are jammed together.

## Target Users

- **Claude (coding agent)**: the primary consumer of `i2code plan` subcommands, invoked via the `plan-tracking` and `plan-file-management` skills during implementation workflows.

## Problem Statement

After running `insert-task-before`, `insert-task-after`, or `replace-task`, the resulting plan file has no blank line between the newly created task and its neighbors. The same issue affects thread-level operations and `---` separators.

### Confirmed by test

`tests/plan-domain/test_thread_to_lines_blank_lines.py` demonstrates:
- `insert-task-before`: FAIL — no blank line before inserted task
- `insert-task-after`: FAIL — no blank line after inserted task

## Goals

1. All `i2code plan` subcommands produce plan files with consistent inter-element spacing.
2. Existing round-trip tests continue to pass — parsing and serializing a plan produces identical output.
3. Formatting responsibility is centralized in the serialization layer, not scattered across entities or the parser.

## In Scope

- Normalizing blank lines between tasks within a thread
- Normalizing `---` and blank lines between threads within a plan
- Stripping trailing blank lines and `---` separators from parsed element `_lines` in the parser
- Updating `Thread.to_lines()` to emit blank lines between tasks
- Updating `Plan.to_text()` to emit `---` separators between threads
- Updating existing round-trip tests if the normalized output differs from the input (e.g., plans without `---` separators)

## Out of Scope

- Changing the plan file format itself (headings, task structure, metadata fields)
- Modifying CLI argument parsing or command signatures
- Adding new subcommands
- Changing preamble or postamble formatting

## Functional Requirements

### FR1: Parser strips trailing whitespace from task lines

When `_parse_thread` constructs `Task` objects, it must strip trailing empty lines from each task's `_lines` slice.

**Before** (current behavior): Task 1's `_lines` for a plan with two tasks separated by a blank line:
```
['- [ ] **Task 1.1: First**', '  - Steps:', '    - [ ] Step one', '']
```

**After**: Task 1's `_lines`:
```
['- [ ] **Task 1.1: First**', '  - Steps:', '    - [ ] Step one']
```

### FR2: Parser strips trailing whitespace and `---` from thread lines

When the parser constructs `Thread` objects, the thread's lines (including `_header_lines` and the final task's `_lines`) must not include trailing blank lines or `---` separators that serve as inter-thread spacing.

Specifically, the parser must strip trailing lines from the raw thread slice that match `---` or are empty, before those lines are assigned to `_header_lines` or the last task.

### FR3: Thread.to_lines() emits blank lines between tasks

`Thread.to_lines()` must insert a single blank line (`''`) before each task except the first:

```python
for task_num, task in enumerate(self.tasks, 1):
    if task_num > 1:
        lines.append('')
    lines.extend(task.to_lines(thread_number, task_num))
```

### FR4: Plan.to_text() emits separators between threads

`Plan.to_text()` must insert a separator (`['', '---', '']`) before each thread except the first. This matches the existing format where threads are separated by a blank line, `---`, and another blank line.

```python
for thread_num, thread in enumerate(self.threads, 1):
    if thread_num > 1:
        lines.extend(['', '---', ''])
    lines.extend(thread.to_lines(thread_num))
```

### FR5: Plan.to_text() emits separator before postamble

When a postamble exists, `Plan.to_text()` must emit `['', '---', '']` between the last thread and the postamble. Currently this separator is captured as trailing lines of the last thread or leading lines of the postamble — after normalization, `to_text()` must emit it explicitly.

### FR6: Round-trip equivalence

For any plan file that uses the standard format (blank lines between tasks, `---` between threads), `parse(text).to_text()` must produce output identical to `text`.

## Non-Functional Requirements

### NFR1: No behavioral changes

This is a formatting-only fix. No domain logic (task completion, reordering, validation) changes.

### NFR2: Backward compatibility

Plan files written by the updated code must be parseable by the updated parser, and vice versa.

## Security Requirements

Not applicable — this is an internal formatting fix with no authentication, authorization, or external-facing operations.

## Success Metrics

1. All existing tests in `tests/plan-domain/` pass.
2. `tests/plan-domain/test_thread_to_lines_blank_lines.py` — all 4 tests pass (currently 2 fail).
3. Plan files modified by `insert-task-before`, `insert-task-after`, `replace-task`, and their thread-level equivalents have consistent blank-line spacing.

## Epics and User Stories

### Epic 1: Normalize parser output

**US1.1**: As the plan serializer, I need parsed tasks to have no trailing blank lines so that `Thread.to_lines()` can be the single source of inter-task spacing.

**US1.2**: As the plan serializer, I need parsed threads to have no trailing `---` or blank lines so that `Plan.to_text()` can be the single source of inter-thread separators.

### Epic 2: Centralize formatting in serialization

**US2.1**: As a user of `insert-task-before`, I need a blank line between the inserted task and its neighbors so the plan file is readable.

**US2.2**: As a user of `insert-thread-before`, I need a `---` separator between the inserted thread and its neighbors so the plan file matches the standard format.

## Scenarios

### Scenario 1 (Primary): Insert task and verify spacing

1. Parse a plan file with 2 tasks in thread 1, separated by a blank line.
2. Insert a new task before task 1.
3. Serialize the plan.
4. Verify the output has blank lines between all 3 tasks.

### Scenario 2: Replace task and verify spacing

1. Parse a plan file with 2 tasks in thread 1.
2. Replace task 2 with a new task.
3. Serialize the plan.
4. Verify the output has a blank line between task 1 and the replaced task 2.

### Scenario 3: Insert thread and verify separators

1. Parse a plan file with 2 threads separated by `---`.
2. Insert a new thread before thread 1.
3. Serialize the plan.
4. Verify the output has `---` separators between all 3 threads.

### Scenario 4: Round-trip with no modifications

1. Parse a standard plan file (with blank lines and `---` separators).
2. Serialize without modifications.
3. Verify output is identical to input.

### Scenario 5: Round-trip plan without `---` separators

1. Parse a plan file where threads are separated by blank lines only (no `---`).
2. Serialize without modifications.
3. Verify the output format. Note: after normalization, `Plan.to_text()` will emit `---` separators between threads. This means plans originally lacking `---` will gain them on round-trip. The existing `test_no_separator_lines` test will need updating to reflect this.
