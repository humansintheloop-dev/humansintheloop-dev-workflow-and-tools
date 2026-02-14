"""Tests for Plan.mark_task_complete() delegation."""

import pytest

from i2code.plan_domain.parser import parse


PLAN_TEXT = """\
# Implementation Plan: Test

---

## Steel Thread 1: First Thread
Intro.

- [ ] **Task 1.1: First task**
  - TaskType: INFRA
  - Entrypoint: `echo hello`
  - Observable: Something
  - Evidence: `echo done`
  - Steps:
    - [ ] Step one

- [ ] **Task 1.2: Second task**
  - TaskType: OUTCOME
  - Entrypoint: `echo hello2`
  - Observable: Something else
  - Evidence: `echo done2`
  - Steps:
    - [ ] Step one

---

## Summary
Done."""


class TestPlanMarkTaskComplete:
    """Plan.mark_task_complete() delegates to Task and validates inputs."""

    def test_marks_task_complete(self):
        plan = parse(PLAN_TEXT)
        plan.mark_task_complete(1, 1)
        assert plan.threads[0].tasks[0].is_completed

    def test_does_not_affect_other_tasks(self):
        plan = parse(PLAN_TEXT)
        plan.mark_task_complete(1, 1)
        assert not plan.threads[0].tasks[1].is_completed

    def test_error_for_nonexistent_thread(self):
        plan = parse(PLAN_TEXT)
        with pytest.raises(ValueError, match="thread 99 does not exist"):
            plan.mark_task_complete(99, 1)

    def test_error_for_nonexistent_task(self):
        plan = parse(PLAN_TEXT)
        with pytest.raises(ValueError, match="task 99 does not exist"):
            plan.mark_task_complete(1, 99)

    def test_error_for_already_complete(self):
        plan = parse(PLAN_TEXT)
        plan.mark_task_complete(1, 1)
        with pytest.raises(ValueError, match="already complete"):
            plan.mark_task_complete(1, 1)
