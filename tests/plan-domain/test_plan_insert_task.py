"""Tests for Plan.insert_task_before() and Plan.insert_task_after() delegation."""

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


class TestPlanInsertTaskBefore:
    """Plan.insert_task_before() delegates to Thread.insert_task and validates inputs."""

    def test_inserts_before_first_task(self):
        plan = parse(PLAN_TEXT)
        new_task = Task.create("New task", "INFRA", "echo new", "New works", "echo new-done", ["Step new"])
        plan.insert_task_before(1, 1, new_task)
        assert len(plan.threads[0].tasks) == 3
        assert plan.threads[0].tasks[0].title == "New task"
        assert plan.threads[0].tasks[1].title == "First task"

    def test_renumbers_in_output(self):
        plan = parse(PLAN_TEXT)
        new_task = Task.create("New task", "INFRA", "echo new", "New works", "echo new-done", ["Step new"])
        plan.insert_task_before(1, 1, new_task)
        text = plan.to_text()
        assert "Task 1.1: New task" in text
        assert "Task 1.2: First task" in text
        assert "Task 1.3: Second task" in text

    def test_inserts_before_second_task(self):
        plan = parse(PLAN_TEXT)
        new_task = Task.create("New task", "INFRA", "echo new", "New works", "echo new-done", ["Step new"])
        plan.insert_task_before(1, 2, new_task)
        assert plan.threads[0].tasks[0].title == "First task"
        assert plan.threads[0].tasks[1].title == "New task"
        assert plan.threads[0].tasks[2].title == "Second task"

    def test_error_for_nonexistent_thread(self):
        plan = parse(PLAN_TEXT)
        new_task = Task.create("New", "INFRA", "e", "o", "v", ["s"])
        with pytest.raises(ValueError, match="insert-task-before: thread 99 does not exist"):
            plan.insert_task_before(99, 1, new_task)

    def test_error_for_nonexistent_task(self):
        plan = parse(PLAN_TEXT)
        new_task = Task.create("New", "INFRA", "e", "o", "v", ["s"])
        with pytest.raises(ValueError, match="insert-task-before: task 1.99 does not exist"):
            plan.insert_task_before(1, 99, new_task)


class TestPlanInsertTaskAfter:
    """Plan.insert_task_after() delegates to Thread.insert_task and validates inputs."""

    def test_inserts_after_first_task(self):
        plan = parse(PLAN_TEXT)
        new_task = Task.create("New task", "INFRA", "echo new", "New works", "echo new-done", ["Step new"])
        plan.insert_task_after(1, 1, new_task)
        assert len(plan.threads[0].tasks) == 3
        assert plan.threads[0].tasks[0].title == "First task"
        assert plan.threads[0].tasks[1].title == "New task"
        assert plan.threads[0].tasks[2].title == "Second task"

    def test_inserts_after_last_task(self):
        plan = parse(PLAN_TEXT)
        new_task = Task.create("New task", "INFRA", "echo new", "New works", "echo new-done", ["Step new"])
        plan.insert_task_after(1, 2, new_task)
        assert plan.threads[0].tasks[0].title == "First task"
        assert plan.threads[0].tasks[1].title == "Second task"
        assert plan.threads[0].tasks[2].title == "New task"

    def test_renumbers_in_output(self):
        plan = parse(PLAN_TEXT)
        new_task = Task.create("New task", "INFRA", "echo new", "New works", "echo new-done", ["Step new"])
        plan.insert_task_after(1, 1, new_task)
        text = plan.to_text()
        assert "Task 1.1: First task" in text
        assert "Task 1.2: New task" in text
        assert "Task 1.3: Second task" in text

    def test_error_for_nonexistent_thread(self):
        plan = parse(PLAN_TEXT)
        new_task = Task.create("New", "INFRA", "e", "o", "v", ["s"])
        with pytest.raises(ValueError, match="insert-task-after: thread 99 does not exist"):
            plan.insert_task_after(99, 1, new_task)

    def test_error_for_nonexistent_task(self):
        plan = parse(PLAN_TEXT)
        new_task = Task.create("New", "INFRA", "e", "o", "v", ["s"])
        with pytest.raises(ValueError, match="insert-task-after: task 1.99 does not exist"):
            plan.insert_task_after(1, 99, new_task)
