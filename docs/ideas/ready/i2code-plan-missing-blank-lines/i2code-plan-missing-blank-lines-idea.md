# i2code plan: Missing Blank Lines Between Tasks

## Problem

The `i2code plan` subcommands `insert-task-before`, `insert-task-after`, and `replace-task` do not emit a blank line between tasks when writing to the plan file. The same issue affects thread-level operations (`insert-thread-before`, `insert-thread-after`, `replace-thread`) and `---` separators between threads.

This produces inconsistent formatting — tasks and threads modified by these commands are visually jammed together, while unmodified ones have proper spacing.

### Root Cause

The parser captures inter-element whitespace (blank lines, `---` separators) as trailing content of the preceding element's raw `_lines`. `Task.create()` and `Thread.create()` produce lines without this whitespace. `Thread.to_lines()` and `Plan.to_text()` concatenate elements with no separators, relying on elements to carry their own spacing.

## Goal

Normalize formatting responsibility:

1. The parser strips trailing blank lines from each task's `_lines` and trailing blank lines / `---` separators from each thread's lines.
2. `Thread.to_lines()` emits a blank line between consecutive tasks.
3. `Plan.to_text()` emits `---` and blank line separators between consecutive threads.

All `i2code plan` subcommands that modify tasks or threads produce output with consistent spacing, matching the original plan generation format.

## Locations

- **Parser** — `src/i2code/plan_domain/parser.py` (`_parse_thread`)
- **Thread serialization** — `src/i2code/plan_domain/thread.py` (`Thread.to_lines`)
- **Plan serialization** — `src/i2code/plan_domain/plan.py` (`Plan.to_text`)
- **Test demonstrating the bug** — `tests/plan-domain/test_thread_to_lines_blank_lines.py`
- **Existing round-trip tests** — `tests/plan-domain/test_parse_write_round_trip.py`

## Classification

**A. User-facing feature** (bug fix)
