"""Tests for Plan.delete_thread() method."""

import pytest

from i2code.plan_domain.parser import parse


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

## Steel Thread 3: Third Thread
Intro third.

- [ ] **Task 3.1: Third task**
  - TaskType: OUTCOME
  - Entrypoint: `echo third`
  - Observable: Third
  - Evidence: `echo third-done`
  - Steps:
    - [ ] Do third

---

## Summary
Done."""


class TestPlanDeleteThread:
    """Plan.delete_thread() removes a thread and validates inputs."""

    def test_deletes_thread(self):
        plan = parse(PLAN_TEXT)
        plan.delete_thread(2)
        assert len(plan.threads) == 2

    def test_error_for_nonexistent_thread(self):
        plan = parse(PLAN_TEXT)
        with pytest.raises(ValueError, match="thread 99 does not exist"):
            plan.delete_thread(99)

    def test_renumbers_in_output(self):
        plan = parse(PLAN_TEXT)
        plan.delete_thread(1)
        text = plan.to_text()
        assert "Steel Thread 1: Second Thread" in text
        assert "Steel Thread 2: Third Thread" in text
        assert "Task 1.1: Second task" in text
        assert "Task 2.1: Third task" in text
