"""Regression test: thread operations must not produce Task 0.x numbering."""

from i2code.plan.threads import reorder_threads
from i2code.plan_domain.parser import parse
from i2code.plan_domain.thread import Thread


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
        plan = parse(PLAN)
        plan.delete_thread(1)
        result = plan.to_text()
        assert '**Task 0.' not in result
        assert '**Task 1.1: Task B**' in result

    def test_reorder_threads_renumbers_correctly(self):
        result = reorder_threads(PLAN, [2, 1], "swap")
        assert '**Task 0.' not in result
        assert '**Task 1.1: Task B**' in result
        assert '**Task 2.1: Task A**' in result

    def test_insert_thread_before_first_renumbers_correctly(self):
        plan = parse(PLAN)
        new_thread = Thread.create(title='New', introduction='New intro.', tasks=[{
            'title': 'New task', 'task_type': 'INFRA',
            'entrypoint': 'echo new', 'observable': 'New done',
            'evidence': 'echo new', 'steps': ['Do new']
        }])
        plan.insert_thread_before(1, new_thread)
        result = plan.to_text()
        assert '**Task 0.' not in result
        assert '**Task 1.1: New task**' in result

    def test_replace_first_thread_renumbers_correctly(self):
        plan = parse(PLAN)
        new_thread = Thread.create(title="Replaced", introduction="Replaced intro.", tasks=[{
            'title': 'Replaced task', 'task_type': 'INFRA',
            'entrypoint': 'echo r', 'observable': 'R done',
            'evidence': 'echo r', 'steps': ['Do r']
        }])
        plan.replace_thread(1, new_thread)
        result = plan.to_text()
        assert '**Task 0.' not in result
        assert '**Task 1.1: Replaced task**' in result
