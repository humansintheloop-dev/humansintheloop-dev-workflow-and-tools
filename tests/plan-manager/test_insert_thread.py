"""Tests for insert_thread_before and insert_thread_after pure functions."""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'skills', 'plan-file-management', 'scripts'))

from importlib import import_module
_mod = import_module('plan-manager')
insert_thread_before = _mod.insert_thread_before
insert_thread_after = _mod.insert_thread_after


TWO_THREAD_PLAN = """\
# Implementation Plan: Test Plan

## Idea Type
**A. Feature** - A test feature

---

## Overview
This is a test plan.

---

## Steel Thread 1: First Thread
Introduction to first thread.

- [ ] **Task 1.1: Alpha task**
  - TaskType: INFRA
  - Entrypoint: `echo alpha`
  - Observable: Alpha happens
  - Evidence: `echo alpha-done`
  - Steps:
    - [ ] Alpha step one

---

## Steel Thread 2: Second Thread
Introduction to second thread.

- [ ] **Task 2.1: Beta task**
  - TaskType: OUTCOME
  - Entrypoint: `echo beta`
  - Observable: Beta happens
  - Evidence: `echo beta-done`
  - Steps:
    - [ ] Beta step one

---

## Summary
This plan has 2 threads.
"""

NEW_TASKS = [
    {
        "title": "New task",
        "task_type": "INFRA",
        "entrypoint": "echo new",
        "observable": "New thing happens",
        "evidence": "echo new-done",
        "steps": ["Do new thing", "Verify new thing"]
    }
]


class TestInsertThreadBefore:
    """insert_thread_before inserts a thread before the specified thread."""

    def test_inserts_before_thread_2(self):
        result = insert_thread_before(
            TWO_THREAD_PLAN, 2, "New Thread", "New intro.", NEW_TASKS, "Added new thread"
        )
        # New thread should be thread 2, old thread 2 becomes thread 3
        assert "## Steel Thread 1: First Thread" in result
        assert "## Steel Thread 2: New Thread" in result
        assert "## Steel Thread 3: Second Thread" in result

    def test_inserts_before_thread_1(self):
        result = insert_thread_before(
            TWO_THREAD_PLAN, 1, "New Thread", "New intro.", NEW_TASKS, "Added new thread"
        )
        # New thread becomes thread 1, old threads shift
        assert "## Steel Thread 1: New Thread" in result
        assert "## Steel Thread 2: First Thread" in result
        assert "## Steel Thread 3: Second Thread" in result

    def test_renumbers_tasks(self):
        result = insert_thread_before(
            TWO_THREAD_PLAN, 2, "New Thread", "New intro.", NEW_TASKS, "Added new thread"
        )
        assert "**Task 1.1: Alpha task**" in result
        assert "**Task 2.1: New task**" in result
        assert "**Task 3.1: Beta task**" in result

    def test_new_thread_has_correct_content(self):
        result = insert_thread_before(
            TWO_THREAD_PLAN, 2, "New Thread", "New intro.", NEW_TASKS, "Added new thread"
        )
        assert "New intro." in result
        assert "TaskType: INFRA" in result
        assert "Entrypoint: `echo new`" in result
        assert "Observable: New thing happens" in result
        assert "Evidence: `echo new-done`" in result
        assert "Do new thing" in result
        assert "Verify new thing" in result

    def test_new_task_steps_are_unchecked(self):
        result = insert_thread_before(
            TWO_THREAD_PLAN, 2, "New Thread", "New intro.", NEW_TASKS, "Added new thread"
        )
        assert "- [ ] Do new thing" in result
        assert "- [ ] Verify new thing" in result

    def test_appends_change_history(self):
        result = insert_thread_before(
            TWO_THREAD_PLAN, 2, "New Thread", "New intro.", NEW_TASKS, "Added new thread"
        )
        assert "## Change History" in result
        assert "insert-thread-before" in result
        assert "Added new thread" in result

    def test_error_on_nonexistent_thread(self):
        try:
            insert_thread_before(
                TWO_THREAD_PLAN, 99, "New Thread", "New intro.", NEW_TASKS, "Bad"
            )
            assert False, "Expected ValueError"
        except ValueError as e:
            assert "thread" in str(e).lower()


class TestInsertThreadAfter:
    """insert_thread_after inserts a thread after the specified thread."""

    def test_inserts_after_thread_1(self):
        result = insert_thread_after(
            TWO_THREAD_PLAN, 1, "New Thread", "New intro.", NEW_TASKS, "Added new thread"
        )
        assert "## Steel Thread 1: First Thread" in result
        assert "## Steel Thread 2: New Thread" in result
        assert "## Steel Thread 3: Second Thread" in result

    def test_inserts_after_last_thread(self):
        result = insert_thread_after(
            TWO_THREAD_PLAN, 2, "New Thread", "New intro.", NEW_TASKS, "Added new thread"
        )
        assert "## Steel Thread 1: First Thread" in result
        assert "## Steel Thread 2: Second Thread" in result
        assert "## Steel Thread 3: New Thread" in result

    def test_renumbers_tasks(self):
        result = insert_thread_after(
            TWO_THREAD_PLAN, 1, "New Thread", "New intro.", NEW_TASKS, "Added new thread"
        )
        assert "**Task 1.1: Alpha task**" in result
        assert "**Task 2.1: New task**" in result
        assert "**Task 3.1: Beta task**" in result

    def test_error_on_nonexistent_thread(self):
        try:
            insert_thread_after(
                TWO_THREAD_PLAN, 99, "New Thread", "New intro.", NEW_TASKS, "Bad"
            )
            assert False, "Expected ValueError"
        except ValueError as e:
            assert "thread" in str(e).lower()

    def test_appends_change_history(self):
        result = insert_thread_after(
            TWO_THREAD_PLAN, 1, "New Thread", "New intro.", NEW_TASKS, "Added"
        )
        assert "## Change History" in result
        assert "insert-thread-after" in result
