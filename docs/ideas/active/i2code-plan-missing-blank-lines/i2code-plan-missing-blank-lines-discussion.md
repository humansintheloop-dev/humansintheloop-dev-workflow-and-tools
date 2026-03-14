# Discussion: i2code plan missing blank lines

## Codebase Analysis

### How blank lines are currently handled

The parser (`parser.py`) slices tasks using `_consecutive_ranges` — each task's `_lines` span from its header line to the start of the next task. This means blank lines between tasks in the original file are captured as trailing lines of the *preceding* task.

`Task.create()` produces lines with no leading or trailing blank line.

`Thread.to_lines()` simply concatenates each task's `to_lines()` output with no separator:

```python
for task_num, task in enumerate(self.tasks, 1):
    lines.extend(task.to_lines(thread_number, task_num))
```

### Test results

A test (`tests/plan-domain/test_thread_to_lines_blank_lines.py`) confirms:

- **Round-trip of parsed plans**: PASS (blank lines preserved in raw `_lines`)
- **`replace-task` on task 2**: PASS (blank line is part of task 1's trailing `_lines`)
- **`insert-task-before`**: FAIL (no blank line before newly inserted task)
- **`insert-task-after`**: FAIL (no blank line after newly inserted task)

### Root cause

`Thread.to_lines()` relies on tasks carrying their own inter-task whitespace. Tasks created via `Task.create()` have no such whitespace, so inserted tasks are jammed against their neighbors.

## Classification

**A. User-facing feature** — this is a formatting bug fix. Users see corrupted plan file formatting after using `insert-task-before`, `insert-task-after`, and potentially `replace-task` (when replacing task 1, the blank line before task 2 is lost).

### Rationale

This is not an architecture POC, platform capability, or educational example. It's a bug in existing user-facing functionality where plan file output doesn't match the expected format.

## Questions and Answers

### Q1: Where should the blank-line-between-tasks responsibility live?

Options considered:
- **Thread.to_lines()** — inserts blank line between tasks during serialization
- **Task.create()** — prepends blank line to new task's `_lines`
- **Parser normalization** — strip trailing blanks during parsing, re-add in Thread.to_lines()

**Answer: Thread.to_lines()** — clean separation of concerns. Tasks stay unaware of their position.

### Q2: How to handle double blank lines from parsed tasks?

Parsed tasks carry trailing blank lines from the original file. If Thread.to_lines() also adds a blank line, round-trip output gets double blank lines.

Options considered:
- **Strip in parser** — strip trailing empty lines from each task's `_lines` during parsing
- **Strip in Task.to_lines()** — defensive stripping in Task
- **Strip in Thread.to_lines()** — Thread strips trailing blanks from each task's output

**Answer: Strip in parser** — normalizes internal representation. Thread.to_lines() becomes the single source of inter-task spacing.

### Q3: Should we also fix thread-level spacing?

The same issue likely affects `insert-thread-before`, `insert-thread-after`, `replace-thread` in `Plan.to_text()`.

**Answer: Yes, fix both** — consistent formatting at both task and thread levels.

### Q4: Should we normalize `---` separators between threads too?

Options considered:
- **Normalize `---` too** — strip from parsed threads, emit in Plan.to_text()
- **Blank lines only** — leave `---` embedded in raw lines

**Answer: Normalize `---` too** — Plan.to_text() becomes the single source of truth for all inter-thread formatting.

### Q5: Test strategy order?

Options considered:
- **Round-trip first** — refactor parser + serialization so existing round-trip tests pass, then verify insert/replace tests
- **New tests first** — make insert/replace tests pass first, fix round-trip regressions after

**Answer: Round-trip first** — ensures no regressions before adding new behavior.
