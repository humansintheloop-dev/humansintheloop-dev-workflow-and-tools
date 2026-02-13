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
