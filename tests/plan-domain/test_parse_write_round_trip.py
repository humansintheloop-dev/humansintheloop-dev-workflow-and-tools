"""Parse a plan string into domain objects, write it back, and verify identity."""

from i2code.plan_domain.parser import parse
from i2code.plan_domain.plan import Plan


FULL_PLAN = """\
# Implementation Plan: Complete Test Plan

## Idea Type
**C. Platform/infrastructure capability** - A comprehensive test plan

---

## Instructions for Coding Agent

- IMPORTANT: Use simple commands.

### Required Skills

| Skill | When to Use |
|-------|-------------|
| `skill-a` | Always |

---

## Overview
This plan covers a complete feature with multiple threads, mixed completion status, and change history.

---

## Steel Thread 1: Setup
Set up the infrastructure for the project.

- [x] **Task 1.1: Create project structure**
  - TaskType: INFRA
  - Entrypoint: `echo setup`
  - Observable: Project exists
  - Evidence: `ls project/`
  - Steps:
    - [x] Create directory
    - [x] Add config file

- [x] **Task 1.2: Add CI pipeline**
  - TaskType: INFRA
  - Entrypoint: `echo ci`
  - Observable: CI runs
  - Evidence: `gh run list`
  - Steps:
    - [x] Create workflow file
    - [x] Test locally

---

## Steel Thread 2: Core Feature
Implement the core feature with multiple tasks.

- [x] **Task 2.1: Implement parser**
  - TaskType: OUTCOME
  - Entrypoint: `echo parse`
  - Observable: Parser works
  - Evidence: `pytest tests/parser/`
  - Steps:
    - [x] Write parser tests
    - [x] Implement parser

- [ ] **Task 2.2: Implement formatter**
  - TaskType: OUTCOME
  - Entrypoint: `echo format`
  - Observable: Formatter works
  - Evidence: `pytest tests/formatter/`
  - Steps:
    - [ ] Write formatter tests
    - [x] Implement basic formatter
    - [ ] Add edge cases

---

## Steel Thread 3: Documentation
Write comprehensive documentation.

- [ ] **Task 3.1: Write README**
  - TaskType: OUTCOME
  - Entrypoint: `echo docs`
  - Observable: README exists
  - Evidence: `cat README.md`
  - Steps:
    - [ ] Write introduction
    - [ ] Add usage examples
    - [ ] Add API reference

---

## Summary
This plan covers 3 threads with 5 tasks total.

---

## Change History
### 2026-02-01 - Initial plan
Created the initial implementation plan.

### 2026-02-02 - mark-task-complete
Completed task 1.1 and 1.2.
"""


PLAN_WITH_UNKNOWN_TRAILING_SECTION = """\
# Implementation Plan: Test Plan

## Overview
A simple plan.

---

## Steel Thread 1: Setup
Set up the project.

- [ ] **Task 1.1: Create structure**
  - TaskType: INFRA
  - Entrypoint: `echo setup`
  - Observable: Project exists
  - Evidence: `ls project/`
  - Steps:
    - [ ] Create directory

---

## Notes
These are extra notes that should be in the postamble.
"""


class TestParseAndWrite:

    def test_round_trip_produces_identical_output(self):
        plan = parse(FULL_PLAN)
        assert isinstance(plan, Plan)
        result = plan.to_text()
        assert result == FULL_PLAN

    def test_unknown_trailing_section_round_trips(self):
        plan = parse(PLAN_WITH_UNKNOWN_TRAILING_SECTION)
        result = plan.to_text()
        assert result == PLAN_WITH_UNKNOWN_TRAILING_SECTION

    def test_unknown_trailing_section_is_in_postamble(self):
        plan = parse(PLAN_WITH_UNKNOWN_TRAILING_SECTION)
        postamble = '\n'.join(plan._postamble_lines)
        assert '## Notes' in postamble

    def test_full_plan_structure(self):
        plan = parse(FULL_PLAN)
        assert len(plan.threads) == 3
        assert [len(t.tasks) for t in plan.threads] == [2, 2, 1]
        postamble = '\n'.join(plan._postamble_lines)
        assert '## Summary' in postamble
        assert '## Change History' in postamble

    def test_unknown_trailing_section_structure(self):
        plan = parse(PLAN_WITH_UNKNOWN_TRAILING_SECTION)
        assert len(plan.threads) == 1
        assert len(plan.threads[0].tasks) == 1
        postamble = '\n'.join(plan._postamble_lines)
        assert '## Notes' in postamble


PREAMBLE_ONLY = """\
# Implementation Plan: Preamble Only

## Overview
This plan has no steel threads yet.

## Instructions
Just some notes.
"""


THREAD_NO_TASKS = """\
# Implementation Plan: Thread No Tasks

## Overview
A plan with a thread but no tasks.

---

## Steel Thread 1: Planning
This thread has intro text but no task lines yet.

---

## Summary
Nothing done yet.
"""


class TestEdgeCases:

    def test_no_threads(self):
        plan = parse(PREAMBLE_ONLY)
        assert len(plan.threads) == 0
        assert plan._postamble_lines == []
        assert plan.to_text() == PREAMBLE_ONLY

    def test_thread_with_no_tasks(self):
        plan = parse(THREAD_NO_TASKS)
        assert len(plan.threads) == 1
        assert len(plan.threads[0].tasks) == 0
        header = '\n'.join(plan.threads[0]._header_lines)
        assert 'Steel Thread 1: Planning' in header
        assert plan.to_text() == THREAD_NO_TASKS

    def test_no_postamble(self):
        text = """\
# Implementation Plan: No Postamble

---

## Steel Thread 1: Work
Do the work.

- [ ] **Task 1.1: Do something**
  - Steps:
    - [ ] Step one
"""
        plan = parse(text)
        assert len(plan.threads) == 1
        assert len(plan.threads[0].tasks) == 1
        assert plan._postamble_lines == []
        assert plan.to_text() == text

    def test_misnumbered_input_renumbers(self):
        text = """\
# Plan

---

## Steel Thread 5: Only Thread

- [ ] **Task 5.3: First task**
  - Steps:
    - [ ] Do it

- [ ] **Task 5.7: Second task**
  - Steps:
    - [ ] Do it too
"""
        plan = parse(text)
        assert len(plan.threads) == 1
        assert len(plan.threads[0].tasks) == 2
        output = plan.to_text()
        assert '## Steel Thread 1: Only Thread' in output
        assert '**Task 1.1: First task**' in output
        assert '**Task 1.2: Second task**' in output

    def test_single_thread_single_task(self):
        text = """\
# Minimal Plan

## Steel Thread 1: Only

- [ ] **Task 1.1: Only task**
  - Steps:
    - [ ] Do it
"""
        plan = parse(text)
        assert len(plan.threads) == 1
        assert len(plan.threads[0].tasks) == 1
        assert plan._preamble_lines == ['# Minimal Plan', '']
        assert plan._postamble_lines == []
        assert plan.to_text() == text

    def test_no_separator_lines(self):
        text = """\
# Plan Without Separators

## Steel Thread 1: First
First thread intro.

- [ ] **Task 1.1: Task A**
  - Steps:
    - [ ] Step

## Steel Thread 2: Second
Second thread intro.

- [ ] **Task 2.1: Task B**
  - Steps:
    - [ ] Step

## Summary
All done.
"""
        plan = parse(text)
        assert len(plan.threads) == 2
        assert len(plan.threads[0].tasks) == 1
        assert len(plan.threads[1].tasks) == 1
        postamble = '\n'.join(plan._postamble_lines)
        assert '## Summary' in postamble
        assert plan.to_text() == text

    def test_change_history_without_summary(self):
        text = """\
# Plan

---

## Steel Thread 1: Work

- [ ] **Task 1.1: Do it**
  - Steps:
    - [ ] Step

---

## Change History
### 2026-02-01 - Initial plan
Created the plan.
"""
        plan = parse(text)
        assert len(plan.threads) == 1
        assert len(plan.threads[0].tasks) == 1
        postamble = '\n'.join(plan._postamble_lines)
        assert '## Change History' in postamble
        assert '## Summary' not in postamble
        assert plan.to_text() == text
