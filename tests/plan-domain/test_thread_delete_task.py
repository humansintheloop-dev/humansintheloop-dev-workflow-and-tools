"""Tests for Thread.delete_task() method."""

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


class TestThreadDeleteTask:
    """Thread.delete_task() removes a task by 1-based index."""

    def test_removes_task(self):
        plan = parse(PLAN_TEXT)
        thread = plan.threads[0]
        thread.delete_task(2)
        assert len(thread.tasks) == 2
        assert thread.tasks[0].title == "First task"
        assert thread.tasks[1].title == "Third task"

    def test_error_for_nonexistent_task(self):
        plan = parse(PLAN_TEXT)
        thread = plan.threads[0]
        with pytest.raises(ValueError, match="task 99 does not exist"):
            thread.delete_task(99)
