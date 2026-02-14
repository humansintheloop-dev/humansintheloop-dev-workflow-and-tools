"""Tests for Thread.reorder_tasks() method."""

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


class TestThreadReorderTasks:
    """Thread.reorder_tasks() reorders tasks by 1-based indices."""

    def test_reverses_task_order(self):
        plan = parse(PLAN_TEXT)
        thread = plan.threads[0]
        thread.reorder_tasks([3, 2, 1])
        assert thread.tasks[0].title == "Third task"
        assert thread.tasks[1].title == "Second task"
        assert thread.tasks[2].title == "First task"

    def test_preserves_completion_status(self):
        plan = parse(PLAN_TEXT)
        thread = plan.threads[0]
        thread.reorder_tasks([2, 3, 1])
        assert thread.tasks[2].is_completed is True
        assert thread.tasks[0].is_completed is False

    def test_error_for_duplicate_task_numbers(self):
        plan = parse(PLAN_TEXT)
        thread = plan.threads[0]
        with pytest.raises(ValueError, match="duplicate"):
            thread.reorder_tasks([1, 1, 2])

    def test_error_for_wrong_count(self):
        plan = parse(PLAN_TEXT)
        thread = plan.threads[0]
        with pytest.raises(ValueError, match="does not match"):
            thread.reorder_tasks([1, 2])

    def test_error_for_nonexistent_task_number(self):
        plan = parse(PLAN_TEXT)
        thread = plan.threads[0]
        with pytest.raises(ValueError, match="does not match"):
            thread.reorder_tasks([1, 2, 99])
