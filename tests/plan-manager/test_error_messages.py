"""Tests for error message format: each error includes subcommand name and human-readable message."""

import pytest

from i2code.plan.plans import get_thread
from i2code.plan.tasks import (
    mark_task_complete, mark_step_complete,
    delete_task, insert_task_before,
    reorder_tasks, move_task_before, move_task_after, replace_task,
)
from i2code.plan.threads import delete_thread, replace_thread, reorder_threads


SIMPLE_PLAN = """\
# Implementation Plan: Test Plan

## Idea Type
**A. Feature** - A test feature

---

## Overview
Test.

---

## Steel Thread 1: Thread
Intro.

- [x] **Task 1.1: Done task**
  - TaskType: INFRA
  - Entrypoint: `echo done`
  - Observable: Done
  - Evidence: `echo done`
  - Steps:
    - [x] Already done

---

## Summary
Done.
"""


class TestErrorMessageFormat:
    """Error messages include subcommand name and are human-readable."""

    def test_get_thread_includes_subcommand_name(self):
        with pytest.raises(ValueError, match="get-thread:"):
            get_thread(SIMPLE_PLAN, 99)

    def test_mark_task_complete_already_complete(self):
        with pytest.raises(ValueError, match="mark-task-complete:.*already complete"):
            mark_task_complete(SIMPLE_PLAN, 1, 1)

    def test_mark_task_complete_nonexistent(self):
        with pytest.raises(ValueError, match="mark-task-complete:.*does not exist"):
            mark_task_complete(SIMPLE_PLAN, 1, 99)

    def test_mark_step_complete_already_complete(self):
        with pytest.raises(ValueError, match="mark-step-complete:.*already complete"):
            mark_step_complete(SIMPLE_PLAN, 1, 1, 1, "reason")

    def test_mark_step_complete_nonexistent(self):
        with pytest.raises(ValueError, match="mark-step-complete:.*does not exist"):
            mark_step_complete(SIMPLE_PLAN, 1, 1, 99, "reason")

    def test_delete_thread_nonexistent(self):
        with pytest.raises(ValueError, match="delete-thread:.*does not exist"):
            delete_thread(SIMPLE_PLAN, 99, "reason")

    def test_delete_task_nonexistent(self):
        with pytest.raises(ValueError, match="delete-task:.*does not exist"):
            delete_task(SIMPLE_PLAN, 1, 99, "reason")

    def test_insert_task_before_nonexistent(self):
        with pytest.raises(ValueError, match="insert-task-before:.*does not exist"):
            insert_task_before(SIMPLE_PLAN, 1, 99, "t", "INFRA", "e", "o", "v", ["s"], "r")

    def test_replace_thread_nonexistent(self):
        with pytest.raises(ValueError, match="replace-thread:.*does not exist"):
            replace_thread(SIMPLE_PLAN, 99, "t", "i", [], "r")

    def test_reorder_threads_invalid(self):
        with pytest.raises(ValueError, match="reorder-threads:"):
            reorder_threads(SIMPLE_PLAN, [1, 2], "r")

    def test_reorder_tasks_nonexistent_thread(self):
        with pytest.raises(ValueError, match="reorder-tasks:.*does not exist"):
            reorder_tasks(SIMPLE_PLAN, 99, [1], "r")

    def test_reorder_tasks_invalid_order(self):
        with pytest.raises(ValueError, match="reorder-tasks:"):
            reorder_tasks(SIMPLE_PLAN, 1, [1, 2], "r")

    def test_move_task_before_nonexistent_thread(self):
        with pytest.raises(ValueError, match="move-task-before:.*does not exist"):
            move_task_before(SIMPLE_PLAN, 99, 1, 2, "r")

    def test_move_task_before_same_task(self):
        with pytest.raises(ValueError, match="move-task-before:.*same task"):
            move_task_before(SIMPLE_PLAN, 1, 1, 1, "r")

    def test_move_task_after_nonexistent_thread(self):
        with pytest.raises(ValueError, match="move-task-after:.*does not exist"):
            move_task_after(SIMPLE_PLAN, 99, 1, 2, "r")

    def test_move_task_after_same_task(self):
        with pytest.raises(ValueError, match="move-task-after:.*same task"):
            move_task_after(SIMPLE_PLAN, 1, 1, 1, "r")

    def test_replace_task_nonexistent_thread(self):
        with pytest.raises(ValueError, match="replace-task:.*does not exist"):
            replace_task(SIMPLE_PLAN, 99, 1, "t", "INFRA", "e", "o", "v", ["s"], "r")

    def test_replace_task_nonexistent_task(self):
        with pytest.raises(ValueError, match="replace-task:.*does not exist"):
            replace_task(SIMPLE_PLAN, 1, 99, "t", "INFRA", "e", "o", "v", ["s"], "r")
