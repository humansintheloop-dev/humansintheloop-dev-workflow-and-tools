"""Tests for Plan.reorder_threads() method."""

import pytest

from i2code.plan_domain.parser import parse


PLAN_TEXT = """\
# Implementation Plan: Test

---

## Steel Thread 1: First Thread
Intro first.

- [ ] **Task 1.1: Alpha task**
  - TaskType: INFRA
  - Entrypoint: `echo alpha`
  - Observable: Alpha
  - Evidence: `echo alpha-done`
  - Steps:
    - [ ] Alpha step

## Steel Thread 2: Second Thread
Intro second.

- [ ] **Task 2.1: Beta task**
  - TaskType: OUTCOME
  - Entrypoint: `echo beta`
  - Observable: Beta
  - Evidence: `echo beta-done`
  - Steps:
    - [ ] Beta step

---

## Summary
Done."""


class TestPlanReorderThreads:
    """Plan.reorder_threads() reorders threads and validates inputs."""

    def test_swaps_two_threads(self):
        plan = parse(PLAN_TEXT)
        plan.reorder_threads([2, 1])
        text = plan.to_text()
        assert "Steel Thread 1: Second Thread" in text
        assert "Steel Thread 2: First Thread" in text

    def test_renumbers_tasks_after_swap(self):
        plan = parse(PLAN_TEXT)
        plan.reorder_threads([2, 1])
        text = plan.to_text()
        assert "Task 1.1: Beta task" in text
        assert "Task 2.1: Alpha task" in text

    def test_error_for_duplicate_thread_numbers(self):
        plan = parse(PLAN_TEXT)
        with pytest.raises(ValueError, match="reorder-threads: --order contains duplicate"):
            plan.reorder_threads([1, 1])

    def test_error_for_nonexistent_thread(self):
        plan = parse(PLAN_TEXT)
        with pytest.raises(ValueError, match="nonexistent threads"):
            plan.reorder_threads([1, 3])

    def test_error_for_missing_thread(self):
        plan = parse(PLAN_TEXT)
        with pytest.raises(ValueError, match="missing threads"):
            plan.reorder_threads([1])
