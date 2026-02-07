"""Tests for round-trip fidelity: read + write produces identical output."""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'skills', 'plan-file-management', 'scripts'))

from importlib import import_module
_mod = import_module('plan-manager')
fix_numbering = _mod.fix_numbering


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


class TestRoundTrip:
    """fix_numbering on a correctly-numbered plan produces byte-identical output."""

    def test_full_plan_round_trip(self):
        result = fix_numbering(FULL_PLAN)
        assert result == FULL_PLAN

    def test_preserves_blank_lines(self):
        result = fix_numbering(FULL_PLAN)
        # Count blank lines in both
        orig_blanks = FULL_PLAN.count('\n\n')
        result_blanks = result.count('\n\n')
        assert orig_blanks == result_blanks

    def test_preserves_horizontal_rules(self):
        result = fix_numbering(FULL_PLAN)
        assert result.count('---') == FULL_PLAN.count('---')

    def test_preserves_change_history(self):
        result = fix_numbering(FULL_PLAN)
        assert '## Change History' in result
        assert '### 2026-02-01 - Initial plan' in result
        assert '### 2026-02-02 - mark-task-complete' in result

    def test_preserves_completion_status(self):
        result = fix_numbering(FULL_PLAN)
        assert '- [x] **Task 1.1:' in result
        assert '- [ ] **Task 2.2:' in result
        assert '    - [x] Write parser tests' in result
        assert '    - [ ] Write formatter tests' in result
