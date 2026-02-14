"""Tests for Thread.move_task_after() method."""

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


class TestThreadMoveTaskAfter:
    """Thread.move_task_after() moves a task after another task."""

    def test_move_first_after_last(self):
        plan = parse(PLAN_TEXT)
        thread = plan.threads[0]
        thread.move_task_after(1, 3)
        assert thread.tasks[0].title == "Second task"
        assert thread.tasks[1].title == "Third task"
        assert thread.tasks[2].title == "First task"

    def test_move_first_after_second(self):
        plan = parse(PLAN_TEXT)
        thread = plan.threads[0]
        thread.move_task_after(1, 2)
        assert thread.tasks[0].title == "Second task"
        assert thread.tasks[1].title == "First task"
        assert thread.tasks[2].title == "Third task"

    def test_preserves_completion_status(self):
        plan = parse(PLAN_TEXT)
        thread = plan.threads[0]
        thread.move_task_after(1, 3)
        assert thread.tasks[2].is_completed is True
        assert thread.tasks[0].is_completed is False

    def test_error_for_same_task(self):
        plan = parse(PLAN_TEXT)
        thread = plan.threads[0]
        with pytest.raises(ValueError, match="same task"):
            thread.move_task_after(2, 2)

    def test_error_for_nonexistent_task(self):
        plan = parse(PLAN_TEXT)
        thread = plan.threads[0]
        with pytest.raises(ValueError, match="task 99 does not exist"):
            thread.move_task_after(99, 1)

    def test_error_for_nonexistent_after_task(self):
        plan = parse(PLAN_TEXT)
        thread = plan.threads[0]
        with pytest.raises(ValueError, match="task 99 does not exist"):
            thread.move_task_after(1, 99)
