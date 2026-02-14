"""Tests for Plan.reorder_tasks() delegation."""

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


class TestPlanReorderTasks:
    """Plan.reorder_tasks() delegates to Thread and validates inputs."""

    def test_reorders_tasks(self):
        plan = parse(PLAN_TEXT)
        plan.reorder_tasks(1, [3, 2, 1])
        assert plan.threads[0].tasks[0].title == "Third task"
        assert plan.threads[0].tasks[1].title == "Second task"
        assert plan.threads[0].tasks[2].title == "First task"

    def test_renumbers_in_output(self):
        plan = parse(PLAN_TEXT)
        plan.reorder_tasks(1, [3, 2, 1])
        text = plan.to_text()
        assert "Task 1.1: Third task" in text
        assert "Task 1.2: Second task" in text
        assert "Task 1.3: First task" in text

    def test_error_for_nonexistent_thread(self):
        plan = parse(PLAN_TEXT)
        with pytest.raises(ValueError, match="thread 99 does not exist"):
            plan.reorder_tasks(99, [1, 2, 3])

    def test_error_for_invalid_order(self):
        plan = parse(PLAN_TEXT)
        with pytest.raises(ValueError, match="does not match"):
            plan.reorder_tasks(1, [1, 2])
