"""Tests for move-task-before: moves a task to before another task within the same thread."""

import pytest

from i2code.plan.tasks import move_task_before


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


class TestMoveTaskBefore:
    """move_task_before moves a task to before another task within the same thread."""

    def test_move_last_before_first(self):
        result = move_task_before(PLAN_WITH_THREE_TASKS, 1, 3, 1, "Move task 3 before task 1")
        assert '**Task 1.1: Third task**' in result
        assert '**Task 1.2: First task**' in result
        assert '**Task 1.3: Second task**' in result

    def test_move_last_before_second(self):
        result = move_task_before(PLAN_WITH_THREE_TASKS, 1, 3, 2, "Move task 3 before task 2")
        assert '**Task 1.1: First task**' in result
        assert '**Task 1.2: Third task**' in result
        assert '**Task 1.3: Second task**' in result

    def test_preserves_task_content(self):
        result = move_task_before(PLAN_WITH_THREE_TASKS, 1, 3, 1, "Move")
        # Third task (now 1.1) should have its step
        assert 'Step E' in result
        # First task (now 1.2) should be complete with its steps
        assert '- [x] **Task 1.2: First task**' in result
        assert '    - [x] Step A' in result

    def test_preserves_completion_status(self):
        result = move_task_before(PLAN_WITH_THREE_TASKS, 1, 1, 3, "Move completed task")
        # First task (complete) moved before task 3, so it becomes 1.2
        assert '- [x] **Task 1.2: First task**' in result
        assert '- [ ] **Task 1.1: Second task**' in result

    def test_appends_change_history(self):
        result = move_task_before(PLAN_WITH_THREE_TASKS, 1, 3, 1, "Priority change")
        assert '## Change History' in result
        assert 'move-task-before' in result
        assert 'Priority change' in result

    def test_does_not_affect_other_threads(self):
        result = move_task_before(TWO_THREADS, 1, 2, 1, "Swap in thread 1")
        assert '**Task 1.1: A2**' in result
        assert '**Task 1.2: A1**' in result
        assert '**Task 2.1: B1**' in result

    def test_error_nonexistent_thread(self):
        with pytest.raises(ValueError, match="move-task-before:.*does not exist"):
            move_task_before(PLAN_WITH_THREE_TASKS, 99, 1, 2, "reason")

    def test_error_nonexistent_task(self):
        with pytest.raises(ValueError, match="move-task-before:.*does not exist"):
            move_task_before(PLAN_WITH_THREE_TASKS, 1, 99, 1, "reason")

    def test_error_nonexistent_before_task(self):
        with pytest.raises(ValueError, match="move-task-before:.*does not exist"):
            move_task_before(PLAN_WITH_THREE_TASKS, 1, 1, 99, "reason")

    def test_error_same_task(self):
        with pytest.raises(ValueError, match="move-task-before:.*same task"):
            move_task_before(PLAN_WITH_THREE_TASKS, 1, 2, 2, "reason")
