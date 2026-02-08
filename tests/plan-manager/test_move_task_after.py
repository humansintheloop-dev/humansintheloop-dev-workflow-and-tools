"""Tests for move-task-after: moves a task to after another task within the same thread."""

import pytest

from i2c.plan.tasks import move_task_after


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


class TestMoveTaskAfter:
    """move_task_after moves a task to after another task within the same thread."""

    def test_move_first_after_last(self):
        result = move_task_after(PLAN_WITH_THREE_TASKS, 1, 1, 3, "Move task 1 after task 3")
        assert '**Task 1.1: Second task**' in result
        assert '**Task 1.2: Third task**' in result
        assert '**Task 1.3: First task**' in result

    def test_move_first_after_second(self):
        result = move_task_after(PLAN_WITH_THREE_TASKS, 1, 1, 2, "Move task 1 after task 2")
        assert '**Task 1.1: Second task**' in result
        assert '**Task 1.2: First task**' in result
        assert '**Task 1.3: Third task**' in result

    def test_preserves_task_content(self):
        result = move_task_after(PLAN_WITH_THREE_TASKS, 1, 1, 3, "Move")
        # First task (now 1.3) should be complete with its steps
        assert '- [x] **Task 1.3: First task**' in result
        assert '    - [x] Step A' in result
        assert '    - [x] Step B' in result

    def test_appends_change_history(self):
        result = move_task_after(PLAN_WITH_THREE_TASKS, 1, 1, 3, "Deferred task")
        assert '## Change History' in result
        assert 'move-task-after' in result
        assert 'Deferred task' in result

    def test_does_not_affect_other_threads(self):
        result = move_task_after(TWO_THREADS, 1, 1, 2, "Swap in thread 1")
        assert '**Task 1.1: A2**' in result
        assert '**Task 1.2: A1**' in result
        assert '**Task 2.1: B1**' in result

    def test_error_nonexistent_thread(self):
        with pytest.raises(ValueError, match="move-task-after:.*does not exist"):
            move_task_after(PLAN_WITH_THREE_TASKS, 99, 1, 2, "reason")

    def test_error_nonexistent_task(self):
        with pytest.raises(ValueError, match="move-task-after:.*does not exist"):
            move_task_after(PLAN_WITH_THREE_TASKS, 1, 99, 1, "reason")

    def test_error_nonexistent_after_task(self):
        with pytest.raises(ValueError, match="move-task-after:.*does not exist"):
            move_task_after(PLAN_WITH_THREE_TASKS, 1, 1, 99, "reason")

    def test_error_same_task(self):
        with pytest.raises(ValueError, match="move-task-after:.*same task"):
            move_task_after(PLAN_WITH_THREE_TASKS, 1, 2, 2, "reason")
