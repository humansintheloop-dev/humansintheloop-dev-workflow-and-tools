"""Tests for replace_thread pure function."""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'skills', 'plan-file-management', 'scripts'))

from importlib import import_module
_mod = import_module('plan-manager')
replace_thread = _mod.replace_thread


PLAN_WITH_TWO_THREADS = """\
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

## Summary
Done.
"""

NEW_TASKS = [
    {
        "title": "New task A",
        "task_type": "INFRA",
        "entrypoint": "echo new-a",
        "observable": "New A works",
        "evidence": "echo new-a-done",
        "steps": ["Step A1", "Step A2"]
    },
    {
        "title": "New task B",
        "task_type": "OUTCOME",
        "entrypoint": "echo new-b",
        "observable": "New B works",
        "evidence": "echo new-b-done",
        "steps": ["Step B1"]
    }
]


class TestReplaceThread:
    """replace_thread replaces a thread's content in place."""

    def test_replaces_thread_title(self):
        result = replace_thread(PLAN_WITH_TWO_THREADS, 1, "Replaced Thread",
                                "New introduction.", NEW_TASKS, "Replacing thread 1")
        assert '## Steel Thread 1: Replaced Thread' in result

    def test_replaces_thread_introduction(self):
        result = replace_thread(PLAN_WITH_TWO_THREADS, 1, "Replaced Thread",
                                "New introduction.", NEW_TASKS, "Replacing")
        assert 'New introduction.' in result
        assert 'Introduction to first.' not in result

    def test_replaces_tasks(self):
        result = replace_thread(PLAN_WITH_TWO_THREADS, 1, "Replaced Thread",
                                "New intro.", NEW_TASKS, "Replacing")
        assert 'Task 1.1: New task A' in result
        assert 'Task 1.2: New task B' in result
        assert 'First task' not in result

    def test_other_threads_unchanged(self):
        result = replace_thread(PLAN_WITH_TWO_THREADS, 1, "Replaced Thread",
                                "New intro.", NEW_TASKS, "Replacing")
        assert '## Steel Thread 2: Second Thread' in result
        assert 'Task 2.1: Second task' in result

    def test_appends_change_history(self):
        result = replace_thread(PLAN_WITH_TWO_THREADS, 1, "Replaced Thread",
                                "New intro.", NEW_TASKS, "Restructured thread 1")
        assert '## Change History' in result
        assert 'replace-thread' in result
        assert 'Restructured thread 1' in result

    def test_new_tasks_have_steps(self):
        result = replace_thread(PLAN_WITH_TWO_THREADS, 1, "Replaced Thread",
                                "New intro.", NEW_TASKS, "Replacing")
        assert '    - [ ] Step A1' in result
        assert '    - [ ] Step A2' in result
        assert '    - [ ] Step B1' in result


class TestReplaceThreadErrors:
    """replace_thread returns errors for invalid inputs."""

    def test_error_on_nonexistent_thread(self):
        import pytest
        with pytest.raises(ValueError, match="thread 99 does not exist"):
            replace_thread(PLAN_WITH_TWO_THREADS, 99, "Title", "Intro",
                           NEW_TASKS, "Reason")
