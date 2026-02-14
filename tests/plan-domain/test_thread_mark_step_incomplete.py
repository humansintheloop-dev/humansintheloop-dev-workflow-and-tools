"""Tests for Thread.mark_step_incomplete() method."""

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
    - [x] Do first
    - [x] Do second

---

## Summary
Done."""


class TestThreadMarkStepIncomplete:
    """Thread.mark_step_incomplete() validates task and delegates to Task."""

    def test_marks_step_incomplete(self):
        plan = parse(PLAN_TEXT)
        thread = plan.threads[0]
        thread.mark_step_incomplete(1, 1)
        assert not thread.tasks[0].steps[0]['completed']

    def test_error_for_nonexistent_task(self):
        plan = parse(PLAN_TEXT)
        thread = plan.threads[0]
        with pytest.raises(ValueError, match="task 99 does not exist"):
            thread.mark_step_incomplete(99, 1)

    def test_error_for_nonexistent_step(self):
        plan = parse(PLAN_TEXT)
        thread = plan.threads[0]
        with pytest.raises(ValueError, match="step 99 does not exist"):
            thread.mark_step_incomplete(1, 99)
