"""Tests for insert_task_before and insert_task_after pure functions."""

from i2code.plan.tasks import insert_task_before, insert_task_after


PLAN_WITH_TWO_TASKS = """\
# Implementation Plan: Test Plan

## Idea Type
**A. Feature** - A test feature

---

## Overview
This is a test plan.

---

## Steel Thread 1: First Thread
Introduction.

- [ ] **Task 1.1: Existing task A**
  - TaskType: INFRA
  - Entrypoint: `echo a`
  - Observable: A works
  - Evidence: `echo a-done`
  - Steps:
    - [ ] Do A

- [ ] **Task 1.2: Existing task B**
  - TaskType: OUTCOME
  - Entrypoint: `echo b`
  - Observable: B works
  - Evidence: `echo b-done`
  - Steps:
    - [ ] Do B

---

## Summary
Done.
"""


class TestInsertTaskBefore:
    """insert_task_before inserts a task and renumbers within the thread."""

    def test_inserts_before_first_task(self):
        result = insert_task_before(
            PLAN_WITH_TWO_TASKS, 1, 1,
            "New task", "INFRA", "echo new", "New works", "echo new-done",
            ["Step new"], "Adding new task"
        )
        assert 'Task 1.1: New task' in result
        assert 'Task 1.2: Existing task A' in result
        assert 'Task 1.3: Existing task B' in result

    def test_inserts_before_second_task(self):
        result = insert_task_before(
            PLAN_WITH_TWO_TASKS, 1, 2,
            "New task", "OUTCOME", "echo new", "New works", "echo new-done",
            ["Step new"], "Adding new task"
        )
        assert 'Task 1.1: Existing task A' in result
        assert 'Task 1.2: New task' in result
        assert 'Task 1.3: Existing task B' in result

    def test_new_task_has_metadata(self):
        result = insert_task_before(
            PLAN_WITH_TWO_TASKS, 1, 1,
            "New task", "INFRA", "echo new", "New works", "echo new-done",
            ["Step one", "Step two"], "Adding"
        )
        assert 'TaskType: INFRA' in result
        assert 'Entrypoint: `echo new`' in result
        assert 'Observable: New works' in result
        assert 'Evidence: `echo new-done`' in result
        assert '    - [ ] Step one' in result
        assert '    - [ ] Step two' in result

    def test_appends_change_history(self):
        result = insert_task_before(
            PLAN_WITH_TWO_TASKS, 1, 1,
            "New task", "INFRA", "echo new", "New works", "echo new-done",
            ["Step"], "Need a new task"
        )
        assert 'insert-task-before' in result
        assert 'Need a new task' in result

    def test_error_on_nonexistent_thread(self):
        import pytest
        with pytest.raises(ValueError, match="thread 99 does not exist"):
            insert_task_before(
                PLAN_WITH_TWO_TASKS, 99, 1,
                "New", "INFRA", "echo", "obs", "ev", ["step"], "reason"
            )

    def test_error_on_nonexistent_task(self):
        import pytest
        with pytest.raises(ValueError, match="task 99.*does not exist"):
            insert_task_before(
                PLAN_WITH_TWO_TASKS, 1, 99,
                "New", "INFRA", "echo", "obs", "ev", ["step"], "reason"
            )


class TestInsertTaskAfter:
    """insert_task_after inserts a task after the specified task."""

    def test_inserts_after_first_task(self):
        result = insert_task_after(
            PLAN_WITH_TWO_TASKS, 1, 1,
            "New task", "INFRA", "echo new", "New works", "echo new-done",
            ["Step new"], "Adding new task"
        )
        assert 'Task 1.1: Existing task A' in result
        assert 'Task 1.2: New task' in result
        assert 'Task 1.3: Existing task B' in result

    def test_inserts_after_last_task(self):
        result = insert_task_after(
            PLAN_WITH_TWO_TASKS, 1, 2,
            "New task", "OUTCOME", "echo new", "New works", "echo new-done",
            ["Step new"], "Adding new task"
        )
        assert 'Task 1.1: Existing task A' in result
        assert 'Task 1.2: Existing task B' in result
        assert 'Task 1.3: New task' in result

    def test_appends_change_history(self):
        result = insert_task_after(
            PLAN_WITH_TWO_TASKS, 1, 1,
            "New", "INFRA", "echo", "obs", "ev", ["step"], "reason"
        )
        assert 'insert-task-after' in result

    def test_error_on_nonexistent_thread(self):
        import pytest
        with pytest.raises(ValueError, match="thread 99 does not exist"):
            insert_task_after(
                PLAN_WITH_TWO_TASKS, 99, 1,
                "New", "INFRA", "echo", "obs", "ev", ["step"], "reason"
            )

    def test_error_on_nonexistent_task(self):
        import pytest
        with pytest.raises(ValueError, match="task 99.*does not exist"):
            insert_task_after(
                PLAN_WITH_TWO_TASKS, 1, 99,
                "New", "INFRA", "echo", "obs", "ev", ["step"], "reason"
            )
