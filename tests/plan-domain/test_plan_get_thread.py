"""Tests for Plan.get_thread()."""

import pytest

from i2code.plan_domain.parser import parse


PLAN_TEXT = """\
# Implementation Plan: Test

---

## Steel Thread 1: First Thread
Intro.

- [ ] **Task 1.1: First task**
  - TaskType: INFRA
  - Entrypoint: `echo first`
  - Observable: First
  - Evidence: `echo first-done`
  - Steps:
    - [ ] Do first

---

## Steel Thread 2: Second Thread
Intro.

- [ ] **Task 2.1: Another task**
  - TaskType: OUTCOME
  - Entrypoint: `echo another`
  - Observable: Another
  - Evidence: `echo another-done`
  - Steps:
    - [ ] Do another

---

## Summary
Done."""


class TestPlanGetThread:
    """Plan.get_thread() returns the Thread at the given 1-based index."""

    def test_returns_first_thread(self):
        plan = parse(PLAN_TEXT)
        thread = plan.get_thread(1)
        assert len(thread.tasks) == 1
        assert thread.tasks[0].title == "First task"

    def test_returns_second_thread(self):
        plan = parse(PLAN_TEXT)
        thread = plan.get_thread(2)
        assert len(thread.tasks) == 1
        assert thread.tasks[0].title == "Another task"

    def test_error_for_nonexistent_thread(self):
        plan = parse(PLAN_TEXT)
        with pytest.raises(ValueError, match="thread 99 does not exist"):
            plan.get_thread(99)

    def test_error_for_zero_thread(self):
        plan = parse(PLAN_TEXT)
        with pytest.raises(ValueError, match="thread 0 does not exist"):
            plan.get_thread(0)
