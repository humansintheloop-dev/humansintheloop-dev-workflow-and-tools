"""Tests for Thread.mark_task_complete() method."""

import pytest

from i2code.plan_domain.parser import parse


PLAN_TEXT = """\
# Implementation Plan: Test

---

## Steel Thread 1: First Thread
Intro.

- [ ] **Task 1.1: First task**
  - TaskType: INFRA
  - Entrypoint: `echo first`
  - Observable: First
  - Evidence: `echo first-done`
  - Steps:
    - [ ] Do first

- [ ] **Task 1.2: Second task**
  - TaskType: OUTCOME
  - Entrypoint: `echo second`
  - Observable: Second
  - Evidence: `echo second-done`
  - Steps:
    - [ ] Do second

---

## Summary
Done."""


class TestThreadMarkTaskComplete:
    """Thread.mark_task_complete() validates task and delegates to Task."""

    def test_marks_task_complete(self):
        plan = parse(PLAN_TEXT)
        thread = plan.threads[0]
        thread.mark_task_complete(1)
        assert thread.tasks[0].is_completed

    def test_error_for_nonexistent_task(self):
        plan = parse(PLAN_TEXT)
        thread = plan.threads[0]
        with pytest.raises(ValueError, match="task 99 does not exist"):
            thread.mark_task_complete(99)
