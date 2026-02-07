"""Tests for get_thread pure function."""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'skills', 'plan-file-management', 'scripts'))

from importlib import import_module
_mod = import_module('plan-manager')
get_thread = _mod.get_thread


PLAN_WITH_TWO_THREADS = """\
# Implementation Plan: Test Plan

## Idea Type
**A. Feature** - A test feature

---

## Overview
This is a test plan.

---

## Steel Thread 1: First Thread
Introduction to the first thread.

This has multiple paragraphs of introduction.

- [x] **Task 1.1: Completed task**
  - TaskType: INFRA
  - Entrypoint: `echo setup`
  - Observable: Setup is done
  - Evidence: `echo verified`
  - Steps:
    - [x] Create the file
    - [x] Verify the file

- [ ] **Task 1.2: Pending task**
  - TaskType: OUTCOME
  - Entrypoint: `echo run`
  - Observable: Feature works
  - Evidence: `pytest tests/`
  - Steps:
    - [ ] Write the test
    - [x] Implement the code
    - [ ] Verify it works

---

## Steel Thread 2: Second Thread
Introduction to second thread.

- [ ] **Task 2.1: Another task**
  - TaskType: OUTCOME
  - Entrypoint: `echo another`
  - Observable: Another thing happens
  - Evidence: `echo another-done`
  - Steps:
    - [ ] Do another thing

---

## Summary
Done.
"""


class TestGetThread:
    """get_thread returns full thread content with tasks and steps."""

    def test_returns_thread_number_and_title(self):
        result = get_thread(PLAN_WITH_TWO_THREADS, 1)
        assert result['number'] == 1
        assert result['title'] == 'First Thread'

    def test_returns_introduction(self):
        result = get_thread(PLAN_WITH_TWO_THREADS, 1)
        assert 'Introduction to the first thread.' in result['introduction']
        assert 'multiple paragraphs' in result['introduction']

    def test_returns_all_tasks(self):
        result = get_thread(PLAN_WITH_TWO_THREADS, 1)
        assert len(result['tasks']) == 2

    def test_returns_completed_task_metadata(self):
        result = get_thread(PLAN_WITH_TWO_THREADS, 1)
        task1 = result['tasks'][0]
        assert task1['task_number'] == 1
        assert task1['title'] == 'Completed task'
        assert task1['completed'] is True
        assert task1['task_type'] == 'INFRA'
        assert task1['entrypoint'] == 'echo setup'
        assert task1['observable'] == 'Setup is done'
        assert task1['evidence'] == 'echo verified'

    def test_returns_task_steps_with_completion_status(self):
        result = get_thread(PLAN_WITH_TWO_THREADS, 1)
        task1 = result['tasks'][0]
        assert len(task1['steps']) == 2
        assert task1['steps'][0] == {'description': 'Create the file', 'completed': True}
        assert task1['steps'][1] == {'description': 'Verify the file', 'completed': True}

    def test_returns_pending_task_with_mixed_steps(self):
        result = get_thread(PLAN_WITH_TWO_THREADS, 1)
        task2 = result['tasks'][1]
        assert task2['task_number'] == 2
        assert task2['title'] == 'Pending task'
        assert task2['completed'] is False
        assert task2['task_type'] == 'OUTCOME'
        assert len(task2['steps']) == 3
        assert task2['steps'][0]['completed'] is False
        assert task2['steps'][1]['completed'] is True
        assert task2['steps'][2]['completed'] is False

    def test_returns_second_thread(self):
        result = get_thread(PLAN_WITH_TWO_THREADS, 2)
        assert result['number'] == 2
        assert result['title'] == 'Second Thread'
        assert 'Introduction to second thread.' in result['introduction']
        assert len(result['tasks']) == 1

    def test_error_on_nonexistent_thread(self):
        import pytest
        with pytest.raises(ValueError, match="get-thread: thread 99 does not exist"):
            get_thread(PLAN_WITH_TWO_THREADS, 99)
