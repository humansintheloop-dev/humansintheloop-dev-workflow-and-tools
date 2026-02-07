"""Tests for delete_task pure function."""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'skills', 'plan-file-management', 'scripts'))

from importlib import import_module
_mod = import_module('plan-manager')
delete_task = _mod.delete_task


PLAN_WITH_THREE_TASKS = """\
# Implementation Plan: Test Plan

## Idea Type
**A. Feature** - A test feature

---

## Overview
This is a test plan.

---

## Steel Thread 1: First Thread
Introduction.

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
Done.
"""


class TestDeleteTask:
    """delete_task removes a task and renumbers remaining tasks."""

    def test_removes_first_task(self):
        result = delete_task(PLAN_WITH_THREE_TASKS, 1, 1, "Not needed")
        assert 'First task' not in result

    def test_renumbers_remaining_tasks(self):
        result = delete_task(PLAN_WITH_THREE_TASKS, 1, 1, "Not needed")
        assert 'Task 1.1: Second task' in result
        assert 'Task 1.2: Third task' in result

    def test_removes_middle_task(self):
        result = delete_task(PLAN_WITH_THREE_TASKS, 1, 2, "Not needed")
        assert 'Task 1.1: First task' in result
        assert 'Task 1.2: Third task' in result
        assert 'Second task' not in result

    def test_removes_last_task(self):
        result = delete_task(PLAN_WITH_THREE_TASKS, 1, 3, "Not needed")
        assert 'Task 1.1: First task' in result
        assert 'Task 1.2: Second task' in result
        assert 'Third task' not in result

    def test_appends_change_history(self):
        result = delete_task(PLAN_WITH_THREE_TASKS, 1, 1, "Covered by another task")
        assert '## Change History' in result
        assert 'delete-task' in result
        assert 'Covered by another task' in result


class TestDeleteTaskErrors:
    """delete_task returns errors for invalid inputs."""

    def test_error_on_nonexistent_thread(self):
        import pytest
        with pytest.raises(ValueError, match="thread 99 does not exist"):
            delete_task(PLAN_WITH_THREE_TASKS, 99, 1, "reason")

    def test_error_on_nonexistent_task(self):
        import pytest
        with pytest.raises(ValueError, match="task 99.*does not exist"):
            delete_task(PLAN_WITH_THREE_TASKS, 1, 99, "reason")
