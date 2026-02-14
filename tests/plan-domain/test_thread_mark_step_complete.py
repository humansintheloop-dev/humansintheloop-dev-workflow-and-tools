"""Tests for Thread.mark_step_complete() method."""

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
    - [ ] Do second

---

## Summary
Done."""


class TestThreadMarkStepComplete:
    """Thread.mark_step_complete() validates task and delegates to Task."""

    def test_marks_step_complete(self):
        plan = parse(PLAN_TEXT)
        thread = plan.threads[0]
        thread.mark_step_complete(1, 1)
        assert thread.tasks[0].steps[0]['completed']

    def test_error_for_nonexistent_task(self):
        plan = parse(PLAN_TEXT)
        thread = plan.threads[0]
        with pytest.raises(ValueError, match="task 99 does not exist"):
            thread.mark_step_complete(99, 1)

    def test_error_for_nonexistent_step(self):
        plan = parse(PLAN_TEXT)
        thread = plan.threads[0]
        with pytest.raises(ValueError, match="step 99 does not exist"):
            thread.mark_step_complete(1, 99)
