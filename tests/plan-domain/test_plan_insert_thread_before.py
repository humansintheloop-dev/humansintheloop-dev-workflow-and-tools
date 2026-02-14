"""Tests for Plan.insert_thread_before() method."""

import pytest

from i2code.plan_domain.parser import parse
from i2code.plan_domain.thread import Thread


PLAN_TEXT = """\
# Implementation Plan: Test

---

## Steel Thread 1: First Thread
Intro first.

- [ ] **Task 1.1: First task**
  - TaskType: INFRA
  - Entrypoint: `echo first`
  - Observable: First
  - Evidence: `echo first-done`
  - Steps:
    - [ ] Do first

## Steel Thread 2: Second Thread
Intro second.

- [ ] **Task 2.1: Second task**
  - TaskType: OUTCOME
  - Entrypoint: `echo second`
  - Observable: Second
  - Evidence: `echo second-done`
  - Steps:
    - [ ] Do second

---

## Summary
Done."""


def _new_thread():
    return Thread.create(
        title='New Thread',
        introduction='New intro.',
        tasks=[{
            'title': 'New task',
            'task_type': 'INFRA',
            'entrypoint': 'echo new',
            'observable': 'New thing',
            'evidence': 'echo new-done',
            'steps': ['Do new thing'],
        }],
    )


class TestPlanInsertThreadBefore:

    def test_inserts_before_first_thread(self):
        plan = parse(PLAN_TEXT)
        plan.insert_thread_before(1, _new_thread())
        assert len(plan.threads) == 3
        assert plan.threads[0].tasks[0].title == 'New task'

    def test_inserts_before_second_thread(self):
        plan = parse(PLAN_TEXT)
        plan.insert_thread_before(2, _new_thread())
        assert len(plan.threads) == 3
        assert plan.threads[1].tasks[0].title == 'New task'

    def test_renumbers_in_output(self):
        plan = parse(PLAN_TEXT)
        plan.insert_thread_before(1, _new_thread())
        text = plan.to_text()
        assert "Steel Thread 1: New Thread" in text
        assert "Steel Thread 2: First Thread" in text
        assert "Steel Thread 3: Second Thread" in text
        assert "Task 1.1: New task" in text
        assert "Task 2.1: First task" in text
        assert "Task 3.1: Second task" in text

    def test_error_for_nonexistent_thread(self):
        plan = parse(PLAN_TEXT)
        with pytest.raises(ValueError, match="thread 99 does not exist"):
            plan.insert_thread_before(99, _new_thread())
