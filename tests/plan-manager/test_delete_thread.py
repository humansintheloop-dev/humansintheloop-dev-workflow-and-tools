"""Tests for delete_thread pure function."""

from i2code.plan.threads import delete_thread


PLAN_WITH_THREE_THREADS = """\
# Implementation Plan: Test Plan

## Idea Type
**A. Feature** - A test feature

---

## Overview
This is a test plan.

---

## Steel Thread 1: First Thread
Introduction to first.

- [ ] **Task 1.1: First task**
  - TaskType: INFRA
  - Entrypoint: `echo first`
  - Observable: First
  - Evidence: `echo first-done`
  - Steps:
    - [ ] Do first

---

## Steel Thread 2: Second Thread
Introduction to second.

- [ ] **Task 2.1: Second task**
  - TaskType: OUTCOME
  - Entrypoint: `echo second`
  - Observable: Second
  - Evidence: `echo second-done`
  - Steps:
    - [ ] Do second

---

## Steel Thread 3: Third Thread
Introduction to third.

- [ ] **Task 3.1: Third task**
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


class TestDeleteThread:
    """delete_thread removes a thread and renumbers remaining threads."""

    def test_removes_first_thread(self):
        result = delete_thread(PLAN_WITH_THREE_THREADS, 1, "Removing first thread")
        assert 'First Thread' not in result
        assert 'First task' not in result

    def test_renumbers_remaining_threads(self):
        result = delete_thread(PLAN_WITH_THREE_THREADS, 1, "Removing first thread")
        assert '## Steel Thread 1: Second Thread' in result
        assert '## Steel Thread 2: Third Thread' in result

    def test_renumbers_tasks(self):
        result = delete_thread(PLAN_WITH_THREE_THREADS, 1, "Removing first thread")
        assert 'Task 1.1: Second task' in result
        assert 'Task 2.1: Third task' in result

    def test_removes_middle_thread(self):
        result = delete_thread(PLAN_WITH_THREE_THREADS, 2, "Removing second thread")
        assert '## Steel Thread 1: First Thread' in result
        assert '## Steel Thread 2: Third Thread' in result
        assert 'Second Thread' not in result.split('## Steel Thread')[1:].__repr__() or 'Second task' not in result

    def test_removes_last_thread(self):
        result = delete_thread(PLAN_WITH_THREE_THREADS, 3, "Removing third thread")
        assert '## Steel Thread 1: First Thread' in result
        assert '## Steel Thread 2: Second Thread' in result
        assert 'Third Thread' not in result

    def test_appends_change_history(self):
        result = delete_thread(PLAN_WITH_THREE_THREADS, 1, "No longer needed")
        assert '## Change History' in result
        assert 'delete-thread' in result
        assert 'No longer needed' in result

    def test_preserves_summary(self):
        result = delete_thread(PLAN_WITH_THREE_THREADS, 1, "Removing")
        assert '## Summary' in result
        assert 'Done.' in result


class TestDeleteThreadErrors:
    """delete_thread returns errors for invalid inputs."""

    def test_error_on_nonexistent_thread(self):
        import pytest
        with pytest.raises(ValueError, match="thread 99 does not exist"):
            delete_thread(PLAN_WITH_THREE_THREADS, 99, "No such thread")
