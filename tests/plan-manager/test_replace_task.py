"""Tests for replace-task: replaces a task in place within a thread."""

import sys
import os
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'skills', 'plan-file-management', 'scripts'))

from importlib import import_module
_mod = import_module('plan-manager')
replace_task = _mod.replace_task


PLAN_WITH_THREE_TASKS = """\
# Implementation Plan: Test Plan

## Idea Type
**A. Feature** - A test feature

---

## Overview
Test plan.

---

## Steel Thread 1: Setup
Intro to setup.

- [x] **Task 1.1: First task**
  - TaskType: INFRA
  - Entrypoint: `echo first`
  - Observable: First done
  - Evidence: `echo first`
  - Steps:
    - [x] Step A
    - [x] Step B

- [ ] **Task 1.2: Second task**
  - TaskType: OUTCOME
  - Entrypoint: `echo second`
  - Observable: Second done
  - Evidence: `echo second`
  - Steps:
    - [ ] Step C
    - [ ] Step D

- [ ] **Task 1.3: Third task**
  - TaskType: OUTCOME
  - Entrypoint: `echo third`
  - Observable: Third done
  - Evidence: `echo third`
  - Steps:
    - [ ] Step E

---

## Summary
Done.
"""

TWO_THREADS = """\
# Implementation Plan: Test Plan

## Idea Type
**A. Feature** - A test feature

---

## Overview
Test plan.

---

## Steel Thread 1: Alpha
Alpha intro.

- [ ] **Task 1.1: A1**
  - TaskType: INFRA
  - Entrypoint: `echo a1`
  - Observable: A1
  - Evidence: `echo a1`
  - Steps:
    - [ ] Do A1

- [ ] **Task 1.2: A2**
  - TaskType: INFRA
  - Entrypoint: `echo a2`
  - Observable: A2
  - Evidence: `echo a2`
  - Steps:
    - [ ] Do A2

---

## Steel Thread 2: Beta
Beta intro.

- [ ] **Task 2.1: B1**
  - TaskType: OUTCOME
  - Entrypoint: `echo b1`
  - Observable: B1
  - Evidence: `echo b1`
  - Steps:
    - [ ] Do B1

---

## Summary
Done.
"""


class TestReplaceTask:
    """replace_task replaces a task's content in place within a thread."""

    def test_replaces_task_content(self):
        result = replace_task(
            PLAN_WITH_THREE_TASKS, 1, 2,
            "Replaced task", "INFRA", "echo replaced", "Replaced done",
            "echo replaced", ["New step 1", "New step 2"], "Replaced second task"
        )
        assert '**Task 1.2: Replaced task**' in result
        assert 'TaskType: INFRA' in result
        assert '`echo replaced`' in result
        assert 'New step 1' in result
        assert 'New step 2' in result

    def test_preserves_other_tasks(self):
        result = replace_task(
            PLAN_WITH_THREE_TASKS, 1, 2,
            "Replaced", "INFRA", "e", "o", "v", ["s"], "reason"
        )
        assert '**Task 1.1: First task**' in result
        assert '**Task 1.3: Third task**' in result

    def test_replaced_task_is_incomplete(self):
        result = replace_task(
            PLAN_WITH_THREE_TASKS, 1, 1,
            "New first", "OUTCOME", "e", "o", "v", ["s"], "reason"
        )
        # Even though task 1.1 was complete, replaced task is new and incomplete
        assert '- [ ] **Task 1.1: New first**' in result

    def test_preserves_numbering(self):
        result = replace_task(
            PLAN_WITH_THREE_TASKS, 1, 2,
            "Replaced", "INFRA", "e", "o", "v", ["s"], "reason"
        )
        assert '**Task 1.1: First task**' in result
        assert '**Task 1.2: Replaced**' in result
        assert '**Task 1.3: Third task**' in result

    def test_appends_change_history(self):
        result = replace_task(
            PLAN_WITH_THREE_TASKS, 1, 2,
            "Replaced", "INFRA", "e", "o", "v", ["s"], "Rewritten for clarity"
        )
        assert '## Change History' in result
        assert 'replace-task' in result
        assert 'Rewritten for clarity' in result

    def test_does_not_affect_other_threads(self):
        result = replace_task(
            TWO_THREADS, 1, 1,
            "Replaced A1", "INFRA", "e", "o", "v", ["s"], "reason"
        )
        assert '**Task 1.1: Replaced A1**' in result
        assert '**Task 1.2: A2**' in result
        assert '**Task 2.1: B1**' in result

    def test_error_nonexistent_thread(self):
        with pytest.raises(ValueError, match="replace-task:.*does not exist"):
            replace_task(PLAN_WITH_THREE_TASKS, 99, 1, "t", "INFRA", "e", "o", "v", ["s"], "r")

    def test_error_nonexistent_task(self):
        with pytest.raises(ValueError, match="replace-task:.*does not exist"):
            replace_task(PLAN_WITH_THREE_TASKS, 1, 99, "t", "INFRA", "e", "o", "v", ["s"], "r")
