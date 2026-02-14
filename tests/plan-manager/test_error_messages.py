"""Tests for error message format: each error includes subcommand name and human-readable message."""

import pytest

from i2code.plan.plans import get_thread
from i2code.plan_domain.task import Task
from i2code.plan.threads import delete_thread, replace_thread, reorder_threads
from i2code.plan_domain.parser import parse


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
        plan = parse(SIMPLE_PLAN)
        with pytest.raises(ValueError, match="already complete"):
            plan.mark_task_complete(1, 1)

    def test_mark_task_complete_nonexistent(self):
        plan = parse(SIMPLE_PLAN)
        with pytest.raises(ValueError, match="task 99 does not exist"):
            plan.mark_task_complete(1, 99)

    def test_mark_task_incomplete_already_incomplete(self):
        plan = parse(SIMPLE_PLAN)
        plan.mark_task_incomplete(1, 1)
        with pytest.raises(ValueError, match="already incomplete"):
            plan.mark_task_incomplete(1, 1)

    def test_mark_task_incomplete_nonexistent(self):
        plan = parse(SIMPLE_PLAN)
        with pytest.raises(ValueError, match="task 99 does not exist"):
            plan.mark_task_incomplete(1, 99)

    def test_delete_thread_nonexistent(self):
        with pytest.raises(ValueError, match="delete-thread:.*does not exist"):
            delete_thread(SIMPLE_PLAN, 99, "reason")

    def test_delete_task_nonexistent(self):
        plan = parse(SIMPLE_PLAN)
        with pytest.raises(ValueError, match="task 99 does not exist"):
            plan.delete_task(1, 99)

    def test_insert_task_before_nonexistent(self):
        plan = parse(SIMPLE_PLAN)
        new_task = Task.create("t", "INFRA", "e", "o", "v", ["s"])
        with pytest.raises(ValueError, match="task 99 does not exist"):
            plan.insert_task_before(1, 99, new_task)

    def test_replace_thread_nonexistent(self):
        with pytest.raises(ValueError, match="replace-thread:.*does not exist"):
            replace_thread(SIMPLE_PLAN, 99, "t", "i", [], "r")

    def test_reorder_threads_invalid(self):
        with pytest.raises(ValueError, match="reorder-threads:"):
            reorder_threads(SIMPLE_PLAN, [1, 2], "r")

    def test_reorder_tasks_nonexistent_thread(self):
        plan = parse(SIMPLE_PLAN)
        with pytest.raises(ValueError, match="thread 99 does not exist"):
            plan.reorder_tasks(99, [1])

    def test_reorder_tasks_invalid_order(self):
        plan = parse(SIMPLE_PLAN)
        with pytest.raises(ValueError, match="reorder-tasks:"):
            plan.reorder_tasks(1, [1, 2])


