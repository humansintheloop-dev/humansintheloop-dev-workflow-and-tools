"""Tests for Thread.move_task_before() method."""

import pytest

from i2code.plan_domain.parser import parse


PLAN_TEXT = """\
# Implementation Plan: Test

---

## Steel Thread 1: First Thread
Intro.

- [x] **Task 1.1: First task**
  - TaskType: INFRA
  - Entrypoint: `echo first`
  - Observable: First
  - Evidence: `echo first-done`
  - Steps:
    - [x] Do first

- [ ] **Task 1.2: Second task**
  - TaskType: OUTCOME
  - Entrypoint: `echo second`
  - Observable: Second
  - Evidence: `echo second-done`
  - Steps:
    - [ ] Do second

- [ ] **Task 1.3: Third task**
  - TaskType: OUTCOME
  - Entrypoint: `echo third`
  - Observable: Third
  - Evidence: `echo third-done`
  - Steps:
    - [ ] Do third

---

## Summary
Done."""


class TestThreadMoveTaskBefore:
    """Thread.move_task_before() moves a task before another task."""

    def test_move_last_before_first(self):
        plan = parse(PLAN_TEXT)
        thread = plan.threads[0]
        thread.move_task_before(3, 1)
        assert thread.tasks[0].title == "Third task"
        assert thread.tasks[1].title == "First task"
        assert thread.tasks[2].title == "Second task"

    def test_move_last_before_second(self):
        plan = parse(PLAN_TEXT)
        thread = plan.threads[0]
        thread.move_task_before(3, 2)
        assert thread.tasks[0].title == "First task"
        assert thread.tasks[1].title == "Third task"
        assert thread.tasks[2].title == "Second task"

    def test_preserves_completion_status(self):
        plan = parse(PLAN_TEXT)
        thread = plan.threads[0]
        thread.move_task_before(1, 3)
        assert thread.tasks[1].is_completed is True
        assert thread.tasks[0].is_completed is False

    def test_error_for_same_task(self):
        plan = parse(PLAN_TEXT)
        thread = plan.threads[0]
        with pytest.raises(ValueError, match="same task"):
            thread.move_task_before(2, 2)

    def test_error_for_nonexistent_task(self):
        plan = parse(PLAN_TEXT)
        thread = plan.threads[0]
        with pytest.raises(ValueError, match="task 99 does not exist"):
            thread.move_task_before(99, 1)

    def test_error_for_nonexistent_before_task(self):
        plan = parse(PLAN_TEXT)
        thread = plan.threads[0]
        with pytest.raises(ValueError, match="task 99 does not exist"):
            thread.move_task_before(1, 99)
