"""Tests for Thread.insert_task_before() method."""

import pytest

from i2code.plan_domain.parser import parse
from i2code.plan_domain.task import Task, TaskMetadata


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

---

## Summary
Done."""


class TestThreadInsertTaskBefore:
    """Thread.insert_task_before() validates 1-based task and inserts before it."""

    def test_inserts_before_first_task(self):
        plan = parse(PLAN_TEXT)
        thread = plan.threads[0]
        new_task = Task.create("New", TaskMetadata("INFRA", "echo new", "New", "echo new-done"), ["Do new"])
        thread.insert_task_before(1, new_task)
        assert len(thread.tasks) == 3
        assert thread.tasks[0].title == "New"
        assert thread.tasks[1].title == "First task"

    def test_inserts_before_second_task(self):
        plan = parse(PLAN_TEXT)
        thread = plan.threads[0]
        new_task = Task.create("New", TaskMetadata("INFRA", "echo new", "New", "echo new-done"), ["Do new"])
        thread.insert_task_before(2, new_task)
        assert thread.tasks[0].title == "First task"
        assert thread.tasks[1].title == "New"
        assert thread.tasks[2].title == "Second task"

    def test_error_for_nonexistent_task(self):
        plan = parse(PLAN_TEXT)
        thread = plan.threads[0]
        new_task = Task.create("New", TaskMetadata("INFRA", "echo new", "New", "echo new-done"), ["Do new"])
        with pytest.raises(ValueError, match="task 99 does not exist"):
            thread.insert_task_before(99, new_task)
