"""Tests for Plan.delete_task() delegation."""

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


class TestPlanDeleteTask:
    """Plan.delete_task() delegates to Thread and validates inputs."""

    def test_deletes_task(self):
        plan = parse(PLAN_TEXT)
        plan.delete_task(1, 2)
        assert len(plan.threads[0].tasks) == 2
        assert plan.threads[0].tasks[0].title == "First task"
        assert plan.threads[0].tasks[1].title == "Third task"

    def test_renumbers_in_output(self):
        plan = parse(PLAN_TEXT)
        plan.delete_task(1, 1)
        text = plan.to_text()
        assert "Task 1.1: Second task" in text
        assert "Task 1.2: Third task" in text

    def test_error_for_nonexistent_thread(self):
        plan = parse(PLAN_TEXT)
        with pytest.raises(ValueError, match="delete-task: thread 99 does not exist"):
            plan.delete_task(99, 1)

    def test_error_for_nonexistent_task(self):
        plan = parse(PLAN_TEXT)
        with pytest.raises(ValueError, match="delete-task: task 1.99 does not exist"):
            plan.delete_task(1, 99)
