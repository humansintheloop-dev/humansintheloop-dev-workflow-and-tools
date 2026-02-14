"""Tests for Plan.mark_step_incomplete() delegation."""

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
    - [x] Step one
    - [x] Step two

- [ ] **Task 1.2: Second task**
  - TaskType: OUTCOME
  - Entrypoint: `echo hello2`
  - Observable: Something else
  - Evidence: `echo done2`
  - Steps:
    - [x] Step one

---

## Summary
Done."""


class TestPlanMarkStepIncomplete:
    """Plan.mark_step_incomplete() delegates to Task and validates inputs."""

    def test_marks_step_incomplete(self):
        plan = parse(PLAN_TEXT)
        plan.mark_step_incomplete(1, 1, 1)
        assert not plan.threads[0].tasks[0].steps[0]['completed']

    def test_does_not_affect_other_steps(self):
        plan = parse(PLAN_TEXT)
        plan.mark_step_incomplete(1, 1, 1)
        assert plan.threads[0].tasks[0].steps[1]['completed']

    def test_error_for_nonexistent_thread(self):
        plan = parse(PLAN_TEXT)
        with pytest.raises(ValueError, match="thread 99 does not exist"):
            plan.mark_step_incomplete(99, 1, 1)

    def test_error_for_nonexistent_task(self):
        plan = parse(PLAN_TEXT)
        with pytest.raises(ValueError, match="task 99 does not exist"):
            plan.mark_step_incomplete(1, 99, 1)

    def test_error_for_nonexistent_step(self):
        plan = parse(PLAN_TEXT)
        with pytest.raises(ValueError, match="step 99 does not exist"):
            plan.mark_step_incomplete(1, 1, 99)

    def test_error_for_already_incomplete(self):
        plan = parse(PLAN_TEXT)
        plan.mark_step_incomplete(1, 1, 1)
        with pytest.raises(ValueError, match="already incomplete"):
            plan.mark_step_incomplete(1, 1, 1)
