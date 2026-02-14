"""Tests for Thread.insert_task() method."""

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

---

## Summary
Done."""


class TestThreadInsertTask:
    """Thread.insert_task() inserts a Task at a 0-based index."""

    def test_inserts_at_beginning(self):
        plan = parse(PLAN_TEXT)
        thread = plan.threads[0]
        new_task = Task.create("New task", "INFRA", "echo new", "New works", "echo new-done", ["Step new"])
        thread.insert_task(0, new_task)
        assert len(thread.tasks) == 3
        assert thread.tasks[0].title == "New task"
        assert thread.tasks[1].title == "First task"
        assert thread.tasks[2].title == "Second task"

    def test_inserts_in_middle(self):
        plan = parse(PLAN_TEXT)
        thread = plan.threads[0]
        new_task = Task.create("New task", "INFRA", "echo new", "New works", "echo new-done", ["Step new"])
        thread.insert_task(1, new_task)
        assert len(thread.tasks) == 3
        assert thread.tasks[0].title == "First task"
        assert thread.tasks[1].title == "New task"
        assert thread.tasks[2].title == "Second task"

    def test_inserts_at_end(self):
        plan = parse(PLAN_TEXT)
        thread = plan.threads[0]
        new_task = Task.create("New task", "INFRA", "echo new", "New works", "echo new-done", ["Step new"])
        thread.insert_task(2, new_task)
        assert len(thread.tasks) == 3
        assert thread.tasks[0].title == "First task"
        assert thread.tasks[1].title == "Second task"
        assert thread.tasks[2].title == "New task"
