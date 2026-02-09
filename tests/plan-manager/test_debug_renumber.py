"""Regression test: thread operations must not produce Task 0.x numbering."""

from i2code.plan.threads import (
    delete_thread, reorder_threads, insert_thread_before, replace_thread,
)


PLAN = """\
# Implementation Plan: Test Plan

## Idea Type
**A. Feature** - A test feature

---

## Overview
Test plan.

---

## Steel Thread 1: First
First intro.

- [ ] **Task 1.1: Task A**
  - TaskType: INFRA
  - Entrypoint: `echo a`
  - Observable: A done
  - Evidence: `echo a`
  - Steps:
    - [ ] Step A

---

## Steel Thread 2: Second
Second intro.

- [ ] **Task 2.1: Task B**
  - TaskType: OUTCOME
  - Entrypoint: `echo b`
  - Observable: B done
  - Evidence: `echo b`
  - Steps:
    - [ ] Step B

---

## Summary
Done.
"""


class TestNoZeroNumbering:
    """Thread operations must never produce Task 0.x numbering."""

    def test_delete_first_thread_renumbers_correctly(self):
        result = delete_thread(PLAN, 1, "remove first")
        assert '**Task 0.' not in result
        assert '**Task 1.1: Task B**' in result

    def test_reorder_threads_renumbers_correctly(self):
        result = reorder_threads(PLAN, [2, 1], "swap")
        assert '**Task 0.' not in result
        assert '**Task 1.1: Task B**' in result
        assert '**Task 2.1: Task A**' in result

    def test_insert_thread_before_first_renumbers_correctly(self):
        result = insert_thread_before(PLAN, 1, "New", "New intro.", [{
            'title': 'New task', 'task_type': 'INFRA',
            'entrypoint': 'echo new', 'observable': 'New done',
            'evidence': 'echo new', 'steps': ['Do new']
        }], "insert before first")
        assert '**Task 0.' not in result
        assert '**Task 1.1: New task**' in result

    def test_replace_first_thread_renumbers_correctly(self):
        result = replace_thread(PLAN, 1, "Replaced", "Replaced intro.", [{
            'title': 'Replaced task', 'task_type': 'INFRA',
            'entrypoint': 'echo r', 'observable': 'R done',
            'evidence': 'echo r', 'steps': ['Do r']
        }], "replace first")
        assert '**Task 0.' not in result
        assert '**Task 1.1: Replaced task**' in result
