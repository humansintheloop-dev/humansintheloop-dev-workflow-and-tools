"""Tests for Plan.move_task_after() delegation."""

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


class TestPlanMoveTaskAfter:
    """Plan.move_task_after() delegates to Thread and validates inputs."""

    def test_moves_task(self):
        plan = parse(PLAN_TEXT)
        plan.move_task_after(1, 1, 3)
        assert plan.threads[0].tasks[0].title == "Second task"
        assert plan.threads[0].tasks[1].title == "Third task"
        assert plan.threads[0].tasks[2].title == "First task"

    def test_renumbers_in_output(self):
        plan = parse(PLAN_TEXT)
        plan.move_task_after(1, 1, 3)
        text = plan.to_text()
        assert "Task 1.1: Second task" in text
        assert "Task 1.2: Third task" in text
        assert "Task 1.3: First task" in text

    def test_error_for_nonexistent_thread(self):
        plan = parse(PLAN_TEXT)
        with pytest.raises(ValueError, match="thread 99 does not exist"):
            plan.move_task_after(99, 1, 2)
