"""Tests for Thread.replace_task() method."""

import pytest

from i2code.plan_domain.parser import parse
from i2code.plan_domain.task import Task


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


class TestThreadReplaceTask:
    """Thread.replace_task() replaces a task by 1-based index."""

    def test_replaces_task(self):
        plan = parse(PLAN_TEXT)
        thread = plan.threads[0]
        new_task = Task.create("Replaced", "INFRA", "echo r", "R done", "echo r-done", ["Step R"])
        thread.replace_task(2, new_task)
        assert len(thread.tasks) == 3
        assert thread.tasks[1].title == "Replaced"

    def test_error_for_nonexistent_task(self):
        plan = parse(PLAN_TEXT)
        thread = plan.threads[0]
        new_task = Task.create("New", "INFRA", "echo", "obs", "ev", ["step"])
        with pytest.raises(ValueError, match="task 99 does not exist"):
            thread.replace_task(99, new_task)
